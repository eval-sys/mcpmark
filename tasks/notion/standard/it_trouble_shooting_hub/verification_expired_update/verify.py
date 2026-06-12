import sys
from notion_client import Client
from tasks.utils import notion_utils

CALL_OUT_TEXT = "VERIFICATION EXPIRED - This page needs review and re-verification"
CALL_OUT_ICON = "⚠️"
CALL_OUT_COLOR = "red_background"
IT_HOMEPAGE_DB_TITLE = "IT Homepage"
IT_REQUESTS_DB_TITLE = "IT Requests"
REQUEST_TITLE = "Batch Verification Update Required"
PRIORITY_HIGH = "High"
STATUS_IN_PROGRESS = "In progress"

# Ground-truth list of pages that were 'expired' in the seed template.
# We hardcode by title because the live Verification.state drifts (Notion can
# transition expired -> unverified over time, and editing a page can clear the
# state), so re-querying it at verify time is unreliable.
EXPECTED_EXPIRED_TITLES = [
    "What Is IT in Charge Of",
    "How to Submit a Ticket",
    "Security Awareness Guide",
]


def _get_main_page_id(notion: Client, main_id: str | None) -> str | None:
    """Resolve the main page id starting from CLI arg or by title search."""
    if main_id:
        found_id, obj_type = notion_utils.find_page_or_database_by_id(notion, main_id)
        if found_id and obj_type == "page":
            return found_id
    # Fallback to title search (case-insensitive)
    return notion_utils.find_page(notion, "It Trouble Shooting Hub")


def _fetch_database_id(
    notion: Client, parent_page_id: str, db_title: str
) -> str | None:
    """Locate a child database by title inside a given page."""
    return notion_utils.find_database_in_block(notion, parent_page_id, db_title)


def _query_all_pages(notion: Client, db_id: str) -> list[dict]:
    """Query every page in a database, paginating until exhausted."""
    pages: list[dict] = []
    cursor: str | None = None
    while True:
        kwargs = {"database_id": db_id, "page_size": 100}
        if cursor:
            kwargs["start_cursor"] = cursor
        resp = notion.databases.query(**kwargs)
        pages.extend(resp.get("results", []))
        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")
    return pages


def _expected_expired_pages(notion: Client, db_id: str) -> list[dict] | None:
    """Resolve the seed-defined expired pages by title.

    Returns the list in the same order as EXPECTED_EXPIRED_TITLES, or None
    if any expected title is missing in the database.
    """
    by_title: dict[str, dict] = {}
    for page in _query_all_pages(notion, db_id):
        title_prop = page.get("properties", {}).get("Page", {}).get("title", [])
        title_text = title_prop[0].get("plain_text") if title_prop else ""
        if title_text:
            by_title[title_text.strip()] = page

    resolved: list[dict] = []
    for expected in EXPECTED_EXPIRED_TITLES:
        page = by_title.get(expected)
        if not page:
            print(
                f"Error: Expected expired page '{expected}' not found in IT Homepage.",
                file=sys.stderr,
            )
            return None
        resolved.append(page)
    return resolved


def _check_callout_present(notion: Client, page_id: str) -> bool:
    """Verify the specified callout is the first child block of the page."""
    children = notion.blocks.children.list(block_id=page_id, page_size=1).get(
        "results", []
    )
    if not children:
        return False
    first_block = children[0]
    if first_block.get("type") != "callout":
        return False
    data = first_block.get("callout", {})
    # Check color
    if data.get("color") != CALL_OUT_COLOR:
        return False

    # Check icon
    icon = data.get("icon", {})
    if icon.get("type") != "emoji" or icon.get("emoji") != CALL_OUT_ICON:
        return False

    # Check text content (callout rich text plain text) — exact match after trim
    plain_text = notion_utils.get_block_plain_text(first_block).strip()
    return plain_text == CALL_OUT_TEXT


def _find_request_page(notion: Client, db_id: str) -> dict | None:
    """Find the IT Request page with the expected title."""
    # Use a simple search inside database
    res = notion.databases.query(
        database_id=db_id,
        filter={"property": "Task name", "title": {"equals": REQUEST_TITLE}},
    ).get("results", [])
    return res[0] if res else None


def _check_request_properties(page: dict) -> bool:
    props = page.get("properties", {})
    priority = props.get("Priority", {}).get("select", {}).get("name")
    status = (
        props.get("Status", {}).get("status", {}).get("name")
        if props.get("Status", {}).get("status")
        else props.get("Status", {}).get("select", {}).get("name")
    )
    return priority == PRIORITY_HIGH and status == STATUS_IN_PROGRESS


def _request_page_bullets_match(
    notion: Client, request_page_id: str, expected_page_ids: list[str]
) -> bool:
    """Check the IT Request body bullets correspond exactly to the expected pages.

    Strict reading of "each bullet is a mention of the page processed":
      - bullet count == len(expected_page_ids)
      - each bullet's rich_text contains exactly one element, of type
        mention/page
      - the set of mentioned page ids equals the set of expected page ids
    """
    children = notion.blocks.children.list(
        block_id=request_page_id, page_size=100
    ).get("results", [])
    bullet_blocks = [b for b in children if b.get("type") == "bulleted_list_item"]

    if len(bullet_blocks) != len(expected_page_ids):
        print(
            f"Error: IT Request body has {len(bullet_blocks)} bullets, "
            f"expected exactly {len(expected_page_ids)}.",
            file=sys.stderr,
        )
        return False

    expected_set = {_normalize_id(pid) for pid in expected_page_ids}
    mentioned_ids: list[str] = []
    for block in bullet_blocks:
        rich_text = block.get("bulleted_list_item", {}).get("rich_text", [])
        page_mentions = [
            rt for rt in rich_text
            if rt.get("type") == "mention"
            and rt.get("mention", {}).get("type") == "page"
        ]
        if len(page_mentions) != 1:
            print(
                "Error: each IT Request bullet must contain exactly one page "
                f"mention; found {len(page_mentions)}.",
                file=sys.stderr,
            )
            return False
        mentioned_ids.append(
            _normalize_id(page_mentions[0]["mention"]["page"].get("id", ""))
        )

    if set(mentioned_ids) != expected_set:
        print(
            f"Error: IT Request bullet mentions do not match expected pages.\n"
            f"  expected: {sorted(expected_set)}\n"
            f"  got:      {sorted(set(mentioned_ids))}",
            file=sys.stderr,
        )
        return False
    return True


def _normalize_id(pid: str) -> str:
    """Notion ids may appear with or without dashes; normalise for comparison."""
    return pid.replace("-", "").lower()


def verify(notion: Client, main_id: str | None = None) -> bool:
    main_page_id = _get_main_page_id(notion, main_id)
    if not main_page_id:
        print(
            "Error: Could not locate the main page 'It Trouble Shooting Hub'.",
            file=sys.stderr,
        )
        return False

    # Locate required databases
    it_home_db_id = _fetch_database_id(notion, main_page_id, IT_HOMEPAGE_DB_TITLE)
    it_req_db_id = _fetch_database_id(notion, main_page_id, IT_REQUESTS_DB_TITLE)
    if not all([it_home_db_id, it_req_db_id]):
        print(
            "Error: Required databases not found under the main page.", file=sys.stderr
        )
        return False

    # Identify the expected expired pages by hardcoded title (ground truth)
    expected_pages = _expected_expired_pages(notion, it_home_db_id)
    if expected_pages is None:
        return False

    # Verify callout on each expected expired page
    for pg in expected_pages:
        pid = pg["id"]
        title_prop = pg.get("properties", {}).get("Page", {}).get("title", [])
        title_text = title_prop[0].get("plain_text") if title_prop else pid
        if not _check_callout_present(notion, pid):
            print(
                f"Failure: Callout missing or incorrect on page '{title_text}'.",
                file=sys.stderr,
            )
            return False

    # Verify IT Request entry
    request_page = _find_request_page(notion, it_req_db_id)
    if not request_page:
        print(
            "Failure: IT Request 'Batch Verification Update Required' not found.",
            file=sys.stderr,
        )
        return False
    if not _check_request_properties(request_page):
        print("Failure: Priority or Status incorrect on IT Request.", file=sys.stderr)
        return False

    # Verify bullet list in IT Request body matches the expected pages exactly
    expected_page_ids = [p["id"] for p in expected_pages]
    if not _request_page_bullets_match(
        notion, request_page["id"], expected_page_ids
    ):
        return False

    print("Success: All verification checks passed.")
    return True


def main():
    notion = notion_utils.get_notion_client()
    main_id = sys.argv[1] if len(sys.argv) > 1 else None
    if verify(notion, main_id):
        sys.exit(0)
    sys.exit(1)


if __name__ == "__main__":
    main()
