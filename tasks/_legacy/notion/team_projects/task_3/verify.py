import sys
from datetime import date
from typing import List, Dict
from notion_client import Client
from tasks.utils import notion_utils

# Expected metadata for the two new projects
PROJECT_SPECS = {
    "Foundations of RL and LLM Agents": {
        "priority": "P0",
        "start": date(2025, 3, 24),
        "end": date(2025, 5, 1),
        "eng_hours": 500,
        "task_titles": [
            "Study fundamentals of reinforcement learning",
            "Explore architectures of LLM-based agents",
        ],
    },
    "Infrastructure for LLM + RL Training": {
        "priority": "P1",
        "start": date(2025, 5, 4),
        "end": date(2025, 5, 28),
        "eng_hours": 800,
        "task_titles": [
            "Research existing training pipelines for RL",
            "Compare distributed training frameworks for large models",
            "Build training infrastructure for agentic RL",
            "Train a prototype agent using the new pipeline",
        ],
    },
}

PROJECT_TYPE_EXPECTED = "Train an agentic RL model"


def _extract_title(page: dict) -> str:
    """Return the plain text title of a Notion page."""
    props = page.get("properties", {})
    title_prop = (
        props.get("Project")
        or props.get("Name")
        or props.get("Title")
        or props.get("title")
    )
    if title_prop and title_prop.get("title"):
        return "".join(rt.get("plain_text", "") for rt in title_prop["title"]).strip()
    # Fallback
    title_list = props.get("title", {}).get("title", [])
    return "".join(rt.get("plain_text", "") for rt in title_list).strip()


def _get_select_name(select_prop: dict) -> str:
    if not select_prop:
        return ""
    if select_prop.get("type") == "select":
        return (select_prop.get("select") or {}).get("name", "")
    # Could already be the inner dict
    return select_prop.get("name", "")


def _dates_match(date_prop: dict, expected_start: date, expected_end: date) -> bool:
    if not date_prop or date_prop.get("type") != "date":
        return False
    date_range = date_prop.get("date") or {}
    start = date_range.get("start")
    end = date_range.get("end")
    try:
        return start == expected_start.isoformat() and end == expected_end.isoformat()
    except Exception:
        return False


def _verify_tasks(
    notion: Client, task_ids: List[str], expected_titles: List[str]
) -> bool:
    if len(task_ids) != len(expected_titles):
        print(
            f"Error: Expected {len(expected_titles)} tasks, found {len(task_ids)}.",
            file=sys.stderr,
        )
        return False

    titles_found: List[str] = []
    for tid in task_ids:
        try:
            task_page = notion.pages.retrieve(page_id=tid)
        except Exception as e:
            print(f"Error retrieving task page {tid}: {e}", file=sys.stderr)
            return False
        title = _extract_title(task_page)
        titles_found.append(title)

    if sorted(titles_found) != sorted(expected_titles):
        print(
            f"Error: Task titles mismatch. Found {titles_found}, expected {expected_titles}.",
            file=sys.stderr,
        )
        return False
    return True


def verify(notion: Client, main_id: str = None) -> bool:
    # 1. Locate Team Projects page & Projects database
    team_page_id = None
    if main_id:
        found_id, object_type = notion_utils.find_page_or_database_by_id(
            notion, main_id
        )
        if found_id and object_type == "page":
            team_page_id = found_id

    if not team_page_id:
        team_page_id = notion_utils.find_page(notion, "Team Projects")
    if not team_page_id:
        print("Error: Team Projects page not found.", file=sys.stderr)
        return False

    projects_db_id = notion_utils.find_database_in_block(
        notion, team_page_id, "Projects"
    )
    if not projects_db_id:
        print(
            "Error: Projects database not found in Team Projects page.", file=sys.stderr
        )
        return False

    # Retrieve all project pages once
    try:
        all_projects = notion.databases.query(database_id=projects_db_id).get(
            "results", []
        )
    except Exception as e:
        print(f"Error querying Projects database: {e}", file=sys.stderr)
        return False

    # Map title -> page dict
    title_to_page: Dict[str, dict] = {}
    for pg in all_projects:
        title = _extract_title(pg)
        if title in PROJECT_SPECS:
            title_to_page[title] = pg

    # Ensure both projects exist
    missing = [t for t in PROJECT_SPECS if t not in title_to_page]
    if missing:
        print(f"Error: Missing project pages {missing}.", file=sys.stderr)
        return False

    # IDs for cross-reference
    foundations_id = title_to_page["Foundations of RL and LLM Agents"]["id"]
    infra_id = title_to_page["Infrastructure for LLM + RL Training"]["id"]

    # 2. Validate each project
    for title, spec in PROJECT_SPECS.items():
        page = title_to_page[title]
        props = page.get("properties", {})

        # Priority
        priority_name = _get_select_name(props.get("Priority"))
        if priority_name != spec["priority"]:
            print(
                f"Error: Priority for '{title}' expected {spec['priority']}, found '{priority_name}'.",
                file=sys.stderr,
            )
            return False

        # Timeline
        if not _dates_match(props.get("Timeline"), spec["start"], spec["end"]):
            print(f"Error: Timeline for '{title}' incorrect.", file=sys.stderr)
            return False

        # Eng hours
        eng_hours = props.get("Eng hours", {}).get("number")
        if eng_hours != spec["eng_hours"]:
            print(
                f"Error: Eng hours for '{title}' expected {spec['eng_hours']}, found {eng_hours}.",
                file=sys.stderr,
            )
            return False

        # Project Type
        project_type_name = _get_select_name(props.get("Project type"))
        if project_type_name != PROJECT_TYPE_EXPECTED:
            print(
                f"Error: Project type for '{title}' expected '{PROJECT_TYPE_EXPECTED}', found '{project_type_name}'.",
                file=sys.stderr,
            )
            return False

        # Tasks relation
        tasks_rel = props.get("Tasks", {})
        if tasks_rel.get("type") != "relation":
            print(
                f"Error: Tasks property missing or not a relation for '{title}'.",
                file=sys.stderr,
            )
            return False
        task_ids = [rel["id"] for rel in tasks_rel.get("relation", [])]
        if not _verify_tasks(notion, task_ids, spec["task_titles"]):
            return False

    # 3. Validate blocking relations between the two projects
    foundations_props = title_to_page["Foundations of RL and LLM Agents"].get(
        "properties", {}
    )
    infra_props = title_to_page["Infrastructure for LLM + RL Training"].get(
        "properties", {}
    )

    # Foundations should block Infra
    blocking_rel = foundations_props.get("Blocking", {})
    blocking_ids = (
        [rel["id"] for rel in blocking_rel.get("relation", [])]
        if blocking_rel.get("type") == "relation"
        else []
    )
    if infra_id not in blocking_ids:
        print(
            "Error: 'Foundations of RL and LLM Agents' does not block 'Infrastructure for LLM + RL Training'.",
            file=sys.stderr,
        )
        return False

    # Infra should be blocked by Foundations
    blocked_by_rel = infra_props.get("Blocked by", {})
    blocked_by_ids = (
        [rel["id"] for rel in blocked_by_rel.get("relation", [])]
        if blocked_by_rel.get("type") == "relation"
        else []
    )
    if foundations_id not in blocked_by_ids:
        print(
            "Error: 'Infrastructure for LLM + RL Training' is not blocked by 'Foundations of RL and LLM Agents'.",
            file=sys.stderr,
        )
        return False

    print(
        "Success: Verified both projects with correct metadata, tasks, and blocking relations."
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
