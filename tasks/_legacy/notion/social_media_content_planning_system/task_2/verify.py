import sys
from notion_client import Client
from tasks.utils import notion_utils


def verify(notion: Client, main_id: str = None) -> bool:
    """Verification for Social Media Content Planning System – Task 2.

    Requirements to satisfy:
      • For every content entry where Target Audience includes "Gen Z" OR "Millennials"
        AND Status is NOT "Published", the Expected Engagement should have been
        increased by 200.
      • Based on the provided ground-truth, the rows that must satisfy this are:
            1. "Show Us: What's Your Favorite Corner at Home?"   → 3400
            2. "5 Small Habits That Make Home Feel Warmer"        → 1100
            3. "Summer Eco-Friendly Home Makeover Guide"          → 1050
            4. "Behind the Brand: A Founder's Morning Ritual"     → 2100

    The script verifies that each of these rows exists, still matches the filtering
    conditions, and has the exact Expected Engagement value above.
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

    # Ground-truth mapping of Content Title → expected Expected Engagement value
    expected_map = {
        "Show Us: What’s Your Favorite Corner at Home?": 3400,
        "5 Small Habits That Make Home Feel Warmer": 1100,
        "Summer Eco-Friendly Home Makeover Guide": 1050,
        "Behind the Brand: A Founder’s Morning Ritual": 2100,
    }

    passed = set()
    failed_titles = []
    failure_reasons = []

    for page in results:
        properties = page.get("properties", {})

        # Extract title (assume property name "Content Title", fall back to generic title)
        title_prop = (
            properties.get("Content Title")
            or properties.get("Name")
            or properties.get("Title")
            or properties.get("title")
            or {}
        )
        title_rich = title_prop.get("title", [])
        title_text = "".join(rt.get("plain_text", "") for rt in title_rich).strip()

        if title_text not in expected_map:
            continue  # Not one of the target rows

        # Target Audience
        audience_prop = properties.get("Target Audience", {})
        audience_list = [
            opt.get("name") for opt in audience_prop.get("multi_select", [])
        ]

        # Status
        status_prop = properties.get("Status", {})
        status_name = (status_prop.get("status") or {}).get("name")

        # Expected Engagement
        engagement_prop = properties.get("Expected Engagement", {})
        engagement_value = engagement_prop.get("number")

        ok = True

        if not (
            ("Gen Z" in audience_list or "Millennials" in audience_list)
            and status_name != "Published"
        ):
            ok = False
            failure_reasons.append(
                f"Row '{title_text}' does not satisfy Audience/Status filtering conditions."
            )

        if engagement_value != expected_map[title_text]:
            ok = False
            failure_reasons.append(
                f"Row '{title_text}' Expected Engagement is {engagement_value}, expected {expected_map[title_text]}."
            )

        if ok:
            passed.add(title_text)
        else:
            failed_titles.append(title_text)

    # Identify titles not found at all
    missing_titles = set(expected_map.keys()) - passed - set(failed_titles)
    failed_titles.extend(list(missing_titles))
    for t in missing_titles:
        failure_reasons.append(f"Row '{t}' not found in database query results.")

    if failed_titles:
        print(
            f"Failure: {len(failed_titles)}/{len(expected_map)} rows failed verification.",
            file=sys.stderr,
        )
        # Print detailed reasons for easier debugging
        for reason in failure_reasons:
            print(f"- {reason}", file=sys.stderr)
        return False

    print(
        f"Success: All {len(expected_map)} target rows passed verification (Audience/Status and Expected Engagement)."
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
