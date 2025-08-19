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
    Parse the Key|Value format from the submission body.
    This handles both the expected format from label.txt and the submission format.
    """
    data = {}
    
    # Split by lines and parse each line
    lines = text.strip().split('\n')
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
            
        # Remove bullet point if present
        if line.startswith('- '):
            line = line[2:]
        elif line.startswith('• '):
            line = line[2:]
            
        # Parse pipe-separated format
        if '|' in line:
            parts = line.split('|', 1)
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                if value and value != 'FILL_VALUE':
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
    # Also normalize apostrophes - use unicode escapes to be safe
    text = text.replace("\u2019", "'")  # RIGHT SINGLE QUOTATION MARK (')
    text = text.replace("\u2018", "'")  # LEFT SINGLE QUOTATION MARK (')

    # Normalize whitespace
    text = " ".join(text.split())

    return text.strip()


async def verify() -> bool:
    """
    Verifies that the NBA analysis task has been completed correctly.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # Navigate to the main page
            print("Navigating to forum...", file=sys.stderr)
            await page.goto("http://34.143.228.182:9999/", wait_until="networkidle")

            # Check if logged in as NBA_DataAnalyst_2024
            user_button = page.locator('button:has-text("NBA_DataAnalyst_2024")')
            if not await user_button.count():
                # Try to login
                print("Not logged in, attempting to login...", file=sys.stderr)

                await page.click('a:has-text("Log in")')
                await page.wait_for_load_state("networkidle")

                await page.fill('input[name="_username"]', "NBA_DataAnalyst_2024")
                await page.fill('input[name="_password"]', "Research#2024!")

                await page.click('button:has-text("Log in")')
                await page.wait_for_load_state("networkidle")

                user_button = page.locator('button:has-text("NBA_DataAnalyst_2024")')
                if not await user_button.count():
                    print(
                        "Error: Login failed for NBA_DataAnalyst_2024", file=sys.stderr
                    )
                    await page.screenshot(path=str(SCREENSHOT_DIR / "login_failed.png"))
                    return False

                print("Successfully logged in as NBA_DataAnalyst_2024", file=sys.stderr)
            else:
                print("Already logged in as NBA_DataAnalyst_2024", file=sys.stderr)

            # Navigate to sports forum to check submission
            print("Navigating to sports forum to check submission...", file=sys.stderr)
            await page.goto(
                "http://34.143.228.182:9999/f/sports", wait_until="networkidle"
            )

            # Look for the submission with our specific title
            print(
                "Looking for submission 'Statistical Analysis: NBA Content Engagement on This Forum'...",
                file=sys.stderr,
            )
            post_link = page.locator(
                'a:has-text("Statistical Analysis: NBA Content Engagement on This Forum")'
            )

            if not await post_link.count():
                print(
                    "Error: Could not find submission with required title",
                    file=sys.stderr,
                )
                await page.screenshot(
                    path=str(SCREENSHOT_DIR / "submission_not_found.png")
                )
                return False

            # Click on the submission to view its content
            await post_link.first.click()
            await page.wait_for_load_state("networkidle")

            # Take screenshot of the submission
            await page.screenshot(path=str(SCREENSHOT_DIR / "submission_page.png"))
            print(
                f"Screenshot saved: {SCREENSHOT_DIR / 'submission_page.png'}",
                file=sys.stderr,
            )

            # Extract the submission body content
            # Try multiple possible selectors for the post body
            post_content = None
            selectors = [
                ".submission__body",
                ".post-body",
                ".RichText",
                '[class*="RichText"]',
                'div:has(> p:has-text("Total_NBA_Posts"))',
                'div:has-text("Total_NBA_Posts"):has-text("Most_Popular_NBA_Author")',
            ]

            for selector in selectors:
                content_element = page.locator(selector)
                if await content_element.count():
                    post_content = await content_element.first.inner_text()
                    if "Total_NBA_Posts" in post_content:
                        print(
                            f"Found submission content using selector: {selector}",
                            file=sys.stderr,
                        )
                        break

            if not post_content or "Total_NBA_Posts" not in post_content:
                print(
                    "Error: Could not find submission body with required format",
                    file=sys.stderr,
                )
                await page.screenshot(
                    path=str(SCREENSHOT_DIR / "content_not_found.png")
                )
                return False

            print("Submission content found, parsing data...", file=sys.stderr)
            print(f"Raw content: {post_content[:200]}...", file=sys.stderr)

            # Parse the Key: Value format
            extracted_data = parse_key_value_format(post_content)
            print(f"Extracted data: {extracted_data}", file=sys.stderr)

            # Load expected values from label.txt
            label_path = Path(__file__).parent / "label.txt"
            if label_path.exists():
                with open(label_path, "r") as f:
                    expected_text = f.read().strip()
                expected_data = parse_key_value_format(expected_text)
                print("Loaded expected values from label.txt", file=sys.stderr)

            # Verify all required keys are present
            required_keys = [
                "Total_NBA_Posts",
                "Top1_Title",
                "Top1_Votes",
                "Top1_Comments",
                "Top1_Author",
                "Top2_Title",
                "Top2_Votes",
                "Top2_Comments",
                "Top2_Author",
                "Top3_Title",
                "Top3_Votes",
                "Top3_Comments",
                "Top3_Author",
                "Top4_Title",
                "Top4_Votes",
                "Top4_Comments",
                "Top4_Author",
                "Top5_Title",
                "Top5_Votes",
                "Top5_Comments",
                "Top5_Author",
                "BCLetsRide69_Total_Posts",
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

            # Check Total_NBA_Posts is a number and matches expected
            try:
                total_posts = int(extracted_data["Total_NBA_Posts"])
                if "expected_data" in locals() and "Total_NBA_Posts" in expected_data:
                    expected_total = int(expected_data["Total_NBA_Posts"])
                    if total_posts != expected_total:
                        errors.append(
                            f"Total_NBA_Posts mismatch: got {total_posts}, expected {expected_total}"
                        )
                elif (
                    total_posts < 5
                ):  # Should be at least 5 since we're collecting top 5
                    errors.append(f"Total_NBA_Posts seems too low: {total_posts}")
            except ValueError:
                errors.append(
                    f"Total_NBA_Posts must be a number, got: {extracted_data['Total_NBA_Posts']}"
                )

            # If we have expected data, compare against it
            if "expected_data" in locals():
                # Compare each field
                for key in required_keys:
                    if key in expected_data and key in extracted_data:
                        expected_val = normalize_text(expected_data[key])
                        actual_val = normalize_text(extracted_data[key])

                        # For numeric fields, compare as integers
                        if (
                            "Votes" in key
                            or "Comments" in key
                            or key == "Total_NBA_Posts"
                            or key == "BCLetsRide69_Total_Posts"
                        ):
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
                            if expected_val != actual_val:
                                errors.append(
                                    f"{key} mismatch: got '{actual_val}', expected '{expected_val}'"
                                )

            else:
                # If no expected data, just do basic validation
                for key in required_keys:
                    if key not in extracted_data:
                        errors.append(f"Missing required key: {key}")
                    elif (
                        not extracted_data[key] or extracted_data[key] == "[FILL_VALUE]"
                    ):
                        errors.append(f"{key} was not filled in")

            if errors:
                print(
                    "Error: Validation failed with the following issues:",
                    file=sys.stderr,
                )
                for error in errors:
                    print(f"  - {error}", file=sys.stderr)
                return False

            # Take final success screenshot
            await page.screenshot(path=str(SCREENSHOT_DIR / "verification_success.png"))
            print(
                f"Screenshot saved: {SCREENSHOT_DIR / 'verification_success.png'}",
                file=sys.stderr,
            )

            # All checks passed
            print("Success: NBA analysis task completed successfully.")
            print("- Account NBA_DataAnalyst_2024 verified")
            print(
                "- Submission 'Statistical Analysis: NBA Content Engagement on This Forum' found"
            )
            print(
                f"- Total NBA-related posts analyzed: {extracted_data['Total_NBA_Posts']}"
            )
            print("- Top 5 posts identified and documented")
            print(
                f"- BCLetsRide69's total posts: {extracted_data['BCLetsRide69_Total_Posts']}"
            )
            print("- All data in correct Key|Value format")
            return True

        except PlaywrightTimeoutError as e:
            print(f"Error: Timeout occurred - {str(e)}", file=sys.stderr)
            await page.screenshot(path=str(SCREENSHOT_DIR / "timeout_error.png"))
            return False
        except Exception as e:
            print(f"Error: Unexpected error - {str(e)}", file=sys.stderr)
            await page.screenshot(path=str(SCREENSHOT_DIR / "unexpected_error.png"))
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
