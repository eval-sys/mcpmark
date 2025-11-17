#!/usr/bin/env python3
"""
Verification script for Find Math Paper Task
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

def verify_answer_file_exists(test_dir: Path) -> bool:
    """Verify that answer.html exists in the papers directory."""
    answer_file = test_dir  / "answer.html"
    
    if not answer_file.exists():
        print("❌ File 'answer.html' not found")
        return False
    
    print("✅ answer.html found")
    return True

def verify_original_file_removed(test_dir: Path) -> bool:
    """Verify that the original file (2407.01284.html) no longer exists."""
    original_file = test_dir  / "2407.01284.html"
    
    if original_file.exists():
        print("❌ Original file 2407.01284.html still exists")
        return False
    
    print("✅ Original file has been renamed")
    return True

def main():
    """Main verification function."""
    test_dir = get_test_directory()
    print("🔍 Verifying Find Math Paper Task...")
    
    # Define verification steps
    verification_steps = [
        ("Answer File Exists", verify_answer_file_exists),
        ("Original File Renamed", verify_original_file_removed),
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
        print("✅ Paper correctly renamed to answer.html!")
        print("🎉 Task verification: PASS")
        sys.exit(0)
    else:
        print("❌ Task verification: FAIL")
        sys.exit(1)

if __name__ == "__main__":
    main()