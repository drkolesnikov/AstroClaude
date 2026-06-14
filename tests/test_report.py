import json
import math
import tomllib
import textwrap
from pathlib import Path

import natal_chart.report as report_module
from natal_chart.models import (
    Aspect,
    BodyPosition,
    ChartBrief,
    Configuration,
    HouseCusp,
    LayerBrief,
    ResolvedBirth,
)
from natal_chart.report import render_report
from natal_chart.run import RunSpec, init_run, write_fabrication_report


STRUCTURES = [
    "ego",
    "persona",
    "shadow",
    "anima-animus",
    "parental",
    "wound",
    "vocation",
    "eros",
    "numinous",
]


def _report_brief() -> ChartBrief:
    resolved = ResolvedBirth(
        input_date="1906-12-09",
        input_time="18:30",
        place="New York",
        country_code="US",
        latitude=40.7128,
        longitude=-74.0060,
        timezone="America/New_York",
        local_datetime="1906-12-09T18:30:00-05:00",
        utc_datetime="1906-12-09T23:30:00+00:00",
    )
    natal = LayerBrief(
        name="natal",
        julian_day_ut=2417564.4792,
        bodies=[
            BodyPosition(name="Sun", longitude=257.5, sign="Sagittarius", degree=17.5, house=6, speed=1.0),
            BodyPosition(name="Moon", longitude=184.2, sign="Libra", degree=4.2, house=3, speed=12.1),
            BodyPosition(name="Ascendant", longitude=122.0, sign="Leo", degree=2.0, house=1, speed=None),
            BodyPosition(name="Midheaven", longitude=28.0, sign="Aries", degree=28.0, house=10, speed=None),
            BodyPosition(name="Mercury", longitude=260.0, sign="Sagittarius", degree=20.0, house=6, speed=0.8),
            BodyPosition(name="Saturn", longitude=264.0, sign="Sagittarius", degree=24.0, house=6, speed=-0.05),
        ],
        house_cusps=[
            HouseCusp(house=1, longitude=122.0, sign="Leo", degree=2.0),
            HouseCusp(house=10, longitude=28.0, sign="Aries", degree=28.0),
        ],
        aspects=[
            Aspect(body_a="Sun", body_b="Moon", aspect="sextile", angle=60.0, orb=1.1),
            Aspect(body_a="Mercury", body_b="Saturn", aspect="conjunction", angle=0.0, orb=4.0),
        ],
        configurations=[
            Configuration(type="stellium", bodies=["Sun", "Mercury", "Saturn"], details={"sign": "Sagittarius"})
        ],
    )
    return ChartBrief(zodiac="tropical", house_system="Placidus", resolved_birth=resolved, layers=[natal])


def _complete_run(tmp_path):
    spec = RunSpec(
        native="grace-hopper",
        structures=STRUCTURES,
        selection=["natal"],
        run_mode="blind",
        models={"structure": "sonnet", "interpreter": "opus"},
        seed=1944,
    )
    run_dir = init_run(
        spec,
        _report_brief(),
        runs_root=tmp_path,
        timestamp="2026-06-15T08:00:00Z",
        revision="abc123",
    )
    (run_dir / "interpretation.md").write_text(
        textwrap.dedent(
            """
        # Individuation Portrait

        **Grace** reads the field through *precision*.

        1. First falsifiable hypothesis.
        2. Second falsifiable hypothesis.

        - A bullet thread.
        - Another bullet thread.

        > A quoted challenge.

        ---

        | Thread | Evidence |
        | --- | --- |
        | vocation | Sun in Sagittarius |
        """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    for slug in STRUCTURES:
        (run_dir / "structure" / f"{slug}.md").write_text(
            f"# {slug.title()} Reading\n\nThis is the {slug} page.\n",
            encoding="utf-8",
        )
    write_fabrication_report(run_dir)
    (run_dir / "critic.md").write_text("# Depth Critic\n\nNo fabricated claims survive.\n", encoding="utf-8")
    return run_dir


def test_render_report_writes_navigable_html_from_run_artifacts(tmp_path):
    run_dir = _complete_run(tmp_path)

    report_path = render_report(run_dir)

    assert report_path == run_dir / "report" / "index.html"
    html = report_path.read_text(encoding="utf-8")
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["scripts"]["render_report"] == "natal_chart.report_cli:main"
    assert any(requirement.startswith("markdown") for requirement in pyproject["project"]["dependencies"])

    assert "Grace Hopper" in html
    assert "John D" not in html
    assert "New York, US" in html
    assert "1906-12-09T18:30:00-05:00" in html
    assert "1906-12-09T23:30:00+00:00" in html
    assert "40.7128, -74.006" in html
    assert "America/New_York" in html
    assert "GH" in html
    assert "blind" in html
    assert "natal" in html
    assert "sonnet" in html
    assert "opus" in html
    assert "1944" in html
    assert "abc123" in html

    for page_id in ["portrait", *STRUCTURES, "critic", "chart"]:
        assert f'id="page-{page_id}"' in html
        assert f'data-target="{page_id}"' in html

    assert "Sun: Sagittarius, house 6" in html
    assert "Moon: Libra, house 3" in html
    assert "Ascendant: Leo, house 1" in html
    assert "Midheaven: Aries, house 10" in html
    assert "stellium: Sun, Mercury, Saturn" in html

    assert "<strong>Grace</strong>" in html
    assert "<em>precision</em>" in html
    assert "<ol>" in html
    assert "<ul>" in html
    assert "<blockquote>" in html
    assert "<hr" in html
    assert "<table>" in html
    assert "<th>Thread</th>" in html
    assert "<td>vocation</td>" in html

    assert "class=\"sidebar\"" in html
    assert "class=\"pager\"" in html
    assert "function showPage" in html
    assert "@media (max-width: 760px)" in html

    chart_json = json.loads((run_dir / "chart-brief.json").read_text(encoding="utf-8"))
    for body in chart_json["layers"][0]["bodies"]:
        assert f"<td>{body['name']}</td>" in html


def test_chart_wheel_geometry_orients_ascendant_left_and_midheaven_top():
    geometry = report_module.chart_wheel_geometry(_report_brief().to_dict())

    center = geometry["center"]
    ascendant = geometry["angles"]["Ascendant"]
    midheaven = geometry["angles"]["Midheaven"]

    assert ascendant["screen_angle"] == 180
    assert ascendant["x"] < center["x"] - 130
    assert abs(ascendant["y"] - center["y"]) < 1
    assert 270 <= midheaven["screen_angle"] <= 278
    assert midheaven["y"] < center["y"] - 130
    assert abs(midheaven["x"] - center["x"]) < 20


def test_chart_wheel_geometry_declusters_stellium_glyphs_without_moving_true_angles():
    geometry = report_module.chart_wheel_geometry(_report_brief().to_dict())
    bodies = {body["name"]: body for body in geometry["bodies"]}
    stellium = [bodies[name] for name in ("Sun", "Mercury", "Saturn")]

    for body in stellium:
        assert math.isclose(
            body["screen_angle"],
            (geometry["ascendant_longitude"] + 180 - body["longitude"]) % 360,
            abs_tol=0.001,
        )
        assert body["connector"], f"{body['name']} should keep a connector to its exact tick"

    for index, body in enumerate(stellium):
        for other in stellium[index + 1 :]:
            distance = math.dist((body["glyph_x"], body["glyph_y"]), (other["glyph_x"], other["glyph_y"]))
            assert distance >= 26, f"{body['name']} and {other['name']} glyphs collide"


def test_render_report_includes_scaling_monochrome_chart_wheel(tmp_path):
    run_dir = _complete_run(tmp_path)

    html = render_report(run_dir).read_text(encoding="utf-8")

    assert 'class="chart-wheel-frame"' in html
    assert 'class="wheel-svg"' in html
    assert 'viewBox="0 0 640 640"' in html
    assert 'class="sign-sector sign-fire"' in html
    assert 'class="house-cusp"' in html
    assert 'class="angle-axis angle-asc"' in html
    assert 'class="aspect-line aspect-sextile"' in html
    assert 'class="body-tick"' in html
    assert 'class="glyph-overlay planet-symbol"' in html
    assert 'class="glyph-overlay sign-symbol"' in html
    assert "font-variant-emoji: text" in html
    assert "☉\ufe0e" in html
    assert "☽\ufe0e" in html
    assert "♄\ufe0e" in html
    assert "♈\ufe0e" in html
    assert 'data-body="Sun"' in html
    assert "R" in html
    assert "@media (max-width: 760px)" in html
    assert "aspect-ratio: 1 / 1" in html
