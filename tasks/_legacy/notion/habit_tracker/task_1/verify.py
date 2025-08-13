import sys
from typing import Dict
from notion_client import Client
from tasks.utils import notion_utils

EXPECTED_HABIT_NAME = "no phone after 10pm"
EXPECTED_CHECKBOX_DAYS = ["Thurs", "Fri", "Sat", "Sun"]


def _extract_title(page: dict) -> str:
    """Return the plain text title of a database entry page."""
    props = page.get("properties", {})
    # Find the first property whose type is 'title'
    for prop in props.values():
        if prop.get("type") == "title":
            return "".join(
                rt.get("plain_text", "") for rt in prop.get("title", [])
            ).strip()
    return ""


def verify(notion: Client, main_id: str = None) -> bool:
    """Verify that the habit 'no phone after 10pm' exists and is completed Thu-Sun."""
    # 1. Locate Habit Tracker page
    page_id = None
    if main_id:
        found_id, object_type = notion_utils.find_page_or_database_by_id(
            notion, main_id
        )
        if found_id and object_type == "page":
            page_id = found_id

    if not page_id:
        page_id = notion_utils.find_page(
            notion, "habit tracker"
        ) or notion_utils.find_page(notion, "Habit Tracker")
    if not page_id:
        print("Error: Habit Tracker page not found.", file=sys.stderr)
        return False

    # 2. Find Habit Tracker database inside the page
    db_id = notion_utils.find_database_in_block(
        notion, page_id, "habit tracker"
    ) or notion_utils.find_database_in_block(notion, page_id, "Habit Tracker")
    if not db_id:
        print(
            "Error: Habit Tracker database not found within the page.", file=sys.stderr
        )
        return False

    # 3. Query all habits
    try:
        results = notion.databases.query(database_id=db_id).get("results", [])
    except Exception as e:
        print(f"Error querying Habit Tracker database: {e}", file=sys.stderr)
        return False

    # 4. Search for expected habit entry (case-insensitive comparison)
    expected_name_lower = EXPECTED_HABIT_NAME.lower()
    for entry in results:
        title = _extract_title(entry)
        if title.lower() != expected_name_lower:
            continue
        props: Dict[str, dict] = entry.get("properties", {})

        all_ok = True
        for day in EXPECTED_CHECKBOX_DAYS:
            day_prop = props.get(day)
            if not day_prop or day_prop.get("type") != "checkbox":
                print(
                    f"Error: Property '{day}' missing or not a checkbox for habit entry.",
                    file=sys.stderr,
                )
                return False
            if not day_prop.get("checkbox", False):
                print(
                    f"Error: Checkbox for '{day}' not marked true for habit entry.",
                    file=sys.stderr,
                )
                return False
        # Found a matching entry that passes all checks
        print("Success: Habit entry verified with correct checkboxes set.")
        return True

    print(
        f"Failure: Habit '{EXPECTED_HABIT_NAME}' not found in Habit Tracker database.",
        file=sys.stderr,
    )
    return False


def main():
    notion = notion_utils.get_notion_client()
    main_id = sys.argv[1] if len(sys.argv) > 1 else None
    if verify(notion, main_id):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
