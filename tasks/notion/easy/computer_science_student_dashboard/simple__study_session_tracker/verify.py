import sys
from notion_client import Client
from tasks.utils import notion_utils


def verify(notion: Client, main_id: str | None = None) -> bool:
    """Verify that the new study-session entry for 2025-01-29 was added correctly.

    The script checks that:
    1. A bold date-mention with start=2025-01-29 exists.
    2. The mention sits after the 2022-09-02 section but before the divider that originally
       followed that section.
    """

    # ---------------------------------------------------------------------
    # Locate the main page -------------------------------------------------
    # ---------------------------------------------------------------------
    page_id: str | None = None

    if main_id:
        found_id, object_type = notion_utils.find_page_or_database_by_id(
            notion, main_id
        )
        if found_id and object_type == "page":
            page_id = found_id

    if not page_id:
        page_id = notion_utils.find_page(notion, "Computer Science Student Dashboard")

    if not page_id:
        print(
            "Error: Page 'Computer Science Student Dashboard' not found.",
            file=sys.stderr,
        )
        return False

    # ---------------------------------------------------------------------
    # Fetch all blocks under the page (flattened order) --------------------
    # ---------------------------------------------------------------------
    all_blocks = notion_utils.get_all_blocks_recursively(notion, page_id)

    # ---------------------------------------------------------------------
    # Locate reference blocks ---------------------------------------------
    # ---------------------------------------------------------------------
    TARGET_DATE = "2025-01-29"
    PREVIOUS_DATE = "2022-09-02"

    index_previous_date: int | None = None
    index_new_date: int | None = None
    index_divider_after_previous: int | None = None

    for idx, block in enumerate(all_blocks):
        # Divider detection (we care only about the first divider that appears after
        # the 2022-09-02 block)
        if block.get("type") == "divider":
            if index_previous_date is not None and index_divider_after_previous is None:
                index_divider_after_previous = idx

        # We only need to inspect paragraph blocks that contain a date mention
        if block.get("type") != "paragraph":
            continue

        rich_text_list = block["paragraph"].get("rich_text", [])
        for rt in rich_text_list:
            if (
                rt.get("type") != "mention"
                or rt.get("mention", {}).get("type") != "date"
            ):
                continue

            date_start = rt["mention"]["date"].get("start")

            if date_start == PREVIOUS_DATE and index_previous_date is None:
                index_previous_date = idx

            if date_start == TARGET_DATE and index_new_date is None:
                index_new_date = idx
                # (1) Verify bold annotation
                if not rt.get("annotations", {}).get("bold", False):
                    print(
                        "Error: The 2025-01-29 date mention is not bold.",
                        file=sys.stderr,
                    )
                    return False

    # Ensure all reference indices were found
    if index_previous_date is None:
        print("Error: Could not locate the 2022-09-02 date section.", file=sys.stderr)
        return False
    if index_divider_after_previous is None:
        print(
            "Error: Could not locate the divider that follows the 2022-09-02 section.",
            file=sys.stderr,
        )
        return False
    if index_new_date is None:
        print(
            "Error: Could not locate the new 2025-01-29 date mention.", file=sys.stderr
        )
        return False

    # (2) Verify ordering
    if not (index_previous_date < index_new_date < index_divider_after_previous):
        print(
            "Error: The 2025-01-29 section is positioned incorrectly.", file=sys.stderr
        )
        return False

    # ---------------------------------------------------------------------
    # Success --------------------------------------------------------------
    # ---------------------------------------------------------------------
    print("Success: Date mention for 2025-01-29 added in the correct position.")
    return True


# -------------------------------------------------------------------------
# Command-line entry-point -------------------------------------------------
# -------------------------------------------------------------------------


def main() -> None:
    notion = notion_utils.get_notion_client()
    main_id = sys.argv[1] if len(sys.argv) > 1 else None

    if verify(notion, main_id):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
