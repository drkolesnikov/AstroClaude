import pytest
from pytest import approx

from natal_chart import BirthData, ChartComputationError, ChartSelection, compute_chart


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


def test_compute_chart_renders_exactly_selected_natal_and_transit_layers():
    brief = compute_chart(
        BirthData(
            date="1990-01-01",
            time="12:00",
            place="Moscow",
            country_code="RU",
        ),
        selection=ChartSelection(
            layers=("natal", "transits"),
            transit_date="2026-06-14",
        ),
    )

    data = brief.to_dict()

    assert [layer["name"] for layer in data["layers"]] == ["natal", "transits"]
    assert all(len(layer["bodies"]) == 17 for layer in data["layers"])

    markdown = brief.to_markdown()
    assert "## Natal Layer" in markdown
    assert "## Transits Layer" in markdown
    assert "## Secondary Progressions Layer" not in markdown
    assert "## Solar Arc Layer" not in markdown
    assert "## Solar Return Layer" not in markdown


def test_optional_bodies_are_included_only_when_requested():
    brief = compute_chart(
        BirthData(
            date="1990-01-01",
            time="12:00",
            place="Moscow",
            country_code="RU",
        ),
        selection=ChartSelection(
            layers=("natal", "transits"),
            transit_date="2026-06-14",
            include_optional_bodies=True,
        ),
    )

    optional_names = {"Black Moon Lilith", "Ceres", "Pallas", "Juno", "Vesta", "Part of Fortune"}

    for layer in brief.to_dict()["layers"]:
        bodies = {body["name"] for body in layer["bodies"]}
        assert optional_names <= bodies
        assert len(bodies) == 23


def test_transit_layer_matches_reference_positions_for_known_date():
    brief = compute_chart(
        BirthData(
            date="1990-01-01",
            time="12:00",
            place="Moscow",
            country_code="RU",
        ),
        selection=ChartSelection(
            layers=("transits",),
            transit_date="2026-06-14",
        ),
    )

    transits = brief.to_dict()["layers"][0]
    assert transits["name"] == "transits"
    assert transits["julian_day_ut"] == approx(2461205.5)

    bodies = {body["name"]: body for body in transits["bodies"]}
    assert bodies["Sun"]["sign"] == "Gemini"
    assert bodies["Sun"]["house"] == 1
    assert bodies["Sun"]["longitude"] == approx(82.9787, abs=0.01)
    assert bodies["Moon"]["sign"] == "Gemini"
    assert bodies["Moon"]["house"] == 12
    assert bodies["Moon"]["longitude"] == approx(66.9024, abs=0.01)
    assert bodies["Chiron"]["sign"] == "Aries"
    assert bodies["Chiron"]["longitude"] == approx(29.7706, abs=0.01)

    cusps = {cusp["house"]: cusp for cusp in transits["house_cusps"]}
    assert cusps[1]["longitude"] == approx(67.0786, abs=0.01)
    assert cusps[10]["longitude"] == approx(297.8386, abs=0.01)

    aspects = {(aspect["body_a"], aspect["aspect"], aspect["body_b"]): aspect for aspect in transits["aspects"]}
    assert aspects[("Moon", "conjunction", "Ascendant")]["orb"] == approx(0.1762, abs=0.01)
    assert aspects[("Venus", "square", "Chiron")]["orb"] == approx(0.8709, abs=0.01)


def test_secondary_progressions_layer_uses_day_for_year_reference():
    brief = compute_chart(
        BirthData(
            date="1990-01-01",
            time="12:00",
            place="Moscow",
            country_code="RU",
        ),
        selection=ChartSelection(
            layers=("secondary_progressions",),
            progression_date="2026-06-14",
        ),
    )

    progressed = brief.to_dict()["layers"][0]
    assert progressed["name"] == "secondary_progressions"
    assert progressed["julian_day_ut"] == approx(2447929.3238, abs=0.0001)
    assert len(progressed["bodies"]) == 17
    assert len(progressed["house_cusps"]) == 12

    bodies = {body["name"]: body for body in progressed["bodies"]}
    assert bodies["Sun"]["sign"] == "Aquarius"
    assert bodies["Sun"]["longitude"] == approx(317.7675, abs=0.01)
    assert bodies["Moon"]["sign"] == "Cancer"
    assert bodies["Moon"]["longitude"] == approx(100.5878, abs=0.01)


def test_solar_arc_layer_directs_natal_factors_by_progressed_sun_arc():
    brief = compute_chart(
        BirthData(
            date="1990-01-01",
            time="12:00",
            place="Moscow",
            country_code="RU",
        ),
        selection=ChartSelection(
            layers=("solar_arc",),
            solar_arc_date="2026-06-14",
        ),
    )

    solar_arc = brief.to_dict()["layers"][0]
    assert solar_arc["name"] == "solar_arc"
    assert solar_arc["julian_day_ut"] == approx(2461205.5)
    assert len(solar_arc["bodies"]) == 17
    assert len(solar_arc["house_cusps"]) == 12

    bodies = {body["name"]: body for body in solar_arc["bodies"]}
    assert bodies["Sun"]["sign"] == "Aquarius"
    assert bodies["Sun"]["longitude"] == approx(317.7675, abs=0.01)
    assert bodies["Moon"]["sign"] == "Aries"
    assert bodies["Moon"]["longitude"] == approx(8.6662, abs=0.01)
    assert bodies["Ascendant"]["longitude"] == approx(47.1405, abs=0.01)

    cusps = {cusp["house"]: cusp for cusp in solar_arc["house_cusps"]}
    assert cusps[1]["longitude"] == approx(47.1405, abs=0.01)
    assert cusps[10]["longitude"] == approx(310.1748, abs=0.01)


def test_solar_return_layer_finds_exact_sun_return_for_year():
    brief = compute_chart(
        BirthData(
            date="1990-01-01",
            time="12:00",
            place="Moscow",
            country_code="RU",
        ),
        selection=ChartSelection(
            layers=("solar_return",),
            solar_return_year=2026,
        ),
    )

    solar_return = brief.to_dict()["layers"][0]
    assert solar_return["name"] == "solar_return"
    assert solar_return["julian_day_ut"] == approx(2461041.6160, abs=0.0001)
    assert len(solar_return["bodies"]) == 17
    assert len(solar_return["house_cusps"]) == 12

    bodies = {body["name"]: body for body in solar_return["bodies"]}
    assert bodies["Sun"]["sign"] == "Capricorn"
    assert bodies["Sun"]["longitude"] == approx(280.6868, abs=0.01)
    assert bodies["Moon"]["sign"] == "Gemini"
    assert bodies["Moon"]["longitude"] == approx(68.4557, abs=0.01)

    cusps = {cusp["house"]: cusp for cusp in solar_return["house_cusps"]}
    assert cusps[1]["longitude"] == approx(239.8152, abs=0.01)
    assert cusps[10]["longitude"] == approx(180.1755, abs=0.01)
