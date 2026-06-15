from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
from pathlib import Path

from natal_chart.fabrication import FabricationReport, check_fabrications
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
        from natal_chart.run_artifact import relative_path_for

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
            biography_path=relative_path_for("biography") if spec.run_mode == "contextualized" else None,
        )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ValidationReport:
    """The result of the artifact-contract check (Seam 3): whether a run
    directory is well-formed, and every problem found if not."""

    ok: bool
    problems: list[str]


@dataclass(frozen=True)
class RunFabricationReport:
    readings: dict[str, FabricationReport]

    @property
    def total_unsupported_count(self) -> int:
        return sum(report.unsupported_count for report in self.readings.values())

    def to_dict(self) -> dict[str, object]:
        return {
            "total_unsupported_count": self.total_unsupported_count,
            "readings": {slug: report.to_dict() for slug, report in self.readings.items()},
        }


def init_run(
    spec: RunSpec,
    brief: ChartBrief,
    *,
    runs_root: Path,
    timestamp: str,
    revision: str,
    charter_root: Path | None = None,
) -> Path:
    """Lay down a fresh run directory through the artifact contract."""
    from natal_chart.run_artifact import RunArtifact

    return RunArtifact.scaffold(
        runs_root=runs_root,
        spec=spec,
        brief=brief,
        timestamp=timestamp,
        revision=revision,
        charter_root=charter_root,
    ).run_dir


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


def write_fabrication_report(run_dir: Path) -> RunFabricationReport:
    """Check structure readings against the chart brief and write the guard
    report that downstream critic/interpreter steps consume."""
    from natal_chart.run_artifact import RunArtifact

    artifact = RunArtifact(run_dir)
    provenance = artifact.read_json("provenance")
    chart_brief = ChartBrief.from_dict(artifact.read_json("chart_brief_json"))
    readings = {}
    for slug in provenance["structures"]:
        reading_path = artifact.structure_reading(str(slug))
        reading = reading_path.read_text(encoding="utf-8") if reading_path.exists() else ""
        readings[str(slug)] = check_fabrications(reading, chart_brief)

    report = RunFabricationReport(readings=readings)
    artifact.write_json("fabrication_report_json", report.to_dict())
    artifact.write_text("fabrication_report", _fabrication_markdown(report))
    return report


def assemble_dossier(run_dir: Path) -> Path:
    """Compose the layered dossier from the persisted run artifact parts."""
    from natal_chart.run_artifact import RunArtifact

    return RunArtifact(run_dir).assemble()


def validate_run(run_dir: Path) -> ValidationReport:
    """Check a run directory against the artifact contract (Seam 3): provenance,
    chart brief, the depth-critic's pass, the interpreter's portrait, and one
    reading per active structure agent must all be present and non-empty. Reports
    every gap, not just the first."""
    from natal_chart.run_artifact import RunArtifact

    return RunArtifact(run_dir).validate()


def compare_runs(run_a: Path, run_b: Path, *, output_path: Path | None = None) -> Path:
    """Write a side-by-side Markdown comparison for two run artifacts."""
    from natal_chart.run_artifact import RunArtifact

    left = RunArtifact(run_a)
    right = RunArtifact(run_b)
    left_provenance = left.read_json("provenance")
    right_provenance = right.read_json("provenance")

    if left_provenance["native"] != right_provenance["native"]:
        raise ValueError("run comparison requires the same native.")

    native = str(left_provenance["native"])
    output_path = Path(output_path) if output_path else left.run_dir.parent / f"{native}-comparison.md"
    left_name = left.run_dir.name
    right_name = right.run_dir.name

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
        f"| {_markdown_table_cell(_read_required(left.path('interpretation')))} | "
        f"{_markdown_table_cell(_read_required(right.path('interpretation')))} |",
        "",
        "## Reflections",
        "",
        f"| {left_name} | {right_name} |",
        "| --- | --- |",
        f"| {_markdown_table_cell(_read_required(left.path('reflection')))} | "
        f"{_markdown_table_cell(_read_required(right.path('reflection')))} |",
        "",
    ]
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def _fabrication_markdown(report: RunFabricationReport) -> str:
    lines = [
        "# Fabrication Report",
        "",
        f"- Unsupported claim count: {report.total_unsupported_count}",
        "",
        "## Claims to drop before synthesis",
        "",
    ]
    if report.total_unsupported_count == 0:
        lines.append("- None detected")
        return "\n".join(lines).rstrip() + "\n"

    for slug, reading_report in report.readings.items():
        if reading_report.unsupported_count == 0:
            continue
        lines.extend([f"### {slug}", ""])
        for claim in reading_report.unsupported_claims:
            if claim.claim_type == "aspect":
                label = f"{claim.body_a} {claim.aspect} {claim.body_b}"
            else:
                label = f"stationary {claim.body_a}"
            lines.append(f"- Drop `{claim.text}` ({label}): {claim.reason}.")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _read_required(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def _format_nullable(value: object) -> str:
    return "" if value is None else str(value)


def _markdown_table_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", "<br>")
