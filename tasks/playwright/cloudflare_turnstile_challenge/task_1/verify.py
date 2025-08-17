#!/usr/bin/env python3
"""
Simplified verification script for Playwright Cloudflare Turnstile authentication task.

This script only verifies that the model successfully reported capturing the expected
success message by checking the last assistant message in messages.json.
"""

import sys
import json
import os

# Expected success message that agent should capture
EXPECTED_SUCCESS_MESSAGE = "Authentication successful! Security challenge verified."


def get_model_response():
    """
    Get the model's response from the MCP_MESSAGES environment variable.
    Returns the last assistant message text.
    """
    messages_path = os.getenv("MCP_MESSAGES")
    print(f"MCP_MESSAGES: {messages_path}")
    if not messages_path:
        print("Warning: MCP_MESSAGES environment variable not set", file=sys.stderr)
        return None
    
    try:
        with open(messages_path, 'r') as f:
            messages = json.load(f)
        
        # Find the last assistant message with status completed
        for message in reversed(messages):
            if (message.get('role') == 'assistant' and 
                message.get('status') == 'completed' and 
                message.get('type') == 'message'):
                content = message.get('content', [])
                # Extract text from content
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get('type') in ['text', 'output_text']:
                            return item.get('text', '')
                elif isinstance(content, str):
                    return content
        
        print("Warning: No completed assistant message found", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error reading messages file: {str(e)}", file=sys.stderr)
        return None


def verify():
    """
    Verifies that the model's last response contains the expected success message.
    """
    # Get model's response from MCP_MESSAGES
    model_response = get_model_response()
    
    if not model_response:
        print("No model response found", file=sys.stderr)
        return False
    
    print(f"\nModel response (first 500 chars): {model_response[:500]}...", file=sys.stderr)
    
    # Check if the expected success message is in the model's response
    if EXPECTED_SUCCESS_MESSAGE in model_response:
        print(f"\n✓ Success message found: '{EXPECTED_SUCCESS_MESSAGE}'", file=sys.stderr)
        return True
    else:
        print(f"\n✗ Success message NOT found: '{EXPECTED_SUCCESS_MESSAGE}'", file=sys.stderr)
        return False


def main():
    """
    Executes the verification process and exits with a status code.
    """
    result = verify()
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
