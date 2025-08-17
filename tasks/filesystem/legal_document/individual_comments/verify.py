#!/usr/bin/env python3
"""
Verification script for Legal Document Individual Comments Task
"""

import sys
from pathlib import Path
import csv
import os

def get_test_directory() -> Path:
    """Get the test directory from FILESYSTEM_TEST_DIR env var."""
    test_root = os.environ.get("FILESYSTEM_TEST_DIR")
    if not test_root:
        raise ValueError("FILESYSTEM_TEST_DIR environment variable is required")
    return Path(test_root)

def verify_output_file_exists(test_dir: Path) -> bool:
    """Verify that the individual_comment.csv file exists."""
    output_file = test_dir / "individual_comment.csv"
    
    if not output_file.exists():
        print("❌ File 'individual_comment.csv' not found")
        return False
    
    print("✅ Output file 'individual_comment.csv' found")
    return True

def verify_csv_format(test_dir: Path) -> bool:
    """Verify that the CSV file has the correct format."""
    output_file = test_dir / "individual_comment.csv"
    
    try:
        with open(output_file, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            rows = list(reader)
            
            if not rows:
                print("❌ CSV file is empty")
                return False
            
            # Check if there are at least 2 rows (header + data)
            if len(rows) < 2:
                print("❌ CSV file has insufficient rows")
                return False
            
            # Check if header row has correct number of columns
            header = rows[0]
            if len(header) != 7:  # First column (can be anything) + 6 clauses
                print(f"❌ Header row has incorrect number of columns: {len(header)}, expected 7")
                return False
            
            # Check if data rows have correct number of columns
            for i, row in enumerate(rows[1:], 1):
                if len(row) != 7:
                    print(f"❌ Data row {i} has incorrect number of columns: {len(row)}, expected 7")
                    return False
            
            print("✅ CSV format is correct")
            return True
            
    except Exception as e:
        print(f"❌ Error reading CSV file: {e}")
        return False

def verify_csv_content(test_dir: Path) -> bool:
    """Verify that the CSV content matches the expected answer exactly."""
    output_file = test_dir / "individual_comment.csv"
    
    try:
        with open(output_file, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            rows = list(reader)
            
            # Expected data based on answer.csv
            expected_data = {
                "Bill Harvey": ["0", "2", "3", "1", "1", "1"],
                "Michelle Jackson": ["0", "1", "2", "1", "1", "1"],
                "David Russel": ["2", "1", "1", "2", "1", "1"],
                "Tony Taylor": ["2", "0", "1", "2", "1", "1"]
            }
            
            # Expected header columns (excluding first column which can be anything)
            expected_header_columns = ["1.1", "1.3", "4.6", "4.16", "6.8", "6.16"]
            
            # Verify header has correct number of columns
            header = rows[0]
            if len(header) != 7:  # First column + 6 clauses
                print(f"❌ Header row has incorrect number of columns: {len(header)}, expected 7")
                return False
            
            # Check if all expected clause columns are present (allow order to be different)
            # Allow first column to be anything, so we check columns 1-6
            header_clauses = header[1:7]
            missing_clauses = []
            for expected_clause in expected_header_columns:
                if expected_clause not in header_clauses:
                    missing_clauses.append(expected_clause)
            
            if missing_clauses:
                print(f"❌ Missing expected clause columns: {missing_clauses}")
                return False
            
            # Check if there are extra clause columns
            extra_clauses = []
            for clause in header_clauses:
                if clause not in expected_header_columns:
                    extra_clauses.append(clause)
            
            if extra_clauses:
                print(f"❌ Unexpected extra clause columns: {extra_clauses}")
                return False
            
            # Create a mapping from expected clause order to actual column indices
            clause_mapping = {}
            for i, clause in enumerate(header_clauses):
                if clause in expected_header_columns:
                    clause_mapping[clause] = i
            
            # Parse the CSV data into a dictionary with correct column mapping
            csv_data = {}
            for row in rows[1:]:
                if len(row) >= 7:
                    name = row[0]
                    # Map values according to the expected clause order
                    values = []
                    for expected_clause in expected_header_columns:
                        col_index = clause_mapping[expected_clause] + 1  # +1 because we skip first column
                        values.append(row[col_index])
                    csv_data[name] = values
            
            # Check if all expected names are present
            missing_names = []
            for expected_name in expected_data:
                if expected_name not in csv_data:
                    missing_names.append(expected_name)
            
            if missing_names:
                print(f"❌ Missing expected names: {missing_names}")
                return False
            
            # Check if there are extra names
            extra_names = []
            for name in csv_data:
                if name not in expected_data:
                    extra_names.append(name)
            
            if extra_names:
                print(f"❌ Unexpected extra names: {extra_names}")
                return False
            
            # Check values for each person
            for name, expected_values in expected_data.items():
                actual_values = csv_data[name]
                
                if actual_values != expected_values:
                    print(f"❌ Values mismatch for {name}:")
                    print(f"   Expected: {expected_values}")
                    print(f"   Got:      {actual_values}")
                    return False
            
            print("✅ CSV content matches expected answer exactly")
            return True
            
    except Exception as e:
        print(f"❌ Error verifying CSV content: {e}")
        return False

def verify_data_accuracy(test_dir: Path) -> bool:
    """Verify that the data values are accurate (all values are non-negative integers)."""
    output_file = test_dir / "individual_comment.csv"
    
    try:
        with open(output_file, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            rows = list(reader)
            
            # Skip header row
            for i, row in enumerate(rows[1:], 1):
                if len(row) >= 7:
                    name = row[0]
                    values = row[1:7]
                    
                    for j, value in enumerate(values, 1):
                        try:
                            int_val = int(value)
                            if int_val < 0:
                                print(f"❌ Row {i}, column {j}: negative value '{value}' for {name}")
                                return False
                        except ValueError:
                            print(f"❌ Row {i}, column {j}: non-integer value '{value}' for {name}")
                            return False
            
            print("✅ All data values are valid non-negative integers")
            return True
            
    except Exception as e:
        print(f"❌ Error verifying data accuracy: {e}")
        return False

def verify_file_location(test_dir: Path) -> bool:
    """Verify that the file is in the main directory (not in a subdirectory)."""
    output_file = test_dir / "individual_comment.csv"
    
    if output_file.exists():
        print("✅ File is located in the main directory")
        return True
    else:
        print("❌ File is not in the main directory")
        return False

def main():
    """Main verification function."""
    test_dir = get_test_directory()
    print("🔍 Verifying Legal Document Individual Comments Task...")
    
    # Define verification steps
    verification_steps = [
        ("Output File Exists", verify_output_file_exists),
        ("CSV Format", verify_csv_format),
        ("CSV Content", verify_csv_content),
        ("Data Accuracy", verify_data_accuracy),
        ("File Location", verify_file_location),
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
        print("✅ Legal document individual comments task completed correctly!")
        print("🎉 Task verification: PASS")
        sys.exit(0)
    else:
        print("❌ Task verification: FAIL")
        sys.exit(1)

if __name__ == "__main__":
    main()