#!/usr/bin/env python3
"""
Verification script for Text File Merging Task
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

def get_expected_contents():
    """Return the expected content from each .txt file."""
    return [
        "O rErmZ4tDgzMNoxn1oNfQhT1TRpy9w0tQPGTcrsaoMFrrgt9bY5mgBxO6q8c8lZywXxEEBWW4i6Jh9NbAtYtRKvkzB4bshGIMzn2G1 rDTpKJj",
        "DmRrDFFaIl1mPubzSJJaN4aMeZyBHqVxZe5tpztHQ9zSe6b69Hnl7coqeNJXHXU2EnaDnyhYxZSWHPn3IWLsLGWrx7py8d37Z8blMnh7VDUH7hAMamhLRO8lfUVV1roM8a0njnW9evXRq5AoNTt8Tv7kQ5LmLe6Z66MZwtjckRAXmOB4x3AYbbxLULYZAxitW1KNG1yTaDOYZQhtKdZkX1XqytzBl9dRXI4gk91ZlVHLOiujwUa89EVsdjayKeCc21gCJMXvbhDSOGAs6dXZEHuaHQnnBdM19X3TwPgfDONyhlc pjwoQ45D56UQVWxwNIJUTgwS1vctYOx4XFpMgf3PRQ7zZdfhIuPBFdQwnQvYUeQbWa5gnyMO9FVSU0vm9uccbJQvkcEAJzMkEh9i7z6EEixtbwVedlTGWL2XBwjenRdf2qsOgvJo8Dyuvf35ieCFMG7wR7200rs GJZ5bRdx4R2gGOWVMi3MOBrqcw3KhbcpJtdQoKMALEjBMrY7VYKtAZNI6LoXX OOTJZ3x3usHRJY0gMtKhh6OJ 37aknvBwNYJ0IRWYWaeJ8LBwJyO6ZV3ZJ0palISQvGaHEZ0olHnK2iNCTxqxvF8J7EdIdIPYssl5f0XgPl6",
        "aFCzXJbJq02zlCKnyarJnPUiwVIuUrQci3fZvGD53F5fUsKDUlEwO5 ANJ2VgBnJ5cuBJzjILcM9AxTvyNZ5NPIHjSCo5O20K"
    ]

def verify_merge_file_exists(test_dir: Path) -> bool:
    """Verify that merge.txt exists in the test directory."""
    merge_file = test_dir / "merge.txt"
    
    if not merge_file.exists():
        print("❌ merge.txt not found")
        return False
    
    if not merge_file.is_file():
        print("❌ merge.txt exists but is not a file")
        return False
    
    print("✅ merge.txt exists")
    return True

def verify_merge_file_contents(test_dir: Path) -> bool:
    """Verify that merge.txt contains all expected content strings."""
    merge_file = test_dir / "merge.txt"
    expected_contents = get_expected_contents()
    
    try:
        with open(merge_file, 'r', encoding='utf-8') as f:
            merge_content = f.read()
    except Exception as e:
        print(f"❌ Failed to read merge.txt: {e}")
        return False
    
    # Check that each expected content string is present in the merged file
    missing_contents = []
    for content in expected_contents:
        if content not in merge_content:
            missing_contents.append(content[:50] + "..." if len(content) > 50 else content)
    
    if missing_contents:
        print(f"❌ Missing content in merge.txt:")
        for content in missing_contents:
            print(f"   - {content}")
        return False
    
    print("✅ merge.txt contains all expected content")
    return True

def main():
    """Main verification function."""
    try:
        test_dir = get_test_directory()
        print(f"🔍 Verifying text file merging in: {test_dir}")
        
        # Run all verification checks
        checks = [
            ("Merge file existence", verify_merge_file_exists),
            ("Merge file contents", verify_merge_file_contents)
        ]
        
        all_passed = True
        for check_name, check_func in checks:
            print(f"\n📋 Checking: {check_name}")
            if not check_func(test_dir):
                all_passed = False
        
        if all_passed:
            print("\n🎉 All verification checks passed!")
            sys.exit(0)
        else:
            print("\n❌ Some verification checks failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Verification failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
