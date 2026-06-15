from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from natal_chart.models import ChartBrief
    from natal_chart.run import RunSpec, ValidationReport


@dataclass(frozen=True)
class ArtifactPart:
    key: str
    path: str
    required: bool
    family: str | None = None
    order: int | None = None
    heading: str | None = None


LAYOUT: tuple[ArtifactPart, ...] = (
    ArtifactPart(key="provenance", path="provenance.json", required=True),
    ArtifactPart(key="chart_brief_json", path="chart-brief.json", required=True),
    ArtifactPart(key="chart_brief", path="chart-brief.md", required=True, order=50, heading="Chart Brief"),
    ArtifactPart(key="reflection", path="reflection.md", required=True, order=60, heading="Reflection"),
    ArtifactPart(key="biography", path="biography.md", required=False),
    ArtifactPart(
        key="structure_reading",
        path="structure/{slug}.md",
        required=True,
        family="structure",
        order=20,
        heading="Structure Readings",
    ),
    ArtifactPart(key="grounding", path="grounding/{slug}.md", required=False, family="grounding"),
    ArtifactPart(key="amplification_grounding", path="grounding/amplification.md", required=False),
    ArtifactPart(key="critic", path="critic.md", required=True, order=40, heading="Critic Challenges"),
    ArtifactPart(
        key="interpretation",
        path="interpretation.md",
        required=True,
        order=10,
        heading="Individuation Portrait",
    ),
    ArtifactPart(key="fabrication_report_json", path="fabrication-report.json", required=True),
    ArtifactPart(
        key="fabrication_report",
        path="fabrication-report.md",
        required=True,
        order=30,
        heading="Fabrication Guard",
    ),
    ArtifactPart(key="dossier", path="dossier.md", required=False),
)

_PARTS_BY_KEY = {part.key: part for part in LAYOUT}
_PARTS_BY_PATH = {part.path: part for part in LAYOUT}
_FABRICATION_KEYS = {"fabrication_report_json", "fabrication_report"}
_INVALID_FABRICATION_REPORT = object()

_MISSING_MESSAGES = {
    "chart_brief_json": "missing chart brief json",
    "chart_brief": "missing chart brief",
    "interpretation": "missing interpretation",
    "critic": "missing critic",
    "reflection": "missing reflection",
}


@dataclass(frozen=True)
class RunArtifact:
    run_dir: Path

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_dir", Path(self.run_dir))

    @classmethod
    def scaffold(
        cls,
        *,
        runs_root: str | Path,
        spec: RunSpec,
        brief: ChartBrief,
        timestamp: str,
        revision: str,
        charter_root: str | Path | None = None,
    ) -> RunArtifact:
        from natal_chart.run import (
            REFLECTION_SCAFFOLD,
            Provenance,
            _charter_hashes,
            _sha256_file,
            _validate_run_spec,
        )

        _validate_run_spec(spec)
        run_dir = Path(runs_root) / f"{spec.native}-{timestamp.replace(':', '')}"
        artifact = cls(run_dir)
        artifact.structure_reading("_scaffold").parent.mkdir(parents=True, exist_ok=True)

        artifact.write_json("chart_brief_json", brief.to_dict())
        provenance = Provenance.from_spec(
            spec,
            revision=revision,
            timestamp=timestamp,
            chart_brief_sha256=_sha256_file(artifact.path("chart_brief_json")),
            charter_sha256=_charter_hashes(spec.structures, Path(charter_root) if charter_root is not None else None),
        )
        artifact.write_json("provenance", provenance.to_dict())
        artifact.write_text("chart_brief", brief.to_markdown())
        artifact.write_text("reflection", REFLECTION_SCAFFOLD)
        if spec.run_mode == "contextualized":
            artifact.write_text("biography", spec.biography.strip() + "\n")
        return artifact

    @property
    def dossier_path(self) -> Path:
        return self.path("dossier")

    def structure_reading(self, slug: str) -> Path:
        return self.path("structure_reading", slug=slug)

    def grounding_path(self, slug: str) -> Path:
        return self.path("grounding", slug=slug)

    def path(self, key: str, *, slug: str | None = None) -> Path:
        part = _part_for_key(key)
        if part.family:
            if slug is None or str(slug).strip() == "":
                raise ValueError(f"{key} requires a slug.")
            relative_path = part.path.format(slug=slug)
        else:
            if slug is not None:
                raise ValueError(f"{key} does not accept a slug.")
            relative_path = part.path
        return self.run_dir / relative_path

    def read_text(self, key: str, *, slug: str | None = None) -> str:
        return self.path(key, slug=slug).read_text(encoding="utf-8")

    def write_text(self, key: str, text: str, *, slug: str | None = None) -> Path:
        path = self.path(key, slug=slug)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def read_json(self, key: str, *, slug: str | None = None) -> dict[str, object]:
        return json.loads(self.read_text(key, slug=slug))

    def write_json(self, key: str, payload: object, *, slug: str | None = None) -> Path:
        return self.write_text(key, json.dumps(payload, indent=2, ensure_ascii=False) + "\n", slug=slug)

    def validate(self) -> ValidationReport:
        from natal_chart.run import ValidationReport

        provenance_path = self.path("provenance")
        if not _non_empty(provenance_path):
            return ValidationReport(ok=False, problems=["missing provenance.json"])
        provenance = self.read_json("provenance")

        problems: list[str] = []
        for part in LAYOUT:
            if part.key in {"provenance", "biography"} or part.family or not part.required:
                continue
            if part.key in _FABRICATION_KEYS:
                continue
            if not _non_empty(self.path(part.key)):
                problems.append(_MISSING_MESSAGES[part.key])

        if provenance.get("run_mode") == "contextualized" and not _non_empty(self.path("biography")):
            problems.append("missing biography")

        structures = list(provenance["structures"])
        for slug in structures:
            if not _non_empty(self.structure_reading(str(slug))):
                problems.append(f"missing structure reading: {slug}")

        fabrication_payload = self._load_fabrication_payload()
        if fabrication_payload is None:
            problems.append("missing fabrication report")
        elif fabrication_payload is _INVALID_FABRICATION_REPORT:
            problems.append("invalid fabrication report")
        elif not isinstance(fabrication_payload, dict):
            problems.append("invalid fabrication report")
        else:
            readings = fabrication_payload.get("readings", {})
            if not isinstance(readings, dict):
                problems.append("invalid fabrication report")
            else:
                reported_structures = set(readings)
                for slug in structures:
                    if slug not in reported_structures:
                        problems.append(f"fabrication report missing structure: {slug}")
                problems.extend(self._unresolved_fabrication_problems(fabrication_payload))

        return ValidationReport(ok=not problems, problems=problems)

    def assemble(self) -> Path:
        provenance = self.read_json("provenance")

        parts = ["# Dossier", ""]
        for part in _ordered_parts():
            if part.key == "structure_reading":
                parts.extend([f"## {part.heading}", ""])
                for slug in provenance["structures"]:
                    reading = self.read_text(part.key, slug=str(slug)).rstrip()
                    parts.extend([f"### {slug}", "", reading, ""])
                continue

            if part.key in {"fabrication_report", "critic"} and not self.path(part.key).exists():
                continue

            parts.extend([f"## {part.heading}", "", self.read_text(part.key).rstrip(), ""])

        return self.write_text("dossier", "\n".join(parts).rstrip() + "\n")

    def _load_fabrication_payload(self) -> object | None:
        if not _non_empty(self.path("fabrication_report_json")) or not _non_empty(self.path("fabrication_report")):
            return None
        try:
            return self.read_json("fabrication_report_json")
        except json.JSONDecodeError:
            return _INVALID_FABRICATION_REPORT

    def _unresolved_fabrication_problems(self, payload: dict[str, object]) -> list[str]:
        if not _non_empty(self.path("interpretation")):
            return []
        interpretation = _normalize_text(self.read_text("interpretation"))
        readings = payload.get("readings", {})
        if not isinstance(readings, dict):
            return ["invalid fabrication report"]

        problems = []
        for slug, report in readings.items():
            if not isinstance(report, dict):
                problems.append(f"invalid fabrication report for structure: {slug}")
                continue
            claims = report.get("unsupported_claims", [])
            if not isinstance(claims, list):
                problems.append(f"invalid fabrication claims for structure: {slug}")
                continue
            for claim in claims:
                if not isinstance(claim, dict):
                    continue
                text = str(claim.get("text", "")).strip()
                if text and _normalize_text(text) in interpretation:
                    problems.append(f"unresolved fabrication in interpretation: {slug}: {text}")
        return problems


def _part_for_key(key: str) -> ArtifactPart:
    try:
        return _PARTS_BY_KEY[key]
    except KeyError as error:
        raise KeyError(f"Unknown run artifact part: {key}") from error


def relative_path_for(key: str) -> str:
    part = _part_for_key(key)
    if part.family:
        raise ValueError(f"{key} requires a slug.")
    return part.path


def _ordered_parts() -> list[ArtifactPart]:
    return sorted((part for part in LAYOUT if part.order is not None), key=lambda part: part.order)


def _non_empty(path: Path) -> bool:
    return path.exists() and path.read_text(encoding="utf-8").strip() != ""


def _normalize_text(text: str) -> str:
    return " ".join(text.casefold().split())
