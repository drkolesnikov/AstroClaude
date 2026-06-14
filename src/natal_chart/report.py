from __future__ import annotations

import html
import json
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


@dataclass(frozen=True)
class ReportPage:
    page_id: str
    title: str
    subtitle: str
    html_body: str


def render_report(run_dir: str | Path) -> Path:
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
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=EB+Garamond:wght@400;500;600&display=swap" rel="stylesheet">
<style>{_css()}</style>
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


def _chart_tables(chart_brief: dict[str, Any]) -> str:
    sections = []
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
  --display: 'Cormorant Garamond', Georgia, serif;
  --body: 'EB Garamond', Georgia, serif;
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
.brand-kicker { color: var(--gold); font: 700 11px/1 var(--ui); letter-spacing: .24em; text-transform: uppercase; }
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
  font: 700 10px/1 var(--ui); letter-spacing: .08em; text-transform: uppercase;
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
.nav-link span { width: 18px; color: var(--gold); text-align: center; }
.main { margin-left: 292px; width: calc(100% - 292px); }
.topbar { display: none; }
.cover-note { max-width: 860px; margin: 0 auto; padding: 46px 42px 0; }
.run-badges { margin-bottom: 12px; }
.report-page { display: none; max-width: 860px; margin: 0 auto; padding: 42px 42px 92px; }
.report-page.active { display: block; }
.page-header { margin: 0 0 30px; border-bottom: 1px solid var(--line); padding-bottom: 24px; }
.page-glyph {
  width: 56px; height: 56px; display: grid; place-items: center; border-radius: 50%;
  border: 1px solid var(--gold); color: var(--gold); background: var(--paper); font-size: 28px;
}
.page-header p { margin: 16px 0 6px; color: var(--gold); font: 700 11px/1 var(--ui); letter-spacing: .18em; text-transform: uppercase; }
.page-header h2 { margin: 0; font: 600 54px/1 var(--display); }
.prose { background: var(--paper); border: 1px solid var(--line); padding: 34px; font-size: 20px; line-height: 1.72; }
.prose h1, .prose h2, .prose h3 { font-family: var(--display); line-height: 1.08; }
.prose h1 { font-size: 42px; }
.prose h2 { font-size: 32px; }
.prose h3 { font-size: 25px; }
.prose blockquote { border-left: 3px solid var(--gold); margin: 24px 0; padding: 4px 0 4px 22px; color: var(--muted); font-style: italic; }
.prose table { width: 100%; border-collapse: collapse; margin: 20px 0; font: 14px/1.35 var(--ui); }
.prose th { color: #8b662e; text-align: left; text-transform: uppercase; letter-spacing: .08em; font-size: 11px; border-bottom: 2px solid var(--gold); padding: 9px; }
.prose td { border-bottom: 1px solid var(--line); padding: 9px; }
.prose hr { border: 0; height: 1px; background: linear-gradient(90deg, transparent, var(--line), transparent); margin: 32px 0; }
.pager { display: flex; justify-content: space-between; gap: 20px; margin-top: 28px; }
.pager button {
  border: 1px solid var(--line); background: var(--paper); color: var(--muted); padding: 10px 14px;
  font: 700 12px/1 var(--ui); cursor: pointer;
}
.pager button:hover { color: var(--ink); border-color: var(--gold); }
@media (max-width: 760px) {
  .app-shell { display: block; }
  .sidebar { transform: translateX(-100%); transition: transform .2s ease; z-index: 4; width: 280px; }
  .sidebar.open { transform: translateX(0); }
  .main { width: 100%; margin-left: 0; }
  .topbar {
    display: flex; gap: 12px; align-items: center; position: sticky; top: 0; z-index: 3;
    padding: 12px 16px; color: white; background: var(--night);
  }
  .menu-button { border: 0; background: transparent; color: var(--gold); font-size: 22px; }
  .cover-note, .report-page { padding: 24px 18px 70px; }
  .page-header h2 { font-size: 38px; }
  .prose { padding: 22px; font-size: 18px; }
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
