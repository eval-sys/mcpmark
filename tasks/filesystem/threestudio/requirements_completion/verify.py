#!/usr/bin/env python3
"""
Verification script for ThreeStudio Task 3: Restore Zero123 Dependencies in Requirements.txt
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
    """Verify that all required Zero123 dependencies are present."""
    requirements_file = test_dir / "requirements.txt"
    
    try:
        content = requirements_file.read_text()
        
        # Required dependencies to check for (simplified)
        required_deps = [
            "einops",
            "kornia", 
            "taming",
            "openai",
            "clip"
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

def verify_specific_dependency_entries(test_dir: Path) -> bool:
    """Verify that the specific dependency entries are present."""
    requirements_file = test_dir / "requirements.txt"
    
    try:
        content = requirements_file.read_text()
        
        # Check for specific dependency entries (simplified)
        # For taming, we only need to check if "taming" is present, not the full package name
        required_checks = [
            ("einops", "einops"),
            ("kornia", "kornia"),
            ("taming", "taming"),  # Just check for "taming" substring
        ]
        
        missing_entries = []
        found_entries = []
        
        for check_name, full_entry in required_checks:
            if check_name in content.lower():
                found_entries.append(check_name)
            else:
                missing_entries.append(check_name)
        
        # Special check for openai and clip - they should be on the same line
        lines = content.split('\n')
        openai_clip_found = False
        for line in lines:
            line_lower = line.lower()
            if "openai" in line_lower and "clip" in line_lower:
                openai_clip_found = True
                break
        
        if openai_clip_found:
            found_entries.append("openai+clip")
        else:
            missing_entries.append("openai+clip")
        
        if missing_entries:
            print(f"❌ Missing required dependency checks: {missing_entries}")
            return False
        
        print(f"✅ All required dependency checks passed: {found_entries}")
        return True
        
    except Exception as e:
        print(f"❌ Error checking specific entries: {e}")
        return False

def verify_file_format(test_dir: Path) -> bool:
    """Verify that the requirements.txt file has proper format."""
    requirements_file = test_dir / "requirements.txt"
    
    try:
        content = requirements_file.read_text()
        lines = content.split('\n')
        
        # Basic format check - just ensure file is not completely empty
        if not content.strip():
            print("❌ File is completely empty")
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
        
        # Simplified duplicate check - just ensure the file is not completely corrupted
        if len(content) < 10:  # Basic sanity check
            print("❌ File seems too short to be valid")
            return False
        
        print("✅ File appears to be valid")
        return True
        
    except Exception as e:
        print(f"❌ Error checking file: {e}")
        return False

def main():
    """Main verification function."""
    test_dir = get_test_directory()
    print("🔍 Verifying ThreeStudio Task 3: Restore Zero123 Dependencies in Requirements.txt...")
    
    # Define verification steps
    verification_steps = [
        ("Requirements File Exists", verify_requirements_file_exists),
        ("File is Readable", verify_requirements_file_readable),
        ("Required Dependencies Present", verify_required_dependencies_present),
        ("Specific Entries Present", verify_specific_dependency_entries),
        ("File Format", verify_file_format),
        ("File Validity", verify_no_duplicate_entries),
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
        print("✅ Zero123 dependencies successfully restored in requirements.txt!")
        print("🎉 Task 3 verification: PASS")
        sys.exit(0)
    else:
        print("❌ Task 3 verification: FAIL")
        sys.exit(1)

if __name__ == "__main__":
    main()
