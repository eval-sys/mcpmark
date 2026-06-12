import sys
from notion_client import Client
from tasks.utils import notion_utils

EXPECTED_TITLE = "Research Assistant"
EXPECTED_DATE = "January - August 2023"
EXPECTED_DESCRIPTION = (
    "Assisted in conducting user experience research projects at my bachelor's program, "
    "supporting data collection, analyzing user feedback, and preparing research reports. "
    "Developed strong skills in research methodologies and improved collaboration with "
    "interdisciplinary teams."
)
EXPECTED_SKILL_NAME = "Research Methodologies"
EXPECTED_SKILL_LEVEL = 0.7
SUMMARY_KEYWORD = "research"
SUMMARY_PRESERVED_TOKEN = "Recent graduate"


def _list_children(notion: Client, parent_id: str) -> list[dict]:
    out: list[dict] = []
    cursor: str | None = None
    while True:
        kwargs = {"block_id": parent_id, "page_size": 100}
        if cursor:
            kwargs["start_cursor"] = cursor
        resp = notion.blocks.children.list(**kwargs)
        out.extend(resp.get("results", []))
        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")
    return out


def _annotations(block: dict) -> dict:
    block_type = block.get("type")
    if not block_type:
        return {}
    rich_text = block.get(block_type, {}).get("rich_text", [])
    if not rich_text:
        return {}
    return rich_text[0].get("annotations", {})


def _check_first_work_entry(notion: Client, page_id: str) -> bool:
    all_blocks = notion_utils.get_all_blocks_recursively(notion, page_id)

    wh_block = None
    edu_block = None
    for b in all_blocks:
        if b.get("type") != "heading_1":
            continue
        text = notion_utils.get_block_plain_text(b).strip()
        if text == "Work History" and wh_block is None:
            wh_block = b
        elif text == "Education" and edu_block is None:
            edu_block = b

    if not wh_block or not edu_block:
        print(
            "Error: Could not locate both 'Work History' and 'Education' headings.",
            file=sys.stderr,
        )
        return False

    wh_parent_id = wh_block.get("parent", {}).get("block_id")
    edu_parent_id = edu_block.get("parent", {}).get("block_id")
    if not wh_parent_id or wh_parent_id != edu_parent_id:
        print(
            "Error: 'Work History' and 'Education' headings are not siblings under the "
            "same parent block.",
            file=sys.stderr,
        )
        return False

    siblings = _list_children(notion, wh_parent_id)
    wh_idx = next(
        (i for i, b in enumerate(siblings) if b.get("id") == wh_block["id"]), -1
    )
    edu_idx = next(
        (i for i, b in enumerate(siblings) if b.get("id") == edu_block["id"]), -1
    )
    if wh_idx < 0 or edu_idx < 0 or edu_idx <= wh_idx:
        print(
            "Error: Could not order 'Work History' before 'Education' in their parent.",
            file=sys.stderr,
        )
        return False

    first_column_list = None
    for i in range(wh_idx + 1, edu_idx):
        if siblings[i].get("type") == "column_list":
            first_column_list = siblings[i]
            break

    if not first_column_list:
        print(
            "Error: No column_list found between 'Work History' and 'Education'.",
            file=sys.stderr,
        )
        return False

    columns = _list_children(notion, first_column_list["id"])
    image_column = None
    text_column = None
    for col in columns:
        if col.get("type") != "column":
            continue
        ratio = col.get("column", {}).get("width_ratio")
        if ratio == 0.125 and image_column is None:
            image_column = col
        elif ratio == 0.875 and text_column is None:
            text_column = col

    if not image_column or not text_column:
        print(
            "Error: First Work History column_list does not have the expected "
            "width_ratios (0.125 / 0.875).",
            file=sys.stderr,
        )
        return False

    text_blocks = _list_children(notion, text_column["id"])
    paragraphs = [
        b
        for b in text_blocks
        if b.get("type") == "paragraph"
        and notion_utils.get_block_plain_text(b).strip()
    ]
    if len(paragraphs) < 3:
        print(
            f"Error: First entry's text column has fewer than 3 non-empty "
            f"paragraphs (got {len(paragraphs)}).",
            file=sys.stderr,
        )
        return False

    title_block, date_block, description_block = paragraphs[0], paragraphs[1], paragraphs[2]

    title_text = notion_utils.get_block_plain_text(title_block).strip()
    if title_text != EXPECTED_TITLE:
        print(
            f"Error: First Work History entry title is {title_text!r}, expected "
            f"{EXPECTED_TITLE!r}. The Research Assistant entry must be the FIRST "
            f"entry under Work History (above UI Design Internship).",
            file=sys.stderr,
        )
        return False
    if not _annotations(title_block).get("bold"):
        print("Error: Title is not bold.", file=sys.stderr)
        return False

    date_text = notion_utils.get_block_plain_text(date_block).strip()
    if date_text != EXPECTED_DATE:
        print(
            f"Error: Date paragraph is {date_text!r}, expected {EXPECTED_DATE!r}.",
            file=sys.stderr,
        )
        return False
    date_annot = _annotations(date_block)
    if not date_annot.get("italic"):
        print(
            f"Error: Date should be italic (annotations: {date_annot}).",
            file=sys.stderr,
        )
        return False
    if date_annot.get("color") != "gray":
        print(
            f"Error: Date color should be 'gray' (got {date_annot.get('color')!r}).",
            file=sys.stderr,
        )
        return False

    description_text = notion_utils.get_block_plain_text(description_block).strip()
    if description_text != EXPECTED_DESCRIPTION:
        print(
            "Error: Description text mismatch.\n"
            f"  expected: {EXPECTED_DESCRIPTION!r}\n"
            f"  got:      {description_text!r}",
            file=sys.stderr,
        )
        return False
    desc_annot = _annotations(description_block)
    if desc_annot.get("bold") or desc_annot.get("italic"):
        print(
            f"Error: Description should not be bold or italic (got {desc_annot}).",
            file=sys.stderr,
        )
        return False
    if desc_annot.get("color") not in (None, "default"):
        print(
            f"Error: Description color should be 'default' (got "
            f"{desc_annot.get('color')!r}).",
            file=sys.stderr,
        )
        return False

    return True


def _check_summary_callout(notion: Client, page_id: str) -> bool:
    all_blocks = notion_utils.get_all_blocks_recursively(notion, page_id)

    work_history_idx = -1
    for i, b in enumerate(all_blocks):
        if (
            b.get("type") == "heading_1"
            and notion_utils.get_block_plain_text(b).strip() == "Work History"
        ):
            work_history_idx = i
            break
    if work_history_idx < 0:
        print(
            "Error: 'Work History' heading not found while looking for summary callout.",
            file=sys.stderr,
        )
        return False

    callouts = [
        b for b in all_blocks[:work_history_idx] if b.get("type") == "callout"
    ]
    if not callouts:
        print(
            "Error: No callout block found above the 'Work History' heading.",
            file=sys.stderr,
        )
        return False

    for callout in callouts:
        text = notion_utils.get_block_plain_text(callout)
        if SUMMARY_KEYWORD in text.lower() and SUMMARY_PRESERVED_TOKEN in text:
            return True

    print(
        f"Error: No callout above 'Work History' contains both the new keyword "
        f"{SUMMARY_KEYWORD!r} (case-insensitive) and the original phrase "
        f"{SUMMARY_PRESERVED_TOKEN!r}. The summary should be lightly edited, "
        f"not rewritten.",
        file=sys.stderr,
    )
    for callout in callouts:
        snippet = notion_utils.get_block_plain_text(callout)[:200]
        print(f"  callout text: {snippet!r}", file=sys.stderr)
    return False


def _check_skills_database(notion: Client, page_id: str) -> bool:
    all_blocks = notion_utils.get_all_blocks_recursively(notion, page_id)
    skills_db_id = None
    for b in all_blocks:
        if b.get("type") == "child_database":
            title = b.get("child_database", {}).get("title", "")
            if title == "Skills":
                skills_db_id = b["id"]
                break

    if not skills_db_id:
        print("Error: 'Skills' child database not found on the page.", file=sys.stderr)
        return False

    rows: list[dict] = []
    cursor: str | None = None
    while True:
        kwargs = {"database_id": skills_db_id, "page_size": 100}
        if cursor:
            kwargs["start_cursor"] = cursor
        resp = notion.databases.query(**kwargs)
        rows.extend(resp.get("results", []))
        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")

    for row in rows:
        props = row.get("properties", {})
        title_prop = props.get("Skill", {}).get("title", [])
        title_text = "".join(rt.get("plain_text", "") for rt in title_prop).strip()
        if title_text != EXPECTED_SKILL_NAME:
            continue
        level = props.get("Skill Level", {}).get("number")
        if level == EXPECTED_SKILL_LEVEL:
            return True
        print(
            f"Error: Skills entry {EXPECTED_SKILL_NAME!r} has Skill Level={level!r}, "
            f"expected {EXPECTED_SKILL_LEVEL}.",
            file=sys.stderr,
        )
        return False

    print(
        f"Error: Skills database has no entry titled {EXPECTED_SKILL_NAME!r}.",
        file=sys.stderr,
    )
    return False


def verify(notion: Client, main_id: str | None = None) -> bool:
    page_id: str | None = None
    if main_id:
        found_id, object_type = notion_utils.find_page_or_database_by_id(
            notion, main_id
        )
        if found_id and object_type == "page":
            page_id = found_id
        else:
            print(
                f"Error: Could not resolve main_id {main_id!r} to an accessible page.",
                file=sys.stderr,
            )
            return False
    else:
        page_id = notion_utils.find_page(notion, "Online Resume")

    if not page_id:
        print("Error: Page 'Online Resume' not found.", file=sys.stderr)
        return False

    if not _check_first_work_entry(notion, page_id):
        return False
    if not _check_summary_callout(notion, page_id):
        return False
    if not _check_skills_database(notion, page_id):
        return False

    print(
        "Success: Verified Research Assistant entry (positioned first), summary "
        "callout update, and Skills database entry."
    )
    return True


def main() -> None:
    notion = notion_utils.get_notion_client()
    main_id = sys.argv[1] if len(sys.argv) > 1 else None
    if verify(notion, main_id):
        sys.exit(0)
    sys.exit(1)


if __name__ == "__main__":
    main()
