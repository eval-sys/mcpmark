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
        "Deeplearning_Post_Count": r"Deeplearning_Post_Count:\s*(\d+)",
        "ChatGPT_Tool_Vote_Count": r"ChatGPT_Tool_Vote_Count:\s*(\d+)",
        "Transformer_Third_Result": r"Transformer_Third_Result:\s*(.+?)(?=\s*Page2_Top_Post_Title:)",
        "Page2_Top_Post_Title": r"Page2_Top_Post_Title:\s*(.+?)(?=\s*Page2_Top_Post_Votes:)",
        "Page2_Top_Post_Votes": r"Page2_Top_Post_Votes:\s*(\d+)",
        "Page2_Last_Comment_Username": r"Page2_Last_Comment_Username:\s*(.+?)(?=\s*Page2_Last_Comment_Text:)",
        "Page2_Last_Comment_Text": r"Page2_Last_Comment_Text:\s*(.+?)(?=\s*$)",
    }

    # Extract each field using regex
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.DOTALL | re.MULTILINE)
        if match:
            # For text fields, clean up newlines and extra spaces
            value = match.group(1).strip()
            if key not in [
                "Deeplearning_Post_Count",
                "ChatGPT_Tool_Vote_Count",
                "Page2_Top_Post_Votes",
            ]:
                # Replace newlines with spaces and normalize whitespace
                value = " ".join(value.split())
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


async def verify() -> bool:
    """
    Verifies that the ML extraction task has been completed correctly by checking the forum post.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # Navigate to the main page
            print("Navigating to forum...", file=sys.stderr)
            await page.goto("http://35.247.158.69:9999/", wait_until="networkidle")

            # Check if already logged in
            user_button = page.locator('button:has-text("AIDataAnalyst2025")')
            if not await user_button.count():
                # Try to login
                print("Not logged in, attempting to login...", file=sys.stderr)

                # Click login link
                await page.click('a:has-text("Log in")')
                await page.wait_for_load_state("networkidle")

                # Fill login form
                await page.fill('input[name="_username"]', "AIDataAnalyst2025")
                await page.fill('input[name="_password"]', "SecurePass123!")

                # Submit login form
                await page.click('button:has-text("Log in")')
                await page.wait_for_load_state("networkidle")

                # Check if login successful
                user_button = page.locator('button:has-text("AIDataAnalyst2025")')
                if not await user_button.count():
                    print("Error: Login failed for AIDataAnalyst2025", file=sys.stderr)
                    await page.screenshot(path=str(SCREENSHOT_DIR / "login_failed.png"))
                    return False

                print("Successfully logged in as AIDataAnalyst2025", file=sys.stderr)
            else:
                print("Already logged in as AIDataAnalyst2025", file=sys.stderr)

            # Navigate to MachineLearning forum
            print("Navigating to MachineLearning forum...", file=sys.stderr)
            await page.goto(
                "http://35.247.158.69:9999/f/machinelearning", wait_until="networkidle"
            )

            # Look for the post with title "MachineLearning_Extraction"
            print(
                "Looking for submission 'MachineLearning_Extraction'...",
                file=sys.stderr,
            )
            post_link = page.locator('a:has-text("MachineLearning_Extraction")')

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
                'div:has(> p:has-text("Deeplearning_Post_Count"))',
                'div:has-text("Deeplearning_Post_Count"):has-text("Page2_Last_Comment_Text")',
            ]

            for selector in selectors:
                content_element = page.locator(selector)
                if await content_element.count():
                    post_content = await content_element.first.inner_text()
                    if "Deeplearning_Post_Count" in post_content:
                        print(
                            f"Found submission content using selector: {selector}",
                            file=sys.stderr,
                        )
                        break

            if not post_content or "Deeplearning_Post_Count" not in post_content:
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
                "Deeplearning_Post_Count",
                "ChatGPT_Tool_Vote_Count",
                "Transformer_Third_Result",
                "Page2_Top_Post_Title",
                "Page2_Top_Post_Votes",
                "Page2_Last_Comment_Username",
                "Page2_Last_Comment_Text",
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

            # Check numeric fields
            try:
                post_count = int(extracted_data["Deeplearning_Post_Count"])
                if (
                    "expected_data" in locals()
                    and "Deeplearning_Post_Count" in expected_data
                ):
                    expected_count = int(expected_data["Deeplearning_Post_Count"])
                    if post_count != expected_count:
                        errors.append(
                            f"Deeplearning_Post_Count mismatch: got {post_count}, expected {expected_count}"
                        )
            except ValueError:
                errors.append(
                    f"Deeplearning_Post_Count must be a number, got: {extracted_data['Deeplearning_Post_Count']}"
                )

            # If we have expected data, compare against it
            if "expected_data" in locals():
                # Compare each field
                for key in required_keys:
                    if key in expected_data and key in extracted_data:
                        expected_val = normalize_text(expected_data[key])
                        actual_val = normalize_text(extracted_data[key])

                        # For numeric fields, compare as integers
                        if key in [
                            "Deeplearning_Post_Count",
                            "ChatGPT_Tool_Vote_Count",
                            "Page2_Top_Post_Votes",
                        ]:
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
            print("Success: ML extraction task completed successfully.")
            print("- Account AIDataAnalyst2025 verified")
            print("- Submission 'MachineLearning_Extraction' found")
            print(
                f"- Deeplearning forum post count: {extracted_data['Deeplearning_Post_Count']}"
            )
            print(
                f"- ChatGPT tool post vote count: {extracted_data['ChatGPT_Tool_Vote_Count']}"
            )
            print(
                f"- Third transformer search result: {extracted_data['Transformer_Third_Result']}"
            )
            print(
                f"- Page 2 highest upvoted post captured with {extracted_data['Page2_Top_Post_Votes']} votes"
            )
            print(
                f"- Last comment by {extracted_data['Page2_Last_Comment_Username']}: {extracted_data['Page2_Last_Comment_Text']}"
            )
            print("- All data in correct Key: Value format with 7 lines")
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
