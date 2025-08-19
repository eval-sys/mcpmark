#!/usr/bin/env python3
"""
Verification script for Student Database Task: English Talent Recruitment
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

def verify_qualified_students_file_exists(test_dir: Path) -> bool:
    """Verify that the qualified_students.txt file exists."""
    answer_file = test_dir / "qualified_students.txt"
    
    if not answer_file.exists():
        print("❌ File 'qualified_students.txt' not found")
        return False
    
    print("✅ Qualified students file found")
    return True

def verify_file_format(test_dir: Path) -> bool:
    """Verify that the qualified_students.txt file has the correct format."""
    answer_file = test_dir / "qualified_students.txt"
    
    try:
        content = answer_file.read_text()
        lines = content.strip().split('\n')
        
        if not lines:
            print("❌ File is empty")
            return False
        
        # Check if content follows the expected pattern
        # Each student should have 3 lines: name, id, email
        # Students should be separated by blank lines
        current_line = 0
        student_count = 0
        
        while current_line < len(lines):
            # Skip blank lines
            if not lines[current_line].strip():
                current_line += 1
                continue
            
            # Check if we have enough lines for a complete student
            if current_line + 2 >= len(lines):
                print(f"❌ Incomplete student entry at line {current_line + 1}")
                return False
            
            # Verify name line format
            if not lines[current_line].strip().startswith("name: "):
                print(f"❌ Invalid name line format at line {current_line + 1}: {lines[current_line]}")
                return False
            
            # Verify id line format
            if not lines[current_line + 1].strip().startswith("id: "):
                print(f"❌ Invalid id line format at line {current_line + 2}: {lines[current_line + 1]}")
                return False
            
            # Verify email line format
            if not lines[current_line + 2].strip().startswith("email: "):
                print(f"❌ Invalid email line format at line {current_line + 3}: {lines[current_line + 2]}")
                return False
            
            student_count += 1
            current_line += 3
            
            # Check for blank line separator (except for the last student)
            if current_line < len(lines) and lines[current_line].strip():
                print(f"❌ Missing blank line separator after student {student_count}")
                return False
            
            current_line += 1
        
        if student_count == 0:
            print("❌ No valid student entries found")
            return False
        
        print(f"✅ File format is correct with {student_count} students")
        return True
        
    except Exception as e:
        print(f"❌ Error reading qualified students file: {e}")
        return False

def parse_qualified_students_file(test_dir: Path) -> list:
    """Parse the qualified_students.txt file and return structured data."""
    answer_file = test_dir / "qualified_students.txt"
    
    try:
        content = answer_file.read_text()
        lines = content.strip().split('\n')
        
        students = []
        current_line = 0
        
        while current_line < len(lines):
            # Skip blank lines
            if not lines[current_line].strip():
                current_line += 1
                continue
            
            # Parse student entry
            name_line = lines[current_line].strip()
            id_line = lines[current_line + 1].strip()
            email_line = lines[current_line + 2].strip()
            
            # Extract name
            name = name_line.replace("name: ", "").strip()
            
            # Extract id
            student_id = id_line.replace("id: ", "").strip()
            
            # Extract email
            email = email_line.replace("email: ", "").strip()
            
            students.append({
                'name': name,
                'id': student_id,
                'email': email
            })
            
            current_line += 4  # Skip to next student (after blank line)
        
        return students
        
    except Exception as e:
        print(f"❌ Error parsing qualified students file: {e}")
        return []

def verify_student_count(students: list) -> bool:
    """Verify that exactly 19 students are found."""
    expected_count = 19
    actual_count = len(students)
    
    if actual_count != expected_count:
        print(f"❌ Expected {expected_count} students, but found {actual_count}")
        return False
    
    print(f"✅ Found exactly {expected_count} students")
    return True

def verify_expected_students(students: list) -> bool:
    """Verify that all expected students are present with correct details."""
    # Expected students from answer.md
    expected_students = {
        'James Smith': {'id': '20177389', 'email': 'james.smith30@outlook.com'},
        'Ava Lopez': {'id': '20166998', 'email': 'ava.lopez67@outlook.com'},
        'James Anderson': {'id': '20153606', 'email': 'james.anderson71@yahoo.com'},
        'Benjamin Anderson': {'id': '20136681', 'email': 'benjamin.anderson37@qq.com'},
        'Sarah Wilson': {'id': '20158819', 'email': 'sarah.wilson96@outlook.com'},
        'Isabella Davis': {'id': '20101701', 'email': 'isabella.davis89@gmail.com'},
        'James Moore': {'id': '20188937', 'email': 'james.moore62@gmail.com'},
        'Harper Williams': {'id': '20157943', 'email': 'harper.williams38@163.com'},
        'Noah Smith': {'id': '20132669', 'email': 'noah.smith45@163.com'},
        'Emma Thomas': {'id': '20109144', 'email': 'emma.thomas68@163.com'},
        'Mary Brown': {'id': '20199583', 'email': 'mary.brown27@yahoo.com'},
        'John Jones': {'id': '20201800', 'email': 'john.jones46@gmail.com'},
        'Mia Anderson': {'id': '20162542', 'email': 'mia.anderson3@outlook.com'},
        'Barbara Davis': {'id': '20126203', 'email': 'barbara.davis67@163.com'},
        'Thomas Brown': {'id': '20119528', 'email': 'thomas.brown43@163.com'},
        'Susan Anderson': {'id': '20148778', 'email': 'susan.anderson16@163.com'},
        'Mary Garcia': {'id': '20174369', 'email': 'mary.garcia58@gmail.com'},
        'Richard Wilson': {'id': '20174207', 'email': 'richard.wilson39@outlook.com'},
        'Joseph Lopez': {'id': '20191265', 'email': 'joseph.lopez93@yahoo.com'}
    }
    
    # Check if all expected students are present
    found_students = set()
    for student in students:
        found_students.add(student['name'])
    
    missing_students = set(expected_students.keys()) - found_students
    if missing_students:
        print(f"❌ Missing expected students: {missing_students}")
        return False
    
    # Check if all found students are expected
    unexpected_students = found_students - set(expected_students.keys())
    if unexpected_students:
        print(f"❌ Unexpected students found: {unexpected_students}")
        return False
    
    # Check if student details match exactly
    for student in students:
        expected = expected_students[student['name']]
        if student['id'] != expected['id']:
            print(f"❌ ID mismatch for {student['name']}: expected {expected['id']}, got {student['id']}")
            return False
        if student['email'] != expected['email']:
            print(f"❌ Email mismatch for {student['name']}: expected {expected['email']}, got {student['email']}")
            return False
    
    print("✅ All expected students are present with correct details")
    return True

def main():
    """Main verification function."""
    test_dir = get_test_directory()
    print("🔍 Verifying Student Database Task: English Talent Recruitment...")
    
    # Define verification steps
    verification_steps = [
        ("Qualified Students File Exists", verify_qualified_students_file_exists),
        ("File Format", verify_file_format),
    ]
    
    # Run basic verification steps first
    all_passed = True
    for step_name, verify_func in verification_steps:
        print(f"\n--- {step_name} ---")
        if not verify_func(test_dir):
            all_passed = False
            break
    
    if not all_passed:
        print("\n❌ Basic verification failed, cannot proceed with content verification")
        sys.exit(1)
    
    # Parse the file and run content verification
    print("\n--- Content Verification ---")
    students = parse_qualified_students_file(test_dir)
    
    if not students:
        print("❌ Failed to parse qualified students file")
        sys.exit(1)
    
    content_verification_steps = [
        ("Student Count", lambda: verify_student_count(students)),
        ("Expected Students", lambda: verify_expected_students(students)),
    ]
    
    for step_name, verify_func in content_verification_steps:
        print(f"\n--- {step_name} ---")
        if not verify_func():
            all_passed = False
    
    # Final result
    print("\n" + "="*50)
    if all_passed:
        print("✅ English talent recruitment completed correctly!")
        print(f"🎉 Found exactly {len(students)} qualified students")
        print("🎉 Task verification: PASS")
        sys.exit(0)
    else:
        print("❌ Task verification: FAIL")
        sys.exit(1)

if __name__ == "__main__":
    main()