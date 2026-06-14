from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from natal_chart.corpus import VECTOR_DIMENSIONS, embed_text


@dataclass(frozen=True)
class RetrievedPassage:
    chunk_id: str
    source_id: str
    chunk_index: int
    text: str
    score: float
    title: str
    author: str | None
    filename: str
    start_word: int
    end_word: int


@dataclass(frozen=True)
class RetrievalResult:
    query: str
    charter: str
    key_images: list[str]
    passages: list[RetrievedPassage]
    sparse: bool
    grounding_note: str | None


def retrieve_passages(
    *,
    index_dir: str | Path | None = None,
    charter: str,
    query: str,
    key_images: list[str] | None = None,
    top_k: int = 5,
    min_results: int = 1,
) -> RetrievalResult:
    if top_k <= 0:
        raise ValueError("top_k must be greater than 0.")
    if min_results < 0:
        raise ValueError("min_results must be non-negative.")

    key_images = list(key_images or [])
    scoped_query = _scoped_query(charter=charter, query=query, key_images=key_images)
    database_path = _database_path(index_dir)
    idf_weights = _load_idf_weights(database_path)
    query_vector = embed_text(scoped_query, idf_weights=idf_weights)

    rows = _load_chunk_rows(database_path)
    scored = sorted(
        (
            RetrievedPassage(
                chunk_id=row["chunk_id"],
                source_id=row["source_id"],
                chunk_index=row["chunk_index"],
                text=row["text"],
                score=round(_dot(query_vector, row["vector"]), 6),
                title=row["title"],
                author=row["author"],
                filename=row["filename"],
                start_word=row["start_word"],
                end_word=row["end_word"],
            )
            for row in rows
        ),
        key=lambda passage: (passage.score, passage.title, -passage.chunk_index),
        reverse=True,
    )[:top_k]

    sparse = len(scored) < min_results
    return RetrievalResult(
        query=query,
        charter=charter,
        key_images=key_images,
        passages=scored,
        sparse=sparse,
        grounding_note=_grounding_note(len(scored), min_results) if sparse else None,
    )


def retrieve_amplification(
    *,
    index_dir: str | Path | None = None,
    key_images: list[str],
    top_k: int = 5,
    min_results: int = 1,
) -> RetrievalResult:
    return retrieve_passages(
        index_dir=index_dir,
        charter="amplification",
        query="myth alchemy fairy tale symbolic parallel amplification image",
        key_images=key_images,
        top_k=top_k,
        min_results=min_results,
    )


def write_agent_grounding(
    *,
    run_dir: str | Path,
    index_dir: str | Path | None = None,
    charter_root: str | Path,
    structures: list[str],
    key_images: list[str] | None = None,
    top_k: int = 5,
    min_results: int = 2,
) -> dict[str, RetrievalResult]:
    run_dir = Path(run_dir)
    charter_root = Path(charter_root)
    chart_brief = (run_dir / "chart-brief.md").read_text(encoding="utf-8")
    grounding_dir = run_dir / "grounding"
    grounding_dir.mkdir(parents=True, exist_ok=True)

    results = {}
    for slug in structures:
        charter = (charter_root / f"{slug}.md").read_text(encoding="utf-8")
        try:
            result = retrieve_passages(
                index_dir=index_dir,
                charter=slug,
                query=f"{charter}\n\n{chart_brief}",
                key_images=key_images,
                top_k=top_k,
                min_results=min_results,
            )
        except FileNotFoundError:
            result = RetrievalResult(
                query=f"{charter}\n\n{chart_brief}",
                charter=slug,
                key_images=list(key_images or []),
                passages=[],
                sparse=True,
                grounding_note=f"Sparse grounding: corpus index not found at {_database_path_candidate(index_dir)}.",
            )
        results[slug] = result
        (grounding_dir / f"{slug}.md").write_text(_grounding_markdown(slug, result), encoding="utf-8")
    return results


def write_amplification_grounding(
    *,
    run_dir: str | Path,
    index_dir: str | Path | None = None,
    key_images: list[str],
    top_k: int = 5,
    min_results: int = 1,
) -> RetrievalResult:
    run_dir = Path(run_dir)
    grounding_dir = run_dir / "grounding"
    grounding_dir.mkdir(parents=True, exist_ok=True)

    try:
        result = retrieve_amplification(
            index_dir=index_dir,
            key_images=key_images,
            top_k=top_k,
            min_results=min_results,
        )
    except FileNotFoundError:
        result = RetrievalResult(
            query="myth alchemy fairy tale symbolic parallel amplification image",
            charter="amplification",
            key_images=list(key_images),
            passages=[],
            sparse=True,
            grounding_note=f"Sparse grounding: corpus index not found at {_database_path_candidate(index_dir)}.",
        )
    (grounding_dir / "amplification.md").write_text(_grounding_markdown("amplification", result), encoding="utf-8")
    return result


DEFAULT_INDEX_DIR = "corpus/index"
INDEX_ENV_VAR = "NATAL_CORPUS_INDEX"


def resolve_index_dir(index_dir: str | Path | None = None) -> Path:
    """Resolve the corpus index location so a run finds it regardless of CWD or
    worktree. Explicit arg wins; else the ``NATAL_CORPUS_INDEX`` env var (a stable
    path that survives worktree isolation); else the in-repo default."""
    if index_dir is not None:
        return Path(index_dir)
    env = os.environ.get(INDEX_ENV_VAR)
    if env and env.strip():
        return Path(env.strip())
    return Path(DEFAULT_INDEX_DIR)


def _database_path(index_dir: str | Path | None) -> Path:
    path = _database_path_candidate(index_dir)
    if not path.exists():
        raise FileNotFoundError(f"Corpus index does not exist: {path}")
    return path


def _database_path_candidate(index_dir: str | Path | None) -> Path:
    path = resolve_index_dir(index_dir)
    if path.is_dir() or path.suffix == "":
        return path / "corpus.sqlite"
    return path


def _scoped_query(*, charter: str, query: str, key_images: list[str]) -> str:
    pieces = [charter, query, *key_images]
    return " ".join(piece for piece in pieces if piece.strip())


def _load_chunk_rows(database_path: Path) -> list[dict[str, object]]:
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            select
              chunks.chunk_id,
              chunks.source_id,
              chunks.chunk_index,
              chunks.text,
              chunks.start_word,
              chunks.end_word,
              sources.title,
              sources.author,
              sources.filename,
              chunk_vectors.dimensions,
              chunk_vectors.vector_json
            from chunks
            join sources on sources.source_id = chunks.source_id
            join chunk_vectors on chunk_vectors.chunk_id = chunks.chunk_id
            """
        ).fetchall()

    loaded = []
    for row in rows:
        vector = json.loads(row["vector_json"])
        if row["dimensions"] != VECTOR_DIMENSIONS or len(vector) != VECTOR_DIMENSIONS:
            raise ValueError(f"Invalid vector dimensions for chunk {row['chunk_id']}.")
        loaded.append({**dict(row), "vector": vector})
    return loaded


def _load_idf_weights(database_path: Path) -> dict[str, float]:
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        try:
            rows = connection.execute("select term, idf from term_idf").fetchall()
        except sqlite3.OperationalError as error:
            if "no such table: term_idf" in str(error):
                return {}
            raise
    return {row["term"]: row["idf"] for row in rows}


def _dot(vector_a: list[float], vector_b: list[float]) -> float:
    return sum(a * b for a, b in zip(vector_a, vector_b, strict=True))


def _grounding_note(result_count: int, min_results: int) -> str:
    return (
        "Sparse grounding: retrieved "
        f"{result_count} passage(s), below the requested minimum of {min_results}."
    )


def _grounding_markdown(slug: str, result: RetrievalResult) -> str:
    lines = [
        f"# Grounding: {slug}",
        "",
        f"- Charter scope: {result.charter}",
        f"- Key images: {', '.join(result.key_images) if result.key_images else 'none'}",
    ]
    if result.grounding_note:
        lines.extend(["", result.grounding_note])
    if not result.passages:
        lines.extend(["", "No retrieved passages."])
        return "\n".join(lines).rstrip() + "\n"

    lines.extend(["", "## Retrieved Passages", ""])
    for index, passage in enumerate(result.passages, start=1):
        author = f"{passage.author}, " if passage.author else ""
        lines.extend(
            [
                f"### {index}. {author}{passage.title}",
                "",
                f"- Source: {passage.filename}",
                f"- Score: {passage.score:.6f}",
                "",
                passage.text,
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"
