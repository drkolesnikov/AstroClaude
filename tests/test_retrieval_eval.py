from natal_chart.corpus import ingest_corpus
from natal_chart.retrieval_eval import (
    CharterRetrievalCase,
    LabeledSource,
    evaluate_retrieval_discrimination,
    write_labeled_fixture,
)


def test_retrieval_eval_scores_on_charter_discrimination(tmp_path):
    source_dir = tmp_path / "sources"
    index_dir = tmp_path / "index"
    labels = write_labeled_fixture(
        source_dir,
        [
            LabeledSource(
                filename="C.G. Jung — Shadow and Individuation.txt",
                charters=("shadow",),
                text="shadow rejected disowned not-I repression inferior function Saturn fear hidden complex " * 80,
            ),
            LabeledSource(
                filename="Anne Carson — Eros the Bittersweet.txt",
                charters=("eros",),
                text="eros desire longing union beloved appetite intimacy beauty Venus Mars relational hunger " * 80,
            ),
            LabeledSource(
                filename="James Hillman — Vocation and Daimon.txt",
                charters=("vocation",),
                text="vocation daimon calling telos work destiny craft public task Saturn Jupiter becoming " * 80,
            ),
        ],
    )
    ingest_corpus(source_dir=source_dir, index_dir=index_dir)

    report = evaluate_retrieval_discrimination(
        index_dir=index_dir,
        labels=labels,
        cases=[
            CharterRetrievalCase(
                charter="shadow",
                query="shadow disowned rejected inferior Saturn complex",
            ),
            CharterRetrievalCase(
                charter="eros",
                query="eros desire beloved intimacy Venus Mars appetite",
            ),
            CharterRetrievalCase(
                charter="vocation",
                query="vocation calling telos public work daimon",
            ),
        ],
        top_k=2,
    )

    assert report.mean_score >= 1.0
    assert report.max_top_source_share <= 0.5
    assert {score.charter: score.top_source for score in report.scores} == {
        "shadow": "C.G. Jung — Shadow and Individuation.txt",
        "eros": "Anne Carson — Eros the Bittersweet.txt",
        "vocation": "James Hillman — Vocation and Daimon.txt",
    }
    assert all(score.on_charter_above_off_charter for score in report.scores)


def test_retrieval_eval_rewards_charter_specific_terms_over_generic_depth_vocabulary(tmp_path):
    source_dir = tmp_path / "sources"
    index_dir = tmp_path / "index"
    labels = write_labeled_fixture(
        source_dir,
        [
            LabeledSource(
                filename="Dense Author — Generic Depth Vocabulary.txt",
                charters=(),
                text="psyche archetype image complex soul individuation chart symbol meaning pattern " * 320,
            ),
            LabeledSource(
                filename="Focused Author — Saturn Boundary.txt",
                charters=("shadow",),
                text="saturn boundary authority discipline necessity fear law time " * 30,
            ),
            LabeledSource(
                filename="Focused Author — Eros Desire.txt",
                charters=("eros",),
                text="eros desire intimacy beloved union venus appetite longing " * 30,
            ),
        ],
    )
    ingest_corpus(source_dir=source_dir, index_dir=index_dir, chunk_words=80, chunk_overlap=0)

    report = evaluate_retrieval_discrimination(
        index_dir=index_dir,
        labels=labels,
        cases=[
            CharterRetrievalCase(
                charter="shadow",
                query="charter shadow psyche archetype image complex soul saturn boundary discipline",
            ),
            CharterRetrievalCase(
                charter="eros",
                query="charter eros psyche archetype image complex soul desire beloved intimacy",
            ),
        ],
        top_k=3,
    )

    assert report.mean_score == 1.0
    assert report.max_top_source_share == 0.5
    assert {score.charter: score.top_source for score in report.scores} == {
        "shadow": "Focused Author — Saturn Boundary.txt",
        "eros": "Focused Author — Eros Desire.txt",
    }
    assert all(score.on_charter_above_off_charter for score in report.scores)


def test_retrieval_eval_clears_low_literal_semantic_discrimination(tmp_path):
    source_dir = tmp_path / "sources"
    index_dir = tmp_path / "index"
    labels = write_labeled_fixture(
        source_dir,
        [
            LabeledSource(
                filename="Depth Author — Banished Twin.txt",
                charters=("shadow",),
                text=(
                    "In the basement lives a banished twin, keeper of forbidden anger and "
                    "unlived vitality behind a sealed door. The shadow appears as this refused double. "
                    * 20
                ),
            ),
            LabeledSource(
                filename="Depth Author — Magnetized Beloved.txt",
                charters=("eros",),
                text=(
                    "A magnetized beloved draws appetite toward union, tenderness, beauty, "
                    "and intimate longing. The eros current moves through the body. "
                    * 20
                ),
            ),
            LabeledSource(
                filename="Literal Author — Dictionary Shadows.txt",
                charters=(),
                text=(
                    "A technical dictionary says shadow means darkness cast by an object; "
                    "rejected ballots are discarded and inferior goods are rejected. "
                    * 20
                ),
            ),
            LabeledSource(
                filename="Other Author — Civic Work.txt",
                charters=(),
                text="The public committee schedules work tasks and administrative categories for planning. " * 20,
            ),
        ],
    )
    ingest_corpus(source_dir=source_dir, index_dir=index_dir, chunk_words=80, chunk_overlap=0)

    report = evaluate_retrieval_discrimination(
        index_dir=index_dir,
        labels=labels,
        cases=[
            CharterRetrievalCase(
                charter="shadow",
                query="disowned rejected inferior complex self",
            ),
            CharterRetrievalCase(
                charter="eros",
                query="desire intimacy beloved appetite union",
            ),
        ],
        top_k=3,
    )

    assert report.mean_score == 1.0
    assert report.max_top_source_share == 0.5
    assert {score.charter: score.top_source for score in report.scores} == {
        "shadow": "Depth Author — Banished Twin.txt",
        "eros": "Depth Author — Magnetized Beloved.txt",
    }
    assert all(score.on_charter_above_off_charter for score in report.scores)
