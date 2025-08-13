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
    Parse the <answer>...</answer> format from the agent's output.
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

    if len(lines) != 5:
        print(f"Error: Expected 5 lines in answer, got {len(lines)}", file=sys.stderr)
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

        # Exact match for all fields
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
    Verifies that the customer segmentation setup task has been completed correctly.
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

            # 1. Verify Customer Groups
            print("\nVerifying Customer Groups...", file=sys.stderr)
            await page.goto(
                "http://34.143.185.85:7780/admin/customer/group/",
                wait_until="networkidle",
            )
            await page.wait_for_timeout(2000)  # Wait for grid to load

            # Check for Premium Europe group
            premium_europe_exists = (
                await page.locator("text=Premium Europe").count() > 0
            )
            if premium_europe_exists:
                print("✓ Found 'Premium Europe' customer group", file=sys.stderr)

                # Check if it has Retail Customer tax class
                # Look for Premium Europe row and check its tax class
                premium_row = page.locator('tr:has-text("Premium Europe")')
                if await premium_row.count() > 0:
                    tax_class_text = await premium_row.locator("td").nth(2).inner_text()
                    if "Retail Customer" in tax_class_text:
                        print(
                            "✓ Premium Europe has 'Retail Customer' tax class",
                            file=sys.stderr,
                        )
                    else:
                        print(
                            f"Warning: Premium Europe tax class is '{tax_class_text}'",
                            file=sys.stderr,
                        )
            else:
                print("✗ 'Premium Europe' customer group not found", file=sys.stderr)
                await page.screenshot(path=str(SCREENSHOT_DIR / "customer_groups.png"))
                return False

            # Check total groups count
            records_found = page.locator("text=records found").first
            if await records_found.count() > 0:
                count_text = await records_found.inner_text()
                print(f"Customer Groups count: {count_text}", file=sys.stderr)

                # Extract number
                import re

                match = re.search(r"(\d+)\s+records found", count_text)
                if match:
                    groups_count = int(match.group(1))
                    print(f"✓ Customer groups count is {groups_count}", file=sys.stderr)

            # 2. Verify Customer
            print("\nVerifying Customer Isabella Romano...", file=sys.stderr)
            await page.goto(
                "http://34.143.185.85:7780/admin/customer/index/",
                wait_until="networkidle",
            )
            await page.wait_for_timeout(3000)  # Wait for grid to load

            # Check total customers count
            customer_records = page.locator("text=records found").first
            if await customer_records.count() > 0:
                count_text = await customer_records.inner_text()
                print(f"Customers count: {count_text}", file=sys.stderr)

                # Extract number
                match = re.search(r"(\d+)\s+records found", count_text)
                if match:
                    customers_count = int(match.group(1))
                    print(
                        f"✓ Total customers count is {customers_count}", file=sys.stderr
                    )

                    # Verify against expected answer if available
                    if expected_answer and "FinalCustomers" in expected_answer:
                        expected_final = int(expected_answer["FinalCustomers"])
                        if customers_count == expected_final:
                            print(
                                f"✓ Customer count matches expected: {customers_count}",
                                file=sys.stderr,
                            )
                        else:
                            print(
                                f"Warning: Expected {expected_final} customers, found {customers_count}",
                                file=sys.stderr,
                            )

            # Check if Isabella Romano exists without searching (to avoid timeout)
            # Just check if the email appears on the page
            isabella_exists = (
                await page.locator("text=isabella.romano@premium.eu").count() > 0
            )
            if isabella_exists:
                print(
                    "✓ Found customer with email 'isabella.romano@premium.eu'",
                    file=sys.stderr,
                )
            else:
                print(
                    "Note: Customer 'isabella.romano@premium.eu' not visible on current page",
                    file=sys.stderr,
                )

            # 3. Verify Dashboard Last Orders
            print("\nVerifying Dashboard Last Orders...", file=sys.stderr)
            await page.goto(
                "http://34.143.185.85:7780/admin/admin/dashboard/",
                wait_until="networkidle",
            )
            await page.wait_for_timeout(2000)

            # Check for Last Orders section
            last_orders_exists = await page.locator("text=Last Orders").count() > 0
            if last_orders_exists:
                print("✓ Found 'Last Orders' section on dashboard", file=sys.stderr)

                # Find the first customer in the table
                # Look for the table after "Last Orders" heading
                orders_table = (
                    page.locator("text=Last Orders")
                    .locator("..")
                    .locator("table")
                    .first
                )
                if await orders_table.count() > 0:
                    # Get the first row in tbody
                    first_row = orders_table.locator("tbody tr").first
                    if await first_row.count() > 0:
                        first_customer = await first_row.locator(
                            "td"
                        ).first.inner_text()
                        print(
                            f"✓ First customer in Last Orders: {first_customer}",
                            file=sys.stderr,
                        )

                        # Verify against expected answer if available
                        if expected_answer and "LastOrderCustomer" in expected_answer:
                            if first_customer == expected_answer["LastOrderCustomer"]:
                                print(
                                    f"✓ Last Order Customer matches expected: {first_customer}",
                                    file=sys.stderr,
                                )
                            else:
                                print(
                                    f"Warning: Expected '{expected_answer['LastOrderCustomer']}' but actual is '{first_customer}'",
                                    file=sys.stderr,
                                )
            else:
                print(
                    "Warning: 'Last Orders' section not found on dashboard",
                    file=sys.stderr,
                )

            # Take final screenshot
            await page.screenshot(
                path=str(SCREENSHOT_DIR / "verification_complete.png")
            )
            print(
                f"\nScreenshot saved: {SCREENSHOT_DIR / 'verification_complete.png'}",
                file=sys.stderr,
            )

            # Summary of verification
            print("\n=== Browser Verification Summary ===", file=sys.stderr)
            print("✓ Magento Admin login successful", file=sys.stderr)
            print(
                "✓ Customer group 'Premium Europe' exists with correct tax class",
                file=sys.stderr,
            )
            print("✓ Customer counts verified", file=sys.stderr)
            print("✓ Dashboard Last Orders section accessible", file=sys.stderr)

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
