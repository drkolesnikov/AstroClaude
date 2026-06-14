import json
import sqlite3
import zipfile
from pathlib import Path

from natal_chart.corpus import ingest_corpus
from natal_chart.semantic import SEMANTIC_MODEL_NAME, VECTOR_DIMENSIONS


def test_ingest_corpus_indexes_flat_text_sources(tmp_path):
    source_dir = tmp_path / "sources"
    index_dir = tmp_path / "index"
    source_dir.mkdir()
    (source_dir / "C.G. Jung — CW 7, Two Essays on Analytical Psychology.txt").write_text(
        "Persona and individuation are not abstractions here. "
        "The psyche is described through complexes, adaptation, and the work of becoming.\n"
        * 80,
        encoding="utf-8",
    )
    (source_dir / "James Hillman — Re-Visioning Psychology.txt").write_text(
        "The imaginal attitude asks for seeing-through, image, soul, and polytheistic psychology.\n"
        * 80,
        encoding="utf-8",
    )
    (source_dir / "clean_source_filenames.rs").write_text("not a corpus document", encoding="utf-8")
    (source_dir / ".hidden-helper").write_text("not a corpus document", encoding="utf-8")

    result = ingest_corpus(source_dir=source_dir, index_dir=index_dir)

    assert result.indexed_sources == 2
    assert result.excluded_sources == 0
    assert result.chunks_indexed > 0
    assert (index_dir / "corpus.sqlite").exists()
    assert (index_dir / "manifest.json").exists()

    manifest = json.loads((index_dir / "manifest.json").read_text(encoding="utf-8"))
    assert [source["filename"] for source in manifest["sources"]] == [
        "C.G. Jung — CW 7, Two Essays on Analytical Psychology.txt",
        "James Hillman — Re-Visioning Psychology.txt",
    ]

    with sqlite3.connect(index_dir / "corpus.sqlite") as connection:
        source_count = connection.execute("select count(*) from sources").fetchone()[0]
        chunk_count = connection.execute("select count(*) from chunks").fetchone()[0]
        vector_count = connection.execute("select count(*) from chunk_vectors").fetchone()[0]

    assert source_count == 2
    assert chunk_count == result.chunks_indexed
    assert vector_count == result.chunks_indexed


def test_ingest_corpus_persists_local_semantic_model(tmp_path):
    source_dir = tmp_path / "sources"
    index_dir = tmp_path / "index"
    source_dir.mkdir()
    (source_dir / "Depth Author — Shadow Essay.txt").write_text(
        "Shadow, hidden double, basement twin, disowned anger, and the work of integration.\n" * 40,
        encoding="utf-8",
    )

    ingest_corpus(source_dir=source_dir, index_dir=index_dir)

    manifest = json.loads((index_dir / "manifest.json").read_text(encoding="utf-8"))
    with sqlite3.connect(index_dir / "corpus.sqlite") as connection:
        row = connection.execute(
            "select model_name, dimensions, payload_json from embedding_model"
        ).fetchone()

    assert manifest["embedding_model"] == SEMANTIC_MODEL_NAME
    assert row[0] == SEMANTIC_MODEL_NAME
    assert row[1] == VECTOR_DIMENSIONS
    payload = json.loads(row[2])
    assert payload["name"] == SEMANTIC_MODEL_NAME
    assert payload["dimensions"] == VECTOR_DIMENSIONS
    assert "shadow" in payload["concept_order"]


def test_ingest_corpus_excludes_and_records_cookbook_sources(tmp_path):
    source_dir = tmp_path / "sources"
    index_dir = tmp_path / "index"
    source_dir.mkdir()
    (source_dir / "Depth Author — Archetypal Essay.txt").write_text(
        "Archetypal image psyche shadow individuation complex symbolic amplification.\n" * 50,
        encoding="utf-8",
    )
    (source_dir / "Cookbook Author — Sun Sign Tables.txt").write_text(
        "Sun in Aries means bold. Moon in Taurus means stable. Mercury in Gemini means clever.\n"
        "Venus in Cancer means tender. Mars in Leo means dramatic.\n"
        * 25,
        encoding="utf-8",
    )

    result = ingest_corpus(source_dir=source_dir, index_dir=index_dir)

    assert result.indexed_sources == 1
    assert result.excluded_sources == 1

    decisions = json.loads((index_dir / "curation_decisions.json").read_text(encoding="utf-8"))
    assert decisions["excluded_sources"] == [
        {
            "filename": "Cookbook Author — Sun Sign Tables.txt",
            "reason": "cookbook delineation pattern",
        }
    ]

    manifest = json.loads((index_dir / "manifest.json").read_text(encoding="utf-8"))
    assert [source["filename"] for source in manifest["sources"]] == [
        "Depth Author — Archetypal Essay.txt"
    ]


def test_ingest_corpus_is_rerunnable_without_duplicate_chunks(tmp_path):
    source_dir = tmp_path / "sources"
    index_dir = tmp_path / "index"
    source_dir.mkdir()
    (source_dir / "Murray Stein — Jung's Map of the Soul.txt").write_text(
        "Ego persona shadow anima animus Self complex individuation.\n" * 60,
        encoding="utf-8",
    )

    first = ingest_corpus(source_dir=source_dir, index_dir=index_dir)
    second = ingest_corpus(source_dir=source_dir, index_dir=index_dir)

    assert second.indexed_sources == first.indexed_sources
    assert second.chunks_indexed == first.chunks_indexed
    with sqlite3.connect(index_dir / "corpus.sqlite") as connection:
        chunk_count = connection.execute("select count(*) from chunks").fetchone()[0]
        chunk_ids = connection.execute("select count(distinct chunk_id) from chunks").fetchone()[0]

    assert chunk_count == first.chunks_indexed
    assert chunk_ids == chunk_count


def test_ingest_corpus_extracts_epub_text(tmp_path):
    source_dir = tmp_path / "sources"
    index_dir = tmp_path / "index"
    source_dir.mkdir()
    epub_path = source_dir / "Liz Greene & Howard Sasportas — Dynamics of the Unconscious.epub"
    with zipfile.ZipFile(epub_path, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip")
        archive.writestr(
            "chapter.xhtml",
            """
            <html xmlns="http://www.w3.org/1999/xhtml">
              <body>
                <h1>Dynamics of the Unconscious</h1>
                <p>Dream image complex shadow psyche amplification.</p>
              </body>
            </html>
            """,
        )

    result = ingest_corpus(source_dir=source_dir, index_dir=index_dir)

    assert result.indexed_sources == 1
    with sqlite3.connect(index_dir / "corpus.sqlite") as connection:
        text = connection.execute("select text from chunks").fetchone()[0]

    assert "Dream image complex shadow psyche amplification" in text


def test_ingest_corpus_extracts_pdf_text(tmp_path):
    source_dir = tmp_path / "sources"
    index_dir = tmp_path / "index"
    source_dir.mkdir()
    (source_dir / "C.G. Jung — CW 9i, The Archetypes and the Collective Unconscious.pdf").write_bytes(
        b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>
endobj
4 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
5 0 obj
<< /Length 75 >>
stream
BT
/F1 12 Tf
72 720 Td
(Archetype collective unconscious mandala shadow psyche) Tj
ET
endstream
endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000241 00000 n
0000000311 00000 n
trailer
<< /Root 1 0 R /Size 6 >>
startxref
436
%%EOF
"""
    )

    result = ingest_corpus(source_dir=source_dir, index_dir=index_dir)

    assert result.indexed_sources == 1
    with sqlite3.connect(index_dir / "corpus.sqlite") as connection:
        text = connection.execute("select text from chunks").fetchone()[0]

    assert "Archetype collective unconscious mandala shadow psyche" in text


def test_corpus_source_and_index_paths_are_gitignored():
    gitignore = Path(".gitignore").read_text(encoding="utf-8")

    assert "corpus/sources/" in gitignore
    assert "corpus/index/" in gitignore
