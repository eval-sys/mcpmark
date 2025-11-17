#!/usr/bin/env python3
"""
Verification script for Paper Counting Task: Count HTML Files
"""

import sys
from pathlib import Path
import os

def get_test_directory() -> Path:
    """Get the test directory from FILESYSTEM_TEST_DIR env var."""
    test_root = os.environ.get("FILESYSTEM_TEST_DIR")
    if not test_root:
        raise ValueError("FILESYSTEM_TEST_DIR environment variable is required")
    return Path(test_root)

def verify_count_file_exists(test_dir: Path) -> bool:
    """Verify that the count.txt file exists."""
    count_file = test_dir / "count.txt"
    
    if not count_file.exists():
        print("❌ File 'count.txt' not found")
        return False
    
    print("✅ count.txt file found")
    return True

def verify_count_content(test_dir: Path) -> bool:
    """Verify that count.txt contains the correct number (83)."""
    count_file = test_dir / "count.txt"
    
    try:
        content = count_file.read_text().strip()
        
        # Check if content is exactly "83"
        if content == "83":
            print("✅ count.txt contains the correct number: 83")
            return True
        else:
            print(f"❌ count.txt contains '{content}' but expected '83'")
            return False
        
    except Exception as e:
        print(f"❌ Error reading count.txt: {e}")
        return False

def verify_actual_html_count(test_dir: Path) -> bool:
    """Verify that there are actually 83 HTML files in the directory."""
    html_files = list(test_dir.glob("*.html"))
    count = len(html_files)
    
    if count == 83:
        print(f"✅ Verified: There are exactly {count} HTML files in the directory")
        return True
    else:
        print(f"⚠️  Found {count} HTML files in the directory (expected 83)")
        return False

def main():
    """Main verification function."""
    try:
        test_dir = get_test_directory()
        print(f"🔍 Verifying HTML file count in: {test_dir}")
        
        # Define verification steps
        verification_steps = [
            ("Count File Exists", verify_count_file_exists),
            ("Count Content", verify_count_content),
            ("Actual HTML Count", verify_actual_html_count),
        ]
        
        # Run all verification steps
        all_passed = True
        for step_name, verify_func in verification_steps:
            print(f"\n--- {step_name} ---")
            if not verify_func(test_dir):
                all_passed = False
        
        # Final result
        print("\n" + "="*50)
        if all_passed:
            print("✅ HTML file count is correct!")
            print("🎉 Task verification: PASS")
            sys.exit(0)
        else:
            print("❌ Task verification: FAIL")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Verification failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
