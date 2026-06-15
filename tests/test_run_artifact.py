import hashlib
import json
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
from natal_chart.run import (
    Provenance,
    RunSpec,
    assemble_dossier,
    compare_runs,
    init_run,
    validate_run,
    write_fabrication_report,
)


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


def _fabrication_chart_brief() -> ChartBrief:
    resolved = ResolvedBirth(
        input_date="1980-01-01",
        input_time="12:00",
        place="London",
        country_code="GB",
        latitude=51.5074,
        longitude=-0.1278,
        timezone="Europe/London",
        local_datetime="1980-01-01T12:00:00+00:00",
        utc_datetime="1980-01-01T12:00:00+00:00",
    )
    natal = LayerBrief(
        name="natal",
        julian_day_ut=2444239.0,
        bodies=[
            BodyPosition(name="Sun", longitude=280.0, sign="Capricorn", degree=10.0, house=10, speed=1.0),
            BodyPosition(name="Moon", longitude=340.0, sign="Pisces", degree=10.0, house=12, speed=12.0),
            BodyPosition(name="Mercury", longitude=260.0, sign="Sagittarius", degree=20.0, house=9, speed=0.92),
            BodyPosition(name="Pluto", longitude=197.0, sign="Libra", degree=17.0, house=7, speed=0.02),
            BodyPosition(name="Imum Coeli", longitude=180.0, sign="Libra", degree=0.0, house=4, speed=None),
        ],
        house_cusps=[HouseCusp(house=4, longitude=180.0, sign="Libra", degree=0.0)],
        aspects=[Aspect(body_a="Sun", body_b="Moon", aspect="sextile", angle=60.0, orb=0.0)],
        configurations=[],
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


def test_init_run_captures_complete_provenance_hashes_and_seed(tmp_path):
    charter_root = tmp_path / "charters"
    charter_root.mkdir()
    (charter_root / "ego.md").write_text("# Ego charter\nRead conscious standpoint.\n", encoding="utf-8")
    (charter_root / "shadow.md").write_text("# Shadow charter\nRead disowned material.\n", encoding="utf-8")
    spec = RunSpec(
        native="ada-lovelace",
        structures=["ego", "shadow"],
        selection=["natal", "transits"],
        models={"structure": "sonnet", "interpreter": "opus"},
        seed=4242,
    )
    brief = _sample_chart_brief()

    run_dir = init_run(
        spec,
        brief,
        runs_root=tmp_path,
        timestamp="2026-06-14T12:00:00Z",
        revision="abc123",
        charter_root=charter_root,
    )

    provenance = json.loads((run_dir / "provenance.json").read_text(encoding="utf-8"))
    chart_brief_bytes = (run_dir / "chart-brief.json").read_bytes()

    assert provenance["selection"] == ["natal", "transits"]
    assert provenance["run_mode"] == "blind"
    assert provenance["models"] == {"structure": "sonnet", "interpreter": "opus"}
    assert provenance["seed"] == 4242
    assert provenance["timestamp"] == "2026-06-14T12:00:00Z"
    assert provenance["chart_brief_sha256"] == hashlib.sha256(chart_brief_bytes).hexdigest()
    assert provenance["charter_sha256"] == {
        "ego": hashlib.sha256((charter_root / "ego.md").read_bytes()).hexdigest(),
        "shadow": hashlib.sha256((charter_root / "shadow.md").read_bytes()).hexdigest(),
    }


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


def test_contextualized_run_accepts_and_persists_biography(tmp_path):
    brief = _sample_chart_brief()

    contextualized = RunSpec(
        native="ada-lovelace",
        structures=["ego"],
        run_mode="contextualized",
        biography="Known collaborator, mathematician, and writer.",
    )
    run_dir = init_run(contextualized, brief, runs_root=tmp_path, timestamp="2026-06-14T12:00:00Z", revision="abc123")

    assert (run_dir / "biography.md").read_text(encoding="utf-8") == (
        "Known collaborator, mathematician, and writer.\n"
    )
    provenance = json.loads((run_dir / "provenance.json").read_text(encoding="utf-8"))
    assert provenance["run_mode"] == "contextualized"
    assert provenance["biography_path"] == "biography.md"

    blind = RunSpec(native="grace-hopper", structures=["ego"])
    blind_dir = init_run(blind, brief, runs_root=tmp_path, timestamp="2026-06-14T13:00:00Z", revision="abc123")

    assert not (blind_dir / "biography.md").exists()
    blind_provenance = json.loads((blind_dir / "provenance.json").read_text(encoding="utf-8"))
    assert blind_provenance["run_mode"] == "blind"
    assert blind_provenance["biography_path"] is None


def test_init_run_includes_qualitative_reflection_scaffold_without_scores(tmp_path):
    spec = RunSpec(native="ada-lovelace", structures=["ego"])
    brief = _sample_chart_brief()

    run_dir = init_run(spec, brief, runs_root=tmp_path, timestamp="2026-06-14T12:00:00Z", revision="abc123")

    reflection = (run_dir / "reflection.md").read_text(encoding="utf-8")
    assert "# Reflection" in reflection
    assert "What landed" in reflection
    assert "What felt generic or Barnum" in reflection
    assert "What surprised" in reflection
    assert "score" not in reflection.casefold()
    assert "rubric" not in reflection.casefold()
    assert "rating" not in reflection.casefold()


def test_assemble_dossier_composes_layered_dossier(tmp_path):
    spec = RunSpec(native="ada-lovelace", structures=["ego", "shadow"])
    brief = _sample_chart_brief()
    run_dir = init_run(spec, brief, runs_root=tmp_path, timestamp="2026-06-14T12:00:00Z", revision="abc123")

    # simulate the interpreter + structure agents writing their parts
    (run_dir / "interpretation.md").write_text("PORTRAIT: the individuation arc.\n", encoding="utf-8")
    (run_dir / "structure" / "ego.md").write_text("EGO reading.\n", encoding="utf-8")
    (run_dir / "structure" / "shadow.md").write_text("SHADOW reading.\n", encoding="utf-8")
    (run_dir / "critic.md").write_text("CRITIC: too vague, says the critic.\n", encoding="utf-8")

    dossier_path = assemble_dossier(run_dir)

    assert dossier_path == run_dir / "dossier.md"
    text = dossier_path.read_text()

    # layered order: portrait, then structure readings, then the critic's challenges, then the brief
    assert text.index("PORTRAIT: the individuation arc.") < text.index("EGO reading.")
    assert text.index("EGO reading.") < text.index("SHADOW reading.")
    assert text.index("SHADOW reading.") < text.index("CRITIC: too vague, says the critic.")
    assert text.index("CRITIC: too vague, says the critic.") < text.index("# Natal Chart Brief")
    # the chart brief is included verbatim at the bottom
    assert brief.to_markdown() in text


def test_write_fabrication_report_checks_each_structure_reading(tmp_path):
    spec = RunSpec(native="ada-lovelace", structures=["ego", "shadow"])
    brief = _fabrication_chart_brief()
    run_dir = init_run(spec, brief, runs_root=tmp_path, timestamp="2026-06-14T12:00:00Z", revision="abc123")
    (run_dir / "structure" / "ego.md").write_text("Ego rests on Sun sextile Moon.\n", encoding="utf-8")
    (run_dir / "structure" / "shadow.md").write_text(
        "Shadow claims Pluto conjunct the IC and stationary Mercury.\n",
        encoding="utf-8",
    )

    report = write_fabrication_report(run_dir)

    payload = json.loads((run_dir / "fabrication-report.json").read_text(encoding="utf-8"))
    markdown = (run_dir / "fabrication-report.md").read_text(encoding="utf-8")
    assert report.total_unsupported_count == 2
    assert payload["total_unsupported_count"] == 2
    assert payload["readings"]["ego"]["unsupported_count"] == 0
    assert payload["readings"]["shadow"]["unsupported_count"] == 2
    assert "Claims to drop before synthesis" in markdown
    assert "Pluto conjunct the IC" in markdown
    assert "stationary Mercury" in markdown

    (run_dir / "interpretation.md").write_text("portrait drops the false specifics\n", encoding="utf-8")
    (run_dir / "critic.md").write_text("critic receives the guard report\n", encoding="utf-8")
    dossier = assemble_dossier(run_dir).read_text(encoding="utf-8")
    assert "## Fabrication Guard" in dossier
    assert dossier.index("## Fabrication Guard") < dossier.index("## Critic Challenges")


def test_write_fabrication_report_reads_chart_brief_json_not_markdown(tmp_path):
    spec = RunSpec(native="ada-lovelace", structures=["shadow"])
    brief = _fabrication_chart_brief()
    run_dir = init_run(spec, brief, runs_root=tmp_path, timestamp="2026-06-14T12:00:00Z", revision="abc123")
    (run_dir / "structure" / "shadow.md").write_text(
        "Shadow claims Pluto conjunct the IC and stationary Mercury.\n",
        encoding="utf-8",
    )
    (run_dir / "chart-brief.md").write_text(
        """# Misleading Rendered Brief

## Natal Layer

### Bodies

| Body | Sign | Degree | House | Longitude | Speed |
| --- | --- | ---: | ---: | ---: | ---: |
| Mercury | Sagittarius | 20.0000 | 9 | 260.0000 | 0.0000 |
| Pluto | Libra | 17.0000 | 7 | 197.0000 | 0.0200 |
| Imum Coeli | Libra | 0.0000 | 4 | 180.0000 | |

### Aspects

| Body A | Aspect | Body B | Orb |
| --- | --- | --- | ---: |
| Pluto | conjunction | Imum Coeli | 0.0000 |
""",
        encoding="utf-8",
    )

    report = write_fabrication_report(run_dir)

    assert report.total_unsupported_count == 2


def test_write_fabrication_report_requires_chart_brief_json(tmp_path):
    spec = RunSpec(native="ada-lovelace", structures=["ego"])
    brief = _sample_chart_brief()
    run_dir = init_run(spec, brief, runs_root=tmp_path, timestamp="2026-06-14T12:00:00Z", revision="abc123")
    (run_dir / "structure" / "ego.md").write_text("Ego rests on Sun sextile Moon.\n", encoding="utf-8")
    (run_dir / "chart-brief.json").unlink()

    with pytest.raises(FileNotFoundError):
        write_fabrication_report(run_dir)


def test_write_fabrication_report_rejects_malformed_chart_brief_json(tmp_path):
    spec = RunSpec(native="ada-lovelace", structures=["ego"])
    brief = _sample_chart_brief()
    run_dir = init_run(spec, brief, runs_root=tmp_path, timestamp="2026-06-14T12:00:00Z", revision="abc123")
    (run_dir / "structure" / "ego.md").write_text("Ego rests on Sun sextile Moon.\n", encoding="utf-8")
    (run_dir / "chart-brief.json").write_text(json.dumps({"zodiac": "tropical"}) + "\n", encoding="utf-8")

    with pytest.raises((KeyError, TypeError)):
        write_fabrication_report(run_dir)


def test_validate_run_passes_complete_artifact(tmp_path):
    spec = RunSpec(native="ada-lovelace", structures=["ego", "shadow"])
    brief = _sample_chart_brief()
    run_dir = init_run(spec, brief, runs_root=tmp_path, timestamp="2026-06-14T12:00:00Z", revision="abc123")
    (run_dir / "interpretation.md").write_text("portrait\n", encoding="utf-8")
    (run_dir / "structure" / "ego.md").write_text("ego reading\n", encoding="utf-8")
    (run_dir / "structure" / "shadow.md").write_text("shadow reading\n", encoding="utf-8")
    write_fabrication_report(run_dir)
    (run_dir / "critic.md").write_text("critic challenges\n", encoding="utf-8")

    report = validate_run(run_dir)

    assert report.ok is True
    assert report.problems == []


def test_validate_run_requires_fabrication_report_for_complete_artifact(tmp_path):
    spec = RunSpec(native="ada-lovelace", structures=["ego"])
    brief = _sample_chart_brief()
    run_dir = init_run(spec, brief, runs_root=tmp_path, timestamp="2026-06-14T12:00:00Z", revision="abc123")
    (run_dir / "interpretation.md").write_text("portrait\n", encoding="utf-8")
    (run_dir / "structure" / "ego.md").write_text("ego reading\n", encoding="utf-8")
    (run_dir / "critic.md").write_text("critic challenges\n", encoding="utf-8")

    report = validate_run(run_dir)

    assert report.ok is False
    assert "missing fabrication report" in report.problems


def test_validate_run_reports_fabricated_claim_repeated_in_portrait(tmp_path):
    spec = RunSpec(native="ada-lovelace", structures=["shadow"])
    brief = _fabrication_chart_brief()
    run_dir = init_run(spec, brief, runs_root=tmp_path, timestamp="2026-06-14T12:00:00Z", revision="abc123")
    (run_dir / "structure" / "shadow.md").write_text(
        "Shadow claims Pluto conjunct the IC.\n",
        encoding="utf-8",
    )
    write_fabrication_report(run_dir)
    (run_dir / "critic.md").write_text(
        "Fabrication guard: drop Pluto conjunct the IC.\n",
        encoding="utf-8",
    )
    (run_dir / "interpretation.md").write_text(
        "The final portrait repeats Pluto conjunct the IC.\n",
        encoding="utf-8",
    )

    unresolved = validate_run(run_dir)

    assert unresolved.ok is False
    assert "unresolved fabrication in interpretation: shadow: Pluto conjunct the IC" in unresolved.problems

    (run_dir / "interpretation.md").write_text(
        "The final portrait keeps the root pressure image without the false specific.\n",
        encoding="utf-8",
    )

    resolved = validate_run(run_dir)

    assert resolved.ok is True
    assert resolved.problems == []


def test_validate_run_requires_critic_section_for_complete_artifact(tmp_path):
    spec = RunSpec(native="ada-lovelace", structures=["ego"])
    brief = _sample_chart_brief()
    run_dir = init_run(spec, brief, runs_root=tmp_path, timestamp="2026-06-14T12:00:00Z", revision="abc123")
    (run_dir / "interpretation.md").write_text("portrait\n", encoding="utf-8")
    (run_dir / "structure" / "ego.md").write_text("ego reading\n", encoding="utf-8")

    report = validate_run(run_dir)

    assert report.ok is False
    assert "missing critic" in report.problems


def test_validate_run_requires_reflection_scaffold_for_complete_artifact(tmp_path):
    spec = RunSpec(native="ada-lovelace", structures=["ego"])
    brief = _sample_chart_brief()
    run_dir = init_run(spec, brief, runs_root=tmp_path, timestamp="2026-06-14T12:00:00Z", revision="abc123")
    (run_dir / "interpretation.md").write_text("portrait\n", encoding="utf-8")
    (run_dir / "critic.md").write_text("critic challenges\n", encoding="utf-8")
    (run_dir / "structure" / "ego.md").write_text("ego reading\n", encoding="utf-8")
    (run_dir / "reflection.md").unlink()

    report = validate_run(run_dir)

    assert report.ok is False
    assert "missing reflection" in report.problems


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


def test_validate_run_requires_the_critic_pass(tmp_path):
    spec = RunSpec(native="ada-lovelace", structures=["ego", "shadow"])
    brief = _sample_chart_brief()
    run_dir = init_run(spec, brief, runs_root=tmp_path, timestamp="2026-06-14T12:00:00Z", revision="abc123")
    (run_dir / "interpretation.md").write_text("portrait\n", encoding="utf-8")
    (run_dir / "structure" / "ego.md").write_text("ego reading\n", encoding="utf-8")
    (run_dir / "structure" / "shadow.md").write_text("shadow reading\n", encoding="utf-8")
    # everything present except the depth-critic's pass

    report = validate_run(run_dir)

    assert report.ok is False
    assert any("critic" in problem for problem in report.problems)


def test_compare_runs_writes_side_by_side_markdown_for_same_native(tmp_path):
    brief = _sample_chart_brief()
    blind_dir = init_run(
        RunSpec(native="ada-lovelace", structures=["ego"], run_mode="blind", seed=1),
        brief,
        runs_root=tmp_path,
        timestamp="2026-06-14T12:00:00Z",
        revision="abc123",
    )
    contextualized_dir = init_run(
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
    for run_dir, portrait in ((blind_dir, "Blind portrait"), (contextualized_dir, "Contextualized portrait")):
        (run_dir / "interpretation.md").write_text(f"{portrait}\n", encoding="utf-8")
        (run_dir / "critic.md").write_text("critic challenges\n", encoding="utf-8")
        (run_dir / "structure" / "ego.md").write_text("ego reading\n", encoding="utf-8")
        assemble_dossier(run_dir)

    comparison_path = compare_runs(blind_dir, contextualized_dir)

    assert comparison_path == tmp_path / "ada-lovelace-comparison.md"
    comparison = comparison_path.read_text(encoding="utf-8")
    assert "# Run Comparison: ada-lovelace" in comparison
    assert "| Field | ada-lovelace-2026-06-14T120000Z | ada-lovelace-2026-06-14T130000Z |" in comparison
    assert "| Run mode | blind | contextualized |" in comparison
    assert "| Seed | 1 | 2 |" in comparison
    assert "Blind portrait" in comparison
    assert "Contextualized portrait" in comparison


def test_agents_brief_documents_fabrication_guard_step():
    brief = Path("AGENTS.md").read_text(encoding="utf-8")

    assert "fabrication-report.md" in brief
    assert "claims to drop" in brief
    assert "validate_run" in brief
