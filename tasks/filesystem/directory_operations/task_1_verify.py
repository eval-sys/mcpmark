#!/usr/bin/env python3
"""
Verification script for Filesystem Task 3: Directory Operations
"""

import os
import sys
from pathlib import Path

# =============================================================================
# CONFIGURATION
# =============================================================================

# Expected directory structure
EXPECTED_STRUCTURE = {
    "project": {
        "type": "dir",
        "children": {
            "src": {
                "type": "dir",
                "children": {
                    "main.py": {
                        "type": "file",
                        "content_patterns": ["Main application", "Hello from main"]
                    },
                    "utils.py": {
                        "type": "file",
                        "content_patterns": ["Utility functions", "helper", "Helper function"]
                    }
                }
            },
            "tests": {
                "type": "dir",
                "children": {
                    "test_main.py": {
                        "type": "file",
                        "content_patterns": ["Tests for main", "unittest"]
                    }
                }
            },
            "README.md": {
                "type": "file",
                "content_patterns": ["Project README", "sample project"]
            }
        }
    }
}

# =============================================================================
# IMPLEMENTATION
# =============================================================================

def get_test_directory() -> Path:
    """Get the test directory from environment variable."""
    test_dir = os.getenv("FILESYSTEM_TEST_DIR")
    if not test_dir:
        print("❌ FILESYSTEM_TEST_DIR environment variable not set")
        sys.exit(1)
    return Path(test_dir)

def verify_structure(base_path: Path, structure: dict, path_prefix: str = "") -> bool:
    """Recursively verify directory structure."""
    all_passed = True
    
    for name, info in structure.items():
        current_path = base_path / name
        display_path = f"{path_prefix}/{name}" if path_prefix else name
        
        if info["type"] == "dir":
            # Check directory exists
            if current_path.exists() and current_path.is_dir():
                print(f"✅ Directory exists: {display_path}/")
                
                # Check children if any
                if "children" in info:
                    child_result = verify_structure(current_path, info["children"], display_path)
                    all_passed = all_passed and child_result
            else:
                print(f"❌ Directory missing: {display_path}/")
                all_passed = False
                
        elif info["type"] == "file":
            # Check file exists
            if current_path.exists() and current_path.is_file():
                print(f"✅ File exists: {display_path}")
                
                # Check content patterns if specified
                if "content_patterns" in info:
                    try:
                        content = current_path.read_text()
                        content_lower = content.lower()
                        
                        for pattern in info["content_patterns"]:
                            if pattern.lower() in content_lower:
                                print(f"  ✅ Contains: '{pattern}'")
                            else:
                                print(f"  ❌ Missing: '{pattern}'")
                                all_passed = False
                    except Exception as e:
                        print(f"  ❌ Error reading file: {e}")
                        all_passed = False
            else:
                print(f"❌ File missing: {display_path}")
                all_passed = False
    
    return all_passed

def count_items(structure: dict) -> tuple[int, int]:
    """Count total directories and files in structure."""
    dirs = 0
    files = 0
    
    for name, info in structure.items():
        if info["type"] == "dir":
            dirs += 1
            if "children" in info:
                child_dirs, child_files = count_items(info["children"])
                dirs += child_dirs
                files += child_files
        else:
            files += 1
    
    return dirs, files

def main():
    """Main verification function."""
    print("🔍 Verifying Filesystem Task 3: Directory Operations")
    print("=" * 50)
    
    # Get test directory
    test_dir = get_test_directory()
    print(f"📁 Test directory: {test_dir}")
    
    # Count expected items
    expected_dirs, expected_files = count_items(EXPECTED_STRUCTURE)
    print(f"\n📊 Expected: {expected_dirs} directories, {expected_files} files")
    
    # Verify structure
    print("\n🔍 Checking directory structure:")
    if not verify_structure(test_dir, EXPECTED_STRUCTURE):
        print("\n❌ Task 3 verification: FAIL")
        print("Directory structure does not match specification")
        sys.exit(1)
    
    print("\n🎉 Task 3 verification: PASS")
    print("Directory structure created correctly with all files")
    sys.exit(0)

if __name__ == "__main__":
    main()