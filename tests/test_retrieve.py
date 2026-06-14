from pathlib import Path

from natal_chart.corpus import ingest_corpus
from natal_chart.retrieve import (
    DEFAULT_INDEX_DIR,
    resolve_index_dir,
    retrieve_amplification,
    retrieve_passages,
    write_agent_grounding,
    write_amplification_grounding,
)


def test_retrieve_passages_returns_ranked_depth_corpus_passages(tmp_path):
    source_dir = tmp_path / "sources"
    index_dir = tmp_path / "index"
    source_dir.mkdir()
    (source_dir / "C.G. Jung — Shadow and Individuation.txt").write_text(
        "The shadow gathers rejected psychic material. "
        "Saturn images authority, fear, discipline, and the hard gate of individuation.\n"
        * 80,
        encoding="utf-8",
    )
    (source_dir / "James Hillman — The Dream and the Underworld.txt").write_text(
        "Dream, image, soul, underworld, and mythic descent ask the psyche to see through literalism.\n"
        * 80,
        encoding="utf-8",
    )
    ingest_corpus(source_dir=source_dir, index_dir=index_dir)

    result = retrieve_passages(
        index_dir=index_dir,
        charter="shadow",
        query="Saturn shadow authority fear discipline",
        key_images=["Saturn", "shadow"],
        top_k=2,
    )

    assert result.sparse is False
    assert len(result.passages) == 2
    assert result.passages[0].score >= result.passages[1].score
    assert result.passages[0].title == "Shadow and Individuation"
    assert result.passages[0].author == "C.G. Jung"
    assert result.passages[0].filename == "C.G. Jung — Shadow and Individuation.txt"
    assert "Saturn images authority" in result.passages[0].text


def test_retrieval_weights_charter_specific_terms_above_ubiquitous_depth_terms(tmp_path):
    source_dir = tmp_path / "sources"
    index_dir = tmp_path / "index"
    source_dir.mkdir()
    (source_dir / "Dense Author — Generic Depth Vocabulary.txt").write_text(
        "psyche archetype image complex soul individuation chart symbol meaning pattern " * 320,
        encoding="utf-8",
    )
    (source_dir / "Focused Author — Saturn Boundary.txt").write_text(
        "saturn boundary authority discipline necessity fear law time " * 30,
        encoding="utf-8",
    )
    (source_dir / "Other Author — Eros.txt").write_text(
        "eros desire intimacy beloved union venus appetite " * 30,
        encoding="utf-8",
    )
    ingest_corpus(source_dir=source_dir, index_dir=index_dir, chunk_words=80, chunk_overlap=0)

    result = retrieve_passages(
        index_dir=index_dir,
        charter="shadow",
        query="charter shadow psyche archetype image complex soul saturn boundary discipline",
        top_k=3,
    )

    assert result.passages[0].filename == "Focused Author — Saturn Boundary.txt"


def test_retrieve_passages_matches_shadow_semantics_with_low_literal_overlap(tmp_path):
    source_dir = tmp_path / "sources"
    index_dir = tmp_path / "index"
    source_dir.mkdir()
    (source_dir / "Depth Author — Banished Twin.txt").write_text(
        "In the basement lives a banished twin, keeper of forbidden anger and "
        "unlived vitality behind a sealed door. The shadow appears as this refused double. "
        * 20,
        encoding="utf-8",
    )
    (source_dir / "Literal Author — Dictionary Shadows.txt").write_text(
        "A technical dictionary says shadow means darkness cast by an object; "
        "rejected ballots are discarded and inferior goods are rejected. "
        * 20,
        encoding="utf-8",
    )
    (source_dir / "Other Author — Desire.txt").write_text(
        "eros beloved appetite union desire intimacy beauty longing " * 30,
        encoding="utf-8",
    )
    ingest_corpus(source_dir=source_dir, index_dir=index_dir, chunk_words=80, chunk_overlap=0)

    result = retrieve_passages(
        index_dir=index_dir,
        charter="shadow",
        query="disowned rejected inferior complex self",
        top_k=3,
    )

    assert result.passages[0].filename == "Depth Author — Banished Twin.txt"
    assert "banished twin" in result.passages[0].text


def test_retrieve_amplification_returns_mythic_material_for_key_images(tmp_path):
    source_dir = tmp_path / "sources"
    index_dir = tmp_path / "index"
    source_dir.mkdir()
    (source_dir / "Marie-Louise von Franz — Fairy Tales and Alchemy.txt").write_text(
        "The underworld descent appears in fairy tale and alchemy as nigredo, "
        "the dark vessel where the old king dies and the soul image is transformed.\n"
        * 80,
        encoding="utf-8",
    )
    (source_dir / "Liz Greene — Saturn.txt").write_text(
        "Saturn as discipline, time, fear, boundary, and apprenticeship to necessity.\n"
        * 80,
        encoding="utf-8",
    )
    ingest_corpus(source_dir=source_dir, index_dir=index_dir)

    result = retrieve_amplification(
        index_dir=index_dir,
        key_images=["underworld descent", "nigredo"],
        top_k=1,
    )

    assert result.sparse is False
    assert result.charter == "amplification"
    assert result.passages[0].title == "Fairy Tales and Alchemy"
    assert "underworld descent" in result.passages[0].text


def test_retrieval_results_preserve_no_cookbook_curation_invariant(tmp_path):
    source_dir = tmp_path / "sources"
    index_dir = tmp_path / "index"
    source_dir.mkdir()
    (source_dir / "Depth Author — Archetypal Essay.txt").write_text(
        "Shadow, complex, image, psyche, individuation, and symbolic amplification.\n" * 80,
        encoding="utf-8",
    )
    (source_dir / "Cookbook Author — Delineation Tables.txt").write_text(
        "Sun in Aries means bold. Moon in Taurus means stable. Mercury in Gemini means clever.\n"
        "Venus in Cancer means tender. Mars in Leo means dramatic.\n"
        * 25,
        encoding="utf-8",
    )
    ingest_corpus(source_dir=source_dir, index_dir=index_dir)

    result = retrieve_passages(
        index_dir=index_dir,
        charter="ego",
        query="Sun in Aries means bold symbolic ego",
        top_k=5,
    )

    assert result.passages
    filenames = {passage.filename for passage in result.passages}
    assert filenames == {"Depth Author — Archetypal Essay.txt"}
    assert all("means bold" not in passage.text for passage in result.passages)


def test_retrieve_passages_flags_sparse_grounding_for_empty_corpus(tmp_path):
    source_dir = tmp_path / "sources"
    index_dir = tmp_path / "index"
    source_dir.mkdir()
    ingest_corpus(source_dir=source_dir, index_dir=index_dir)

    result = retrieve_passages(
        index_dir=index_dir,
        charter="wound",
        query="Chiron wound medicine",
        top_k=3,
        min_results=2,
    )

    assert result.passages == []
    assert result.sparse is True
    assert result.grounding_note == "Sparse grounding: retrieved 0 passage(s), below the requested minimum of 2."


def test_resolve_index_dir_prefers_arg_then_env_then_default(tmp_path, monkeypatch):
    # explicit arg always wins
    assert resolve_index_dir(tmp_path / "explicit") == tmp_path / "explicit"
    # else the env var (a stable path that survives worktree isolation)
    monkeypatch.setenv("NATAL_CORPUS_INDEX", str(tmp_path / "from-env"))
    assert resolve_index_dir() == tmp_path / "from-env"
    assert resolve_index_dir(None) == tmp_path / "from-env"
    assert resolve_index_dir(tmp_path / "explicit") == tmp_path / "explicit"
    # else the in-repo default
    monkeypatch.delenv("NATAL_CORPUS_INDEX", raising=False)
    assert resolve_index_dir() == Path(DEFAULT_INDEX_DIR)


def test_retrieve_resolves_corpus_from_env_when_index_dir_omitted(tmp_path, monkeypatch):
    # Regression for the corpus-reachability bug: a run launched without a
    # CWD-local corpus (e.g. an isolation worktree) must still find the corpus via
    # NATAL_CORPUS_INDEX rather than silently grounding on nothing.
    source_dir = tmp_path / "sources"
    index_dir = tmp_path / "stable-home" / "index"
    source_dir.mkdir()
    (source_dir / "C.G. Jung — Shadow.txt").write_text(
        "The shadow gathers rejected psychic material; Saturn images the hard gate.\n" * 80,
        encoding="utf-8",
    )
    ingest_corpus(source_dir=source_dir, index_dir=index_dir)
    monkeypatch.setenv("NATAL_CORPUS_INDEX", str(index_dir))

    result = retrieve_passages(charter="shadow", query="Saturn shadow", min_results=1)

    assert result.sparse is False
    assert result.passages


def test_write_agent_grounding_flags_sparse_corpus_without_blocking_run(tmp_path):
    source_dir = tmp_path / "sources"
    index_dir = tmp_path / "index"
    run_dir = tmp_path / "run"
    charter_root = tmp_path / "agents"
    source_dir.mkdir()
    run_dir.mkdir()
    charter_root.mkdir()
    ingest_corpus(source_dir=source_dir, index_dir=index_dir)
    (run_dir / "chart-brief.md").write_text("Saturn in the twelfth house square the Moon.\n", encoding="utf-8")
    (charter_root / "shadow.md").write_text(
        "# Shadow\nWhat is split off and disowned in this psyche?\n",
        encoding="utf-8",
    )

    results = write_agent_grounding(
        run_dir=run_dir,
        index_dir=index_dir,
        charter_root=charter_root,
        structures=["shadow"],
        key_images=["Saturn", "twelfth house"],
        min_results=2,
    )

    grounding = (run_dir / "grounding" / "shadow.md").read_text(encoding="utf-8")
    assert results["shadow"].sparse is True
    assert "# Grounding: shadow" in grounding
    assert "Sparse grounding" in grounding
    assert "No retrieved passages" in grounding


def test_write_agent_grounding_flags_missing_index_without_blocking_run(tmp_path):
    run_dir = tmp_path / "run"
    charter_root = tmp_path / "agents"
    run_dir.mkdir()
    charter_root.mkdir()
    (run_dir / "chart-brief.md").write_text("Moon opposite Saturn.\n", encoding="utf-8")
    (charter_root / "parental.md").write_text(
        "# Parental\nWhat mother and father imagos does this psyche carry?\n",
        encoding="utf-8",
    )

    results = write_agent_grounding(
        run_dir=run_dir,
        index_dir=tmp_path / "missing-index",
        charter_root=charter_root,
        structures=["parental"],
        key_images=["Moon opposite Saturn"],
    )

    grounding = (run_dir / "grounding" / "parental.md").read_text(encoding="utf-8")
    assert results["parental"].sparse is True
    assert "corpus index not found" in grounding
    assert "No retrieved passages" in grounding


def test_write_amplification_grounding_flags_missing_index_without_blocking_run(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    result = write_amplification_grounding(
        run_dir=run_dir,
        index_dir=tmp_path / "missing-index",
        key_images=["underworld descent"],
    )

    grounding = (run_dir / "grounding" / "amplification.md").read_text(encoding="utf-8")
    assert result.sparse is True
    assert "corpus index not found" in grounding
    assert "No retrieved passages" in grounding
