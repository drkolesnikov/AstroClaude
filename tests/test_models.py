from __future__ import annotations

import ast
from pathlib import Path

import natal_chart.models as models
from natal_chart.models import (
    Aspect,
    BodyPosition,
    ChartBrief,
    Configuration,
    HouseCusp,
    LayerBrief,
    ResolvedBirth,
)


def _brief_with_two_layers() -> ChartBrief:
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
            BodyPosition(name="Sun", longitude=280.1, sign="Capricorn", degree=10.1, house=10, speed=1.01),
            BodyPosition(name="Moon", longitude=282.6, sign="Capricorn", degree=12.6, house=10, speed=12.34),
            BodyPosition(name="Mars", longitude=190.0, sign="Libra", degree=10.0, house=7, speed=None),
            BodyPosition(name="Ascendant", longitude=10.0, sign="Aries", degree=10.0, house=1, speed=None),
        ],
        house_cusps=[
            HouseCusp(house=1, longitude=10.0, sign="Aries", degree=10.0),
            HouseCusp(house=10, longitude=270.0, sign="Capricorn", degree=0.0),
        ],
        aspects=[
            Aspect(body_a="Moon", body_b="Sun", aspect="conjunction", angle=0.0, orb=2.5),
            Aspect(body_a="Mars", body_b="Sun", aspect="square", angle=90.0, orb=0.1),
        ],
        configurations=[
            Configuration(
                type="cardinal pressure",
                bodies=["Sun", "Moon", "Mars"],
                details={"apex": "Mars", "orb_window": {"max": 2.5}},
            )
        ],
    )
    transits = LayerBrief(
        name="transits",
        julian_day_ut=2461205.5,
        bodies=[
            BodyPosition(name="Sun", longitude=82.0, sign="Gemini", degree=22.0, house=1, speed=0.98),
            BodyPosition(name="Moon", longitude=66.0, sign="Gemini", degree=6.0, house=12, speed=13.22),
            BodyPosition(name="Mars", longitude=281.0, sign="Capricorn", degree=11.0, house=10, speed=0.033),
            BodyPosition(name="Ascendant", longitude=67.0, sign="Gemini", degree=7.0, house=1, speed=None),
        ],
        house_cusps=[
            HouseCusp(house=1, longitude=67.0, sign="Gemini", degree=7.0),
            HouseCusp(house=10, longitude=297.0, sign="Capricorn", degree=27.0),
        ],
        aspects=[
            Aspect(body_a="Mars", body_b="Moon", aspect="trine", angle=120.0, orb=1.0),
        ],
        configurations=[
            Configuration(type="lunar bridge", bodies=["Moon", "Mars"], details={"layers": ["transits"]})
        ],
    )
    return ChartBrief(zodiac="tropical", house_system="Placidus", resolved_birth=resolved, layers=[natal, transits])


def _facts(brief: ChartBrief):
    view = brief.facts
    return view() if callable(view) else view


def test_chartbrief_from_dict_roundtrips_nested_layers_bodies_aspects_and_configurations():
    brief = _brief_with_two_layers()

    reconstructed = ChartBrief.from_dict(brief.to_dict())

    assert reconstructed == brief
    assert isinstance(reconstructed.resolved_birth, ResolvedBirth)
    assert isinstance(reconstructed.layers[0], LayerBrief)
    assert isinstance(reconstructed.layers[0].bodies[0], BodyPosition)
    assert isinstance(reconstructed.layers[0].house_cusps[0], HouseCusp)
    assert isinstance(reconstructed.layers[0].aspects[0], Aspect)
    assert isinstance(reconstructed.layers[0].configurations[0], Configuration)
    assert reconstructed.layers[0].configurations[0].details == {"apex": "Mars", "orb_window": {"max": 2.5}}


def test_chartbrief_facts_are_derived_from_structured_layers_not_markdown(monkeypatch):
    brief = _brief_with_two_layers()

    def fail_if_markdown_is_used(self: ChartBrief) -> str:
        raise AssertionError("facts must be derived from structured layers, not ChartBrief.to_markdown()")

    monkeypatch.setattr(ChartBrief, "to_markdown", fail_if_markdown_is_used)

    facts = _facts(brief)

    assert facts.aspects == frozenset(
        {
            (frozenset({"Sun", "Moon"}), "conjunction"),
            (frozenset({"Sun", "Mars"}), "square"),
            (frozenset({"Moon", "Mars"}), "trine"),
        }
    )
    assert facts.speeds_by_body == {
        "Sun": [1.01, 0.98],
        "Moon": [12.34, 13.22],
        "Mars": [0.033],
    }


def test_chartbrief_fact_aspect_names_match_fabrication_guard_vocabulary():
    from natal_chart.fabrication import ASPECT_ALIASES

    facts = _facts(_brief_with_two_layers())
    guard_aspect_names = frozenset(ASPECT_ALIASES.values())

    assert "conjunction" in guard_aspect_names
    assert {aspect_name for _body_pair, aspect_name in facts.aspects} <= guard_aspect_names
    assert (frozenset({"Sun", "Moon"}), "conjunction") in facts.aspects


def test_models_module_does_not_import_fabrication_guard():
    source = Path(models.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_modules: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_modules.add(node.module)
                if node.module == "natal_chart":
                    imported_modules.update(f"natal_chart.{alias.name}" for alias in node.names)

    assert "natal_chart.fabrication" not in imported_modules
