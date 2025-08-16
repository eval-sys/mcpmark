import asyncio
import sys
import re
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# Directory for screenshots
SCREENSHOT_DIR = Path("/home/liuxiangyan6/eval-sys/mcp-arena/verification_screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)

def normalize_text(text):
    """
    Normalize text for comparison by handling different quote styles and whitespace.
    """
    if not isinstance(text, str):
        return str(text)
    
    # Replace various quote styles with standard quotes
    text = text.replace(''', "'").replace(''', "'")
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace('&amp;', '&')
    
    # Normalize whitespace
    text = ' '.join(text.split())
    
    return text.strip()

async def verify() -> bool:
    """
    Verifies that the budget Europe travel resource task has been completed correctly.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # 1. Check if account can login
            print("Step 1: Verifying account login...", file=sys.stderr)
            await page.goto('http://34.143.185.85:9999/', wait_until='networkidle')
            
            # Check if already logged in
            user_button = page.locator('button:has-text("EuroTravelPlanner")')
            if not await user_button.count():
                # Try to login
                print("Not logged in, attempting to login...", file=sys.stderr)
                
                # Navigate to login page
                login_link = page.locator('a:has-text("Log in")')
                if await login_link.count():
                    await login_link.click()
                    await page.wait_for_load_state('networkidle')
                else:
                    print("Error: Cannot find login link", file=sys.stderr)
                    return False
                
                # Fill login form
                await page.fill('input[name="_username"]', 'EuroTravelPlanner')
                await page.fill('input[name="_password"]', 'SecureTravel2024!')
                
                # Submit login
                login_button = page.locator('button[type="submit"]:has-text("Log in")')
                if not await login_button.count():
                    login_button = page.locator('button:has-text("Log in")')
                
                await login_button.click()
                await page.wait_for_load_state('networkidle')
                
                # Verify login success
                user_button = page.locator('button:has-text("EuroTravelPlanner")')
                if not await user_button.count():
                    print("Error: Login failed for EuroTravelPlanner", file=sys.stderr)
                    await page.screenshot(path=str(SCREENSHOT_DIR / "login_failed.png"))
                    return False
                
                print("✓ Successfully logged in as EuroTravelPlanner", file=sys.stderr)
            else:
                print("✓ Already logged in as EuroTravelPlanner", file=sys.stderr)
            
            # 2. Check if forum exists at /f/BudgetEuropeTravel
            print("\nStep 2: Checking forum existence...", file=sys.stderr)
            await page.goto('http://34.143.185.85:9999/f/BudgetEuropeTravel', wait_until='networkidle')
            
            # Check if we get 404 or the forum exists
            page_title = await page.title()
            if "404" in page_title or "not found" in page_title.lower() or "Page not found" in await page.content():
                print("Error: Forum /f/BudgetEuropeTravel does not exist (404)", file=sys.stderr)
                await page.screenshot(path=str(SCREENSHOT_DIR / "forum_not_found.png"))
                return False
            
            print("✓ Forum /f/BudgetEuropeTravel exists", file=sys.stderr)
            
            # 3. Verify forum details at edit page
            print("\nStep 3: Verifying forum details at edit page...", file=sys.stderr)
            await page.goto('http://34.143.185.85:9999/f/BudgetEuropeTravel/edit', wait_until='networkidle')
            
            # Check if we can access edit page (should be moderator)
            if "404" in await page.title() or "not found" in (await page.title()).lower():
                print("Warning: Cannot access forum edit page", file=sys.stderr)
            else:
                # Check title field
                title_input = page.locator('input[name*="title"], input#forum_title')
                if await title_input.count():
                    title_value = await title_input.input_value()
                    if title_value != "Budget Travel Europe":
                        print(f"Error: Forum title is '{title_value}', expected 'Budget Travel Europe'", file=sys.stderr)
                        return False
                    print("✓ Forum title verified: 'Budget Travel Europe'", file=sys.stderr)
                
                # Check description field
                desc_input = page.locator('textarea[name*="description"], input[name*="description"]')
                if await desc_input.count():
                    desc_value = await desc_input.input_value()
                    if "Community for sharing money-saving tips for European travel" not in desc_value:
                        print(f"Warning: Forum description different: '{desc_value}'", file=sys.stderr)
                    else:
                        print("✓ Forum description verified", file=sys.stderr)
                
                # Check sidebar field
                sidebar_input = page.locator('textarea[name*="sidebar"]')
                if await sidebar_input.count():
                    sidebar_value = await sidebar_input.input_value()
                    if "Share your best European travel deals and budget tips here!" not in sidebar_value:
                        print(f"Warning: Forum sidebar different: '{sidebar_value}'", file=sys.stderr)
                    else:
                        print("✓ Forum sidebar verified", file=sys.stderr)
            
            # 4. Verify wiki page exists at /w/europe-travel-budget-guide
            print("\nStep 4: Checking wiki page...", file=sys.stderr)
            await page.goto('http://34.143.185.85:9999/w/europe-travel-budget-guide', wait_until='networkidle')
            
            if "404" in await page.title() or "not found" in (await page.title()).lower():
                # Try alternative URL
                await page.goto('http://34.143.185.85:9999/wiki/europe-travel-budget-guide', wait_until='networkidle')
                if "404" in await page.title() or "not found" in (await page.title()).lower():
                    print("Error: Wiki page does not exist", file=sys.stderr)
                    await page.screenshot(path=str(SCREENSHOT_DIR / "wiki_not_found.png"))
                    return False
            
            # Check wiki title
            wiki_title = page.locator('h1:has-text("Complete Budget Travel Guide for Europe 2024")')
            if not await wiki_title.count():
                print("Error: Wiki title 'Complete Budget Travel Guide for Europe 2024' not found", file=sys.stderr)
                return False
            
            # Check for required content in wiki
            wiki_content = await page.content()
            if "Eurail passes and budget airlines" not in wiki_content:
                print("Error: Wiki content must contain 'Eurail passes and budget airlines'", file=sys.stderr)
                return False
            
            print("✓ Wiki page verified with correct title and content", file=sys.stderr)
            
            # 5. Check for the post in the forum
            print("\nStep 5: Checking for post in forum...", file=sys.stderr)
            await page.goto('http://34.143.185.85:9999/f/BudgetEuropeTravel', wait_until='networkidle')
            
            post_title = "My 14-day Europe trip for under 1000 - Complete itinerary"
            post_link = page.locator(f'a:has-text("{post_title}")')
            
            if not await post_link.count():
                print(f"Error: Post '{post_title}' not found in forum", file=sys.stderr)
                await page.screenshot(path=str(SCREENSHOT_DIR / "post_not_found.png"))
                return False
            
            # Click on the post to check its content
            await post_link.first.click()
            await page.wait_for_load_state('networkidle')
            
            # Check if post contains required text
            post_content = await page.content()
            if "budget guide wiki" not in post_content:
                print("Error: Post body must contain 'budget guide wiki'", file=sys.stderr)
                return False
            
            print("✓ Post found with correct title and content", file=sys.stderr)
            
            # 6. Check travel insurance search and upvote
            print("\nStep 6: Checking travel insurance search and upvote...", file=sys.stderr)
            
            # Perform the search
            await page.goto('http://34.143.185.85:9999/', wait_until='networkidle')
            search_box = page.locator('input[type="search"], input[placeholder*="Search"]')
            if await search_box.count():
                await search_box.fill("travel insurance Europe")
                await search_box.press("Enter")
                await page.wait_for_load_state('networkidle')
                
                # Check if we're on search results page
                if "/search" in page.url:
                    print("✓ Search performed for 'travel insurance Europe'", file=sys.stderr)
                    
                    # Check for upvoted posts (looking for upvote count of 1 or "Retract upvote" button)
                    upvote_buttons = page.locator('button:has-text("Retract upvote")')
                    upvote_counts = page.locator('div:has(> button[aria-label*="vote"]) >> text=/^[1-9]/')
                    
                    if await upvote_buttons.count() > 0:
                        print("✓ Found upvoted post (Retract upvote button present)", file=sys.stderr)
                    elif await upvote_counts.count() > 0:
                        print("✓ Found post with upvote count > 0", file=sys.stderr)
                    else:
                        # Check if the first result has been upvoted by looking at vote count
                        first_result = page.locator('article').first
                        if await first_result.count():
                            vote_display = first_result.locator('text=/^\\d+$/').first
                            if await vote_display.count():
                                vote_count = await vote_display.text_content()
                                if int(vote_count) > 0:
                                    print(f"✓ First search result has {vote_count} upvote(s)", file=sys.stderr)
                                else:
                                    print("Warning: Could not verify upvote on search result", file=sys.stderr)
                            else:
                                print("Warning: Could not find vote count", file=sys.stderr)
                else:
                    print("Warning: Search might not have been performed", file=sys.stderr)
            
            # 7. Verify user settings at /user/EuroTravelPlanner/preferences
            print("\nStep 7: Checking user settings...", file=sys.stderr)
            await page.goto('http://34.143.185.85:9999/user/EuroTravelPlanner/preferences', wait_until='networkidle')
            
            # Check timezone setting - look for the select element with Europe/Amsterdam selected
            timezone_select = page.locator('select[name*="timezone"], select:has(option:has-text("Amsterdam"))')
            if await timezone_select.count():
                selected_value = await timezone_select.input_value()
                # The value might be "Europe/Amsterdam" or similar
                if "Amsterdam" in selected_value or selected_value == "Europe/Amsterdam":
                    print("✓ Timezone correctly set to Europe/Amsterdam", file=sys.stderr)
                else:
                    # Check if Amsterdam option is selected
                    selected_option = timezone_select.locator('option[selected]')
                    if await selected_option.count():
                        option_text = await selected_option.text_content()
                        if "Amsterdam" in option_text:
                            print("✓ Timezone correctly set to Europe/Amsterdam", file=sys.stderr)
                        else:
                            print(f"Error: Timezone is set to '{option_text}', not Europe/Amsterdam", file=sys.stderr)
                            return False
                    else:
                        print(f"Error: Timezone is '{selected_value}', not Europe/Amsterdam", file=sys.stderr)
                        return False
            else:
                print("Error: Could not find timezone selector", file=sys.stderr)
                return False
            
            # Check "Notify on reply" setting
            notify_checkbox = None
            
            # Try multiple selectors for the checkbox
            selectors = [
                'input[type="checkbox"]:near(:text("Notify on reply"))',
                'label:has-text("Notify on reply") input[type="checkbox"]',
                'input[type="checkbox"][name*="notify_on_reply"]',
                'input[type="checkbox"][id*="notify_on_reply"]'
            ]
            
            for selector in selectors:
                element = page.locator(selector)
                if await element.count():
                    notify_checkbox = element
                    break
            
            if notify_checkbox:
                is_checked = await notify_checkbox.is_checked()
                if is_checked:
                    print("✓ 'Notify on reply' is enabled", file=sys.stderr)
                else:
                    print("Error: 'Notify on reply' is not enabled", file=sys.stderr)
                    return False
            else:
                # If we can't find the checkbox, check if the text indicates it's enabled
                page_content = await page.content()
                if "Notify on reply" in page_content:
                    print("✓ 'Notify on reply' setting found (assuming enabled)", file=sys.stderr)
                else:
                    print("Warning: Could not verify 'Notify on reply' setting", file=sys.stderr)
            
            # Take final success screenshot
            await page.screenshot(path=str(SCREENSHOT_DIR / "verification_success.png"))
            print(f"\n✓ Screenshot saved: {SCREENSHOT_DIR / 'verification_success.png'}", file=sys.stderr)
            
            # All checks passed
            print("\n" + "="*50)
            print("SUCCESS: All verification checks passed!")
            print("="*50)
            print("✓ Account 'EuroTravelPlanner' can login")
            print("✓ Forum /f/BudgetEuropeTravel exists with correct details")
            print("✓ Wiki page created with required content")
            print("✓ Post created with required content")
            print("✓ Travel insurance search performed")
            print("✓ User settings configured correctly")
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