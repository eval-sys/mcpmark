#!/usr/bin/env python3
"""
Verification script for Directory Structure Mirroring with Smart Placeholders Task
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

def verify_mirror_directory_exists(test_dir: Path, mirror_path: Path) -> bool:
    """Verify that a mirror directory exists."""
    if not mirror_path.exists():
        print(f"❌ Mirror directory not found: {mirror_path.relative_to(test_dir)}")
        return False
    
    if not mirror_path.is_dir():
        print(f"❌ Mirror path exists but is not a directory: {mirror_path.relative_to(test_dir)}")
        return False
    
    print(f"✅ Mirror directory exists: {mirror_path.relative_to(test_dir)}")
    return True

def verify_placeholder_file_exists(mirror_path: Path, test_dir: Path) -> bool:
    """Verify that placeholder.txt exists in the mirror directory."""
    placeholder_file = mirror_path / "placeholder.txt"
    
    if not placeholder_file.exists():
        print(f"❌ placeholder.txt not found in: {mirror_path.relative_to(test_dir)}")
        return False
    
    if not placeholder_file.is_file():
        print(f"❌ placeholder.txt exists but is not a file in: {mirror_path.relative_to(test_dir)}")
        return False
    
    print(f"✅ placeholder.txt exists in: {mirror_path.relative_to(test_dir)}")
    return True

def verify_placeholder_content(mirror_path: Path, test_dir: Path) -> bool:
    """Verify that placeholder.txt contains the correct path ending with complex_structure_mirror/..."""
    placeholder_file = mirror_path / "placeholder.txt"
    
    try:
        content = placeholder_file.read_text().strip()
        
        # Check if content is not empty
        if not content:
            print(f"❌ placeholder.txt is empty in: {mirror_path.relative_to(test_dir)}")
            return False
        
        # Check if it contains the correct path ending with complex_structure_mirror/...
        expected_ending = f"complex_structure_mirror/{mirror_path.relative_to(test_dir / 'complex_structure_mirror')}"
        if not content.endswith(expected_ending):
            print(f"❌ placeholder.txt content incorrect in: {mirror_path.relative_to(test_dir)}")
            print(f"   Expected ending: {expected_ending}")
            print(f"   Found: {content}")
            return False
        
        print(f"✅ placeholder.txt content is correct in: {mirror_path.relative_to(test_dir)}")
        return True
        
    except Exception as e:
        print(f"❌ Error reading placeholder.txt in {mirror_path.relative_to(test_dir)}: {e}")
        return False

def verify_no_files_copied(test_dir: Path) -> bool:
    """Verify that no file contents were copied, only directory structure."""
    source_dir = test_dir / "complex_structure"
    mirror_dir = test_dir / "complex_structure_mirror"
    
    if not mirror_dir.exists():
        print("❌ Mirror directory 'complex_structure_mirror' not found")
        return False
    
    # Check that no files from source were copied (except placeholder.txt files)
    for source_file in source_dir.rglob("*"):
        if source_file.is_file():
            # Calculate the corresponding mirror path
            relative_path = source_file.relative_to(source_dir)
            mirror_file = mirror_dir / relative_path
            
            # Skip if this would be a placeholder.txt file
            if mirror_file.name == "placeholder.txt":
                continue
            
            if mirror_file.exists():
                print(f"❌ File was copied when it shouldn't be: {relative_path}")
                return False
    
    print("✅ No file contents were copied, only directory structure")
    return True

def verify_mirror_structure_completeness(test_dir: Path) -> bool:
    """Verify that the mirror structure is complete and matches expected structure."""
    mirror_dir = test_dir / "complex_structure_mirror"
    
    if not mirror_dir.exists():
        print("❌ Mirror directory 'complex_structure_mirror' not found")
        return False
    
    # Define expected directories that should exist (based on backup structure)
    expected_dirs = [
        "deeply",
        "deeply/nested",
        "deeply/nested/folder",
        "deeply/nested/folder/structure",
        "empty_folder", 
        "folder_lxkHt_0_1_processed",
        "folder_QdTAj_0_2_processed",
        "folder_xtgyi_0_0_processed",
        "mixed_content",
        "mixed_content/images_and_text",
        "project",
        "project/docs",
        "project/docs/archive",
        "project/docs/archive/2023_processed",
        "project/src",
        "project/src/main",
        "project/src/main/resources"
    ]
    
    # Define which directories should have placeholder.txt files
    placeholder_dirs = [
        "deeply/nested/folder/structure",
        "empty_folder", 
        "folder_lxkHt_0_1_processed",
        "folder_QdTAj_0_2_processed",
        "folder_xtgyi_0_0_processed",
        "mixed_content/images_and_text",
        "project/docs/archive/2023_processed",
        "project/src/main/resources"
    ]
    
    all_passed = True
    
    # Check that all expected directories exist
    for expected_dir in expected_dirs:
        mirror_path = mirror_dir / expected_dir
        if not verify_mirror_directory_exists(test_dir, mirror_path):
            all_passed = False
        elif expected_dir in placeholder_dirs:
            # Check placeholder.txt for directories that should have it
            if not verify_placeholder_file_exists(mirror_path, test_dir):
                all_passed = False
            elif not verify_placeholder_content(mirror_path, test_dir):
                all_passed = False
    
    # Check that no unexpected directories exist
    for mirror_subdir in mirror_dir.rglob("*"):
        if mirror_subdir.is_dir():
            relative_path = mirror_subdir.relative_to(mirror_dir)
            if str(relative_path) not in expected_dirs and str(relative_path) != ".":
                print(f"❌ Unexpected directory found: {relative_path}")
                all_passed = False
    
    return all_passed

def main():
    """Main verification function."""
    try:
        test_dir = get_test_directory()
        # test_dir = Path("/Users/chenlingjun/Desktop/MCP/MCPBench/.mcpbench_backups/backup_filesystem_folder_structure_structure_mirror_30572")
        print(f"🔍 Verifying Directory Structure Mirroring with Smart Placeholders in: {test_dir}")
        
        # Define verification steps
        verification_steps = [
            ("No files copied", verify_no_files_copied),
            ("Mirror structure completeness", verify_mirror_structure_completeness),
        ]
        
        # Run all verification steps
        all_passed = True
        for step_name, verify_func in verification_steps:
            print(f"\n📋 Checking: {step_name}")
            if not verify_func(test_dir):
                all_passed = False
        
        # Final result
        print("\n" + "="*50)
        if all_passed:
            print("✅ Directory structure mirroring completed correctly!")
            print("🎉 Structure Mirror verification: PASS")
            sys.exit(0)
        else:
            print("❌ Structure Mirror verification: FAIL")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Verification failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()