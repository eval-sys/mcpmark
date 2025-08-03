#!/usr/bin/env python3
"""
Verification script for Filesystem Task 3: Create Directory Structure
"""

import sys
from pathlib import Path

def get_test_directory() -> Path:
    """Get the test directory using relative path."""
    script_dir = Path(__file__).parent
    return script_dir / "../../../test_environments/desktop"

def verify_task(test_dir: Path) -> bool:
    """Verify the task was completed correctly."""
    project_dir = test_dir / "new_project"
    
    # Check directories exist
    required_dirs = [
        project_dir,
        project_dir / "src", 
        project_dir / "docs"
    ]
    
    for dir_path in required_dirs:
        if not dir_path.exists():
            print(f"❌ Directory '{dir_path.name}' not found")
            return False
    
    # Check files and content
    expected_files = {
        project_dir / "config.txt": "Configuration settings for the project",
        project_dir / "src" / "main.txt": "Main application code would go here",
        project_dir / "src" / "utils.txt": "Utility functions and helpers",
        project_dir / "docs" / "readme.txt": "Project documentation and setup instructions"
    }
    
    for file_path, expected_content in expected_files.items():
        if not file_path.exists():
            print(f"❌ File '{file_path.relative_to(test_dir)}' not found")
            return False
        
        try:
            actual_content = file_path.read_text().strip()
            if actual_content != expected_content:
                print(f"❌ Content mismatch in '{file_path.name}'")
                return False
        except Exception as e:
            print(f"❌ Error reading '{file_path.name}': {e}")
            return False
    
    print("✅ Directory structure created correctly")
    return True

def main():
    """Main verification function."""
    test_dir = get_test_directory()
    
    if verify_task(test_dir):
        print("🎉 Task 3 verification: PASS")
        sys.exit(0)
    else:
        print("❌ Task 3 verification: FAIL")
        sys.exit(1)

if __name__ == "__main__":
    main()