from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from hashlib import sha256
from pathlib import Path

from natal_chart.models import ChartBrief

REFLECTION_SCAFFOLD = """# Reflection

## What landed


## What felt generic or Barnum


## What surprised

"""


@dataclass(frozen=True)
class RunSpec:
    """The configuration of a single run: which native, which layers are in
    frame, the run mode, the active structure agents, and the models per role."""

    native: str
    structures: list[str]
    selection: list[str] = field(default_factory=lambda: ["natal"])
    run_mode: str = "blind"
    biography: str | None = None
    models: dict[str, str] = field(default_factory=dict)
    seed: int | None = None


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
    seed: int | None = None
    chart_brief_sha256: str | None = None
    charter_sha256: dict[str, str] = field(default_factory=dict)
    biography_path: str | None = None

    @classmethod
    def from_spec(
        cls,
        spec: RunSpec,
        *,
        revision: str,
        timestamp: str,
        chart_brief_sha256: str | None = None,
        charter_sha256: dict[str, str] | None = None,
    ) -> Provenance:
        return cls(
            native=spec.native,
            selection=list(spec.selection),
            run_mode=spec.run_mode,
            structures=list(spec.structures),
            models=dict(spec.models),
            revision=revision,
            timestamp=timestamp,
            seed=spec.seed,
            chart_brief_sha256=chart_brief_sha256,
            charter_sha256=dict(charter_sha256 or {}),
            biography_path="biography.md" if spec.run_mode == "contextualized" else None,
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
    charter_root: Path | None = None,
) -> Path:
    """Lay down a fresh run directory: provenance + the chart brief (json & md)
    and an empty ``structure/`` for the agents to write their readings into."""
    _validate_run_spec(spec)
    run_dir = Path(runs_root) / f"{spec.native}-{timestamp.replace(':', '')}"
    (run_dir / "structure").mkdir(parents=True, exist_ok=True)

    chart_brief_path = run_dir / "chart-brief.json"
    _write_json(chart_brief_path, brief.to_dict())
    provenance = Provenance.from_spec(
        spec,
        revision=revision,
        timestamp=timestamp,
        chart_brief_sha256=_sha256_file(chart_brief_path),
        charter_sha256=_charter_hashes(spec.structures, charter_root),
    )
    _write_json(run_dir / "provenance.json", provenance.to_dict())
    (run_dir / "chart-brief.md").write_text(brief.to_markdown(), encoding="utf-8")
    (run_dir / "reflection.md").write_text(REFLECTION_SCAFFOLD, encoding="utf-8")
    if spec.run_mode == "contextualized":
        (run_dir / "biography.md").write_text(spec.biography.strip() + "\n", encoding="utf-8")
    return run_dir


def _validate_run_spec(spec: RunSpec) -> None:
    if spec.run_mode not in {"blind", "contextualized"}:
        raise ValueError("run_mode must be 'blind' or 'contextualized'.")
    if spec.run_mode == "contextualized" and not (spec.biography and spec.biography.strip()):
        raise ValueError("contextualized runs require a biography.")
    if spec.run_mode == "blind" and spec.biography:
        raise ValueError("blind runs must not include biography.")


def _charter_hashes(structures: list[str], charter_root: Path | None) -> dict[str, str]:
    if charter_root is None:
        return {}
    root = Path(charter_root)
    return {slug: _sha256_file(root / f"{slug}.md") for slug in structures}


def _sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


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
            "## Critic Challenges",
            "",
            (run_dir / "critic.md").read_text(encoding="utf-8").rstrip(),
            "",
            "## Chart Brief",
            "",
            (run_dir / "chart-brief.md").read_text(encoding="utf-8").rstrip(),
            "",
            "## Reflection",
            "",
            (run_dir / "reflection.md").read_text(encoding="utf-8").rstrip(),
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
    if not _non_empty(run_dir / "critic.md"):
        problems.append("missing critic")
    if not _non_empty(run_dir / "reflection.md"):
        problems.append("missing reflection")
    for slug in provenance["structures"]:
        if not _non_empty(run_dir / "structure" / f"{slug}.md"):
            problems.append(f"missing structure reading: {slug}")

    return ValidationReport(ok=not problems, problems=problems)


def compare_runs(run_a: Path, run_b: Path, *, output_path: Path | None = None) -> Path:
    """Write a side-by-side Markdown comparison for two run artifacts."""
    left = Path(run_a)
    right = Path(run_b)
    left_provenance = _read_json(left / "provenance.json")
    right_provenance = _read_json(right / "provenance.json")

    if left_provenance["native"] != right_provenance["native"]:
        raise ValueError("run comparison requires the same native.")

    native = str(left_provenance["native"])
    output_path = Path(output_path) if output_path else left.parent / f"{native}-comparison.md"
    left_name = left.name
    right_name = right.name

    lines = [
        f"# Run Comparison: {native}",
        "",
        f"| Field | {left_name} | {right_name} |",
        "| --- | --- | --- |",
        f"| Run mode | {left_provenance['run_mode']} | {right_provenance['run_mode']} |",
        f"| Selection | {', '.join(left_provenance['selection'])} | {', '.join(right_provenance['selection'])} |",
        f"| Seed | {_format_nullable(left_provenance.get('seed'))} | {_format_nullable(right_provenance.get('seed'))} |",
        f"| Revision | {left_provenance['revision']} | {right_provenance['revision']} |",
        f"| Timestamp | {left_provenance['timestamp']} | {right_provenance['timestamp']} |",
        "",
        "## Individuation Portraits",
        "",
        f"| {left_name} | {right_name} |",
        "| --- | --- |",
        f"| {_markdown_table_cell(_read_required(left / 'interpretation.md'))} | "
        f"{_markdown_table_cell(_read_required(right / 'interpretation.md'))} |",
        "",
        "## Reflections",
        "",
        f"| {left_name} | {right_name} |",
        "| --- | --- |",
        f"| {_markdown_table_cell(_read_required(left / 'reflection.md'))} | "
        f"{_markdown_table_cell(_read_required(right / 'reflection.md'))} |",
        "",
    ]
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def _non_empty(path: Path) -> bool:
    return path.exists() and path.read_text(encoding="utf-8").strip() != ""


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_required(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def _format_nullable(value: object) -> str:
    return "" if value is None else str(value)


def _markdown_table_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", "<br>")
