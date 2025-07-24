#!/usr/bin/env python3
"""
Verification script for Filesystem Task 2: Read and Edit File
"""

import os
import sys
from pathlib import Path
import re

# =============================================================================
# CONFIGURATION
# =============================================================================

# File to check
FILE_NAME = "sample.txt"

# Expected changes
OLD_TEXT = "This is a sample file"
NEW_TEXT = "This is an edited file"
REQUIRED_END_TEXT = "Edited by MCPBench"

# =============================================================================
# IMPLEMENTATION
# =============================================================================

def get_test_directory() -> Path:
    """Get the test directory from environment variable."""
    test_dir = os.getenv("FILESYSTEM_TEST_DIR")
    if not test_dir:
        print("❌ FILESYSTEM_TEST_DIR environment variable not set")
        sys.exit(1)
    return Path(test_dir)

def verify_file_edited(test_dir: Path, file_name: str) -> bool:
    """Verify that the file has been edited correctly."""
    file_path = test_dir / file_name
    
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return False
    
    try:
        content = file_path.read_text()
        print(f"\n📄 Current file content:\n{content}\n")
        
        all_passed = True
        
        # Check that old text has been replaced
        if OLD_TEXT in content:
            print(f"❌ Original text '{OLD_TEXT}' still present (should be replaced)")
            all_passed = False
        else:
            print(f"✅ Original text '{OLD_TEXT}' has been replaced")
        
        # Check that new text is present
        if NEW_TEXT in content:
            print(f"✅ New text '{NEW_TEXT}' found")
        else:
            print(f"❌ New text '{NEW_TEXT}' not found")
            all_passed = False
        
        # Check for the MCPBench edit line
        if REQUIRED_END_TEXT in content:
            print(f"✅ Found '{REQUIRED_END_TEXT}' in the file")
        else:
            print(f"❌ Missing '{REQUIRED_END_TEXT}' in the file")
            all_passed = False
        
        # Check if the last line contains the edit message with date
        lines = content.strip().split('\n')
        if lines:
            last_line = lines[-1]
            if REQUIRED_END_TEXT in last_line:
                print(f"✅ Last line contains edit message: '{last_line}'")
                
                # Check for date pattern (YYYY-MM-DD or similar)
                date_pattern = r'\d{4}[-/]\d{1,2}[-/]\d{1,2}'
                if re.search(date_pattern, last_line):
                    print("✅ Date found in edit message")
                else:
                    print("⚠️  No date pattern found in edit message (optional)")
            else:
                print(f"❌ Last line does not contain '{REQUIRED_END_TEXT}'")
                all_passed = False
        
        # Verify original content structure is somewhat preserved
        if "testing" in content.lower():
            print("✅ Original content structure appears preserved")
        else:
            print("⚠️  Some original content may be missing")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False

def main():
    """Main verification function."""
    print("🔍 Verifying Filesystem Task 2: Read and Edit File")
    print("=" * 50)
    
    # Get test directory
    test_dir = get_test_directory()
    print(f"📁 Test directory: {test_dir}")
    
    # Verify file has been edited correctly
    if not verify_file_edited(test_dir, FILE_NAME):
        print("\n❌ Task 2 verification: FAIL")
        print("File was not edited correctly")
        sys.exit(1)
    
    print("\n🎉 Task 2 verification: PASS")
    print(f"File {FILE_NAME} edited successfully with correct changes")
    sys.exit(0)

if __name__ == "__main__":
    main()