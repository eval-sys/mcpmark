import sys
from notion_client import Client
from tasks.utils import notion_utils
import re


def _get_title_text(page_properties: dict) -> str:
    """Extract the plain text of the first title property from a page."""
    for prop in page_properties.values():
        if prop.get("type") == "title":
            title_rich = prop.get("title", [])
            if title_rich:
                return title_rich[0].get("plain_text")
    return ""


def verify(notion: Client, main_id: str | None = None) -> bool:
    """Verify that the automation created the expected security audit ticket."""

    # ----------------------------------------------------------------------------------
    # Locate the root page (IT Trouble Shooting Hub) either via main_id or by title.
    # ----------------------------------------------------------------------------------
    root_page_id = None
    if main_id:
        found_id, object_type = notion_utils.find_page_or_database_by_id(
            notion, main_id
        )
        if found_id and object_type == "page":
            root_page_id = found_id

    if not root_page_id:
        root_page_id = notion_utils.find_page(notion, "IT Trouble Shooting Hub")
    if not root_page_id:
        print(
            "Error: Could not locate the 'IT Trouble Shooting Hub' page.",
            file=sys.stderr,
        )
        return False

    # ----------------------------------------------------------------------------------
    # Find the IT Requests database under the root page.
    # ----------------------------------------------------------------------------------
    requests_db_id = notion_utils.find_database_in_block(
        notion, root_page_id, "IT Requests"
    )
    if not requests_db_id:
        print(
            "Error: 'IT Requests' database not found in the workspace.", file=sys.stderr
        )
        return False

    # ----------------------------------------------------------------------------------
    # Search for the expected ticket inside the IT Requests database.
    # ----------------------------------------------------------------------------------
    expected_title = "Quarterly Security Audit - Expired Assets Review"
    results = notion.databases.query(database_id=requests_db_id).get("results", [])

    target_page = None
    for page in results:
        title_text = _get_title_text(page.get("properties", {}))
        if title_text == expected_title:
            target_page = page
            break

    if not target_page:
        print(
            f"Failure: Ticket with title '{expected_title}' was not found in 'IT Requests' database.",
            file=sys.stderr,
        )
        return False

    props = target_page.get("properties", {})

    # ----------------------------------------------------------------------------------
    # Validate Priority property.
    # ----------------------------------------------------------------------------------
    priority_value = props.get("Priority", {}).get("select", {}).get("name")
    if priority_value != "High":
        print(
            f"Failure: Expected Priority 'High', found '{priority_value}'.",
            file=sys.stderr,
        )
        return False

    # ----------------------------------------------------------------------------------
    # Validate Due date property.
    # ----------------------------------------------------------------------------------
    due_date_start = props.get("Due", {}).get("date", {}).get("start")
    expected_due_iso = "2023-06-22"
    if not due_date_start or not due_date_start.startswith(expected_due_iso):
        print(
            f"Failure: Expected Due date '{expected_due_iso}', found '{due_date_start}'.",
            file=sys.stderr,
        )
        return False

    # ----------------------------------------------------------------------------------
    # Validate the bulleted list contains the correct expired items in required format.
    # ----------------------------------------------------------------------------------
    page_id = target_page["id"]
    blocks = notion.blocks.children.list(block_id=page_id).get("results", [])
    bullet_texts = [
        notion_utils.get_block_plain_text(b)
        for b in blocks
        if b.get("type") == "bulleted_list_item"
    ]

    expected_items = {
        "192371-8910/54": "Computer Accessory",
        "32x11PIP": "Computer Accessory",
        "76x87PCY": "Laptop",
        "36x10PIQ": "Computer Accessory",
        "65XYQ/GB": "License",
    }

    if len(bullet_texts) != len(expected_items):
        print(
            f"Failure: Expected {len(expected_items)} bullet items, found {len(bullet_texts)}.",
            file=sys.stderr,
        )
        return False

    bullet_pattern = re.compile(r"^\s*(.*?)\s+-\s+(.*?)\s+-\s+(.+?)\s*$")
    matched = set()
    for text in bullet_texts:
        m = bullet_pattern.match(text)
        if not m:
            print(
                f"Failure: Bullet item '{text}' does not follow '<Serial> - <Tag> - <Recommendation>' format.",
                file=sys.stderr,
            )
            return False
        serial, tag, advice = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
        if serial not in expected_items:
            print(
                f"Failure: Unexpected Serial '{serial}' found in bullet list.",
                file=sys.stderr,
            )
            return False
        if expected_items[serial] != tag:
            print(
                f"Failure: Serial '{serial}' expected tag '{expected_items[serial]}', found '{tag}'.",
                file=sys.stderr,
            )
            return False
        if not advice:
            print(
                f"Failure: Bullet item for Serial '{serial}' is missing a recommendation/advice.",
                file=sys.stderr,
            )
            return False
        matched.add(serial)

    if len(matched) != len(expected_items):
        missing = set(expected_items.keys()) - matched
        print(
            f"Failure: Missing bullet items for serials: {', '.join(missing)}.",
            file=sys.stderr,
        )
        return False

    print("Success: All verification criteria satisfied.")
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
