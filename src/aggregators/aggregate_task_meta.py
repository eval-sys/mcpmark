#!/usr/bin/env python3
"""
Task Meta Aggregator for MCPBench
Aggregates all meta.json files from the tasks directory into a single JSON file.
"""

import json
import os
import argparse
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Any, Set


def find_all_meta_files(tasks_root: Path = Path("tasks")) -> List[Path]:
    """Find all meta.json files in the tasks directory"""
    meta_files = []
    for root, dirs, files in os.walk(tasks_root):
        if "meta.json" in files:
            meta_files.append(Path(root) / "meta.json")
    return meta_files


def parse_meta_file(meta_path: Path) -> Dict[str, Any]:
    """Parse a single meta.json file"""
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error parsing {meta_path}: {e}")
        return {}


def aggregate_task_meta(meta_files: List[Path]) -> Dict[str, Any]:
    """Aggregate all meta.json files into the required structure"""
    all_data = []
    categories_dict = {}  # Use dict to track unique categories
    all_tags_set = set()  # Set to collect all unique tags

    for meta_path in meta_files:
        meta_data = parse_meta_file(meta_path)
        if meta_data:
            # Exclude model_results field from aggregated data
            filtered_data = {k: v for k, v in meta_data.items() if k != "model_results"}
            all_data.append(filtered_data)

            # Collect categories using category_id and category_name
            if "category_id" in filtered_data and "category_name" in filtered_data:
                category_id = filtered_data["category_id"]
                category_name = filtered_data["category_name"]
                # Use category_id as the key to ensure uniqueness
                categories_dict[category_id] = {
                    "id": category_id,
                    "name": category_name,
                }

            # Collect all unique tags
            if "tags" in filtered_data and isinstance(filtered_data["tags"], list):
                all_tags_set.update(filtered_data["tags"])

    # Convert categories dict to sorted list
    categories_list = sorted(categories_dict.values(), key=lambda x: x["id"])

    # Convert tags set to sorted list
    all_tags_list = sorted(all_tags_set)

    return {
        "data": all_data,
        "count": len(all_data),
        "categories": categories_list,
        "tags": all_tags_list,
    }


def create_individual_task_files(meta_files: List[Path]) -> List[Dict[str, Any]]:
    """Create individual task JSON files with instruction and verify content"""
    task_files = []

    for meta_path in meta_files:
        meta_data = parse_meta_file(meta_path)
        if not meta_data or "task_id" not in meta_data:
            continue

        # Get the task directory
        task_dir = meta_path.parent

        # Read description.md if exists
        description_path = task_dir / "description.md"
        instruction_content = ""
        if description_path.exists():
            try:
                with open(description_path, "r", encoding="utf-8") as f:
                    instruction_content = f.read()
            except Exception as e:
                print(f"Warning: Could not read {description_path}: {e}")

        # Read verify.py if exists
        verify_path = task_dir / "verify.py"
        verify_content = ""
        if verify_path.exists():
            try:
                with open(verify_path, "r", encoding="utf-8") as f:
                    verify_content = f.read()
            except Exception as e:
                print(f"Warning: Could not read {verify_path}: {e}")

        # Create combined task data, excluding model_results
        task_data = {
            k: v for k, v in meta_data.items() if k != "model_results"
        }
        task_data["instruction"] = instruction_content
        task_data["verify"] = verify_content

        task_files.append({"filename": f"{meta_data['task_id']}.json", "data": task_data})

    return task_files


def push_to_file(
    output_file: Path,
    data: Dict[str, Any],
    task_files: List[Dict[str, Any]] = None,
    push_to_repo: bool = False,
) -> bool:
    """Save the aggregated data to file and optionally push to repo"""
    try:
        # Create parent directory if it doesn't exist
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Write the aggregated data
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"✅ Task meta data saved to: {output_file}")
        print(f"📊 Summary:")
        print(f"   - Total tasks with meta.json: {data['count']}")
        print(f"   - Categories: {len(data['categories'])}")
        print(f"   - Unique tags: {len(data['tags'])}")

        if push_to_repo:
            return push_to_experiments_repo(output_file, task_files)

        return True

    except Exception as e:
        print(f"❌ Error saving file: {e}")
        return False


def push_to_experiments_repo(
    file_path: Path, task_files: List[Dict[str, Any]] = None
) -> bool:
    """Push the task meta file and individual task files to eval-sys/mcpmark-experiments repo"""
    if not file_path.exists():
        print("⚠️  File does not exist")
        return False

    repo_url = "https://github.com/eval-sys/mcpmark-experiments.git"
    temp_dir = Path("./temp_experiments_repo")

    try:
        print(f"\n🔄 Preparing to push task meta to experiments repo...")

        # Clean up any existing temp directory
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

        # Clone the repo
        print("📥 Cloning experiments repo...")
        subprocess.run(
            ["git", "clone", repo_url, str(temp_dir)], check=True, capture_output=True
        )

        # Copy the main task_meta.json file
        target_path = temp_dir / "task_meta.json"
        print(f"📁 Copying task meta file: task_meta.json")
        shutil.copy2(file_path, target_path)

        # Create tasks directory and copy individual task files
        if task_files:
            tasks_dir = temp_dir / "tasks"
            tasks_dir.mkdir(exist_ok=True)
            print(f"📁 Creating individual task files in ./tasks directory...")

            for task_file in task_files:
                task_file_path = tasks_dir / task_file["filename"]
                with open(task_file_path, "w", encoding="utf-8") as f:
                    json.dump(task_file["data"], f, indent=2, ensure_ascii=False)

            print(f"   - Created {len(task_files)} individual task files")

        # Change to repo directory for git operations
        original_dir = os.getcwd()
        os.chdir(temp_dir)

        # Add all changes
        subprocess.run(["git", "add", "."], check=True)

        # Check if there are changes to commit
        result = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True
        )

        if not result.stdout.strip():
            print("✅ No changes to push (files are up to date)")
            return True

        # Commit changes
        commit_msg = "Update task meta data and individual task files"
        subprocess.run(["git", "commit", "-m", commit_msg], check=True)

        # Push changes
        print("🚀 Pushing to remote repository...")
        subprocess.run(["git", "push"], check=True)

        print("✅ Successfully pushed task meta and individual task files to repo!")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Git operation failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Error pushing to repo: {e}")
        return False
    finally:
        # Change back to original directory
        os.chdir(original_dir)
        # Clean up temp directory
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


def main():
    parser = argparse.ArgumentParser(description="Aggregate all task meta.json files")
    parser.add_argument(
        "--output",
        type=str,
        default="task_meta.json",
        help="Output file path (default: task_meta.json)",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push results to eval-sys/mcpmark-experiments repo",
    )
    args = parser.parse_args()

    print("🔍 Searching for meta.json files in tasks directory...")

    # Find all meta.json files
    meta_files = find_all_meta_files()

    if not meta_files:
        print("❌ No meta.json files found in tasks directory")
        return 1

    print(f"📁 Found {len(meta_files)} meta.json files")

    # Aggregate the data
    print("🔄 Aggregating task meta data...")
    aggregated_data = aggregate_task_meta(meta_files)

    # Create individual task files if pushing to repo
    task_files = None
    if args.push:
        print("🔄 Creating individual task files...")
        task_files = create_individual_task_files(meta_files)
        print(f"📝 Prepared {len(task_files)} individual task files")

    # Save to file
    output_path = Path(args.output)
    success = push_to_file(output_path, aggregated_data, task_files, args.push)

    if not success:
        return 1

    if args.push:
        print(
            f"🚀 Task meta data and individual task files pushed to eval-sys/mcpmark-experiments repo"
        )

    return 0


if __name__ == "__main__":
    exit(main())
