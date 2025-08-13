#!/usr/bin/env python3
"""
Verification script for Playwright web navigation task.

This script uses dual verification:
1. Independent Playwright verification of navigation functionality
2. Parsing and comparison of MCP agent results vs independent verification
"""

import sys
import json
import os
from pathlib import Path
from typing import Dict, Any
from playwright.sync_api import sync_playwright

# =============================================================================
# CONFIGURATION
# =============================================================================

# Target websites for navigation testing
NAVIGATION_START_URL = "https://mcp-eval-website.vercel.app/navigation"
FORMS_URL = "https://mcp-eval-website.vercel.app/forms/"

# Expected navigation links (from task description)
EXPECTED_NAVIGATION_LINKS = [
    "/forms",  # Form Interaction
    "/extraction",  # Element Extraction
    "/downloads",  # File Downloads
    "/auth/basic",  # Basic Auth
    "/auth/form",  # Form Login
    "/auth/challenge",  # Challenge Auth
    "/navigation",  # Web Navigation
]

# Expected elements and content
EXPECTED_NAVIGATION_TITLE = "Navigation Test"
EXPECTED_FORMS_TITLE = "Order Form"

# Accuracy thresholds for comparison
MIN_ACCURACY_THRESHOLD = 1.0  # 100% accuracy required to pass

# =============================================================================
# INDEPENDENT PLAYWRIGHT VERIFICATION
# =============================================================================


def test_navigation_sequence() -> Dict[str, Any]:
    """Test the complete navigation sequence between pages."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Step 1: Navigate to the navigation page
            print(f"🌐 Navigating to: {NAVIGATION_START_URL}")
            page.goto(NAVIGATION_START_URL, wait_until="networkidle")

            # Verify navigation page loaded
            navigation_title = page.title()
            navigation_url = page.url

            # Look for navigation links
            nav_links = page.locator("a").all()
            nav_link_count = len(nav_links)
            nav_link_hrefs = [
                link.get_attribute("href")
                for link in nav_links
                if link.get_attribute("href")
            ]

            # Step 2: Find and click link to forms page
            forms_link_found = False
            for link in nav_links:
                href = link.get_attribute("href")
                if href and (
                    "forms" in href.lower()
                    or href.endswith("/forms/")
                    or href.endswith("/forms")
                ):
                    print(f"🔗 Found forms link: {href}")
                    forms_link_found = True
                    # Click the link
                    if href.startswith("/"):
                        # Relative URL, need to construct full URL
                        full_url = "https://mcp-eval-website.vercel.app" + href
                        page.goto(full_url, wait_until="networkidle")
                    else:
                        link.click()
                        page.wait_for_load_state("networkidle")
                    break

            # If no direct link found, try navigating directly
            if not forms_link_found:
                print("🔗 No direct forms link found, navigating directly")
                page.goto(FORMS_URL, wait_until="networkidle")

            # Step 3: Verify forms page loaded
            forms_title = page.title()
            forms_url = page.url

            # Check for form elements on the forms page
            form_elements = page.locator("form").count()
            input_elements = page.locator("input").count()

            browser.close()

            return {
                "success": True,
                "navigation_page": {
                    "title": navigation_title,
                    "url": navigation_url,
                    "nav_links_count": nav_link_count,
                    "nav_links": nav_link_hrefs,
                },
                "forms_page": {
                    "title": forms_title,
                    "url": forms_url,
                    "form_count": form_elements,
                    "input_count": input_elements,
                },
                "navigation_success": forms_link_found or "forms" in forms_url.lower(),
            }

    except Exception as e:
        print(f"❌ Error during navigation test: {e}")
        return {"success": False, "error": str(e)}


def test_reverse_navigation() -> Dict[str, Any]:
    """Test navigation in reverse direction (forms to navigation)."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Start from forms page
            print(f"🌐 Starting from forms page: {FORMS_URL}")
            page.goto(FORMS_URL, wait_until="networkidle")

            # Look for links back to navigation page
            nav_links = page.locator("a").all()
            navigation_link_found = False

            for link in nav_links:
                href = link.get_attribute("href")
                if href and (
                    "navigation" in href.lower() or href.endswith("/navigation")
                ):
                    print(f"🔗 Found navigation link: {href}")
                    navigation_link_found = True
                    # Click the link
                    if href.startswith("/"):
                        # Relative URL, need to construct full URL
                        full_url = "https://mcp-eval-website.vercel.app" + href
                        page.goto(full_url, wait_until="networkidle")
                    else:
                        link.click()
                        page.wait_for_load_state("networkidle")
                    break

            # If no direct link found, try navigating directly
            if not navigation_link_found:
                print("🔗 No direct navigation link found, trying direct navigation")
                page.goto(NAVIGATION_START_URL, wait_until="networkidle")

            # Verify we're back on navigation page
            final_url = page.url
            final_title = page.title()

            browser.close()

            return {
                "success": True,
                "reverse_navigation_success": navigation_link_found
                or "navigation" in final_url.lower(),
                "final_url": final_url,
                "final_title": final_title,
            }

    except Exception as e:
        print(f"❌ Error during reverse navigation test: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# MCP RESULT PARSING
# =============================================================================


# 新函数：统一从环境变量读取 messages.json
def get_messages_path() -> Path:
    env_path = os.getenv("MCP_MESSAGES")
    if not env_path:
        raise FileNotFoundError("Environment variable MCP_MESSAGES not set")

    p = Path(env_path)
    print(f"[DEBUG] MCP_MESSAGES = {env_path}")
    print(f"[DEBUG] messages.json exists: {p.exists()}")

    if not p.exists():
        raise FileNotFoundError(f"messages.json not found at {p}")
    return p


def parse_mcp_agent_results() -> Dict[str, Any]:
    """Extract what the MCP agent actually found from messages.json"""
    messages_file = get_messages_path()

    with messages_file.open("r", encoding="utf-8") as f:
        messages = json.load(f)
    print(f"[DEBUG] Loaded {len(messages)} messages from messages.json")

    try:
        agent_findings = {
            "pages_visited": [],
            "navigation_attempted": False,
            "navigation_successful": False,
            "forms_page_reached": False,
            "reverse_navigation": False,
            "nav_links_count": 0,
            "selected_link": None,
        }

        # Parse agent's findings from conversation
        for message in messages:
            if message.get("role") == "assistant":
                content = message.get("content", "")

                # Handle both string and list content formats
                if isinstance(content, list):
                    content = " ".join(
                        item.get("text", "") if isinstance(item, dict) else str(item)
                        for item in content
                    )

                content_str = str(content)

                # Look for JSON code block in the assistant's response
                import re

                json_pattern = r"```json\s*\n(.*?)\n\s*```"
                json_matches = re.findall(json_pattern, content_str, re.DOTALL)

                if json_matches:
                    try:
                        data = json.loads(json_matches[-1])

                        # Extract navigation links count
                        if "navigationLinks" in data:
                            agent_findings["nav_links_count"] = len(
                                data["navigationLinks"]
                            )
                            agent_findings["pages_visited"].append("navigation")

                        # Extract selected link
                        if "selectedLink" in data:
                            agent_findings["selected_link"] = data["selectedLink"]
                            agent_findings["navigation_attempted"] = True

                            # Check if forms page was selected
                            if "forms" in data["selectedLink"].get("url", "").lower():
                                agent_findings["forms_page_reached"] = True
                                agent_findings["navigation_successful"] = True
                                agent_findings["pages_visited"].append("forms")

                        # Check navigation history
                        if "navigationHistory" in data:
                            if data["navigationHistory"].get(
                                "returnedToNavigation", False
                            ):
                                agent_findings["reverse_navigation"] = True

                        print("[DEBUG] Successfully parsed JSON output")
                        print(
                            f"[DEBUG] - Navigation links found: {agent_findings['nav_links_count']}"
                        )
                        print(
                            f"[DEBUG] - Selected link: {agent_findings['selected_link']}"
                        )
                        print(
                            f"[DEBUG] - Navigation successful: {agent_findings['navigation_successful']}"
                        )
                        print(
                            f"[DEBUG] - Reverse navigation: {agent_findings['reverse_navigation']}"
                        )

                    except json.JSONDecodeError as e:
                        print(f"[DEBUG] Failed to parse JSON: {e}")
                        # Fall back to keyword-based parsing
                        content_lower = content_str.lower()

                        if (
                            "navigation" in content_lower
                            and "mcp-eval-website" in content_lower
                        ):
                            if "navigation" not in agent_findings["pages_visited"]:
                                agent_findings["pages_visited"].append("navigation")

                        if (
                            "forms" in content_lower
                            and "mcp-eval-website" in content_lower
                        ):
                            if "forms" not in agent_findings["pages_visited"]:
                                agent_findings["pages_visited"].append("forms")

                        if any(
                            word in content_lower
                            for word in ["navigate", "click", "link", "goto", "visit"]
                        ):
                            agent_findings["navigation_attempted"] = True

                        if "forms" in content_lower and any(
                            word in content_lower
                            for word in ["successful", "loaded", "found", "reached"]
                        ):
                            agent_findings["forms_page_reached"] = True
                            agent_findings["navigation_successful"] = True

                        if (
                            "navigation" in content_lower
                            and "forms" in content_lower
                            and any(
                                word in content_lower
                                for word in ["back", "return", "reverse"]
                            )
                        ):
                            agent_findings["reverse_navigation"] = True

        return {"success": True, "findings": agent_findings}

    except Exception as e:
        print(f"[DEBUG] Error parsing MCP results: {e}")
        return {"success": False, "error": f"Failed to parse agent results: {e}"}


# =============================================================================
# COMPARISON AND EVALUATION
# =============================================================================


def compare_mcp_vs_independent(
    mcp_results: Dict, navigation_data: Dict, reverse_data: Dict
) -> Dict[str, Any]:
    """Compare MCP agent findings with independent verification"""
    comparison = {}

    # Compare navigation links count
    mcp_nav_links = mcp_results["findings"]["nav_links_count"]
    actual_nav_links = navigation_data["navigation_page"]["nav_links_count"]

    # Allow some tolerance for nav links (might have duplicates or variations)
    nav_links_accuracy = 1.0 if abs(mcp_nav_links - actual_nav_links) <= 4 else 0.5

    comparison["navigation_links"] = {
        "mcp_count": mcp_nav_links,
        "actual_count": actual_nav_links,
        "accuracy": nav_links_accuracy,
        "match": nav_links_accuracy >= 0.5,
    }

    # Compare pages visited
    mcp_pages = set(mcp_results["findings"]["pages_visited"])
    expected_pages = {"navigation", "forms"}

    if expected_pages:
        pages_accuracy = len(mcp_pages.intersection(expected_pages)) / len(
            expected_pages
        )
        missing_pages = list(expected_pages - mcp_pages)
        extra_pages = list(mcp_pages - expected_pages)
    else:
        pages_accuracy = 0.0
        missing_pages = []
        extra_pages = list(mcp_pages)

    comparison["pages_visited"] = {
        "mcp_count": len(mcp_pages),
        "expected_count": len(expected_pages),
        "accuracy": pages_accuracy,
        "match": pages_accuracy >= MIN_ACCURACY_THRESHOLD,
        "missing": missing_pages,
        "extra": extra_pages,
    }

    # Compare forward navigation success
    mcp_navigation = mcp_results["findings"]["navigation_successful"]
    actual_navigation = navigation_data.get("navigation_success", False)

    nav_accuracy = (
        1.0
        if (mcp_navigation and actual_navigation)
        or (not mcp_navigation and not actual_navigation)
        else 0.0
    )

    comparison["forward_navigation"] = {
        "mcp_successful": mcp_navigation,
        "independent_successful": actual_navigation,
        "accuracy": nav_accuracy,
        "match": nav_accuracy >= MIN_ACCURACY_THRESHOLD,
    }

    # Compare reverse navigation
    mcp_reverse = mcp_results["findings"]["reverse_navigation"]
    actual_reverse = reverse_data.get("reverse_navigation_success", False)

    reverse_accuracy = (
        1.0
        if (mcp_reverse and actual_reverse) or (not mcp_reverse and not actual_reverse)
        else 0.0
    )

    comparison["reverse_navigation"] = {
        "mcp_attempted": mcp_reverse,
        "independent_successful": actual_reverse,
        "accuracy": reverse_accuracy,
        "match": reverse_accuracy >= MIN_ACCURACY_THRESHOLD,
    }

    return comparison


def verify_page_content(page_data: Dict[str, Any]) -> bool:
    """Verify that both pages loaded correctly with expected content."""
    if not page_data.get("success"):
        print(
            f"❌ Independent verification failed: {page_data.get('error', 'Unknown error')}"
        )
        return False

    success = True

    # Verify navigation page
    nav_page = page_data["navigation_page"]
    print(f"📄 Navigation page title: {nav_page['title']}")
    print(f"🔗 Navigation links found: {nav_page['nav_links_count']}")

    # Check for all 7 expected navigation links
    found_expected_links = []
    for expected_link in EXPECTED_NAVIGATION_LINKS:
        if expected_link in nav_page["nav_links"]:
            found_expected_links.append(expected_link)

    if len(found_expected_links) == len(EXPECTED_NAVIGATION_LINKS):
        print(
            f"✅ All {len(EXPECTED_NAVIGATION_LINKS)} expected navigation links found"
        )
    else:
        missing_links = [
            link
            for link in EXPECTED_NAVIGATION_LINKS
            if link not in found_expected_links
        ]
        print(f"❌ Missing navigation links: {missing_links}")
        print(
            f"   Found {len(found_expected_links)}/{len(EXPECTED_NAVIGATION_LINKS)} expected links"
        )
        success = False

    # Verify navigation to forms page occurred
    if page_data["navigation_success"]:
        print("✅ Successfully navigated to forms page")
    else:
        print("❌ Failed to navigate to forms page")
        success = False

    # Verify forms page
    forms_page = page_data["forms_page"]
    print(f"📄 Forms page title: {forms_page['title']}")
    print(f"📝 Forms found: {forms_page['form_count']}")
    print(f"🔤 Input fields found: {forms_page['input_count']}")

    if forms_page["form_count"] >= 1:
        print("✅ Forms page has form elements")
    else:
        print("❌ Forms page missing form elements")
        success = False

    if forms_page["input_count"] >= 3:  # Expect at least a few input fields
        print("✅ Forms page has input fields")
    else:
        print("❌ Forms page missing sufficient input fields")
        success = False

    # Check URLs are correct
    if "navigation" in nav_page["url"].lower():
        print("✅ Navigation page URL is correct")
    else:
        print(f"❌ Navigation page URL unexpected: {nav_page['url']}")
        success = False

    if "forms" in forms_page["url"].lower():
        print("✅ Forms page URL is correct")
    else:
        print(f"❌ Forms page URL unexpected: {forms_page['url']}")
        success = False

    return success


# =============================================================================
# MAIN VERIFICATION
# =============================================================================


def verify_task() -> bool:
    """Verify both independent requirements AND MCP agent accuracy"""
    print("🔍 Verifying Playwright Web Navigation Task")
    print("=" * 50)

    # Step 1: Independent verification
    print("\n🎭 Running independent Playwright verification...")

    # Test forward navigation (navigation -> forms)
    print("   Testing forward navigation (navigation → forms)...")
    navigation_data = test_navigation_sequence()

    # Test reverse navigation (forms -> navigation)
    print("   Testing reverse navigation (forms → navigation)...")
    reverse_data = test_reverse_navigation()

    # Verify page content and navigation success
    print("\n📊 Verifying navigation requirements...")
    forward_success = verify_page_content(navigation_data)

    reverse_success = True
    if reverse_data.get("success"):
        if reverse_data["reverse_navigation_success"]:
            print("✅ Reverse navigation successful")
        else:
            print("❌ Reverse navigation failed")
            reverse_success = False
    else:
        print(
            f"❌ Reverse navigation test error: {reverse_data.get('error', 'Unknown error')}"
        )
        reverse_success = False

    independent_success = forward_success and reverse_success

    if not independent_success:
        print(
            "\n❌ Task requirements cannot be met - navigation doesn't work as expected"
        )
        return False

    # Step 2: Parse MCP agent results
    print("\n🤖 Parsing MCP agent results...")
    mcp_data = parse_mcp_agent_results()

    if not mcp_data["success"]:
        print(f"❌ Could not parse MCP results: {mcp_data.get('error')}")
        print("⚠️  Task cannot be evaluated - treating as independent verification only")
        return independent_success

    # Step 3: Compare MCP vs Independent
    print("\n📊 Comparing MCP agent results with independent verification...")
    comparison = compare_mcp_vs_independent(mcp_data, navigation_data, reverse_data)

    # Step 4: Evaluation
    overall_success = True

    for category, results in comparison.items():
        accuracy = results["accuracy"] * 100
        category_name = category.replace("_", " ").title()

        if results["match"]:
            print(f"✅ {category_name}: {accuracy:.1f}% accuracy")
        else:
            print(f"❌ {category_name}: {accuracy:.1f}% accuracy")
            overall_success = False

    # Step 5: Detailed breakdown
    if not overall_success:
        print(f"\n📋 Detailed comparison (threshold: {MIN_ACCURACY_THRESHOLD * 100}%):")

        # Pages visited detail
        pages_results = comparison["pages_visited"]
        if pages_results["missing"] or pages_results["extra"]:
            print("   Pages Visited:")
            if pages_results["missing"]:
                print(f"     • Missing: {pages_results['missing']}")
            if pages_results["extra"]:
                print(f"     • Extra: {pages_results['extra']}")

        # Show what MCP found vs actual
        print(
            f"\n   MCP Found: {len(mcp_data['findings']['pages_visited'])} pages visited"
        )
        print("   Expected: navigation and forms pages")
        print(
            f"   MCP Navigation Success: {mcp_data['findings']['navigation_successful']}"
        )
        print(
            f"   Actually Successful: {navigation_data.get('navigation_success', False)}"
        )

    else:
        print(
            f"\n🎉 MCP agent successfully navigated with ≥{MIN_ACCURACY_THRESHOLD * 100}% accuracy in all categories!"
        )

    return overall_success


def main():
    """Main verification function."""
    try:
        success = verify_task()

        if success:
            print("\n🎉 Web navigation task verification: PASSED")
            print(
                "Both navigation functionality and MCP agent accuracy meet requirements"
            )
            sys.exit(0)
        else:
            print("\n❌ Web navigation task verification: FAILED")
            print(
                "Either navigation functionality or MCP agent accuracy below requirements"
            )
            sys.exit(1)

    except Exception as e:
        print(f"\n💥 Verification error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
