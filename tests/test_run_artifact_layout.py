from pathlib import Path

import pytest

from natal_chart.models import (
    Aspect,
    BodyPosition,
    ChartBrief,
    Configuration,
    HouseCusp,
    LayerBrief,
    ResolvedBirth,
)
from natal_chart.retrieve import write_agent_grounding, write_amplification_grounding
from natal_chart.run import (
    RunSpec,
    assemble_dossier,
    compare_runs,
    init_run,
    validate_run,
    write_fabrication_report,
)
from natal_chart.run_artifact import ArtifactPart, LAYOUT, RunArtifact


def _sample_chart_brief() -> ChartBrief:
    resolved = ResolvedBirth(
        input_date="1990-01-01",
        input_time="12:00",
        place="Moscow",
        country_code="RU",
        latitude=55.7558,
        longitude=37.6173,
        timezone="Europe/Moscow",
        local_datetime="1990-01-01T12:00:00+03:00",
        utc_datetime="1990-01-01T09:00:00+00:00",
    )
    natal = LayerBrief(
        name="natal",
        julian_day_ut=2447892.875,
        bodies=[
            BodyPosition(name="Sun", longitude=280.0, sign="Capricorn", degree=10.0, house=10, speed=1.0),
            BodyPosition(name="Moon", longitude=340.0, sign="Pisces", degree=10.0, house=12, speed=12.0),
        ],
        house_cusps=[HouseCusp(house=1, longitude=10.0, sign="Aries", degree=10.0)],
        aspects=[Aspect(body_a="Sun", body_b="Moon", aspect="sextile", angle=60.0, orb=0.0)],
        configurations=[
            Configuration(type="stellium", bodies=["Sun", "Mercury", "Saturn"], details={"sign": "Capricorn"})
        ],
    )
    return ChartBrief(zodiac="tropical", house_system="Placidus", resolved_birth=resolved, layers=[natal])


def _part_path(part: ArtifactPart) -> str:
    path = getattr(part, "path", getattr(part, "relative_path", None))
    assert path is not None, "ArtifactPart must expose a path or relative_path"
    return str(path)


def _layout_by_path() -> dict[str, ArtifactPart]:
    return {_part_path(part): part for part in LAYOUT}


def _key_for(relative_path: str) -> str:
    return _layout_by_path()[relative_path].key


def _scaffold_artifact(
    runs_root: Path,
    *,
    structures: tuple[str, ...] = ("ego", "shadow"),
    run_mode: str = "blind",
) -> RunArtifact:
    spec = RunSpec(
        native="ada-lovelace",
        structures=list(structures),
        run_mode=run_mode,
        biography="Known mathematician and collaborator." if run_mode == "contextualized" else None,
    )
    return RunArtifact.scaffold(
        runs_root=runs_root,
        spec=spec,
        brief=_sample_chart_brief(),
        timestamp="2026-06-14T12:00:00Z",
        revision="abc123",
    )


def _write_complete_parts(artifact: RunArtifact, structures: tuple[str, ...] = ("ego", "shadow")) -> None:
    artifact.write_text(_key_for("interpretation.md"), "PORTRAIT: complete.\n")
    artifact.write_text(_key_for("critic.md"), "CRITIC: complete.\n")
    for slug in structures:
        artifact.write_text(_key_for("structure/{slug}.md"), f"{slug.upper()} reading.\n", slug=slug)
    artifact.write_json(
        _key_for("fabrication-report.json"),
        {
            "total_unsupported_count": 0,
            "readings": {
                slug: {"unsupported_count": 0, "unsupported_claims": []}
                for slug in structures
            },
        },
    )
    artifact.write_text(
        _key_for("fabrication-report.md"),
        "# Fabrication Report\n\n"
        "- Unsupported claim count: 0\n\n"
        "## Claims to drop before synthesis\n\n"
        "- None detected\n",
    )


def _complete_artifact(
    runs_root: Path,
    *,
    structures: tuple[str, ...] = ("ego", "shadow"),
    run_mode: str = "blind",
) -> RunArtifact:
    artifact = _scaffold_artifact(runs_root, structures=structures, run_mode=run_mode)
    _write_complete_parts(artifact, structures)
    return artifact


def test_layout_table_enumerates_current_run_directory_contract():
    parts = list(LAYOUT)
    paths = [_part_path(part) for part in parts]
    by_path = _layout_by_path()

    assert all(isinstance(part, ArtifactPart) for part in parts)
    assert len(paths) == len(set(paths))
    assert set(paths) == {
        "provenance.json",
        "chart-brief.json",
        "chart-brief.md",
        "reflection.md",
        "biography.md",
        "structure/{slug}.md",
        "grounding/{slug}.md",
        "grounding/amplification.md",
        "critic.md",
        "interpretation.md",
        "fabrication-report.json",
        "fabrication-report.md",
        "dossier.md",
    }

    assert {path for path, part in by_path.items() if part.family} == {
        "structure/{slug}.md",
        "grounding/{slug}.md",
    }
    assert by_path["structure/{slug}.md"].required is True
    assert by_path["grounding/{slug}.md"].required is False
    assert by_path["dossier.md"].required is False

    ordered = [
        (_part_path(part), part.heading)
        for part in sorted((part for part in parts if part.order is not None), key=lambda part: part.order)
    ]
    assert ordered == [
        ("interpretation.md", "Individuation Portrait"),
        ("structure/{slug}.md", "Structure Readings"),
        ("fabrication-report.md", "Fabrication Guard"),
        ("critic.md", "Critic Challenges"),
        ("chart-brief.md", "Chart Brief"),
        ("reflection.md", "Reflection"),
    ]


def test_scaffold_lays_down_deterministic_parts_and_is_reconstructible(tmp_path):
    brief = _sample_chart_brief()
    artifact = RunArtifact.scaffold(
        runs_root=tmp_path,
        spec=RunSpec(native="ada-lovelace", structures=["ego", "shadow"]),
        brief=brief,
        timestamp="2026-06-14T12:00:00Z",
        revision="abc123",
    )

    assert isinstance(artifact, RunArtifact)
    assert artifact.run_dir == tmp_path / "ada-lovelace-2026-06-14T120000Z"
    assert artifact.path(_key_for("provenance.json")).exists()
    assert artifact.path(_key_for("chart-brief.json")).exists()
    assert artifact.path(_key_for("chart-brief.md")).exists()
    assert artifact.path(_key_for("reflection.md")).exists()
    assert artifact.path(_key_for("structure/{slug}.md"), slug="ego").parent.is_dir()
    assert not artifact.path(_key_for("biography.md")).exists()

    reconstructed = RunArtifact(artifact.run_dir)
    assert reconstructed.read_json(_key_for("provenance.json"))["structures"] == ["ego", "shadow"]
    assert reconstructed.read_json(_key_for("chart-brief.json")) == brief.to_dict()
    assert reconstructed.read_text(_key_for("chart-brief.md")) == brief.to_markdown()


def test_init_run_facade_keeps_signature_return_and_reconstructible_artifact(tmp_path):
    run_dir = init_run(
        RunSpec(native="ada-lovelace", structures=["ego"]),
        _sample_chart_brief(),
        runs_root=tmp_path,
        timestamp="2026-06-14T12:00:00Z",
        revision="abc123",
    )

    artifact = RunArtifact(run_dir)

    assert isinstance(run_dir, Path)
    assert run_dir == tmp_path / "ada-lovelace-2026-06-14T120000Z"
    assert artifact.read_json(_key_for("provenance.json"))["native"] == "ada-lovelace"


def test_path_accessors_resolve_singletons_and_families(tmp_path):
    run_dir = tmp_path / "run"
    artifact = RunArtifact(run_dir)

    assert artifact.path(_key_for("provenance.json")) == run_dir / "provenance.json"
    assert artifact.dossier_path == run_dir / "dossier.md"
    assert artifact.structure_reading("ego") == run_dir / "structure" / "ego.md"
    assert artifact.grounding_path("shadow") == run_dir / "grounding" / "shadow.md"
    assert artifact.path(_key_for("grounding/amplification.md")) == run_dir / "grounding" / "amplification.md"

    with pytest.raises((TypeError, ValueError)):
        artifact.path(_key_for("structure/{slug}.md"))
    with pytest.raises((TypeError, ValueError)):
        artifact.path(_key_for("provenance.json"), slug="ego")


def test_typed_read_write_helpers_create_parent_dirs_for_each_part(tmp_path):
    artifact = RunArtifact(tmp_path / "run")

    artifact.write_json(
        _key_for("provenance.json"),
        {"native": "ada-lovelace", "structures": ["ego"], "run_mode": "blind"},
    )
    artifact.write_text(_key_for("structure/{slug}.md"), "EGO reading.\n", slug="ego")
    artifact.write_text(_key_for("grounding/{slug}.md"), "EGO grounding.\n", slug="ego")
    artifact.write_text(_key_for("interpretation.md"), "PORTRAIT.\n")

    assert artifact.read_json(_key_for("provenance.json"))["structures"] == ["ego"]
    assert artifact.read_text(_key_for("structure/{slug}.md"), slug="ego") == "EGO reading.\n"
    assert artifact.read_text(_key_for("grounding/{slug}.md"), slug="ego") == "EGO grounding.\n"
    assert artifact.read_text(_key_for("interpretation.md")) == "PORTRAIT.\n"


def test_validate_accepts_complete_artifact_and_facade_reports_same_result(tmp_path):
    artifact = _complete_artifact(tmp_path)

    report = RunArtifact(artifact.run_dir).validate()

    assert report.ok is True
    assert report.problems == []
    assert validate_run(artifact.run_dir) == report
    assert not artifact.dossier_path.exists(), "dossier.md is assembled output, not a pre-assembly requirement"


def test_validate_reports_missing_or_empty_provenance(tmp_path):
    for mode in ("missing", "empty"):
        artifact = _complete_artifact(tmp_path / mode)
        provenance = artifact.path(_key_for("provenance.json"))
        if mode == "missing":
            provenance.unlink()
        else:
            provenance.write_text("", encoding="utf-8")

        report = artifact.validate()

        assert report.ok is False
        assert report.problems == ["missing provenance.json"]


@pytest.mark.parametrize(
    ("relative_path", "expected_problem"),
    [
        ("chart-brief.json", "missing chart brief json"),
        ("chart-brief.md", "missing chart brief"),
        ("interpretation.md", "missing interpretation"),
        ("critic.md", "missing critic"),
        ("reflection.md", "missing reflection"),
        ("fabrication-report.json", "missing fabrication report"),
        ("fabrication-report.md", "missing fabrication report"),
    ],
)
@pytest.mark.parametrize("mode", ["missing", "empty"])
def test_validate_reports_missing_or_empty_required_singletons(tmp_path, relative_path, expected_problem, mode):
    artifact = _complete_artifact(tmp_path)
    target = artifact.path(_key_for(relative_path))
    if mode == "missing":
        target.unlink()
    else:
        target.write_text("", encoding="utf-8")

    report = artifact.validate()

    assert report.ok is False
    assert expected_problem in report.problems


@pytest.mark.parametrize("mode", ["missing", "empty"])
def test_validate_expands_required_structure_family_over_provenance_roster(tmp_path, mode):
    artifact = _complete_artifact(tmp_path)
    shadow = artifact.structure_reading("shadow")
    if mode == "missing":
        shadow.unlink()
    else:
        shadow.write_text("", encoding="utf-8")

    report = artifact.validate()

    assert report.ok is False
    assert "missing structure reading: shadow" in report.problems
    assert all("missing structure reading: ego" not in problem for problem in report.problems)


def test_validate_reports_fabrication_payload_missing_roster_member(tmp_path):
    artifact = _complete_artifact(tmp_path)
    artifact.write_json(
        _key_for("fabrication-report.json"),
        {
            "total_unsupported_count": 0,
            "readings": {"ego": {"unsupported_count": 0, "unsupported_claims": []}},
        },
    )

    report = artifact.validate()

    assert report.ok is False
    assert "fabrication report missing structure: shadow" in report.problems


def test_validate_requires_biography_only_for_contextualized_runs(tmp_path):
    blind = _complete_artifact(tmp_path / "blind")
    contextualized = _complete_artifact(tmp_path / "contextualized", run_mode="contextualized")

    assert blind.validate().ok is True
    assert not blind.path(_key_for("biography.md")).exists()

    contextualized.path(_key_for("biography.md")).unlink()
    report = contextualized.validate()

    assert report.ok is False
    assert "missing biography" in report.problems


def test_assemble_composes_dossier_from_declared_order_and_headings(tmp_path):
    artifact = _complete_artifact(tmp_path)
    artifact.write_text(_key_for("interpretation.md"), "PORTRAIT: the individuation arc.\n")
    artifact.write_text(_key_for("structure/{slug}.md"), "EGO reading.\n", slug="ego")
    artifact.write_text(_key_for("structure/{slug}.md"), "SHADOW reading.\n", slug="shadow")
    artifact.write_text(_key_for("critic.md"), "CRITIC: too vague, says the critic.\n")
    artifact.write_text(_key_for("reflection.md"), "# Reflection\n\nCustom reflection.\n")

    dossier_path = artifact.assemble()

    fabrication = artifact.read_text(_key_for("fabrication-report.md")).rstrip()
    chart_brief = artifact.read_text(_key_for("chart-brief.md")).rstrip()
    expected = "\n".join(
        [
            "# Dossier",
            "",
            "## Individuation Portrait",
            "",
            "PORTRAIT: the individuation arc.",
            "",
            "## Structure Readings",
            "",
            "### ego",
            "",
            "EGO reading.",
            "",
            "### shadow",
            "",
            "SHADOW reading.",
            "",
            "## Fabrication Guard",
            "",
            fabrication,
            "",
            "## Critic Challenges",
            "",
            "CRITIC: too vague, says the critic.",
            "",
            "## Chart Brief",
            "",
            chart_brief,
            "",
            "## Reflection",
            "",
            "# Reflection\n\nCustom reflection.",
            "",
        ]
    ).rstrip() + "\n"

    assert dossier_path == artifact.dossier_path
    assert dossier_path.read_text(encoding="utf-8") == expected
    assert assemble_dossier(artifact.run_dir).read_text(encoding="utf-8") == expected


def test_fabrication_and_compare_facades_preserve_behavior_on_runartifact_paths(tmp_path):
    brief = _sample_chart_brief()
    left = init_run(
        RunSpec(native="ada-lovelace", structures=["ego"], run_mode="blind", seed=1),
        brief,
        runs_root=tmp_path,
        timestamp="2026-06-14T12:00:00Z",
        revision="abc123",
    )
    right = init_run(
        RunSpec(
            native="ada-lovelace",
            structures=["ego"],
            run_mode="contextualized",
            biography="Known mathematician.",
            seed=2,
        ),
        brief,
        runs_root=tmp_path,
        timestamp="2026-06-14T13:00:00Z",
        revision="def456",
    )
    for run_dir, portrait in ((left, "Blind portrait"), (right, "Contextualized portrait")):
        artifact = RunArtifact(run_dir)
        artifact.write_text(_key_for("structure/{slug}.md"), "Ego rests on Sun sextile Moon.\n", slug="ego")
        report = write_fabrication_report(run_dir)
        artifact.write_text(_key_for("interpretation.md"), f"{portrait}\n")
        artifact.write_text(_key_for("critic.md"), "critic challenges\n")
        artifact.assemble()
        assert report.total_unsupported_count == 0
        assert artifact.path(_key_for("fabrication-report.json")).exists()
        assert artifact.path(_key_for("fabrication-report.md")).exists()

    comparison_path = compare_runs(left, right)

    assert comparison_path == tmp_path / "ada-lovelace-comparison.md"
    comparison = comparison_path.read_text(encoding="utf-8")
    assert "| Run mode | blind | contextualized |" in comparison
    assert "Blind portrait" in comparison
    assert "Contextualized portrait" in comparison


def test_retrieve_grounding_writers_land_on_runartifact_owned_paths(tmp_path):
    run_dir = tmp_path / "run"
    charter_root = tmp_path / "agents"
    run_dir.mkdir()
    charter_root.mkdir()
    (run_dir / "chart-brief.md").write_text("Moon opposite Saturn.\n", encoding="utf-8")
    (charter_root / "ego.md").write_text("# Ego\nRead conscious standpoint.\n", encoding="utf-8")
    artifact = RunArtifact(run_dir)

    write_agent_grounding(
        run_dir=run_dir,
        index_dir=tmp_path / "missing-index",
        charter_root=charter_root,
        structures=["ego"],
        key_images=["Moon opposite Saturn"],
    )
    write_amplification_grounding(
        run_dir=run_dir,
        index_dir=tmp_path / "missing-index",
        key_images=["Moon opposite Saturn"],
    )

    assert artifact.grounding_path("ego").read_text(encoding="utf-8").startswith("# Grounding: ego")
    assert artifact.path(_key_for("grounding/amplification.md")).read_text(encoding="utf-8").startswith(
        "# Grounding: amplification"
    )


def test_agents_brief_keeps_literal_paths_and_no_new_domain_vocabulary():
    brief = Path("AGENTS.md").read_text(encoding="utf-8")

    assert "runs/<run>/structure/<slug>.md" in brief
    assert "runs/<run>/grounding/<slug>.md" in brief
    assert "grounding/amplification.md" in brief
    assert "RunArtifact" not in brief
    assert "run_artifact" not in brief
