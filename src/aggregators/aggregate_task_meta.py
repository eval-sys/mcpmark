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
        with open(meta_path, 'r', encoding='utf-8') as f:
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
            all_data.append(meta_data)
            
            # Collect categories using category_id and category_name
            if "category_id" in meta_data and "category_name" in meta_data:
                category_id = meta_data["category_id"]
                category_name = meta_data["category_name"]
                # Use category_id as the key to ensure uniqueness
                categories_dict[category_id] = {
                    "id": category_id,
                    "name": category_name
                }
            
            # Collect all unique tags
            if "tags" in meta_data and isinstance(meta_data["tags"], list):
                all_tags_set.update(meta_data["tags"])
    
    # Convert categories dict to sorted list
    categories_list = sorted(categories_dict.values(), key=lambda x: x["id"])
    
    # Convert tags set to sorted list
    all_tags_list = sorted(all_tags_set)
    
    return {
        "data": all_data,
        "count": len(all_data),
        "categories": categories_list,
        "tags": all_tags_list
    }


def push_to_file(output_file: Path, data: Dict[str, Any], push_to_repo: bool = False) -> bool:
    """Save the aggregated data to file and optionally push to repo"""
    try:
        # Create parent directory if it doesn't exist
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the aggregated data
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Task meta data saved to: {output_file}")
        print(f"📊 Summary:")
        print(f"   - Total tasks with meta.json: {data['count']}")
        print(f"   - Categories: {len(data['categories'])}")
        print(f"   - Unique tags: {len(data['tags'])}")
        
        if push_to_repo:
            return push_to_experiments_repo(output_file)
        
        return True
        
    except Exception as e:
        print(f"❌ Error saving file: {e}")
        return False


def push_to_experiments_repo(file_path: Path) -> bool:
    """Push the task meta file to eval-sys/mcpmark-experiments repo"""
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
        subprocess.run([
            "git", "clone", repo_url, str(temp_dir)
        ], check=True, capture_output=True)
        
        # Copy the file to repo
        target_path = temp_dir / "task_meta.json"
        print(f"📁 Copying task meta file: task_meta.json")
        shutil.copy2(file_path, target_path)
        
        # Change to repo directory for git operations
        original_dir = os.getcwd()
        os.chdir(temp_dir)
        
        # Add all changes
        subprocess.run(["git", "add", "."], check=True)
        
        # Check if there are changes to commit
        result = subprocess.run(
            ["git", "status", "--porcelain"], 
            capture_output=True, text=True
        )
        
        if not result.stdout.strip():
            print("✅ No changes to push (file is up to date)")
            return True
        
        # Commit changes
        commit_msg = "Update task meta data"
        subprocess.run([
            "git", "commit", "-m", commit_msg
        ], check=True)
        
        # Push changes
        print("🚀 Pushing to remote repository...")
        subprocess.run(["git", "push"], check=True)
        
        print("✅ Successfully pushed task meta to repo!")
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
    parser.add_argument("--output", type=str, default="task_meta.json",
                       help="Output file path (default: task_meta.json)")
    parser.add_argument("--push", action="store_true",
                       help="Push results to eval-sys/mcpmark-experiments repo")
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
    
    # Save to file
    output_path = Path(args.output)
    success = push_to_file(output_path, aggregated_data, args.push)
    
    if not success:
        return 1
    
    if args.push:
        print(f"🚀 Task meta data pushed to eval-sys/mcpmark-experiments repo as task_meta.json")
    
    return 0


if __name__ == "__main__":
    exit(main())