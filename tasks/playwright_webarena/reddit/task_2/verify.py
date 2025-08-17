import asyncio
import sys
import re
from pathlib import Path
from playwright.async_api import (
    async_playwright,
    TimeoutError as PlaywrightTimeoutError,
)

# Directory for screenshots
SCREENSHOT_DIR = Path("/home/liuxiangyan6/eval-sys/mcp-arena/verification_screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)


def parse_markdown_list_format(text):
    """
    Parse the markdown list format (- Key|Value) from the submission body.
    Also handles plain Key|Value format without the dash.
    """
    data = {}
    
    # Pattern to match lines like: - Key|Value or just Key|Value
    pattern = r'^(?:-\s*)?([^|]+)\|(.+)$'
    
    lines = text.strip().split('\n')
    for line in lines:
        line = line.strip()
        if '|' in line:
            match = re.match(pattern, line)
            if match:
                key = match.group(1).strip()
                value = match.group(2).strip()
                data[key] = value
    
    return data


def normalize_text(text):
    """
    Normalize text for comparison by handling different quote styles and whitespace.
    """
    if not isinstance(text, str):
        return str(text)

    # Replace various quote styles with standard quotes
    text = text.replace(""", "'").replace(""", "'")
    text = text.replace('"', '"').replace('"', '"')

    # Normalize whitespace
    text = " ".join(text.split())

    return text.strip()


async def check_account_login(page):
    """
    Check if the account can be successfully logged in.
    Returns True if login successful, False otherwise.
    """
    try:
        # Navigate to main page
        await page.goto("http://34.143.228.182:9999/", wait_until="networkidle")
        
        # Check if already logged in
        user_button = page.locator('button[class*="UserButton"]')
        if await user_button.count():
            username = await user_button.inner_text()
            if username.lower() == "buyitforlife_researcher":
                print(f"Already logged in as {username}", file=sys.stderr)
                return True
            else:
                # Log out first
                await user_button.click()
                await page.click('a:has-text("Log out")')
                await page.wait_for_load_state("networkidle")
        
        # Try to login
        await page.click('a:has-text("Log in")')
        await page.wait_for_load_state("networkidle")
        
        await page.fill('input[name="_username"]', "buyitforlife_researcher")
        await page.fill('input[name="_password"]', "BIFL2024Research!")
        
        await page.click('button:has-text("Log in")')
        await page.wait_for_load_state("networkidle")
        
        # Check if login successful
        user_button = page.locator('button:has-text("buyitforlife_researcher")')
        if await user_button.count():
            print("Successfully logged in as buyitforlife_researcher", file=sys.stderr)
            return True
        else:
            print("Login failed for buyitforlife_researcher", file=sys.stderr)
            return False
            
    except Exception as e:
        print(f"Error during login check: {str(e)}", file=sys.stderr)
        return False


async def check_submission_exists(page):
    """
    Check if the submission exists in the BuyItForLife forum with correct content.
    Returns (exists, content_data) tuple.
    """
    try:
        # Navigate to BuyItForLife forum
        await page.goto("http://34.143.228.182:9999/f/BuyItForLife", wait_until="networkidle")
        
        # Look for the post with correct title
        print("Looking for post 'Research Report for BuyItForLife'...", file=sys.stderr)
        post_locator = page.locator('a:has-text("Research Report for BuyItForLife")')
        
        if not await post_locator.count():
            print("Error: Could not find post with title 'Research Report for BuyItForLife'", file=sys.stderr)
            return False, None
        
        # Click on the post to view its content
        await post_locator.first.click()
        await page.wait_for_load_state("networkidle")
        
        # Get the post content
        post_content = None
        selectors = [
            '.PostFullItem-body',
            '.Post-body',
            '.PostItem-body',
            '.item-RichText',
            '[class*="RichText"]',
            'div:has-text("Post1_Title")',
        ]
        
        for selector in selectors:
            post_content_element = page.locator(selector)
            if await post_content_element.count():
                # Get the text content, handling multiple elements if needed
                if await post_content_element.count() > 1:
                    for i in range(await post_content_element.count()):
                        text = await post_content_element.nth(i).inner_text()
                        if "Post1_Title" in text:
                            post_content = text
                            print(f"Found post content using selector: {selector} (element {i})", file=sys.stderr)
                            break
                else:
                    post_content = await post_content_element.first.inner_text()
                    print(f"Found post content using selector: {selector}", file=sys.stderr)
                
                if post_content and "Post1_Title" in post_content:
                    break
        
        if not post_content:
            print("Error: Could not find post content element", file=sys.stderr)
            return False, None
        
        print("Post content found:", file=sys.stderr)
        print(post_content[:200] + "..." if len(post_content) > 200 else post_content, file=sys.stderr)
        
        # Parse the markdown list format
        extracted_data = parse_markdown_list_format(post_content)
        print(f"Extracted data: {extracted_data}", file=sys.stderr)
        
        return True, extracted_data
        
    except Exception as e:
        print(f"Error checking submission: {str(e)}", file=sys.stderr)
        return False, None


async def verify() -> bool:
    """
    Verifies that the BuyItForLife research task has been completed correctly.
    Checks:
    1. Account creation (can login with credentials)
    2. Submission exists with correct title
    3. Submission content matches expected format and values
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Step 1: Check account creation
            print("=== Step 1: Checking account creation ===", file=sys.stderr)
            account_ok = await check_account_login(page)
            if not account_ok:
                print("Error: Account 'buyitforlife_researcher' cannot be logged in", file=sys.stderr)
                await page.screenshot(path=str(SCREENSHOT_DIR / "task2_login_failed.png"))
                return False
            
            # Step 2: Check submission exists and get content
            print("\n=== Step 2: Checking submission ===", file=sys.stderr)
            submission_exists, extracted_data = await check_submission_exists(page)
            
            if not submission_exists:
                print("Error: Submission not found in BuyItForLife forum", file=sys.stderr)
                await page.screenshot(path=str(SCREENSHOT_DIR / "task2_submission_not_found.png"))
                return False
            
            if not extracted_data:
                print("Error: Could not extract data from submission", file=sys.stderr)
                await page.screenshot(path=str(SCREENSHOT_DIR / "task2_no_data_extracted.png"))
                return False
            
            # Step 3: Load expected data from label.txt
            print("\n=== Step 3: Validating submission content ===", file=sys.stderr)
            label_path = Path(__file__).parent / "label.txt"
            if not label_path.exists():
                print("Error: label.txt not found", file=sys.stderr)
                return False
            
            with open(label_path, "r") as f:
                expected_text = f.read().strip()
            expected_data = parse_markdown_list_format(expected_text)
            print(f"Expected data from label.txt: {expected_data}", file=sys.stderr)
            
            # Verify all required keys are present
            required_keys = [
                "Post1_Title",
                "Post1_Upvotes",
                "Post1_Comments",
                "Post2_Title",
                "Post2_Upvotes",
                "Post2_Comments",
                "Post3_Title",
                "Post3_Upvotes",
                "Post3_Comments",
                "TopComment_Text",
                "TopComment_Username",
                "Post1_Author",
                "Post2_Author",
                "Post3_Author",
            ]
            
            missing_keys = []
            for key in required_keys:
                if key not in extracted_data:
                    missing_keys.append(key)
            
            if missing_keys:
                print(f"Error: Missing required keys: {', '.join(missing_keys)}", file=sys.stderr)
                await page.screenshot(path=str(SCREENSHOT_DIR / "task2_missing_keys.png"))
                return False
            
            # Compare each field with expected values
            errors = []
            for key in required_keys:
                if key in expected_data and key in extracted_data:
                    expected_val = normalize_text(expected_data[key])
                    actual_val = normalize_text(extracted_data[key])
                    
                    # For numeric fields, compare as integers
                    if "Upvotes" in key or "Comments" in key:
                        try:
                            expected_int = int(expected_val)
                            actual_int = int(actual_val)
                            if expected_int != actual_int:
                                errors.append(f"{key} mismatch: got {actual_int}, expected {expected_int}")
                        except ValueError:
                            errors.append(f"{key} should be numeric: got '{actual_val}'")
                    else:
                        # For text fields, special handling for usernames with underscores
                        if "Author" in key or key == "TopComment_Username":
                            # Handle cases where underscores might be interpreted as markdown emphasis
                            # Compare without leading/trailing underscores
                            expected_core = expected_val.strip('_')
                            actual_core = actual_val.strip('_')
                            if expected_core != actual_core:
                                errors.append(f"{key} mismatch: got '{actual_val}', expected '{expected_val}'")
                        else:
                            # For other text fields, exact comparison
                            if expected_val != actual_val:
                                errors.append(f"{key} mismatch: got '{actual_val}', expected '{expected_val}'")
            
            # Verify upvotes are in descending order
            try:
                post1_votes = int(extracted_data["Post1_Upvotes"])
                post2_votes = int(extracted_data["Post2_Upvotes"])
                post3_votes = int(extracted_data["Post3_Upvotes"])
                
                if not (post1_votes >= post2_votes >= post3_votes):
                    errors.append(f"Posts should be ordered by upvotes: {post1_votes} >= {post2_votes} >= {post3_votes}")
            except (ValueError, KeyError):
                pass  # Already reported above
            
            if errors:
                print("Error: Validation failed with the following issues:", file=sys.stderr)
                for error in errors:
                    print(f"  - {error}", file=sys.stderr)
                await page.screenshot(path=str(SCREENSHOT_DIR / "task2_validation_failed.png"))
                return False
            
            # All checks passed
            await page.screenshot(path=str(SCREENSHOT_DIR / "task2_verification_success.png"))
            print("\n=== SUCCESS ===", file=sys.stderr)
            print("✓ Account 'buyitforlife_researcher' created and can login", file=sys.stderr)
            print("✓ Submission 'Research Report for BuyItForLife' found in correct forum", file=sys.stderr)
            print("✓ All 14 required fields present and correct", file=sys.stderr)
            print("✓ Data matches expected values from label.txt", file=sys.stderr)
            print("✓ Posts ordered by upvotes (descending)", file=sys.stderr)
            return True
            
        except PlaywrightTimeoutError as e:
            print(f"Error: Timeout occurred - {str(e)}", file=sys.stderr)
            await page.screenshot(path=str(SCREENSHOT_DIR / "task2_timeout_error.png"))
            return False
        except Exception as e:
            print(f"Error: Unexpected error - {str(e)}", file=sys.stderr)
            await page.screenshot(path=str(SCREENSHOT_DIR / "task2_unexpected_error.png"))
            return False
        finally:
            await browser.close()


def main():
    """
    Executes the verification process and exits with a status code.
    """
    result = asyncio.run(verify())
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()