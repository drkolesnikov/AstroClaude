import argparse
import json

from natal_chart.compute import compute_chart
from natal_chart.models import BirthData, ChartComputationError


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute a deterministic natal chart brief.")
    parser.add_argument("--date", required=True, help="Birth date, YYYY-MM-DD.")
    parser.add_argument("--time", required=True, help="Exact local birth time, HH:MM or HH:MM:SS.")
    parser.add_argument("--place", help="Birth city/place name.")
    parser.add_argument("--country-code", help="ISO 3166-1 alpha-2 country code for place disambiguation.")
    parser.add_argument("--latitude", type=float, help="Birth latitude in decimal degrees.")
    parser.add_argument("--longitude", type=float, help="Birth longitude in decimal degrees.")
    parser.add_argument("--timezone", help="IANA timezone name; optional when place or coordinates can resolve it.")
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="Output format.",
    )
    args = parser.parse_args()

    try:
        brief = compute_chart(
            BirthData(
                date=args.date,
                time=args.time,
                place=args.place,
                country_code=args.country_code,
                latitude=args.latitude,
                longitude=args.longitude,
                timezone=args.timezone,
            )
        )
    except ChartComputationError as exc:
        parser.error(str(exc))

    if args.format == "markdown":
        print(brief.to_markdown())
    else:
        print(json.dumps(brief.to_dict(), indent=2, ensure_ascii=False))
