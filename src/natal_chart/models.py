from __future__ import annotations

from dataclasses import asdict, dataclass, field


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
