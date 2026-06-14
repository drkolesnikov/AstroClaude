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

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?;])\s+")
_BODY_FINDER = re.compile(rf"\b(?:{BODY_PATTERN})\b", re.IGNORECASE | re.VERBOSE)
_ASPECT_FINDER = re.compile(rf"(?<!t-)(?<!grand )\b(?:{ASPECT_PATTERN})\b", re.IGNORECASE)
_STATION_FINDER = re.compile(r"\b(?:mid-)?station(?:ary|ed|ing|s)?\b|\bstandstill\b", re.IGNORECASE)
_OBJECT_GAP = re.compile(r"^\s*(?:the|its|a|an|to|with)?\s*$", re.IGNORECASE)
_COORD_GAP = re.compile(r"^\s*,?\s*(?:and|or)?\s*,?\s*$", re.IGNORECASE)
_ANGLES = frozenset({"Ascendant", "Descendant", "Midheaven", "Imum Coeli"})
_PAIR_THEN_ASPECT = re.compile(
    rf"\b(?P<body_a>{BODY_PATTERN})\b\s*[-–—/]\s*"
    rf"\b(?P<body_b>{BODY_PATTERN})\b\s+(?P<aspect>{ASPECT_PATTERN})",
    re.IGNORECASE | re.VERBOSE,
)


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


def _sentences(text: str) -> list[str]:
    return _SENTENCE_SPLIT.split(text)


def _body_spans(sentence: str) -> list[tuple[int, int, str]]:
    spans: list[tuple[int, int, str]] = []
    for match in _BODY_FINDER.finditer(sentence):
        name = _canonical_body(match.group(0))
        if name:
            spans.append((match.start(), match.end(), name))
    return spans


def _immediate_object(sentence: str, aspect_end: int, bodies: list[tuple[int, int, str]]) -> int | None:
    """The object is the body right after the aspect word, separated only by a
    connector ("the"/"to"/...). If the nearest following body is further than that
    (a clause, "(orb 7°)", an unparsable phrase like "the lunar nodes"), there is
    no object — better to miss than to grab a far body."""
    for index, (start, _end, _name) in enumerate(bodies):
        if start >= aspect_end:
            return index if _OBJECT_GAP.match(sentence[aspect_end:start]) else None
    return None


def _coordinated_object_indices(sentence: str, first: int, bodies: list[tuple[int, int, str]]) -> set[int]:
    """Consume a coordinated object list whole — "sextile Uranus and Neptune"
    makes both objects, so neither leaks as a later aspect's subject."""
    indices = {first}
    cursor = first
    while cursor + 1 < len(bodies) and _COORD_GAP.match(sentence[bodies[cursor][1] : bodies[cursor + 1][0]]):
        cursor += 1
        indices.add(cursor)
    return indices


def _aspect_claims(reading: str) -> list[ParsedAspectClaim]:
    """Sentence-aware. An aspect's object is the body *immediately* after it; a
    coordinated list is consumed whole; the subject is the nearest preceding body
    not used as an object. Catches "Pluto ... conjunct the IC" while refusing to
    grab a far-off body, a coordinated object, or the "square" inside "t-square"."""
    claims: list[ParsedAspectClaim] = []
    for sentence in _sentences(reading):
        bodies = _body_spans(sentence)
        if bodies:
            hits = [
                (m.start(), m.end(), aspect)
                for m in _ASPECT_FINDER.finditer(sentence)
                if (aspect := _canonical_aspect(m.group(0)))
            ]
            objects = [_immediate_object(sentence, a_end, bodies) for (_s, a_end, _a) in hits]
            consumed: set[int] = set()
            for obj_idx in objects:
                if obj_idx is not None:
                    consumed |= _coordinated_object_indices(sentence, obj_idx, bodies)
            for (a_start, _a_end, aspect), obj_idx in zip(hits, objects):
                if obj_idx is None:
                    continue
                subj_idx = next(
                    (i for i in range(len(bodies) - 1, -1, -1) if bodies[i][1] <= a_start and i not in consumed),
                    None,
                )
                if subj_idx is None or bodies[subj_idx][2] == bodies[obj_idx][2]:
                    continue
                text = _clean_claim_text(sentence[bodies[subj_idx][0] : bodies[obj_idx][1]])
                claims.append(
                    ParsedAspectClaim(
                        text=text, body_a=bodies[subj_idx][2], aspect=aspect, body_b=bodies[obj_idx][2]
                    )
                )
        for match in _PAIR_THEN_ASPECT.finditer(sentence):
            body_a = _canonical_body(match.group("body_a"))
            body_b = _canonical_body(match.group("body_b"))
            aspect = _canonical_aspect(match.group("aspect"))
            if body_a and body_b and aspect and body_a != body_b:
                claims.append(
                    ParsedAspectClaim(
                        text=_clean_claim_text(match.group(0)), body_a=body_a, aspect=aspect, body_b=body_b
                    )
                )
    return claims


def _station_claims(reading: str) -> list[ParsedStationClaim]:
    """Catch "stationary"/"standstill" and the noun/verb forms ("station",
    "stationed", "mid-station") that the agents actually use, binding each to the
    nearest body in the same sentence so the speed check can confirm or reject it."""
    claims: list[ParsedStationClaim] = []
    for sentence in _sentences(reading):
        candidates = [span for span in _body_spans(sentence) if span[2] not in _ANGLES]
        if not candidates:
            continue
        for match in _STATION_FINDER.finditer(sentence):
            trigger = (match.start() + match.end()) // 2
            nearest = min(candidates, key=lambda span: min(abs(span[0] - trigger), abs(span[1] - trigger)))
            claims.append(ParsedStationClaim(text=_clean_claim_text(match.group(0)), body=nearest[2]))
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
