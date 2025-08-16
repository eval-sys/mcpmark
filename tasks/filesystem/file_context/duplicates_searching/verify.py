#!/usr/bin/env python3
"""
Verification script for File Duplicates Detection and Organization Task
"""

import sys
from pathlib import Path
import os
import hashlib

def get_test_directory() -> Path:
    """Get the test directory from FILESYSTEM_TEST_DIR env var."""
    test_root = os.environ.get("FILESYSTEM_TEST_DIR")
    if not test_root:
        raise ValueError("FILESYSTEM_TEST_DIR environment variable is required")
    return Path(test_root)

def calculate_file_hash(file_path: Path) -> str:
    """Calculate MD5 hash of file content."""
    try:
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception as e:
        print(f"❌ Error reading file {file_path}: {e}")
        return None

def verify_duplicates_directory_exists(test_dir: Path) -> bool:
    """Verify that the duplicates directory exists."""
    duplicates_dir = test_dir / "duplicates"
    
    if not duplicates_dir.exists():
        print("❌ 'duplicates' directory not found")
        return False
    
    if not duplicates_dir.is_dir():
        print("❌ 'duplicates' exists but is not a directory")
        return False
    
    print("✅ 'duplicates' directory exists")
    return True

def get_expected_duplicate_groups():
    """Return the expected duplicate file groups based on content analysis."""
    # Based on the answer.md and content analysis
    return {
        # Group 1: file_01.txt, file_02.txt (identical content)
        "group1": ["file_01.txt", "file_02.txt"],
        # Group 2: file_03.txt, file_04.txt (identical content)
        "group2": ["file_03.txt", "file_04.txt"],
        # Group 3: file_07.txt, file_08.txt (identical content)
        "group3": ["file_07.txt", "file_08.txt"],
        # Group 4: file_10.txt, file_11.txt (identical content)
        "group4": ["file_10.txt", "file_11.txt"],
        # Group 5: file_13.txt, file_14.txt (identical content)
        "group5": ["file_13.txt", "file_14.txt"],
        # Group 6: file_15.txt, file_16.txt (identical content)
        "group6": ["file_15.txt", "file_16.txt"],
        # Group 7: file_18.txt, file_19.txt (identical content)
        "group7": ["file_18.txt", "file_19.txt"]
    }

def get_expected_unique_files():
    """Return the expected unique files that should remain in original location."""
    return [
        "file_05.txt", "file_06.txt", "file_09.txt", 
        "file_12.txt", "file_17.txt", "file_20.txt"
    ]

def verify_duplicate_files_moved(test_dir: Path) -> bool:
    """Verify that all duplicate files have been moved to the duplicates directory."""
    duplicates_dir = test_dir / "duplicates"
    expected_duplicate_groups = get_expected_duplicate_groups()
    
    # Check that all expected duplicate files are in the duplicates directory
    missing_files = []
    for group_name, files in expected_duplicate_groups.items():
        for filename in files:
            file_path = duplicates_dir / filename
            if not file_path.exists():
                missing_files.append(filename)
    
    if missing_files:
        print(f"❌ Missing duplicate files in 'duplicates' directory: {missing_files}")
        return False
    
    print("✅ All expected duplicate files are in the 'duplicates' directory")
    return True

def verify_unique_files_remain(test_dir: Path) -> bool:
    """Verify that unique files remain in the original location."""
    expected_unique_files = get_expected_unique_files()
    
    missing_files = []
    for filename in expected_unique_files:
        file_path = test_dir / filename
        if not file_path.exists():
            missing_files.append(filename)
    
    if missing_files:
        print(f"❌ Missing unique files in original location: {missing_files}")
        return False
    
    print("✅ All expected unique files remain in the original location")
    return True

def verify_no_duplicate_files_in_original(test_dir: Path) -> bool:
    """Verify that no duplicate files remain in the original location."""
    expected_duplicate_groups = get_expected_duplicate_groups()
    
    remaining_duplicates = []
    for group_name, files in expected_duplicate_groups.items():
        for filename in files:
            file_path = test_dir / filename
            if file_path.exists():
                remaining_duplicates.append(filename)
    
    if remaining_duplicates:
        print(f"❌ Duplicate files still exist in original location: {remaining_duplicates}")
        return False
    
    print("✅ No duplicate files remain in the original location")
    return True

def verify_content_integrity(test_dir: Path) -> bool:
    """Verify that file content integrity is maintained after moving."""
    duplicates_dir = test_dir / "duplicates"
    expected_duplicate_groups = get_expected_duplicate_groups()
    
    # Check that files in each duplicate group have identical content
    for group_name, files in expected_duplicate_groups.items():
        if len(files) < 2:
            continue
            
        # Calculate hash of the first file in the group
        first_file = duplicates_dir / files[0]
        if not first_file.exists():
            print(f"❌ First file of group {group_name} not found: {files[0]}")
            return False
        
        first_hash = calculate_file_hash(first_file)
        if first_hash is None:
            return False
        
        # Check that all other files in the group have the same hash
        for filename in files[1:]:
            file_path = duplicates_dir / filename
            if not file_path.exists():
                print(f"❌ File in group {group_name} not found: {filename}")
                return False
            
            file_hash = calculate_file_hash(file_path)
            if file_hash is None:
                return False
            
            if file_hash != first_hash:
                print(f"❌ Files in group {group_name} have different content: {files[0]} vs {filename}")
                return False
    
    print("✅ Content integrity verified - duplicate files have identical content")
    return True

def verify_total_file_count(test_dir: Path) -> bool:
    """Verify that the duplicates directory contains exactly 14 files."""
    duplicates_dir = test_dir / "duplicates"
    
    # Count files in original location (excluding the duplicates directory itself)
    original_files = [f for f in test_dir.iterdir() if f.is_file()]
    
    # Count files in duplicates directory
    duplicate_files = [f for f in duplicates_dir.iterdir() if f.is_file()]
    
    # Expected: 14 files in duplicates directory
    expected_duplicates = 14
    actual_duplicates = len(duplicate_files)
    
    if actual_duplicates != expected_duplicates:
        print(f"❌ Wrong number of files in duplicates directory. Expected: {expected_duplicates}, Actual: {actual_duplicates}")
        return False
    
    print(f"✅ Duplicates directory has correct number of files: {actual_duplicates}")
    return True



def main():
    """Main verification function."""
    test_dir = get_test_directory()
    # test_dir = Path("/Users/chenlingjun/Desktop/MCP/MCPBench/.mcpbench_backups/backup_filesystem_file_context_duplicates_checking_21630")
    print("🔍 Verifying File Duplicates Detection and Organization Task...")
    
    # Define verification steps
    verification_steps = [
        ("Duplicates Directory Exists", verify_duplicates_directory_exists),
        ("Duplicate Files Moved", verify_duplicate_files_moved),
        ("Unique Files Remain", verify_unique_files_remain),
        ("No Duplicates in Original", verify_no_duplicate_files_in_original),
        ("Content Integrity", verify_content_integrity),
        ("Duplicates Count", verify_total_file_count),
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
        print("✅ File duplicates detection and organization completed correctly!")
        print("🎉 Task verification: PASS")
        sys.exit(0)
    else:
        print("❌ Task verification: FAIL")
        sys.exit(1)

if __name__ == "__main__":
    main()