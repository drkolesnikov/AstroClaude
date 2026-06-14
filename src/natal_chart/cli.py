import argparse
import json

from natal_chart.compute import compute_chart
from natal_chart.models import BirthData, ChartComputationError, ChartSelection


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
        "--layers",
        default="natal",
        help=(
            "Comma-separated whole-layer selection: natal, transits, "
            "secondary_progressions, solar_arc, solar_return."
        ),
    )
    parser.add_argument("--transit-date", help="ISO date/datetime for the transits layer.")
    parser.add_argument("--progression-date", help="ISO date/datetime for the secondary_progressions layer.")
    parser.add_argument("--solar-arc-date", help="ISO date/datetime for the solar_arc layer.")
    parser.add_argument("--solar-return-year", type=int, help="Calendar year for the solar_return layer.")
    parser.add_argument(
        "--include-optional-bodies",
        action="store_true",
        help="Include Black Moon Lilith, Ceres, Pallas, Juno, Vesta, and Part of Fortune.",
    )
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
            ),
            selection=ChartSelection(
                layers=tuple(layer.strip() for layer in args.layers.split(",") if layer.strip()),
                transit_date=args.transit_date,
                progression_date=args.progression_date,
                solar_arc_date=args.solar_arc_date,
                solar_return_year=args.solar_return_year,
                include_optional_bodies=args.include_optional_bodies,
            ),
        )
    except ChartComputationError as exc:
        parser.error(str(exc))

    if args.format == "markdown":
        print(brief.to_markdown())
    else:
        print(json.dumps(brief.to_dict(), indent=2, ensure_ascii=False))
