import sys
from typing import List
from notion_client import Client
from tasks.utils import notion_utils


def _contains_keywords(text: str, keywords: List[str]) -> bool:
    lowered = text.lower()
    return all(kw.lower() in lowered for kw in keywords)


def verify(notion: Client, main_id: str = None) -> bool:
    """Programmatically verify that the dashboard page and its contents meet the
    requirements described in description.md.
    """
    DASHBOARD_TITLE = "Q4 2024 Business Review Dashboard"
    PARENT_PAGE_TITLE = "Company In A Box"
    CALL_OUT_KEYWORDS = ["latam", "enterprise", "employee engagement"]
    DEPARTMENTS = ["Product", "Marketing", "Sales", "Human Resources"]
    REQUIRED_DB_PROPERTIES = {
        "Task Name": "title",
        "Department": "select",
        "Priority": "select",
        "Status": "status",
    }
    PRIORITY_OPTIONS = {"High", "Medium", "Low"}

    # 1. Locate the dashboard page
    page_id = None
    if main_id:
        found_id, obj_type = notion_utils.find_page_or_database_by_id(notion, main_id)
        if found_id and obj_type == "page":
            page_id = found_id

    if not page_id:
        page_id = notion_utils.find_page(notion, DASHBOARD_TITLE)

    if not page_id:
        print(f"Error: Page '{DASHBOARD_TITLE}' not found.", file=sys.stderr)
        return False

    # Optional: ensure it is a child of Company In A Box
    try:
        page_obj = notion.pages.retrieve(page_id=page_id)
        parent_id = page_obj.get("parent", {}).get("page_id")
        if parent_id:
            parent_page = notion.pages.retrieve(page_id=parent_id)
            parent_title_rt = (
                parent_page.get("properties", {}).get("title", {}).get("title", [])
            )
            parent_title = (
                parent_title_rt[0].get("plain_text") if parent_title_rt else None
            )
            if parent_title != PARENT_PAGE_TITLE:
                print(
                    f"Error: Dashboard page is not a direct child of '{PARENT_PAGE_TITLE}'.",
                    file=sys.stderr,
                )
                return False
    except Exception:
        pass  # parent check is best-effort only

    # 2. Verify callout with keywords
    all_blocks = notion_utils.get_all_blocks_recursively(notion, page_id)
    callout_ok = False
    for block in all_blocks:
        if block.get("type") == "callout":
            callout_text = notion_utils.get_block_plain_text(block)
            if _contains_keywords(callout_text, CALL_OUT_KEYWORDS):
                callout_ok = True
                break
    if not callout_ok:
        print(
            "Error: No callout found that includes all three Current Goal keywords (LATAM, Enterprise, Employee engagement).",
            file=sys.stderr,
        )
        return False

    # 3. Verify department section headings
    found_depts = set()
    for block in all_blocks:
        if block.get("type") in {"heading_1", "heading_2", "heading_3"}:
            heading_text = notion_utils.get_block_plain_text(block)
            for dept in DEPARTMENTS:
                if dept.lower() in heading_text.lower():
                    found_depts.add(dept)
    if set(DEPARTMENTS) != found_depts:
        missing = set(DEPARTMENTS) - found_depts
        print(
            f"Error: Missing department headings: {', '.join(missing)}.",
            file=sys.stderr,
        )
        return False

    # 4. Verify Action Items database exists and has correct schema
    db_id = notion_utils.find_database_in_block(notion, page_id, "Action Items")
    if not db_id:
        print(
            "Error: Database 'Action Items' not found on the dashboard.",
            file=sys.stderr,
        )
        return False

    try:
        db = notion.databases.retrieve(database_id=db_id)
    except Exception as exc:
        print(f"Error: Unable to retrieve database: {exc}", file=sys.stderr)
        return False

    db_props = db.get("properties", {})
    for prop_name, expected_type in REQUIRED_DB_PROPERTIES.items():
        if prop_name not in db_props:
            print(
                f"Error: Property '{prop_name}' missing from database.", file=sys.stderr
            )
            return False
        actual_type = db_props[prop_name]["type"]
        if isinstance(expected_type, list):
            if actual_type not in expected_type:
                print(
                    f"Error: Property '{prop_name}' has type '{actual_type}', expected one of {expected_type}.",
                    file=sys.stderr,
                )
                return False
        else:
            if actual_type != expected_type:
                print(
                    f"Error: Property '{prop_name}' has type '{actual_type}', expected '{expected_type}'.",
                    file=sys.stderr,
                )
                return False
        # Extra check for Priority options
        if prop_name == "Priority":
            options = {opt["name"] for opt in db_props[prop_name]["select"]["options"]}
            if not PRIORITY_OPTIONS.issubset(options):
                print(
                    f"Error: Priority property options must include High/Medium/Low. Current options: {options}",
                    file=sys.stderr,
                )
                return False

    # 5. Verify at least 5 action items exist
    try:
        pages = notion.databases.query(database_id=db_id).get("results", [])
    except Exception as exc:
        print(f"Error querying database pages: {exc}", file=sys.stderr)
        return False

    if len(pages) < 5:
        print("Error: Database contains fewer than 5 action items.", file=sys.stderr)
        return False

    # Optional: Verify Department values valid
    for page in pages:
        props = page.get("properties", {})

        # Task Name must be non-empty
        title_rt = props.get("Task Name", {}).get("title", [])
        task_name = title_rt[0].get("plain_text") if title_rt else ""
        if not task_name.strip():
            print(
                f"Error: Action item '{page.get('id')}' is missing a Task Name.",
                file=sys.stderr,
            )
            return False

        # Department must be valid
        dept_select = props.get("Department", {}).get("select", {}).get("name")
        if not dept_select or dept_select not in DEPARTMENTS:
            print(
                f"Error: Action item '{page.get('id')}' has invalid or missing Department value.",
                file=sys.stderr,
            )
            return False

        # Priority and Status must be set (any value)
        priority_val = props.get("Priority", {}).get("select", {}).get("name")
        status_val = props.get("Status", {}).get("status", {}).get("name")
        if not priority_val or not status_val:
            print(
                f"Error: Action item '{page.get('id')}' must have both Priority and Status set.",
                file=sys.stderr,
            )
            return False

    print(
        "Success: Verified Business Review Dashboard, departmental sections, callout, and Action Items database with ≥5 entries."
    )
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
