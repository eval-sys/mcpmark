import sys
from notion_client import Client
from tasks.utils import notion_utils


def verify(notion: Client, main_id: str = None) -> bool:
    """
    Verifies that the 'Type' property has been added to the Applications database
    and that entries are correctly populated based on company names.
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

    # Find the Applications database
    database_id = notion_utils.find_database_in_block(notion, page_id, "Applications")
    if not database_id:
        print(
            "Error: Database 'Applications' not found in Job Applications page.",
            file=sys.stderr,
        )
        return False

    # Check if Type property exists in database schema and is text type
    database = notion.databases.retrieve(database_id=database_id)
    properties = database.get("properties", {})

    if "Type" not in properties:
        print(
            "Error: 'Type' property not found in Applications database.",
            file=sys.stderr,
        )
        return False

    if properties["Type"].get("type") != "rich_text":
        print("Error: 'Type' property is not a text property.", file=sys.stderr)
        return False

    print("Success: 'Type' text property found in database schema.")

    # Query all entries in the database
    results = notion.databases.query(database_id=database_id).get("results", [])
    if not results:
        print("Warning: No entries found in Applications database.", file=sys.stderr)
        return True

    # Verify Type property values based on company names
    correct_entries = 0
    total_entries = len(results)

    for page in results:
        page_properties = page.get("properties", {})

        # Get company name
        company_title_list = page_properties.get("Company", {}).get("title", [])
        company_name = (
            company_title_list[0].get("text", {}).get("content")
            if company_title_list
            else None
        )

        # Get Type value (text property)
        type_rich_text = page_properties.get("Type", {}).get("rich_text", [])
        type_value = (
            type_rich_text[0].get("text", {}).get("content") if type_rich_text else None
        )

        # Check if Type is correctly assigned
        expected_type = "A" if company_name == "24S" else ""

        if type_value == expected_type:
            correct_entries += 1
            print(f"✓ Company '{company_name}' has correct Type '{type_value}'")
        else:
            print(
                f"✗ Company '{company_name}' has incorrect Type '{type_value}', expected '{expected_type}'",
                file=sys.stderr,
            )

    if correct_entries == total_entries:
        print(f"Success: All {total_entries} entries have correct Type values.")
        return True
    else:
        print(
            f"Failure: {correct_entries}/{total_entries} entries have correct Type values.",
            file=sys.stderr,
        )
        return False


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
