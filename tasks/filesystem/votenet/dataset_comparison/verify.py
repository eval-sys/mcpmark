#!/usr/bin/env python3
"""
Verification script for Votenet Dataset Comparison Task
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

def verify_analysis_file_exists(test_dir: Path) -> bool:
    """Verify that the analysis.txt file exists."""
    analysis_file = test_dir / "analysis.txt"
    
    if not analysis_file.exists():
        print("❌ File 'analysis.txt' not found")
        return False
    
    print("✅ Analysis file found")
    return True

def verify_analysis_format(test_dir: Path) -> bool:
    """Verify that the analysis file has the correct format."""
    analysis_file = test_dir / "analysis.txt"
    
    try:
        content = analysis_file.read_text()
        lines = content.split('\n')
        
        # Check if content is not empty
        if not content.strip():
            print("❌ Analysis file is empty")
            return False
        
        # Check if we have enough lines for at least one category block
        if len(lines) < 2:
            print("❌ Analysis file doesn't have enough lines for a category block")
            return False
        
        # Check if the format follows the 2-line block pattern with empty lines between blocks
        # Each block should have: category_name, count, empty_line
        line_index = 0
        block_count = 0
        
        while line_index < len(lines):
            # Skip leading empty lines
            while line_index < len(lines) and lines[line_index].strip() == "":
                line_index += 1
            
            if line_index >= len(lines):
                break
            
            # Check if we have at least 2 lines for a block
            if line_index + 1 >= len(lines):
                print("❌ Incomplete category block at the end")
                return False
            
            # Line 1 should be category name
            category_line = lines[line_index].strip()
            if not category_line:
                print(f"❌ Empty category name at line {line_index + 1}")
                return False
            
            # Line 2 should be count
            count_line = lines[line_index + 1].strip()
            if not count_line:
                print(f"❌ Empty count at line {line_index + 2}")
                return False
            
            # Check if count line contains a number
            if not re.search(r'\d+', count_line):
                print(f"❌ Count line doesn't contain a number at line {line_index + 2}: '{count_line}'")
                return False
            
            block_count += 1
            line_index += 2
            
            # Skip empty line between blocks (if not at the end)
            if line_index < len(lines) and lines[line_index].strip() == "":
                line_index += 1
        
        if block_count == 0:
            print("❌ No valid category blocks found")
            return False
        
        print(f"✅ Analysis format is correct with {block_count} category blocks")
        return True
        
    except Exception as e:
        print(f"❌ Error reading analysis file: {e}")
        return False

def verify_required_categories(test_dir: Path) -> bool:
    """Verify that all required SUN RGB-D categories are present."""
    analysis_file = test_dir / "analysis.txt"
    
    try:
        content = analysis_file.read_text()
        lines = content.split('\n')
        
        # Extract category names from the file
        categories_found = []
        line_index = 0
        
        while line_index < len(lines):
            # Skip empty lines
            while line_index < len(lines) and lines[line_index].strip() == "":
                line_index += 1
            
            if line_index >= len(lines):
                break
            
            # Get category name
            category_line = lines[line_index].strip()
            if category_line:
                categories_found.append(category_line.lower())
            
            # Skip to next block
            line_index += 2
            while line_index < len(lines) and lines[line_index].strip() == "":
                line_index += 1
        
        # Required categories
        required_categories = {
            'chair', 'table', 'bed', 'bookshelf', 'desk', 
            'toilet', 'dresser', 'bathtub', 'sofa', 'night_stand'
        }
        
        # Check if all required categories are present
        missing_categories = required_categories - set(categories_found)
        if missing_categories:
            print(f"❌ Missing required categories: {missing_categories}")
            return False
        
        # Check for extra categories
        extra_categories = set(categories_found) - required_categories
        if extra_categories:
            print(f"⚠️  Extra categories found: {extra_categories}")
        
        print(f"✅ All required categories present: {sorted(required_categories)}")
        return True
        
    except Exception as e:
        print(f"❌ Error verifying required categories: {e}")
        return False

def verify_category_counts(test_dir: Path) -> bool:
    """Verify that the category counts match the expected values."""
    analysis_file = test_dir / "analysis.txt"
    
    try:
        content = analysis_file.read_text()
        lines = content.split('\n')
        
        # Expected counts from answer.txt
        expected_counts = {
            'chair': 4681,
            'table': 1170,
            'bed': 370,
            'bookshelf': 377,
            'desk': 680,
            'toilet': 256,
            'dresser': 213,
            'bathtub': 144,
            'sofa': 1,
            'night_stand': 224
        }
        
        # Extract category counts from the file
        category_counts = {}
        line_index = 0
        
        while line_index < len(lines):
            # Skip empty lines
            while line_index < len(lines) and lines[line_index].strip() == "":
                line_index += 1
            
            if line_index >= len(lines):
                break
            
            # Get category name
            category_line = lines[line_index].strip()
            if not category_line:
                line_index += 1
                continue
            
            # Get count
            if line_index + 1 < len(lines):
                count_line = lines[line_index + 1].strip()
                if count_line:
                    # Extract number from count line
                    count_match = re.search(r'(\d+)', count_line)
                    if count_match:
                        category = category_line.lower()
                        count = int(count_match.group(1))
                        category_counts[category] = count
            
            # Skip to next block
            line_index += 2
            while line_index < len(lines) and lines[line_index].strip() == "":
                line_index += 1
        
        # Verify counts match expected values
        all_counts_correct = True
        for category, expected_count in expected_counts.items():
            if category in category_counts:
                actual_count = category_counts[category]
                if actual_count != expected_count:
                    print(f"❌ Count mismatch for {category}: expected {expected_count}, got {actual_count}")
                    all_counts_correct = False
            else:
                print(f"❌ Category {category} not found in analysis")
                all_counts_correct = False
        
        if all_counts_correct:
            print("✅ All category counts match expected values")
            return True
        else:
            return False
        
    except Exception as e:
        print(f"❌ Error verifying category counts: {e}")
        return False

def verify_file_structure(test_dir: Path) -> bool:
    """Verify that the analysis.txt file is in the correct location."""
    analysis_file = test_dir / "analysis.txt"
    
    if not analysis_file.exists():
        print("❌ Analysis file not found in test directory root")
        return False
    
    # Check if it's directly in the test directory root, not in a subdirectory
    if analysis_file.parent != test_dir:
        print("❌ Analysis file should be in the test directory root")
        return False
    
    print("✅ Analysis file is in the correct location")
    return True

def main():
    """Main verification function."""
    test_dir = get_test_directory()
    # test_dir = Path("/Users/chenlingjun/Desktop/MCP/MCPBench/.mcpbench_backups/backup_filesystem_votenet_dataset_comparison_61641")
    print("🔍 Verifying Votenet Dataset Comparison Task...")
    
    # Define verification steps
    verification_steps = [
        ("Analysis File Exists", verify_analysis_file_exists),
        ("File Location", verify_file_structure),
        ("File Format", verify_analysis_format),
        ("Required Categories", verify_required_categories),
        ("Category Counts", verify_category_counts),
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
        print("✅ Votenet dataset comparison task completed correctly!")
        print("🎉 Task verification: PASS")
        sys.exit(0)
    else:
        print("❌ Task verification: FAIL")
        sys.exit(1)

if __name__ == "__main__":
    main()