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

    report = check_fabrications(reading, _john_d_style_brief().to_markdown())

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
    report = check_fabrications("Pluto conjunct the IC.", _john_d_style_brief().to_markdown())

    assert report.to_dict()["unsupported_count"] == 1
    assert report.to_dict()["unsupported_claims"][0]["body_b"] == "Imum Coeli"
