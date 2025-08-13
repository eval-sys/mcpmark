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


def parse_key_value_format(text):
    """
    Parse the Key: Value format from the submission body using regex.
    Works regardless of line breaks.
    """
    data = {}

    # Define patterns for each field
    patterns = {
        "Post1_Title": r"Post1_Title:\s*(.+?)\s*Post1_Upvotes:",
        "Post1_Upvotes": r"Post1_Upvotes:\s*(\d+)",
        "Post1_Comments": r"Post1_Comments:\s*(\d+)",
        "Post2_Title": r"Post2_Title:\s*(.+?)\s*Post2_Upvotes:",
        "Post2_Upvotes": r"Post2_Upvotes:\s*(\d+)",
        "Post2_Comments": r"Post2_Comments:\s*(\d+)",
        "Post3_Title": r"Post3_Title:\s*(.+?)\s*Post3_Upvotes:",
        "Post3_Upvotes": r"Post3_Upvotes:\s*(\d+)",
        "Post3_Comments": r"Post3_Comments:\s*(\d+)",
        "TopComment_Text": r"TopComment_Text:\s*(.+?)\s*TopComment_Username:",
        "TopComment_Username": r"TopComment_Username:\s*(.+?)\s*Post1_Author:",
        "Post1_Author": r"Post1_Author:\s*(.+?)\s*Post2_Author:",
        "Post2_Author": r"Post2_Author:\s*(.+?)\s*Post3_Author:",
        "Post3_Author": r"Post3_Author:\s*(.+?)(?:\s*$|\n)",
    }

    # Extract each field using regex
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.DOTALL)
        if match:
            data[key] = match.group(1).strip()

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


async def verify() -> bool:
    """
    Verifies that the BuyItForLife extraction task has been completed correctly by checking the forum post.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True
        )  # Set to True for server environment
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # Navigate to the main page
            print("Navigating to forum...", file=sys.stderr)
            await page.goto("http://35.247.158.69:9999/", wait_until="networkidle")

            # Take screenshot after navigation
            await page.screenshot(path=str(SCREENSHOT_DIR / "task1_main_page.png"))
            print(
                f"Screenshot saved: {SCREENSHOT_DIR / 'task1_main_page.png'}",
                file=sys.stderr,
            )

            # Check if logged in (any user is fine for verification)
            user_button = page.locator('button[class*="UserButton"]')
            if await user_button.count():
                username = await user_button.inner_text()
                print(f"Already logged in as {username}", file=sys.stderr)
            else:
                # Try to login with buyitforlife_researcher account
                print(
                    "Not logged in, attempting to login with buyitforlife_researcher...",
                    file=sys.stderr,
                )

                try:
                    await page.click('a:has-text("Log in")')
                    await page.wait_for_load_state("networkidle")

                    await page.fill(
                        'input[name="_username"]', "buyitforlife_researcher"
                    )
                    await page.fill('input[name="_password"]', "BIFL2024Research!")

                    await page.click('button:has-text("Log in")')
                    await page.wait_for_load_state("networkidle")

                    user_button = page.locator(
                        'button:has-text("buyitforlife_researcher")'
                    )
                    if await user_button.count():
                        print(
                            "Successfully logged in as buyitforlife_researcher",
                            file=sys.stderr,
                        )
                    else:
                        print(
                            "Warning: Login failed, will continue without login to check if post exists",
                            file=sys.stderr,
                        )
                except Exception as e:
                    print(
                        f"Warning: Could not login ({str(e)}), continuing without login",
                        file=sys.stderr,
                    )

            # Click on Forums link first
            print("Clicking on Forums link...", file=sys.stderr)
            await page.click('a:has-text("Forums")')
            await page.wait_for_load_state("networkidle")

            # Navigate to BuyItForLife forum
            print("Navigating to BuyItForLife forum...", file=sys.stderr)
            # Try multiple ways to navigate to BuyItForLife forum
            try:
                await page.click('a:has-text("BuyItForLife")', timeout=5000)
                await page.wait_for_load_state("networkidle")
            except:
                # Try alternative approach
                await page.goto(
                    "http://35.247.158.69:9999/f/buyitforlife", wait_until="networkidle"
                )

            # Take screenshot of the forum
            await page.screenshot(
                path=str(SCREENSHOT_DIR / "task1_buyitforlife_forum.png")
            )
            print(
                f"Screenshot saved: {SCREENSHOT_DIR / 'task1_buyitforlife_forum.png'}",
                file=sys.stderr,
            )

            # Look for the post with title "BuyItForLife"
            print("Looking for post 'BuyItForLife'...", file=sys.stderr)
            post_locator = page.locator('a:has-text("BuyItForLife")')

            if not await post_locator.count():
                print(
                    "Error: Could not find post with title 'BuyItForLife'",
                    file=sys.stderr,
                )
                await page.screenshot(
                    path=str(SCREENSHOT_DIR / "task1_post_not_found.png")
                )
                return False

            # Click on the post to view its content
            await post_locator.first.click()
            await page.wait_for_load_state("networkidle")

            # Take screenshot of the post
            await page.screenshot(path=str(SCREENSHOT_DIR / "task1_post_page.png"))
            print(
                f"Screenshot saved: {SCREENSHOT_DIR / 'task1_post_page.png'}",
                file=sys.stderr,
            )

            # Get the post content - try multiple selectors
            post_content = None
            selectors = [
                'div:has(> span:has-text("Submitted by"))',  # The div containing the post content
                ".PostFullItem-body",
                ".Post-body",
                ".PostItem-body",
                ".item-RichText",
                '[class*="RichText"]',
                'div:has-text("Post1_Title")',  # Look for div containing our key-value format
            ]

            for selector in selectors:
                post_content_element = page.locator(selector)
                if await post_content_element.count():
                    # Get the text content, handling multiple elements if needed
                    if await post_content_element.count() > 1:
                        # Try each element to find the one with our content
                        for i in range(await post_content_element.count()):
                            text = await post_content_element.nth(i).inner_text()
                            if "Post1_Title" in text:
                                post_content = text
                                print(
                                    f"Found post content using selector: {selector} (element {i})",
                                    file=sys.stderr,
                                )
                                break
                    else:
                        post_content = await post_content_element.first.inner_text()
                        print(
                            f"Found post content using selector: {selector}",
                            file=sys.stderr,
                        )

                    if post_content and "Post1_Title" in post_content:
                        break

            if not post_content:
                print("Error: Could not find post content element", file=sys.stderr)
                await page.screenshot(
                    path=str(SCREENSHOT_DIR / "task1_no_content_found.png")
                )
                return False

            print("Post content found:", file=sys.stderr)
            print(
                post_content[:200] + "..." if len(post_content) > 200 else post_content,
                file=sys.stderr,
            )

            # Parse the Key: Value format
            extracted_data = parse_key_value_format(post_content)
            print(f"Extracted data: {extracted_data}", file=sys.stderr)

            # Load the label.txt for comparison
            label_path = Path(__file__).parent / "label.txt"
            if label_path.exists():
                with open(label_path, "r") as f:
                    expected_text = f.read().strip()
                expected_data = parse_key_value_format(expected_text)
                print("Loaded expected values from label.txt", file=sys.stderr)
            else:
                print(
                    "Warning: label.txt not found, skipping value comparison",
                    file=sys.stderr,
                )
                expected_data = {}

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
                print(
                    f"Error: Missing required keys: {', '.join(missing_keys)}",
                    file=sys.stderr,
                )
                return False

            # Validate data format and content
            errors = []

            # If we have expected data, compare against it
            if expected_data:
                # Compare each field
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
                                    errors.append(
                                        f"{key} mismatch: got {actual_int}, expected {expected_int}"
                                    )
                            except ValueError:
                                errors.append(
                                    f"{key} should be numeric: got '{actual_val}'"
                                )
                        else:
                            # For text fields, compare normalized text
                            if expected_val.lower() != actual_val.lower():
                                # Allow some flexibility for titles and comments with quotes
                                if key in [
                                    "Post1_Title",
                                    "Post2_Title",
                                    "Post3_Title",
                                    "TopComment_Text",
                                ]:
                                    # Remove all quotes for comparison
                                    expected_no_quotes = (
                                        expected_val.replace("'", "")
                                        .replace('"', "")
                                        .lower()
                                    )
                                    actual_no_quotes = (
                                        actual_val.replace("'", "")
                                        .replace('"', "")
                                        .lower()
                                    )
                                    if expected_no_quotes != actual_no_quotes:
                                        errors.append(
                                            f"{key} mismatch: got '{actual_val}', expected '{expected_val}'"
                                        )
                                elif "Author" in key or key == "TopComment_Username":
                                    # For usernames, check if they match when removing underscores from start/end
                                    expected_core = expected_val.strip("_").lower()
                                    actual_core = actual_val.strip("_").lower()
                                    if expected_core != actual_core:
                                        errors.append(
                                            f"{key} mismatch: got '{actual_val}', expected '{expected_val}'"
                                        )
                                else:
                                    errors.append(
                                        f"{key} mismatch: got '{actual_val}', expected '{expected_val}'"
                                    )
            else:
                # If no expected data, just do basic validation
                for key in required_keys:
                    if not extracted_data[key] or extracted_data[key] == "[FILL_VALUE]":
                        errors.append(f"{key} was not filled in")

            # Verify upvotes are in descending order for posts
            try:
                post1_votes = int(extracted_data["Post1_Upvotes"])
                post2_votes = int(extracted_data["Post2_Upvotes"])
                post3_votes = int(extracted_data["Post3_Upvotes"])

                if not (post1_votes >= post2_votes >= post3_votes):
                    errors.append(
                        f"Posts should be ordered by upvotes: {post1_votes} >= {post2_votes} >= {post3_votes}"
                    )
            except (ValueError, KeyError):
                pass  # Already reported above

            if errors:
                print(
                    "Error: Validation failed with the following issues:",
                    file=sys.stderr,
                )
                for error in errors:
                    print(f"  - {error}", file=sys.stderr)
                return False

            # Take final success screenshot
            await page.screenshot(
                path=str(SCREENSHOT_DIR / "task1_verification_success.png")
            )
            print(
                f"Screenshot saved: {SCREENSHOT_DIR / 'task1_verification_success.png'}",
                file=sys.stderr,
            )

            # All checks passed
            print("Success: BuyItForLife extraction task completed successfully.")
            print("- Post 'BuyItForLife' found and verified")
            print("- Top 3 posts extracted with correct titles, upvotes, and comments")
            print("- Top comment from highest post captured correctly")
            print("- All post authors identified correctly")
            print("- All data in correct Key: Value format with 14 lines")
            return True

        except PlaywrightTimeoutError as e:
            print(f"Error: Timeout occurred - {str(e)}", file=sys.stderr)
            await page.screenshot(path=str(SCREENSHOT_DIR / "task1_timeout_error.png"))
            return False
        except Exception as e:
            print(f"Error: Unexpected error - {str(e)}", file=sys.stderr)
            await page.screenshot(
                path=str(SCREENSHOT_DIR / "task1_unexpected_error.png")
            )
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
