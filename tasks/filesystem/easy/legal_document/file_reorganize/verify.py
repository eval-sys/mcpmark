#!/usr/bin/env python3
"""
Verification script for Legal Document File Reorganization Task
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

def verify_final_version_folder_exists(test_dir: Path) -> bool:
    """Verify that the final_version folder exists in legal_files."""
    final_version_dir = test_dir / "legal_files" / "final_version"
    
    if not final_version_dir.exists():
        print("❌ Folder 'legal_files/final_version' not found")
        return False
    
    if not final_version_dir.is_dir():
        print("❌ 'legal_files/final_version' exists but is not a directory")
        return False
    
    print("✅ Folder 'legal_files/final_version' found")
    return True

def verify_target_file_exists(test_dir: Path) -> bool:
    """Verify that Preferred_Stock_Purchase_Agreement_v10.txt exists in final_version folder."""
    target_file = test_dir / "legal_files" / "final_version" / "Preferred_Stock_Purchase_Agreement_v10.txt"
    
    if not target_file.exists():
        print("❌ File 'legal_files/final_version/Preferred_Stock_Purchase_Agreement_v10.txt' not found")
        return False
    
    if not target_file.is_file():
        print("❌ 'Preferred_Stock_Purchase_Agreement_v10.txt' exists but is not a file")
        return False
    
    print("✅ Target file 'Preferred_Stock_Purchase_Agreement_v10.txt' found in final_version folder")
    return True

def verify_original_file_preserved(test_dir: Path) -> bool:
    """Verify that the original v10 file is still in place."""
    original_file = test_dir / "legal_files" / "Preferred_Stock_Purchase_Agreement_v10.txt"
    
    if not original_file.exists():
        print("❌ Original file 'Preferred_Stock_Purchase_Agreement_v10.txt' was removed")
        return False
    
    print("✅ Original file 'Preferred_Stock_Purchase_Agreement_v10.txt' preserved")
    return True

def verify_only_v10_in_final_version(test_dir: Path) -> bool:
    """Verify that final_version folder contains only v10 file."""
    final_version_dir = test_dir / "legal_files" / "final_version"
    
    # Get all files in final_version folder
    files = list(final_version_dir.iterdir())
    
    # Filter out directories, keep only files
    files_only = [f for f in files if f.is_file()]
    
    if len(files_only) != 1:
        print(f"❌ final_version folder should contain exactly 1 file, but found {len(files_only)}")
        for f in files_only:
            print(f"   - {f.name}")
        return False
    
    # Check if the only file is v10
    if files_only[0].name != "Preferred_Stock_Purchase_Agreement_v10.txt":
        print(f"❌ final_version folder contains wrong file: {files_only[0].name}")
        print("   Expected: Preferred_Stock_Purchase_Agreement_v10.txt")
        return False
    
    print("✅ final_version folder contains only Preferred_Stock_Purchase_Agreement_v10.txt")
    return True

def main():
    """Main verification function."""
    test_dir = get_test_directory()
    print("🔍 Verifying Legal Document File Reorganization Task...")
    
    # Define verification steps
    verification_steps = [
        ("Final Version Folder Exists", verify_final_version_folder_exists),
        ("Target File Exists", verify_target_file_exists),
        ("Only V10 in Final Version", verify_only_v10_in_final_version),
        ("Original File Preserved", verify_original_file_preserved),
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
        print("✅ Legal document file reorganization completed correctly!")
        print("🎉 Task verification: PASS")
        sys.exit(0)
    else:
        print("❌ Task verification: FAIL")
        sys.exit(1)

if __name__ == "__main__":
    main()
