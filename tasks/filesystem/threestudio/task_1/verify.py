#!/usr/bin/env python3
"""
Verification script for ThreeStudio Task 1: Find Zero123 Guidance Implementation
"""

import sys
from pathlib import Path
import re

def get_test_directory() -> Path:
    """Get the test directory using environment variable or fallback to relative path."""
    import os
    # First try to use environment variable (which points to backup directory)
    test_dir = os.getenv("FILESYSTEM_TEST_DIR")
    print("test_dir: ", test_dir)
    if test_dir:
        return Path(test_dir)
    
    # Fallback to relative path for backward compatibility
    script_dir = Path(__file__).parent
    print("script_dir: ", script_dir.parent.parent.parent.parent / "test_environments/threestudio")
    return script_dir.parent.parent.parent.parent / "test_environments/threestudio"

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
        
        # Check if it contains only the file path (no additional text)
        if len(content.split('\n')) > 1:
            print("❌ Answer file contains multiple lines or additional text")
            return False
        
        # Check if it uses forward slashes
        if '\\' in content:
            print("❌ Answer uses backslashes instead of forward slashes")
            return False
        
        # Check if it's a relative path
        if content.startswith('/') or ':' in content:
            print("❌ Answer appears to be an absolute path")
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
        
        # Expected path components for Zero123 guidance
        # In backup directories, the path is threestudio/models/guidance/zero123_guidance.py
        # In test_environments, the path is threestudio/threestudio/models/guidance/zero123_guidance.py
        expected_components = ["threestudio", "models", "guidance", "zero123_guidance.py"]
        
        # Check if all expected components are in the path
        for component in expected_components:
            if component not in content:
                print(f"❌ Path missing expected component: {component}")
                return False
        
        print("✅ File path structure is correct")
        return True
        
    except Exception as e:
        print(f"❌ Error verifying file path structure: {e}")
        return False

def verify_file_exists(test_dir: Path) -> bool:
    """Verify that the identified file actually exists."""
    answer_file = test_dir / "answer.txt"
    
    try:
        content = answer_file.read_text().strip()
        
        # Try the path as provided in the answer file
        file_path = test_dir / content
        
        # If that doesn't exist, try with the correct path structure
        # The answer file might have threestudio/models/guidance/zero123_guidance.py
        # but the actual path is threestudio/threestudio/models/guidance/zero123_guidance.py
        if not file_path.exists():
            # Try to fix the path by adding the missing threestudio prefix
            if content.startswith("threestudio/models/"):
                corrected_path = content.replace("threestudio/models/", "threestudio/threestudio/models/")
                file_path = test_dir / corrected_path
                if file_path.exists():
                    print(f"✅ File exists with corrected path: {corrected_path}")
                    return True
        
        if not file_path.exists():
            print(f"❌ Identified file does not exist: {content}")
            return False
        
        print("✅ Identified file exists")
        return True
        
    except Exception as e:
        print(f"❌ Error verifying file existence: {e}")
        return False

def verify_zero123_guidance_content(test_dir: Path) -> bool:
    """Verify that the identified file actually contains Zero123 guidance implementation."""
    answer_file = test_dir / "answer.txt"
    
    try:
        content = answer_file.read_text().strip()
        
        # Try the path as provided in the answer file
        file_path = test_dir / content
        
        # If that doesn't exist, try with the correct path structure
        if not file_path.exists():
            # Try to fix the path by adding the missing threestudio prefix
            if content.startswith("threestudio/models/"):
                corrected_path = content.replace("threestudio/models/", "threestudio/threestudio/models/")
                file_path = test_dir / corrected_path
        
        if not file_path.exists():
            print(f"❌ Cannot find file for content verification: {content}")
            return False
        
        file_content = file_path.read_text()
        
        # Check for the main Zero123 guidance implementation
        # The main implementation should have the class name "Zero123Guidance" and register as "zero123-guidance"
        main_zero123_indicators = [
            r'class Zero123Guidance',  # Main class name
            r'@threestudio\.register\("zero123-guidance"\)',  # Correct registration
            r'BaseObject',  # Base class
            r'zero123',  # General zero123 reference
        ]
        
        found_indicators = []
        for indicator in main_zero123_indicators:
            if re.search(indicator, file_content, re.IGNORECASE):
                found_indicators.append(indicator)
        
        # Check if this is the main Zero123 guidance implementation
        is_main_implementation = (
            'class Zero123Guidance' in file_content and 
            '@threestudio.register("zero123-guidance")' in file_content
        )
        
        if not is_main_implementation:
            print(f"❌ File is not the main Zero123 guidance implementation")
            print(f"   Expected: class Zero123Guidance and @threestudio.register('zero123-guidance')")
            return False
        
        print(f"✅ File contains main Zero123 guidance implementation indicators: {found_indicators}")
        return True
        
    except Exception as e:
        print(f"❌ Error verifying file content: {e}")
        return False

def main():
    """Main verification function."""
    test_dir = get_test_directory()
    print("🔍 Verifying ThreeStudio Task 1: Find Zero123 Guidance Implementation...")
    
    # Define verification steps
    verification_steps = [
        ("Answer File Exists", verify_answer_file_exists),
        ("Answer Format", verify_answer_format),
        ("File Path Structure", verify_file_path_structure),
        ("File Exists", verify_file_exists),
        ("Zero123 Guidance Content", verify_zero123_guidance_content),
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
        print("✅ Zero123 guidance file path identified correctly!")
        print("🎉 Task 1 verification: PASS")
        sys.exit(0)
    else:
        print("❌ Task 1 verification: FAIL")
        sys.exit(1)

if __name__ == "__main__":
    main()