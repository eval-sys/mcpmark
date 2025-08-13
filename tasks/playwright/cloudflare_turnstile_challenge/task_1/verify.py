#!/usr/bin/env python3
"""
Simplified verification script for Playwright Cloudflare Turnstile authentication task.

This script only verifies that the MCP agent correctly reported its actions
by parsing the conversation messages from messages.json.
"""

import sys
import json
import os
from pathlib import Path
from typing import Dict, Any

# =============================================================================
# CONFIGURATION
# =============================================================================

# Expected success message that agent should capture
EXPECTED_SUCCESS_MESSAGE = "Authentication successful! Security challenge verified."

# =============================================================================
# MCP RESULT PARSING
# =============================================================================

def get_working_directory() -> Path:
    """Get the working directory where messages.json should be."""
    # For MCPMark, check current directory first
    current_dir = Path.cwd()
    if (current_dir / "messages.json").exists():
        return current_dir
    
    # Fallback to environment variable
    work_dir = os.getenv("PLAYWRIGHT_WORK_DIR", ".")
    return Path(work_dir).resolve()

def parse_agent_messages(work_dir: Path) -> Dict[str, Any]:
    """Parse agent's conversation messages to verify task completion."""
    messages_file = work_dir / "messages.json"
    if not messages_file.exists():
        return {"success": False, "error": "No messages.json found"}
    
    try:
        with open(messages_file, 'r', encoding='utf-8') as f:
            messages = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        return {"success": False, "error": f"Failed to read messages.json: {e}"}
    
    # Extract all text content from conversation
    conversation_text = ""
    for message in messages:
        content = message.get("content", "")
        
        # Handle both string and list content formats
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict):
                    text_parts.append(item.get("text", ""))
                else:
                    text_parts.append(str(item))
            conversation_text += " ".join(text_parts) + " "
        else:
            conversation_text += str(content) + " "
    
    # Check if agent captured the expected success message
    success_message_found = EXPECTED_SUCCESS_MESSAGE.lower() in conversation_text.lower()
    
    return {
        "success": True,
        "success_message_found": success_message_found,
        "expected_message": EXPECTED_SUCCESS_MESSAGE,
        "conversation_text": conversation_text[:500] + "..." if len(conversation_text) > 500 else conversation_text
    }

# =============================================================================
# EVALUATION
# =============================================================================

def evaluate_success_message(parse_result: Dict[str, Any]) -> bool:
    """Evaluate if the agent captured the expected success message."""
    print("\n📋 Success Message Verification:")
    print("=" * 40)
    
    success_message_found = parse_result["success_message_found"]
    expected_message = parse_result["expected_message"]
    
    if success_message_found:
        print(f"✅ SUCCESS MESSAGE CAPTURED")
        print(f"   Expected: '{expected_message}'")
        print(f"   Status: Found in agent conversation")
    else:
        print(f"❌ SUCCESS MESSAGE NOT FOUND")
        print(f"   Expected: '{expected_message}'")
        print(f"   Status: Not found in agent conversation")
    
    return success_message_found

# =============================================================================
# MAIN VERIFICATION
# =============================================================================

def verify_task() -> bool:
    """Verify MCP agent completed Turnstile authentication task by analyzing messages."""
    print("🔍 Verifying Playwright Cloudflare Turnstile Authentication Task")
    print("=" * 60)
    
    # Parse agent's conversation messages
    work_dir = get_working_directory()
    print(f"📁 Working directory: {work_dir}")
    
    parse_result = parse_agent_messages(work_dir)
    
    if not parse_result["success"]:
        print(f"❌ Could not parse agent messages: {parse_result.get('error')}")
        return False
    
    # Evaluate if agent captured the success message
    task_completed = evaluate_success_message(parse_result)
    
    # Show sample of agent conversation for debugging
    print(f"\n💬 Agent Conversation Sample:")
    print(f"   {parse_result['conversation_text']}")
    
    if task_completed:
        print(f"\n🎉 Agent successfully captured the Turnstile authentication success message!")
    else:
        print(f"\n❌ Agent did not capture the expected success message.")
        print(f"⚠️  Agent may not have completed the authentication or failed to report the result.")
    
    return task_completed

def main():
    """Main verification function."""
    try:
        success = verify_task()
        
        if success:
            print("\n🎉 Turnstile authentication task verification: PASSED")
            print("Agent successfully captured the authentication success message")
            sys.exit(0)
        else:
            print("\n❌ Turnstile authentication task verification: FAILED")
            print("Agent did not capture the expected authentication success message")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Verification error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()