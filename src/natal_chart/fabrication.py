from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Literal

from natal_chart.models import ChartBrief

AspectName = Literal["conjunction", "opposition", "square", "trine", "sextile"]
ClaimType = Literal["aspect", "station"]

STATION_SPEED_THRESHOLD = 0.05

ASPECT_ALIASES: dict[str, AspectName] = {
    "conjunct": "conjunction",
    "conjunction": "conjunction",
    "opposite": "opposition",
    "opposition": "opposition",
    "square": "square",
    "squares": "square",
    "trine": "trine",
    "trines": "trine",
    "sextile": "sextile",
    "sextiles": "sextile",
}

BODY_ALIASES = {
    "sun": "Sun",
    "moon": "Moon",
    "mercury": "Mercury",
    "venus": "Venus",
    "mars": "Mars",
    "jupiter": "Jupiter",
    "saturn": "Saturn",
    "uranus": "Uranus",
    "neptune": "Neptune",
    "pluto": "Pluto",
    "chiron": "Chiron",
    "north node": "North Node",
    "south node": "South Node",
    "ascendant": "Ascendant",
    "asc": "Ascendant",
    "ac": "Ascendant",
    "descendant": "Descendant",
    "desc": "Descendant",
    "dc": "Descendant",
    "dsc": "Descendant",
    "midheaven": "Midheaven",
    "mc": "Midheaven",
    "imum coeli": "Imum Coeli",
    "ic": "Imum Coeli",
}

BODY_PATTERN = r"""
    North\ Node|South\ Node|Imum\ Coeli|Midheaven|Ascendant|Descendant|
    Mercury|Jupiter|Neptune|Uranus|Chiron|Saturn|Pluto|Venus|Moon|Mars|Sun|
    ASC|DSC|MC|IC|AC|DC|Asc|Desc
"""
ASPECT_PATTERN = r"conjunct(?:ion)?|opposite|opposition|squares?|trines?|sextiles?"


@dataclass(frozen=True)
class UnsupportedClaim:
    claim_type: ClaimType
    text: str
    reason: str
    body_a: str
    aspect: AspectName | None = None
    body_b: str | None = None


@dataclass(frozen=True)
class FabricationReport:
    unsupported_claims: tuple[UnsupportedClaim, ...]

    @property
    def unsupported_count(self) -> int:
        return len(self.unsupported_claims)

    def to_dict(self) -> dict[str, object]:
        return {
            "unsupported_count": self.unsupported_count,
            "unsupported_claims": [asdict(claim) for claim in self.unsupported_claims],
        }


@dataclass(frozen=True)
class ChartGroundTruth:
    aspects: frozenset[tuple[frozenset[str], AspectName]]
    speeds_by_body: dict[str, list[float]]


@dataclass(frozen=True)
class ParsedAspectClaim:
    text: str
    body_a: str
    aspect: AspectName
    body_b: str


@dataclass(frozen=True)
class ParsedStationClaim:
    text: str
    body: str


def check_fabrications(
    reading: str,
    chart_brief: str | ChartBrief,
    *,
    station_speed_threshold: float = STATION_SPEED_THRESHOLD,
) -> FabricationReport:
    brief_markdown = chart_brief.to_markdown() if isinstance(chart_brief, ChartBrief) else chart_brief
    ground_truth = _parse_chart_brief(brief_markdown)
    unsupported: list[UnsupportedClaim] = []

    seen_aspects = set()
    for claim in _aspect_claims(reading):
        key = (frozenset((claim.body_a, claim.body_b)), claim.aspect)
        if key in seen_aspects:
            continue
        seen_aspects.add(key)
        if key not in ground_truth.aspects:
            unsupported.append(
                UnsupportedClaim(
                    claim_type="aspect",
                    text=claim.text,
                    reason="aspect is not listed in the chart brief",
                    body_a=claim.body_a,
                    aspect=claim.aspect,
                    body_b=claim.body_b,
                )
            )

    seen_stations = set()
    for claim in _station_claims(reading):
        if claim.body in seen_stations:
            continue
        seen_stations.add(claim.body)
        speeds = ground_truth.speeds_by_body.get(claim.body, [])
        is_stationary = any(abs(speed) <= station_speed_threshold for speed in speeds)
        if not is_stationary:
            unsupported.append(
                UnsupportedClaim(
                    claim_type="station",
                    text=claim.text,
                    reason=f"body speed is not near zero in the chart brief (threshold {station_speed_threshold})",
                    body_a=claim.body,
                )
            )

    return FabricationReport(unsupported_claims=tuple(unsupported))


def _parse_chart_brief(markdown: str) -> ChartGroundTruth:
    aspects: set[tuple[frozenset[str], AspectName]] = set()
    speeds_by_body: dict[str, list[float]] = {}
    section: str | None = None
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped == "### Bodies":
            section = "bodies"
            continue
        if stripped == "### Aspects":
            section = "aspects"
            continue
        if stripped.startswith("### "):
            section = None
            continue
        if not (stripped.startswith("|") and stripped.endswith("|")):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if _is_table_header_or_rule(cells):
            continue
        if section == "bodies" and len(cells) >= 6:
            body = _canonical_body(cells[0])
            speed = _parse_float(cells[5])
            if body and speed is not None:
                speeds_by_body.setdefault(body, []).append(speed)
        if section == "aspects" and len(cells) >= 3:
            body_a = _canonical_body(cells[0])
            aspect = _canonical_aspect(cells[1])
            body_b = _canonical_body(cells[2])
            if body_a and aspect and body_b:
                aspects.add((frozenset((body_a, body_b)), aspect))

    return ChartGroundTruth(aspects=frozenset(aspects), speeds_by_body=speeds_by_body)


def _aspect_claims(reading: str) -> list[ParsedAspectClaim]:
    claims = []
    direct = re.compile(
        rf"\b(?P<body_a>{BODY_PATTERN})\b\s+(?:is\s+|are\s+|was\s+|were\s+)?"
        rf"(?P<aspect>{ASPECT_PATTERN})\s+(?:the\s+)?\b(?P<body_b>{BODY_PATTERN})\b",
        re.IGNORECASE | re.VERBOSE,
    )
    pair_then_aspect = re.compile(
        rf"\b(?P<body_a>{BODY_PATTERN})\b\s*[-–—/]\s*"
        rf"\b(?P<body_b>{BODY_PATTERN})\b\s+(?P<aspect>{ASPECT_PATTERN})",
        re.IGNORECASE | re.VERBOSE,
    )
    for pattern in (direct, pair_then_aspect):
        for match in pattern.finditer(reading):
            body_a = _canonical_body(match.group("body_a"))
            body_b = _canonical_body(match.group("body_b"))
            aspect = _canonical_aspect(match.group("aspect"))
            if body_a and body_b and aspect:
                claims.append(
                    ParsedAspectClaim(
                        text=_clean_claim_text(match.group(0)),
                        body_a=body_a,
                        aspect=aspect,
                        body_b=body_b,
                    )
                )
    return claims


def _station_claims(reading: str) -> list[ParsedStationClaim]:
    claims = []
    patterns = [
        re.compile(rf"\bstationary\s+(?P<body>{BODY_PATTERN})\b", re.IGNORECASE | re.VERBOSE),
        re.compile(
            rf"\b(?P<body>{BODY_PATTERN})\b\s+(?:is\s+|was\s+|appears\s+)?stationary\b",
            re.IGNORECASE | re.VERBOSE,
        ),
        re.compile(
            rf"\b(?P<body>{BODY_PATTERN})\b\s+(?:is\s+|was\s+)?(?:at\s+)?(?:a\s+)?standstill\b",
            re.IGNORECASE | re.VERBOSE,
        ),
    ]
    for pattern in patterns:
        for match in pattern.finditer(reading):
            body = _canonical_body(match.group("body"))
            if body:
                claims.append(ParsedStationClaim(text=_clean_claim_text(match.group(0)), body=body))
    return claims


def _canonical_body(value: str) -> str | None:
    normalized = re.sub(r"\s+", " ", value.strip().casefold())
    return BODY_ALIASES.get(normalized)


def _canonical_aspect(value: str) -> AspectName | None:
    normalized = value.strip().casefold()
    return ASPECT_ALIASES.get(normalized)


def _parse_float(value: str) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _is_table_header_or_rule(cells: list[str]) -> bool:
    return not cells or all(set(cell) <= {"-", ":"} for cell in cells) or cells[0] in {"Body", "Body A"}


def _clean_claim_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip(" .,;:")
