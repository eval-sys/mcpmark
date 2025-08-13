#!/usr/bin/env python3
"""
Verification script for File Organization by Creation Time Task
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


def get_month_mapping():
    """Return mapping for both numeric and alphabetic month representations."""
    return {
        "07": ["07", "7", "jul", "Jul", "JUL"],
        "08": ["08", "8", "aug", "Aug", "AUG"],
    }


def get_day_mapping():
    """Return mapping for day representations."""
    return {"09": ["09", "9"], "25": ["25"], "26": ["26"], "06": ["06", "6"]}


def get_expected_directory_structure():
    """Return the expected directory structure based on answer.md."""
    return {
        "07": {"09": ["sg.jpg"], "25": ["bus.MOV"], "26": ["road.MOV"]},
        "08": {
            "06": [
                "bear.jpg",
                "bridge.jpg",
                "random_file_1.txt",
                "random_file_2.txt",
                "random_file_3.txt",
            ]
        },
    }


def find_month_directory(test_dir: Path, expected_month: str) -> Path:
    """Find the actual month directory, handling both numeric and alphabetic representations."""
    month_mapping = get_month_mapping()
    valid_month_names = month_mapping.get(expected_month, [expected_month])

    for month_name in valid_month_names:
        month_dir = test_dir / month_name
        if month_dir.exists() and month_dir.is_dir():
            return month_dir

    return None


def find_day_directory(month_dir: Path, expected_day: str) -> Path:
    """Find the actual day directory, handling both numeric representations."""
    day_mapping = get_day_mapping()
    valid_day_names = day_mapping.get(expected_day, [expected_day])

    for day_name in valid_day_names:
        day_dir = month_dir / day_name
        if day_dir.exists() and day_dir.is_dir():
            return day_dir

    return None


def verify_directory_structure(test_dir: Path) -> bool:
    """Verify that the correct directory structure exists."""
    expected_structure = get_expected_directory_structure()

    for expected_month, days in expected_structure.items():
        month_dir = find_month_directory(test_dir, expected_month)
        if month_dir is None:
            valid_names = get_month_mapping().get(expected_month, [expected_month])
            print(f"❌ Month directory not found. Expected one of: {valid_names}")
            return False

        for day, expected_files in days.items():
            day_dir = find_day_directory(month_dir, day)
            if day_dir is None:
                valid_day_names = get_day_mapping().get(day, [day])
                print(
                    f"❌ Day directory '{month_dir.name}/{day}' not found. Expected one of: {valid_day_names}"
                )
                return False
            if not day_dir.is_dir():
                print(
                    f"❌ '{month_dir.name}/{day_dir.name}' exists but is not a directory"
                )
                return False

    print("✅ Directory structure is correct")
    return True


def verify_files_in_directories(test_dir: Path) -> bool:
    """Verify that files are in the correct directories."""
    expected_structure = get_expected_directory_structure()

    for expected_month, days in expected_structure.items():
        month_dir = find_month_directory(test_dir, expected_month)
        if month_dir is None:
            continue  # Already handled in verify_directory_structure

        for day, expected_files in days.items():
            day_dir = find_day_directory(month_dir, day)
            if day_dir is None:
                continue  # Already handled in verify_directory_structure

            # Check that all expected files are in the directory
            missing_files = []
            for filename in expected_files:
                file_path = day_dir / filename
                if not file_path.exists():
                    missing_files.append(filename)

            if missing_files:
                print(
                    f"❌ Missing files in '{month_dir.name}/{day_dir.name}': {missing_files}"
                )
                return False

            # Check that no unexpected files are in the directory (ignore .DS_Store and metadata_analyse.txt)
            actual_files = [f.name for f in day_dir.iterdir() if f.is_file()]
            system_files = [
                ".DS_Store",
                "Thumbs.db",
                ".DS_Store?",
                "._.DS_Store",
                "metadata_analyse.txt",
            ]
            unexpected_files = [
                f
                for f in actual_files
                if f not in expected_files and f not in system_files
            ]

            if unexpected_files:
                print(
                    f"❌ Unexpected files in '{month_dir.name}/{day_dir.name}': {unexpected_files}"
                )
                return False

    print("✅ All files are in correct directories")
    return True


def verify_metadata_analysis_files(test_dir: Path) -> bool:
    """Verify that metadata_analyse.txt files exist and have correct content."""
    expected_structure = get_expected_directory_structure()

    for expected_month, days in expected_structure.items():
        month_dir = find_month_directory(test_dir, expected_month)
        if month_dir is None:
            continue  # Already handled in verify_directory_structure

        for day, expected_files in days.items():
            day_dir = find_day_directory(month_dir, day)
            if day_dir is None:
                continue  # Already handled in verify_directory_structure

            metadata_file = day_dir / "metadata_analyse.txt"

            if not metadata_file.exists():
                print(
                    f"❌ metadata_analyse.txt not found in '{month_dir.name}/{day_dir.name}'"
                )
                return False

            try:
                content = metadata_file.read_text().strip()
                lines = content.split("\n")

                # Check that there are exactly 2 lines
                if len(lines) != 2:
                    print(
                        f"❌ metadata_analyse.txt in '{month_dir.name}/{day_dir.name}' has {len(lines)} lines, expected 2"
                    )
                    return False

                # Check each line - more flexible verification
                for line_num, line in enumerate(lines, 1):
                    line_lower = line.lower()

                    # Check filename based on expected_month and day
                    expected_filename = None
                    if expected_month == "07" and day == "09":
                        expected_filename = "sg.jpg"
                    elif expected_month == "07" and day == "25":
                        expected_filename = "bus.mov"
                    elif expected_month == "07" and day == "26":
                        expected_filename = "road.mov"
                    elif expected_month == "08" and day == "06":
                        # For 08/06, check if it's one of the expected files
                        if line_num == 1:  # First line should be bear.jpg
                            expected_filename = "bear.jpg"
                        else:  # Second line should be one of the random files
                            expected_filenames = [
                                "random_file_1.txt",
                                "random_file_2.txt",
                                "random_file_3.txt",
                            ]
                            if not any(
                                filename in line_lower
                                for filename in expected_filenames
                            ):
                                print(
                                    f"❌ Line {line_num} in '{month_dir.name}/{day_dir.name}' should contain one of {expected_filenames}: {line}"
                                )
                                return False
                            continue  # Skip other checks for this line

                    if expected_filename and expected_filename not in line_lower:
                        print(
                            f"❌ Line {line_num} in '{month_dir.name}/{day_dir.name}' should contain '{expected_filename}': {line}"
                        )
                        return False

                    # Check month letters
                    month_letters = None
                    if expected_month == "07":
                        month_letters = ["jul", "7"]
                    elif expected_month == "08":
                        month_letters = ["aug", "8"]

                    if month_letters and not any(
                        letter in line_lower for letter in month_letters
                    ):
                        print(
                            f"❌ Line {line_num} in '{month_dir.name}/{day_dir.name}' should contain month letters: {line}"
                        )
                        return False

                    # Check year (2025)
                    if "2025" not in line_lower:
                        print(
                            f"❌ Line {line_num} in '{month_dir.name}/{day_dir.name}' should contain '2025': {line}"
                        )
                        return False

                    # Check day number - support both formats
                    valid_day_names = get_day_mapping().get(day, [day])
                    if not any(day_name in line_lower for day_name in valid_day_names):
                        print(
                            f"❌ Line {line_num} in '{month_dir.name}/{day_dir.name}' should contain day '{day}' (or {valid_day_names}): {line}"
                        )
                        return False

            except Exception as e:
                print(
                    f"❌ Error reading metadata_analyse.txt in '{month_dir.name}/{day_dir.name}': {e}"
                )
                return False

    print("✅ All metadata_analyse.txt files are correct")
    return True


def verify_no_files_in_root(test_dir: Path) -> bool:
    """Verify that no files remain in the root test directory."""
    root_files = [f for f in test_dir.iterdir() if f.is_file()]

    # Filter out system files that are commonly present
    system_files = [".DS_Store", "Thumbs.db", ".DS_Store?", "._.DS_Store"]
    non_system_files = [f for f in root_files if f.name not in system_files]

    if non_system_files:
        print(
            f"❌ Files still present in root directory: {[f.name for f in non_system_files]}"
        )
        return False

    print("✅ No files remain in root directory")
    return True


def verify_total_file_count(test_dir: Path) -> bool:
    """Verify that all original files are accounted for."""
    expected_structure = get_expected_directory_structure()
    total_expected = sum(
        len(files) for days in expected_structure.values() for files in days.values()
    )

    total_actual = 0
    for expected_month, days in expected_structure.items():
        month_dir = find_month_directory(test_dir, expected_month)
        if month_dir is None:
            continue
        for day in days:
            day_dir = find_day_directory(month_dir, day)
            if day_dir and day_dir.exists():
                # Count only non-system files
                system_files = [
                    ".DS_Store",
                    "Thumbs.db",
                    ".DS_Store?",
                    "._.DS_Store",
                    "metadata_analyse.txt",
                ]
                files_in_dir = [
                    f
                    for f in day_dir.iterdir()
                    if f.is_file() and f.name not in system_files
                ]
                total_actual += len(files_in_dir)

    if total_actual != total_expected:
        print(f"❌ Expected {total_expected} files total, found {total_actual}")
        return False

    print(f"✅ Total file count is correct: {total_actual}")
    return True


def main():
    """Main verification function."""
    try:
        test_dir = get_test_directory()
        # test_dir = Path("/Users/chenlingjun/Desktop/MCP/MCPMark/.mcpmark_backups/backup_filesystem_file_property_time_classification_91935")
        print(f"🔍 Verifying file organization by creation time in: {test_dir}")

        # Run all verification checks
        checks = [
            ("Directory structure", verify_directory_structure),
            ("Files in directories", verify_files_in_directories),
            ("Metadata analysis files", verify_metadata_analysis_files),
            ("No files in root", verify_no_files_in_root),
            ("Total file count", verify_total_file_count),
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
