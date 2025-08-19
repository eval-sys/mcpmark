#!/usr/bin/env python3
"""
Verification script for Directory Structure Analysis Task
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

def verify_structure_analysis_file_exists(test_dir: Path) -> bool:
    """Verify that the structure_analysis.txt file exists."""
    analysis_file = test_dir / "structure_analysis.txt"
    
    if not analysis_file.exists():
        print("❌ File 'structure_analysis.txt' not found")
        return False
    
    print("✅ structure_analysis.txt file found")
    return True

def verify_structure_analysis_file_readable(test_dir: Path) -> bool:
    """Verify that the structure_analysis.txt file is readable."""
    analysis_file = test_dir / "structure_analysis.txt"
    
    try:
        content = analysis_file.read_text()
        if not content.strip():
            print("❌ structure_analysis.txt file is empty")
            return False
        
        print("✅ structure_analysis.txt file is readable")
        return True
        
    except Exception as e:
        print(f"❌ Error reading structure_analysis.txt file: {e}")
        return False

def verify_subtask1_file_statistics(test_dir: Path) -> bool:
    """Verify subtask 1: File Statistics - files must be 69, folders must be 51, 58097 allows +-1000."""
    analysis_file = test_dir / "structure_analysis.txt"
    
    try:
        content = analysis_file.read_text()
        
        # Extract numbers from the content
        file_count_match = re.search(r'total number of files:\s*(\d+)', content)
        folder_count_match = re.search(r'total number of folders:\s*(\d+)', content)
        size_match = re.search(r'total size of all files:\s*(\d+)', content)
        
        if not file_count_match or not folder_count_match or not size_match:
            print("❌ Could not extract file statistics from structure_analysis.txt")
            return False
        
        file_count = int(file_count_match.group(1))
        folder_count = int(folder_count_match.group(1))
        total_size = int(size_match.group(1))
        
        print(f"📊 Found: files={file_count}, folders={folder_count}, size={total_size}")
        
        # Check if file count is exactly 69
        if file_count != 69:
            print(f"❌ File count must be 69, found: {file_count}")
            return False
        
        # Check if folder count is exactly 51
        if folder_count != 51:
            print(f"❌ Folder count must be 51, found: {folder_count}")
            return False
        
        # Check if size is within acceptable range (58097 ± 1000)
        expected_size = 58097
        size_tolerance = 1000
        if abs(total_size - expected_size) > size_tolerance:
            print(f"❌ Total size ({total_size}) is not within acceptable range ({expected_size} ± {size_tolerance})")
            return False
        
        print(f"✅ File statistics verified: files={file_count}, folders={folder_count}, size={total_size} (within tolerance)")
        return True
        
    except Exception as e:
        print(f"❌ Error verifying file statistics: {e}")
        return False

def verify_subtask2_depth_analysis(test_dir: Path) -> bool:
    """Verify subtask 2: Depth Analysis - depth must be 7, verify path exists."""
    analysis_file = test_dir / "structure_analysis.txt"
    
    try:
        content = analysis_file.read_text()
        
        # Extract depth and path
        depth_match = re.search(r'depth:\s*(\d+)', content)
        path_match = re.search(r'^([^\n]+)$', content, re.MULTILINE)
        
        if not depth_match:
            print("❌ Could not extract depth from structure_analysis.txt")
            return False
        
        depth = int(depth_match.group(1))
        
        # Check if depth is exactly 7
        if depth != 7:
            print(f"❌ Depth must be 7, found: {depth}")
            return False
        
        print(f"✅ Depth verified: {depth}")
        
        # Extract the path (it should be on a separate line after "depth: 7")
        lines = content.split('\n')
        path_line = None
        for i, line in enumerate(lines):
            if line.strip() == f"depth: {depth}":
                if i + 1 < len(lines):
                    path_line = lines[i + 1].strip()
                    break
        
        if not path_line:
            print("❌ Could not find path line after depth specification")
            return False
        
        print(f"📁 Found path: {path_line}")
        
        # Verify that the path depth matches the declared depth
        path_parts = path_line.split('/')
        actual_depth = len(path_parts)
        
        if actual_depth != depth:
            print(f"❌ Path depth mismatch: declared depth is {depth}, but path has {actual_depth} levels")
            print(f"   Path: {path_line}")
            print(f"   Path parts: {path_parts}")
            return False
        
        print(f"✅ Path depth verified: {actual_depth} levels")
        
        # Verify that this path exists in the test environment
        expected_path = test_dir / path_line
        if not expected_path.exists():
            print(f"❌ Path does not exist: {expected_path}")
            return False
        
        if not expected_path.is_dir():
            print(f"❌ Path exists but is not a directory: {expected_path}")
            return False
        
        print(f"✅ Path verified and exists: {path_line}")
        return True
        
    except Exception as e:
        print(f"❌ Error verifying depth analysis: {e}")
        return False

def verify_subtask3_file_type_classification(test_dir: Path) -> bool:
    """Verify subtask 3: File Type Classification - 68 and 1 must be accurate."""
    analysis_file = test_dir / "structure_analysis.txt"
    
    try:
        content = analysis_file.read_text()
        
        # Extract file type counts
        txt_match = re.search(r'txt:\s*(\d+)', content)
        py_match = re.search(r'py:\s*(\d+)', content)
        
        if not txt_match or not py_match:
            print("❌ Could not extract file type counts from structure_analysis.txt")
            return False
        
        txt_count = int(txt_match.group(1))
        py_count = int(py_match.group(1))
        
        print(f"📁 Found: txt={txt_count}, py={py_count}")
        
        # Check if txt count is exactly 68
        if txt_count != 68:
            print(f"❌ txt count must be 68, found: {txt_count}")
            return False
        
        # Check if py count is exactly 1
        if py_count != 1:
            print(f"❌ py count must be 1, found: {py_count}")
            return False
        
        print(f"✅ File type classification verified: txt={txt_count}, py={py_count}")
        return True
        
    except Exception as e:
        print(f"❌ Error verifying file type classification: {e}")
        return False

def verify_file_format(test_dir: Path) -> bool:
    """Verify that the structure_analysis.txt file has proper format."""
    analysis_file = test_dir / "structure_analysis.txt"
    
    try:
        content = analysis_file.read_text()
        lines = content.split('\n')
        
        # Check if file has the expected structure
        if len(lines) < 5:  # Should have at least 5 lines
            print("❌ File seems too short to contain all required information")
            return False
        
        # Basic format check - ensure it's not completely corrupted
        if not content.strip():
            print("❌ File is completely empty")
            return False
        
        print("✅ File format is acceptable")
        return True
        
    except Exception as e:
        print(f"❌ Error checking file format: {e}")
        return False

def main():
    """Main verification function."""
    try:
        test_dir = get_test_directory()
        print(f"🔍 Verifying Directory Structure Analysis Task in: {test_dir}")
        
        # Define verification steps
        verification_steps = [
            ("Structure Analysis File Exists", verify_structure_analysis_file_exists),
            ("File is Readable", verify_structure_analysis_file_readable),
            ("Subtask 1: File Statistics", verify_subtask1_file_statistics),
            ("Subtask 2: Depth Analysis", verify_subtask2_depth_analysis),
            ("Subtask 3: File Type Classification", verify_subtask3_file_type_classification),
            ("File Format", verify_file_format),
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
            print("✅ Directory Structure Analysis completed correctly!")
            print("🎉 Structure Analysis verification: PASS")
            sys.exit(0)
        else:
            print("❌ Structure Analysis verification: FAIL")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Verification failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()