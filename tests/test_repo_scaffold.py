from pathlib import Path


def test_claude_stub_points_to_future_agents_brief():
    stub = Path("CLAUDE.md")

    assert stub.exists()
    text = stub.read_text(encoding="utf-8")
    assert "AGENTS.md" in text
    assert "chart brief" in text
