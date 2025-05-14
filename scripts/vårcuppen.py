"""Script for calculating scores for Vårcupen."""

from xlsxwriter import Workbook
from eventor.api import EventorAPI
import os
import argparse
from collections import defaultdict


def parse_args() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        argparse.Namespace: Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Download results and calculate scores for Vårcupen 2025"
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="Vårcupen2025.xlsx",
        help="Output file name (default: vårcupen2025.xlsx)",
    )
    parser.add_argument(
        "-t",
        "--token",
        type=str,
        default=os.getenv("EVENTOR_API_TOKEN"),
        help="API token (default: EVENTOR_API_TOKEN environment variable)",
    )
    parser.add_argument(
        "-s",
        "--start_date",
        type=str,
        default="2025-05-01",
        help="Start date for the results (default: 2025-05-01)",
    )
    parser.add_argument(
        "-e",
        "--end_date",
        type=str,
        default="2025-05-31",
        help="End date for the results (default: 2025-05-31)",
    )
    parser.add_argument(
        "-r",
        "--organisations",
        type=list[str],
        default=[
            "Falköping",
            "Tidaholm",
            "Mullsjö",
            "Gudhem",
        ],
        help=(
            "List of clubs to include in the results (default: "
            "['Falköping', 'Tidaholm', 'Mullsjö', 'Gudhem'])"
        ),
    )

    return parser.parse_args()


def get_cls_name(cls_name: str) -> str:
    """Take a name from Eventor and convert it into a name for the class"""
    cls_name = cls_name.lower()

    cols = ["grön", "vit", "gul", "orange", "blå"]
    dists = ["kort", "lång"]

    col = next((c for c in cols if c in cls_name), "")
    dist = next((d for d in dists if d in cls_name), "")
    age = "ungdom" if "ung" in cls_name else (
        "vuxen" if "vux" in cls_name else ""
    )
    return f"{col.capitalize()} {dist} {age}".strip()


def main() -> None:
    """Main function to download results and calculate scores for Vårcupen 2025.

    Will create an Excel file with the results.
    """
    args = parse_args()
    api = EventorAPI(args.token)
    # Get all organizations to filter on
    ids = [
        org.organisation_id
        for org in api.get_all_organizations()
        if any(o in org.name for o in args.organisations)
    ]

    # Find all events that is included in "Vårcupen"
    events = sorted(
        (
            event
            for event in api.get_events(
                args.start_date, args.end_date, organisationIds=ids
            )
            if "vårcup" in event.name.lower()
        ),
        key=lambda e: e.start_date,
    )
    # Set up default values for results
    n = len(events)
    res: dict[str, dict[tuple[str, str], list[int]]] = defaultdict(
        lambda: defaultdict(lambda: [-1 for _ in range(n - 1)])
    )
    names = []

    # Loop over events
    for i, event in enumerate(events):
        event_results = api.get_event_results(event.event_id).results
        names.append(event.name)
        # Loop over all results in the event
        for event_class in event_results:
            cls_name = get_cls_name(event_class.class_name.replace("  ", " "))
            # Collect results for the same person over multiple competitions
            for p_res in event_class.class_result:
                person = (p_res.person.name, p_res.organisation.name)
                # Score is 6 for first place and then decreasing to 2
                # 1 point for not compleating or misspunch
                score = (
                    max(7 - pos, 2)
                    if ((r := p_res.result) and (pos := r.position))
                    else 1
                )
                res[cls_name][person][i] = score

    # Setup an excel Workbook with fonts
    wb = Workbook(args.output)
    header_font = wb.add_format({"bold": True, "font_size": 14})
    text_font = wb.add_format({"font_size": 12})

    # Last competion should be a "Jaktstart"
    names[-1] += " (Jaktstart)"
    leading_points = 0
    for cls_name, inner in res.items():
        # Add a sheet
        ws = wb.add_worksheet(cls_name)
        # Add headers
        for i, name in enumerate(["Namn", "Klubb"] + names):
            ws.write(0, i, name, header_font)
        # Sort based on decreasing total score
        sorted_iter = sorted(
            inner.items(), key=lambda x: sum(x[1]), reverse=True
        )
        # Loop over persons and set scores.
        for i, ((name, org), scores) in enumerate(sorted_iter):
            # Remember the score of the top scorer
            if i == 0:
                leading_points = sum(scores)
            # Calculate start time after leader.
            scores.append((leading_points - sum(scores)) * 10)
            # Write to sheet
            ws.write(i + 1, 0, name, text_font)
            ws.write(i + 1, 1, org, text_font)
            for j, s in enumerate(scores):
                ws.write(i + 1, j + 2, s if s > 0 else None, text_font)
        ws.autofit()
    wb.close()


if __name__ == "__main__":
    main()
