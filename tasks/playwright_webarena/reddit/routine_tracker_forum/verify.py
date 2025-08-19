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
            # Step 1: Check if account can be logged in
            print("Step 1: Verifying account login...", file=sys.stderr)
            await page.goto("http://34.143.228.182:9999/", wait_until="networkidle")

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
                    print("Error: Account login failed for RoutineTracker2025", file=sys.stderr)
                    return False

                print("✓ Account login successful", file=sys.stderr)
            else:
                print("✓ Already logged in as RoutineTracker2025", file=sys.stderr)

            # Step 2: Check if the post exists in LifeProTips forum with correct content
            print("Step 2: Verifying post in LifeProTips forum...", file=sys.stderr)
            await page.goto(
                "http://34.143.228.182:9999/f/LifeProTips", wait_until="networkidle"
            )

            # Check for the created post
            expected_title = "My 5-Step Morning Routine That Increased My Productivity by 200%"
            post_link = page.locator(f'a:has-text("{expected_title}")')
            
            if not await post_link.count():
                print(f"Error: Post with title '{expected_title}' not found in LifeProTips forum", file=sys.stderr)
                return False

            # Click on the post to verify content
            await post_link.click()
            await page.wait_for_load_state("networkidle")

            # Verify post content - this should be the content from the most upvoted comment of the calendar post
            expected_content = "As a college student, having a visible reminder of the assignments I have and when they are due is super helpful for me. It also just feels good to erase them from the board once they are completed."

            # Check if the content exists in the page
            content_found = False
            article_content = await page.locator("article").text_content()
            if article_content and expected_content in article_content:
                content_found = True

            if not content_found:
                print(f"Error: Post content does not match expected content", file=sys.stderr)
                print(f"Expected: {expected_content}", file=sys.stderr)
                return False

            print("✓ Post found in LifeProTips with correct title and content", file=sys.stderr)

            # Step 3: Check upvotes via search
            print("Step 3: Verifying upvotes on posts...", file=sys.stderr)
            
            # Check first post upvote
            search_url1 = "http://34.143.228.182:9999/search?q=LPT%3A+Use+your+calendar+as+your+to-do+list.+Assigning+dedicated+time+to+tasks+increases+the+likelyhood+of+you+acting+upon+it."
            await page.goto(search_url1, wait_until="networkidle")
            
            # Find the post and check its upvote count
            posts = await page.locator("article").all()
            calendar_upvoted = False
            
            for post in posts:
                title_elem = post.locator("h1 a")
                if await title_elem.count():
                    title = await title_elem.text_content()
                    if "Use your calendar as your to-do list" in title:
                        # Check upvote count
                        vote_count_elem = post.locator("span.vote__net-score")
                        if await vote_count_elem.count():
                            vote_count = await vote_count_elem.text_content()
                            if vote_count and vote_count.strip() == "1":
                                calendar_upvoted = True
                                print("✓ Calendar post upvoted (count: 1)", file=sys.stderr)
                                break
            
            if not calendar_upvoted:
                print("Error: Calendar post not upvoted or upvote count is not 1", file=sys.stderr)
                return False

            # Check second post upvote
            search_url2 = "http://34.143.228.182:9999/search?q=LPT%3A+clean+your+stovetop+after+using+the+oven.+The+heat+loosens+grime+for+easy+removal"
            await page.goto(search_url2, wait_until="networkidle")
            
            posts = await page.locator("article").all()
            stovetop_upvoted = False
            
            for post in posts:
                title_elem = post.locator("h1 a")
                if await title_elem.count():
                    title = await title_elem.text_content()
                    if "clean your stovetop after using the oven" in title:
                        # Check upvote count
                        vote_count_elem = post.locator("span.vote__net-score")
                        if await vote_count_elem.count():
                            vote_count = await vote_count_elem.text_content()
                            if vote_count and vote_count.strip() == "1":
                                stovetop_upvoted = True
                                print("✓ Stovetop post upvoted (count: 1)", file=sys.stderr)
                                break
            
            if not stovetop_upvoted:
                print("Error: Stovetop post not upvoted or upvote count is not 1", file=sys.stderr)
                return False

            print("Success: All verification steps passed!")
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
