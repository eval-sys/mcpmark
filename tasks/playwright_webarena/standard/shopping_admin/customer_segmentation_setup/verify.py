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

# 从环境变量读取 base_url（shopping_admin 会注入 http://localhost:7780/admin），默认回退到本地
BASE_URL = os.getenv("WEBARENA_BASE_URL", "http://localhost:7780/admin").rstrip("/")


def get_model_response():
    """
    Get the model's response from the MCP_MESSAGES environment variable.
    Returns the last assistant message text.
    """
    messages_path = os.getenv("MCP_MESSAGES")
    print(f"MCP_MESSAGES: {messages_path}", file=sys.stderr)
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
                and message.get("type") == "message"
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


def normalize_text(text):
    """
    Normalize text for comparison by collapsing whitespace.
    """
    if not isinstance(text, str):
        return str(text)

    text = text.replace("‘", "'").replace("’", "'")
    text = text.replace("“", '"').replace("”", '"')

    # Normalize whitespace
    text = " ".join(text.split())

    return text.strip()


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
            result[key.strip()] = normalize_text(value.strip())

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
                expected[key.strip()] = normalize_text(value.strip())

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

        if key in ["InitialGroups", "FinalGroups", "InitialCustomers", "FinalCustomers"]:
            try:
                if int(model_value) != int(expected_value):
                    mismatches.append(
                        f"{key}: expected '{expected_value}', got '{model_value}'"
                    )
            except ValueError:
                mismatches.append(
                    f"{key} should be numeric: got '{model_value}'"
                )
        elif key == "LastOrderCustomer":
            # Case-insensitive exact match
            if model_value.lower() != expected_value.lower():
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
    Verifies that the customer segmentation setup task has been completed correctly.
    First checks the model's answer against the expected label,
    then verifies the actual state in the Magento Admin.
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
            return False
    else:
        print("No model response found", file=sys.stderr)
        return False

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
                f"{BASE_URL}/", wait_until="networkidle"
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
                    return False

            print("Successfully logged into Magento Admin", file=sys.stderr)

            # 1. Verify Customer Groups
            print("\nVerifying Customer Groups...", file=sys.stderr)
            await page.goto(
                f"{BASE_URL}/customer/group/",
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
                            f"✗ Premium Europe tax class is '{tax_class_text}', expected 'Retail Customer'",
                            file=sys.stderr,
                        )
                        return False
                else:
                    print(
                        "✗ Could not locate 'Premium Europe' row to verify tax class",
                        file=sys.stderr,
                    )
                    return False
            else:
                print("✗ 'Premium Europe' customer group not found", file=sys.stderr)
                return False

            # 2. Verify Customer
            print("\nVerifying Customer Isabella Romano...", file=sys.stderr)
            await page.goto(
                f"{BASE_URL}/customer/index/",
                wait_until="networkidle",
            )
            await page.wait_for_timeout(3000)  # Wait for grid to load

            # Wait for the customer grid to load properly
            await page.wait_for_timeout(5000)
            
            # Check if Isabella Romano exists - first wait for grid to load
            grid_loaded = False
            for i in range(3):
                # Look for grid container and wait for it to populate
                grid_container = page.locator(".admin__data-grid-outer-wrap, .data-grid, table").first
                if await grid_container.count() > 0:
                    # Check if there are customer rows loaded
                    customer_rows = page.locator("td[data-column='email'], td:has-text('@')")
                    if await customer_rows.count() > 0:
                        grid_loaded = True
                        break
                await page.wait_for_timeout(2000)
            
            if not grid_loaded:
                print("✗ Customer grid failed to load properly", file=sys.stderr)
                return False
            
            # Now check if Isabella Romano exists in the loaded grid
            isabella_exists = (
                await page.locator("text=isabella.romano@premium.eu").count() > 0
            )
            
            if not isabella_exists:
                # Try searching for the customer to be more thorough
                try:
                    search_box = page.locator('input[placeholder*="Search by keyword"], input[name="search"], [data-role="search"]').first
                    if await search_box.count() > 0:
                        await search_box.clear()
                        await search_box.fill("isabella.romano@premium.eu")
                        await page.keyboard.press("Enter")
                        await page.wait_for_load_state("networkidle")
                        await page.wait_for_timeout(3000)
                        
                        # Check again after search
                        isabella_exists = (
                            await page.locator("text=isabella.romano@premium.eu").count() > 0
                        )
                except Exception as e:
                    print(f"✗ Search failed: {str(e)}", file=sys.stderr)
                    return False
            
            if isabella_exists:
                print(
                    "✓ Found customer with email 'isabella.romano@premium.eu'",
                    file=sys.stderr,
                )
            else:
                print(
                    "✗ Customer 'isabella.romano@premium.eu' not found",
                    file=sys.stderr,
                )
                return False

            # Summary of verification - only print if we reach this point (all checks passed)
            print("\n=== Browser Verification Summary ===", file=sys.stderr)
            print("✓ Magento Admin login successful", file=sys.stderr)
            print(
                "✓ Customer group 'Premium Europe' exists with correct tax class",
                file=sys.stderr,
            )
            print("✓ Customer 'isabella.romano@premium.eu' found in system", file=sys.stderr)

            return True

        except PlaywrightTimeoutError as e:
            print(f"Error: Timeout occurred - {str(e)}", file=sys.stderr)
            return False
        except Exception as e:
            print(f"Error: Unexpected error - {str(e)}", file=sys.stderr)
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
