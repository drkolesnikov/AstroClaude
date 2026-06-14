from __future__ import annotations

import argparse
from pathlib import Path

from natal_chart.report import render_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a completed natal-chart run as an HTML report.")
    parser.add_argument("run_dir", type=Path, help="Run directory containing provenance, chart brief, and readings.")
    args = parser.parse_args()

    path = render_report(args.run_dir)
    print(path)


if __name__ == "__main__":
    main()
