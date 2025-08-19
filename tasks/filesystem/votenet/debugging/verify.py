#!/usr/bin/env python3
"""
Verification script for VoteNet Task: Debug Backbone Module
"""

import sys
from pathlib import Path
import re
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
        
        # Check if content is not empty
        if not content:
            print("❌ Answer file is empty")
            return False
        
        # Check if it contains only one line (no additional text)
        if len(content.split('\n')) > 1:
            print("❌ Answer file contains multiple lines or additional text")
            return False
        
        # Check if path contains the expected components
        if 'models/backbone_module.py' not in content:
            print("❌ Answer should contain 'models/backbone_module.py'")
            return False
        
        print("✅ Answer format is correct")
        return True
        
    except Exception as e:
        print(f"❌ Error reading answer file: {e}")
        return False

def verify_file_path_structure(test_dir: Path) -> bool:
    """Verify that the file path has the expected structure."""
    answer_file = test_dir / "answer.txt"
    
    try:
        content = answer_file.read_text().strip()
        
        # Expected path components for backbone module
        expected_components = ["models", "backbone_module.py"]
        
        # Check if all expected components are in the content
        for component in expected_components:
            if component not in content:
                print(f"❌ Answer missing expected component: {component}")
                return False
        
        print("✅ Answer contains expected components")
        return True
        
    except Exception as e:
        print(f"❌ Error verifying answer structure: {e}")
        return False

def verify_file_exists(test_dir: Path) -> bool:
    """Verify that the identified file actually exists."""
    answer_file = test_dir / "answer.txt"
    
    try:
        content = answer_file.read_text().strip()
        
        # Try the expected path
        file_path = test_dir / "models/backbone_module.py"
        
        if not file_path.exists():
            print(f"❌ Expected file does not exist: models/backbone_module.py")
            return False
        
        print("✅ Expected file exists")
        return True
        
    except Exception as e:
        print(f"❌ Error verifying file existence: {e}")
        return False

def verify_bug_fix(test_dir: Path) -> bool:
    """Verify that the bug has been fixed in the code."""
    answer_file = test_dir / "answer.txt"
    
    try:
        content = answer_file.read_text().strip()
        
        file_path = test_dir / "models/backbone_module.py"
        
        if not file_path.exists():
            print(f"❌ Cannot find file for bug fix verification: models/backbone_module.py")
            return False
        
        # Read the file and search for the specific line containing self.fp2 = PointnetFPModule
        file_content = file_path.read_text()
        lines = file_content.split('\n')
        
        # Find the line containing self.fp2 = PointnetFPModule
        target_line = None
        target_line_number = None
        
        for i, line in enumerate(lines):
            if "self.fp2 = PointnetFPModule" in line:
                target_line = line.strip()
                target_line_number = i + 1  # Convert to 1-based line number
                break
        
        if target_line is None:
            print("❌ Could not find line containing 'self.fp2 = PointnetFPModule'")
            return False
        
        # Check if the original buggy line still exists
        original_bug = "self.fp2 = PointnetFPModule(mlp=[256,256,256])"
        if original_bug in target_line:
            print(f"❌ Bug has not been fixed - original line still exists at line {target_line_number}")
            print(f"   Line {target_line_number} content: {target_line}")
            return False
        
        # Check for the correct fix
        correct_fixes = [
            "self.fp2 = PointnetFPModule(mlp=[256+256,256,256])",
            "self.fp2 = PointnetFPModule(mlp=[512,256,256])"
        ]
        
        fix_found = False
        for fix in correct_fixes:
            if fix in target_line:
                fix_found = True
                break
        
        if not fix_found:
            print(f"❌ Bug fix not found at line {target_line_number}")
            print(f"   Line {target_line_number} content: {target_line}")
            print("   Expected one of:")
            for fix in correct_fixes:
                print(f"   - {fix}")
            return False
        
        print(f"✅ Bug has been fixed correctly at line {target_line_number}")
        return True
        
    except Exception as e:
        print(f"❌ Error verifying bug fix: {e}")
        return False



def main():
    """Main verification function."""
    test_dir = get_test_directory()
    print("🔍 Verifying VoteNet Task: Debug Backbone Module...")
    
    # Define verification steps
    verification_steps = [
        ("Answer File Exists", verify_answer_file_exists),
        ("Answer Format", verify_answer_format),
        ("Answer Structure", verify_file_path_structure),
        ("File Exists", verify_file_exists),
        ("Bug Fix Applied", verify_bug_fix),
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
        print("✅ VoteNet backbone module bug has been correctly identified and fixed!")
        print("🎉 Task verification: PASS")
        sys.exit(0)
    else:
        print("❌ Task verification: FAIL")
        sys.exit(1)

if __name__ == "__main__":
    main()