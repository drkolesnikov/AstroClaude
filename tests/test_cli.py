import json
import sys

from natal_chart.cli import main


def test_cli_accepts_layer_selection_and_optional_bodies(monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "compute_chart",
            "--date",
            "1990-01-01",
            "--time",
            "12:00",
            "--place",
            "Moscow",
            "--country-code",
            "RU",
            "--layers",
            "transits",
            "--transit-date",
            "2026-06-14",
            "--include-optional-bodies",
        ],
    )

    main()

    data = json.loads(capsys.readouterr().out)
    assert [layer["name"] for layer in data["layers"]] == ["transits"]
    bodies = {body["name"] for body in data["layers"][0]["bodies"]}
    assert {"Black Moon Lilith", "Ceres", "Pallas", "Juno", "Vesta", "Part of Fortune"} <= bodies
