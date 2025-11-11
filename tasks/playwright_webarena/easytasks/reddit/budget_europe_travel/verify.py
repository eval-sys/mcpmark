import asyncio
import os
import sys
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

BASE_URL = os.getenv("WEBARENA_BASE_URL", "http://localhost:9999").rstrip("/")
USERNAME = "EuroTravelPlanner"
PASSWORD = "SecureTravel2024!"
FORUM_SLUG = "BudgetEuropeTravel"
FORUM_TITLE = "Budget Travel Europe"
FORUM_DESCRIPTION = "Community for sharing money-saving tips for European travel"
FORUM_SIDEBAR = "Share your best European travel deals and budget tips here!"


async def ensure_logged_in(page) -> bool:
    print("Step 1: Verifying account access...", file=sys.stderr)
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


async def verify_forum_copy(page) -> bool:
    print("Step 2: Checking forum branding copy...", file=sys.stderr)
    await page.goto(f"{BASE_URL}/f/{FORUM_SLUG}", wait_until="networkidle")

    title_text = await page.title()
    if "404" in title_text.lower():
        print(f"FAILED: Forum /f/{FORUM_SLUG} returned 404", file=sys.stderr)
        return False

    page_html = await page.content()
    checks = {
        "title": FORUM_TITLE,
        "description": FORUM_DESCRIPTION,
        "sidebar": FORUM_SIDEBAR,
    }

    for label, snippet in checks.items():
        if snippet not in page_html:
            print(f"FAILED: Forum {label} text missing", file=sys.stderr)
            return False

    print("✓ Forum title/description/sidebar match expected copy", file=sys.stderr)
    return True


async def verify() -> bool:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            if not await ensure_logged_in(page):
                return False
            if not await verify_forum_copy(page):
                return False
            print("SUCCESS: Budget Europe Travel easy task verified", file=sys.stderr)
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
