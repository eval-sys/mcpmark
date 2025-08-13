import sys
from notion_client import Client
from tasks.utils import notion_utils


def verify(notion: Client, main_id: str = None) -> bool:
    """
    Verifies that the 'Interview Schedule' database has been created with correct properties
    and contains at least three sample entries.
    """
    # Find the job applications page
    page_id = None
    if main_id:
        found_id, object_type = notion_utils.find_page_or_database_by_id(
            notion, main_id
        )
        if found_id and object_type == "page":
            page_id = found_id

    if not page_id:
        page_id = notion_utils.find_page(notion, "Job Applications")
    if not page_id:
        print("Error: Page 'Job Applications' not found.", file=sys.stderr)
        return False

    # Find the Interview Schedule database
    database_id = notion_utils.find_database_in_block(
        notion, page_id, "Interview Schedule"
    )
    if not database_id:
        print(
            "Error: Database 'Interview Schedule' not found in Job Applications page.",
            file=sys.stderr,
        )
        return False

    print("Success: 'Interview Schedule' database found.")

    # Check database properties
    database = notion.databases.retrieve(database_id=database_id)
    properties = database.get("properties", {})

    required_properties = {
        "Company": "title",
        "Position": "rich_text",
        "Date": "date",
        "Time": "rich_text",
        "Status": "rich_text",
    }

    for prop_name, expected_type in required_properties.items():
        if prop_name not in properties:
            print(
                f"Error: Property '{prop_name}' not found in database.", file=sys.stderr
            )
            return False

        actual_type = properties[prop_name].get("type")
        if actual_type != expected_type:
            print(
                f"Error: Property '{prop_name}' has type '{actual_type}', expected '{expected_type}'.",
                file=sys.stderr,
            )
            return False

    print("Success: All required properties found with correct types.")

    # Check for sample entries
    results = notion.databases.query(database_id=database_id).get("results", [])
    if len(results) < 3:
        print(
            f"Error: Expected at least 3 entries, found {len(results)}.",
            file=sys.stderr,
        )
        return False

    # Verify entries have data
    companies_found = set()
    for page in results:
        page_properties = page.get("properties", {})

        # Get company name
        company_title_list = page_properties.get("Company", {}).get("title", [])
        company_name = (
            company_title_list[0].get("text", {}).get("content")
            if company_title_list
            else None
        )

        if company_name:
            companies_found.add(company_name)

        # Check if entry has position
        position_text = page_properties.get("Position", {}).get("rich_text", [])
        position_value = (
            position_text[0].get("text", {}).get("content") if position_text else None
        )

        if not company_name or not position_value:
            print(
                f"Error: Entry missing required data (Company: '{company_name}', Position: '{position_value}').",
                file=sys.stderr,
            )
            return False

    if len(companies_found) < 3:
        print(
            f"Error: Expected at least 3 different companies, found {len(companies_found)}.",
            file=sys.stderr,
        )
        return False

    print(
        f"Success: Found {len(results)} entries with {len(companies_found)} different companies."
    )
    return True


def main():
    """
    Executes the verification process and exits with a status code.
    """
    notion = notion_utils.get_notion_client()
    main_id = sys.argv[1] if len(sys.argv) > 1 else None
    if verify(notion, main_id):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
