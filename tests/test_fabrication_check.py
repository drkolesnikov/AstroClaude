import pytest

import natal_chart.fabrication as fabrication
from natal_chart.fabrication import check_fabrications
from natal_chart.models import (
    Aspect,
    BodyPosition,
    ChartBrief,
    Configuration,
    HouseCusp,
    LayerBrief,
    ResolvedBirth,
)


def _john_d_style_brief() -> ChartBrief:
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
            BodyPosition(name="Mars", longitude=120.0, sign="Leo", degree=0.0, house=5, speed=0.003),
            BodyPosition(name="Jupiter", longitude=150.0, sign="Virgo", degree=0.0, house=6, speed=0.08),
            BodyPosition(name="Uranus", longitude=210.0, sign="Scorpio", degree=0.0, house=8, speed=0.04),
            BodyPosition(name="Pluto", longitude=197.0, sign="Libra", degree=17.0, house=7, speed=0.02),
            BodyPosition(name="Imum Coeli", longitude=180.0, sign="Libra", degree=0.0, house=4, speed=None),
        ],
        house_cusps=[HouseCusp(house=4, longitude=180.0, sign="Libra", degree=0.0)],
        aspects=[
            Aspect(body_a="Sun", body_b="Moon", aspect="sextile", angle=60.0, orb=0.0),
            Aspect(body_a="Mars", body_b="Uranus", aspect="trine", angle=120.0, orb=0.3),
        ],
        configurations=[Configuration(type="grand trine", bodies=["Sun", "Moon", "Mars"])],
    )
    return ChartBrief(zodiac="tropical", house_system="Placidus", resolved_birth=resolved, layers=[natal])


def test_fabrication_checker_flags_john_d_style_unsupported_claims():
    reading = """
    The reading leans heavily on Pluto conjunct the IC, as if the roots are under
    Plutonian pressure. It also treats the Jupiter-Uranus conjunction as a license
    for sudden liberation. Stationary Mercury, almost at a standstill, means speech
    freezes before it moves. By contrast, Sun sextile Moon is actually in the chart,
    and Mars at a standstill can be used because its speed is near zero.
    """

    report = check_fabrications(reading, _john_d_style_brief())

    assert report.unsupported_count == 3
    assert {(claim.claim_type, claim.body_a, claim.aspect, claim.body_b) for claim in report.unsupported_claims} == {
        ("aspect", "Pluto", "conjunction", "Imum Coeli"),
        ("aspect", "Jupiter", "conjunction", "Uranus"),
        ("station", "Mercury", None, None),
    }
    unsupported_text = "\n".join(claim.text for claim in report.unsupported_claims)
    assert "Sun sextile Moon" not in unsupported_text
    assert "Mars at a standstill" not in unsupported_text


def test_fabrication_report_serializes_count_for_run_metrics():
    report = check_fabrications("Pluto conjunct the IC.", _john_d_style_brief())

    assert report.to_dict()["unsupported_count"] == 1
    assert report.to_dict()["unsupported_claims"][0]["body_b"] == "Imum Coeli"


def _hardening_brief() -> ChartBrief:
    """Mirrors the john-d facts the checker missed: Mercury ordinary retrograde,
    Mars stationary, a real Venus-MC conjunction, no Pluto-IC, no Jupiter-Uranus."""
    resolved = ResolvedBirth(
        input_date="1980-01-01", input_time="12:00", place="London", country_code="GB",
        latitude=51.5, longitude=-0.1, timezone="Europe/London",
        local_datetime="1980-01-01T12:00:00+00:00", utc_datetime="1980-01-01T12:00:00+00:00",
    )
    natal = LayerBrief(
        name="natal", julian_day_ut=2444239.0,
        bodies=[
            BodyPosition(name="Mercury", longitude=33.9, sign="Taurus", degree=3.9, house=9, speed=-0.6669),
            BodyPosition(name="Venus", longitude=43.6, sign="Taurus", degree=13.6, house=9, speed=1.23),
            BodyPosition(name="Mars", longitude=166.7, sign="Virgo", degree=16.7, house=1, speed=-0.0046),
            BodyPosition(name="Jupiter", longitude=319.0, sign="Aquarius", degree=19.0, house=6, speed=0.12),
            BodyPosition(name="Uranus", longitude=308.5, sign="Aquarius", degree=8.5, house=6, speed=0.01),
            BodyPosition(name="Pluto", longitude=244.9, sign="Sagittarius", degree=4.9, house=4, speed=-0.02),
            BodyPosition(name="Midheaven", longitude=47.5, sign="Taurus", degree=17.5, house=10, speed=None),
            BodyPosition(name="Imum Coeli", longitude=227.5, sign="Scorpio", degree=17.5, house=4, speed=None),
        ],
        house_cusps=[HouseCusp(house=4, longitude=227.5, sign="Scorpio", degree=17.5)],
        aspects=[Aspect(body_a="Venus", body_b="Midheaven", aspect="conjunction", angle=0.0, orb=3.9)],
        configurations=[],
    )
    return ChartBrief(zodiac="tropical", house_system="Placidus", resolved_birth=resolved, layers=[natal])


def test_flags_separated_subject_planet_conjunct_angle():
    # the literal john-d shadow phrasing: subject is far from the aspect word
    reading = "Pluto at 4.96° Sagittarius sits in the fourth house, conjunct the IC at Scorpio 17°."
    report = check_fabrications(reading, _hardening_brief())
    assert ("Pluto", "conjunction", "Imum Coeli") in {
        (c.body_a, c.aspect, c.body_b) for c in report.unsupported_claims
    }


def test_flags_station_in_noun_and_verb_forms_for_nonstationary_body():
    reading = "Mercury is retrograde, stationed and turning, so close to exact station."
    report = check_fabrications(reading, _hardening_brief())
    assert any(c.claim_type == "station" and c.body_a == "Mercury" for c in report.unsupported_claims)


def test_does_not_flag_station_for_genuinely_stationary_mars_in_noun_form():
    reading = "Stationary retrograde Mars in Virgo. The Mars station holds the charge."
    report = check_fabrications(reading, _hardening_brief())
    assert all(not (c.claim_type == "station" and c.body_a == "Mars") for c in report.unsupported_claims)


def test_does_not_flag_real_conjunction_named_in_the_brief():
    reading = "Venus conjunct the Midheaven anchors value to vocation."
    report = check_fabrications(reading, _hardening_brief())
    assert all(not (c.body_a == "Venus" and c.body_b == "Midheaven") for c in report.unsupported_claims)


def test_does_not_misbind_an_aspect_object_as_the_next_aspects_subject():
    # the real john-d shadow phrasing — Venus is the OBJECT of the first trine,
    # not the subject of the second; it must not become a Venus-MC trine claim.
    reading = "Mars stations; the trine to Venus and the trine to the Midheaven integrate it."
    report = check_fabrications(reading, _hardening_brief())
    assert all(
        not (c.body_a == "Venus" and c.aspect == "trine" and c.body_b == "Midheaven")
        for c in report.unsupported_claims
    )


def test_does_not_read_the_word_t_square_as_a_square_aspect():
    reading = "Pluto sits at the apex of the t-square with the Moon."
    report = check_fabrications(reading, _hardening_brief())
    assert all(c.aspect != "square" for c in report.unsupported_claims)


def test_consumes_a_coordinated_object_list_so_it_does_not_leak_a_subject():
    # "sextile Uranus and Neptune, trine the South Node" — Neptune is a coordinated
    # object of the sextile, not the subject of the trine.
    reading = "Pluto is sextile Uranus and Neptune, trine the South Node."
    report = check_fabrications(reading, _hardening_brief())
    assert all(not (c.body_a == "Neptune" and c.body_b == "South Node") for c in report.unsupported_claims)


def test_does_not_bind_a_station_to_an_angle():
    reading = "The Ascendant holds the chart together while Mars sits at a standstill."
    report = check_fabrications(reading, _hardening_brief())
    assert all(c.body_a != "Ascendant" for c in report.unsupported_claims)


def test_check_fabrications_rejects_rendered_chart_brief_markdown():
    with pytest.raises(TypeError, match="ChartBrief"):
        check_fabrications("Pluto conjunct the IC.", _john_d_style_brief().to_markdown())


def test_check_fabrications_uses_structured_chart_brief_without_rendering_markdown(monkeypatch):
    def fail_if_markdown_is_used(self: ChartBrief) -> str:
        raise AssertionError("fabrication guard must derive facts from structured ChartBrief layers")

    monkeypatch.setattr(ChartBrief, "to_markdown", fail_if_markdown_is_used)

    report = check_fabrications("Pluto conjunct the IC and stationary Mercury.", _john_d_style_brief())

    assert report.unsupported_count == 2


def test_markdown_chart_brief_parser_has_been_removed():
    assert not hasattr(fabrication, "_parse_chart_brief")
