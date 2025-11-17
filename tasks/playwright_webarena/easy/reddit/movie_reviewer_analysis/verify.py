import asyncio
import os
import re
import sys
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

BASE_URL = os.getenv("WEBARENA_BASE_URL", "http://localhost:9999").rstrip("/")
USERNAME = "movie_reviewer_2024"
PASSWORD = "movie_reviewer_2024"
FORUM_SLUG = "movies"
POST_TITLE = "Wonderful Movies Analysis: Community Favorites [2024]"
REQUIRED_FIELDS = [
    "Total_Year_Posts",
    "Top_Title",
    "Top_Upvotes",
    "Top_Comments",
]
NUMERIC_FIELDS = {
    "Total_Year_Posts",
    "Top_Upvotes",
    "Top_Comments",
}
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


def normalize_text(value: str) -> str:
    if value is None:
        return ""
    replacements = {
        "\u2019": "'",
        "\u2018": "'",
        "\u201c": '"',
        "\u201d": '"',
    }
    for src, dst in replacements.items():
        value = value.replace(src, dst)
    return " ".join(value.split()).strip()


def load_expected_values() -> dict:
    if not LABEL_PATH.exists():
        return {}
    return parse_key_value_format(LABEL_PATH.read_text(encoding="utf-8"))


async def ensure_logged_in(page) -> bool:
    print("Step 1: Authenticating movie_reviewer_2024...", file=sys.stderr)
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


async def fetch_summary_body(page):
    print("Step 2: Locating the movies summary post...", file=sys.stderr)
    await page.goto(f"{BASE_URL}/f/{FORUM_SLUG}", wait_until="networkidle")
    post_link = page.locator(f'a:has-text("{POST_TITLE}")')
    if not await post_link.count():
        print(f"FAILED: Submission '{POST_TITLE}' not found", file=sys.stderr)
        return None

    await post_link.first.click()
    await page.wait_for_load_state("networkidle")

    selectors = [
        ".submission__body",
        "article",
        ".post-body",
        ".RichText",
        '[class*="RichText"]',
        'div:has-text("Total_Year_Posts")',
    ]

    for selector in selectors:
        locator = page.locator(selector)
        if await locator.count():
            content = await locator.first.inner_text()
            if content:
                print(f"✓ Retrieved summary content via selector {selector}", file=sys.stderr)
                return content

    print("FAILED: Unable to locate submission body", file=sys.stderr)
    return None


def validate_summary(extracted: dict, expected: dict) -> bool:
    missing = [key for key in REQUIRED_FIELDS if key not in extracted]
    if missing:
        print(f"FAILED: Missing required keys: {', '.join(missing)}", file=sys.stderr)
        return False

    errors = []
    for key in REQUIRED_FIELDS:
        actual = extracted.get(key, "")
        expect = expected.get(key, "")
        if key in NUMERIC_FIELDS:
            try:
                actual_val = int(actual)
                expect_val = int(expect)
                if actual_val != expect_val:
                    errors.append(f"{key}: expected {expect_val}, found {actual_val}")
            except ValueError:
                errors.append(f"{key}: '{actual}' is not numeric")
        else:
            if normalize_text(actual) != normalize_text(expect):
                errors.append(f"{key}: expected '{expect}', found '{actual}'")

    if errors:
        print("FAILED: Summary values differ from expected snapshot:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return False

    print("✓ Summary values match expected data", file=sys.stderr)
    return True


async def verify() -> bool:
    expected = load_expected_values()
    if not expected:
        print("FAILED: label.txt is missing", file=sys.stderr)
        return False

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            if not await ensure_logged_in(page):
                return False

            content = await fetch_summary_body(page)
            if not content:
                return False

            extracted = parse_key_value_format(content)
            if not validate_summary(extracted, expected):
                return False

            print("SUCCESS: Movie analysis easy task verified", file=sys.stderr)
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
