import re
import sys
from typing import List
from notion_client import Client
from tasks.utils import notion_utils


def _contains_keywords(text: str, keywords: List[str]) -> bool:
    lowered = text.lower()
    return all(kw.lower() in lowered for kw in keywords)


def _norm(text: str) -> str:
    """Normalize whitespace and case for tolerant string comparison."""
    return " ".join(text.lower().split())


def verify(notion: Client, main_id: str = None) -> bool:
    """Programmatically verify that the dashboard page and its contents meet the
    requirements described in description.md.
    """
    DASHBOARD_TITLE = "Q4 2024 Business Review Dashboard"
    PARENT_PAGE_TITLE = "Company In A Box"
    CALL_OUT_KEYWORDS = ["latam expansion", "enterprise push", "employee engagement"]

    # Section heading uses "Human Resources"; the database `Department` select
    # uses the abbreviation "HR" (per description.md). The two sets are kept
    # separate on purpose.
    HEADING_DEPT_NAMES = ["Product", "Marketing", "Sales", "Human Resources"]
    DB_DEPT_NAMES = {"Product", "Marketing", "Sales", "HR"}

    # Objectives sourced from the Company Goals page in the Company In A Box
    # workspace. Keyed by the database department option name ("HR", not
    # "Human Resources"), so it can be reused for entry-level checks below.
    OBJECTIVES_BY_DEPT = {
        "Product": [
            "Launch 3 major features",
            "Expand enterprise offering",
        ],
        "Marketing": [
            "Improve new user retention",
            "Publish more help content to reduce burden on support",
        ],
        "Sales": [
            "Close 20 SMB deals",
            "Create strong sales pitch",
        ],
        "HR": [
            "Fill hiring gaps",
            "Improve the onboarding experience for new hires",
        ],
    }
    ALL_OBJECTIVES = [obj for objs in OBJECTIVES_BY_DEPT.values() for obj in objs]

    REQUIRED_DB_PROPERTIES = {
        "Task Name": "title",
        "Department": "select",
        "Priority": "select",
        "Status": "status",
    }
    PRIORITY_OPTIONS = {"High", "Medium", "Low"}

    # 1. Locate the dashboard page.
    # `main_id` is the duplicated seed root (Company In A Box). Search inside
    # its direct children for a child_page titled DASHBOARD_TITLE.
    page_id = None
    if main_id:
        try:
            children = notion.blocks.children.list(block_id=main_id).get(
                "results", []
            )
            for block in children:
                if (
                    block.get("type") == "child_page"
                    and block.get("child_page", {}).get("title") == DASHBOARD_TITLE
                ):
                    page_id = block["id"]
                    break
        except Exception:
            pass

    if not page_id:
        page_id = notion_utils.find_page(notion, DASHBOARD_TITLE)

    if not page_id:
        print(f"Error: Page '{DASHBOARD_TITLE}' not found.", file=sys.stderr)
        return False

    # Ensure the dashboard is a direct child of Company In A Box.
    # When `main_id` is provided (the harness path), it IS the seed root, so
    # compare ids directly. Otherwise fall back to a title comparison.
    try:
        page_obj = notion.pages.retrieve(page_id=page_id)
        parent_id = page_obj.get("parent", {}).get("page_id")
        if main_id:
            if not parent_id or parent_id.replace("-", "") != main_id.replace("-", ""):
                print(
                    f"Error: Dashboard page is not a direct child of '{PARENT_PAGE_TITLE}'.",
                    file=sys.stderr,
                )
                return False
        elif parent_id:
            parent_page = notion.pages.retrieve(page_id=parent_id)
            parent_title_rt = (
                parent_page.get("properties", {}).get("title", {}).get("title", [])
            )
            parent_title = "".join(
                rt.get("plain_text", "") for rt in parent_title_rt
            ) or None
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

    # 3. Verify department section headings exist (word-boundary match so
    # "Productivity" is not accepted in place of "Product"). Each department
    # must be satisfied by a *distinct* heading block so a single combined
    # heading like "Product / Marketing / Sales / Human Resources" cannot
    # cover all four.
    dept_to_heading_block = {}
    used_block_ids = set()
    for dept in HEADING_DEPT_NAMES:
        pattern = rf"\b{re.escape(dept)}\b"
        for block in all_blocks:
            if block.get("type") not in {"heading_1", "heading_2", "heading_3"}:
                continue
            if block["id"] in used_block_ids:
                continue
            heading_text = notion_utils.get_block_plain_text(block)
            if re.search(pattern, heading_text, flags=re.IGNORECASE):
                dept_to_heading_block[dept] = block["id"]
                used_block_ids.add(block["id"])
                break
    missing_headings = set(HEADING_DEPT_NAMES) - set(dept_to_heading_block)
    if missing_headings:
        print(
            f"Error: Missing distinct department headings: {', '.join(sorted(missing_headings))}.",
            file=sys.stderr,
        )
        return False

    # 4. Each objective from the Company Goals page must appear verbatim in a
    # to-do (checkbox) block, and that to-do block must be located between its
    # owning department's heading and the next department heading (so each
    # objective lives under the correct section).
    block_index = {b["id"]: i for i, b in enumerate(all_blocks)}
    heading_indices = sorted(block_index[bid] for bid in dept_to_heading_block.values())

    def _section_range(dept: str):
        start = block_index[dept_to_heading_block[dept]]
        next_starts = [i for i in heading_indices if i > start]
        end = next_starts[0] if next_starts else len(all_blocks)
        return start, end

    todo_blocks = [b for b in all_blocks if b.get("type") == "to_do"]
    todo_norm_by_id = {
        b["id"]: _norm(notion_utils.get_block_plain_text(b)) for b in todo_blocks
    }

    HEADING_TO_DB_DEPT = {
        "Product": "Product",
        "Marketing": "Marketing",
        "Sales": "Sales",
        "Human Resources": "HR",
    }
    for heading_dept in HEADING_DEPT_NAMES:
        db_dept = HEADING_TO_DB_DEPT[heading_dept]
        start, end = _section_range(heading_dept)
        section_todo_norms = [
            todo_norm_by_id[b["id"]]
            for b in todo_blocks
            if start < block_index[b["id"]] < end
        ]
        for objective in OBJECTIVES_BY_DEPT[db_dept]:
            norm_obj = _norm(objective)
            if not any(norm_obj in t for t in section_todo_norms):
                print(
                    f"Error: Objective '{objective}' not found in a to-do block under the '{heading_dept}' heading.",
                    file=sys.stderr,
                )
                return False

    # 5. Verify Action Items database exists and has correct schema
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

    # Department select options must be exactly the four declared in description.md
    dept_options = {
        opt["name"] for opt in db_props["Department"]["select"]["options"]
    }
    if dept_options != DB_DEPT_NAMES:
        print(
            f"Error: Department property options must be exactly {sorted(DB_DEPT_NAMES)}. "
            f"Got: {sorted(dept_options)}.",
            file=sys.stderr,
        )
        return False

    # Priority options must be exactly {High, Medium, Low}
    priority_options = {
        opt["name"] for opt in db_props["Priority"]["select"]["options"]
    }
    if priority_options != PRIORITY_OPTIONS:
        print(
            f"Error: Priority property options must be exactly {sorted(PRIORITY_OPTIONS)}. "
            f"Got: {sorted(priority_options)}.",
            file=sys.stderr,
        )
        return False

    # 6. Verify at least 5 action items exist and content matches description.
    try:
        pages = notion.databases.query(database_id=db_id).get("results", [])
    except Exception as exc:
        print(f"Error querying database pages: {exc}", file=sys.stderr)
        return False

    if len(pages) < 5:
        print("Error: Database contains fewer than 5 action items.", file=sys.stderr)
        return False

    # Build reverse map objective -> department for entry validation
    objective_to_dept = {
        objective: dept
        for dept, objs in OBJECTIVES_BY_DEPT.items()
        for objective in objs
    }

    seen_dept_in_entries = set()
    seen_entry_pairs = set()
    for page in pages:
        props = page.get("properties", {})

        # Task Name must contain the verbatim text of one of the underlying objectives.
        title_rt = props.get("Task Name", {}).get("title", [])
        task_name = "".join(rt.get("plain_text", "") for rt in title_rt)
        if not task_name.strip():
            print(
                f"Error: Action item '{page.get('id')}' is missing a Task Name.",
                file=sys.stderr,
            )
            return False

        task_name_norm = _norm(task_name)
        matched_objective = None
        for objective in ALL_OBJECTIVES:
            if _norm(objective) in task_name_norm:
                matched_objective = objective
                break
        if not matched_objective:
            print(
                f"Error: Action item Task Name '{task_name}' does not contain "
                f"the verbatim text of any Company Goals objective.",
                file=sys.stderr,
            )
            return False

        # Department must match the department that owns the matched objective.
        dept_select = props.get("Department", {}).get("select", {}).get("name")
        if not dept_select or dept_select not in DB_DEPT_NAMES:
            print(
                f"Error: Action item '{task_name}' has invalid or missing Department value: '{dept_select}'.",
                file=sys.stderr,
            )
            return False

        expected_dept = objective_to_dept[matched_objective]
        if dept_select != expected_dept:
            print(
                f"Error: Action item '{task_name}' has Department='{dept_select}' "
                f"but objective '{matched_objective}' belongs to '{expected_dept}'.",
                file=sys.stderr,
            )
            return False

        seen_dept_in_entries.add(dept_select)
        seen_entry_pairs.add((_norm(matched_objective), dept_select))

        # Priority and Status must be set (any allowed value).
        priority_val = props.get("Priority", {}).get("select", {}).get("name")
        status_val = props.get("Status", {}).get("status", {}).get("name")
        if not priority_val or not status_val:
            print(
                f"Error: Action item '{task_name}' must have both Priority and Status set.",
                file=sys.stderr,
            )
            return False

    # All four departments must be represented across the entries.
    missing_depts = DB_DEPT_NAMES - seen_dept_in_entries
    if missing_depts:
        print(
            f"Error: Action items do not cover all four departments. "
            f"Missing: {', '.join(sorted(missing_depts))}.",
            file=sys.stderr,
        )
        return False

    # Require at least 5 distinct (objective, department) pairs so the entries
    # genuinely derive from different objectives rather than duplicates.
    if len(seen_entry_pairs) < 5:
        print(
            f"Error: Action items must include at least 5 distinct "
            f"(objective, department) pairs. Got {len(seen_entry_pairs)}.",
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
