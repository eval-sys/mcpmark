import sys
from typing import List, Dict
from notion_client import Client
from tasks.utils import notion_utils

EXPECTED_TITLES = [
    "Draft initial content outline",
    "Gather most common user questions",
    "Organize support topics by category",
    "Review existing help documentation",
]

# Mapping title -> expected image token to verify original task id (A, B, C, D)
TITLE_IMAGE_TOKEN_MAP: Dict[str, str] = {
    "Draft initial content outline": "imagea",
    "Gather most common user questions": "imageb",
    "Organize support topics by category": "imagec",
    "Review existing help documentation": "imaged",
}


def _extract_title(page: dict) -> str:
    """Return the plain text title of the page (empty string if not found)."""
    title_prop = (
        page.get("properties", {}).get("Name")
        or page.get("properties", {}).get("Title")
        or page.get("properties", {}).get("title")
    )
    if title_prop and title_prop.get("title"):
        return "".join(rt.get("plain_text", "") for rt in title_prop["title"]).strip()
    # Fallback: title property may be nested differently (the example uses 'Name')
    title_list = page.get("properties", {}).get("title", {}).get("title", [])
    return "".join(rt.get("plain_text", "") for rt in title_list).strip()


def _cover_contains_token(page: dict, token: str) -> bool:
    """Return True if page.cover.external.url (or file.url) contains the given token (case-insensitive)."""
    cover = page.get("cover")
    if not cover:
        return False
    url = None
    if cover.get("type") == "external":
        url = cover.get("external", {}).get("url")
    elif cover.get("type") == "file":
        url = cover.get("file", {}).get("url")
    if not url:
        return False
    return token.lower() in url.lower()


def verify(notion: Client, main_id: str = None) -> bool:
    """Verify that project 'Publish support knowledge base' has exactly the 4 expected tasks with correct titles and source mapping."""
    # 1. Locate Team Projects page
    page_id = None
    if main_id:
        found_id, object_type = notion_utils.find_page_or_database_by_id(
            notion, main_id
        )
        if found_id and object_type == "page":
            page_id = found_id

    if not page_id:
        page_id = notion_utils.find_page(notion, "Team Projects")
    if not page_id:
        print("Error: Page 'Team Projects' not found.", file=sys.stderr)
        return False

    # 2. Find Projects database inside the page
    db_id = notion_utils.find_database_in_block(notion, page_id, "Projects")
    if not db_id:
        print(
            "Error: 'Projects' database not found under 'Team Projects'.",
            file=sys.stderr,
        )
        return False

    # 3. Query for project page titled 'Publish support knowledge base'
    try:
        results = notion.databases.query(
            database_id=db_id,
            filter={
                "property": "Project"
                if "Project"
                in notion.databases.retrieve(database_id=db_id).get("properties", {})
                else "Name",
                "title": {"equals": "Publish support knowledge base"},
            },
        ).get("results", [])
    except Exception as e:
        print(f"Error querying 'Projects' database: {e}", file=sys.stderr)
        return False

    if not results:
        print(
            "Error: Project 'Publish support knowledge base' not found in database.",
            file=sys.stderr,
        )
        return False

    project_page = results[0]
    # 4. Extract related task IDs from Tasks relation property
    relation_prop = project_page.get("properties", {}).get("Tasks")
    if not relation_prop or relation_prop.get("type") != "relation":
        print(
            "Error: 'Tasks' relation property not found in project page.",
            file=sys.stderr,
        )
        return False

    task_relations: List[dict] = relation_prop.get("relation", [])
    task_ids = [rel["id"] for rel in task_relations]

    if len(task_ids) != 4:
        print(
            f"Error: Expected 4 task relations, found {len(task_ids)}.", file=sys.stderr
        )
        return False

    # 5. Retrieve each task page
    retrieved_titles = []
    for pid in task_ids:
        try:
            task_page = notion.pages.retrieve(page_id=pid)
        except Exception as e:
            print(f"Error retrieving task page {pid}: {e}", file=sys.stderr)
            return False

        title = _extract_title(task_page)
        if not title:
            print(f"Error: Task page {pid} has empty title.", file=sys.stderr)
            return False
        retrieved_titles.append(title)

        # Validate mapping via cover url token
        expected_token = TITLE_IMAGE_TOKEN_MAP.get(title)
        if not expected_token:
            print(f"Error: Unexpected title '{title}' found.", file=sys.stderr)
            return False
        if not _cover_contains_token(task_page, expected_token):
            print(
                f"Error: Cover image for task '{title}' does not contain token '{expected_token}'.",
                file=sys.stderr,
            )
            return False

    # 6. Ensure that retrieved titles match expected set exactly (order irrelevant)
    if sorted(retrieved_titles) != sorted(EXPECTED_TITLES):
        print(
            f"Error: Task titles mismatch. Found {retrieved_titles}, expected {EXPECTED_TITLES} (order irrelevant).",
            file=sys.stderr,
        )
        return False

    print(
        "Success: Verified that project 'Publish support knowledge base' contains exactly the expected tasks with correct source mapping."
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
