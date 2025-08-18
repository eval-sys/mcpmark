#!/usr/bin/env python3
"""
Verification script for checking Playwright SVG icons download tasks.

This script verifies whether the model successfully downloaded SVG icons from the "All Icons" section
by checking the last assistant message in messages.json and verifying downloaded files.
"""

import sys
import json
import os
import re
import glob
from pathlib import Path

# Expected output patterns for SVG download task
EXPECTED_PATTERNS = [
    r"All Icons",
    r"SVG",
    r"download",
    r"icon",
    r"successfully downloaded",
    r"total.*icon",
    r"downloaded.*icon"
]

# Expected file extensions
EXPECTED_EXTENSIONS = ['.svg']

# Minimum expected icons (adjust based on actual website content)
MIN_EXPECTED_ICONS = 1


def get_model_response():
    """
    Get the model's response from the MCP_MESSAGES environment variable.
    Returns the last assistant message text.
    """
    messages_path = os.getenv("MCP_MESSAGES")
    print(f"| MCP_MESSAGES: {messages_path}")
    if not messages_path:
        print("| Warning: MCP_MESSAGES environment variable not set", file=sys.stderr)
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

        print("| Warning: No completed assistant message found", file=sys.stderr)
        return None
    except Exception as e:
        print(f"| Error reading messages file: {str(e)}", file=sys.stderr)
        return None


def check_downloaded_files():
    """
    Check for downloaded SVG files in the current directory.
    """
    current_dir = Path.cwd()
    print(f"| Checking for downloaded files in: {current_dir}")
    
    # Look for SVG files
    svg_files = list(current_dir.glob("*.svg"))
    print(f"| Found {len(svg_files)} SVG files")
    
    # Look for any downloaded files
    all_files = list(current_dir.glob("*"))
    downloaded_files = [f for f in all_files if f.is_file() and f.name != '.DS_Store']
    
    print(f"| Total downloaded files: {len(downloaded_files)}")
    for file in downloaded_files:
        print(f"|   - {file.name}")
    
    return svg_files, downloaded_files


def validate_response_content(response):
    """
    Validate that the response contains appropriate content for SVG download task.
    """
    if not response:
        return False, "No response found"
    
    # Check for expected patterns
    found_patterns = []
    for pattern in EXPECTED_PATTERNS:
        if re.search(pattern, response, re.IGNORECASE):
            found_patterns.append(pattern)
    
    print(f"| Found patterns: {found_patterns}")
    
    # Check for download-related keywords
    download_keywords = ['download', 'downloaded', 'icon', 'svg', 'file', 'save']
    found_keywords = [kw for kw in download_keywords if kw.lower() in response.lower()]
    
    print(f"| Found keywords: {found_keywords}")
    
    # Check for success indicators
    success_indicators = ['success', 'successfully', 'completed', 'finished', 'done']
    has_success = any(indicator in response.lower() for indicator in success_indicators)
    
    # Check for numeric information (count of icons)
    has_count = bool(re.search(r'\d+.*icon', response, re.IGNORECASE))
    
    # Basic validation criteria
    if len(found_patterns) >= 3 and len(found_keywords) >= 3:
        return True, f"Response contains appropriate content: {len(found_patterns)} patterns, {len(found_keywords)} keywords"
    
    return False, f"Insufficient content: only {len(found_patterns)} patterns and {len(found_keywords)} keywords found"


def verify():
    """
    Verify if the model's response indicates successful SVG icon download.
    """
    # Get model response
    model_response = get_model_response()

    if not model_response:
        print("| Model response not found", file=sys.stderr)
        return False

    print(f"|\n| Model response (first 500 characters): {model_response[:500]}...", file=sys.stderr)

    # Check for downloaded files
    svg_files, downloaded_files = check_downloaded_files()
    
    # Validate response content
    is_valid_content, content_message = validate_response_content(model_response)
    
    print(f"|\n| Content validation: {content_message}", file=sys.stderr)
    
    # Check if we have any downloaded files
    has_downloads = len(downloaded_files) > 0
    has_svg_files = len(svg_files) > 0
    
    print(f"| Has downloaded files: {has_downloads}")
    print(f"| Has SVG files: {has_svg_files}")
    
    # Overall validation
    if is_valid_content and has_downloads:
        print(f"|\n| ✓ SVG download task appears successful", file=sys.stderr)
        print(f"|   - Content validation: PASSED", file=sys.stderr)
        print(f"|   - File downloads: {len(downloaded_files)} files found", file=sys.stderr)
        if has_svg_files:
            print(f"|   - SVG files: {len(svg_files)} found", file=sys.stderr)
        return True
    else:
        print(f"|\n| ✗ SVG download task validation failed", file=sys.stderr)
        if not is_valid_content:
            print(f"|   - Content validation: FAILED - {content_message}", file=sys.stderr)
        if not has_downloads:
            print(f"|   - File downloads: FAILED - No downloaded files found", file=sys.stderr)
        return False


def main():
    """
    Executes the verification process and exits with a status code.
    """
    result = verify()
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
