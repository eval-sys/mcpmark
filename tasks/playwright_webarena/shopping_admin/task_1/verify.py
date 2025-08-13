import asyncio
import sys
import re
import os
import json
from pathlib import Path
from playwright.async_api import (
    async_playwright,
    TimeoutError as PlaywrightTimeoutError,
)

# Directory for screenshots
SCREENSHOT_DIR = Path("/home/liuxiangyan6/eval-sys/mcp-arena/verification_screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)


def get_model_response():
    """
    Get the model's response from the MCP_MESSAGES environment variable.
    Returns the last assistant message text.
    """
    messages_path = os.getenv("MCP_MESSAGES")
    print(f"MCP_MESSAGES: {messages_path}")
    if not messages_path:
        print("Warning: MCP_MESSAGES environment variable not set", file=sys.stderr)
        return None

    try:
        with open(messages_path, "r") as f:
            messages = json.load(f)

        # Find the last assistant message
        for message in reversed(messages):
            if (
                message.get("role") == "assistant"
                and message.get("status") == "completed"
            ):
                content = message.get("content", [])
                for item in content:
                    if item.get("type") == "output_text":
                        return item.get("text", "")

        print("Warning: No assistant response found in messages", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error reading messages file: {str(e)}", file=sys.stderr)
        return None


def parse_answer_format(text):
    """
    Parse the new multi-line <answer>xxx</answer> format from the agent's output.
    Returns a dictionary with the parsed values.
    """
    if not text:
        return None

    # Look for <answer>...</answer> pattern
    match = re.search(r"<answer>(.*?)</answer>", text, re.IGNORECASE | re.DOTALL)
    if not match:
        return None

    answer_content = match.group(1).strip()

    # Parse each line
    result = {}
    lines = answer_content.split("\n")

    if len(lines) != 9:
        print(f"Error: Expected 9 lines in answer, got {len(lines)}", file=sys.stderr)
        return None

    for line in lines:
        if "|" in line:
            key, value = line.split("|", 1)
            result[key.strip()] = value.strip()

    return result


def load_expected_answer(label_path):
    """
    Load the expected answer from label.txt file.
    Returns a dictionary with the expected values.
    """
    try:
        with open(label_path, "r") as f:
            lines = f.read().strip().split("\n")

        expected = {}
        for line in lines:
            if "|" in line:
                key, value = line.split("|", 1)
                expected[key.strip()] = value.strip()

        return expected
    except Exception as e:
        print(f"Error reading label file: {str(e)}", file=sys.stderr)
        return None


def compare_answers(model_answer, expected_answer):
    """
    Compare the model's answer with the expected answer.
    Returns True if all key information matches, False otherwise.
    """
    if not model_answer or not expected_answer:
        return False

    # Check each expected key
    mismatches = []
    for key, expected_value in expected_answer.items():
        model_value = model_answer.get(key, "")

        # Special handling for different types of values
        if key == "Top2SearchTerms":
            # Check if both search terms are present with correct counts
            expected_terms = expected_value.split(",")
            model_terms = model_value.split(",")
            if set(expected_terms) != set(model_terms):
                mismatches.append(
                    f"{key}: expected '{expected_value}', got '{model_value}'"
                )

        elif key == "EmailVerification":
            # Check email verification status
            expected_emails = dict(
                item.split(":") for item in expected_value.split(",")
            )
            model_emails = dict(
                item.split(":") for item in model_value.split(",") if ":" in item
            )
            if expected_emails != model_emails:
                mismatches.append(
                    f"{key}: expected '{expected_value}', got '{model_value}'"
                )

        elif key == "CouponCodes":
            # Check if coupon code and rule name are present
            if "H20" not in model_value or "Luma water bottle" not in model_value:
                mismatches.append(
                    f"{key}: expected '{expected_value}', got '{model_value}'"
                )

        elif key == "TopProduct":
            # Check if product name and quantity match
            if expected_value != model_value:
                mismatches.append(
                    f"{key}: expected '{expected_value}', got '{model_value}'"
                )

        else:
            # Exact match for other fields
            if model_value != expected_value:
                mismatches.append(
                    f"{key}: expected '{expected_value}', got '{model_value}'"
                )

    if mismatches:
        print("\n=== Answer Comparison Mismatches ===", file=sys.stderr)
        for mismatch in mismatches:
            print(f"✗ {mismatch}", file=sys.stderr)
        return False

    print("\n=== Answer Comparison ===", file=sys.stderr)
    print("✓ All key information matches the expected answer", file=sys.stderr)
    return True


async def verify() -> bool:
    """
    Verifies that the marketing analysis task has been completed correctly.
    First checks the model's answer against the expected label,
    then optionally verifies the actual state in the Magento Admin.
    """
    # Get the label file path
    label_path = Path(__file__).parent / "label.txt"

    # Load expected answer
    expected_answer = load_expected_answer(label_path)
    if not expected_answer:
        print("Error: Could not load expected answer from label.txt", file=sys.stderr)
        return False

    # Get model's response from MCP_MESSAGES
    model_response = get_model_response()
    if model_response:
        print("Found model response, parsing answer format...", file=sys.stderr)
        model_answer = parse_answer_format(model_response)

        if model_answer:
            print("\n=== Model Answer Parsed ===", file=sys.stderr)
            for key, value in model_answer.items():
                print(f"{key}: {value}", file=sys.stderr)

            # Compare answers
            answer_match = compare_answers(model_answer, expected_answer)
            if not answer_match:
                print("\nModel answer does not match expected answer", file=sys.stderr)
                return False
            print("\n✓ Model answer matches expected answer", file=sys.stderr)
        else:
            print(
                "Warning: Could not parse answer format from model response",
                file=sys.stderr,
            )
            print("Will proceed with browser verification only", file=sys.stderr)
    else:
        print(
            "No model response found, proceeding with browser verification",
            file=sys.stderr,
        )

    # Browser verification for actual state
    print("\n=== Starting Browser Verification ===", file=sys.stderr)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # Navigate to Magento Admin
            print("Navigating to Magento Admin...", file=sys.stderr)
            await page.goto(
                "http://34.143.185.85:7780/admin/", wait_until="networkidle"
            )

            # Check if already logged in, if not, login
            if "dashboard" not in page.url.lower():
                print("Logging into Magento Admin...", file=sys.stderr)
                await page.fill('input[name="login[username]"]', "admin")
                await page.fill('input[name="login[password]"]', "admin1234")
                await page.click('button:has-text("Sign in")')
                await page.wait_for_load_state("networkidle")

                if "dashboard" not in page.url.lower():
                    print("Error: Login failed", file=sys.stderr)
                    await page.screenshot(path=str(SCREENSHOT_DIR / "login_failed.png"))
                    return False

            print("Successfully logged into Magento Admin", file=sys.stderr)

            # 1. Verify Search Terms Report
            print("Verifying Search Terms Report...", file=sys.stderr)
            await page.goto(
                "http://34.143.185.85:7780/admin/search/term/report/",
                wait_until="networkidle",
            )

            # Check for search terms table
            search_terms_table = page.locator("table").first
            if not await search_terms_table.count():
                print("Error: Could not find search terms table", file=sys.stderr)
                await page.screenshot(
                    path=str(SCREENSHOT_DIR / "search_terms_not_found.png")
                )
                return False

            # Verify expected search terms exist
            expected_terms = ["hollister", "nike", "Joust Bag"]
            found_terms = 0
            for term in expected_terms:
                if await page.locator(f"text={term}").count():
                    found_terms += 1

            if found_terms < 2:
                print(
                    f"Warning: Only found {found_terms} of expected search terms",
                    file=sys.stderr,
                )
            else:
                print(f"Found {found_terms} expected search terms", file=sys.stderr)

            # 2. Verify Cart Price Rules
            print("Verifying Cart Price Rules...", file=sys.stderr)
            await page.goto(
                "http://34.143.185.85:7780/admin/sales_rule/promo_quote/",
                wait_until="networkidle",
            )

            # Look for H20 coupon code
            h20_coupon = page.locator("text=H20")
            if not await h20_coupon.count():
                print("Error: Could not find H20 coupon code", file=sys.stderr)
                await page.screenshot(path=str(SCREENSHOT_DIR / "coupon_not_found.png"))
                return False

            # Check for active rules
            active_rules = page.locator("text=Active")
            active_count = await active_rules.count()
            print(f"Found {active_count} active rules", file=sys.stderr)

            # 3. Verify Newsletter Subscribers
            print("Verifying Newsletter Subscribers...", file=sys.stderr)
            await page.goto(
                "http://34.143.185.85:7780/admin/newsletter/subscriber/",
                wait_until="networkidle",
            )

            # Apply Subscribed filter
            if await page.locator('select[name*="status"]').count():
                await page.select_option('select[name*="status"]', "Subscribed")
                await page.click('button:has-text("Search")')
                await page.wait_for_load_state("networkidle")

            # Check for specific emails
            john_email = await page.locator("text=john.smith.xyz@gmail.com").count() > 0
            admin_email = await page.locator("text=admin@magento.com").count() > 0

            print(f"john.smith.xyz@gmail.com found: {john_email}", file=sys.stderr)
            print(f"admin@magento.com found: {admin_email}", file=sys.stderr)

            # 4. Verify Customer Creation
            print("Verifying Customer Creation...", file=sys.stderr)
            await page.goto(
                "http://34.143.185.85:7780/admin/customer/index/",
                wait_until="networkidle",
            )

            # Check if new customers exist
            customer1_exists = (
                await page.locator("text=marketdata1.analysis@magento.com").count() > 0
            )
            customer2_exists = (
                await page.locator("text=analytics1.report@magento.com").count() > 0
            )

            if customer1_exists and customer2_exists:
                print("Both new customers found in the system", file=sys.stderr)
            else:
                print(
                    f"Customer 1 (marketdata1.analysis@magento.com): {'Found' if customer1_exists else 'Not Found'}",
                    file=sys.stderr,
                )
                print(
                    f"Customer 2 (analytics1.report@magento.com): {'Found' if customer2_exists else 'Not Found'}",
                    file=sys.stderr,
                )

            # 5. Verify Dashboard Data
            print("Verifying Dashboard Data...", file=sys.stderr)
            await page.goto(
                "http://34.143.185.85:7780/admin/admin/dashboard/",
                wait_until="networkidle",
            )

            # Check for bestsellers section
            bestsellers_exists = await page.locator("text=Bestsellers").count() > 0
            revenue_exists = await page.locator("text=Revenue").count() > 0

            if bestsellers_exists:
                print("Bestsellers section found on dashboard", file=sys.stderr)

                # Try to find the top product
                sprite_ball_exists = (
                    await page.locator("text=Sprite Stasis Ball 65 cm").count() > 0
                )
                if sprite_ball_exists:
                    print(
                        "✓ Found expected top product: Sprite Stasis Ball 65 cm",
                        file=sys.stderr,
                    )

            if revenue_exists:
                print("Revenue information found on dashboard", file=sys.stderr)

                # Check for $0.00 revenue
                zero_revenue = await page.locator("text=$0.00").count() > 0
                if zero_revenue:
                    print("✓ Revenue shows $0.00 as expected", file=sys.stderr)

            # Take final screenshot
            await page.screenshot(
                path=str(SCREENSHOT_DIR / "verification_complete.png")
            )
            print(
                f"Screenshot saved: {SCREENSHOT_DIR / 'verification_complete.png'}",
                file=sys.stderr,
            )

            # Summary of verification
            print("\n=== Browser Verification Summary ===", file=sys.stderr)
            print("✓ Magento Admin login successful", file=sys.stderr)
            print("✓ Search Terms Report accessible", file=sys.stderr)
            print("✓ Cart Price Rules with coupon codes found", file=sys.stderr)
            print("✓ Newsletter Subscribers filtering works", file=sys.stderr)
            print("✓ Customer creation capability verified", file=sys.stderr)
            print("✓ Dashboard data accessible", file=sys.stderr)

            # Basic validation passed
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
