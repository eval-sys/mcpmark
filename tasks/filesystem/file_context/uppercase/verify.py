#!/usr/bin/env python3
"""
Verification script for File Context Task: Convert Files to Uppercase
"""

import sys
from pathlib import Path
import os
import re

def get_test_directory() -> Path:
    """Get the test directory from FILESYSTEM_TEST_DIR env var."""
    test_root = os.environ.get("FILESYSTEM_TEST_DIR")
    if not test_root:
        raise ValueError("FILESYSTEM_TEST_DIR environment variable is required")
    return Path(test_root)

def verify_uppercase_directory_exists(test_dir: Path) -> bool:
    """Verify that the uppercase directory exists."""
    uppercase_dir = test_dir / "uppercase"
    
    if not uppercase_dir.exists():
        print("❌ Directory 'uppercase' not found")
        return False
    
    if not uppercase_dir.is_dir():
        print("❌ 'uppercase' exists but is not a directory")
        return False
    
    print("✅ Uppercase directory found")
    return True

def verify_uppercase_files_exist(test_dir: Path) -> bool:
    """Verify that all 10 uppercase files exist."""
    uppercase_dir = test_dir / "uppercase"
    
    for i in range(1, 11):
        filename = f"file_{i:02d}.txt"
        file_path = uppercase_dir / filename
        
        if not file_path.exists():
            print(f"❌ File '{filename}' not found in uppercase directory")
            return False
    
    print("✅ All 10 uppercase files found")
    return True

def verify_uppercase_content(test_dir: Path) -> bool:
    """Verify that uppercase files contain the correct uppercase content."""
    uppercase_dir = test_dir / "uppercase"
    
    for i in range(1, 11):
        filename = f"file_{i:02d}.txt"
        original_file = test_dir / filename
        uppercase_file = uppercase_dir / filename
        
        if not original_file.exists():
            print(f"❌ Original file '{filename}' not found")
            return False
        
        try:
            original_content = original_file.read_text()
            uppercase_content = uppercase_file.read_text()
            
            # Check if uppercase content is the uppercase version of original
            expected_uppercase = original_content.upper()
            
            if uppercase_content != expected_uppercase:
                print(f"❌ File '{filename}' content is not properly converted to uppercase")
                return False
                
        except Exception as e:
            print(f"❌ Error reading file '{filename}': {e}")
            return False
    
    print("✅ All uppercase files contain correct uppercase content")
    return True

def verify_answer_file_exists(test_dir: Path) -> bool:
    """Verify that the answer.txt file exists in the uppercase directory."""
    uppercase_dir = test_dir / "uppercase"
    answer_file = uppercase_dir / "answer.txt"
    
    if not answer_file.exists():
        print("❌ File 'answer.txt' not found in uppercase directory")
        return False
    
    print("✅ Answer file found in uppercase directory")
    return True

def verify_answer_format(test_dir: Path) -> bool:
    """Verify that the answer file has the correct format."""
    uppercase_dir = test_dir / "uppercase"
    answer_file = uppercase_dir / "answer.txt"
    
    try:
        content = answer_file.read_text().strip()
        
        if not content:
            print("❌ Answer file is empty")
            return False
        
        lines = content.split('\n')
        
        # Check if we have exactly 10 lines
        if len(lines) != 10:
            print(f"❌ Answer file has {len(lines)} lines, expected 10")
            return False
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                print(f"❌ Line {i} is empty")
                return False
            
            # Check format: filename:word_count
            if ':' not in line:
                print(f"❌ Line {i} has incorrect format: {line}")
                print("   Expected format: filename:word_count")
                return False
            
            parts = line.split(':', 1)
            if len(parts) != 2:
                print(f"❌ Line {i} has incorrect format: {line}")
                print("   Expected format: filename:word_count")
                return False
            
            filename, word_count_str = parts
            
            # Check filename format
            if not filename.endswith('.txt') or not filename.startswith('file_'):
                print(f"❌ Line {i} has invalid filename: {filename}")
                return False
            
            # Check word count format (should be integer)
            try:
                word_count = int(word_count_str)
                if word_count <= 0:
                    print(f"❌ Line {i} has invalid word count: {word_count_str}")
                    return False
            except ValueError:
                print(f"❌ Line {i} has non-integer word count: {word_count_str}")
                return False
        
        print("✅ Answer format is correct")
        return True
        
    except Exception as e:
        print(f"❌ Error reading answer file: {e}")
        return False

def count_words_in_file(file_path: Path) -> int:
    """Count words in a file."""
    try:
        content = file_path.read_text()
        # Split by whitespace and filter out empty strings
        words = [word for word in content.split() if word.strip()]
        return len(words)
    except Exception as e:
        print(f"❌ Error reading file {file_path}: {e}")
        return 0

def verify_word_counts_are_correct(test_dir: Path) -> bool:
    """Verify that the word counts in answer.txt are correct."""
    uppercase_dir = test_dir / "uppercase"
    answer_file = uppercase_dir / "answer.txt"
    
    try:
        content = answer_file.read_text().strip()
        lines = content.split('\n')
        
        # Expected word counts based on answer.md
        expected_counts = [22, 22, 22, 22, 18, 22, 22, 22, 18, 20]
        
        # Create a set of expected file entries for easier checking
        expected_entries = set()
        for i in range(1, 11):
            filename = f"file_{i:02d}.txt"
            expected_count = expected_counts[i - 1]
            if i == 6:  # Special case for file_06.txt: can be 21 or 22
                expected_entries.add(f"{filename}:21")
                expected_entries.add(f"{filename}:22")
            else:
                expected_entries.add(f"{filename}:{expected_count}")
        
        # Check each line in the answer file
        found_entries = set()
        for line in lines:
            line = line.strip()
            if line in expected_entries:
                found_entries.add(line)
            else:
                print(f"❌ Invalid entry: {line}")
                return False
        
        # Check if we found all expected entries
        if len(found_entries) != 10:
            print(f"❌ Found {len(found_entries)} entries, expected 10")
            missing = expected_entries - found_entries
            if missing:
                print(f"   Missing entries: {missing}")
            return False
        
        print("✅ All word counts are correct")
        return True
        
    except Exception as e:
        print(f"❌ Error verifying word counts: {e}")
        return False

def verify_all_files_are_included(test_dir: Path) -> bool:
    """Verify that all 10 files are included in the answer."""
    uppercase_dir = test_dir / "uppercase"
    answer_file = uppercase_dir / "answer.txt"
    
    try:
        content = answer_file.read_text().strip()
        lines = content.split('\n')
        
        # Check that all 10 files are present
        found_files = set()
        for line in lines:
            parts = line.split(':', 1)
            filename = parts[0]
            found_files.add(filename)
        
        expected_files = {f"file_{i:02d}.txt" for i in range(1, 11)}
        
        if found_files != expected_files:
            missing = expected_files - found_files
            extra = found_files - expected_files
            if missing:
                print(f"❌ Missing files in answer: {missing}")
            if extra:
                print(f"❌ Extra files in answer: {extra}")
            return False
        
        print("✅ All 10 files are included in answer")
        return True
        
    except Exception as e:
        print(f"❌ Error verifying file inclusion: {e}")
        return False

def main():
    """Main verification function."""
    try:
        test_dir = get_test_directory()
        print(f"🔍 Verifying Uppercase in: {test_dir}")
        print()
        
        # Run all verification checks
        checks = [
            ("Uppercase directory exists", verify_uppercase_directory_exists),
            ("Uppercase files exist", verify_uppercase_files_exist),
            ("Uppercase content is correct", verify_uppercase_content),
            ("Answer file exists in uppercase directory", verify_answer_file_exists),
            ("Answer format is correct", verify_answer_format),
            ("All files are included", verify_all_files_are_included),
            ("Word counts are correct", verify_word_counts_are_correct),
        ]
        
        all_passed = True
        for check_name, check_func in checks:
            print(f"📋 {check_name}...")
            if not check_func(test_dir):
                all_passed = False
            print()
        
        if all_passed:
            print("🎉 All verification checks passed!")
            sys.exit(0)
        else:
            print("❌ Some verification checks failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Verification failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()