#!/usr/bin/env python3
"""
Verification script for File Merging Task
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

def get_expected_files() -> list:
    """Get the expected 10 files in alphabetical order."""
    # The 10 smallest files (excluding file_12.txt) in alphabetical order
    expected_files = [
        "file_10.txt",
        "file_11.txt", 
        "file_13.txt",
        "file_14.txt",
        "file_15.txt",
        "file_16.txt",
        "file_17.txt",
        "file_18.txt",
        "file_19.txt",
        "file_20.txt"
    ]
    return expected_files

def verify_merged_file_exists(test_dir: Path) -> bool:
    """Verify that the merged_content.txt file exists."""
    merged_file = test_dir / "merged_content.txt"
    
    if not merged_file.exists():
        print("❌ File 'merged_content.txt' not found")
        return False
    
    print("✅ Merged content file found")
    return True



def verify_correct_files_selected(test_dir: Path) -> bool:
    """Verify that the correct 10 files were selected and included."""
    expected_files = get_expected_files()
    merged_file = test_dir / "merged_content.txt"
    
    try:
        content = merged_file.read_text()
        
        # Check if all expected files are present
        for expected_file in expected_files:
            if expected_file not in content:
                print(f"❌ Expected file '{expected_file}' not found in merged content")
                return False
        
        # Check if file_12.txt is NOT present (should be excluded)
        if "file_12.txt" in content:
            print("❌ file_12.txt should be excluded but was found in merged content")
            return False
        
        print("✅ Correct files selected and included")
        return True
        
    except Exception as e:
        print(f"❌ Error verifying file selection: {e}")
        return False

def verify_alphabetical_order(test_dir: Path) -> bool:
    """Verify that files are in alphabetical order."""
    expected_files = get_expected_files()
    merged_file = test_dir / "merged_content.txt"
    
    try:
        content = merged_file.read_text()
        lines = content.split('\n')
        
        # Extract filenames from the content (lines that contain .txt)
        found_files = []
        for line in lines:
            line = line.strip()
            # Check if this line contains any of the expected filenames
            for expected_file in expected_files:
                if expected_file in line:
                    found_files.append(expected_file)
                    break
        
        # Check if files are in alphabetical order
        if found_files != expected_files:
            print(f"❌ Files not in correct alphabetical order")
            print(f"   Expected: {expected_files}")
            print(f"   Found: {found_files}")
            return False
        
        print("✅ Files are in correct alphabetical order")
        return True
        
    except Exception as e:
        print(f"❌ Error verifying alphabetical order: {e}")
        return False

def verify_file_content_integrity(test_dir: Path) -> bool:
    """Verify that the content of each file is preserved correctly."""
    expected_files = get_expected_files()
    merged_file = test_dir / "merged_content.txt"
    
    try:
        content = merged_file.read_text()
        lines = content.split('\n')
        
        for expected_file in expected_files:
            # Get the original file content
            original_file = test_dir / expected_file
            original_content = original_file.read_text().strip()
            
            # Find the line index where this file's header appears
            header_line_index = -1
            for i, line in enumerate(lines):
                if expected_file in line:
                    header_line_index = i
                    break
            
            if header_line_index == -1:
                print(f"❌ Could not find header for {expected_file}")
                return False
            
            # Find the next header line or end of file
            next_header_index = len(lines)
            for i in range(header_line_index + 1, len(lines)):
                for other_file in expected_files:
                    if other_file != expected_file and other_file in lines[i]:
                        next_header_index = i
                        break
                if next_header_index != len(lines):
                    break
            
            # Extract content lines (from header + 1 to next header)
            content_lines = lines[header_line_index + 1:next_header_index]
            merged_content = '\n'.join(content_lines).strip()
            
            if merged_content != original_content:
                print(f"❌ Content mismatch for {expected_file}")
                print(f"   Expected: {original_content}")
                print(f"   Found: {merged_content}")
                return False
        
        print("✅ All file contents preserved correctly")
        return True
        
    except Exception as e:
        print(f"❌ Error verifying content integrity: {e}")
        return False

def verify_filename_headers(test_dir: Path) -> bool:
    """Verify that each file section starts with the correct filename header."""
    expected_files = get_expected_files()
    merged_file = test_dir / "merged_content.txt"
    
    try:
        content = merged_file.read_text()
        
        for expected_file in expected_files:
            # Check if the filename appears anywhere in the content (as part of a line)
            if expected_file not in content:
                print(f"❌ Filename header '{expected_file}' not found")
                return False
        
        print("✅ All filename headers present and correctly formatted")
        return True
        
    except Exception as e:
        print(f"❌ Error verifying filename headers: {e}")
        return False

def main():
    """Main verification function."""
    test_dir = get_test_directory()
    print("🔍 Verifying File Merging Task...")
    
    # Show expected files for debugging
    expected_files = get_expected_files()
    print(f"📋 Expected files (10 smallest, excluding file_12.txt): {expected_files}")
    
    # Define verification steps
    verification_steps = [
        ("Merged File Exists", verify_merged_file_exists),
        ("Correct Files Selected", verify_correct_files_selected),
        ("Alphabetical Order", verify_alphabetical_order),
        ("Filename Headers", verify_filename_headers),
        ("Content Integrity", verify_file_content_integrity),
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
        print("✅ File merging task completed correctly!")
        print("🎉 Task verification: PASS")
        sys.exit(0)
    else:
        print("❌ Task verification: FAIL")
        sys.exit(1)

if __name__ == "__main__":
    main()