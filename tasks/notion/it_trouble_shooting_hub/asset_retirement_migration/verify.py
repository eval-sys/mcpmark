import sys
from typing import Dict, Set
from notion_client import Client
from tasks.utils import notion_utils


def _get_database(root_page_id: str, notion: Client, name: str) -> str | None:
    """Helper that finds a child database by title inside a page."""
    return notion_utils.find_database_in_block(notion, root_page_id, name)


def _check_property(props: Dict, name: str, expected_type: str) -> bool:
    if name not in props:
        print(f"Error: Property '{name}' missing in database.", file=sys.stderr)
        return False
    if props[name]["type"] != expected_type:
        print(
            f"Error: Property '{name}' expected type '{expected_type}', found '{props[name]['type']}'.",
            file=sys.stderr,
        )
        return False
    return True


def verify(notion: Client, main_id: str | None = None) -> bool:
    """Verifies that the IT Asset Retirement Queue was created and populated correctly."""

    # -------------------------------------------------------------------------
    # Resolve the root IT Trouble Shooting Hub page
    # -------------------------------------------------------------------------
    root_page_id = None
    if main_id:
        found_id, obj_type = notion_utils.find_page_or_database_by_id(notion, main_id)
        if found_id and obj_type == "page":
            root_page_id = found_id

    if not root_page_id:
        root_page_id = notion_utils.find_page(notion, "IT Trouble Shooting Hub")
    if not root_page_id:
        print(
            "Error: Could not locate the 'IT Trouble Shooting Hub' page.",
            file=sys.stderr,
        )
        return False

    # -------------------------------------------------------------------------
    # Locate the original and new databases
    # -------------------------------------------------------------------------
    inventory_db_id = _get_database(root_page_id, notion, "IT Inventory")
    if not inventory_db_id:
        print("Error: 'IT Inventory' database not found.", file=sys.stderr)
        return False

    retirement_db_id = _get_database(root_page_id, notion, "IT Asset Retirement Queue")
    if not retirement_db_id:
        print("Error: 'IT Asset Retirement Queue' database not found.", file=sys.stderr)
        return False

    # -------------------------------------------------------------------------
    # Validate schema of the retirement queue database
    # -------------------------------------------------------------------------
    retirement_db = notion.databases.retrieve(database_id=retirement_db_id)
    r_props = retirement_db["properties"]

    required_schema = {
        "Serial": "title",
        "Tags": "multi_select",
        "Status": "select",
        "Vendor": "select",
        "Expiration date": "date",
        "Retirement Reason": "select",
    }

    for pname, ptype in required_schema.items():
        if not _check_property(r_props, pname, ptype):
            return False

    # Check Retirement Reason options
    expected_reason_options: Set[str] = {
        "Expired License",
        "Hardware Obsolete",
        "Security Risk",
        "User Offboarding",
    }
    actual_options = {
        opt["name"] for opt in r_props["Retirement Reason"]["select"]["options"]
    }
    if actual_options != expected_reason_options:
        print(
            "Error: 'Retirement Reason' select options mismatch.\n"
            f"Expected: {sorted(expected_reason_options)}\n"
            f"Found: {sorted(actual_options)}",
            file=sys.stderr,
        )
        return False

    # ---------------------------------------------------------------
    # Validate database description starts with required phrase
    # ---------------------------------------------------------------
    desc_rich = retirement_db.get("description", [])
    desc_text = "".join([t.get("plain_text", "") for t in desc_rich])
    required_desc = "AUTO-GENERATED MIGRATION COMPLETED"
    if desc_text.strip() != required_desc:
        print(
            f"Error: Retirement database description must be exactly '{required_desc}'.",
            file=sys.stderr,
        )
        return False

    # -------------------------------------------------------------------------
    # Validate that inventory items are moved & archived
    # -------------------------------------------------------------------------
    expired_filter = {
        "property": "Status",
        "select": {"equals": "Expired"},
    }
    to_return_filter = {
        "property": "Status",
        "select": {"equals": "To be returned"},
    }
    compound_filter = {"or": [expired_filter, to_return_filter]}

    # Query for any *active* items that still match these statuses
    remaining_items = notion.databases.query(
        database_id=inventory_db_id,
        filter=compound_filter,
        archived=False,
    ).get("results", [])

    if remaining_items:
        print(
            f"Error: {len(remaining_items)} 'Expired' / 'To be returned' items still present in IT Inventory.",
            file=sys.stderr,
        )
        return False

    # There should be at least one entry in the retirement queue
    retirement_pages = notion.databases.query(database_id=retirement_db_id).get(
        "results", []
    )
    expected_serials = {"65XYQ/GB", "36x10PIQ"}
    if len(retirement_pages) != len(expected_serials):
        print(
            f"Error: Expected {len(expected_serials)} retirement pages, found {len(retirement_pages)}.",
            file=sys.stderr,
        )
        return False

    # Each retirement page must have a Retirement Reason
    serials_seen = set()
    for page in retirement_pages:
        props = page["properties"]
        reason = props.get("Retirement Reason", {}).get("select", {})
        if not reason or reason.get("name") not in expected_reason_options:
            print(
                f"Error: Page {page['id']} missing valid 'Retirement Reason'.",
                file=sys.stderr,
            )
            return False

        # Collect Serial title
        title_rich = props.get("Serial", {}).get("title", [])
        serial_val = "".join([t.get("plain_text", "") for t in title_rich]).strip()
        serials_seen.add(serial_val)

    if serials_seen != expected_serials:
        print(
            f"Error: Serial values mismatch. Expected {sorted(expected_serials)}, found {sorted(serials_seen)}.",
            file=sys.stderr,
        )
        return False

    # -----------------------------------------------------------------
    # Verify the migration log page and callout block contents
    # -----------------------------------------------------------------
    log_page_title = "Retirement Migration Log"
    log_page_id = notion_utils.find_page(notion, log_page_title)
    if not log_page_id:
        print(f"Error: Page '{log_page_title}' not found.", file=sys.stderr)
        return False

    # Search for a callout block with required pattern
    import re

    callout_pattern = re.compile(
        r"Successfully migrated (\d+) assets to the retirement queue on 2025-03-24\."
    )
    blocks = notion_utils.get_all_blocks_recursively(notion, log_page_id)
    match_found = False
    for blk in blocks:
        if blk.get("type") == "callout":
            text = notion_utils.get_block_plain_text(blk)
            m = callout_pattern.search(text)
            if m:
                migrated_num = int(m.group(1))
                if migrated_num == len(expected_serials):
                    match_found = True
                else:
                    print(
                        f"Error: Callout reports {migrated_num} assets, but {len(retirement_pages)} retirement pages found.",
                        file=sys.stderr,
                    )
                    return False
                break
    if not match_found:
        print(
            "Error: Required callout block not found in migration log page.",
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
