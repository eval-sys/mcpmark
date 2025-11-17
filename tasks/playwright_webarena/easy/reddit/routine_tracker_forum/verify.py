import asyncio
import os
import sys
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

BASE_URL = os.getenv("WEBARENA_BASE_URL", "http://localhost:9999").rstrip("/")
USERNAME = "RoutineTracker2025"
PASSWORD = "DailyRoutine123!"
FORUM_SLUG = "LifeProTips"
POST_TITLE = "My 5-Step Morning Routine That Increased My Productivity by 200%"
EXPECTED_BODY = (
    "As a college student, having a visible reminder of the assignments I have and when they are due is super helpful for me. "
    "It also just feels good to erase them from the board once they are completed."
)


async def ensure_logged_in(page) -> bool:
    print("Step 1: Logging in before verification...", file=sys.stderr)
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


async def verify_post_body(page) -> bool:
    print("Step 2: Validating reposted comment content...", file=sys.stderr)
    await page.goto(f"{BASE_URL}/f/{FORUM_SLUG}", wait_until="networkidle")
    post_link = page.locator(f'a:has-text("{POST_TITLE}")')
    if not await post_link.count():
        print(f"FAILED: Post '{POST_TITLE}' not found in LifeProTips", file=sys.stderr)
        return False

    await post_link.first.click()
    await page.wait_for_load_state("networkidle")

    article = page.locator("article")
    if not await article.count():
        print("FAILED: Unable to read post body", file=sys.stderr)
        return False

    body_text = await article.first.inner_text()
    if EXPECTED_BODY not in body_text:
        print("FAILED: Post body does not match the copied comment text", file=sys.stderr)
        return False

    print("✓ Post body matches the expected LifeProTips comment", file=sys.stderr)
    return True


async def verify_listing_presence(page) -> bool:
    print("Step 3: Confirming the post appears in the forum listing...", file=sys.stderr)
    await page.goto(f"{BASE_URL}/f/{FORUM_SLUG}", wait_until="networkidle")
    post_link = page.locator(f'a:has-text("{POST_TITLE}")')
    if await post_link.count():
        print("✓ Post is visible in the LifeProTips feed", file=sys.stderr)
        return True

    print("FAILED: Post missing from forum listing", file=sys.stderr)
    return False


async def verify() -> bool:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            if not await ensure_logged_in(page):
                return False
            if not await verify_post_body(page):
                return False
            if not await verify_listing_presence(page):
                return False
            print("SUCCESS: Routine tracker easy task verified", file=sys.stderr)
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
