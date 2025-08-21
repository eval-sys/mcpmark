#!/usr/bin/env python3
"""
Results Aggregator for MCPBench
Aggregates all meta.json files from task results and generates a comprehensive summary.json
Only processes complete and valid results (no pipeline errors).
"""

import json
import os
import argparse
import subprocess
import shutil
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any, Set, Tuple

# Import pipeline retry errors from evaluator
PIPELINE_RETRY_ERRORS: List[str] = [
    "State Duplication Error",
    "MCP Network Error",
]


def discover_all_tasks(service: str, tasks_root: Path = Path("tasks")) -> Set[str]:
    """Return set of expected task identifiers for the given service.

    Each task identifier is in the form "<category>/<task_name>".
    """
    service_root = tasks_root / service
    expected: Set[str] = set()

    if not service_root.exists():
        return expected

    for category_dir in service_root.iterdir():
        if not category_dir.is_dir() or category_dir.name.startswith("."):
            continue

        category_name = category_dir.name

        for task_dir in category_dir.iterdir():
            if task_dir.is_dir() and not task_dir.name.startswith("."):
                task_name = task_dir.name
                expected.add(f"{category_name}/{task_name}")

    return expected


def validate_service_model_results(
    model_path: Path, expected_tasks: Set[str]
) -> Tuple[bool, Set[str], bool]:
    """Validate that all tasks are present and without pipeline errors.

    Returns (is_complete, found_tasks, has_pipeline_error).
    """
    task_dirs = [d for d in model_path.iterdir() if d.is_dir()]

    found_tasks: Set[str] = set()
    has_pipeline_error = False

    for task_dir in task_dirs:
        meta_path = task_dir / "meta.json"
        if not meta_path.exists():
            continue

        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)

            task_name = meta.get("task_name", "")
            if task_name:
                found_tasks.add(task_name)

            # Check for pipeline errors
            error_msg = meta.get("execution_result", {}).get("error_message")
            if error_msg and any(err in error_msg for err in PIPELINE_RETRY_ERRORS):
                has_pipeline_error = True

        except Exception as e:
            print(f"Error reading {meta_path}: {e}")
            continue

    is_complete = expected_tasks.issubset(found_tasks)
    return is_complete, found_tasks, has_pipeline_error


def find_meta_files(results_dir: Path) -> List[Path]:
    """Find all meta.json files in the results directory"""
    meta_files = []
    for root, dirs, files in os.walk(results_dir):
        if "meta.json" in files:
            meta_files.append(Path(root) / "meta.json")
    return meta_files


def extract_category_from_task_name(task_name: str) -> str:
    """Extract category from task name (e.g., 'missing-semester/find_salient_file' -> 'missing-semester')"""
    if "/" in task_name:
        return task_name.split("/")[0].replace("-", "_")
    return "unknown"


def parse_meta_file(meta_path: Path) -> Dict[str, Any]:
    """Parse a single meta.json file"""
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error parsing {meta_path}: {e}")
        return {}


def aggregate_results(meta_files: List[Path]) -> Dict[str, Any]:
    """Aggregate all meta.json files into a summary"""
    if not meta_files:
        return {}

    # Parse all meta files
    all_tasks = []
    for meta_path in meta_files:
        meta_data = parse_meta_file(meta_path)
        if meta_data:
            all_tasks.append(meta_data)

    if not all_tasks:
        return {}

    # Get model name from first task (assuming all tasks use the same model)
    model = all_tasks[0].get("model", "unknown")

    # Calculate overall statistics
    total_tasks = len(all_tasks)
    successful_tasks = sum(
        1
        for task in all_tasks
        if task.get("execution_result", {}).get("success", False)
    )
    failed_tasks = total_tasks - successful_tasks
    success_rate = (
        round((successful_tasks / total_tasks) * 100, 2) if total_tasks > 0 else 0
    )

    # Calculate execution time statistics
    execution_times = [task.get("execution_time", 0) for task in all_tasks]
    total_execution_time = sum(execution_times)
    average_execution_time = (
        total_execution_time / total_tasks if total_tasks > 0 else 0
    )

    # Calculate token usage statistics
    total_input_tokens = sum(
        task.get("token_usage", {}).get("input_tokens", 0) for task in all_tasks
    )
    total_output_tokens = sum(
        task.get("token_usage", {}).get("output_tokens", 0) for task in all_tasks
    )
    total_tokens = total_input_tokens + total_output_tokens
    avg_input_tokens = total_input_tokens / total_tasks if total_tasks > 0 else 0
    avg_output_tokens = total_output_tokens / total_tasks if total_tasks > 0 else 0
    avg_total_tokens = total_tokens / total_tasks if total_tasks > 0 else 0

    # Calculate turn statistics
    total_turns = sum(task.get("turn_count", 0) or 0 for task in all_tasks)
    avg_turns = total_turns / total_tasks if total_tasks > 0 else 0

    # Group by category
    categories = defaultdict(list)
    for task in all_tasks:
        task_name = task.get("task_name", "unknown")
        category = extract_category_from_task_name(task_name)
        categories[category].append(task)

    # Calculate category breakdown
    category_breakdown = {}
    for category, tasks in categories.items():
        cat_total = len(tasks)
        cat_successful = sum(
            1
            for task in tasks
            if task.get("execution_result", {}).get("success", False)
        )
        cat_success_rate = (cat_successful / cat_total) * 100 if cat_total > 0 else 0

        cat_execution_times = [task.get("execution_time", 0) for task in tasks]
        cat_avg_time = sum(cat_execution_times) / cat_total if cat_total > 0 else 0

        cat_input_tokens = sum(
            task.get("token_usage", {}).get("input_tokens", 0) for task in tasks
        )
        cat_output_tokens = sum(
            task.get("token_usage", {}).get("output_tokens", 0) for task in tasks
        )
        cat_total_tokens = cat_input_tokens + cat_output_tokens
        cat_avg_input = cat_input_tokens / cat_total if cat_total > 0 else 0
        cat_avg_output = cat_output_tokens / cat_total if cat_total > 0 else 0
        cat_avg_total = cat_total_tokens / cat_total if cat_total > 0 else 0

        cat_turns = sum(task.get("turn_count", 0) or 0 for task in tasks)
        cat_avg_turns = cat_turns / cat_total if cat_total > 0 else 0

        category_breakdown[category] = {
            "total": cat_total,
            "success_rate": round(cat_success_rate, 2),
            "avg_time": round(cat_avg_time, 2),
            "token_usage": {
                "total_input": cat_input_tokens,
                "total_output": cat_output_tokens,
                "total": cat_total_tokens,
                "avg_input": round(cat_avg_input, 2),
                "avg_output": round(cat_avg_output, 2),
                "avg_total": round(cat_avg_total, 2),
            },
            "turn_usage": {
                "total_turns": cat_turns,
                "avg_turns": round(cat_avg_turns, 2),
            },
        }

    return {
        "model": model,
        "total_tasks": total_tasks,
        "successful_tasks": successful_tasks,
        "failed_tasks": failed_tasks,
        "success_rate": success_rate,
        "total_execution_time": round(total_execution_time, 6),
        "average_execution_time": round(average_execution_time, 6),
        "token_usage": {
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_tokens": total_tokens,
            "avg_input_tokens": round(avg_input_tokens, 2),
            "avg_output_tokens": round(avg_output_tokens, 2),
            "avg_total_tokens": round(avg_total_tokens, 2),
        },
        "turn_usage": {"total_turns": total_turns, "avg_turns": round(avg_turns, 2)},
        "category_breakdown": category_breakdown,
    }


def create_experiment_summary(
    exp_name: str, service_model_results: Dict[str, Any]
) -> Dict[str, Any]:
    """Create an experiment-wide summary containing all services and models"""

    # Group results by service
    services = defaultdict(dict)

    for service_model, summary in service_model_results.items():
        if "_" in service_model:
            service = service_model.split("_", 1)[0]
            model = service_model.split("_", 1)[1]
            services[service][model] = summary

    # Calculate experiment-wide statistics
    total_service_models = len(service_model_results)
    total_valid_service_models = len(
        [s for s in service_model_results.values() if s is not None]
    )

    # Aggregate all tasks across all service/model combinations
    all_tasks = 0
    all_successful = 0
    all_execution_time = 0
    all_input_tokens = 0
    all_output_tokens = 0
    all_turns = 0

    for summary in service_model_results.values():
        if summary:
            all_tasks += summary.get("total_tasks", 0) or 0
            all_successful += summary.get("successful_tasks", 0) or 0
            all_execution_time += summary.get("total_execution_time", 0) or 0
            all_input_tokens += summary.get("token_usage", {}).get("total_input_tokens", 0) or 0
            all_output_tokens += summary.get("token_usage", {}).get("total_output_tokens", 0) or 0
            all_turns += summary.get("turn_usage", {}).get("total_turns", 0) or 0

    overall_success_rate = (all_successful / all_tasks * 100) if all_tasks > 0 else 0

    return {
        "generated_at": datetime.now().isoformat(),
        "overview": {
            "total_service_model_combinations": total_service_models,
            "valid_combinations": total_valid_service_models,
            "total_tasks_across_all": all_tasks,
            "total_successful_across_all": all_successful,
            "overall_success_rate": round(overall_success_rate, 2),
            "total_execution_time": round(all_execution_time, 2),
            "total_token_usage": {
                "input_tokens": all_input_tokens,
                "output_tokens": all_output_tokens,
                "total_tokens": all_input_tokens + all_output_tokens,
            },
            "total_turns": all_turns,
        },
        "services": dict(services),
        "models_comparison": create_models_comparison(service_model_results),
        "services_comparison": create_services_comparison(service_model_results),
    }


def create_models_comparison(service_model_results: Dict[str, Any]) -> Dict[str, Any]:
    """Create model comparison across all services"""
    models = defaultdict(
        lambda: {
            "total_tasks": 0,
            "successful_tasks": 0,
            "services": [],
            "avg_success_rate": 0,
            "total_tokens": 0,
            "total_turns": 0,
        }
    )

    for service_model, summary in service_model_results.items():
        if summary and "_" in service_model:
            service = service_model.split("_", 1)[0]
            model = service_model.split("_", 1)[1]

            models[model]["total_tasks"] += summary.get("total_tasks", 0) or 0
            models[model]["successful_tasks"] += summary.get("successful_tasks", 0) or 0
            models[model]["services"].append(service)
            models[model]["total_tokens"] += summary.get("token_usage", {}).get("total_tokens", 0) or 0
            models[model]["total_turns"] += summary.get("turn_usage", {}).get("total_turns", 0) or 0

    # Calculate averages
    for model_data in models.values():
        if model_data["total_tasks"] > 0:
            model_data["avg_success_rate"] = round(
                (model_data["successful_tasks"] / model_data["total_tasks"]) * 100, 2
            )

    return dict(models)


def create_services_comparison(service_model_results: Dict[str, Any]) -> Dict[str, Any]:
    """Create service comparison across all models"""
    services = defaultdict(
        lambda: {
            "total_tasks": 0,
            "successful_tasks": 0,
            "models": [],
            "avg_success_rate": 0,
            "total_tokens": 0,
            "total_turns": 0,
        }
    )

    for service_model, summary in service_model_results.items():
        if summary and "_" in service_model:
            service = service_model.split("_", 1)[0]
            model = service_model.split("_", 1)[1]

            services[service]["total_tasks"] += summary.get("total_tasks", 0) or 0
            services[service]["successful_tasks"] += summary.get("successful_tasks", 0) or 0
            services[service]["models"].append(model)
            services[service]["total_tokens"] += summary.get("token_usage", {}).get("total_tokens", 0) or 0
            services[service]["total_turns"] += summary.get("turn_usage", {}).get("total_turns", 0) or 0

    # Calculate averages
    for service_data in services.values():
        if service_data["total_tasks"] > 0:
            service_data["avg_success_rate"] = round(
                (service_data["successful_tasks"] / service_data["total_tasks"]) * 100,
                2,
            )

    return dict(services)


def generate_task_jsons(exp_name: str, exp_dir: Path) -> Dict[str, Dict[str, Any]]:
    """Generate individual task JSON files with instruction, verify code, and model results."""
    task_jsons = {}
    tasks_root = Path("tasks")

    print("\n📋 Generating individual task JSONs...")

    # Find all service/model directories
    service_model_dirs = [d for d in exp_dir.iterdir() if d.is_dir() and "_" in d.name]

    # Collect all task results by task_id
    task_results_by_id = defaultdict(dict)
    task_service_mapping = {}  # Track which service each task belongs to

    for service_model_dir in service_model_dirs:
        service_model = service_model_dir.name
        if "_" not in service_model:
            continue

        service = service_model.split("_", 1)[0]
        model = service_model.split("_", 1)[1]

        # Find all task results in this service/model directory
        for task_dir in service_model_dir.iterdir():
            if not task_dir.is_dir():
                continue

            meta_path = task_dir / "meta.json"
            if not meta_path.exists():
                continue

            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    result_meta = json.load(f)

                # Extract task name and determine task path
                task_name = result_meta.get("task_name", "")
                if not task_name or "/" not in task_name:
                    continue

                category, task_id = task_name.rsplit("/", 1)
                category = category.replace("-", "_")  # Normalize category name

                # Store model result (1 for success, 0 for failure)
                success = result_meta.get("execution_result", {}).get("success", False)
                task_results_by_id[task_id][model] = 1 if success else 0
                task_service_mapping[task_id] = service

                # Load original task meta.json if not already loaded
                if task_id not in task_jsons:
                    # Try to find the task in the tasks directory
                    task_meta_path = (
                        tasks_root / service / category / task_id / "meta.json"
                    )
                    if task_meta_path.exists():
                        with open(task_meta_path, "r", encoding="utf-8") as f:
                            task_meta = json.load(f)

                        # Load description.md as instruction
                        desc_path = (
                            tasks_root / service / category / task_id / "description.md"
                        )
                        instruction = ""
                        if desc_path.exists():
                            with open(desc_path, "r", encoding="utf-8") as f:
                                instruction = f.read()

                        # Load verify.py
                        verify_path = (
                            tasks_root / service / category / task_id / "verify.py"
                        )
                        verify_code = ""
                        if verify_path.exists():
                            with open(verify_path, "r", encoding="utf-8") as f:
                                verify_code = f.read()

                        # Create enriched task JSON
                        task_jsons[task_id] = {
                            **task_meta,
                            "instruction": instruction,
                            "verify": verify_code,
                            "model_results": {},
                        }

            except Exception as e:
                print(f"  ⚠️  Error processing {meta_path}: {e}")
                continue

    # Add model results to task JSONs
    for task_id, model_results in task_results_by_id.items():
        if task_id in task_jsons:
            task_jsons[task_id]["model_results"] = model_results

    print(f"  ✅ Generated {len(task_jsons)} task JSON files")
    return task_jsons


def push_to_experiments_repo(
    exp_name: str, summary_file_path: Path, task_jsons: Dict[str, Dict[str, Any]] = None
) -> bool:
    """Push the experiment summary.json file and individual task JSONs to eval-sys/mcpmark-experiments repo"""
    if not summary_file_path.exists():
        print("⚠️  Summary file does not exist")
        return False

    repo_url = "https://github.com/eval-sys/mcpmark-experiments.git"
    temp_dir = Path("./temp_experiments_repo")

    try:
        print(f"\n🔄 Preparing to push experiment results to experiments repo...")

        # Clean up any existing temp directory
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

        # Clone the repo
        print("📥 Cloning experiments repo...")
        subprocess.run(
            ["git", "clone", repo_url, str(temp_dir)], check=True, capture_output=True
        )

        # Copy the summary file directly to the repo root as summary.json
        target_path = temp_dir / "summary.json"

        print(f"📁 Copying experiment summary: summary.json")

        # Copy file (overwrites if exists)
        shutil.copy2(summary_file_path, target_path)
        print(f"  📄 summary.json")

        # Create tasks directory and copy individual task JSONs
        if task_jsons:
            tasks_dir = temp_dir / "tasks"
            tasks_dir.mkdir(exist_ok=True)

            print(f"📁 Copying individual task JSONs to tasks/")
            for task_id, task_data in task_jsons.items():
                task_file = tasks_dir / f"{task_id}.json"
                with open(task_file, "w", encoding="utf-8") as f:
                    json.dump(task_data, f, indent=2, ensure_ascii=False)
                print(f"  📄 tasks/{task_id}.json")

        # Change to repo directory for git operations
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
        commit_msg = f"Update experiment summary and task results for {exp_name}"
        subprocess.run(["git", "commit", "-m", commit_msg], check=True)

        # Push changes
        print("🚀 Pushing to remote repository...")
        subprocess.run(["git", "push"], check=True)

        print("✅ Successfully pushed experiment results to repo!")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Git operation failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Error pushing to repo: {e}")
        return False
    finally:
        # Change back to original directory
        os.chdir("..")
        # Clean up temp directory
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


def main():
    parser = argparse.ArgumentParser(
        description="Aggregate meta.json files and generate summary.json"
    )
    parser.add_argument(
        "--exp-name", required=True, help="Experiment name (directory under ./results/)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force generation even for incomplete/invalid results",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push results to eval-sys/mcpmark-experiments repo",
    )
    args = parser.parse_args()

    # Define paths
    results_base = Path("./results")
    exp_dir = results_base / args.exp_name

    if not exp_dir.exists():
        print(f"Error: Experiment directory {exp_dir} does not exist")
        return 1

    print(f"Processing experiment: {args.exp_name}")
    
    # Check if this is a k-run experiment (has run-N subdirectories)
    run_dirs = sorted([d for d in exp_dir.iterdir() if d.is_dir() and d.name.startswith("run-")])
    k_run_summary = None  # Initialize for later use
    k = 0  # Initialize k
    
    if run_dirs:
        # This is a k-run experiment
        k = len(run_dirs)
        print(f"Detected {k}-run experiment structure")
        
        # First, run the k-run aggregator
        from .aggregate_k_runs import (
            collect_task_results_from_run,
            calculate_pass_k_metrics,
            aggregate_by_service_model,
            generate_k_run_summary
        )
        
        print(f"Computing pass@k metrics for {k} runs...")
        
        # Collect results from all runs
        all_runs_results = {}
        for run_idx in range(1, k + 1):
            run_name = f"run-{run_idx}"
            run_dir = exp_dir / run_name
            
            if run_dir.exists():
                print(f"Processing {run_name}...")
                results = collect_task_results_from_run(run_dir)
                all_runs_results[run_name] = results
                print(f"  Found {len(results)} task results")
            else:
                print(f"Warning: {run_name} directory not found")
                all_runs_results[run_name] = {}
        
        # Calculate pass@k metrics
        task_metrics = calculate_pass_k_metrics(all_runs_results, k)
        service_model_metrics = aggregate_by_service_model(task_metrics)
        k_run_summary = generate_k_run_summary(
            args.exp_name, k, all_runs_results, task_metrics, service_model_metrics
        )
        
        # We no longer save a separate k_run_summary.json file
        print(f"✅ Computed pass@k metrics for {k} runs")
        
        # Process results from run-1 for detailed aggregation
        # (to maintain compatibility with existing summary format)
        print(f"\nProcessing run-1 for detailed aggregation...")
        exp_dir = exp_dir / "run-1"
        if not exp_dir.exists():
            print(f"Error: run-1 directory not found")
            return 1
    
    print(f"Looking for service/model directories in: {exp_dir}")

    # Find service/model directories
    service_model_dirs = [d for d in exp_dir.iterdir() if d.is_dir() and "_" in d.name]

    if not service_model_dirs:
        print("No service/model directories found")
        return 1

    print(f"Found {len(service_model_dirs)} service/model combinations")

    processed_count = 0
    skipped_count = 0
    invalid_results = []  # Track invalid results for warning
    service_model_results = {}  # Store all service/model results

    # Process each service/model combination
    for service_model_dir in service_model_dirs:
        service_model = service_model_dir.name

        # Extract service name (part before first underscore)
        if "_" in service_model:
            service = service_model.split("_", 1)[0]
            model = service_model.split("_", 1)[1]
        else:
            print(f"Warning: Cannot parse service from '{service_model}', skipping")
            continue

        print(f"\n--- Processing {service_model} ---")

        # Discover expected tasks for this service
        expected_tasks = discover_all_tasks(service)
        if not expected_tasks:
            print(f"Warning: No tasks found for service '{service}', skipping")
            continue

        print(f"Expected {len(expected_tasks)} tasks for service '{service}'")

        # Validate results
        is_complete, found_tasks, has_pipeline_error = validate_service_model_results(
            service_model_dir, expected_tasks
        )

        missing_tasks = expected_tasks - found_tasks
        is_valid = is_complete and not has_pipeline_error

        print(f"Found {len(found_tasks)} tasks")
        if missing_tasks:
            print(f"Missing tasks: {sorted(missing_tasks)}")
        if has_pipeline_error:
            print("⚠️  Contains pipeline errors")

        # Track invalid results
        if not is_valid:
            invalid_results.append(
                {
                    "service_model": service_model,
                    "incomplete": not is_complete,
                    "pipeline_errors": has_pipeline_error,
                    "missing_count": len(missing_tasks),
                }
            )

        # Check if we should process this service/model
        should_process = is_valid or args.force

        if not should_process:
            print("❌ Skipping: incomplete or contains pipeline errors")
            print(f"   Use --force to generate summary anyway")
            skipped_count += 1
            service_model_results[service_model] = None  # Mark as invalid
            continue

        # Find meta.json files for this service/model
        meta_files = find_meta_files(service_model_dir)

        if not meta_files:
            print(f"No meta.json files found in {service_model_dir}")
            skipped_count += 1
            service_model_results[service_model] = None
            continue

        print(f"Processing {len(meta_files)} meta.json files")

        # Generate summary for this service/model
        summary = aggregate_results(meta_files)
        if summary:
            status = "✅" if is_valid else "⚠️ "
            warning_note = "" if is_valid else " (INCOMPLETE/INVALID)"
            print(f"{status} Processed {service_model}{warning_note}")
            print(f"   - Total tasks: {summary['total_tasks']}")
            print(f"   - Success rate: {summary['success_rate']}%")
            print(f"   - Categories: {list(summary['category_breakdown'].keys())}")

            service_model_results[service_model] = summary
            processed_count += 1
        else:
            print("❌ Failed to generate summary")
            service_model_results[service_model] = None
            skipped_count += 1

    print(f"\n=== Processing Summary ===")
    print(f"Processed: {processed_count}")
    print(f"Skipped: {skipped_count}")
    print(f"Total: {processed_count + skipped_count}")

    # Warn about invalid results if not using force
    if invalid_results and not args.force:
        print(
            f"\n⚠️  WARNING: {len(invalid_results)} service/model combinations have invalid results:"
        )
        for result in invalid_results:
            reasons = []
            if result["incomplete"]:
                reasons.append(f"missing {result['missing_count']} tasks")
            if result["pipeline_errors"]:
                reasons.append("pipeline errors")
            print(f"  - {result['service_model']}: {', '.join(reasons)}")

        print(f"\n❌ Cannot generate experiment-wide summary with invalid results.")
        print(f"📋 Options:")
        print(f"   1. Complete missing evaluations for the above models")
        print(f"   2. Use --force to generate summary anyway (not recommended)")
        return 1

    elif invalid_results and args.force:
        print(
            f"\n⚠️  WARNING: Using --force with {len(invalid_results)} invalid results."
        )
        print(f"📊 Summary will include incomplete/invalid data.")

    # Generate experiment-wide summary
    print(f"\n🔄 Generating experiment-wide summary...")

    # Filter out None results for the summary
    valid_results = {k: v for k, v in service_model_results.items() if v is not None}

    if not valid_results:
        print("❌ No valid results to generate experiment summary")
        return 1

    experiment_summary = create_experiment_summary(args.exp_name, valid_results)

    # Determine correct path for summary.json
    # If this was a k-run experiment, save to parent directory
    if run_dirs:
        summary_path = results_base / args.exp_name / "summary.json"
        
        # Create a new summary with k_run_metrics at the beginning
        final_summary = {
            "k": k,
            "k_run_metrics": k_run_summary.get("overall_metrics", {}),
            "k_run_service_model_breakdown": k_run_summary.get("service_model_breakdown", {}),
            **experiment_summary  # Include all other fields
        }
    else:
        summary_path = exp_dir / "summary.json"
        final_summary = experiment_summary
    
    # Save experiment summary
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(final_summary, f, indent=2, ensure_ascii=False)

    print(f"✅ Experiment summary saved to: {summary_path}")
    print(f"📊 Summary includes:")
    
    # Print k-run metrics if available
    if run_dirs and k_run_summary:
        overall_metrics = k_run_summary.get("overall_metrics", {})
        print(f"   - K-run evaluation with k={k}")
        print(f"   - pass@1: {overall_metrics.get('pass@1', 0):.2%} (run-1 success rate)")
        print(f"   - pass@{k}: {overall_metrics.get('pass@k', 0):.2%} (at least 1 success)")
        print(f"   - pass^{k}: {overall_metrics.get('pass^k', 0):.2%} (all {k} runs succeed)")
        print(f"   - avg@{k}: {overall_metrics.get('avg@k', 0):.2%} (average success rate)")
    
    print(
        f"   - {experiment_summary['overview']['total_service_model_combinations']} service/model combinations"
    )
    print(
        f"   - {experiment_summary['overview']['total_tasks_across_all']} total tasks"
    )
    print(
        f"   - {experiment_summary['overview']['overall_success_rate']}% overall success rate"
    )
    print(f"   - {len(experiment_summary['services'])} services")
    print(f"   - {len(experiment_summary['models_comparison'])} models")

    # Generate individual task JSONs
    task_jsons = None
    if args.push:
        task_jsons = generate_task_jsons(args.exp_name, exp_dir)

    # Git push functionality
    if args.push:
        success = push_to_experiments_repo(args.exp_name, summary_path, task_jsons)
        if not success:
            print("❌ Failed to push to experiments repo")
            return 1

    print(f"\n✅ Experiment summary generated successfully!")
    if args.push:
        print(
            f"🚀 Summary and task results pushed to eval-sys/mcpmark-experiments repo"
        )
        if task_jsons:
            print(
                f"📊 Pushed {len(task_jsons)} individual task JSON files to tasks/ folder"
            )

    return 0


if __name__ == "__main__":
    exit(main())
