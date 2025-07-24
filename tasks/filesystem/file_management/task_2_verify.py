#!/usr/bin/env python3
"""
Verification script for Filesystem Task 6: Simple File Organization
"""

import os
import sys
from pathlib import Path

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

def verify_organization(test_dir: Path) -> bool:
    """Verify the file organization was done correctly."""
    all_passed = True
    
    # Check that sorted directory exists
    sorted_dir = test_dir / "sorted"
    if not sorted_dir.exists() or not sorted_dir.is_dir():
        print("❌ Directory 'sorted' not found")
        return False
    print("✅ Directory 'sorted' exists")
    
    # Check no .txt files in root
    root_txt_files = list(test_dir.glob("*.txt"))
    if root_txt_files:
        print(f"❌ Found {len(root_txt_files)} .txt files still in root directory:")
        for f in root_txt_files:
            print(f"   - {f.name}")
        all_passed = False
    else:
        print("✅ No .txt files remain in root directory")
    
    # Check .txt files in sorted directory
    sorted_txt_files = list(sorted_dir.glob("*.txt"))
    if len(sorted_txt_files) < 2:  # Should have at least moved files + count.txt
        print(f"❌ Only {len(sorted_txt_files)} files in sorted directory (expected at least 2)")
        all_passed = False
    else:
        print(f"✅ Found {len(sorted_txt_files)} files in sorted directory")
    
    # Check count.txt exists and has correct content
    count_file = sorted_dir / "count.txt"
    if not count_file.exists():
        print("❌ File 'sorted/count.txt' not found")
        all_passed = False
    else:
        print("✅ File 'sorted/count.txt' exists")
        
        # Read and verify content
        try:
            content = count_file.read_text().strip()
            # Extract number from "Moved X files"
            if "Moved" in content and "file" in content:
                print(f"✅ Count file contains: '{content}'")
                
                # Try to extract the number
                parts = content.split()
                for i, part in enumerate(parts):
                    if part.isdigit() and i > 0 and parts[i-1].lower() == "moved":
                        count = int(part)
                        # Expected count is total files minus count.txt itself
                        expected = len(sorted_txt_files) - 1
                        if count == expected:
                            print(f"✅ Count is correct: {count} files moved")
                        else:
                            print(f"⚠️  Count mismatch: says {count} but found {expected} moved files")
                        break
            else:
                print(f"❌ Count file has unexpected format: '{content}'")
                all_passed = False
        except Exception as e:
            print(f"❌ Error reading count file: {e}")
            all_passed = False
    
    return all_passed

def main():
    """Main verification function."""
    print("🔍 Verifying Filesystem Task 6: Simple File Organization")
    print("=" * 50)
    
    # Get test directory
    test_dir = get_test_directory()
    print(f"📁 Test directory: {test_dir}\n")
    
    # Verify organization
    if not verify_organization(test_dir):
        print("\n❌ Task 6 verification: FAIL")
        print("File organization incomplete or incorrect")
        sys.exit(1)
    
    print("\n🎉 Task 6 verification: PASS")
    print("Files successfully organized")
    sys.exit(0)

if __name__ == "__main__":
    main()