import asyncio
import sys
from pathlib import Path
from datetime import datetime
from playwright.async_api import (
    async_playwright,
    TimeoutError as PlaywrightTimeoutError,
)


async def verify() -> bool:
    """
    Verifies that the daily routine tracking setup has been completed correctly on the forum.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # Navigate to the main page
            await page.goto("http://35.247.158.69:9999/", wait_until="networkidle")

            # Take a screenshot to verify the page is accessible
            screenshot_dir = Path(__file__).parent
            screenshot_path = (
                screenshot_dir
                / f"verify_homepage_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            )
            await page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"Screenshot saved to: {screenshot_path}", file=sys.stderr)

            # Check if already logged in
            user_button = page.locator('button:has-text("RoutineTracker2025")')
            if not await user_button.count():
                # Try to login
                print("Not logged in, attempting to login...", file=sys.stderr)

                # Click login link
                await page.click('a:has-text("Log in")')
                await page.wait_for_load_state("networkidle")

                # Fill login form
                await page.fill('input[name="_username"]', "RoutineTracker2025")
                await page.fill('input[name="_password"]', "DailyRoutine123!")

                # Submit login form
                await page.click('button:has-text("Log in")')
                await page.wait_for_load_state("networkidle")

                # Check if login successful
                user_button = page.locator('button:has-text("RoutineTracker2025")')
                if not await user_button.count():
                    print("Error: Login failed for RoutineTracker2025", file=sys.stderr)
                    return False

                print("Successfully logged in as RoutineTracker2025", file=sys.stderr)

                # Take a screenshot after successful login
                screenshot_path = (
                    screenshot_dir
                    / f"verify_after_login_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                )
                await page.screenshot(path=str(screenshot_path), full_page=True)
                print(
                    f"Screenshot after login saved to: {screenshot_path}",
                    file=sys.stderr,
                )

            # Navigate to user submissions page to check for the post
            await page.goto(
                "http://35.247.158.69:9999/user/RoutineTracker2025/submissions",
                wait_until="networkidle",
            )

            # Check if the post with the exact title exists
            expected_title = (
                "My 5-Step Morning Routine That Increased My Productivity by 200%"
            )
            post_title_link = page.locator(f'h1 a:has-text("{expected_title}")')
            if not await post_title_link.count():
                print(
                    f"Error: Post with title '{expected_title}' not found in user submissions",
                    file=sys.stderr,
                )
                return False

            print("User submission verified successfully", file=sys.stderr)

            # Navigate to LifeProTips forum
            await page.goto(
                "http://35.247.158.69:9999/f/LifeProTips", wait_until="networkidle"
            )

            # Check for the created post
            post_title = (
                "My 5-Step Morning Routine That Increased My Productivity by 200%"
            )
            post_link = page.locator(f'a:has-text("{post_title}")')
            if not await post_link.count():
                print(
                    f"Error: Post with title '{post_title}' not found", file=sys.stderr
                )
                return False

            # Click on the post to verify content
            await post_link.click()
            await page.wait_for_load_state("networkidle")

            # Verify post content
            expected_content = """After years of struggling with mornings, I discovered these 5 steps:"""

            # Check if the content exists in the page
            content_found = False
            paragraphs = await page.locator("article p").all()
            for p in paragraphs:
                text = await p.text_content()
                if text and expected_content in text:
                    content_found = True
                    break

            if not content_found:
                print(
                    "Error: Post content does not match expected content",
                    file=sys.stderr,
                )
                return False

            # Navigate back to LifeProTips to check upvoted posts
            await page.goto(
                "http://35.247.158.69:9999/f/LifeProTips", wait_until="networkidle"
            )

            # Define expected upvote counts after upvoting
            # Note: In the test environment, all upvoted posts show "1"
            expected_upvotes = {
                "calendar": {
                    "title": "Use your calendar as your to-do list",
                    "expected_count": "1",  # After upvoting, shows 1
                    "comments": "179 comments",
                },
                "stovetop": {
                    "title": "clean your stovetop after using the oven",
                    "expected_count": "1",  # After upvoting, shows 1
                },
            }

            # Check all posts for upvotes
            posts = await page.locator("article").all()
            verification_results = {}

            for post_key, post_info in expected_upvotes.items():
                found = False
                for post in posts:
                    title_elem = post.locator("h1 a")
                    if await title_elem.count():
                        title = await title_elem.text_content()
                        if post_info["title"] in title:
                            # For calendar post, also verify comments
                            if post_key == "calendar":
                                comments = post.locator(
                                    f'text="{post_info["comments"]}"'
                                )
                                if not await comments.count():
                                    continue

                            # Get upvote count - look for the vote count element
                            # Try multiple selectors for vote count
                            vote_count = None

                            # Try 1: Look for span with class vote__net-score
                            vote_count_elem = post.locator("span.vote__net-score")
                            if await vote_count_elem.count():
                                vote_count = await vote_count_elem.text_content()
                            else:
                                # Try 2: Look for generic element in the vote area
                                vote_generic = post.locator(
                                    ".submission__vote generic"
                                ).nth(1)
                                if await vote_generic.count():
                                    vote_count = await vote_generic.text_content()

                            if vote_count:
                                vote_count = vote_count.strip()

                                if vote_count == post_info["expected_count"]:
                                    verification_results[post_key] = True
                                    print(
                                        f"✓ {post_key} post upvoted successfully (count: {vote_count})"
                                    )
                                else:
                                    print(
                                        f"Error: {post_key} post has {vote_count} upvotes, expected exactly {post_info['expected_count']}",
                                        file=sys.stderr,
                                    )
                                    return False
                            else:
                                print(
                                    f"Error: Could not find vote count for {post_key} post",
                                    file=sys.stderr,
                                )
                                return False

                            found = True
                            break

                if not found:
                    print(f"Error: {post_key} post not found", file=sys.stderr)
                    return False

            # Verify all posts were upvoted
            if len(verification_results) != 2 or not all(verification_results.values()):
                print("Error: Not all posts were upvoted correctly", file=sys.stderr)
                return False

            print("Success: Daily routine tracking setup completed successfully.")
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
