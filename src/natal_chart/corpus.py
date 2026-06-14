from __future__ import annotations

import hashlib
import html.parser
import json
import math
import re
import sqlite3
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path

from pypdf import PdfReader

SOURCE_EXTENSIONS = {".txt", ".md", ".pdf", ".epub"}
VECTOR_DIMENSIONS = 128
DEFAULT_CHUNK_WORDS = 220
DEFAULT_CHUNK_OVERLAP = 40


@dataclass(frozen=True)
class CorpusIngestionResult:
    indexed_sources: int
    excluded_sources: int
    chunks_indexed: int
    index_path: Path
    manifest_path: Path


@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    filename: str
    title: str
    author: str | None
    extension: str
    sha256: str
    byte_size: int
    chunk_count: int


@dataclass(frozen=True)
class ChunkRecord:
    chunk_id: str
    source_id: str
    chunk_index: int
    text: str
    start_word: int
    end_word: int
    vector: list[float]


@dataclass(frozen=True)
class CurationDecision:
    filename: str
    reason: str


def ingest_corpus(
    *,
    source_dir: str | Path,
    index_dir: str | Path,
    chunk_words: int = DEFAULT_CHUNK_WORDS,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> CorpusIngestionResult:
    source_dir = Path(source_dir)
    index_dir = Path(index_dir)
    if not source_dir.exists():
        raise FileNotFoundError(f"Corpus source directory does not exist: {source_dir}")
    if chunk_words <= 0:
        raise ValueError("chunk_words must be greater than 0")
    if chunk_overlap < 0 or chunk_overlap >= chunk_words:
        raise ValueError("chunk_overlap must be non-negative and smaller than chunk_words")

    index_dir.mkdir(parents=True, exist_ok=True)
    sources, chunks, curation_decisions = _build_records(source_dir, chunk_words, chunk_overlap)

    database_path = index_dir / "corpus.sqlite"
    _write_database(database_path, sources, chunks)

    manifest_path = index_dir / "manifest.json"
    _write_manifest(manifest_path, source_dir, database_path, sources, len(chunks))
    _write_curation_decisions(index_dir / "curation_decisions.json", curation_decisions)

    return CorpusIngestionResult(
        indexed_sources=len(sources),
        excluded_sources=len(curation_decisions),
        chunks_indexed=len(chunks),
        index_path=database_path,
        manifest_path=manifest_path,
    )


def _build_records(
    source_dir: Path,
    chunk_words: int,
    chunk_overlap: int,
) -> tuple[list[SourceRecord], list[ChunkRecord], list[CurationDecision]]:
    sources = []
    chunks = []
    curation_decisions = []
    for path in _source_paths(source_dir):
        raw_bytes = path.read_bytes()
        text = _extract_text(path)
        reason = _exclusion_reason(path, text)
        if reason is not None:
            curation_decisions.append(CurationDecision(filename=path.name, reason=reason))
            continue
        source_id = hashlib.sha256(raw_bytes).hexdigest()
        chunk_texts = list(_chunk_text(text, chunk_words, chunk_overlap))
        source = SourceRecord(
            source_id=source_id,
            filename=path.name,
            title=_title_from_filename(path),
            author=_author_from_filename(path),
            extension=path.suffix.lower(),
            sha256=source_id,
            byte_size=len(raw_bytes),
            chunk_count=len(chunk_texts),
        )
        sources.append(source)
        for chunk_index, (chunk_text, start_word, end_word) in enumerate(chunk_texts):
            chunk_id = hashlib.sha256(f"{source_id}:{chunk_index}".encode("utf-8")).hexdigest()
            chunks.append(
                ChunkRecord(
                    chunk_id=chunk_id,
                    source_id=source_id,
                    chunk_index=chunk_index,
                    text=chunk_text,
                    start_word=start_word,
                    end_word=end_word,
                    vector=_embed(chunk_text),
                )
            )
    return sources, chunks, curation_decisions


def _source_paths(source_dir: Path) -> list[Path]:
    paths = []
    for path in source_dir.iterdir():
        if not path.is_file():
            continue
        if path.name.startswith("."):
            continue
        if path.suffix.lower() not in SOURCE_EXTENSIONS:
            continue
        paths.append(path)
    return sorted(paths, key=lambda item: item.name.casefold())


def _extract_text(path: Path) -> str:
    if path.suffix.lower() in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() == ".pdf":
        return _extract_pdf_text(path)
    if path.suffix.lower() == ".epub":
        return _extract_epub_text(path)
    raise ValueError(f"Unsupported source format for this ingestion path: {path.name}")


def _extract_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    parts = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            parts.append(text.strip())
    return "\n\n".join(parts)


def _extract_epub_text(path: Path) -> str:
    parts = []
    with zipfile.ZipFile(path) as archive:
        for name in sorted(archive.namelist()):
            if not name.lower().endswith((".html", ".xhtml", ".htm")):
                continue
            data = archive.read(name).decode("utf-8", errors="replace")
            parts.append(_html_to_text(data))
    return "\n\n".join(part for part in parts if part.strip())


class _TextExtractor(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data.strip())


def _html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    return " ".join(parser.parts)


def _chunk_text(text: str, chunk_words: int, chunk_overlap: int) -> list[tuple[str, int, int]]:
    words = re.findall(r"\S+", text)
    if not words:
        return []
    chunks = []
    step = chunk_words - chunk_overlap
    start = 0
    while start < len(words):
        end = min(start + chunk_words, len(words))
        chunks.append((" ".join(words[start:end]), start, end))
        if end == len(words):
            break
        start += step
    return chunks


def _embed(text: str) -> list[float]:
    vector = [0.0] * VECTOR_DIMENSIONS
    for token in _tokens(text):
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        value = int.from_bytes(digest, "big")
        index = value % VECTOR_DIMENSIONS
        sign = 1.0 if value & 1 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [round(value / norm, 8) for value in vector]


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.casefold())


def _exclusion_reason(path: Path, text: str) -> str | None:
    name = path.stem.casefold()
    if "cookbook" in name or "sun sign" in name or "delineation table" in name:
        return "cookbook delineation pattern"

    planets = "sun|moon|mercury|venus|mars|jupiter|saturn|uranus|neptune|pluto"
    signs = "aries|taurus|gemini|cancer|leo|virgo|libra|scorpio|sagittarius|capricorn|aquarius|pisces"
    pattern = re.compile(rf"\b(?:{planets})\s+in\s+(?:{signs})\s+means\b", re.IGNORECASE)
    if len(pattern.findall(text)) >= 3:
        return "cookbook delineation pattern"
    return None


def _write_database(database_path: Path, sources: list[SourceRecord], chunks: list[ChunkRecord]) -> None:
    if database_path.exists():
        database_path.unlink()
    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            create table sources (
              source_id text primary key,
              filename text not null,
              title text not null,
              author text,
              extension text not null,
              sha256 text not null,
              byte_size integer not null,
              chunk_count integer not null
            );

            create table chunks (
              chunk_id text primary key,
              source_id text not null references sources(source_id),
              chunk_index integer not null,
              text text not null,
              start_word integer not null,
              end_word integer not null
            );

            create table chunk_vectors (
              chunk_id text primary key references chunks(chunk_id),
              dimensions integer not null,
              vector_json text not null
            );
            """
        )
        connection.executemany(
            """
            insert into sources (
              source_id, filename, title, author, extension, sha256, byte_size, chunk_count
            ) values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    source.source_id,
                    source.filename,
                    source.title,
                    source.author,
                    source.extension,
                    source.sha256,
                    source.byte_size,
                    source.chunk_count,
                )
                for source in sources
            ],
        )
        connection.executemany(
            """
            insert into chunks (
              chunk_id, source_id, chunk_index, text, start_word, end_word
            ) values (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    chunk.chunk_id,
                    chunk.source_id,
                    chunk.chunk_index,
                    chunk.text,
                    chunk.start_word,
                    chunk.end_word,
                )
                for chunk in chunks
            ],
        )
        connection.executemany(
            """
            insert into chunk_vectors (chunk_id, dimensions, vector_json)
            values (?, ?, ?)
            """,
            [
                (
                    chunk.chunk_id,
                    VECTOR_DIMENSIONS,
                    json.dumps(chunk.vector, separators=(",", ":")),
                )
                for chunk in chunks
            ],
        )


def _write_manifest(
    manifest_path: Path,
    source_dir: Path,
    database_path: Path,
    sources: list[SourceRecord],
    chunk_count: int,
) -> None:
    manifest = {
        "source_dir": str(source_dir),
        "database": str(database_path),
        "indexed_sources": len(sources),
        "chunks_indexed": chunk_count,
        "sources": [asdict(source) for source in sources],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_curation_decisions(path: Path, curation_decisions: list[CurationDecision]) -> None:
    payload = {
        "rule": "ADR-0005 no-cookbook curation rule",
        "excluded_sources": [asdict(decision) for decision in curation_decisions],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _title_from_filename(path: Path) -> str:
    stem = path.stem
    if " — " in stem:
        return stem.split(" — ", 1)[1]
    return stem


def _author_from_filename(path: Path) -> str | None:
    stem = path.stem
    if " — " not in stem:
        return None
    return stem.split(" — ", 1)[0]
