import sys
from notion_client import Client
from tasks.utils import notion_utils


def verify(notion: Client, main_id: str = None) -> bool:
    """Verification for Social Media Content Planning System – Task 3.

    Requirement:
      Locate the content entry titled "7 Days, 7 Home Styling Ideas" and ensure
      that its Platform multi-select property:
        • contains at least 5 platforms, and
        • includes "Instagram" among them.
    """

    db_title = "Social Media Content Planning System"
    database_id = None
    if main_id:
        # main_id is now always a page id
        database_id = notion_utils.find_database_in_block(notion, main_id, db_title)
    if not database_id:
        print(
            f"Error: Database '{db_title}' not found under the provided page.",
            file=sys.stderr,
        )
        return False

    try:
        results = notion.databases.query(database_id=database_id).get("results", [])
    except Exception as e:
        print(f"Error: Failed to query database '{db_title}'. {e}", file=sys.stderr)
        return False

    target_title = "7 Days, 7 Home Styling Ideas"

    for page in results:
        props = page.get("properties", {})

        # Extract title (assume property name "Content Title", else fallback)
        title_prop = (
            props.get("Content Title")
            or props.get("Name")
            or props.get("Title")
            or props.get("title")
            or {}
        )
        rich = title_prop.get("title", [])
        title_text = "".join(rt.get("plain_text", "") for rt in rich).strip()

        if title_text != target_title:
            continue

        platform_prop = props.get("Platform") or props.get("Platforms")
        platforms = [
            opt.get("name") for opt in (platform_prop or {}).get("multi_select", [])
        ]

        if len(platforms) < 5:
            print(
                f"Failure: '{target_title}' has only {len(platforms)} platforms (need ≥5).",
                file=sys.stderr,
            )
            return False

        if not any(p.lower() == "instagram" for p in platforms):
            print(
                f"Failure: 'Instagram' not found in Platform list for '{target_title}'.",
                file=sys.stderr,
            )
            return False

        print(
            f"Success: '{target_title}' has {len(platforms)} platforms and includes Instagram."
        )
        return True

    print(
        f"Failure: Row titled '{target_title}' not found in database query results.",
        file=sys.stderr,
    )
    return False


def main():
    notion = notion_utils.get_notion_client()
    main_id = sys.argv[1] if len(sys.argv) > 1 else None
    if verify(notion, main_id):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
