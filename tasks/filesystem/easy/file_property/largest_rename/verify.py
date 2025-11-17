#!/usr/bin/env python3
"""
Verification script for Largest File Rename Task
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

def verify_sg_jpg_not_exists(test_dir: Path) -> bool:
    """Verify that sg.jpg does not exist."""
    sg_file = test_dir / "sg.jpg"
    
    if sg_file.exists():
        print("❌ sg.jpg still exists (should be renamed)")
        return False
    
    print("✅ sg.jpg does not exist")
    return True

def verify_largest_jpg_exists(test_dir: Path) -> bool:
    """Verify that largest.jpg exists."""
    largest_file = test_dir / "largest.jpg"
    
    if not largest_file.exists():
        print("❌ largest.jpg does not exist")
        return False
    
    print("✅ largest.jpg exists")
    return True

def main():
    """Main verification function."""
    try:
        test_dir = get_test_directory()
        print(f"🔍 Verifying largest file rename in: {test_dir}")
        
        # Run all verification checks
        checks = [
            ("sg.jpg does not exist", verify_sg_jpg_not_exists),
            ("largest.jpg exists", verify_largest_jpg_exists)
        ]
        
        all_passed = True
        for check_name, check_func in checks:
            print(f"\n📋 Checking: {check_name}")
            if not check_func(test_dir):
                all_passed = False
        
        if all_passed:
            print("\n🎉 All verification checks passed!")
            sys.exit(0)
        else:
            print("\n❌ Some verification checks failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Verification failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()