import json

from natal_chart.models import (
    Aspect,
    BodyPosition,
    ChartBrief,
    Configuration,
    HouseCusp,
    LayerBrief,
    ResolvedBirth,
)
from natal_chart.run import Provenance, RunSpec, assemble_dossier, init_run, validate_run


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


def test_provenance_captures_run_config():
    spec = RunSpec(
        native="ada-lovelace",
        structures=["ego", "persona", "shadow", "anima-animus"],
        models={"structure": "sonnet", "interpreter": "opus"},
    )

    prov = Provenance.from_spec(spec, revision="abc123", timestamp="2026-06-14T12:00:00Z")
    data = prov.to_dict()

    assert data["native"] == "ada-lovelace"
    assert data["selection"] == ["natal"]  # default
    assert data["run_mode"] == "blind"  # default (ADR-0004)
    assert data["structures"] == ["ego", "persona", "shadow", "anima-animus"]
    assert data["models"] == {"structure": "sonnet", "interpreter": "opus"}
    assert data["revision"] == "abc123"
    assert data["timestamp"] == "2026-06-14T12:00:00Z"
    assert json.loads(json.dumps(data)) == data  # JSON round-trip


def test_init_run_lays_down_provenance_and_chart_brief(tmp_path):
    spec = RunSpec(native="ada-lovelace", structures=["ego", "shadow"])
    brief = _sample_chart_brief()

    run_dir = init_run(
        spec,
        brief,
        runs_root=tmp_path,
        timestamp="2026-06-14T12:00:00Z",
        revision="abc123",
    )

    # run directory is namespaced by native + a filesystem-safe timestamp
    assert run_dir.parent == tmp_path
    assert run_dir.name == "ada-lovelace-2026-06-14T120000Z"

    # provenance written and parseable
    prov = json.loads((run_dir / "provenance.json").read_text())
    assert prov["native"] == "ada-lovelace"
    assert prov["revision"] == "abc123"
    assert prov["structures"] == ["ego", "shadow"]

    # chart brief written in both forms; markdown matches the brief's own rendering
    assert json.loads((run_dir / "chart-brief.json").read_text()) == brief.to_dict()
    assert (run_dir / "chart-brief.md").read_text() == brief.to_markdown()

    # empty structure/ dir ready for the agents to write into
    assert (run_dir / "structure").is_dir()


def test_assemble_dossier_composes_layered_dossier(tmp_path):
    spec = RunSpec(native="ada-lovelace", structures=["ego", "shadow"])
    brief = _sample_chart_brief()
    run_dir = init_run(spec, brief, runs_root=tmp_path, timestamp="2026-06-14T12:00:00Z", revision="abc123")

    # simulate the interpreter + structure agents writing their parts
    (run_dir / "interpretation.md").write_text("PORTRAIT: the individuation arc.\n", encoding="utf-8")
    (run_dir / "structure" / "ego.md").write_text("EGO reading.\n", encoding="utf-8")
    (run_dir / "structure" / "shadow.md").write_text("SHADOW reading.\n", encoding="utf-8")

    dossier_path = assemble_dossier(run_dir)

    assert dossier_path == run_dir / "dossier.md"
    text = dossier_path.read_text()

    # layered order: portrait first, then structure readings (in provenance order), then chart brief
    assert text.index("PORTRAIT: the individuation arc.") < text.index("EGO reading.")
    assert text.index("EGO reading.") < text.index("SHADOW reading.")
    assert text.index("SHADOW reading.") < text.index("# Natal Chart Brief")
    # the chart brief is included verbatim at the bottom
    assert brief.to_markdown() in text


def test_validate_run_passes_complete_artifact(tmp_path):
    spec = RunSpec(native="ada-lovelace", structures=["ego", "shadow"])
    brief = _sample_chart_brief()
    run_dir = init_run(spec, brief, runs_root=tmp_path, timestamp="2026-06-14T12:00:00Z", revision="abc123")
    (run_dir / "interpretation.md").write_text("portrait\n", encoding="utf-8")
    (run_dir / "structure" / "ego.md").write_text("ego reading\n", encoding="utf-8")
    (run_dir / "structure" / "shadow.md").write_text("shadow reading\n", encoding="utf-8")

    report = validate_run(run_dir)

    assert report.ok is True
    assert report.problems == []


def test_validate_run_flags_incomplete_artifact(tmp_path):
    spec = RunSpec(native="ada-lovelace", structures=["ego", "shadow"])
    brief = _sample_chart_brief()
    run_dir = init_run(spec, brief, runs_root=tmp_path, timestamp="2026-06-14T12:00:00Z", revision="abc123")
    # only one of two active structure readings; no interpretation written
    (run_dir / "structure" / "ego.md").write_text("ego reading\n", encoding="utf-8")

    report = validate_run(run_dir)

    assert report.ok is False
    joined = " ".join(report.problems)
    assert "interpretation" in joined  # missing portrait flagged
    assert "shadow" in joined  # missing structure reading flagged by name
