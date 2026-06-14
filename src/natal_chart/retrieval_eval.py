from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from natal_chart.retrieve import retrieve_passages


@dataclass(frozen=True)
class LabeledSource:
    filename: str
    charters: tuple[str, ...]
    text: str


@dataclass(frozen=True)
class CharterRetrievalCase:
    charter: str
    query: str
    key_images: tuple[str, ...] = ()


@dataclass(frozen=True)
class SourceLabels:
    by_filename: dict[str, tuple[str, ...]]

    def filenames_for(self, charter: str) -> set[str]:
        return {filename for filename, charters in self.by_filename.items() if charter in charters}


@dataclass(frozen=True)
class CharterDiscriminationScore:
    charter: str
    score: float
    top_source: str | None
    top_sources: tuple[str, ...]
    expected_sources: tuple[str, ...]
    on_charter_above_off_charter: bool


@dataclass(frozen=True)
class RetrievalDiscriminationReport:
    scores: tuple[CharterDiscriminationScore, ...]
    mean_score: float
    max_top_source_share: float


def write_labeled_fixture(source_dir: str | Path, sources: list[LabeledSource]) -> SourceLabels:
    source_dir = Path(source_dir)
    source_dir.mkdir(parents=True, exist_ok=True)
    labels = {}
    for source in sources:
        (source_dir / source.filename).write_text(source.text, encoding="utf-8")
        labels[source.filename] = tuple(source.charters)
    return SourceLabels(by_filename=labels)


def evaluate_retrieval_discrimination(
    *,
    index_dir: str | Path,
    labels: SourceLabels,
    cases: list[CharterRetrievalCase],
    top_k: int,
) -> RetrievalDiscriminationReport:
    scores = []
    for case in cases:
        result = retrieve_passages(
            index_dir=index_dir,
            charter=case.charter,
            query=case.query,
            key_images=list(case.key_images),
            top_k=top_k,
        )
        expected_sources = labels.filenames_for(case.charter)
        top_sources = tuple(passage.filename for passage in result.passages)
        score = _rank_score(top_sources, expected_sources)
        scores.append(
            CharterDiscriminationScore(
                charter=case.charter,
                score=score,
                top_source=top_sources[0] if top_sources else None,
                top_sources=top_sources,
                expected_sources=tuple(sorted(expected_sources)),
                on_charter_above_off_charter=_on_charter_above_off_charter(top_sources, expected_sources),
            )
        )

    mean_score = sum(score.score for score in scores) / len(scores) if scores else 0.0
    return RetrievalDiscriminationReport(
        scores=tuple(scores),
        mean_score=round(mean_score, 4),
        max_top_source_share=_max_top_source_share(scores),
    )


def _rank_score(top_sources: tuple[str, ...], expected_sources: set[str]) -> float:
    if not top_sources or not expected_sources:
        return 0.0
    for index, filename in enumerate(top_sources, start=1):
        if filename in expected_sources:
            return 1 / index
    return 0.0


def _on_charter_above_off_charter(top_sources: tuple[str, ...], expected_sources: set[str]) -> bool:
    if not top_sources or not expected_sources:
        return False
    first_expected_rank = next(
        (index for index, filename in enumerate(top_sources) if filename in expected_sources),
        None,
    )
    first_off_rank = next(
        (index for index, filename in enumerate(top_sources) if filename not in expected_sources),
        None,
    )
    if first_expected_rank is None:
        return False
    if first_off_rank is None:
        return True
    return first_expected_rank < first_off_rank


def _max_top_source_share(scores: list[CharterDiscriminationScore]) -> float:
    top_sources = [score.top_source for score in scores if score.top_source is not None]
    if not top_sources:
        return 0.0
    counts = Counter(top_sources)
    return round(max(counts.values()) / len(top_sources), 4)
