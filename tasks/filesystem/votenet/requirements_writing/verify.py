#!/usr/bin/env python3
"""
Verification script for VoteNet Task: Create Requirements.txt File
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

def verify_requirements_file_exists(test_dir: Path) -> bool:
    """Verify that the requirements.txt file exists."""
    requirements_file = test_dir / "requirements.txt"
    
    if not requirements_file.exists():
        print("❌ File 'requirements.txt' not found")
        return False
    
    print("✅ Requirements.txt file found")
    return True

def verify_requirements_file_readable(test_dir: Path) -> bool:
    """Verify that the requirements.txt file is readable."""
    requirements_file = test_dir / "requirements.txt"
    
    try:
        content = requirements_file.read_text()
        if not content.strip():
            print("❌ Requirements.txt file is empty")
            return False
        
        print("✅ Requirements.txt file is readable")
        return True
        
    except Exception as e:
        print(f"❌ Error reading requirements.txt file: {e}")
        return False

def verify_required_dependencies_present(test_dir: Path) -> bool:
    """Verify that all required dependencies are present."""
    requirements_file = test_dir / "requirements.txt"
    
    try:
        content = requirements_file.read_text()
        
        # Required dependencies from answer.txt
        required_deps = [
            "matplotlib",
            "opencv", 
            "plyfile",
            "trimesh",
            "pointnet2",
            "networkx"
        ]
        
        missing_deps = []
        found_deps = []
        
        for dep in required_deps:
            if dep.lower() in content.lower():
                found_deps.append(dep)
            else:
                missing_deps.append(dep)
        
        if missing_deps:
            print(f"❌ Missing required dependencies: {missing_deps}")
            return False
        
        print(f"✅ All required dependencies found: {found_deps}")
        return True
        
    except Exception as e:
        print(f"❌ Error checking dependencies: {e}")
        return False

def verify_file_format(test_dir: Path) -> bool:
    """Verify that the requirements.txt file has proper format."""
    requirements_file = test_dir / "requirements.txt"
    
    try:
        content = requirements_file.read_text()
        lines = content.split('\n')
        
        # Check if file has content and proper line structure
        if not content.strip():
            print("❌ File is completely empty")
            return False
        
        # Check if there are multiple lines (indicating multiple dependencies)
        non_empty_lines = [line.strip() for line in lines if line.strip()]
        if len(non_empty_lines) < 3:  # Should have at least 3 dependencies
            print("❌ File seems to have too few dependencies")
            return False
        
        print("✅ File format is acceptable")
        return True
        
    except Exception as e:
        print(f"❌ Error checking file format: {e}")
        return False

def verify_no_duplicate_entries(test_dir: Path) -> bool:
    """Verify that there are no duplicate dependency entries."""
    requirements_file = test_dir / "requirements.txt"
    
    try:
        content = requirements_file.read_text()
        lines = [line.strip().lower() for line in content.split('\n') if line.strip()]
        
        # Check for duplicates
        if len(lines) != len(set(lines)):
            print("❌ File contains duplicate entries")
            return False
        
        print("✅ No duplicate entries found")
        return True
        
    except Exception as e:
        print(f"❌ Error checking for duplicates: {e}")
        return False

def main():
    """Main verification function."""
    test_dir = get_test_directory()
    print("🔍 Verifying VoteNet Task: Create Requirements.txt File...")
    
    # Define verification steps
    verification_steps = [
        ("Requirements File Exists", verify_requirements_file_exists),
        ("File is Readable", verify_requirements_file_readable),
        ("Required Dependencies Present", verify_required_dependencies_present),
        ("File Format", verify_file_format),
        ("No Duplicate Entries", verify_no_duplicate_entries),
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
        print("✅ Requirements.txt file successfully created with all required dependencies!")
        print("🎉 Task verification: PASS")
        sys.exit(0)
    else:
        print("❌ Task verification: FAIL")
        sys.exit(1)

if __name__ == "__main__":
    main()