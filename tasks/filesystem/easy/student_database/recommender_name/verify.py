#!/usr/bin/env python3
"""
Verification script for Student Database Task: Find Recommender Name
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

def verify_recommender_file_exists(test_dir: Path) -> bool:
    """Verify that the recommender.txt file exists."""
    recommender_file = test_dir / "recommender.txt"
    
    if not recommender_file.exists():
        print("❌ File 'recommender.txt' not found")
        return False
    
    print("✅ Recommender file found")
    return True

def verify_recommender_content(test_dir: Path) -> bool:
    """Verify that the recommender.txt file contains 'Brown'."""
    recommender_file = test_dir / "recommender.txt"
    
    try:
        content = recommender_file.read_text()
        
        if "Brown" in content:
            print("✅ Recommender name 'Brown' found in file")
            return True
        else:
            print("❌ Recommender name 'Brown' not found in file")
            print(f"   File content: {content.strip()}")
            return False
        
    except Exception as e:
        print(f"❌ Error reading recommender file: {e}")
        return False

def main():
    """Main verification function."""
    test_dir = get_test_directory()
    print("🔍 Verifying Student Database Task: Find Recommender Name...")
    
    # Check if recommender file exists
    print("\n--- File Existence Check ---")
    if not verify_recommender_file_exists(test_dir):
        print("\n❌ Basic verification failed, cannot proceed with content verification")
        sys.exit(1)
    
    # Verify content
    print("\n--- Content Verification ---")
    if not verify_recommender_content(test_dir):
        print("\n❌ Task verification: FAIL")
        sys.exit(1)
    
    # Final result
    print("\n" + "="*50)
    print("✅ Recommender identification completed correctly!")
    print("🎉 Task verification: PASS")
    sys.exit(0)

if __name__ == "__main__":
    main()
