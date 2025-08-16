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

    # Browser verification - only check customer creation (the critical task requirement)
    print("\n=== Starting Browser Verification ===", file=sys.stderr)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # Navigate to Magento Admin
            print("Navigating to Magento Admin...", file=sys.stderr)
            await page.goto(
                "http://34.143.228.182:7780/admin/", wait_until="networkidle"
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

            # Verify Customer Creation (the only critical check for task completion)
            print("Verifying Customer Creation...", file=sys.stderr)
            await page.goto(
                "http://34.143.228.182:7780/admin/customer/index/",
                wait_until="networkidle",
            )

            # Wait for the customer grid to load
            try:
                await page.wait_for_selector("table", timeout=15000)
            except PlaywrightTimeoutError:
                print("Table not found, trying to proceed anyway...", file=sys.stderr)

            # Define customer requirements
            customer1_requirements = {
                "email": "marketdata1.analysis@magento.com",
                "first_name": "Marketing1",
                "last_name": "Analy",
                "group": "General",
                "website": "Main Website"
            }
            
            customer2_requirements = {
                "email": "analytics1.report@magento.com", 
                "first_name": "Analytics1",
                "last_name": "Report",
                "group": "Wholesale",
                "website": "Main Website"
            }

            async def check_customer_exists(customer_requirements):
                """Check if a customer exists by looking for their details in the customer grid"""
                email = customer_requirements["email"]
                first_name = customer_requirements["first_name"]
                last_name = customer_requirements["last_name"]
                group = customer_requirements["group"]
                
                # First check if email exists in current page without searching
                email_found = await page.locator(f"*:has-text('{email}')").count() > 0
                
                if not email_found:
                    # Try searching for the customer
                    try:
                        search_box = page.locator('input[placeholder*="Search by keyword"]').first
                        await search_box.clear()
                        await search_box.fill(email)
                        await page.keyboard.press("Enter")
                        await page.wait_for_load_state("networkidle")
                        await page.wait_for_timeout(2000)
                        
                        # Check again after search
                        email_found = await page.locator(f"*:has-text('{email}')").count() > 0
                    except:
                        pass
                
                if not email_found:
                    return False, f"Email {email} not found"
                
                # More precise validation: find the row containing this customer's email
                # Then check if the required fields are in the same row or nearby context
                try:
                    # Find the specific row containing this email
                    email_cell = page.locator(f"td:has-text('{email}')").first
                    if await email_cell.count() == 0:
                        # Fall back to broader search
                        email_cell = page.locator(f"*:has-text('{email}')").first
                    
                    # Get the parent row or container
                    row = email_cell.locator("xpath=ancestor::tr[1]")
                    if await row.count() == 0:
                        # Fall back to getting nearby content
                        row = email_cell.locator("xpath=..")
                    
                    # Get the text content of the row/container
                    row_text = await row.text_content() if await row.count() > 0 else ""
                    
                    # If we can't get a specific row, fall back to broader validation
                    if not row_text or len(row_text.strip()) < 10:
                        # Search in nearby cells or elements
                        nearby_elements = page.locator(f"*:has-text('{email}')").locator("xpath=../following-sibling::* | xpath=../preceding-sibling::*")
                        nearby_count = await nearby_elements.count()
                        nearby_text = ""
                        for i in range(min(nearby_count, 5)):  # Check up to 5 nearby elements
                            element_text = await nearby_elements.nth(i).text_content()
                            if element_text:
                                nearby_text += element_text + " "
                        row_text = row_text + " " + nearby_text
                    
                    # Check if required fields are present in the row/context
                    required_fields = [first_name, last_name, group]
                    found_fields = [email]  # Email is already confirmed
                    missing_fields = []
                    
                    for field in required_fields:
                        if field in row_text:
                            found_fields.append(field)
                        else:
                            missing_fields.append(field)
                    
                    if missing_fields:
                        return False, f"Customer found but missing fields in row context: {', '.join(missing_fields)}. Row text: {row_text[:100]}..."
                    
                    return True, f"Customer verified with all required fields: {', '.join(found_fields)}"
                    
                except Exception as e:
                    # Fall back to original simple validation
                    page_content = await page.content()
                    required_fields = [first_name, last_name, group, email]
                    found_fields = []
                    missing_fields = []
                    
                    for field in required_fields:
                        if field in page_content:
                            found_fields.append(field)
                        else:
                            missing_fields.append(field)
                    
                    if missing_fields:
                        return False, f"Customer found but missing fields (fallback): {', '.join(missing_fields)}"
                    
                    return True, f"Customer verified with all required fields (fallback): {', '.join(found_fields)}"

            # Check both customers
            customer1_exists, customer1_msg = await check_customer_exists(customer1_requirements)
            customer2_exists, customer2_msg = await check_customer_exists(customer2_requirements)

            print(
                f"Customer 1 (marketdata1.analysis@magento.com): {'Found' if customer1_exists else 'Not Found'} - {customer1_msg}",
                file=sys.stderr,
            )
            print(
                f"Customer 2 (analytics1.report@magento.com): {'Found' if customer2_exists else 'Not Found'} - {customer2_msg}",
                file=sys.stderr,
            )

            # If customers are not found, take screenshot for debugging
            if not (customer1_exists and customer2_exists):
                print("Taking screenshot for debugging...", file=sys.stderr)
                await page.screenshot(path=str(SCREENSHOT_DIR / "customers_debug.png"))
                
                # Also try to log the page content to understand the structure
                page_content = await page.content()
                debug_file = SCREENSHOT_DIR / "customer_page_debug.html"
                with open(debug_file, "w") as f:
                    f.write(page_content)
                print(f"Page content saved to: {debug_file}", file=sys.stderr)
                
                print("Error: Required customers were not found in the system", file=sys.stderr)
                return False

            print("✓ Both required customers found in the system", file=sys.stderr)
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
