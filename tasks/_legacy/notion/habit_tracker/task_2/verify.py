import sys
from typing import List, Dict
from notion_client import Client
from tasks.utils import notion_utils

# Mapping ranges to expected status (lower-case for comparison)
STATUS_RULES = [
    (0, 2, "barely started"),  # inclusive range 0-2
    (3, 5, "making progress"),  # inclusive range 3-5
    (6, float("inf"), "crushing it"),  # 6 or more
]

FORMULA_PROP_CANDIDATES = ["Formula", "formula", "Completed Days", "completed"]
STATUS_PROP_CANDIDATES = ["Status", "status"]


def _find_property_by_name(props: Dict[str, dict], candidates: List[str]):
    for name in candidates:
        if name in props:
            return name, props[name]
    # Fallback: first formula or status type
    for prop_name, prop in props.items():
        if prop.get("type") == "formula" and "formula" in candidates:
            return prop_name, prop
        if prop.get("type") == "status" and "status" in candidates:
            return prop_name, prop
    return None, None


def _expected_status_for_value(val: float) -> str:
    for low, high, status in STATUS_RULES:
        if low <= val <= high:
            return status
    # Should not happen
    return ""


def verify(notion: Client, main_id: str = None) -> bool:
    # 1. Locate Habit Tracker page and database
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

    db_id = notion_utils.find_database_in_block(
        notion, page_id, "habit tracker"
    ) or notion_utils.find_database_in_block(notion, page_id, "Habit Tracker")
    if not db_id:
        print("Error: Habit Tracker database not found.", file=sys.stderr)
        return False

    # 2. Query all entries
    try:
        entries = notion.databases.query(database_id=db_id).get("results", [])
    except Exception as e:
        print(f"Error querying Habit Tracker database: {e}", file=sys.stderr)
        return False

    if not entries:
        print(
            "Error: Habit Tracker database has no entries to verify.", file=sys.stderr
        )
        return False

    failed_count = 0
    for entry in entries:
        props: Dict[str, dict] = entry.get("properties", {})

        # Find formula property
        formula_name, formula_prop = _find_property_by_name(
            props, FORMULA_PROP_CANDIDATES
        )
        if not formula_prop or formula_prop.get("type") != "formula":
            print("Error: Formula property not found on an entry.", file=sys.stderr)
            return False
        formula_value = (formula_prop.get("formula") or {}).get("number")
        if formula_value is None:
            print("Error: Formula result is None for an entry.", file=sys.stderr)
            return False

        # Expected status
        expected_status = _expected_status_for_value(formula_value)

        # Retrieve status property
        status_name, status_prop = _find_property_by_name(props, STATUS_PROP_CANDIDATES)
        if not status_prop or status_prop.get("type") != "status":
            print(
                "Error: Status property missing or wrong type for an entry.",
                file=sys.stderr,
            )
            return False
        status_value = (status_prop.get("status") or {}).get("name", "").lower()

        if status_value != expected_status:
            title = "".join(
                rt.get("plain_text", "")
                for rt in (props.get("habit tracker ") or {}).get("title", [])
            )
            print(
                f"Error: Entry '{title or entry.get('id')}' formula={formula_value} expects status '{expected_status}', found '{status_value}'.",
                file=sys.stderr,
            )
            failed_count += 1

    if failed_count:
        print(
            f"Failure: {failed_count} entries have mismatched status.", file=sys.stderr
        )
        return False

    print("Success: All habit entries have correct status based on formula values.")
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
