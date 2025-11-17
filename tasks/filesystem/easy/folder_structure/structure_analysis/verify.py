#!/usr/bin/env python3
"""
Verification script for Directory Structure Analysis Task
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

def verify_structure_analysis_file_exists(test_dir: Path) -> bool:
    """Verify that the structure_analysis.txt file exists."""
    analysis_file = test_dir / "structure_analysis.txt"
    
    if not analysis_file.exists():
        print("❌ File 'structure_analysis.txt' not found")
        return False
    
    print("✅ structure_analysis.txt file found")
    return True

def verify_structure_analysis_content(test_dir: Path) -> bool:
    """Verify that the structure_analysis.txt file contains the correct count."""
    analysis_file = test_dir / "structure_analysis.txt"
    
    try:
        content = analysis_file.read_text().strip()
        
        if not content:
            print("❌ structure_analysis.txt file is empty")
            return False
        
        # The expected answer is 1
        expected_count = 1
        
        # Check if content is exactly "1"
        if content != str(expected_count):
            print(f"❌ Expected '{expected_count}', but found: '{content}'")
            return False
        
        print(f"✅ Python file count is correct: {content}")
        return True
        
    except Exception as e:
        print(f"❌ Error reading structure_analysis.txt file: {e}")
        return False

def main():
    """Main verification function."""
    try:
        test_dir = get_test_directory()
        print(f"🔍 Verifying Directory Structure Analysis Task in: {test_dir}")
        print()
        
        # Define verification steps
        verification_steps = [
            ("Structure Analysis File Exists", verify_structure_analysis_file_exists),
            ("Python File Count is Correct", verify_structure_analysis_content),
        ]
        
        # Run all verification steps
        all_passed = True
        for step_name, verify_func in verification_steps:
            print(f"📋 {step_name}...")
            if not verify_func(test_dir):
                all_passed = False
            print()
        
        # Final result
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
