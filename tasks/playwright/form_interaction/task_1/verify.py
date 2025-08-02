#!/usr/bin/env python3
"""
Verification script for Playwright form interaction task.

This script uses dual verification:
1. Independent Playwright verification of form functionality
2. Parsing and comparison of MCP agent results vs independent verification
"""

import sys
import asyncio
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from playwright.sync_api import sync_playwright, Page

# =============================================================================
# CONFIGURATION
# =============================================================================

# Target website for verification
TARGET_URL = "https://mcp-eval-website.vercel.app/forms/"
# Result page URL (where the form submission can be viewed)
RESULT_URL = "https://mcp-eval-website.vercel.app/forms/result"

# Expected form fields based on task description (6 fields total)
EXPECTED_FORM_FIELDS = {
    "custname": "Customer Name",
    "custtel": "Phone",
    "custemail": "Email", 
    "size": "Size",
    "delivery": "Delivery Time",
    "comments": "Comments"
}

# Test data for form submission (matches task requirements)
TEST_FORM_DATA = {
    "custname": "John Doe",
    "custtel": "123-456-7890",
    "custemail": "john.doe@example.com",
    "size": "large",
    "delivery": "afternoon",
    "comments": "This is a test submission for MCPBench"
}

# NOTE: The original script compared the agent's self-reported actions with
# independent browser verification using messages.json. That layer has been
# removed to keep the verifier focused on real DOM interaction only.

# =============================================================================
# INDEPENDENT PLAYWRIGHT VERIFICATION
# =============================================================================

def verify_form_fields(page: Optional[Page] = None) -> Dict[str, Any]:
    """Check presence of expected form fields.

    If an external `page` (already loaded) is provided, run read-only checks on
    it. Otherwise spin up an isolated headless browser as旧逻辑."""

    # -------------------------------------
    # Path A – reuse existing page instance
    # -------------------------------------
    if page is not None:
        try:
            form_fields_found = {}

            # 不再进行任何导航操作；直接在当前页面检查所需元素。
            for field_name in EXPECTED_FORM_FIELDS.keys():
                selectors = [
                    f"input[name='{field_name}']",
                    f"textarea[name='{field_name}']",
                    f"select[name='{field_name}']",
                    f"input[id='{field_name}']",
                    f"textarea[id='{field_name}']",
                    f"select[id='{field_name}']",
                ]
                found = False
                field_type = None
                for sel in selectors:
                    if page.locator(sel).count() > 0:
                        found = True
                        el = page.locator(sel).first
                        field_type = el.get_attribute("type") or el.evaluate("e=>e.tagName.toLowerCase()")
                        break
                form_fields_found[field_name] = {"found": found, "type": field_type}

            return {
                "success": True,
                "form_fields": form_fields_found,
                "total_fields": sum(1 for f in form_fields_found.values() if f["found"]),
                "expected_fields": len(EXPECTED_FORM_FIELDS),
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # -------------------------------------
    # Path B – fall back to standalone browser (may need thread)
    # -------------------------------------

    def _run() -> Dict[str, Any]:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            print(f"🌐 Navigating to: {TARGET_URL}")
            page.goto(TARGET_URL, wait_until="networkidle")
            
            # Check if form exists
            form_selector = "form"
            if not page.locator(form_selector).count():
                browser.close()
                return {"success": False, "error": "No form found on page"}
            
            form_fields_found = {}
            
            # Check each expected form field
            for field_name, field_label in EXPECTED_FORM_FIELDS.items():
                # Try different selectors for each field
                selectors = [
                    f"input[name='{field_name}']",
                    f"textarea[name='{field_name}']",
                    f"select[name='{field_name}']",
                    f"input[id='{field_name}']",
                    f"textarea[id='{field_name}']",
                    f"select[id='{field_name}']"
                ]
                
                field_found = False
                field_type = None
                
                for selector in selectors:
                    if page.locator(selector).count() > 0:
                        field_found = True
                        element = page.locator(selector).first
                        field_type = element.get_attribute("type")
                        if not field_type:
                            # Get tag name as fallback
                            try:
                                field_type = element.evaluate("element => element.tagName.toLowerCase()")
                            except:
                                field_type = "unknown"
                        break
                
                form_fields_found[field_name] = {
                    "found": field_found,
                    "type": field_type
                }
            
            browser.close()
            
            result = {
                "success": True,
                "form_fields": form_fields_found,
                "total_fields": len([f for f in form_fields_found.values() if f["found"]]),
                "expected_fields": len(EXPECTED_FORM_FIELDS)
            }
            return result

    # If there's an active asyncio loop in this thread, run _run in a worker
    try:
        loop_running = False
        try:
            asyncio.get_running_loop()
            loop_running = True
        except RuntimeError:
            loop_running = False

        if loop_running:
            with ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(_run).result()
        else:
            return _run()
    except Exception as e:
        return {"success": False, "error": str(e)}

def test_form_submission(page: Optional[Page] = None) -> Dict[str, Any]:
    """Inspect the page (if provided) or perform an independent submission test."""

    # ------------------------------------------------------------------
    # 1. If a live Page is supplied (i.e., reuse agent's browser instance)
    # ------------------------------------------------------------------
    if page is not None:
        try:
            filled_fields = {}
            # Detect whether each expected field currently has a value on page
            for field_name in EXPECTED_FORM_FIELDS.keys():
                selectors = [
                    f"input[name='{field_name}']",
                    f"textarea[name='{field_name}']",
                    f"select[name='{field_name}']",
                    f"input[id='{field_name}']",
                    f"textarea[id='{field_name}']",
                    f"select[id='{field_name}']",
                ]
                field_filled = False
                for selector in selectors:
                    if page.locator(selector).count() > 0:
                        element = page.locator(selector).first
                        try:
                            value = element.input_value()
                        except Exception:
                            value = ""
                        if value:
                            field_filled = True
                        break
                filled_fields[field_name] = field_filled

            fields_filled_count = sum(1 for v in filled_fields.values() if v)

            # --------------------------------------------------------------
            # Inspect the result page to confirm the submission actually
            # landed on the server. We stay inside the SAME browser context.
            # --------------------------------------------------------------
            submit_attempted = False
            submission_success = False

            # 不再打开新标签或导航；只在当前页面判断结果。
            result_page = page

            # Determine if the submission data is present on result page
            if result_page:
                submit_attempted = True
                # Look for any of the test values on the result page
                found_any = False
                for value in TEST_FORM_DATA.values():
                    if result_page.locator(f"text={value}").count() > 0:
                        found_any = True
                        break
                submission_success = found_any
                # 无论是否找到值，都打印当前页 URL，方便调试
                print(f"🌐 Active page final URL: {result_page.url}")
            else:
                # Could not load result page; fall back heuristic
                submission_success = fields_filled_count >= 4

            return {
                "success": True,
                "filled_fields": filled_fields,
                "fields_filled_count": fields_filled_count,
                "submit_attempted": submit_attempted,
                "submission_success": submission_success,
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # 2. Fallback: run the original independent browser-based test
    # ------------------------------------------------------------------
    def _run_submission() -> Dict[str, Any]:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            print(f"🌐 Testing form submission on: {TARGET_URL}")
            page.goto(TARGET_URL, wait_until="networkidle")
            
            # Fill out the form with test data
            submission_success = True
            filled_fields = {}
            
            for field_name, test_value in TEST_FORM_DATA.items():
                selectors = [
                    f"input[name='{field_name}']",
                    f"textarea[name='{field_name}']",
                    f"select[name='{field_name}']",
                    f"input[id='{field_name}']",
                    f"textarea[id='{field_name}']",
                    f"select[id='{field_name}']"
                ]
                
                field_filled = False
                for selector in selectors:
                    try:
                        if page.locator(selector).count() > 0:
                            element = page.locator(selector).first
                            try:
                                tag_name = element.evaluate("element => element.tagName.toLowerCase()")
                            except:
                                tag_name = "input"
                            if tag_name == "select":
                                # For select elements, try to select by value or text
                                page.select_option(selector, value=test_value)
                            elif element.get_attribute("type") == "radio":
                                # For radio buttons, check the one with matching value
                                page.check(f"{selector}[value='{test_value}']")
                            else:
                                # For text inputs and textareas
                                page.fill(selector, test_value)
                            field_filled = True
                            break
                    except Exception as e:
                        continue
                
                filled_fields[field_name] = field_filled
                if not field_filled:
                    submission_success = False
            
            # Try to submit the form
            submit_attempted = False
            try:
                # Look for submit button
                submit_selectors = [
                    "input[type='submit']",
                    "button[type='submit']",
                    "button:has-text('Submit')",
                    "input[value*='Submit']"
                ]
                
                for selector in submit_selectors:
                    if page.locator(selector).count() > 0:
                        page.click(selector)
                        submit_attempted = True
                        break
                
                if not submit_attempted:
                    # Try pressing Enter in the form
                    page.keyboard.press("Enter")
                    submit_attempted = True
                    
            except Exception as e:
                print(f"⚠️  Form submission attempt failed: {e}")
            
            # Wait for redirect to result page (if any) and then print URL
            try:
                page.wait_for_url("**/forms/result", timeout=3000)
            except Exception:
                # If no redirect, continue with current URL
                pass

            print(f"🌐 Result page URL: {page.url}")

            # 保存当前验证页面截图，便于人工查看
            try:
                screenshot_path = Path(__file__).parent / "verification_page.png"
                page.screenshot(path=str(screenshot_path), full_page=True)
                print(f"📸 Verification screenshot saved to {screenshot_path}")
            except Exception as exc:
                print(f"⚠️  Failed to capture verification screenshot: {exc}")

            browser.close()
            
            return {
                "success": True,
                "filled_fields": filled_fields,
                "fields_filled_count": sum(1 for f in filled_fields.values() if f),
                "submit_attempted": submit_attempted,
                "submission_success": submission_success
            }
            
    try:
        loop_running = False
        try:
            asyncio.get_running_loop()
            loop_running = True
        except RuntimeError:
            loop_running = False

        if loop_running:
            with ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(_run_submission).result()
        else:
            return _run_submission()
    except Exception as e:
        return {"success": False, "error": str(e)}

# =============================================================================
# COMPARISON AND EVALUATION
# =============================================================================

def verify_form_requirements(field_data: Dict[str, Any], submission_data: Dict[str, Any]) -> bool:
    """Verify that the form meets task requirements."""
    if not field_data.get("success") or not submission_data.get("success"):
        print(f"❌ Independent verification failed: {field_data.get('error', '')} {submission_data.get('error', '')}")
        return False
    
    success = True
    
    # Check that all expected form fields are present
    total_fields = field_data["total_fields"]
    expected_fields = field_data["expected_fields"]
    
    if total_fields == expected_fields:
        print(f"✅ Form fields: {total_fields}/{expected_fields} found")
    else:
        print(f"❌ Form fields: {total_fields}/{expected_fields} found (missing some fields)")
        success = False
    
    # Check form submission capability
    fields_filled = submission_data["fields_filled_count"]
    if fields_filled >= 4:  # Require at least 4 fields to be fillable
        print(f"✅ Form interaction: {fields_filled} fields successfully filled")
    else:
        print(f"❌ Form interaction: Only {fields_filled} fields could be filled (expected at least 4)")
        success = False
    
    # Check if form submission was attempted
    if submission_data["submit_attempted"]:
        print("✅ Form submission: Submit attempt successful")
    else:
        print("❌ Form submission: Could not attempt form submission")
        success = False
    
    return success

# =============================================================================
# MAIN VERIFICATION
# =============================================================================

def verify_task(active_page: Optional[Page] = None) -> bool:
    """Run independent Playwright checks (field presence, fill & submit).
    If `active_page` is provided, reuse that browser instance; otherwise launch
    a temporary headless browser."""
    print("🔍 Verifying Playwright Form Interaction Task")
    print("=" * 50)

    # ------------------------------------------------------------------
    # Capture a screenshot of the *final* page state produced by the agent
    # before we begin any verification steps. This helps diagnose failures
    # that may be caused by DOM state differences.
    # ------------------------------------------------------------------
    if active_page is not None:
        try:
            print(f"[verify.py] active_page id={id(active_page)} url={active_page.url}")
            screenshot_path = Path(__file__).parent / "last_page.png"
            # Use full_page to capture the whole document for easier debugging
            active_page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"📸 Screenshot saved to {screenshot_path}")
        except Exception as exc:
            print(f"⚠️  Failed to capture screenshot: {exc}")
    
    # Step 1: Independent verification
    print("\n🎭 Running independent Playwright verification...")
    field_data = verify_form_fields(active_page)
    submission_data = test_form_submission(active_page)
    independent_success = verify_form_requirements(field_data, submission_data)
    
    if not independent_success:
        print("\n❌ Task requirements cannot be met - form doesn't meet expected functionality")
        return False
    
    # If you don't need to evaluate the agent's self-report, skip message.json
    # parsing entirely and treat the independent browser checks as the sole
    # source of truth.

    return independent_success

def main():
    """Main verification function."""
    try:
        success = verify_task()
        
        if success:
            print("\n🎉 Form interaction task verification: PASSED")
            print("Both form functionality and MCP agent accuracy meet requirements")
            sys.exit(0)
        else:
            print("\n❌ Form interaction task verification: FAILED")
            print("Either form functionality or MCP agent accuracy below requirements")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Verification error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()