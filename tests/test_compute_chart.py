import pytest
from pytest import approx

from natal_chart import BirthData, ChartComputationError, compute_chart


def test_compute_chart_returns_grounded_natal_brief_for_known_birth():
    brief = compute_chart(
        BirthData(
            date="1990-01-01",
            time="12:00",
            place="Moscow",
            country_code="RU",
        )
    )

    data = brief.to_dict()

    assert data["zodiac"] == "tropical"
    assert data["house_system"] == "Placidus"
    assert data["resolved_birth"]["timezone"] == "Europe/Moscow"
    assert data["resolved_birth"]["utc_datetime"] == "1990-01-01T09:00:00+00:00"

    natal = data["layers"][0]
    assert natal["name"] == "natal"
    assert natal["julian_day_ut"] == approx(2447892.875)

    bodies = {body["name"]: body for body in natal["bodies"]}
    assert set(bodies) == {
        "Sun",
        "Moon",
        "Mercury",
        "Venus",
        "Mars",
        "Jupiter",
        "Saturn",
        "Uranus",
        "Neptune",
        "Pluto",
        "Ascendant",
        "Descendant",
        "Midheaven",
        "Imum Coeli",
        "North Node",
        "South Node",
        "Chiron",
    }
    assert "Black Moon Lilith" not in bodies
    assert "Ceres" not in bodies
    assert "Part of Fortune" not in bodies

    assert bodies["Sun"]["sign"] == "Capricorn"
    assert bodies["Sun"]["house"] == 10
    assert bodies["Sun"]["longitude"] == approx(280.6868, abs=0.01)
    assert bodies["Moon"]["sign"] == "Pisces"
    assert bodies["Moon"]["house"] == 12
    assert bodies["Chiron"]["sign"] == "Cancer"
    assert bodies["Chiron"]["longitude"] == approx(103.8218, abs=0.01)

    cusps = {cusp["house"]: cusp for cusp in natal["house_cusps"]}
    assert cusps[1]["longitude"] == approx(10.0672, abs=0.01)
    assert cusps[10]["longitude"] == approx(273.0957, abs=0.01)

    aspects = {(aspect["body_a"], aspect["aspect"], aspect["body_b"]): aspect for aspect in natal["aspects"]}
    assert aspects[("Sun", "conjunction", "Neptune")]["orb"] == approx(1.3466, abs=0.01)
    assert aspects[("Jupiter", "opposition", "Uranus")]["orb"] == approx(0.6124, abs=0.01)

    configurations = {(item["type"], tuple(item["bodies"])) for item in natal["configurations"]}
    assert ("stellium", ("Sun", "Mercury", "Saturn", "Uranus", "Neptune")) in configurations

    markdown = brief.to_markdown()
    assert "# Natal Chart Brief" in markdown
    assert "## Natal Layer" in markdown
    assert "Sun | Capricorn" in markdown


def test_compute_chart_fails_loudly_for_ambiguous_place():
    with pytest.raises(ChartComputationError, match="ambiguous"):
        compute_chart(BirthData(date="1990-01-01", time="12:00", place="Springfield"))

    with pytest.raises(ChartComputationError, match="Could not resolve"):
        compute_chart(BirthData(date="1990-01-01", time="12:00", place="NoSuchBirthplaceXYZ"))
