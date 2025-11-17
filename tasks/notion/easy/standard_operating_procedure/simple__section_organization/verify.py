import sys
from notion_client import Client
from tasks.utils import notion_utils


TARGET_PAGE_TITLE = "Standard Operating Procedure"
ROLES_HEADING = "Roles & responsibilities"
TERMINOLOGIES_HEADING = "Terminologies"


def _find_heading_indices(blocks: list[dict]) -> tuple[int | None, int | None]:
    """Return the indices of the target headings within the flattened block list."""
    roles_index = None
    terminologies_index = None

    for index, block in enumerate(blocks):
        if block.get("type") != "heading_2":
            continue
        rich_text = block.get("heading_2", {}).get("rich_text", [])
        if not rich_text:
            continue
        heading_text = rich_text[0].get("text", {}).get("content", "")
        if heading_text == ROLES_HEADING and roles_index is None:
            roles_index = index
        elif heading_text == TERMINOLOGIES_HEADING and terminologies_index is None:
            terminologies_index = index

    return roles_index, terminologies_index


def verify(notion: Client, main_id: str | None = None) -> bool:
    """Ensure the Roles & responsibilities section appears before Terminologies."""
    # Resolve page id.
    if main_id:
        page_id, object_type = notion_utils.find_page_or_database_by_id(notion, main_id)
        if not page_id or object_type != "page":
            print("Error: Standard Operating Procedure page not found.", file=sys.stderr)
            return False
    else:
        page_id = notion_utils.find_page(notion, TARGET_PAGE_TITLE)
        if not page_id:
            print("Error: Standard Operating Procedure page not found.", file=sys.stderr)
            return False

    # Fetch all blocks (flattened order from top to bottom).
    blocks = notion_utils.get_all_blocks_recursively(notion, page_id)
    roles_index, terminologies_index = _find_heading_indices(blocks)

    if roles_index is None:
        print("Error: 'Roles & responsibilities' section not found.", file=sys.stderr)
        return False
    if terminologies_index is None:
        print("Error: 'Terminologies' section not found.", file=sys.stderr)
        return False

    if roles_index >= terminologies_index:
        print(
            "Error: Sections are not swapped. 'Roles & responsibilities' should appear before 'Terminologies'.",
            file=sys.stderr,
        )
        return False

    print("Success: Section order updated so 'Roles & responsibilities' precedes 'Terminologies'.")
    return True


def main() -> None:
    notion = notion_utils.get_notion_client()
    main_id = sys.argv[1] if len(sys.argv) > 1 else None
    if verify(notion, main_id):
        sys.exit(0)
    sys.exit(1)


if __name__ == "__main__":
    main()
