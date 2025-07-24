#!/usr/bin/env python3
"""
Verification script for Filesystem Task 4: File Metadata Collection
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

def verify_metadata_collection(test_dir: Path) -> bool:
    """Verify the metadata collection task."""
    all_passed = True
    
    # Check report file exists
    report_file = test_dir / "file_report.txt"
    if not report_file.exists():
        print("❌ File 'file_report.txt' not found")
        return False
    
    print("✅ File 'file_report.txt' exists")
    
    # Read report content
    try:
        content = report_file.read_text()
        print("\n📄 Report content:")
        print(content)
        
        # Check if report mentions files and directories
        has_file_info = "file" in content.lower()
        has_dir_info = "director" in content.lower()
        
        if has_file_info:
            print("✅ Report mentions files")
        else:
            print("❌ Report doesn't mention files")
            all_passed = False
            
        if has_dir_info:
            print("✅ Report mentions directories")
        else:
            print("⚠️  Report doesn't mention directories (may be okay if none exist)")
        
        # Check for count/summary
        has_numbers = any(char.isdigit() for char in content)
        if has_numbers:
            print("✅ Report contains numbers (likely counts)")
        else:
            print("❌ Report doesn't contain any numbers")
            all_passed = False
            
        # Check minimum content length
        if len(content.strip()) < 20:
            print("❌ Report seems too short")
            all_passed = False
        else:
            print("✅ Report has reasonable length")
            
    except Exception as e:
        print(f"❌ Error reading report file: {e}")
        return False
    
    return all_passed

def main():
    """Main verification function."""
    print("🔍 Verifying Filesystem Task 4: File Metadata Collection")
    print("=" * 50)
    
    test_dir = get_test_directory()
    print(f"📁 Test directory: {test_dir}\n")
    
    if not verify_metadata_collection(test_dir):
        print("\n❌ Task 4 verification: FAIL")
        sys.exit(1)
    
    print("\n🎉 Task 4 verification: PASS")
    print("Metadata collection completed successfully")
    sys.exit(0)

if __name__ == "__main__":
    main()