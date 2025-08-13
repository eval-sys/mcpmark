#!/usr/bin/env python3
"""
Verification script for Playwright form interaction task.

Uses Playwright to navigate to the result page and verify the data directly.
"""

import sys
import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright
from typing import Dict, Any
import os

# Expected form data from task description
EXPECTED_DATA = {
    "customer_name": "John Doe",
    "phone_number": "123-456-7890",
    "email_address": "john.doe@example.com",
    "size": "large",  # Backend normalizes to lowercase  
    "delivery_time": "afternoon",  # Backend normalizes to lowercase
    "comments": "This is a test submission for MCPMark"
}

def locate_messages_json() -> Path:
    """
    Search for messages.json starting at CWD and walking up parent directories.
    Returns the Path if found, otherwise raises FileNotFoundError.
    """
    cur = Path.cwd().resolve()
    for path in [cur, *cur.parents]:
        candidate = path / "messages.json"
        if candidate.exists():
            return candidate
    raise FileNotFoundError("No messages.json found in current or parent directories")

def get_submission_id_from_messages() -> int:
    """Extract submission ID from MCP agent messages."""
    env_path = os.getenv("MCP_MESSAGES")
    if not env_path:
        raise FileNotFoundError("Environment variable MCP_MESSAGES not set")

    messages_file = Path(env_path)
    if not messages_file.exists():
        raise FileNotFoundError(f"messages.json not found at {messages_file}")

    # DEBUG（可选）
    print(f"[DEBUG] Using messages.json from: {messages_file}")

    with messages_file.open("r", encoding="utf-8") as f:
        messages = json.load(f)
    print(f"[DEBUG] Loaded {len(messages)} messages from messages.json")

    # Look for result page URL in agent messages
    for message in messages:
        if message.get("type") == "function_call_output":
            output = str(message.get("output", ""))
            if "/forms/result/" in output:
                match = re.search(r'/forms/result/(\d+)', output)
                if match:
                    return int(match.group(1))
    
    raise Exception("No result page URL found in agent messages")

def verify_result_page_with_playwright(submission_id: int) -> Dict[str, Any]:
    """Navigate to result page with Playwright and verify the data."""
    result_url = f"https://mcp-eval-website.vercel.app/forms/result/{submission_id}"
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            print(f"📍 Navigating to result page: {result_url}")
            page.goto(result_url, wait_until="networkidle")
            
            # Check if page loaded successfully
            if "404" in page.title() or "not found" in page.content().lower():
                browser.close()
                return {"success": False, "error": f"Result page not found: {result_url}"}
            
            # Extract data from the page
            page_content = page.inner_text("body")
            print(f"📄 Page content loaded, checking data...")
            
            # Verify each field
            data_matches = {}
            extracted_data = {}
            
            # Check each expected field in the page content
            content_lower = page_content.lower()
            
            for field, expected_value in EXPECTED_DATA.items():
                expected_lower = expected_value.lower()
                if expected_lower in content_lower:
                    data_matches[field] = True
                    extracted_data[field] = expected_value
                    print(f"   ✅ {field}: '{expected_value}' found")
                else:
                    data_matches[field] = False
                    extracted_data[field] = "NOT FOUND"
                    print(f"   ❌ {field}: '{expected_value}' not found")
            
            browser.close()
            
            return {
                "success": True,
                "submission_id": submission_id,
                "extracted_data": extracted_data,
                "data_matches": data_matches,
                "all_correct": all(data_matches.values()),
                "page_content": page_content[:500] + "..." if len(page_content) > 500 else page_content
            }
            
    except Exception as e:
        return {"success": False, "error": f"Playwright verification failed: {str(e)}"}

def verify_task() -> bool:
    """Main verification function."""
    print("🔍 Verifying Playwright Form Interaction Task")
    print("=" * 50)
    
    try:
        # Step 1: Get submission ID from agent messages
        print("📋 Extracting submission ID from agent messages...")
        submission_id = get_submission_id_from_messages()
        print(f"✅ Found submission ID: {submission_id}")
        
        # Step 2: Navigate to result page with Playwright and verify
        print("🎭 Using Playwright to verify result page data...")
        result = verify_result_page_with_playwright(submission_id)
        
        if not result["success"]:
            print(f"❌ {result['error']}")
            return False
        
        # Step 3: Check results
        if result["all_correct"]:
            print("✅ All submitted data appears correctly on result page")
            return True
        else:
            print("❌ Some submitted data is incorrect:")
            for field, matches in result["data_matches"].items():
                status = "✅" if matches else "❌"
                expected = EXPECTED_DATA[field]
                actual = result["extracted_data"].get(field, "NOT FOUND")
                print(f"   {status} {field}: expected '{expected}', got '{actual}'")
            return False
            
    except Exception as e:
        print(f"❌ Verification error: {e}")
        return False

def main():
    """Entry point."""
    try:
        success = verify_task()
        if success:
            print("\n🎉 Form interaction task verification: PASSED")
            sys.exit(0)
        else:
            print("\n❌ Form interaction task verification: FAILED")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Verification error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()