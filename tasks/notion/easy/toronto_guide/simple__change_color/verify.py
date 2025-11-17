import sys
from notion_client import Client
from tasks.utils import notion_utils


TARGET_PAGE_TITLE = "Toronto Guide"
FOOD_DATABASE_KEYWORD = "Food"
TARGET_TAG_NAMES = [
    "Middle Eastern",
    "Jamaican",
    "Indian",
]


def _get_food_database_id(notion: Client, page_id: str) -> str | None:
    """Return the block ID of the Food database shown on the target page."""
    all_blocks = notion_utils.get_all_blocks_recursively(notion, page_id)
    for block in all_blocks:
        if not block or block.get("type") != "child_database":
            continue
        title = block.get("child_database", {}).get("title", "")
        if FOOD_DATABASE_KEYWORD.lower() in title.lower():
            return block.get("id")
    return None


def verify(notion: Client, main_id: str | None = None) -> bool:
    """Check that all target tags in the Food database are no longer pink."""
    # Resolve the Toronto Guide page ID.
    if main_id:
        found_id, object_type = notion_utils.find_page_or_database_by_id(notion, main_id)
        if not found_id or object_type != "page":
            print("Error: Toronto Guide page not found.", file=sys.stderr)
            return False
        page_id = found_id
    else:
        page_id = notion_utils.find_page(notion, TARGET_PAGE_TITLE)
        if not page_id:
            print("Error: Toronto Guide page not found.", file=sys.stderr)
            return False

    # Locate the Food database block.
    food_db_id = _get_food_database_id(notion, page_id)
    if not food_db_id:
        print("Error: Food database not found on the Toronto Guide page.", file=sys.stderr)
        return False

    # Fetch database definition and inspect tag options.
    try:
        db_info = notion.databases.retrieve(database_id=food_db_id)
    except Exception as exc:
        print(f"Error: Unable to retrieve Food database ({exc}).", file=sys.stderr)
        return False

    tags_property = db_info.get("properties", {}).get("Tags", {})
    if tags_property.get("type") != "multi_select":
        print("Error: Food database does not have a multi-select Tags property.", file=sys.stderr)
        return False

    options = tags_property.get("multi_select", {}).get("options", [])
    remaining_targets = set(TARGET_TAG_NAMES)
    failures = False

    for option in options:
        tag_name = option.get("name", "").strip()
        if tag_name not in remaining_targets:
            continue

        remaining_targets.discard(tag_name)
        color = option.get("color")
        if color == "pink":
            print(f"Error: Tag '{tag_name}' in Food database is still pink.", file=sys.stderr)
            failures = True
        else:
            print(f"✓ Tag '{tag_name}' color updated to '{color}'.")

    if remaining_targets:
        print(
            f"Error: Food tags not found (expected to exist): {sorted(remaining_targets)}.",
            file=sys.stderr,
        )
        return False

    if failures:
        return False

    print("Success: All Food database tags are now non-pink.")
    return True


def main() -> None:
    notion = notion_utils.get_notion_client()
    main_id = sys.argv[1] if len(sys.argv) > 1 else None
    if verify(notion, main_id):
        sys.exit(0)
    sys.exit(1)


if __name__ == "__main__":
    main()
