#!/usr/bin/env python3
"""
Verification script for Desktop 2 Timeline Extraction Task
"""

import sys
from pathlib import Path
import os
import re
from datetime import datetime
from typing import List, Tuple, Set

def get_test_directory() -> Path:
    """Get the test directory from FILESYSTEM_TEST_DIR env var."""
    test_root = os.environ.get("FILESYSTEM_TEST_DIR")
    if not test_root:
        raise ValueError("FILESYSTEM_TEST_DIR environment variable is required")
    return Path(test_root)

def verify_timeline_file_exists(test_dir: Path) -> bool:
    """Verify that the timeline.txt file exists in the main directory."""
    timeline_file = test_dir / "timeline.txt"
    
    if not timeline_file.exists():
        print("❌ 'timeline.txt' file not found in main directory")
        return False
    
    if not timeline_file.is_file():
        print("❌ 'timeline.txt' exists but is not a file")
        return False
    
    print("✅ 'timeline.txt' file exists in main directory")
    return True

def verify_timeline_file_readable(test_dir: Path) -> bool:
    """Verify that the timeline.txt file is readable."""
    timeline_file = test_dir / "timeline.txt"
    
    try:
        content = timeline_file.read_text(encoding='utf-8')
        if not content.strip():
            print("❌ 'timeline.txt' file is empty")
            return False
        
        print("✅ 'timeline.txt' file is readable")
        return True
        
    except Exception as e:
        print(f"❌ Error reading 'timeline.txt' file: {e}")
        return False

def verify_line_count(test_dir: Path) -> bool:
    """Verify that the timeline.txt file has exactly 43 lines."""
    timeline_file = test_dir / "timeline.txt"
    
    try:
        content = timeline_file.read_text(encoding='utf-8')
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        
        if len(lines) != 43:
            print(f"❌ Expected 43 lines, but found {len(lines)} lines")
            return False
        
        print(f"✅ File contains exactly {len(lines)} lines")
        return True
        
    except Exception as e:
        print(f"❌ Error checking line count: {e}")
        return False

def verify_line_format(test_dir: Path) -> bool:
    """Verify that each line contains both file path and date time information."""
    timeline_file = test_dir / "timeline.txt"
    
    try:
        content = timeline_file.read_text(encoding='utf-8')
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        
        # More flexible pattern: just check if line contains both path-like content and date-like content
        date_pattern = r'\d{4}-\d{2}-\d{2}'  # YYYY-MM-DD format
        
        invalid_lines = []
        for i, line in enumerate(lines, 1):
            # Check if line contains a date
            if not re.search(date_pattern, line):
                invalid_lines.append(f"Line {i}: '{line}' (no valid date found)")
                continue
            
            # Check if line contains path-like content (contains '/' or '.' and not just a date)
            # More flexible: look for path anywhere in the line, not just at the beginning
            path_found = False
            
            # Split line into words and look for path-like content
            words = line.split()
            for word in words:
                # Check if word looks like a file path (contains '/' or '.' and not just a date)
                if ('/' in word or '.' in word) and not re.match(r'^\d{4}-\d{2}-\d{2}$', word.strip()):
                    path_found = True
                    break
            
            # Also check if line contains path-like content with colon separator
            if ':' in line:
                parts = line.split(':')
                for part in parts:
                    if ('/' in part or '.' in part) and not re.match(r'^\d{4}-\d{2}-\d{2}$', part.strip()):
                        path_found = True
                        break
            
            if not path_found:
                invalid_lines.append(f"Line {i}: '{line}' (no valid path found)")
                continue
        
        if invalid_lines:
            print(f"❌ Invalid line format found: {invalid_lines[:5]}...")
            return False
        
        print("✅ All lines contain both file path and date time information")
        return True
        
    except Exception as e:
        print(f"❌ Error checking line format: {e}")
        return False

def verify_date_format(test_dir: Path) -> bool:
    """Verify that all dates are in valid YYYY-MM-DD format."""
    timeline_file = test_dir / "timeline.txt"
    
    try:
        content = timeline_file.read_text(encoding='utf-8')
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        
        invalid_dates = []
        for i, line in enumerate(lines, 1):
            try:
                # Find date pattern in the line (more flexible)
                date_match = re.search(r'\d{4}-\d{2}-\d{2}', line)
                if not date_match:
                    invalid_dates.append(f"Line {i}: '{line}' (no date found)")
                    continue
                
                date_part = date_match.group()
                datetime.strptime(date_part, '%Y-%m-%d')
            except (IndexError, ValueError) as e:
                invalid_dates.append(f"Line {i}: '{line}' (invalid date: {e})")
        
        if invalid_dates:
            print(f"❌ Invalid date format found: {invalid_dates[:5]}...")
            return False
        
        print("✅ All dates are in valid YYYY-MM-DD format")
        return True
        
    except Exception as e:
        print(f"❌ Error checking date format: {e}")
        return False

def verify_chronological_order(test_dir: Path) -> bool:
    """Verify that dates are in chronological order."""
    timeline_file = test_dir / "timeline.txt"
    
    try:
        content = timeline_file.read_text(encoding='utf-8')
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        
        dates = []
        for line in lines:
            # Find date pattern in the line (more flexible)
            date_match = re.search(r'\d{4}-\d{2}-\d{2}', line)
            if date_match:
                date_obj = datetime.strptime(date_match.group(), '%Y-%m-%d')
                dates.append(date_obj)
        
        # Check if dates are in ascending order
        for i in range(1, len(dates)):
            if dates[i] < dates[i-1]:
                print(f"❌ Date order violation: {dates[i-1].strftime('%Y-%m-%d')} comes after {dates[i].strftime('%Y-%m-%d')}")
                return False
        
        print("✅ All dates are in chronological order")
        return True
        
    except Exception as e:
        print(f"❌ Error checking chronological order: {e}")
        return False

def verify_expected_entries(test_dir: Path) -> bool:
    """Verify that all expected entries from answer.txt are present."""
    timeline_file = test_dir / "timeline.txt"
    
    try:
        content = timeline_file.read_text(encoding='utf-8')
        actual_lines = [line.strip() for line in content.split('\n') if line.strip()]
        
        # Expected entries from answer.txt
        expected_entries = {
            "exp_logs/project_2/analysis_report.md:2024-01-01",
            "learning/2024/learning_progress.csv:2024-01-01",
            "exp_logs/experiment_summary.md:2024-01-05",
            "play/kit&shoes_collection/inventory.py:2024-01-05",
            "exp_logs/experiment_summary.md:2024-01-10",
            "play/kit&shoes_collection/inventory.py:2024-01-10",
            "exp_logs/aug/augmentation_log.txt:2024-01-15",
            "exp_logs/experiment_summary.md:2024-01-15",
            "play/kit&shoes_collection/inventory.py:2024-01-15",
            "learning/2024/learning_progress.csv:2024-02-01",
            "learning/2024/learning_progress.csv:2024-03-01",
            "play/hongkong_tour/travel_itinerary.csv:2024-03-15",
            "travel_plan/travel_calculator.py:2024-03-15",
            "play/hongkong_tour/travel_itinerary.csv:2024-03-16",
            "play/hongkong_tour/travel_itinerary.csv:2024-03-17",
            "play/hongkong_tour/travel_itinerary.csv:2024-03-18",
            "play/hongkong_tour/travel_itinerary.csv:2024-03-19",
            "play/hongkong_tour/travel_itinerary.csv:2024-03-20",
            "travel_plan/travel_bucket_list.md:2024-04-01",
            "learning/2024/learning_progress.csv:2024-04-01",
            "learning/2024/learning_progress.csv:2024-05-01",
            "travel_plan/travel_bucket_list.md:2024-06-01",
            "learning/2024/learning_progress.csv:2024-06-01",
            "learning/2024/learning_progress.csv:2024-07-01",
            "exp_logs/exp_record.md:2024-08-01",
            "exp_logs/results_record.csv:2024-08-01",
            "travel_plan/travel_bucket_list.md:2024-08-01",
            "learning/2024/learning_progress.csv:2024-08-01",
            "exp_logs/results_record.csv:2024-08-02",
            "exp_logs/results_record.csv:2024-08-03",
            "exp_logs/results_record.csv:2024-08-04",
            "exp_logs/exp_record.md:2024-09-01",
            "exp_logs/sep/september_summary.csv:2024-09-01",
            "learning/2024/learning_progress.csv:2024-09-01",
            "exp_logs/sep/september_summary.csv:2024-09-05",
            "exp_logs/sep/september_summary.csv:2024-09-10",
            "exp_logs/sep/september_summary.csv:2024-09-15",
            "exp_logs/sep/september_summary.csv:2024-09-20",
            "exp_logs/sep/september_summary.csv:2024-09-25",
            "exp_logs/sep/september_summary.csv:2024-09-30",
            "learning/2024/learning_progress.csv:2024-10-01",
            "learning/2024/learning_progress.csv:2024-11-01",
            "learning/2024/learning_progress.csv:2024-12-01"
        }
        
        # Check if each expected entry is found in actual lines (more flexible matching)
        missing_entries = []
        for expected in expected_entries:
            expected_path, expected_date = expected.split(':')
            found = False
            
            for actual_line in actual_lines:
                # Check if line contains both the expected path and date
                # More flexible: path can be anywhere in the line, not just at the beginning
                if expected_path in actual_line and expected_date in actual_line:
                    found = True
                    break
            
            if not found:
                missing_entries.append(expected)
        
        # Check for extra entries (lines that don't match any expected pattern)
        extra_entries = []
        for actual_line in actual_lines:
            # Extract date from actual line
            date_match = re.search(r'\d{4}-\d{2}-\d{2}', actual_line)
            if not date_match:
                continue
                
            actual_date = date_match.group()
            
            # Try to extract file path from the line
            actual_path = None
            words = actual_line.split()
            for word in words:
                if ('/' in word or '.' in word) and not re.match(r'^\d{4}-\d{2}-\d{2}$', word.strip()):
                    actual_path = word
                    break
            
            if not actual_path:
                continue
            
            # Find if this line matches any expected entry
            found_expected = False
            for expected in expected_entries:
                expected_path, expected_date = expected.split(':')
                if expected_path in actual_path and expected_date == actual_date:
                    found_expected = True
                    break
            
            if not found_expected:
                extra_entries.append(actual_line)
        
        if missing_entries:
            print(f"❌ Missing {len(missing_entries)} expected entries")
            print(f"   Examples: {missing_entries[:3]}")
            return False
        
        if extra_entries:
            print(f"❌ Found {len(extra_entries)} unexpected entries")
            print(f"   Examples: {extra_entries[:3]}")
            return False
        
        print("✅ All expected entries are present, no extra entries")
        return True
        
    except Exception as e:
        print(f"❌ Error checking expected entries: {e}")
        return False

def verify_no_duplicates(test_dir: Path) -> bool:
    """Verify that there are no duplicate entries."""
    timeline_file = test_dir / "timeline.txt"
    
    try:
        content = timeline_file.read_text(encoding='utf-8')
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        
        if len(lines) != len(set(lines)):
            print("❌ Duplicate entries found in timeline.txt")
            return False
        
        print("✅ No duplicate entries found")
        return True
        
    except Exception as e:
        print(f"❌ Error checking for duplicates: {e}")
        return False

def verify_file_paths_exist(test_dir: Path) -> bool:
    """Verify that all file paths mentioned in timeline.txt actually exist."""
    timeline_file = test_dir / "timeline.txt"
    
    try:
        content = timeline_file.read_text(encoding='utf-8')
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        
        missing_files = []
        for line in lines:
            # Try to extract file path from the line (more flexible)
            file_path_found = False
            
            # Method 1: Split by colon and check each part
            if ':' in line:
                parts = line.split(':')
                for part in parts:
                    part = part.strip()
                    if part and ('/' in part or '.' in part) and not re.match(r'^\d{4}-\d{2}-\d{2}$', part):
                        # This looks like a file path
                        full_path = test_dir / part
                        if not full_path.exists():
                            missing_files.append(part)
                        file_path_found = True
                        break
            
            # Method 2: Split into words and look for path-like content
            if not file_path_found:
                words = line.split()
                for word in words:
                    word = word.strip()
                    if ('/' in word or '.' in word) and not re.match(r'^\d{4}-\d{2}-\d{2}$', word):
                        # This looks like a file path
                        full_path = test_dir / word
                        if not full_path.exists():
                            missing_files.append(word)
                        file_path_found = True
                        break
            
            # Method 3: Look for path pattern in the entire line
            if not file_path_found:
                # Use regex to find path-like patterns
                path_pattern = r'[a-zA-Z0-9_\-\.\/]+/[a-zA-Z0-9_\-\.\/]+'
                path_matches = re.findall(path_pattern, line)
                for match in path_matches:
                    if '.' in match or '/' in match:
                        full_path = test_dir / match
                        if not full_path.exists():
                            missing_files.append(match)
                        file_path_found = True
                        break
        
        if missing_files:
            print(f"❌ {len(missing_files)} referenced files do not exist")
            print(f"   Examples: {missing_files[:3]}")
            return False
        
        print("✅ All referenced file paths exist")
        return True
        
    except Exception as e:
        print(f"❌ Error checking file paths: {e}")
        return False

def main():
    """Main verification function."""
    test_dir = get_test_directory()
    print("🔍 Verifying Desktop Timeline Extraction Task...")
    
    # Define verification steps
    verification_steps = [
        ("Timeline File Exists", verify_timeline_file_exists),
        ("File is Readable", verify_timeline_file_readable),
        ("Correct Line Count", verify_line_count),
        ("Line Format", verify_line_format),
        ("Date Format", verify_date_format),
        ("Chronological Order", verify_chronological_order),
        ("Expected Entries", verify_expected_entries),
        ("No Duplicates", verify_no_duplicates),
        ("File Paths Exist", verify_file_paths_exist),
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
        print("✅ Desktop 2 Timeline Extraction completed correctly!")
        print("🎉 Task verification: PASS")
        sys.exit(0)
    else:
        print("❌ Task verification: FAIL")
        sys.exit(1)

if __name__ == "__main__":
    main()