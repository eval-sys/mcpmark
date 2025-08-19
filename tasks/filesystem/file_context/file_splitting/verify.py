#!/usr/bin/env python3
"""
Verification script for File Splitting Task
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

def verify_split_directory_exists(test_dir: Path) -> bool:
    """Verify that the split directory exists."""
    split_dir = test_dir / "split"
    
    if not split_dir.exists():
        print("❌ Directory 'split' not found")
        return False
    
    if not split_dir.is_dir():
        print("❌ 'split' exists but is not a directory")
        return False
    
    print("✅ Split directory found")
    return True

def verify_all_split_files_exist(test_dir: Path) -> bool:
    """Verify that all 10 split files exist with correct names."""
    split_dir = test_dir / "split"
    
    expected_files = [f"split_{i:02d}.txt" for i in range(1, 11)]
    missing_files = []
    
    for filename in expected_files:
        file_path = split_dir / filename
        if not file_path.exists():
            missing_files.append(filename)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    
    print("✅ All 10 split files exist with correct names")
    return True

def verify_equal_file_lengths(test_dir: Path) -> bool:
    """Verify that all split files have equal character counts."""
    split_dir = test_dir / "split"
    
    file_lengths = []
    for i in range(1, 11):
        filename = f"split_{i:02d}.txt"
        file_path = split_dir / filename
        
        try:
            content = file_path.read_text()
            file_lengths.append(len(content))
        except Exception as e:
            print(f"❌ Error reading {filename}: {e}")
            return False
    
    # Check if all lengths are equal
    if len(set(file_lengths)) != 1:
        print(f"❌ File lengths are not equal: {file_lengths}")
        return False
    
    print(f"✅ All files have equal length: {file_lengths[0]} characters")
    return True

def verify_content_integrity(test_dir: Path) -> bool:
    """Verify that concatenated split files equal the original file."""
    split_dir = test_dir / "split"
    original_file = test_dir / "large_file.txt"
    
    # Read original content
    try:
        original_content = original_file.read_text()
    except Exception as e:
        print(f"❌ Error reading original file: {e}")
        return False
    
    # Concatenate all split files
    concatenated_content = ""
    for i in range(1, 11):
        filename = f"split_{i:02d}.txt"
        file_path = split_dir / filename
        
        try:
            content = file_path.read_text()
            concatenated_content += content
        except Exception as e:
            print(f"❌ Error reading {filename}: {e}")
            return False
    
    # Compare content
    if concatenated_content != original_content:
        print("❌ Concatenated content does not match original file")
        print(f"   Original length: {len(original_content)}")
        print(f"   Concatenated length: {len(concatenated_content)}")
        return False
    
    print("✅ Concatenated content matches original file exactly")
    return True

def verify_no_extra_files(test_dir: Path) -> bool:
    """Verify that no extra files exist in the split directory."""
    split_dir = test_dir / "split"
    
    expected_files = {f"split_{i:02d}.txt" for i in range(1, 11)}
    actual_files = {f.name for f in split_dir.iterdir() if f.is_file()}
    
    extra_files = actual_files - expected_files
    if extra_files:
        print(f"❌ Extra files found in split directory: {extra_files}")
        return False
    
    print("✅ No extra files in split directory")
    return True

def main():
    """Main verification function."""
    test_dir = get_test_directory()
    print("🔍 Verifying File Splitting Task...")
    
    # Define verification steps
    verification_steps = [
        ("Split Directory Exists", verify_split_directory_exists),
        ("All Split Files Exist", verify_all_split_files_exist),
        ("Equal File Lengths", verify_equal_file_lengths),
        ("Content Integrity", verify_content_integrity),
        ("No Extra Files", verify_no_extra_files),
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
        print("✅ File splitting task completed correctly!")
        print("🎉 Task verification: PASS")
        sys.exit(0)
    else:
        print("❌ Task verification: FAIL")
        sys.exit(1)

if __name__ == "__main__":
    main()