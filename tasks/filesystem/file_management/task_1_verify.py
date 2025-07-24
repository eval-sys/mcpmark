#!/usr/bin/env python3
"""
Verification script for Filesystem Task 5: Basic File Sorting
"""

import os
import sys
from pathlib import Path

def get_test_directory() -> Path:
    """Get the test directory from environment variable."""
    test_dir = os.getenv("FILESYSTEM_TEST_DIR")
    if not test_dir:
        print("❌ FILESYSTEM_TEST_DIR environment variable not set")
        sys.exit(1)
    return Path(test_dir)

def verify_basic_sorting(test_dir: Path) -> bool:
    """Verify the basic file sorting."""
    all_passed = True
    
    # Check directories exist
    has_test_dir = test_dir / "has_test"
    no_test_dir = test_dir / "no_test"
    
    if not has_test_dir.exists():
        print("❌ Directory 'has_test' not found")
        return False
    print("✅ Directory 'has_test' exists")
    
    if not no_test_dir.exists():
        print("❌ Directory 'no_test' not found")
        return False
    print("✅ Directory 'no_test' exists")
    
    # Check no .txt files in root
    root_txt = list(test_dir.glob("*.txt"))
    if root_txt:
        print(f"❌ Found {len(root_txt)} .txt files still in root")
        all_passed = False
    else:
        print("✅ No .txt files remain in root")
    
    # Check files in has_test
    has_test_files = list(has_test_dir.glob("*.txt"))
    print(f"\n📁 Files in has_test: {len(has_test_files)}")
    for f in has_test_files:
        if "test" in f.read_text().lower():
            print(f"  ✅ {f.name} - contains 'test'")
        else:
            print(f"  ❌ {f.name} - NO 'test' found")
            all_passed = False
    
    # Check files in no_test
    no_test_files = list(no_test_dir.glob("*.txt"))
    print(f"\n📁 Files in no_test: {len(no_test_files)}")
    for f in no_test_files:
        if "test" not in f.read_text().lower():
            print(f"  ✅ {f.name} - no 'test'")
        else:
            print(f"  ❌ {f.name} - contains 'test'!")
            all_passed = False
    
    total = len(has_test_files) + len(no_test_files)
    print(f"\n📊 Total sorted: {total} files")
    
    if total < 4:
        print(f"❌ Too few files sorted (expected at least 4)")
        all_passed = False
    
    return all_passed

def main():
    """Main verification function."""
    print("🔍 Verifying Filesystem Task 5: Basic File Sorting")
    print("=" * 50)
    
    test_dir = get_test_directory()
    print(f"📁 Test directory: {test_dir}\n")
    
    if not verify_basic_sorting(test_dir):
        print("\n❌ Task 5 verification: FAIL")
        sys.exit(1)
    
    print("\n🎉 Task 5 verification: PASS")
    print("Files successfully sorted")
    sys.exit(0)

if __name__ == "__main__":
    main()