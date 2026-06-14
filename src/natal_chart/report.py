"""Offline-portable HTML report renderer.

render_report writes a self-contained ``report/index.html`` with display, body,
and symbol fonts inlined as data URLs. If an offline font cannot be found, the
tool fails loudly instead of falling back to default serif or colour-emoji
rendering.
"""

from __future__ import annotations

import base64
import html
import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import markdown

STRUCTURE_TITLES = {
    "ego": "Ego",
    "persona": "Persona",
    "shadow": "Shadow",
    "anima-animus": "Anima / Animus",
    "parental": "Parental Complexes",
    "wound": "The Wound",
    "vocation": "Vocation / Telos",
    "eros": "Eros / Relating",
    "numinous": "Numinous / Transpersonal",
}

PAGE_GLYPHS = {
    "portrait": "☉",
    "critic": "⚖",
    "chart": "⊕",
    "ego": "☉",
    "persona": "♌",
    "shadow": "♇",
    "anima-animus": "☽",
    "parental": "♄",
    "wound": "⚷",
    "vocation": "☊",
    "eros": "♀",
    "numinous": "♆",
}

WHEEL_SIZE = 640
WHEEL_CENTER = WHEEL_SIZE / 2
WHEEL_RADII = {
    "sign_outer": 296,
    "sign_inner": 252,
    "sign_label": 274,
    "house_outer": 246,
    "house_inner": 176,
    "house_label": 196,
    "body_tick": 222,
    "body_glyph": 206,
    "aspect": 118,
}

SIGN_DEFS = [
    ("Aries", "♈", "fire", 0),
    ("Taurus", "♉", "earth", 30),
    ("Gemini", "♊", "air", 60),
    ("Cancer", "♋", "water", 90),
    ("Leo", "♌", "fire", 120),
    ("Virgo", "♍", "earth", 150),
    ("Libra", "♎", "air", 180),
    ("Scorpio", "♏", "water", 210),
    ("Sagittarius", "♐", "fire", 240),
    ("Capricorn", "♑", "earth", 270),
    ("Aquarius", "♒", "air", 300),
    ("Pisces", "♓", "water", 330),
]

BODY_GLYPHS = {
    "Sun": "☉",
    "Moon": "☽",
    "Mercury": "☿",
    "Venus": "♀",
    "Mars": "♂",
    "Jupiter": "♃",
    "Saturn": "♄",
    "Uranus": "♅",
    "Neptune": "♆",
    "Pluto": "♇",
    "Chiron": "⚷",
    "North Node": "☊",
    "South Node": "☋",
    "Ascendant": "ASC",
    "Descendant": "DSC",
    "Midheaven": "MC",
    "Imum Coeli": "IC",
}

ANGLE_LABELS = {
    "Ascendant": ("ASC", "asc"),
    "Descendant": ("DSC", "dsc"),
    "Midheaven": ("MC", "mc"),
    "IC": ("IC", "ic"),
}

REPORT_FONT_SPECS = [
    (
        "NatalReportDisplay",
        "NATAL_REPORT_DISPLAY_FONT",
        [
            Path("/System/Library/Fonts/Supplemental/Georgia.ttf"),
            Path("/System/Library/Fonts/Palatino.ttc"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"),
            Path("/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf"),
            Path("C:/Windows/Fonts/georgia.ttf"),
        ],
    ),
    (
        "NatalReportBody",
        "NATAL_REPORT_BODY_FONT",
        [
            Path("/System/Library/Fonts/Supplemental/Times New Roman.ttf"),
            Path("/System/Library/Fonts/Supplemental/Georgia.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"),
            Path("/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf"),
            Path("C:/Windows/Fonts/times.ttf"),
        ],
    ),
    (
        "NatalReportSymbols",
        "NATAL_REPORT_SYMBOL_FONT",
        [
            Path("/System/Library/Fonts/Apple Symbols.ttf"),
            Path("/System/Library/Fonts/Symbol.ttf"),
            Path("/usr/share/fonts/truetype/noto/NotoSansSymbols2-Regular.ttf"),
            Path("/usr/share/fonts/truetype/noto/NotoSansSymbols-Regular.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("C:/Windows/Fonts/seguisym.ttf"),
        ],
    ),
]


@dataclass(frozen=True)
class ReportPage:
    page_id: str
    title: str
    subtitle: str
    html_body: str


def render_report(run_dir: str | Path) -> Path:
    """Render an offline-portable, self-contained HTML dossier for a completed run."""
    run_dir = Path(run_dir)
    provenance = _read_json(run_dir / "provenance.json")
    chart_brief = _read_json(run_dir / "chart-brief.json")
    report_dir = run_dir / "report"
    report_dir.mkdir(parents=True, exist_ok=True)

    pages = _report_pages(run_dir, provenance, chart_brief)
    html_text = _document_html(provenance=provenance, chart_brief=chart_brief, pages=pages)
    output_path = report_dir / "index.html"
    output_path.write_text(html_text, encoding="utf-8")
    return output_path


def _report_pages(run_dir: Path, provenance: dict[str, Any], chart_brief: dict[str, Any]) -> list[ReportPage]:
    native = _display_native(str(provenance["native"]))
    pages = [
        ReportPage(
            page_id="portrait",
            title="Individuation Portrait",
            subtitle=f"{native} · holistic synthesis",
            html_body=_markdown_file(run_dir / "interpretation.md"),
        )
    ]
    for slug in provenance["structures"]:
        title = STRUCTURE_TITLES.get(slug, _display_native(slug))
        pages.append(
            ReportPage(
                page_id=slug,
                title=title,
                subtitle="Structure reading",
                html_body=_markdown_file(run_dir / "structure" / f"{slug}.md"),
            )
        )
    pages.extend(
        [
            ReportPage(
                page_id="critic",
                title="Depth-Critic",
                subtitle="Grounding and falsifiability challenges",
                html_body=_markdown_file(run_dir / "critic.md"),
            ),
            ReportPage(
                page_id="chart",
                title="Chart Brief",
                subtitle="Deterministic ground truth tables",
                html_body=_chart_tables(chart_brief),
            ),
        ]
    )
    return pages


def _document_html(
    *,
    provenance: dict[str, Any],
    chart_brief: dict[str, Any],
    pages: list[ReportPage],
) -> str:
    native = _display_native(str(provenance["native"]))
    resolved = chart_brief["resolved_birth"]
    badges = _run_badges(provenance)
    glance = _at_a_glance(chart_brief)
    nav = _nav_html(pages)
    page_sections = "\n".join(_page_html(index, page, pages) for index, page in enumerate(pages))
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_e(native)} · Natal Chart Dossier</title>
<style>{_font_faces_css()}{_css()}</style>
</head>
<body>
<div class="app-shell">
  <aside class="sidebar">
    <div class="brand">
      <div class="brand-kicker">Natal Chart Dossier</div>
      <div class="monogram" aria-hidden="true">{_e(_monogram(native))}</div>
      <h1>{_e(native)}</h1>
      <p>{_e(resolved["place"])}, {_e(resolved.get("country_code") or "unknown")}</p>
      <p>{_e(resolved["local_datetime"])}<br>{_e(resolved["utc_datetime"])}<br>{_e(str(resolved["latitude"]))}, {_e(str(resolved["longitude"]))}<br>{_e(resolved["timezone"])}</p>
    </div>
    <div class="badges">{badges}</div>
    <nav class="nav" aria-label="Report pages">{nav}</nav>
  </aside>
  <main class="main">
    <header class="topbar">
      <button class="menu-button" type="button" aria-label="Toggle navigation" onclick="toggleSidebar()">☰</button>
      <strong>{_e(native)}</strong>
    </header>
    <section class="cover-note">
      <div class="run-badges">{badges}</div>
      <div class="glance">{glance}</div>
    </section>
    {page_sections}
  </main>
</div>
<script>{_js()}</script>
</body>
</html>
"""


def _page_html(index: int, page: ReportPage, pages: list[ReportPage]) -> str:
    previous_page = pages[index - 1] if index > 0 else None
    next_page = pages[index + 1] if index < len(pages) - 1 else None
    previous_link = (
        f'<button type="button" onclick="showPage(\'{previous_page.page_id}\')">← {_e(previous_page.title)}</button>'
        if previous_page
        else "<span></span>"
    )
    next_link = (
        f'<button type="button" onclick="showPage(\'{next_page.page_id}\')">{_e(next_page.title)} →</button>'
        if next_page
        else "<span></span>"
    )
    active = " active" if index == 0 else ""
    return f"""
<article class="report-page{active}" id="page-{_e(page.page_id)}" data-page="{_e(page.page_id)}">
  <header class="page-header">
    <div class="page-glyph">{_e(PAGE_GLYPHS.get(page.page_id, "✦"))}</div>
    <p>{_e(page.subtitle)}</p>
    <h2>{_e(page.title)}</h2>
  </header>
  <div class="prose">{page.html_body}</div>
  <footer class="pager">{previous_link}{next_link}</footer>
</article>
"""


def _nav_html(pages: list[ReportPage]) -> str:
    links = []
    for index, page in enumerate(pages):
        active = " active" if index == 0 else ""
        links.append(
            f'<button class="nav-link{active}" type="button" data-target="{_e(page.page_id)}" '
            f'onclick="showPage(\'{_e(page.page_id)}\')">'
            f'<span>{_e(PAGE_GLYPHS.get(page.page_id, "✦"))}</span>{_e(page.title)}</button>'
        )
    return "\n".join(links)


def _run_badges(provenance: dict[str, Any]) -> str:
    values = [
        str(provenance["run_mode"]),
        ", ".join(provenance["selection"]),
        *[str(value) for value in provenance.get("models", {}).values()],
        f"seed {provenance.get('seed')}" if provenance.get("seed") is not None else None,
        str(provenance["revision"]),
    ]
    return "".join(f'<span class="badge">{_e(value)}</span>' for value in values if value)


def _at_a_glance(chart_brief: dict[str, Any]) -> str:
    natal = _primary_layer(chart_brief)
    bodies = {body["name"]: body for body in natal.get("bodies", [])}
    chips = []
    for name in ("Sun", "Moon", "Ascendant", "Midheaven"):
        body = bodies.get(name)
        if body:
            chips.append(f"{name}: {body['sign']}, house {body['house']}")
    for configuration in natal.get("configurations", []):
        bodies_text = ", ".join(configuration.get("bodies", []))
        chips.append(f"{configuration['type']}: {bodies_text}")
    return "".join(f'<span class="chip">{_e(chip)}</span>' for chip in chips)


def chart_wheel_geometry(chart_brief: dict[str, Any]) -> dict[str, Any]:
    natal = _primary_layer(chart_brief)
    bodies = natal.get("bodies", [])
    house_cusps = natal.get("house_cusps", [])
    ascendant_longitude = _body_longitude("Ascendant", bodies, house_cusps, fallback_house=1)
    midheaven_longitude = _body_longitude("Midheaven", bodies, house_cusps, fallback_house=10)

    angles = {
        "Ascendant": ascendant_longitude,
        "Descendant": (ascendant_longitude + 180) % 360,
        "Midheaven": midheaven_longitude,
        "IC": (midheaven_longitude + 180) % 360,
    }
    geometry = {
        "size": WHEEL_SIZE,
        "center": {"x": WHEEL_CENTER, "y": WHEEL_CENTER},
        "ascendant_longitude": ascendant_longitude,
        "angles": {
            name: {
                "longitude": longitude,
                "screen_angle": _round(_screen_angle(longitude, ascendant_longitude)),
                **_point(_screen_angle(longitude, ascendant_longitude), WHEEL_RADII["house_outer"]),
            }
            for name, longitude in angles.items()
        },
        "signs": _sign_geometry(ascendant_longitude),
        "houses": _house_geometry(house_cusps, ascendant_longitude),
        "aspects": _aspect_geometry(natal.get("aspects", []), bodies, ascendant_longitude),
        "bodies": _body_geometry(bodies, ascendant_longitude),
    }
    return geometry


def _chart_tables(chart_brief: dict[str, Any]) -> str:
    sections = [_chart_wheel(chart_brief)]
    for layer in chart_brief.get("layers", []):
        title = str(layer["name"]).replace("_", " ").title()
        sections.append(f"<h3>{_e(title)} Layer</h3>")
        sections.append(_table(["Body", "Sign", "Degree", "House", "Longitude", "Speed"], layer.get("bodies", [])))
        sections.append(_table(["House", "Sign", "Degree", "Longitude"], layer.get("house_cusps", [])))
        sections.append(_table(["Body A", "Aspect", "Body B", "Orb"], layer.get("aspects", [])))
        configurations = layer.get("configurations", [])
        if configurations:
            items = "".join(
                f"<li>{_e(item['type'])}: {_e(', '.join(item.get('bodies', [])))}</li>"
                for item in configurations
            )
            sections.append(f"<h4>Configurations</h4><ul>{items}</ul>")
    return "\n".join(sections)


def _chart_wheel(chart_brief: dict[str, Any]) -> str:
    geometry = chart_wheel_geometry(chart_brief)
    center = geometry["center"]
    svg_parts = [
        '<svg class="wheel-svg" viewBox="0 0 640 640" role="img" aria-label="Natal chart wheel">',
        '<circle class="wheel-background" cx="320" cy="320" r="302"></circle>',
    ]
    for sign in geometry["signs"]:
        svg_parts.append(
            f'<path class="sign-sector sign-{_e(sign["element"])}" data-sign="{_e(sign["name"])}" '
            f'd="{_e(sign["path"])}"></path>'
        )
    svg_parts.append('<circle class="house-ring" cx="320" cy="320" r="246"></circle>')
    svg_parts.append('<circle class="aspect-hub" cx="320" cy="320" r="118"></circle>')
    for house in geometry["houses"]:
        svg_parts.append(
            '<line class="house-cusp" '
            f'data-house="{house["house"]}" x1="{_fmt(house["inner_x"])}" y1="{_fmt(house["inner_y"])}" '
            f'x2="{_fmt(house["outer_x"])}" y2="{_fmt(house["outer_y"])}"></line>'
        )
        svg_parts.append(
            f'<text class="house-number" x="{_fmt(house["label_x"])}" y="{_fmt(house["label_y"])}">'
            f'{house["house"]}</text>'
        )
    for name, angle in geometry["angles"].items():
        label, class_name = ANGLE_LABELS[name]
        svg_parts.append(
            f'<line class="angle-axis angle-{class_name}" x1="{_fmt(center["x"])}" y1="{_fmt(center["y"])}" '
            f'x2="{_fmt(angle["x"])}" y2="{_fmt(angle["y"])}"></line>'
        )
        label_point = _point(angle["screen_angle"], WHEEL_RADII["house_outer"] + 20)
        svg_parts.append(
            f'<text class="angle-label angle-{class_name}-label" x="{_fmt(label_point["x"])}" '
            f'y="{_fmt(label_point["y"])}">{label}</text>'
        )
    for aspect in geometry["aspects"]:
        svg_parts.append(
            f'<line class="aspect-line aspect-{_e(aspect["class_name"])}" '
            f'data-aspect="{_e(aspect["aspect"])}" x1="{_fmt(aspect["x1"])}" y1="{_fmt(aspect["y1"])}" '
            f'x2="{_fmt(aspect["x2"])}" y2="{_fmt(aspect["y2"])}"></line>'
        )
    for body in geometry["bodies"]:
        if body["connector"]:
            svg_parts.append(
                f'<line class="body-connector" data-body="{_e(body["name"])}" '
                f'x1="{_fmt(body["tick_x"])}" y1="{_fmt(body["tick_y"])}" '
                f'x2="{_fmt(body["glyph_x"])}" y2="{_fmt(body["glyph_y"])}"></line>'
            )
        svg_parts.append(
            f'<circle class="body-tick" data-body="{_e(body["name"])}" '
            f'cx="{_fmt(body["tick_x"])}" cy="{_fmt(body["tick_y"])}" r="3.4"></circle>'
        )
    svg_parts.append("</svg>")

    overlays = []
    for sign in geometry["signs"]:
        overlays.append(
            '<div class="glyph-overlay sign-symbol" '
            f'aria-label="{_e(sign["name"])}" style="--x: {_percent(sign["glyph_x"])}; --y: {_percent(sign["glyph_y"])};">'
            f'{_symbol(sign["glyph"])}</div>'
        )
    for body in geometry["bodies"]:
        retrograde = '<span class="retrograde">R</span>' if body["retrograde"] else ""
        overlays.append(
            '<div class="glyph-overlay planet-symbol" '
            f'data-body="{_e(body["name"])}" aria-label="{_e(body["name"])} {_e(_degree_label(body["degree"]))}" '
            f'style="--x: {_percent(body["glyph_x"])}; --y: {_percent(body["glyph_y"])};">'
            f'<span class="planet-glyph">{_symbol(body["glyph"])}</span>'
            f'<span class="degree-label">{_e(_degree_label(body["degree"]))}{retrograde}</span>'
            "</div>"
        )
    return (
        '<section class="chart-wheel-frame">'
        '<div class="wheel-plot">'
        + "".join(svg_parts)
        + '<div class="glyph-layer">'
        + "".join(overlays)
        + "</div></div>"
        "</section>"
    )


def _sign_geometry(ascendant_longitude: float) -> list[dict[str, Any]]:
    signs = []
    for name, glyph, element, start in SIGN_DEFS:
        end = (start + 30) % 360
        label_point = _point(_screen_angle(start + 15, ascendant_longitude), WHEEL_RADII["sign_label"])
        signs.append(
            {
                "name": name,
                "glyph": glyph,
                "element": element,
                "start_longitude": start,
                "end_longitude": end,
                "path": _donut_sector_path(start, start + 30, ascendant_longitude),
                "glyph_x": label_point["x"],
                "glyph_y": label_point["y"],
            }
        )
    return signs


def _house_geometry(house_cusps: list[dict[str, Any]], ascendant_longitude: float) -> list[dict[str, Any]]:
    if not house_cusps:
        return []
    ordered = sorted(house_cusps, key=lambda cusp: int(cusp["house"]))
    houses = []
    for index, cusp in enumerate(ordered):
        longitude = float(cusp["longitude"])
        angle = _screen_angle(longitude, ascendant_longitude)
        inner = _point(angle, WHEEL_RADII["house_inner"])
        outer = _point(angle, WHEEL_RADII["house_outer"])
        next_longitude = float(ordered[(index + 1) % len(ordered)]["longitude"])
        span = (next_longitude - longitude) % 360
        if len(ordered) == 1 or span == 0:
            span = 30
        label = _point(_screen_angle(longitude + span / 2, ascendant_longitude), WHEEL_RADII["house_label"])
        houses.append(
            {
                "house": int(cusp["house"]),
                "longitude": longitude,
                "screen_angle": _round(angle),
                "inner_x": inner["x"],
                "inner_y": inner["y"],
                "outer_x": outer["x"],
                "outer_y": outer["y"],
                "label_x": label["x"],
                "label_y": label["y"],
            }
        )
    return houses


def _aspect_geometry(
    aspects: list[dict[str, Any]],
    bodies: list[dict[str, Any]],
    ascendant_longitude: float,
) -> list[dict[str, Any]]:
    body_by_name = {body["name"]: body for body in bodies}
    lines = []
    for aspect in aspects:
        body_a = body_by_name.get(aspect.get("body_a"))
        body_b = body_by_name.get(aspect.get("body_b"))
        if not body_a or not body_b:
            continue
        start = _point(_screen_angle(float(body_a["longitude"]), ascendant_longitude), WHEEL_RADII["aspect"])
        end = _point(_screen_angle(float(body_b["longitude"]), ascendant_longitude), WHEEL_RADII["aspect"])
        aspect_name = str(aspect["aspect"])
        lines.append(
            {
                "aspect": aspect_name,
                "class_name": _class_name(aspect_name),
                "x1": start["x"],
                "y1": start["y"],
                "x2": end["x"],
                "y2": end["y"],
            }
        )
    return lines


def _body_geometry(bodies: list[dict[str, Any]], ascendant_longitude: float) -> list[dict[str, Any]]:
    clusters = _body_clusters(bodies)
    plotted = []
    for cluster in clusters:
        offsets = _radius_offsets(len(cluster))
        for body, offset in zip(cluster, offsets, strict=True):
            longitude = float(body["longitude"])
            screen_angle = _screen_angle(longitude, ascendant_longitude)
            tick = _point(screen_angle, WHEEL_RADII["body_tick"])
            glyph = _point(screen_angle, WHEEL_RADII["body_glyph"] + offset)
            speed = body.get("speed")
            plotted.append(
                {
                    "name": str(body["name"]),
                    "glyph": BODY_GLYPHS.get(str(body["name"]), str(body["name"])[:2].upper()),
                    "longitude": longitude,
                    "degree": float(body.get("degree", longitude % 30)),
                    "screen_angle": _round(screen_angle),
                    "tick_x": tick["x"],
                    "tick_y": tick["y"],
                    "glyph_x": glyph["x"],
                    "glyph_y": glyph["y"],
                    "connector": len(cluster) > 1 or offset != 0,
                    "retrograde": isinstance(speed, (float, int)) and speed < 0,
                }
            )
    return sorted(plotted, key=lambda body: body["name"])


def _body_clusters(bodies: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    if not bodies:
        return []
    ordered = sorted(bodies, key=lambda body: float(body["longitude"]) % 360)
    clusters: list[list[dict[str, Any]]] = [[ordered[0]]]
    for body in ordered[1:]:
        previous = clusters[-1][-1]
        if _zodiac_distance(float(previous["longitude"]), float(body["longitude"])) <= 8:
            clusters[-1].append(body)
        else:
            clusters.append([body])
    if len(clusters) > 1 and _zodiac_distance(float(clusters[0][0]["longitude"]), float(clusters[-1][-1]["longitude"])) <= 8:
        clusters[0] = clusters[-1] + clusters[0]
        clusters.pop()
    return clusters


def _radius_offsets(count: int) -> list[float]:
    if count <= 1:
        return [0]
    midpoint = (count - 1) / 2
    return [(index - midpoint) * 30 for index in range(count)]


def _body_longitude(
    name: str,
    bodies: list[dict[str, Any]],
    house_cusps: list[dict[str, Any]],
    *,
    fallback_house: int,
) -> float:
    aliases = {
        "Ascendant": {"ascendant", "asc"},
        "Midheaven": {"midheaven", "mc"},
    }
    accepted = aliases.get(name, {name.lower()})
    for body in bodies:
        if str(body.get("name", "")).lower() in accepted:
            return float(body["longitude"])
    for cusp in house_cusps:
        if int(cusp["house"]) == fallback_house:
            return float(cusp["longitude"])
    raise ValueError(f"chart brief is missing {name} longitude")


def _screen_angle(longitude: float, ascendant_longitude: float) -> float:
    return (ascendant_longitude + 180 - longitude) % 360


def _point(screen_angle: float, radius: float) -> dict[str, float]:
    radians = math.radians(screen_angle)
    return {
        "x": _round(WHEEL_CENTER + math.cos(radians) * radius),
        "y": _round(WHEEL_CENTER + math.sin(radians) * radius),
    }


def _donut_sector_path(start_longitude: float, end_longitude: float, ascendant_longitude: float) -> str:
    start_angle = _screen_angle(start_longitude, ascendant_longitude)
    end_angle = _screen_angle(end_longitude, ascendant_longitude)
    start_outer = _point(start_angle, WHEEL_RADII["sign_outer"])
    end_outer = _point(end_angle, WHEEL_RADII["sign_outer"])
    end_inner = _point(end_angle, WHEEL_RADII["sign_inner"])
    start_inner = _point(start_angle, WHEEL_RADII["sign_inner"])
    arc_size = (end_longitude - start_longitude) % 360
    large_arc = 1 if arc_size > 180 else 0
    return (
        f"M {_fmt(start_outer['x'])} {_fmt(start_outer['y'])} "
        f"A {WHEEL_RADII['sign_outer']} {WHEEL_RADII['sign_outer']} 0 {large_arc} 0 "
        f"{_fmt(end_outer['x'])} {_fmt(end_outer['y'])} "
        f"L {_fmt(end_inner['x'])} {_fmt(end_inner['y'])} "
        f"A {WHEEL_RADII['sign_inner']} {WHEEL_RADII['sign_inner']} 0 {large_arc} 1 "
        f"{_fmt(start_inner['x'])} {_fmt(start_inner['y'])} Z"
    )


def _zodiac_distance(a: float, b: float) -> float:
    distance = abs((a - b) % 360)
    return min(distance, 360 - distance)


def _round(value: float) -> float:
    return round(value, 3)


def _fmt(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _percent(value: float) -> str:
    return f"{value / WHEEL_SIZE * 100:.4f}%"


def _symbol(glyph: str) -> str:
    text = glyph + "\ufe0e" if len(glyph) == 1 else glyph
    return _e(text)


def _degree_label(value: float) -> str:
    return f"{_fmt(round(value, 1))}°"


def _class_name(value: str) -> str:
    return "".join(character if character.isalnum() else "-" for character in value.lower()).strip("-")


def _table(headers: list[str], rows: list[dict[str, Any]]) -> str:
    key_map = {
        "Body": "name",
        "Sign": "sign",
        "Degree": "degree",
        "House": "house",
        "Longitude": "longitude",
        "Speed": "speed",
        "Body A": "body_a",
        "Aspect": "aspect",
        "Body B": "body_b",
        "Orb": "orb",
    }
    header_html = "".join(f"<th>{_e(header)}</th>" for header in headers)
    body_rows = []
    for row in rows:
        cells = []
        for header in headers:
            value = row.get(key_map[header], "")
            if isinstance(value, float):
                value = f"{value:.4f}".rstrip("0").rstrip(".")
            cells.append(f"<td>{_e('' if value is None else str(value))}</td>")
        body_rows.append(f"<tr>{''.join(cells)}</tr>")
    return f"<table><thead><tr>{header_html}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"


def _markdown_file(path: Path) -> str:
    if not path.exists():
        return "<p>Missing artifact.</p>"
    return _markdown(path.read_text(encoding="utf-8"))


def _markdown(text: str) -> str:
    renderer = markdown.Markdown(extensions=["extra", "sane_lists", "smarty"])
    return renderer.convert(text)


def _primary_layer(chart_brief: dict[str, Any]) -> dict[str, Any]:
    layers = chart_brief.get("layers", [])
    return next((layer for layer in layers if layer.get("name") == "natal"), layers[0] if layers else {})


def _display_native(native: str) -> str:
    return " ".join(part.capitalize() for part in native.replace("_", "-").split("-") if part)


def _monogram(name: str) -> str:
    parts = [part[0] for part in name.split() if part]
    return "".join(parts[:2]).upper()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _e(value: str) -> str:
    return html.escape(value, quote=True)


def _font_faces_css() -> str:
    faces = []
    for family, env_var, candidates in REPORT_FONT_SPECS:
        font_path = _resolve_report_font(env_var, candidates)
        encoded = base64.b64encode(font_path.read_bytes()).decode("ascii")
        mime_type, format_name = _font_data_type(font_path)
        faces.append(
            "@font-face { "
            f"font-family: '{family}'; "
            f"src: url(data:{mime_type};base64,{encoded}) format('{format_name}'); "
            "font-style: normal; font-weight: 400; font-display: block; "
            "}"
        )
    return "\n".join(faces) + "\n"


def _resolve_report_font(env_var: str, candidates: list[Path]) -> Path:
    override = os.environ.get(env_var)
    if override:
        path = Path(override).expanduser()
        if path.exists():
            return path
        raise FileNotFoundError(f"{env_var} points to a missing offline report font: {path}")
    for candidate in candidates:
        if candidate.exists():
            return candidate
    searched = ", ".join(str(candidate) for candidate in candidates)
    raise FileNotFoundError(f"Offline report font not found for {env_var}; searched {searched}")


def _font_data_type(path: Path) -> tuple[str, str]:
    suffix = path.suffix.lower()
    if suffix == ".otf":
        return "font/otf", "opentype"
    if suffix == ".ttc":
        return "font/collection", "truetype-collection"
    if suffix == ".woff":
        return "font/woff", "woff"
    if suffix == ".woff2":
        return "font/woff2", "woff2"
    return "font/ttf", "truetype"


def _css() -> str:
    return """
:root {
  --night: #0b102f;
  --night-2: #171d49;
  --gold: #b98b42;
  --ivory: #f6f0e4;
  --paper: #fffaf0;
  --ink: #2b2540;
  --muted: #6f6685;
  --line: #e4d8bf;
  --display: 'NatalReportDisplay';
  --body: 'NatalReportBody';
  --symbol: 'NatalReportSymbols';
  --ui: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--ivory); color: var(--ink); font-family: var(--body); }
.app-shell { min-height: 100vh; display: flex; }
.sidebar {
  position: fixed; inset: 0 auto 0 0; width: 292px; overflow: auto; padding: 28px 24px;
  color: #eee9fa; background: linear-gradient(155deg, var(--night), var(--night-2) 58%, #0d1235);
  border-right: 1px solid rgba(185, 139, 66, .36);
}
.brand-kicker { color: var(--gold); font: 700 11px/1 var(--ui); letter-spacing: 0; text-transform: uppercase; }
.brand h1 { font: 600 36px/1 var(--display); margin: 10px 0 8px; color: white; }
.brand p { margin: 8px 0; color: #c6bfdc; font: 12px/1.45 var(--ui); }
.monogram {
  width: 58px; height: 58px; display: grid; place-items: center; margin: 18px 0 8px;
  border: 1px solid rgba(185, 139, 66, .8); border-radius: 50%;
  font: 600 20px/1 var(--display); color: var(--gold);
}
.badges, .run-badges, .glance { display: flex; flex-wrap: wrap; gap: 8px; }
.badges { margin: 18px 0 24px; }
.badge, .chip {
  border: 1px solid rgba(185, 139, 66, .45); border-radius: 999px; padding: 6px 10px;
  font: 700 10px/1 var(--ui); letter-spacing: 0; text-transform: uppercase;
}
.badge { color: #d7b976; }
.chip { color: #5f5576; background: var(--paper); }
.nav { display: grid; gap: 5px; }
.nav-link {
  width: 100%; border: 0; border-left: 2px solid transparent; padding: 10px 8px;
  display: flex; align-items: center; gap: 10px; color: #d8d1e8; background: transparent;
  font: 13px/1.2 var(--ui); text-align: left; cursor: pointer;
}
.nav-link:hover, .nav-link.active { color: white; background: rgba(255,255,255,.06); border-left-color: var(--gold); }
.nav-link span { width: 18px; color: var(--gold); text-align: center; font-family: var(--symbol); font-variant-emoji: text; }
.main { margin-left: 292px; width: calc(100% - 292px); }
.topbar { display: none; }
.cover-note { max-width: 860px; margin: 0 auto; padding: 46px 42px 0; }
.run-badges { margin-bottom: 12px; }
.report-page { display: none; max-width: 860px; margin: 0 auto; padding: 42px 42px 92px; }
.report-page.active { display: block; }
.page-header { margin: 0 0 30px; border-bottom: 1px solid var(--line); padding-bottom: 24px; }
.page-glyph {
  width: 56px; height: 56px; display: grid; place-items: center; border-radius: 50%;
  border: 1px solid var(--gold); color: var(--gold); background: var(--paper); font: 28px/1 var(--symbol); font-variant-emoji: text;
}
.page-header p { margin: 16px 0 6px; color: var(--gold); font: 700 11px/1 var(--ui); letter-spacing: 0; text-transform: uppercase; }
.page-header h2 { margin: 0; font: 600 54px/1 var(--display); }
	.prose { background: var(--paper); border: 1px solid var(--line); padding: 34px; font-size: 20px; line-height: 1.72; }
	.prose h1, .prose h2, .prose h3 { font-family: var(--display); line-height: 1.08; }
	.prose h1 { font-size: 42px; }
	.prose h2 { font-size: 32px; }
	.prose h3 { font-size: 25px; }
	.prose blockquote { border-left: 3px solid var(--gold); margin: 24px 0; padding: 4px 0 4px 22px; color: var(--muted); font-style: italic; }
	.chart-wheel-frame { margin: 4px 0 34px; }
	.wheel-plot {
	  position: relative; width: min(100%, 640px); aspect-ratio: 1 / 1; margin: 0 auto 14px;
	}
	.wheel-svg { width: 100%; height: 100%; display: block; overflow: visible; }
	.wheel-background { fill: #fffdf7; stroke: var(--line); stroke-width: 1.2; }
	.sign-sector { stroke: #fffaf0; stroke-width: 1.4; }
	.sign-fire { fill: #f1d1bd; }
	.sign-earth { fill: #d9dfc8; }
	.sign-air { fill: #d5e4ec; }
	.sign-water { fill: #d8d3ec; }
	.house-ring, .aspect-hub {
	  fill: none; stroke: rgba(43, 37, 64, .18); stroke-width: 1.2;
	}
	.house-cusp { stroke: rgba(43, 37, 64, .42); stroke-width: 1; }
	.house-number, .angle-label {
	  fill: var(--muted); text-anchor: middle; dominant-baseline: central; font: 700 12px/1 var(--ui);
	}
	.angle-axis { stroke: var(--gold); stroke-width: 1.7; stroke-linecap: round; }
	.angle-dsc, .angle-ic { opacity: .62; }
	.aspect-line { stroke-width: 1.6; stroke-linecap: round; opacity: .7; }
	.aspect-conjunction { stroke: #6f6685; }
	.aspect-opposition, .aspect-square { stroke: #9b4f53; }
	.aspect-trine, .aspect-sextile { stroke: #4f7c7c; }
	.body-connector { stroke: rgba(43, 37, 64, .36); stroke-width: .9; stroke-dasharray: 3 4; }
	.body-tick { fill: var(--ink); stroke: var(--paper); stroke-width: 1; }
	.glyph-layer { position: absolute; inset: 0; pointer-events: none; }
	.glyph-overlay {
	  position: absolute; left: var(--x); top: var(--y); transform: translate(-50%, -50%);
	  color: var(--ink); text-align: center; white-space: nowrap; font-variant-emoji: text;
	  font-family: var(--symbol);
	}
	.sign-symbol { color: #4c435f; font-size: 20px; line-height: 1; }
	.planet-symbol {
	  min-width: 46px; display: grid; place-items: center; gap: 2px; padding: 2px 4px;
	  border-radius: 6px; background: rgba(255, 250, 240, .76);
	}
	.planet-glyph { font-size: 22px; line-height: 1; }
	.degree-label { color: var(--muted); font: 700 9px/1 var(--ui); }
	.retrograde { color: #9b4f53; margin-left: 2px; }
	.prose table { width: 100%; border-collapse: collapse; margin: 20px 0; font: 14px/1.35 var(--ui); }
	.prose th { color: #8b662e; text-align: left; text-transform: uppercase; letter-spacing: 0; font-size: 11px; border-bottom: 2px solid var(--gold); padding: 9px; }
	.prose td { border-bottom: 1px solid var(--line); padding: 9px; }
	.prose hr { border: 0; height: 1px; background: linear-gradient(90deg, transparent, var(--line), transparent); margin: 32px 0; }
.pager { display: flex; justify-content: space-between; gap: 20px; margin-top: 28px; }
.pager button {
  border: 1px solid var(--line); background: var(--paper); color: var(--muted); padding: 10px 14px;
  font: 700 12px/1 var(--ui); cursor: pointer;
}
.pager button:hover { color: var(--ink); border-color: var(--gold); }
	@media (max-width: 760px) {
	  html, body { overflow-x: hidden; }
	  .app-shell { display: block; }
	  .sidebar { transform: translateX(-100%); transition: transform .2s ease; z-index: 4; width: 280px; }
	  .sidebar.open { transform: translateX(0); }
	  .main { width: 100%; margin-left: 0; }
  .topbar {
    display: flex; gap: 12px; align-items: center; position: sticky; top: 0; z-index: 3;
    padding: 12px 16px; color: white; background: var(--night);
	  }
	  .menu-button { border: 0; background: transparent; color: var(--gold); font-size: 22px; }
	  .cover-note, .report-page { width: 100%; max-width: 100%; margin: 0; padding: 24px 18px 70px; }
	  .page-header h2 { font-size: 38px; }
	  .badge, .chip { max-width: 100%; white-space: normal; overflow-wrap: anywhere; line-height: 1.2; }
	  .prose { max-width: 100%; overflow-x: hidden; padding: 22px; font-size: 18px; }
	  .prose table { display: block; max-width: 100%; overflow-x: auto; }
	  .wheel-plot { width: min(250px, 100%); max-width: 250px; }
	  .planet-symbol { min-width: 30px; padding: 1px 2px; }
	  .planet-glyph { font-size: 18px; }
	  .sign-symbol { font-size: 18px; }
	}
	@media print {
	  @page { margin: 18mm 16mm; }
	  * { color-adjust: exact; print-color-adjust: exact; }
	  body { background: white; color: #1f1a30; }
	  .sidebar, .topbar, .cover-note, .pager { display: none !important; }
	  .app-shell, .main { display: block; width: 100%; min-height: auto; margin: 0; }
	  .report-page { display: block !important; max-width: none; margin: 0; padding: 0 0 16mm; page-break-before: always; break-before: page; }
	  .report-page:first-of-type { page-break-before: auto; break-before: auto; }
	  .page-header { margin-bottom: 12mm; break-after: avoid; page-break-after: avoid; }
	  .page-header h2 { font-size: 34px; }
	  .page-glyph { width: 42px; height: 42px; font-size: 22px; }
	  .prose { border: 0; background: white; padding: 0; font-size: 13pt; line-height: 1.45; }
	  .prose h1, .prose h2, .prose h3, .prose blockquote, .chart-wheel-frame { break-inside: avoid; page-break-inside: avoid; }
	  .chart-wheel-frame { max-width: 150mm; margin: 0 auto 10mm; }
	  .wheel-plot { max-width: 150mm; }
	  .prose table { break-inside: avoid; page-break-inside: avoid; font-size: 9pt; }
	}
	"""


def _js() -> str:
    return """
function showPage(pageId) {
  document.querySelectorAll('.report-page').forEach(page => {
    page.classList.toggle('active', page.dataset.page === pageId);
  });
  document.querySelectorAll('.nav-link').forEach(link => {
    link.classList.toggle('active', link.dataset.target === pageId);
  });
  history.replaceState(null, '', '#' + pageId);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}
function toggleSidebar() {
  document.querySelector('.sidebar').classList.toggle('open');
}
window.addEventListener('DOMContentLoaded', () => {
  const initial = location.hash ? location.hash.slice(1) : 'portrait';
  if (document.querySelector('[data-page="' + initial + '"]')) showPage(initial);
});
"""
