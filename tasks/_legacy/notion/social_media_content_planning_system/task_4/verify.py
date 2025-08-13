import sys
from notion_client import Client
from tasks.utils import notion_utils


def verify(notion: Client, main_id: str = None) -> bool:
    """Verification for Social Media Content Planning System – Task 4.

    Requirement:
      For each of the four specified content items, the Publish Date should have
      been postponed by 14 days, resulting in the following target dates:

        • "7 Days, 7 Home Styling Ideas"                → 2025-08-10
        • "Show Us: What's Your Favorite Corner at Home?" → 2025-08-06
        • "Minimalism: More Than White Walls & Empty Shelves" → 2025-08-02
        • "5 Small Habits That Make Home Feel Warmer"   → 2025-07-30

      A failure summary (n/4) is printed if any row fails verification.
    """

    db_title = "Social Media Content Planning System"
    database_id = None
    if main_id:
        # main_id is now always a page id
        database_id = notion_utils.find_database_in_block(notion, main_id, db_title)
    if not database_id:
        print(
            f"Error: Database '{db_title}' not found under the provided page.",
            file=sys.stderr,
        )
        return False

    try:
        results = notion.databases.query(database_id=database_id).get("results", [])
    except Exception as e:
        print(f"Error: Failed to query database '{db_title}'. {e}", file=sys.stderr)
        return False

    expected_dates = {
        "7 Days, 7 Home Styling Ideas": "2025-08-10",
        "Show Us: What’s Your Favorite Corner at Home?": "2025-08-06",
        "Minimalism: More Than White Walls & Empty Shelves": "2025-08-02",
        "5 Small Habits That Make Home Feel Warmer": "2025-07-30",
    }

    passed = set()
    failed_titles = []
    failure_reasons = []

    for page in results:
        props = page.get("properties", {})

        # Extract title (assume property name "Content Title", else fallback)
        title_prop = (
            props.get("Content Title")
            or props.get("Name")
            or props.get("Title")
            or props.get("title")
            or {}
        )
        rich = title_prop.get("title", [])
        title_text = "".join(rt.get("plain_text", "") for rt in rich).strip()

        if title_text not in expected_dates:
            continue

        publish_prop = props.get("Publish Date", {})
        publish_date = (publish_prop.get("date") or {}).get(
            "start"
        )  # iso format string

        if publish_date == expected_dates[title_text]:
            passed.add(title_text)
        else:
            failed_titles.append(title_text)
            failure_reasons.append(
                f"Row '{title_text}' Publish Date is {publish_date}, expected {expected_dates[title_text]}."
            )

    missing_titles = set(expected_dates.keys()) - passed - set(failed_titles)
    for t in missing_titles:
        failed_titles.append(t)
        failure_reasons.append(f"Row '{t}' not found in database query results.")

    if failed_titles:
        print(
            f"Failure: {len(failed_titles)}/{len(expected_dates)} rows failed verification.",
            file=sys.stderr,
        )
        for reason in failure_reasons:
            print(f"- {reason}", file=sys.stderr)
        return False

    print(
        f"Success: All {len(expected_dates)} target rows have correct postponed Publish Dates."
    )
    return True


def main():
    notion = notion_utils.get_notion_client()
    main_id = sys.argv[1] if len(sys.argv) > 1 else None
    if verify(notion, main_id):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
