from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from natal_chart.models import ChartBrief


@dataclass(frozen=True)
class RunSpec:
    """The configuration of a single run: which native, which layers are in
    frame, the run mode, the active structure agents, and the models per role."""

    native: str
    structures: list[str]
    selection: list[str] = field(default_factory=lambda: ["natal"])
    run_mode: str = "blind"
    models: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Provenance:
    """The auto-captured config of a run, making any judgement reproducible and
    attributable. Revision (git SHA) and timestamp are injected, not captured
    internally, so runs stay deterministic and testable."""

    native: str
    selection: list[str]
    run_mode: str
    structures: list[str]
    models: dict[str, str]
    revision: str
    timestamp: str

    @classmethod
    def from_spec(cls, spec: RunSpec, *, revision: str, timestamp: str) -> Provenance:
        return cls(
            native=spec.native,
            selection=list(spec.selection),
            run_mode=spec.run_mode,
            structures=list(spec.structures),
            models=dict(spec.models),
            revision=revision,
            timestamp=timestamp,
        )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ValidationReport:
    """The result of the artifact-contract check (Seam 3): whether a run
    directory is well-formed, and every problem found if not."""

    ok: bool
    problems: list[str]


def init_run(
    spec: RunSpec,
    brief: ChartBrief,
    *,
    runs_root: Path,
    timestamp: str,
    revision: str,
) -> Path:
    """Lay down a fresh run directory: provenance + the chart brief (json & md)
    and an empty ``structure/`` for the agents to write their readings into."""
    run_dir = Path(runs_root) / f"{spec.native}-{timestamp.replace(':', '')}"
    (run_dir / "structure").mkdir(parents=True, exist_ok=True)

    provenance = Provenance.from_spec(spec, revision=revision, timestamp=timestamp)
    _write_json(run_dir / "provenance.json", provenance.to_dict())
    _write_json(run_dir / "chart-brief.json", brief.to_dict())
    (run_dir / "chart-brief.md").write_text(brief.to_markdown(), encoding="utf-8")
    return run_dir


def assemble_dossier(run_dir: Path) -> Path:
    """Compose the layered ``dossier.md`` from the parts the agents wrote: the
    interpreter's portrait on top, then the structure readings in provenance
    order, then the chart brief beneath."""
    run_dir = Path(run_dir)
    provenance = _read_json(run_dir / "provenance.json")

    parts = [
        "# Dossier",
        "",
        "## Individuation Portrait",
        "",
        (run_dir / "interpretation.md").read_text(encoding="utf-8").rstrip(),
        "",
        "## Structure Readings",
        "",
    ]
    for slug in provenance["structures"]:
        reading = (run_dir / "structure" / f"{slug}.md").read_text(encoding="utf-8").rstrip()
        parts.extend([f"### {slug}", "", reading, ""])
    parts.extend(
        [
            "## Chart Brief",
            "",
            (run_dir / "chart-brief.md").read_text(encoding="utf-8").rstrip(),
            "",
        ]
    )

    dossier_path = run_dir / "dossier.md"
    dossier_path.write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8")
    return dossier_path


def validate_run(run_dir: Path) -> ValidationReport:
    """Check a run directory against the artifact contract (Seam 3): provenance,
    chart brief, the interpreter's portrait, and one reading per active structure
    agent must all be present and non-empty. Reports every gap, not just the first."""
    run_dir = Path(run_dir)
    provenance_path = run_dir / "provenance.json"
    if not _non_empty(provenance_path):
        return ValidationReport(ok=False, problems=["missing provenance.json"])
    provenance = _read_json(provenance_path)

    problems: list[str] = []
    if not _non_empty(run_dir / "chart-brief.md"):
        problems.append("missing chart brief")
    if not _non_empty(run_dir / "interpretation.md"):
        problems.append("missing interpretation")
    for slug in provenance["structures"]:
        if not _non_empty(run_dir / "structure" / f"{slug}.md"):
            problems.append(f"missing structure reading: {slug}")

    return ValidationReport(ok=not problems, problems=problems)


def _non_empty(path: Path) -> bool:
    return path.exists() and path.read_text(encoding="utf-8").strip() != ""


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))
