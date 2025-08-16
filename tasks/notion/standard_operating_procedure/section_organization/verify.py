import sys
from notion_client import Client
from tasks.utils import notion_utils

def verify(notion: Client, main_id: str = None) -> bool:
    """
    Verifies that the Standard Operating Procedure page has been reorganized correctly.
    """
    # Step 1: Find the Standard Operating Procedure page
    if main_id:
        found_id, object_type = notion_utils.find_page_or_database_by_id(notion, main_id)
        if not found_id or object_type != 'page':
            print("Error: Standard Operating Procedure page not found.", file=sys.stderr)
            return False
    else:
        # Try to find the page by searching
        found_id = notion_utils.find_page(notion, "Standard Operating Procedure")
        if not found_id:
            print("Error: Standard Operating Procedure page not found.", file=sys.stderr)
            return False
    
    print(f"Found Standard Operating Procedure page: {found_id}")
    
    # Get all blocks from the page
    all_blocks = notion_utils.get_all_blocks_recursively(notion, found_id)
    print(f"Found {len(all_blocks)} blocks")
    
    print("Starting verification...")
    
    # Step 2: Verify the structure and section order
    print("2. Checking page structure and section order...")
    
    # Expected structure after the initial content and dividers
    # We'll look for main sections by their headings
    roles_index = None
    tools_column_index = None
    toggle_index = None
    procedure_index = None
    
    for i, block in enumerate(all_blocks):
        if block.get("type") == "heading_2":
            heading_text = ""
            rich_text = block.get("heading_2", {}).get("rich_text", [])
            if rich_text:
                heading_text = rich_text[0].get("text", {}).get("content", "")
            
            if heading_text == "Roles & responsibilities":
                roles_index = i
                print(f"✓ Found 'Roles & responsibilities' section at index {i}")
            elif heading_text == "Procedure":
                procedure_index = i
                print(f"✓ Found 'Procedure' section at index {i}")
    
    # Check for column_list (containing Tools and Terminologies)
    for i, block in enumerate(all_blocks):
        if block.get("type") == "column_list":
            # Check if this is the right column_list (should be after Roles & responsibilities)
            if roles_index and i > roles_index:
                tools_column_index = i
                print(f"✓ Found column_list at index {i}")
                break
    
    # Check for toggle block with "original pages"
    for i, block in enumerate(all_blocks):
        if block.get("type") == "toggle":
            toggle_text = ""
            rich_text = block.get("toggle", {}).get("rich_text", [])
            if rich_text:
                toggle_text = rich_text[0].get("text", {}).get("content", "")
            
            if toggle_text.lower() == "original pages":
                toggle_index = i
                print(f"✓ Found 'original pages' toggle at index {i}")
                break
    
    # Step 3: Verify section order
    print("3. Verifying section order...")
    
    if roles_index is None:
        print("Error: 'Roles & responsibilities' section not found.", file=sys.stderr)
        return False
    
    if tools_column_index is None:
        print("Error: Column layout not found.", file=sys.stderr)
        return False
    
    if toggle_index is None:
        print("Error: 'original pages' toggle not found.", file=sys.stderr)
        return False
    
    if procedure_index is None:
        print("Error: 'Procedure' section not found.", file=sys.stderr)
        return False
    
    # Verify order: Roles & responsibilities < column_list < toggle < Procedure
    if not (roles_index < tools_column_index < toggle_index < procedure_index):
        print("Error: Sections are not in the correct order.", file=sys.stderr)
        print(f"  Expected order: Roles & responsibilities ({roles_index}) < column_list ({tools_column_index}) < toggle ({toggle_index}) < Procedure ({procedure_index})", file=sys.stderr)
        return False
    
    print("✓ Sections are in the correct order")
    
    # Step 4: Verify column_list structure
    print("4. Verifying column layout structure...")
    
    column_list_block = all_blocks[tools_column_index]
    column_list_id = column_list_block.get("id")
    
    # Get direct children of column_list (should be columns only)
    try:
        column_response = notion.blocks.children.list(block_id=column_list_id)
        column_children = column_response.get("results", [])
    except Exception as e:
        print(f"Error getting column children: {e}", file=sys.stderr)
        return False
    
    if len(column_children) < 2:
        print(f"Error: Column list should have at least 2 columns, found {len(column_children)}.", file=sys.stderr)
        return False
    
    # Verify left column (Tools)
    left_column = column_children[0]
    if left_column.get("type") != "column":
        print("Error: First child of column_list should be a column.", file=sys.stderr)
        return False
    
    left_column_id = left_column.get("id")
    left_column_blocks = notion_utils.get_all_blocks_recursively(notion, left_column_id)
    
    # Check for Tools heading and link_to_page blocks in left column
    tools_heading_found = False
    link_to_page_count = 0
    for block in left_column_blocks:
        if block.get("type") == "heading_2":
            heading_text = block.get("heading_2", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "")
            if heading_text == "Tools":
                tools_heading_found = True
                print("✓ Found 'Tools' heading in left column")
        elif block.get("type") == "link_to_page":
            link_to_page_count += 1
    
    if not tools_heading_found:
        print("Error: 'Tools' heading not found in left column.", file=sys.stderr)
        return False
    
    # Check for link_to_page blocks in Tools column
    if link_to_page_count < 2:
        print(f"Error: Tools column should have at least 2 link_to_page blocks, found {link_to_page_count}.", file=sys.stderr)
        return False
    
    print(f"✓ Found {link_to_page_count} link_to_page blocks in Tools column")
    
    # Verify right column (Terminologies)
    right_column = column_children[1]
    if right_column.get("type") != "column":
        print("Error: Second child of column_list should be a column.", file=sys.stderr)
        return False
    
    right_column_id = right_column.get("id")
    right_column_blocks = notion_utils.get_all_blocks_recursively(notion, right_column_id)
    
    # Check for Terminologies heading in right column
    terminologies_heading_found = False
    for block in right_column_blocks:
        if block.get("type") == "heading_2":
            heading_text = block.get("heading_2", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "")
            if heading_text == "Terminologies":
                terminologies_heading_found = True
                print("✓ Found 'Terminologies' heading in right column")
                break
    
    if not terminologies_heading_found:
        print("Error: 'Terminologies' heading not found in right column.", file=sys.stderr)
        return False
    
    # Step 5: Verify toggle block content
    print("5. Verifying toggle block content...")
    
    toggle_block = all_blocks[toggle_index]
    toggle_id = toggle_block.get("id")
    
    # Get direct children of toggle
    try:
        toggle_response = notion.blocks.children.list(block_id=toggle_id)
        toggle_children = toggle_response.get("results", [])
    except Exception as e:
        print(f"Error getting toggle children: {e}", file=sys.stderr)
        return False
    
    # Check for child_page blocks (Notion and Figma)
    notion_page_found = False
    figma_page_found = False
    
    for block in toggle_children:
        if block.get("type") == "child_page":
            title = block.get("child_page", {}).get("title", "")
            if title == "Notion":
                notion_page_found = True
                print("✓ Found 'Notion' child page in toggle")
            elif title == "Figma":
                figma_page_found = True
                print("✓ Found 'Figma' child page in toggle")
    
    if not notion_page_found:
        print("Error: 'Notion' child page not found in toggle block.", file=sys.stderr)
        return False
    
    if not figma_page_found:
        print("Error: 'Figma' child page not found in toggle block.", file=sys.stderr)
        return False
    
    # Step 6: Verify that original sections no longer exist at top level
    print("6. Verifying original sections have been removed from top level...")
    
    # Check that there's no standalone "Terminologies" heading before "Roles & responsibilities"
    for i in range(0, roles_index if roles_index else len(all_blocks)):
        block = all_blocks[i]
        if block.get("type") == "heading_2":
            heading_text = block.get("heading_2", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "")
            if heading_text == "Terminologies":
                print("Error: 'Terminologies' section found before 'Roles & responsibilities'.", file=sys.stderr)
                return False
    
    # Check that there's no standalone "Tools" heading outside the column
    tools_outside_column = False
    for i, block in enumerate(all_blocks):
        if i == tools_column_index:
            continue  # Skip the column_list itself
        if block.get("type") == "heading_2":
            heading_text = block.get("heading_2", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "")
            if heading_text == "Tools" and i != tools_column_index:
                # Check if this is NOT inside the column
                parent_id = block.get("parent", {}).get("block_id")
                if parent_id != left_column_id:
                    tools_outside_column = True
                    break
    
    if tools_outside_column:
        print("Error: Standalone 'Tools' section found outside column layout.", file=sys.stderr)
        return False
    
    print("✓ Original sections have been properly reorganized")
    
    # Step 7: Final summary
    print("\n7. Final verification summary:")
    print("✓ 'Roles & responsibilities' and 'Terminologies' sections have been swapped")
    print("✓ 'Tools' and 'Terminologies' are in a 2-column layout")
    print("✓ Links to Notion and Figma pages are in the Tools column")
    print("✓ Original child pages are preserved in 'original pages' toggle")
    print("✓ Page structure is correct")
    
    print("\n✅ All verification checks passed!")
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