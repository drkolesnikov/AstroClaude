from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from importlib import resources
from itertools import combinations
from math import floor
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import geonamescache
import swisseph as swe
from timezonefinder import TimezoneFinder

from natal_chart.models import (
    Aspect,
    BirthData,
    BodyPosition,
    ChartBrief,
    ChartComputationError,
    ChartSelection,
    Configuration,
    HouseCusp,
    LayerBrief,
    ResolvedBirth,
)

SIGN_NAMES = (
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
)

PLANET_IDS = (
    ("Sun", swe.SUN),
    ("Moon", swe.MOON),
    ("Mercury", swe.MERCURY),
    ("Venus", swe.VENUS),
    ("Mars", swe.MARS),
    ("Jupiter", swe.JUPITER),
    ("Saturn", swe.SATURN),
    ("Uranus", swe.URANUS),
    ("Neptune", swe.NEPTUNE),
    ("Pluto", swe.PLUTO),
    ("North Node", swe.TRUE_NODE),
    ("Chiron", swe.CHIRON),
)

OPTIONAL_BODY_IDS = (
    ("Black Moon Lilith", swe.MEAN_APOG),
    ("Ceres", swe.CERES),
    ("Pallas", swe.PALLAS),
    ("Juno", swe.JUNO),
    ("Vesta", swe.VESTA),
)

ANGLE_HOUSES = {
    "Ascendant": 1,
    "Descendant": 7,
    "Midheaven": 10,
    "Imum Coeli": 4,
}

ASPECT_DEFINITIONS = (
    ("conjunction", 0.0, 8.0),
    ("opposition", 180.0, 8.0),
    ("trine", 120.0, 8.0),
    ("square", 90.0, 8.0),
    ("sextile", 60.0, 6.0),
    ("quincunx", 150.0, 3.0),
)

CONFIGURATION_BODY_NAMES = {
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
    "North Node",
    "South Node",
    "Chiron",
}

TROPICAL_YEAR_DAYS = 365.2422
EPHEMERIS_FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED


def compute_chart(birth: BirthData, *, selection: ChartSelection | None = None) -> ChartBrief:
    selection = selection or ChartSelection()
    resolved = _resolve_birth(birth)
    _set_swiss_ephemeris_path()

    layer_builders = {
        "natal": lambda: _compute_standard_layer(
            "natal",
            _julian_day(resolved.utc_datetime),
            resolved.latitude,
            resolved.longitude,
            include_optional_bodies=selection.include_optional_bodies,
        ),
        "transits": lambda: _compute_standard_layer(
            "transits",
            _julian_day(_required_layer_datetime(selection.transit_date, "transits", "transit_date")),
            resolved.latitude,
            resolved.longitude,
            include_optional_bodies=selection.include_optional_bodies,
        ),
        "secondary_progressions": lambda: _compute_standard_layer(
            "secondary_progressions",
            _secondary_progressed_jd(
                datetime.fromisoformat(resolved.utc_datetime),
                _required_layer_datetime(selection.progression_date, "secondary_progressions", "progression_date"),
            ),
            resolved.latitude,
            resolved.longitude,
            include_optional_bodies=selection.include_optional_bodies,
        ),
        "solar_arc": lambda: _compute_solar_arc_layer(
            datetime.fromisoformat(resolved.utc_datetime),
            _required_layer_datetime(selection.solar_arc_date, "solar_arc", "solar_arc_date"),
            resolved.latitude,
            resolved.longitude,
            include_optional_bodies=selection.include_optional_bodies,
        ),
        "solar_return": lambda: _compute_standard_layer(
            "solar_return",
            _solar_return_jd(
                _planet_longitude(
                    _julian_day(resolved.utc_datetime),
                    swe.SUN,
                    "Sun",
                    EPHEMERIS_FLAGS,
                )[0],
                _required_layer_year(selection.solar_return_year, "solar_return", "solar_return_year"),
            ),
            resolved.latitude,
            resolved.longitude,
            include_optional_bodies=selection.include_optional_bodies,
        ),
    }

    layers = []
    for layer_name in selection.layers:
        if layer_name not in layer_builders:
            raise ChartComputationError(f"Unknown chart layer: {layer_name}.")
        layers.append(layer_builders[layer_name]())

    return ChartBrief(
        zodiac="tropical",
        house_system="Placidus",
        resolved_birth=resolved,
        layers=layers,
    )


def _compute_standard_layer(
    name: str,
    jd_ut: float,
    latitude: float,
    longitude: float,
    *,
    include_optional_bodies: bool,
) -> LayerBrief:
    house_cusps, raw_cusps, angle_longitudes = _compute_houses(jd_ut, latitude, longitude)
    bodies = _compute_bodies(jd_ut, raw_cusps, angle_longitudes, include_optional_bodies=include_optional_bodies)
    aspects = _compute_aspects(bodies)
    configurations = _detect_configurations(bodies, aspects)

    return LayerBrief(
        name=name,
        julian_day_ut=_round(jd_ut),
        bodies=bodies,
        house_cusps=house_cusps,
        aspects=aspects,
        configurations=configurations,
    )


def _compute_solar_arc_layer(
    birth_utc: datetime,
    target_utc: datetime,
    latitude: float,
    longitude: float,
    *,
    include_optional_bodies: bool,
) -> LayerBrief:
    birth_jd = _julian_day(birth_utc)
    target_jd = _julian_day(target_utc)
    natal = _compute_standard_layer(
        "natal",
        birth_jd,
        latitude,
        longitude,
        include_optional_bodies=include_optional_bodies,
    )
    progressed_jd = _secondary_progressed_jd(birth_utc, target_utc)
    progressed_sun, _ = _planet_longitude(progressed_jd, swe.SUN, "Sun", EPHEMERIS_FLAGS)
    natal_sun = _body_by_name(natal.bodies, "Sun").longitude
    arc = _normalize_degrees(progressed_sun - natal_sun)

    house_cusps = [
        HouseCusp(
            house=cusp.house,
            longitude=_round(_normalize_degrees(cusp.longitude + arc)),
            sign=_sign_name(cusp.longitude + arc),
            degree=_round((cusp.longitude + arc) % 30),
        )
        for cusp in natal.house_cusps
    ]
    raw_cusps = tuple(cusp.longitude for cusp in house_cusps)

    bodies = [
        _body_position(
            body.name,
            body.longitude + arc,
            raw_cusps,
            house=ANGLE_HOUSES.get(body.name),
            speed=None,
        )
        for body in natal.bodies
    ]
    bodies = sorted(bodies, key=lambda item: _body_order(item.name))
    aspects = _compute_aspects(bodies)
    configurations = _detect_configurations(bodies, aspects)

    return LayerBrief(
        name="solar_arc",
        julian_day_ut=_round(target_jd),
        bodies=bodies,
        house_cusps=house_cusps,
        aspects=aspects,
        configurations=configurations,
    )


def _set_swiss_ephemeris_path() -> None:
    try:
        ephemeris_path = resources.files("kerykeion").joinpath("sweph")
    except ModuleNotFoundError as exc:
        raise ChartComputationError(
            "Swiss Ephemeris data files are unavailable; install project dependencies with `uv sync`."
        ) from exc
    swe.set_ephe_path(str(ephemeris_path))


def _resolve_birth(birth: BirthData) -> ResolvedBirth:
    latitude = birth.latitude
    longitude = birth.longitude
    place_name = birth.place
    country_code = birth.country_code.upper() if birth.country_code else None
    timezone_name = birth.timezone

    if latitude is None or longitude is None:
        if not place_name:
            raise ChartComputationError("Birth place is required unless latitude and longitude are supplied.")
        location = _resolve_place(place_name, country_code)
        latitude = location["latitude"]
        longitude = location["longitude"]
        place_name = location["name"]
        country_code = location["country_code"]
        timezone_name = timezone_name or location["timezone"]
    else:
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            raise ChartComputationError("Latitude/longitude are out of range.")

    if timezone_name is None:
        timezone_name = TimezoneFinder().timezone_at(lat=latitude, lng=longitude)
    if timezone_name is None:
        raise ChartComputationError("Could not resolve an IANA timezone for the birth place.")

    try:
        timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ChartComputationError(f"Unknown IANA timezone: {timezone_name}") from exc

    local_naive = _parse_local_datetime(birth.date, birth.time)
    local_datetime = _strict_localize(local_naive, timezone)

    return ResolvedBirth(
        input_date=birth.date,
        input_time=birth.time,
        place=place_name or "coordinates",
        country_code=country_code,
        latitude=_round(latitude),
        longitude=_round(longitude),
        timezone=timezone_name,
        local_datetime=local_datetime.isoformat(),
        utc_datetime=local_datetime.astimezone(UTC).isoformat(),
    )


def _resolve_place(place: str, country_code: str | None) -> dict[str, object]:
    normalized_place, parsed_country = _split_place(place)
    country_code = country_code or _country_name_to_code(parsed_country)
    place_key = _normalize(normalized_place)

    gc = geonamescache.GeonamesCache()
    matches = []
    for city in gc.get_cities().values():
        if country_code and city.get("countrycode") != country_code:
            continue
        names = [city["name"], *city.get("alternatenames", [])]
        if place_key in {_normalize(name) for name in names}:
            matches.append(city)

    if not matches:
        suffix = f" in {country_code}" if country_code else ""
        raise ChartComputationError(f"Could not resolve birth place '{normalized_place}'{suffix}.")

    exact_name_matches = [city for city in matches if _normalize(city["name"]) == place_key]
    if exact_name_matches:
        matches = exact_name_matches

    if len(matches) > 1:
        matches = sorted(matches, key=lambda item: int(item.get("population") or 0), reverse=True)
        if not country_code or len(matches) > 1 and matches[1].get("population", 0) > 100000:
            options = ", ".join(
                f"{item['name']} {item.get('countrycode', '')}".strip() for item in matches[:5]
            )
            raise ChartComputationError(f"Birth place '{normalized_place}' is ambiguous: {options}.")

    city = matches[0]
    return {
        "name": city["name"],
        "country_code": city.get("countrycode"),
        "latitude": float(city["latitude"]),
        "longitude": float(city["longitude"]),
        "timezone": city.get("timezone"),
    }


def _split_place(place: str) -> tuple[str, str | None]:
    pieces = [piece.strip() for piece in place.split(",") if piece.strip()]
    if len(pieces) >= 2:
        return pieces[0], pieces[-1]
    return place.strip(), None


def _country_name_to_code(country_name: str | None) -> str | None:
    if not country_name:
        return None
    country_key = _normalize(country_name)
    countries = geonamescache.GeonamesCache().get_countries()
    for code, country in countries.items():
        names = {country.get("name"), country.get("iso"), country.get("iso3"), country.get("fips")}
        if country_key in {_normalize(name) for name in names if name}:
            return code
    return None


def _parse_local_datetime(date_value: str, time_value: str) -> datetime:
    try:
        return datetime.fromisoformat(f"{date_value}T{time_value}")
    except ValueError as exc:
        raise ChartComputationError("Birth date/time must be valid ISO values: YYYY-MM-DD and HH:MM.") from exc


def _strict_localize(local_naive: datetime, timezone: ZoneInfo) -> datetime:
    candidates = []
    for fold in (0, 1):
        aware = local_naive.replace(tzinfo=timezone, fold=fold)
        roundtrip = aware.astimezone(UTC).astimezone(timezone)
        if roundtrip.replace(tzinfo=None) == local_naive:
            candidates.append(aware)

    unique_by_utc = {candidate.astimezone(UTC): candidate for candidate in candidates}
    if not unique_by_utc:
        raise ChartComputationError(
            f"Birth time {local_naive.isoformat()} does not exist in timezone {timezone.key}."
        )
    if len(unique_by_utc) > 1:
        raise ChartComputationError(
            f"Birth time {local_naive.isoformat()} is ambiguous in timezone {timezone.key}; supply a UTC time."
        )
    return next(iter(unique_by_utc.values()))


def _julian_day(utc_datetime: str | datetime) -> float:
    if isinstance(utc_datetime, str):
        value = datetime.fromisoformat(utc_datetime).astimezone(UTC)
    else:
        value = utc_datetime.astimezone(UTC)
    hour = value.hour + value.minute / 60 + value.second / 3600 + value.microsecond / 3_600_000_000
    return swe.julday(value.year, value.month, value.day, hour, swe.GREG_CAL)


def _required_layer_datetime(value: str | None, layer_name: str, field_name: str) -> datetime:
    if value is None:
        raise ChartComputationError(f"{layer_name} layer requires {field_name}.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ChartComputationError(f"{field_name} must be an ISO date or datetime.") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _secondary_progressed_jd(birth_utc: datetime, target_utc: datetime) -> float:
    birth_utc = birth_utc.astimezone(UTC)
    target_utc = target_utc.astimezone(UTC)
    age_days = (target_utc - birth_utc).total_seconds() / 86_400
    if age_days < 0:
        raise ChartComputationError("secondary_progressions date must not be before the birth date.")
    progressed_utc = birth_utc + timedelta(days=age_days / TROPICAL_YEAR_DAYS)
    return _julian_day(progressed_utc)


def _required_layer_year(value: int | None, layer_name: str, field_name: str) -> int:
    if value is None:
        raise ChartComputationError(f"{layer_name} layer requires {field_name}.")
    if value < 1:
        raise ChartComputationError(f"{field_name} must be a positive calendar year.")
    return value


def _solar_return_jd(natal_sun_longitude: float, year: int) -> float:
    start_jd = swe.julday(year, 1, 1, 0.0, swe.GREG_CAL)
    end_jd = swe.julday(year + 1, 1, 1, 0.0, swe.GREG_CAL)
    start_longitude, _ = _planet_longitude(start_jd, swe.SUN, "Sun", EPHEMERIS_FLAGS)
    target = start_longitude + ((natal_sun_longitude - start_longitude) % 360)

    def unwrapped_sun(jd_ut: float) -> float:
        longitude, _ = _planet_longitude(jd_ut, swe.SUN, "Sun", EPHEMERIS_FLAGS)
        return start_longitude + ((longitude - start_longitude) % 360)

    low = start_jd
    high = end_jd
    for _ in range(80):
        midpoint = (low + high) / 2
        if unwrapped_sun(midpoint) < target:
            low = midpoint
        else:
            high = midpoint
    return (low + high) / 2


def _compute_houses(
    jd_ut: float, latitude: float, longitude: float
) -> tuple[list[HouseCusp], tuple[float, ...], dict[str, float]]:
    try:
        cusps, ascmc = swe.houses_ex(jd_ut, latitude, longitude, b"P", 0)
    except swe.Error as exc:
        raise ChartComputationError(f"Could not compute Placidus houses: {exc}") from exc

    house_cusps = [
        HouseCusp(
            house=index + 1,
            longitude=_round(cusp),
            sign=_sign_name(cusp),
            degree=_round(cusp % 30),
        )
        for index, cusp in enumerate(cusps)
    ]
    angles = {
        "Ascendant": float(ascmc[0]),
        "Midheaven": float(ascmc[1]),
        "Descendant": _normalize_degrees(float(ascmc[0]) + 180),
        "Imum Coeli": _normalize_degrees(float(ascmc[1]) + 180),
    }
    return house_cusps, tuple(float(cusp) for cusp in cusps), angles


def _compute_bodies(
    jd_ut: float,
    cusps: tuple[float, ...],
    angle_longitudes: dict[str, float],
    *,
    include_optional_bodies: bool,
) -> list[BodyPosition]:
    bodies = []
    raw_longitudes = {}
    for name, planet_id in PLANET_IDS:
        longitude, speed = _planet_longitude(jd_ut, planet_id, name, EPHEMERIS_FLAGS)
        raw_longitudes[name] = longitude
        bodies.append(_body_position(name, longitude, cusps, speed=speed))

    south_node_longitude = _normalize_degrees(raw_longitudes["North Node"] + 180)
    bodies.append(_body_position("South Node", south_node_longitude, cusps, speed=None))

    if include_optional_bodies:
        for name, planet_id in OPTIONAL_BODY_IDS:
            longitude, speed = _planet_longitude(jd_ut, planet_id, name, EPHEMERIS_FLAGS)
            raw_longitudes[name] = longitude
            bodies.append(_body_position(name, longitude, cusps, speed=speed))

        fortune_longitude = _part_of_fortune_longitude(
            ascendant=angle_longitudes["Ascendant"],
            sun=raw_longitudes["Sun"],
            moon=raw_longitudes["Moon"],
            sun_house=_house_for_longitude(raw_longitudes["Sun"], cusps),
        )
        bodies.append(_body_position("Part of Fortune", fortune_longitude, cusps, speed=None))

    for name in ("Ascendant", "Descendant", "Midheaven", "Imum Coeli"):
        bodies.append(
            _body_position(
                name,
                angle_longitudes[name],
                cusps,
                house=ANGLE_HOUSES[name],
                speed=None,
            )
        )

    return sorted(bodies, key=lambda item: _body_order(item.name))


def _planet_longitude(jd_ut: float, planet_id: int, name: str, flags: int) -> tuple[float, float]:
    try:
        result, _ = swe.calc_ut(jd_ut, planet_id, flags)
    except swe.Error as exc:
        raise ChartComputationError(f"Could not compute {name}: {exc}") from exc
    return _normalize_degrees(float(result[0])), float(result[3])


def _body_by_name(bodies: list[BodyPosition], name: str) -> BodyPosition:
    for body in bodies:
        if body.name == name:
            return body
    raise ChartComputationError(f"Could not find {name} in computed bodies.")


def _part_of_fortune_longitude(*, ascendant: float, sun: float, moon: float, sun_house: int) -> float:
    sun_above_horizon = 7 <= sun_house <= 12
    if sun_above_horizon:
        return _normalize_degrees(ascendant + moon - sun)
    return _normalize_degrees(ascendant + sun - moon)


def _body_position(
    name: str,
    longitude: float,
    cusps: tuple[float, ...],
    *,
    house: int | None = None,
    speed: float | None,
) -> BodyPosition:
    longitude = _normalize_degrees(longitude)
    return BodyPosition(
        name=name,
        longitude=_round(longitude),
        sign=_sign_name(longitude),
        degree=_round(longitude % 30),
        house=house or _house_for_longitude(longitude, cusps),
        speed=None if speed is None else _round(speed),
    )


def _compute_aspects(bodies: list[BodyPosition]) -> list[Aspect]:
    aspects = []
    for body_a, body_b in combinations(bodies, 2):
        separation = _angular_separation(body_a.longitude, body_b.longitude)
        for aspect_name, exact_angle, max_orb in ASPECT_DEFINITIONS:
            orb = abs(separation - exact_angle)
            if orb <= max_orb:
                aspects.append(
                    Aspect(
                        body_a=body_a.name,
                        body_b=body_b.name,
                        aspect=aspect_name,
                        angle=_round(exact_angle),
                        orb=_round(orb),
                    )
                )
                break
    return aspects


def _detect_configurations(bodies: list[BodyPosition], aspects: list[Aspect]) -> list[Configuration]:
    config_bodies = [body for body in bodies if body.name in CONFIGURATION_BODY_NAMES]
    aspect_lookup = {frozenset((aspect.body_a, aspect.body_b)): aspect.aspect for aspect in aspects}
    configurations = []
    configurations.extend(_detect_stelliums(config_bodies))
    configurations.extend(_detect_t_squares(config_bodies, aspect_lookup))
    configurations.extend(_detect_grand_trines(config_bodies, aspect_lookup))
    configurations.extend(_detect_grand_crosses(config_bodies, aspect_lookup))
    configurations.extend(_detect_yods(config_bodies, aspect_lookup))
    configurations.extend(_detect_kites(config_bodies, aspect_lookup))
    return _unique_configurations(configurations)


def _detect_stelliums(bodies: list[BodyPosition]) -> list[Configuration]:
    by_sign = defaultdict(list)
    for body in bodies:
        by_sign[body.sign].append(body.name)
    return [
        Configuration(type="stellium", bodies=_ordered_names(names), details={"sign": sign})
        for sign, names in by_sign.items()
        if len(names) >= 3
    ]


def _detect_t_squares(bodies: list[BodyPosition], aspects: dict[frozenset[str], str]) -> list[Configuration]:
    results = []
    for trio in combinations([body.name for body in bodies], 3):
        for opposition_pair in combinations(trio, 2):
            remaining = next(name for name in trio if name not in opposition_pair)
            if _has_aspect(opposition_pair[0], opposition_pair[1], "opposition", aspects) and all(
                _has_aspect(remaining, endpoint, "square", aspects) for endpoint in opposition_pair
            ):
                results.append(
                    Configuration(
                        type="t-square",
                        bodies=_ordered_names(trio),
                        details={"apex": remaining, "opposition": _ordered_names(opposition_pair)},
                    )
                )
    return results


def _detect_grand_trines(bodies: list[BodyPosition], aspects: dict[frozenset[str], str]) -> list[Configuration]:
    return [
        Configuration(type="grand trine", bodies=_ordered_names(trio), details={})
        for trio in combinations([body.name for body in bodies], 3)
        if all(_has_aspect(a, b, "trine", aspects) for a, b in combinations(trio, 2))
    ]


def _detect_grand_crosses(bodies: list[BodyPosition], aspects: dict[frozenset[str], str]) -> list[Configuration]:
    results = []
    for quartet in combinations([body.name for body in bodies], 4):
        oppositions = [pair for pair in combinations(quartet, 2) if _has_aspect(pair[0], pair[1], "opposition", aspects)]
        squares = [pair for pair in combinations(quartet, 2) if _has_aspect(pair[0], pair[1], "square", aspects)]
        if len(oppositions) >= 2 and len(squares) >= 4:
            results.append(
                Configuration(
                    type="grand cross",
                    bodies=_ordered_names(quartet),
                    details={"oppositions": [_ordered_names(pair) for pair in oppositions]},
                )
            )
    return results


def _detect_yods(bodies: list[BodyPosition], aspects: dict[frozenset[str], str]) -> list[Configuration]:
    results = []
    names = [body.name for body in bodies]
    for apex in names:
        others = [name for name in names if name != apex]
        for base_a, base_b in combinations(others, 2):
            if (
                _has_aspect(apex, base_a, "quincunx", aspects)
                and _has_aspect(apex, base_b, "quincunx", aspects)
                and _has_aspect(base_a, base_b, "sextile", aspects)
            ):
                results.append(
                    Configuration(
                        type="yod",
                        bodies=_ordered_names((apex, base_a, base_b)),
                        details={"apex": apex, "base": _ordered_names((base_a, base_b))},
                    )
                )
    return results


def _detect_kites(bodies: list[BodyPosition], aspects: dict[frozenset[str], str]) -> list[Configuration]:
    results = []
    names = [body.name for body in bodies]
    for trine in combinations(names, 3):
        if not all(_has_aspect(a, b, "trine", aspects) for a, b in combinations(trine, 2)):
            continue
        for anchor in trine:
            candidates = [name for name in names if name not in trine]
            for tail in candidates:
                other_trine_points = [name for name in trine if name != anchor]
                if _has_aspect(anchor, tail, "opposition", aspects) and all(
                    _has_aspect(tail, other, "sextile", aspects) for other in other_trine_points
                ):
                    results.append(
                        Configuration(
                            type="kite",
                            bodies=_ordered_names((*trine, tail)),
                            details={"opposition": _ordered_names((anchor, tail))},
                        )
                    )
    return results


def _unique_configurations(configurations: list[Configuration]) -> list[Configuration]:
    seen = set()
    unique = []
    for configuration in configurations:
        detail_items = tuple(sorted((key, repr(value)) for key, value in configuration.details.items()))
        key = (configuration.type, tuple(configuration.bodies), detail_items)
        if key not in seen:
            seen.add(key)
            unique.append(configuration)
    return unique


def _has_aspect(body_a: str, body_b: str, aspect: str, aspects: dict[frozenset[str], str]) -> bool:
    return aspects.get(frozenset((body_a, body_b))) == aspect


def _house_for_longitude(longitude: float, cusps: tuple[float, ...]) -> int:
    for index, start in enumerate(cusps):
        end = cusps[(index + 1) % 12]
        span = (end - start) % 360
        offset = (longitude - start) % 360
        if offset < span or abs(offset - span) < 1e-9:
            return index + 1
    raise ChartComputationError(f"Could not assign house for longitude {longitude}.")


def _sign_name(longitude: float) -> str:
    return SIGN_NAMES[floor(_normalize_degrees(longitude) / 30)]


def _angular_separation(longitude_a: float, longitude_b: float) -> float:
    return abs((_normalize_degrees(longitude_a - longitude_b) + 180) % 360 - 180)


def _normalize_degrees(value: float) -> float:
    return value % 360


def _round(value: float) -> float:
    return round(float(value), 4)


def _normalize(value: str) -> str:
    return " ".join(value.casefold().strip().split())


def _body_order(name: str) -> int:
    order = [
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
        "Black Moon Lilith",
        "Ceres",
        "Pallas",
        "Juno",
        "Vesta",
        "Part of Fortune",
    ]
    return order.index(name)


def _ordered_names(names: tuple[str, ...] | list[str]) -> list[str]:
    return sorted(names, key=_body_order)
