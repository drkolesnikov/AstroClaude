from pathlib import Path

ROSTER = [
    "ego",
    "persona",
    "shadow",
    "anima-animus",
    "parental",
    "wound",
    "vocation",
    "eros",
    "numinous",
]


def test_all_nine_structure_charters_exist_with_a_charter_question():
    agents = Path("agents")
    for slug in ROSTER:
        charter = agents / f"{slug}.md"
        assert charter.exists(), f"missing charter: {slug}"
        assert "## Your charter" in charter.read_text(encoding="utf-8"), f"{slug}: no charter question"


def test_anima_charter_is_read_fluidly_without_requiring_gender():
    # ADR-0004: the soul-image is contrasexual and fluid, never assigned by sex.
    text = (Path("agents") / "anima-animus.md").read_text(encoding="utf-8")
    assert "fluid" in text.lower()
