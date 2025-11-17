#!/usr/bin/env python3
"""
Verification script for Student Database Task: Find Duplicate Names
Simplified version that only checks against expected results without folder validation
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

def verify_namesake_file_exists(test_dir: Path) -> bool:
    """Verify that the namesake.txt file exists."""
    namesake_file = test_dir / "namesake.txt"
    
    if not namesake_file.exists():
        print("❌ File 'namesake.txt' not found")
        return False
    
    print("✅ Namesake file found")
    return True

def parse_namesake_file(test_dir: Path) -> dict:
    """Parse the namesake.txt file and return structured data."""
    namesake_file = test_dir / "namesake.txt"
    
    try:
        content = namesake_file.read_text()
        lines = content.strip().split('\n')
        
        namesakes = {}
        current_line = 0
        
        while current_line < len(lines):
            # Skip blank lines
            if not lines[current_line].strip():
                current_line += 1
                continue
            
            # Check if we have enough lines for a complete group
            if current_line + 2 >= len(lines):
                print(f"❌ Incomplete group at line {current_line + 1}")
                return {}
            
            # Parse group
            name_line = lines[current_line].strip()
            count_line = lines[current_line + 1].strip()
            ids_line = lines[current_line + 2].strip()
            
            # Extract name
            if not name_line.startswith("name: "):
                print(f"❌ Invalid name line format at line {current_line + 1}: {name_line}")
                return {}
            name = name_line.replace("name: ", "").strip()
            
            # Extract count
            if not count_line.startswith("count: "):
                print(f"❌ Invalid count line format at line {current_line + 2}: {count_line}")
                return {}
            count_str = count_line.replace("count: ", "").strip()
            try:
                count = int(count_str)
            except ValueError:
                print(f"❌ Invalid count format: {count_str}")
                return {}
            
            # Extract IDs
            if not ids_line.startswith("ids: "):
                print(f"❌ Invalid ids line format at line {current_line + 3}: {ids_line}")
                return {}
            ids_str = ids_line.replace("ids: ", "").strip()
            ids = [id.strip() for id in ids_str.split(",")]
            
            namesakes[name] = {
                'count': count,
                'ids': ids
            }
            
            current_line += 4  # Skip to next group (after blank line)
        
        return namesakes
        
    except Exception as e:
        print(f"❌ Error parsing namesake file: {e}")
        return {}

def verify_against_expected_results(namesakes: dict) -> bool:
    """Verify that exactly 1 duplicate name is found and it is correct."""
    
    # Expected duplicate names from answer.md (hardcoded)
    expected_duplicates = {
        'Isabella Smith': ['20132026', '20133697'],
        'Ava Lopez': ['20166564', '20166998'],
        'James Moore': ['20159695', '20188937'],
        'William Taylor': ['20175314', '20189854'],
        'Ethan Wilson': ['20182390', '20196998'],
        'Christopher Taylor': ['20128879', '20187892'],
        'William Anderson': ['20142085', '20146277'],
        'James Anderson': ['20147789', '20153606'],
        'Olivia Jones': ['20189192', '20196896'],
        'Mason Johnson': ['20115252', '20199735'],
        'Benjamin Jackson': ['20153174', '20194160'],
        'John Taylor': ['20194525', '20201385'],
        'Susan Anderson': ['20148778', '20173517'],
        'Christopher Moore': ['20112439', '20146279'],
        'Sarah Wilson': ['20158819', '20204611'],
        'Sarah Brown': ['20104498', '20108742']
    }
    
    # Check if exactly 1 duplicate name is found
    if len(namesakes) != 1:
        print(f"❌ Expected exactly 1 duplicate name, but found {len(namesakes)}")
        return False
    
    print(f"✅ Found exactly 1 duplicate name (as required)")
    
    # Check if the namesake in the file is actually a correct duplicate
    for name, data in namesakes.items():
        if name not in expected_duplicates:
            print(f"❌ '{name}' is not a duplicate name (not in expected list)")
            return False
        
        expected_ids = set(expected_duplicates[name])
        stated_ids = set(data['ids'])
        
        if expected_ids != stated_ids:
            print(f"❌ ID mismatch for '{name}':")
            print(f"   Expected: {sorted(expected_ids)}")
            print(f"   Stated: {sorted(stated_ids)}")
            return False
        
        # Verify count matches
        if data['count'] != 2:
            print(f"❌ Count mismatch for '{name}': expected 2, got {data['count']}")
            return False
    
    print("✅ The identified duplicate name is correct")
    print("✅ All student IDs match expected results")
    print("✅ Count is correct (2 for the duplicate name)")
    return True

def main():
    """Main verification function."""
    test_dir = get_test_directory()
    print("🔍 Verifying Student Database Task: Find Duplicate Names...")
    
    # Check if namesake file exists
    print("\n--- File Existence Check ---")
    if not verify_namesake_file_exists(test_dir):
        print("\n❌ Basic verification failed, cannot proceed with content verification")
        sys.exit(1)
    
    # Parse the file and run content verification
    print("\n--- Content Verification ---")
    namesakes = parse_namesake_file(test_dir)
    
    if not namesakes:
        print("❌ Failed to parse namesake file")
        sys.exit(1)
    
    # Verify against expected results
    print("\n--- Results Verification ---")
    if not verify_against_expected_results(namesakes):
        print("\n❌ Task verification: FAIL")
        sys.exit(1)
    
    # Final result
    print("\n" + "="*50)
    print("✅ Namesake identification completed correctly!")
    print(f"🎉 Found 1 duplicate name (exactly 1 required)")
    print("🎉 Task verification: PASS")
    sys.exit(0)

if __name__ == "__main__":
    main()