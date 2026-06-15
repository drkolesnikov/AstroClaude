from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

AspectName = Literal["conjunction", "opposition", "square", "trine", "sextile"]

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


class ChartComputationError(ValueError):
    """Raised when the chart brief cannot be computed without ambiguity."""


@dataclass(frozen=True)
class BirthData:
    date: str
    time: str
    place: str | None = None
    country_code: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    timezone: str | None = None


@dataclass(frozen=True)
class ChartSelection:
    layers: tuple[str, ...] = ("natal",)
    transit_date: str | None = None
    progression_date: str | None = None
    solar_arc_date: str | None = None
    solar_return_year: int | None = None
    include_optional_bodies: bool = False


@dataclass(frozen=True)
class ResolvedBirth:
    input_date: str
    input_time: str
    place: str
    country_code: str | None
    latitude: float
    longitude: float
    timezone: str
    local_datetime: str
    utc_datetime: str


@dataclass(frozen=True)
class BodyPosition:
    name: str
    longitude: float
    sign: str
    degree: float
    house: int
    speed: float | None


@dataclass(frozen=True)
class HouseCusp:
    house: int
    longitude: float
    sign: str
    degree: float


@dataclass(frozen=True)
class Aspect:
    body_a: str
    body_b: str
    aspect: str
    angle: float
    orb: float


@dataclass(frozen=True)
class Configuration:
    type: str
    bodies: list[str]
    details: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ChartFacts:
    aspects: frozenset[tuple[frozenset[str], AspectName]]
    speeds_by_body: dict[str, list[float]]


@dataclass(frozen=True)
class LayerBrief:
    name: str
    julian_day_ut: float
    bodies: list[BodyPosition]
    house_cusps: list[HouseCusp]
    aspects: list[Aspect]
    configurations: list[Configuration]


@dataclass(frozen=True)
class ChartBrief:
    zodiac: str
    house_system: str
    resolved_birth: ResolvedBirth
    layers: list[LayerBrief]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> ChartBrief:
        resolved_birth = ResolvedBirth(**_mapping(payload["resolved_birth"]))
        layers = [
            LayerBrief(
                name=layer["name"],
                julian_day_ut=layer["julian_day_ut"],
                bodies=[BodyPosition(**_mapping(body)) for body in _sequence(layer["bodies"])],
                house_cusps=[HouseCusp(**_mapping(cusp)) for cusp in _sequence(layer["house_cusps"])],
                aspects=[Aspect(**_mapping(aspect)) for aspect in _sequence(layer["aspects"])],
                configurations=[
                    Configuration(
                        type=configuration["type"],
                        bodies=list(_sequence(configuration["bodies"])),
                        details=dict(_mapping(configuration["details"])),
                    )
                    for configuration in _sequence(layer["configurations"])
                ],
            )
            for layer in (_mapping(item) for item in _sequence(payload["layers"]))
        ]
        return cls(
            zodiac=payload["zodiac"],
            house_system=payload["house_system"],
            resolved_birth=resolved_birth,
            layers=layers,
        )

    @property
    def facts(self) -> ChartFacts:
        aspects: set[tuple[frozenset[str], AspectName]] = set()
        speeds_by_body: dict[str, list[float]] = {}
        for layer in self.layers:
            for aspect in layer.aspects:
                canonical_aspect = canonical_aspect_name(aspect.aspect)
                if canonical_aspect:
                    aspects.add((frozenset((aspect.body_a, aspect.body_b)), canonical_aspect))
            for body in layer.bodies:
                if body.speed is not None:
                    speeds_by_body.setdefault(body.name, []).append(body.speed)
        return ChartFacts(aspects=frozenset(aspects), speeds_by_body=speeds_by_body)

    def to_markdown(self) -> str:
        lines = [
            "# Natal Chart Brief",
            "",
            f"- Zodiac: {self.zodiac}",
            f"- House system: {self.house_system}",
            f"- Birth place: {self.resolved_birth.place}, {self.resolved_birth.country_code or 'unknown'}",
            f"- Coordinates: {self.resolved_birth.latitude}, {self.resolved_birth.longitude}",
            f"- Timezone: {self.resolved_birth.timezone}",
            f"- Local birth time: {self.resolved_birth.local_datetime}",
            f"- UTC birth time: {self.resolved_birth.utc_datetime}",
            "",
        ]

        for layer in self.layers:
            layer_title = layer.name.replace("_", " ").title()
            lines.extend(
                [
                    f"## {layer_title} Layer",
                    "",
                    f"- Julian day UT: {layer.julian_day_ut}",
                    "",
                    "### Bodies",
                    "",
                    "| Body | Sign | Degree | House | Longitude | Speed |",
                    "| --- | --- | ---: | ---: | ---: | ---: |",
                ]
            )
            for body in layer.bodies:
                speed = "" if body.speed is None else f"{body.speed:.4f}"
                lines.append(
                    f"| {body.name} | {body.sign} | {body.degree:.4f} | {body.house} | "
                    f"{body.longitude:.4f} | {speed} |"
                )

            lines.extend(
                [
                    "",
                    "### House Cusps",
                    "",
                    "| House | Sign | Degree | Longitude |",
                    "| ---: | --- | ---: | ---: |",
                ]
            )
            for cusp in layer.house_cusps:
                lines.append(f"| {cusp.house} | {cusp.sign} | {cusp.degree:.4f} | {cusp.longitude:.4f} |")

            lines.extend(
                [
                    "",
                    "### Aspects",
                    "",
                    "| Body A | Aspect | Body B | Orb |",
                    "| --- | --- | --- | ---: |",
                ]
            )
            for aspect in layer.aspects:
                lines.append(f"| {aspect.body_a} | {aspect.aspect} | {aspect.body_b} | {aspect.orb:.4f} |")

            lines.extend(
                [
                    "",
                    "### Configurations",
                    "",
                ]
            )
            if layer.configurations:
                for configuration in layer.configurations:
                    bodies = ", ".join(configuration.bodies)
                    lines.append(f"- {configuration.type}: {bodies}")
            else:
                lines.append("- None detected")
            lines.append("")

        return "\n".join(lines).rstrip() + "\n"


def canonical_aspect_name(value: str) -> AspectName | None:
    return ASPECT_ALIASES.get(value.strip().casefold())


def _mapping(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError("expected a mapping while reconstructing ChartBrief")
    return value


def _sequence(value: object) -> list[Any]:
    if not isinstance(value, list):
        raise TypeError("expected a list while reconstructing ChartBrief")
    return value
