#!/usr/bin/env python3
"""
Verification script for ThreeStudio Task 2: Analyze Zero123 Guidance Output Structure
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

def verify_answer_file_exists(test_dir: Path) -> bool:
    """Verify that the answer.txt file exists."""
    answer_file = test_dir / "answer.txt"
    
    if not answer_file.exists():
        print("❌ File 'answer.txt' not found")
        return False
    
    print("✅ Answer file found")
    return True

def verify_required_strings(test_dir: Path) -> bool:
    """Verify that the answer contains the four required strings."""
    answer_file = test_dir / "answer.txt"
    
    try:
        content = answer_file.read_text()
        
        # Check for required strings
        required_strings = ["loss_sds", "grad_norm", "min_step", "max_step"]
        missing_strings = []
        
        for string in required_strings:
            if string not in content:
                missing_strings.append(string)
        
        if missing_strings:
            print(f"❌ Missing required strings: {missing_strings}")
            return False
        
        print("✅ All required strings found")
        return True
        
    except Exception as e:
        print(f"❌ Error reading answer file: {e}")
        return False

def verify_file_path(test_dir: Path) -> bool:
    """Verify that the file path contains the exact expected path string."""
    answer_file = test_dir / "answer.txt"
    
    try:
        content = answer_file.read_text()
        
        # Check for the exact expected file path
        expected_path = "threestudio/models/guidance/zero123_guidance.py"
        
        if expected_path not in content:
            print(f"❌ Missing expected file path: {expected_path}")
            return False
        
        print("✅ File path found: threestudio/models/guidance/zero123_guidance.py")
        return True
        
    except Exception as e:
        print(f"❌ Error verifying file path: {e}")
        return False

def main():
    """Main verification function."""
    test_dir = get_test_directory()
    # test_dir = Path("/Users/chenlingjun/Desktop/MCP/MCPBench/.mcpbench_backups/backup_filesystem_threestudio_output_analysis_mv_38067")
    print("🔍 Verifying ThreeStudio Task 2: Analyze Zero123 Guidance Output Structure...")
    
    # Define verification steps
    verification_steps = [
        ("Answer File Exists", verify_answer_file_exists),
        ("Required Strings", verify_required_strings),
        ("File Path Components", verify_file_path),
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
        print("✅ Zero123 guidance output structure analyzed correctly!")
        print("🎉 Task 2 verification: PASS")
        sys.exit(0)
    else:
        print("❌ Task 2 verification: FAIL")
        sys.exit(1)

if __name__ == "__main__":
    main()