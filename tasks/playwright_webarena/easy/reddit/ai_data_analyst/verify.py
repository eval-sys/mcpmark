import asyncio
import os
import re
import sys
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

BASE_URL = os.getenv("WEBARENA_BASE_URL", "http://localhost:9999").rstrip("/")
USERNAME = "AIDataAnalyst2025"
PASSWORD = "SecurePass123!"
POST_TITLE = "MachineLearning_Extraction"
REQUIRED_FIELDS = [
    "Deeplearning_Post_Count",
    "ChatGPT_Tool_Vote_Count",
]
LABEL_PATH = Path(__file__).parent / "label.txt"


def parse_key_value_format(text: str) -> dict:
    data = {}
    if not text:
        return data
    for line in text.splitlines():
        line = line.strip()
        if not line or "|" not in line:
            continue
        line = re.sub(r"^[-•*]\s*", "", line)
        key, value = line.split("|", 1)
        data[key.strip()] = value.strip()
    return data


def load_expected_values() -> dict:
    if not LABEL_PATH.exists():
        return {}
    return parse_key_value_format(LABEL_PATH.read_text(encoding="utf-8"))


async def ensure_logged_in(page) -> bool:
    print("Step 1: Ensuring we are logged in...", file=sys.stderr)
    await page.goto(f"{BASE_URL}/", wait_until="networkidle")
    user_button = page.locator(f'button:has-text("{USERNAME}")')
    if await user_button.count():
        print("✓ Already logged in", file=sys.stderr)
        return True

    login_link = page.locator('a:has-text("Log in")')
    if not await login_link.count():
        print("FAILED: Login link not found", file=sys.stderr)
        return False

    await login_link.click()
    await page.wait_for_load_state("networkidle")
    await page.fill('input[name="_username"]', USERNAME)
    await page.fill('input[name="_password"]', PASSWORD)
    await page.click('button:has-text("Log in")')
    await page.wait_for_load_state("networkidle")

    if await page.locator(f'button:has-text("{USERNAME}")').count():
        print(f"✓ Logged in as {USERNAME}", file=sys.stderr)
        return True

    print("FAILED: Could not log in with provided credentials", file=sys.stderr)
    return False


async def fetch_submission_content(page):
    print("Step 2: Retrieving MachineLearning submission...", file=sys.stderr)
    await page.goto(f"{BASE_URL}/f/MachineLearning", wait_until="networkidle")
    post_link = page.locator(f'a:has-text("{POST_TITLE}")')
    if not await post_link.count():
        print(
            f"FAILED: Submission '{POST_TITLE}' not found in MachineLearning forum",
            file=sys.stderr,
        )
        return None

    await post_link.first.click()
    await page.wait_for_load_state("networkidle")

    selectors = [
        ".submission__body",
        "article",
        ".post-body",
        ".RichText",
        '[class*="RichText"]',
    ]

    for selector in selectors:
        locator = page.locator(selector)
        if await locator.count():
            content = await locator.first.inner_text()
            if content:
                print(f"✓ Found submission body via selector {selector}", file=sys.stderr)
                return content

    print("FAILED: Unable to locate submission body content", file=sys.stderr)
    return None


def validate_submission(extracted: dict, expected: dict) -> bool:
    missing = [key for key in REQUIRED_FIELDS if key not in extracted]
    if missing:
        print(
            f"FAILED: Submission body missing required keys: {', '.join(missing)}",
            file=sys.stderr,
        )
        return False

    errors = []
    for key in REQUIRED_FIELDS:
        actual = extracted.get(key, "")
        expect = expected.get(key, "")
        try:
            actual_val = int(actual)
            expect_val = int(expect)
            if actual_val != expect_val:
                errors.append(f"{key}: expected {expect_val}, found {actual_val}")
        except ValueError:
            errors.append(f"{key}: value '{actual}' is not numeric")

    if errors:
        print("FAILED: Submission values do not match expected data:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return False

    print("✓ Submission content matches expected metrics", file=sys.stderr)
    return True


async def verify() -> bool:
    expected = load_expected_values()
    if not expected:
        print("FAILED: label.txt with expected values is missing", file=sys.stderr)
        return False


    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            if not await ensure_logged_in(page):
                return False

            content = await fetch_submission_content(page)
            if not content:
                return False

            extracted = parse_key_value_format(content)
            if not validate_submission(extracted, expected):
                return False

            print("SUCCESS: Easy AI data analyst task verified", file=sys.stderr)
            return True

        except PlaywrightTimeoutError as exc:
            print(f"FAILED: Timeout occurred - {exc}", file=sys.stderr)
            return False
        except Exception as exc:
            print(f"FAILED: Unexpected error - {exc}", file=sys.stderr)
            return False
        finally:
            await browser.close()


def main():
    result = asyncio.run(verify())
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
