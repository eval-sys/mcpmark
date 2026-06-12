import sys
from notion_client import Client
from tasks.utils import notion_utils
from typing import Dict


def _normalize_string(s: str) -> str:
    """Replace non-breaking space with regular space for safe comparison."""
    return s.replace("\xa0", " ")


def verify(notion: Client, main_id: str | None = None) -> bool:
    """Verify that the new study-session entry for 2025-01-29 was added correctly.

    The script checks that:
    1. A bold date-mention with start=2025-01-29 exists.
    2. The mention sits after the 2022-09-02 section but before the divider that originally
       followed that section.
    3. Exactly four specified to-do items follow the new date mention and they are all unchecked.
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

    # (2) Verify ordering: new date paragraph must come AFTER the last consecutive
    #     to-do under the 2022-09-02 paragraph and BEFORE the divider that follows.
    last_previous_todo_idx = index_previous_date
    walk = index_previous_date + 1
    while walk < len(all_blocks) and all_blocks[walk].get("type") == "to_do":
        last_previous_todo_idx = walk
        walk += 1

    if not (last_previous_todo_idx < index_new_date < index_divider_after_previous):
        print(
            "Error: The 2025-01-29 section is positioned incorrectly "
            "(must sit after the existing 2022-09-02 to-do items and before the divider).",
            file=sys.stderr,
        )
        return False

    # ---------------------------------------------------------------------
    # Verify to-do items under the new date section ------------------------
    # ---------------------------------------------------------------------
    expected_texts = [
        "🧠 Review algorithms for technical interview",
        "📚 Study database systems chapter 7",
        "⚡ Practice system design problems",
        "🎯 Complete data structures assignment",
    ]
    expected_set = {_normalize_string(t) for t in expected_texts}

    # The blocks between the new date paragraph and the divider must be EXACTLY
    # the four expected to-dos, directly beneath the date mention.
    new_section_blocks = all_blocks[index_new_date + 1 : index_divider_after_previous]
    if len(new_section_blocks) != 4:
        print(
            f"Error: Expected exactly 4 blocks directly beneath the 2025-01-29 date "
            f"(before the divider), found {len(new_section_blocks)}.",
            file=sys.stderr,
        )
        return False

    found_texts: set[str] = set()
    for block in new_section_blocks:
        if block.get("type") != "to_do":
            print(
                f"Error: Block directly beneath the 2025-01-29 date is not a to-do "
                f"(got type '{block.get('type')}').",
                file=sys.stderr,
            )
            return False
        plain_text = notion_utils.get_block_plain_text(block).strip()
        plain_text_norm = _normalize_string(plain_text)
        if block["to_do"].get("checked", False):
            print(f"Error: To-do '{plain_text}' is checked.", file=sys.stderr)
            return False
        found_texts.add(plain_text_norm)

    missing_items = [t for t in expected_set if t not in found_texts]
    if missing_items:
        print(f"Error: Missing to-do items: {missing_items}", file=sys.stderr)
        return False
    extra_items = [t for t in found_texts if t not in expected_set]
    if extra_items:
        print(f"Error: Unexpected to-do items: {extra_items}", file=sys.stderr)
        return False

    # ---------------------------------------------------------------------
    # Success --------------------------------------------------------------
    # ---------------------------------------------------------------------
    print("Success: Study session for 2025-01-29 added correctly.")
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
