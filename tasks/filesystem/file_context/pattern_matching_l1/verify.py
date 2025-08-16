#!/usr/bin/env python3
"""
Verification script for File Filtering Task: Find Files with Common Substring
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
    """Verify that the answer.txt file exists."""
    answer_file = test_dir / "answer.txt"
    
    if not answer_file.exists():
        print("❌ File 'answer.txt' not found")
        return False
    
    print("✅ Answer file found")
    return True

def verify_answer_format(test_dir: Path) -> bool:
    """Verify that the answer file has the correct format."""
    answer_file = test_dir / "answer.txt"
    
    try:
        content = answer_file.read_text().strip()
        
        # If file is empty, that's acceptable (no matches found)
        if not content:
            print("✅ Answer file is empty (no matches found)")
            return True
        
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
                
            # Check format: just filename.txt
            if not line.endswith('.txt') or not line.startswith('file_'):
                print(f"❌ Line {i} has incorrect format: {line}")
                print("   Expected format: filename.txt")
                return False
        
        print("✅ Answer format is correct")
        return True
        
    except Exception as e:
        print(f"❌ Error reading answer file: {e}")
        return False

def find_30_plus_char_matches(test_dir: Path) -> set:
    """Find all files that have 30+ character substring matches with large_file.txt."""
    large_file = test_dir / "large_file.txt"
    if not large_file.exists():
        print("❌ large_file.txt not found")
        return set()
    
    large_content = large_file.read_text()
    matching_files = set()
    
    # Check each file from file_01.txt to file_20.txt
    for i in range(1, 21):
        filename = f"file_{i:02d}.txt"
        file_path = test_dir / filename
        
        if not file_path.exists():
            continue
            
        file_content = file_path.read_text()
        
        # Check if there's a substring of 30+ characters that matches
        has_match = False
        for start_pos in range(len(file_content)):
            for end_pos in range(start_pos + 30, len(file_content) + 1):
                substring = file_content[start_pos:end_pos]
                if substring in large_content:
                    has_match = True
                    break
            if has_match:
                break
        
        if has_match:
            matching_files.add(filename)
    
    return matching_files

def verify_matches_are_correct(test_dir: Path) -> bool:
    """Verify that the files listed in answer.txt actually have 30+ character matches."""
    answer_file = test_dir / "answer.txt"
    
    try:
        content = answer_file.read_text().strip()
        
        # If no content, check if there should actually be no matches
        if not content:
            expected_matches = find_30_plus_char_matches(test_dir)
            if expected_matches:
                print("❌ Answer file is empty but matches should exist")
                for filename in expected_matches:
                    print(f"   Expected: {filename}")
                return False
            else:
                print("✅ No matches found (correct)")
                return True
        
        # Parse answer file
        answer_files = set()
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            answer_files.add(line)
        
        # Get expected matches
        expected_matches = find_30_plus_char_matches(test_dir)
        
        # Check if all answer files actually have matches
        for filename in answer_files:
            if filename not in expected_matches:
                print(f"❌ File {filename} listed in answer but has no valid 30+ character match")
                return False
        
        # Check if all expected matches are in answer
        for filename in expected_matches:
            if filename not in answer_files:
                print(f"❌ Missing match for {filename} in answer file")
                return False
        
        print("✅ All matches are correct")
        return True
        
    except Exception as e:
        print(f"❌ Error verifying matches: {e}")
        return False

def verify_files_exist(test_dir: Path) -> bool:
    """Verify that all files mentioned in answer.txt actually exist."""
    answer_file = test_dir / "answer.txt"
    
    try:
        content = answer_file.read_text().strip()
        
        if not content:
            return True  # No files to verify
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            file_path = test_dir / line
            
            if not file_path.exists():
                print(f"❌ File mentioned in answer does not exist: {line}")
                return False
        
        print("✅ All files mentioned in answer exist")
        return True
        
    except Exception as e:
        print(f"❌ Error verifying file existence: {e}")
        return False

def main():
    """Main verification function."""
    test_dir = get_test_directory()
    #test_dir = Path("/Users/chenlingjun/Desktop/MCP/MCPBench/.mcpbench_backups/backup_filesystem_file_context_pattern_matching_sv_31079")
    print("🔍 Verifying File Filtering Task: Find Files with Common Substring...")
    
    # Define verification steps
    verification_steps = [
        ("Answer File Exists", verify_answer_file_exists),
        ("Answer Format", verify_answer_format),
        ("Files Exist", verify_files_exist),
        ("Matches are Correct", verify_matches_are_correct),
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
        print("✅ File filtering task completed correctly!")
        print("🎉 Task verification: PASS")
        sys.exit(0)
    else:
        print("❌ Task verification: FAIL")
        sys.exit(1)

if __name__ == "__main__":
    main()