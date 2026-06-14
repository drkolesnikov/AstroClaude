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
