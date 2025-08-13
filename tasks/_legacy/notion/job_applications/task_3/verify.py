import sys
from notion_client import Client
from tasks.utils import notion_utils


def verify(notion: Client, main_id: str = None) -> bool:
    """
    Verifies that a two-column table has been created with correct data
    for interview stage entries.
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

    # Find the Applications database first to get interview entries
    applications_db_id = notion_utils.find_database_in_block(
        notion, page_id, "Applications"
    )
    if not applications_db_id:
        print("Error: Applications database not found.", file=sys.stderr)
        return False

    # Query for interview stage entries
    interview_filter = {"property": "Stage", "status": {"equals": "Interview"}}

    interview_results = notion.databases.query(
        database_id=applications_db_id, filter=interview_filter
    ).get("results", [])

    if len(interview_results) == 0:
        print(
            "Warning: No interview stage entries found in Applications database.",
            file=sys.stderr,
        )
        expected_rows = 0
    else:
        expected_rows = len(interview_results)
        print(f"Found {expected_rows} interview entries to verify.")

    # Get all blocks from the Job Applications page
    all_blocks = notion_utils.get_all_blocks_recursively(notion, page_id)

    # Find table blocks
    table_blocks = [block for block in all_blocks if block.get("type") == "table"]

    if not table_blocks:
        print("Error: No table block found in Job Applications page.", file=sys.stderr)
        return False

    if len(table_blocks) > 1:
        print("Warning: Multiple table blocks found, checking the first one.")

    table_block = table_blocks[0]
    table_id = table_block["id"]

    # Check table properties
    table_props = table_block.get("table", {})
    table_width = table_props.get("table_width", 0)

    if table_width != 2:
        print(
            f"Error: Table should have 2 columns, found {table_width}.", file=sys.stderr
        )
        return False

    print("Success: Found table with 2 columns.")

    # Get table rows
    table_children = notion.blocks.children.list(block_id=table_id).get("results", [])
    table_rows = [block for block in table_children if block.get("type") == "table_row"]
    # Should have header row + data rows
    expected_total_rows = expected_rows + 1  # +1 for header
    if len(table_rows) < expected_total_rows:
        print(
            f"Error: Expected {expected_total_rows} table rows (1 header + {expected_rows} data), found {len(table_rows)}.",
            file=sys.stderr,
        )
        return False

    # Check header row
    header_row = table_rows[0]
    header_cells = header_row.get("table_row", {}).get("cells", [])

    if len(header_cells) < 2:
        print("Error: Header row should have 2 cells.", file=sys.stderr)
        return False

    # Check header content
    header1_text = "".join(rt.get("plain_text", "") for rt in header_cells[0])
    header2_text = "".join(rt.get("plain_text", "") for rt in header_cells[1])

    if header1_text.strip() != "Company":
        print(
            f"Error: First header should be 'Company', found '{header1_text}'.",
            file=sys.stderr,
        )
        return False

    if header2_text.strip() != "Date":
        print(
            f"Error: Second header should be 'Date', found '{header2_text}'.",
            file=sys.stderr,
        )
        return False

    print("Success: Header row has correct 'Company' and 'Date' columns.")

    # Get expected interview data
    interview_data = {}
    for entry in interview_results:
        company_title_list = (
            entry.get("properties", {}).get("Company", {}).get("title", [])
        )
        company_name = (
            company_title_list[0].get("text", {}).get("content")
            if company_title_list
            else None
        )

        date_prop = entry.get("properties", {}).get("Appl Date", {}).get("date")
        date_value = date_prop.get("start") if date_prop else None

        if company_name:
            interview_data[company_name] = date_value

    # Check data rows (skip header)
    table_companies = set()
    valid_dates = 0

    for row in table_rows[1:]:  # Skip header row
        cells = row.get("table_row", {}).get("cells", [])
        if len(cells) >= 2:
            # First cell: company name
            company_text = "".join(rt.get("plain_text", "") for rt in cells[0]).strip()

            # Second cell: date
            date_text = "".join(rt.get("plain_text", "") for rt in cells[1]).strip()

            if company_text:
                table_companies.add(company_text)

                # Verify date matches expected
                expected_date = interview_data.get(company_text)
                if expected_date and date_text:
                    # Convert ISO date to readable format for comparison
                    from datetime import datetime

                    try:
                        iso_date = datetime.strptime(expected_date, "%Y-%m-%d")
                        readable_date = iso_date.strftime("%b %d, %Y")
                        if date_text == readable_date or date_text == expected_date:
                            valid_dates += 1
                        else:
                            print(
                                f"Warning: Date format mismatch for {company_text}: expected '{readable_date}', found '{date_text}'"
                            )
                    except ValueError:
                        # If date parsing fails, do basic string comparison
                        if date_text == expected_date:
                            valid_dates += 1
                elif expected_date:
                    print(
                        f"Warning: Missing date for {company_text} (expected '{expected_date}')"
                    )

    # Verify all interview companies are in table
    missing_companies = set(interview_data.keys()) - table_companies
    if missing_companies:
        print(
            f"Error: Missing companies in table: {missing_companies}", file=sys.stderr
        )
        return False

    if valid_dates < expected_rows:
        print(
            f"Error: Expected {expected_rows} valid dates, found {valid_dates}.",
            file=sys.stderr,
        )
        return False

    print(
        f"Success: Table contains all {len(interview_data)} interview companies with correct dates."
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
