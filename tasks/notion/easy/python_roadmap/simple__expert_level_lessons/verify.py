import sys
from notion_client import Client
from tasks.utils import notion_utils


TARGET_PAGE_TITLE = "Python Roadmap"
CHAPTER_NAME = "Expert Level"
CHAPTER_ICON = "🟣"
BRIDGE_TITLE = "Advanced Foundations Review"
REQUIRED_SUBITEM_TITLES = ["Decorators", "Calling API"]

LESSON_REQUIREMENTS = [
    {
        "title": "Metaprogramming and AST Manipulation",
        "status": "To Do",
        "date": "2025-09-15",
        "parent_title": BRIDGE_TITLE,
    },
    {
        "title": "Async Concurrency Patterns",
        "status": "To Do",
        "date": "2025-09-20",
        "parent_title": "Calling API",
    },
]


def _get_database_ids(notion: Client, page_id: str) -> tuple[str | None, str | None]:
    """Return the block IDs for the Chapters and Steps databases on the page."""
    chapters_db_id = None
    steps_db_id = None

    blocks = notion_utils.get_all_blocks_recursively(notion, page_id)
    for block in blocks:
        if block.get("type") != "child_database":
            continue
        title = block.get("child_database", {}).get("title", "")
        if "Chapters" in title and not chapters_db_id:
            chapters_db_id = block["id"]
        elif "Steps" in title and not steps_db_id:
            steps_db_id = block["id"]

    return chapters_db_id, steps_db_id


def _query_step_by_title(notion: Client, database_id: str, title: str, *, exact: bool = True):
    """Return the first step entry matching the given title pattern."""
    title_filter = {"equals": title} if exact else {"contains": title}
    response = notion.databases.query(
        database_id=database_id,
        filter={"property": "Lessons", "title": title_filter},
        page_size=5,
    )
    results = response.get("results", [])
    return results[0] if results else None


def verify(notion: Client, main_id: str | None = None) -> bool:
    """Verify the simplified Expert Level learning path setup."""
    # Resolve the roadmap page.
    if main_id:
        page_id, object_type = notion_utils.find_page_or_database_by_id(notion, main_id)
        if not page_id or object_type != "page":
            print("Error: Python Roadmap page not found.", file=sys.stderr)
            return False
    else:
        page_id = notion_utils.find_page(notion, TARGET_PAGE_TITLE)
        if not page_id:
            print("Error: Python Roadmap page not found.", file=sys.stderr)
            return False

    # Locate the Chapters and Steps databases.
    chapters_db_id, steps_db_id = _get_database_ids(notion, page_id)
    if not chapters_db_id:
        print("Error: Chapters database not found on the page.", file=sys.stderr)
        return False
    if not steps_db_id:
        print("Error: Steps database not found on the page.", file=sys.stderr)
        return False

    # Ensure the Expert Level chapter exists with the purple icon.
    try:
        chapter_resp = notion.databases.query(
            database_id=chapters_db_id,
            filter={"property": "Name", "title": {"equals": CHAPTER_NAME}},
            page_size=1,
        )
    except Exception as exc:
        print(f"Error querying Chapters database: {exc}", file=sys.stderr)
        return False

    results = chapter_resp.get("results", [])
    if not results:
        print("Error: Expert Level chapter not found.", file=sys.stderr)
        return False

    expert_chapter = results[0]
    expert_chapter_id = expert_chapter["id"]
    icon = expert_chapter.get("icon") or {}
    if icon.get("type") != "emoji" or icon.get("emoji") != CHAPTER_ICON:
        print("Error: Expert Level chapter must use the purple circle emoji icon.", file=sys.stderr)
        return False

    print("✓ Expert Level chapter exists with the correct icon.")

    # Locate prerequisite lessons (Control Flow, Decorators, Calling API).
    control_lesson = _query_step_by_title(notion, steps_db_id, "Control", exact=False)
    if not control_lesson:
        print("Error: Could not find a lesson containing 'Control' in its title.", file=sys.stderr)
        return False
    control_lesson_id = control_lesson["id"]

    prerequisite_ids = {}
    for title in REQUIRED_SUBITEM_TITLES:
        lesson = _query_step_by_title(notion, steps_db_id, title, exact=False)
        if not lesson:
            print(f"Error: Required lesson containing '{title}' not found.", file=sys.stderr)
            return False
        prerequisite_ids[title] = lesson["id"]

    # Verify the bridge lesson.
    bridge_lesson = _query_step_by_title(notion, steps_db_id, BRIDGE_TITLE, exact=True)
    if not bridge_lesson:
        print("Error: Advanced Foundations Review lesson not found.", file=sys.stderr)
        return False

    status = (bridge_lesson["properties"].get("Status", {}).get("status") or {}).get("name")
    if status != "Done":
        print("Error: Advanced Foundations Review must have status 'Done'.", file=sys.stderr)
        return False

    # Ensure chapter relation includes Expert Level.
    chapter_rel = bridge_lesson["properties"].get("Chapters", {}).get("relation", [])
    if not any(rel["id"] == expert_chapter_id for rel in chapter_rel):
        print("Error: Advanced Foundations Review must link to the Expert Level chapter.", file=sys.stderr)
        return False

    # Parent item should be the control lesson.
    parent_rel = bridge_lesson["properties"].get("Parent item", {}).get("relation", [])
    if not parent_rel or parent_rel[0]["id"] != control_lesson_id:
        print("Error: Advanced Foundations Review should use the control lesson as its Parent item.", file=sys.stderr)
        return False

    # Sub-items must include the required lessons.
    sub_rel = bridge_lesson["properties"].get("Sub-item", {}).get("relation", [])
    sub_ids = {rel["id"] for rel in sub_rel}
    missing = [title for title, rel_id in prerequisite_ids.items() if rel_id not in sub_ids]
    if missing:
        print(
            f"Error: Advanced Foundations Review must include these lessons as sub-items: {', '.join(missing)}.",
            file=sys.stderr,
        )
        return False

    print("✓ Bridge lesson configured with the correct status, chapter, parent, and sub-items.")

    # Verify the two expert lessons.
    overall_success = True
    for spec in LESSON_REQUIREMENTS:
        lesson = _query_step_by_title(notion, steps_db_id, spec["title"], exact=True)
        if not lesson:
            print(f"Error: Lesson '{spec['title']}' not found.", file=sys.stderr)
            overall_success = False
            continue

        lesson_ok = True

        # Status check.
        status_name = (lesson["properties"].get("Status", {}).get("status") or {}).get("name")
        if status_name != spec["status"]:
            print(
                f"Error: Lesson '{spec['title']}' should have status '{spec['status']}', found '{status_name}'.",
                file=sys.stderr,
            )
            lesson_ok = False

        # Chapter relation check.
        lesson_chapters = lesson["properties"].get("Chapters", {}).get("relation", [])
        if not any(rel["id"] == expert_chapter_id for rel in lesson_chapters):
            print(f"Error: Lesson '{spec['title']}' must link to the Expert Level chapter.", file=sys.stderr)
            lesson_ok = False

        # Parent relation check.
        parent_title = spec["parent_title"]
        if parent_title == BRIDGE_TITLE:
            expected_parent_id = bridge_lesson["id"]
        else:
            expected_parent_id = prerequisite_ids.get(parent_title)

        parent_relation = lesson["properties"].get("Parent item", {}).get("relation", [])
        if not expected_parent_id:
            print(
                f"Error: Could not resolve expected parent '{parent_title}' for lesson '{spec['title']}'.",
                file=sys.stderr,
            )
            lesson_ok = False
        else:
            if not parent_relation or parent_relation[0]["id"] != expected_parent_id:
                print(
                    f"Error: Lesson '{spec['title']}' should have '{parent_title}' as its Parent item.",
                    file=sys.stderr,
                )
                lesson_ok = False
        # Date check.
        date_prop = lesson["properties"].get("Date", {}).get("date") or {}
        if date_prop.get("start") != spec["date"]:
            print(
                f"Error: Lesson '{spec['title']}' should use date {spec['date']}, found {date_prop.get('start')}.",
                file=sys.stderr,
            )
            lesson_ok = False

        if lesson_ok:
            print(f"✓ Lesson '{spec['title']}' has the expected properties.")
        else:
            overall_success = False

    if not overall_success:
        return False

    print("Success: Expert Level chapter, bridge lesson, and expert lessons configured correctly.")
    return True


def main() -> None:
    notion = notion_utils.get_notion_client()
    main_id = sys.argv[1] if len(sys.argv) > 1 else None
    if verify(notion, main_id):
        sys.exit(0)
    sys.exit(1)


if __name__ == "__main__":
    main()
