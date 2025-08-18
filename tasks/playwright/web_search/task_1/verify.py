#!/usr/bin/env python3
"""
Verification script for Playwright web search task.

Simple verification that checks if the AI agent found the correct answer.
Since we know the answer is "Andrew Jackson", we just parse the AI's results.
"""

import sys
import json
import os
from pathlib import Path
from typing import Dict, Any

# =============================================================================
# CONFIGURATION
# =============================================================================

# Expected answer (case insensitive)
EXPECTED_PRESIDENT = "Andrew Jackson"
ACCEPTED_PRESIDENT_NAMES = [
    "andrew jackson",
    "jackson",
    "president andrew jackson",
    "president jackson",
]

# =============================================================================
# MCP RESULT PARSING
# =============================================================================


def get_working_directory() -> Path:
    """Get the working directory where messages.json should be."""
    # Priority 1: Use MCP_MESSAGES path if available (most reliable)
    messages_path = os.getenv("MCP_MESSAGES")
    if messages_path and Path(messages_path).exists():
        return Path(messages_path).parent.resolve()
    
    # Priority 2: Use PLAYWRIGHT_WORK_DIR environment variable
    work_dir = os.getenv("PLAYWRIGHT_WORK_DIR")
    if work_dir:
        work_path = Path(work_dir).resolve()
        if (work_path / "messages.json").exists():
            return work_path
    
    # Priority 3: Check current directory (fallback)
    current_dir = Path.cwd()
    if (current_dir / "messages.json").exists():
        return current_dir
    
    # Priority 4: Default fallback
    return Path(".").resolve()


def parse_ai_results(work_dir: Path) -> Dict[str, Any]:
    """Parse the AI agent's results from messages.json"""
    messages_file = work_dir / "messages.json"
    if not messages_file.exists():
        return {"success": False, "error": "No messages.json found"}

    try:
        with open(messages_file, "r", encoding="utf-8") as f:
            messages = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        return {"success": False, "error": f"Failed to read messages.json: {e}"}

    # Look for Andrew Jackson in the AI's responses
    found_andrew_jackson = False
    ai_responses = []

    for message in messages:
        if message.get("role") == "assistant":
            content = str(message.get("content", ""))

            # Handle both string and list content formats
            if isinstance(message.get("content"), list):
                content = " ".join(
                    item.get("text", "") if isinstance(item, dict) else str(item)
                    for item in message.get("content", [])
                )

            ai_responses.append(content)
            content_lower = content.lower()

            # Check if Andrew Jackson was found (case insensitive)
            if any(name in content_lower for name in ACCEPTED_PRESIDENT_NAMES):
                found_andrew_jackson = True

    return {
        "success": True,
        "found_andrew_jackson": found_andrew_jackson,
        "ai_responses": ai_responses,
        "total_responses": len(ai_responses),
    }


# =============================================================================
# MAIN VERIFICATION
# =============================================================================


def verify_task() -> bool:
    """Verify the AI agent found the correct answer"""
    print("| Verifying Playwright Web Search Task")

    # Parse AI agent results
    print("🤖 Parsing AI agent results...")
    work_dir = get_working_directory()
    print(f"📁 Working directory: {work_dir}")

    ai_results = parse_ai_results(work_dir)

    if not ai_results["success"]:
        print(f"❌ Could not parse AI results: {ai_results.get('error')}")
        return False

    # Check results
    print(f"📊 AI agent provided {ai_results['total_responses']} responses")

    if ai_results["found_andrew_jackson"]:
        print("✅ AI agent correctly identified: Andrew Jackson")
        print("🎉 Task verification: PASSED")
        return True
    else:
        print("❌ AI agent did not find the correct answer: Andrew Jackson")
        print(
            "💡 Expected one of: Andrew Jackson, Jackson, President Andrew Jackson, President Jackson"
        )
        print("❌ Task verification: FAILED")
        return False


def main():
    """Main verification function."""
    try:
        success = verify_task()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n💥 Verification error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
