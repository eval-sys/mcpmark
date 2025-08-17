#!/usr/bin/env python3
"""
Verification script for Desktop File Organization Task
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

def verify_folder_structure(test_dir: Path) -> bool:
    """Verify that all required folders exist."""
    required_folders = ["work", "life", "archives", "temp", "others"]
    missing_folders = []
    
    for folder in required_folders:
        folder_path = test_dir / folder
        if not folder_path.exists() or not folder_path.is_dir():
            missing_folders.append(folder)
    
    if missing_folders:
        print(f"❌ Missing required folders: {missing_folders}")
        return False
    
    print("✅ All required folders exist")
    return True

def verify_work_folder_files(test_dir: Path) -> bool:
    """Verify that work folder contains the required files."""
    work_dir = test_dir / "work"
    required_files = [
        "client_list.csv",
        "timesheet.csv", 
        "experiment_results.txt",
        "budget_tracker.csv"
    ]
    
    missing_files = []
    for file_name in required_files:
        file_path = work_dir / file_name
        if not file_path.exists():
            missing_files.append(file_name)
    
    if missing_files:
        print(f"❌ Missing required files in work/ folder: {missing_files}")
        return False
    
    # Count total files in work folder for info
    total_files = len([f for f in work_dir.iterdir() if f.is_file()])
    print(f"✅ All required files found in work/ folder (total: {total_files} files)")
    return True

def verify_life_folder_files(test_dir: Path) -> bool:
    """Verify that life folder contains the required files."""
    life_dir = test_dir / "life"
    required_files = [
        "contacts.csv",
        "budget.csv",
        "important_dates.csv",
        "expenses.csv",
        "fitness_log.csv",
        "price_comparisons.csv",
        "book_list.txt",
        "bookmark_export.txt",
        "emergency_contacts.txt"
    ]
    
    missing_files = []
    for file_name in required_files:
        file_path = life_dir / file_name
        if not file_path.exists():
            missing_files.append(file_name)
    
    if missing_files:
        print(f"❌ Missing required files in life/ folder: {missing_files}")
        return False
    
    # Count total files in life folder for info
    total_files = len([f for f in life_dir.iterdir() if f.is_file()])
    print(f"✅ All required files found in life/ folder (total: {total_files} files)")
    return True

def verify_archives_folder_files(test_dir: Path) -> bool:
    """Verify that archives folder contains the required files."""
    archives_dir = test_dir / "archives"
    required_files = [
        "backup_contacts.csv",
        "tax_documents_2022.csv",
        "correspondence_2023.txt",
        "tax_info_2023.csv"
    ]
    
    missing_files = []
    for file_name in required_files:
        file_path = archives_dir / file_name
        if not file_path.exists():
            missing_files.append(file_name)
    
    if missing_files:
        print(f"❌ Missing required files in archives/ folder: {missing_files}")
        return False
    
    # Count total files in archives folder for info
    total_files = len([f for f in archives_dir.iterdir() if f.is_file()])
    print(f"✅ All required files found in archives/ folder (total: {total_files} files)")
    return True

def verify_temp_folder_files(test_dir: Path) -> bool:
    """Verify that temp folder contains the required files."""
    temp_dir = test_dir / "temp"
    required_files = [
        "test_data.csv",
        "draft_letter.txt"
    ]
    
    missing_files = []
    for file_name in required_files:
        file_path = temp_dir / file_name
        if not file_path.exists():
            missing_files.append(file_name)
    
    if missing_files:
        print(f"❌ Missing required files in temp/ folder: {missing_files}")
        return False
    
    # Count total files in temp folder for info
    total_files = len([f for f in temp_dir.iterdir() if f.is_file()])
    print(f"✅ All required files found in temp/ folder (total: {total_files} files)")
    return True

def verify_others_folder_files(test_dir: Path) -> bool:
    """Verify that others folder exists and can contain any files."""
    others_dir = test_dir / "others"
    
    if not others_dir.exists() or not others_dir.is_dir():
        print("❌ others/ folder not found")
        return False
    
    # Count files in others folder for info
    total_files = len([f for f in others_dir.iterdir() if f.is_file()])
    print(f"✅ others/ folder exists (contains {total_files} files)")
    return True

def verify_required_files_in_correct_folders(test_dir: Path) -> bool:
    """Verify that all 19 required files are in their correct designated folders."""
    # Define the mapping of required files to their correct folders
    required_file_mapping = {
        "work": [
            "client_list.csv",
            "timesheet.csv", 
            "experiment_results.txt",
            "budget_tracker.csv"
        ],
        "life": [
            "contacts.csv",
            "budget.csv",
            "important_dates.csv",
            "expenses.csv",
            "fitness_log.csv",
            "price_comparisons.csv",
            "book_list.txt",
            "bookmark_export.txt",
            "emergency_contacts.txt"
        ],
        "archives": [
            "backup_contacts.csv",
            "tax_documents_2022.csv",
            "correspondence_2023.txt",
            "tax_info_2023.csv"
        ],
        "temp": [
            "test_data.csv",
            "draft_letter.txt"
        ]
    }
    
    missing_files = []
    
    # Check each required file is in its correct folder
    for folder, files in required_file_mapping.items():
        folder_path = test_dir / folder
        for file_name in files:
            file_path = folder_path / file_name
            if not file_path.exists():
                missing_files.append(f"{folder}/{file_name}")
    
    if missing_files:
        print(f"❌ Missing required files: {missing_files}")
        return False
    
    print("✅ All 19 required files are in their correct designated folders")
    return True

def verify_no_duplicate_required_files(test_dir: Path) -> bool:
    """Verify that the 19 required files are not duplicated across folders."""
    required_files = [
        "client_list.csv", "timesheet.csv", "experiment_results.txt", "budget_tracker.csv",
        "contacts.csv", "budget.csv", "important_dates.csv", "expenses.csv", "fitness_log.csv",
        "price_comparisons.csv", "book_list.txt", "bookmark_export.txt", "emergency_contacts.txt",
        "backup_contacts.csv", "tax_documents_2022.csv", "correspondence_2023.txt", "tax_info_2023.csv",
        "test_data.csv", "draft_letter.txt"
    ]
    
    # Check for duplicates of required files
    file_locations = {}
    duplicates = []
    
    for folder in ["work", "life", "archives", "temp", "others"]:
        folder_path = test_dir / folder
        if folder_path.exists() and folder_path.is_dir():
            for file_path in folder_path.iterdir():
                if file_path.is_file() and file_path.name in required_files:
                    if file_path.name in file_locations:
                        duplicates.append(f"{file_path.name} (in {file_locations[file_path.name]} and {folder}/)")
                    else:
                        file_locations[file_path.name] = f"{folder}/"
    
    if duplicates:
        print(f"❌ Duplicate required files found: {duplicates}")
        return False
    
    print("✅ No duplicate required files found")
    return True

def main():
    """Main verification function."""
    test_dir = get_test_directory()
    print("🔍 Verifying Desktop File Organization Task...")
    
    # Define verification steps
    verification_steps = [
        ("Folder Structure", verify_folder_structure),
        ("Required Files in Work Folder", verify_work_folder_files),
        ("Required Files in Life Folder", verify_life_folder_files),
        ("Required Files in Archives Folder", verify_archives_folder_files),
        ("Required Files in Temp Folder", verify_temp_folder_files),
        ("Others Folder Exists", verify_others_folder_files),
        ("All Required Files in Correct Folders", verify_required_files_in_correct_folders),
        ("No Duplicate Required Files", verify_no_duplicate_required_files),
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
        print("✅ Desktop file organization task completed successfully!")
        print("🎉 All 19 required files are correctly placed in their designated folders")
        print("📊 Summary:")
        print("   - work/ folder: 4 required files")
        print("   - life/ folder: 9 required files") 
        print("   - archives/ folder: 4 required files")
        print("   - temp/ folder: 2 required files")
        print("   - others/ folder: can contain any files")
        print("   - Total required files: 19")
        print("   - Note: Other files can be placed in any folder")
        sys.exit(0)
    else:
        print("❌ Desktop file organization task verification: FAIL")
        print("Please check the errors above and ensure all 19 required files are in their correct locations")
        sys.exit(1)

if __name__ == "__main__":
    main()