#!/usr/bin/env python3
"""
Verification script for Filesystem Task 1: Create and Write File
"""

import sys
from pathlib import Path
import re

def get_test_directory() -> Path:
    """Get the test directory using relative path."""
    # Use relative path from this script to test environment
    script_dir = Path(__file__).parent
    return script_dir / "../../../test_environments/desktop"

def verify_task(test_dir: Path) -> bool:
    """Verify the task was completed correctly."""
    file_path = test_dir / "new_document.txt"
    
    # Check file exists
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return False
    
    # Check content
    try:
        content = file_path.read_text()
        required = ["New Document Created by MCP", "MCP tools", "Creation date:", "Complete"]
        
        for pattern in required:
            if pattern.lower() not in content.lower():
                print(f"❌ Missing: '{pattern}'")
                return False
        
        if not re.search(r'\d{4}-\d{2}-\d{2}', content):
            print("❌ Missing date in YYYY-MM-DD format")
            return False
        
        print("✅ File created with correct content")
        return True
        
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False

def main():
    """Main verification function."""    
    test_dir = get_test_directory()
    
    if verify_task(test_dir):
        print("🎉 Task 1 verification: PASS")
        sys.exit(0)
    else:
        print("❌ Task 1 verification: FAIL")
        sys.exit(1)

if __name__ == "__main__":
    main()