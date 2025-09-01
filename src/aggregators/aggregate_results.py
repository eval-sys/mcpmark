#!/usr/bin/env python3
"""
Simplified MCPMark Results Aggregator
Aggregates evaluation results and generates summary with pass@k metrics.
"""

import json
import os
import argparse
import subprocess
import shutil
import tempfile
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any, Tuple
from datetime import datetime
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from src.errors import is_retryable_error


def discover_tasks() -> Dict[str, List[str]]:
    """Discover all tasks from ./tasks directory."""
    tasks_dir = Path("./tasks")
    
    all_tasks = {}
    
    # Handle each MCP service
    # Note: playwright and playwright_webarena both map to "playwright" MCP
    service_mappings = {
        "filesystem": ["filesystem"],
        "github": ["github"],
        "notion": ["notion"],
        "playwright": ["playwright", "playwright_webarena"],  # Both count as playwright
        "postgres": ["postgres"]
    }
    
    for mcp_service, task_dirs in service_mappings.items():
        tasks = []
        for task_dir_name in task_dirs:
            service_path = tasks_dir / task_dir_name
            if not service_path.exists():
                continue
            
            # Find all category/task combinations
            for category_dir in service_path.iterdir():
                if not category_dir.is_dir() or category_dir.name.startswith("__"):
                    continue
                
                for task_dir in category_dir.iterdir():
                    if task_dir.is_dir():
                        # Prefix with original dir name for uniqueness
                        if task_dir_name == "playwright_webarena":
                            tasks.append(f"webarena__{category_dir.name}__{task_dir.name}")
                        else:
                            tasks.append(f"{category_dir.name}__{task_dir.name}")
        
        all_tasks[mcp_service] = sorted(tasks)
    
    return all_tasks


def collect_results(exp_dir: Path, k: int) -> Dict[str, Dict[str, Any]]:
    """Collect all results from experiment directory."""
    results = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    
    # Current layout: results/<exp>/<model>__<service>/run-N/<category>__<task>/
    for model_service_dir in exp_dir.iterdir():
        if not model_service_dir.is_dir() or "__" not in model_service_dir.name:
            continue
        
        model, service = model_service_dir.name.split("__", 1)
        
        for run_idx in range(1, k + 1):
            run_dir = model_service_dir / f"run-{run_idx}"
            if not run_dir.exists():
                continue
            
            for task_dir in run_dir.iterdir():
                if not task_dir.is_dir() or "__" not in task_dir.name:
                    continue
                
                meta_path = task_dir / "meta.json"
                if meta_path.exists():
                    with open(meta_path) as f:
                        meta = json.load(f)
                        task_name = task_dir.name
                        results[model][service][f"run-{run_idx}"][task_name] = meta
    
    return results


def check_completeness_and_validity(
    results: Dict, all_tasks: Dict, k: int, single_run_models: List[str]
) -> Tuple[Dict, Dict, Dict]:
    """Check completeness and validity of results."""
    complete_models = {}
    incomplete_models = {}
    invalid_models = {}
    
    for model, model_results in results.items():
        is_single_run = any(srm in model for srm in single_run_models)
        required_runs = 1 if is_single_run else k
        
        missing_info = []
        invalid_info = []
        
        # Check each service
        for service, service_tasks in all_tasks.items():
            if service not in model_results:
                missing_info.append(f"Missing entire service: {service}")
                continue
            
            service_results = model_results[service]
            
            # Check runs
            for run_idx in range(1, required_runs + 1):
                run_name = f"run-{run_idx}"
                if run_name not in service_results:
                    missing_info.append(f"Missing {run_name} for {service}")
                    continue
                
                run_results = service_results[run_name]
                
                # Check tasks
                missing_tasks = []
                invalid_tasks = []
                
                for task in service_tasks:
                    if task not in run_results:
                        missing_tasks.append(task)
                    else:
                        # Check for retryable errors
                        meta = run_results[task]
                        error_msg = meta.get("execution_result", {}).get("error_message", "")
                        if error_msg and is_retryable_error(error_msg):
                            invalid_tasks.append(f"{task}: {error_msg[:50]}...")
                
                if missing_tasks:
                    missing_info.append(f"{service}/{run_name}: missing {len(missing_tasks)} tasks")
                if invalid_tasks:
                    invalid_info.extend([f"{service}/{run_name}/{t}" for t in invalid_tasks])
        
        if missing_info:
            incomplete_models[model] = missing_info
        elif invalid_info:
            invalid_models[model] = invalid_info
        else:
            complete_models[model] = model_results
    
    return complete_models, incomplete_models, invalid_models


def calculate_metrics(complete_models: Dict, all_tasks: Dict, k: int, single_run_models: List[str]) -> Dict:
    """Calculate pass@k metrics for complete models."""
    summary = {
        "generated_at": datetime.now().isoformat(),
        "k": k,
        "overall": {},
    }
    
    # Initialize per-service sections
    for service in all_tasks.keys():
        summary[service] = {}
    
    for model, model_results in complete_models.items():
        is_single_run = any(srm in model for srm in single_run_models)
        
        # Calculate metrics across all services
        total_tasks = sum(len(tasks) for tasks in all_tasks.values())
        pass_at_1 = 0
        pass_at_k = 0
        pass_power_k = 0
        
        for service, service_tasks in all_tasks.items():
            service_pass_1 = 0
            service_pass_k = 0
            service_pass_power_k = 0
            
            for task in service_tasks:
                successes = []
                
                # Collect success across runs
                num_runs = 1 if is_single_run else k
                for run_idx in range(1, num_runs + 1):
                    run_name = f"run-{run_idx}"
                    if (service in model_results and 
                        run_name in model_results[service] and 
                        task in model_results[service][run_name]):
                        
                        meta = model_results[service][run_name][task]
                        success = meta.get("execution_result", {}).get("success", False)
                        successes.append(success)
                    else:
                        successes.append(False)
                
                # Calculate task metrics
                if successes[0]:  # Pass@1
                    service_pass_1 += 1
                    pass_at_1 += 1
                
                if not is_single_run:
                    if any(successes):  # Pass@k
                        service_pass_k += 1
                        pass_at_k += 1
                    
                    if all(successes):  # Pass^k
                        service_pass_power_k += 1
                        pass_power_k += 1
            
            # Store service-level metrics
            service_metrics = {
                "total_tasks": len(service_tasks),
                "pass@1": round(service_pass_1 / len(service_tasks), 4),
            }
            
            if not is_single_run:
                service_metrics[f"pass@{k}"] = round(service_pass_k / len(service_tasks), 4)
                service_metrics[f"pass^{k}"] = round(service_pass_power_k / len(service_tasks), 4)
            
            summary[service][model] = service_metrics
        
        # Store overall metrics
        overall_metrics = {
            "total_tasks": total_tasks,
            "pass@1": round(pass_at_1 / total_tasks, 4),
        }
        
        if not is_single_run:
            overall_metrics[f"pass@{k}"] = round(pass_at_k / total_tasks, 4)
            overall_metrics[f"pass^{k}"] = round(pass_power_k / total_tasks, 4)
        
        summary["overall"][model] = overall_metrics
    
    return summary


def generate_model_results(exp_dir: Path, complete_models: Dict, all_tasks: Dict):
    """Generate model_results directory."""
    model_results_dir = exp_dir / "model_results"
    if model_results_dir.exists():
        shutil.rmtree(model_results_dir)
    model_results_dir.mkdir()
    
    for model, model_data in complete_models.items():
        model_dir = model_results_dir / model
        model_dir.mkdir()
        
        # Create a file for each task
        for service, service_tasks in all_tasks.items():
            if service not in model_data:
                continue
            
            for task in service_tasks:
                task_data = {
                    "model": model,
                    "service": service,
                    "task": task,
                    "runs": {}
                }
                
                # Collect data from all runs
                for run_name, run_data in model_data[service].items():
                    if task in run_data:
                        meta = run_data[task]
                        task_data["runs"][run_name] = {
                            "success": meta.get("execution_result", {}).get("success", False),
                            "error_message": meta.get("execution_result", {}).get("error_message"),
                            "execution_time": meta.get("agent_execution_time", 0),
                            "token_usage": meta.get("token_usage", {}),
                            "turn_count": meta.get("turn_count", 0)
                        }
                
                # Save task file
                task_file = model_dir / f"{task}.json"
                with open(task_file, "w") as f:
                    json.dump(task_data, f, indent=2)


def generate_task_results(exp_dir: Path, complete_models: Dict, all_tasks: Dict):
    """Generate task_results directory."""
    task_results_dir = exp_dir / "task_results"
    if task_results_dir.exists():
        shutil.rmtree(task_results_dir)
    task_results_dir.mkdir()
    
    # For each task, collect results across all models
    for service, service_tasks in all_tasks.items():
        for task in service_tasks:
            task_data = {
                "task": task,
                "service": service,
                "models": {}
            }
            
            for model, model_data in complete_models.items():
                if service not in model_data:
                    continue
                
                model_task_data = {"runs": []}
                
                for run_name, run_data in model_data[service].items():
                    if task in run_data:
                        meta = run_data[task]
                        model_task_data["runs"].append({
                            "run": run_name,
                            "success": meta.get("execution_result", {}).get("success", False),
                            "execution_time": meta.get("agent_execution_time", 0),
                            "token_usage": meta.get("token_usage", {})
                        })
                
                if model_task_data["runs"]:
                    task_data["models"][model] = model_task_data
            
            # Save task file
            task_file = task_results_dir / f"{task}.json"
            with open(task_file, "w") as f:
                json.dump(task_data, f, indent=2)


def generate_readme(exp_name: str, summary: Dict, k: int) -> str:
    """Generate README.md content."""
    lines = [
        f"# {exp_name} - Evaluation Results",
        "",
        f"Generated: {summary['generated_at']}",
        "",
        "## Overall Performance",
        "",
        "| Model | Total Tasks | Pass@1 |" + (f" Pass@{k} | Pass^{k} |" if k > 1 else ""),
        "|-------|-------------|--------|" + ("----------|----------|" if k > 1 else ""),
    ]
    
    # Sort models by Pass@1
    sorted_models = sorted(
        summary["overall"].items(),
        key=lambda x: x[1]["pass@1"],
        reverse=True
    )
    
    for model, metrics in sorted_models:
        row = f"| {model} | {metrics['total_tasks']} | {metrics['pass@1'] * 100:.1f}% |"
        if k > 1 and f"pass@{k}" in metrics:
            row += f" {metrics[f'pass@{k}'] * 100:.1f}% | {metrics[f'pass^{k}'] * 100:.1f}% |"
        lines.append(row)
    
    return "\n".join(lines)


def push_to_github(exp_dir: Path, exp_name: str):
    """Push results to GitHub repository."""
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            print("📥 Cloning experiments repository...")
            subprocess.run([
                "git", "clone",
                "git@github.com:eval-sys/mcpmark-experiments.git",
                str(temp_path)
            ], check=True, capture_output=True)
            
            # Copy files
            for item in ["summary.json", "README.md", "model_results", "task_results"]:
                src = exp_dir / item
                if src.exists():
                    dst = temp_path / item
                    if src.is_dir():
                        if dst.exists():
                            shutil.rmtree(dst)
                        shutil.copytree(src, dst)
                    else:
                        shutil.copy2(src, dst)
                    print(f"  📄 {item}")
            
            # Git operations
            os.chdir(temp_path)
            subprocess.run(["git", "add", "."], check=True)
            
            # Check for changes
            result = subprocess.run(
                ["git", "diff", "--staged", "--name-only"],
                capture_output=True, text=True
            )
            
            if not result.stdout.strip():
                print("✅ No changes to push")
                return True
            
            # Commit and push
            subprocess.run([
                "git", "commit", "-m", f"Update results for {exp_name}"
            ], check=True)
            subprocess.run(["git", "push"], check=True)
            print("✅ Successfully pushed to GitHub")
            
            return True
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Git operation failed: {e}")
        return False


def print_validation_report(complete: Dict, incomplete: Dict, invalid: Dict, all_tasks: Dict, k: int, single_run_models: List[str], raw_results: Dict):
    """Print structured validation report with summary table."""
    
    # Combine all models
    all_models = {}
    for model in complete:
        all_models[model] = {"status": "complete", "data": complete[model]}
    for model in incomplete:
        all_models[model] = {"status": "incomplete", "issues": incomplete[model]}
    for model in invalid:
        all_models[model] = {"status": "invalid", "issues": invalid[model]}
    
    # Calculate expected counts
    total_expected_tasks = sum(len(tasks) for tasks in all_tasks.values())
    
    # Summary table
    print("\n" + "=" * 100)
    print("COMPLETENESS SUMMARY TABLE")
    print("=" * 100)
    print()
    print(f"{'Model':<30} {'Expected':<12} {'Actual':<12} {'Missing':<12} {'Status':<30}")
    print("-" * 100)
    
    sorted_models = sorted(all_models.keys())
    
    for model_name in sorted_models:
        model_info = all_models[model_name]
        
        # Determine expected runs and tasks
        is_single_run = any(srm in model_name for srm in single_run_models)
        expected_runs = 1 if is_single_run else k
        expected_total = total_expected_tasks * expected_runs
        
        if model_info["status"] == "complete":
            # Count actual tasks from complete model data
            actual_total = 0
            for service, service_data in model_info["data"].items():
                for run_name, run_data in service_data.items():
                    actual_total += len(run_data)
            missing = 0
            status = "✅ Complete"
        else:
            # For incomplete/invalid models, count from raw results
            actual_total = 0
            if model_name in raw_results:
                for service, service_data in raw_results[model_name].items():
                    for run_name, run_data in service_data.items():
                        actual_total += len(run_data)
            
            missing = expected_total - actual_total
            
            if model_info["status"] == "incomplete":
                # Find which services have issues
                problem_services = set()
                for issue in model_info["issues"]:
                    if "Missing entire service:" in issue:
                        service = issue.split(": ")[1]
                        problem_services.add(service)
                    elif "/" in issue:
                        service = issue.split("/")[0]
                        problem_services.add(service)
                    elif "Missing run" in issue:
                        service = issue.split(" for ")[1]
                        problem_services.add(service)
                
                if problem_services:
                    services_str = ", ".join(sorted(problem_services))
                    status = f"❌ Incomplete ({services_str})"
                else:
                    status = "❌ Incomplete"
            else:  # invalid
                status = "⚠️  Invalid (retryable errors)"
        
        # Format the row
        print(f"{model_name:<30} {expected_total:<12} {actual_total:<12} {missing:<12} {status:<30}")
    
    print()
    
    # Overall statistics
    complete_count = len(complete)
    incomplete_count = len(incomplete)
    invalid_count = len(invalid)
    total_models = complete_count + incomplete_count + invalid_count
    
    print("=" * 100)
    print("OVERALL STATISTICS")
    print("=" * 100)
    print(f"Total models analyzed: {total_models}")
    print(f"Complete models: {complete_count}")
    print(f"Incomplete models: {incomplete_count}")
    print(f"Invalid models (with retryable errors): {invalid_count}")
    print(f"Total tasks per MCP: {total_expected_tasks}")
    print(f"Expected runs (k): {k}")
    
    if not complete:
        print("\n❌ No models have complete and valid results!")
    else:
        print(f"\n✅ {complete_count} model(s) ready for aggregation: {', '.join(sorted(complete.keys()))}")


def main():
    parser = argparse.ArgumentParser(
        description="Simplified MCPMark results aggregator"
    )
    parser.add_argument("--exp-name", required=True, help="Experiment name")
    parser.add_argument("--k", type=int, default=4, help="Number of runs (default: 4)")
    parser.add_argument(
        "--single-run-models",
        type=str,
        help="Comma-separated list of models that only need run-1"
    )
    parser.add_argument("--push", action="store_true", help="Push to GitHub")
    
    args = parser.parse_args()
    
    # Parse single-run models
    single_run_models = []
    if args.single_run_models:
        single_run_models = [m.strip() for m in args.single_run_models.split(",")]
        print(f"📌 Single-run models: {', '.join(single_run_models)}")
    
    # Setup paths
    exp_dir = Path("./results") / args.exp_name
    if not exp_dir.exists():
        print(f"❌ Experiment directory {exp_dir} does not exist")
        return 1
    
    print(f"🔄 Processing experiment: {args.exp_name}")
    
    # Discover all tasks
    print("📋 Discovering tasks...")
    all_tasks = discover_tasks()
    total_tasks = sum(len(tasks) for tasks in all_tasks.values())
    print(f"  Found {total_tasks} tasks across {len(all_tasks)} services")
    
    print("📥 Collecting results...")
    results = collect_results(exp_dir, args.k)
    print(f"  Found results for {len(results)} models")
    
    # Check completeness and validity
    print("✓ Checking completeness and validity...")
    complete_models, incomplete_models, invalid_models = check_completeness_and_validity(
        results, all_tasks, args.k, single_run_models
    )
    
    # Print validation report with summary table
    print_validation_report(complete_models, incomplete_models, invalid_models, 
                           all_tasks, args.k, single_run_models, results)
    
    if not complete_models:
        return 1
    
    # Calculate metrics
    print("\n📊 Calculating metrics...")
    summary = calculate_metrics(complete_models, all_tasks, args.k, single_run_models)
    
    # Save summary
    summary_path = exp_dir / "summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"  📄 Saved summary.json")
    
    # Generate model_results
    print("📁 Generating model_results...")
    generate_model_results(exp_dir, complete_models, all_tasks)
    print(f"  Created {len(complete_models)} model directories")
    
    # Generate task_results
    print("📁 Generating task_results...")
    generate_task_results(exp_dir, complete_models, all_tasks)
    print(f"  Created {total_tasks} task files")
    
    # Generate README
    readme_content = generate_readme(args.exp_name, summary, args.k)
    readme_path = exp_dir / "README.md"
    with open(readme_path, "w") as f:
        f.write(readme_content)
    print("  📄 Generated README.md")
    
    # Push to GitHub if requested
    if args.push:
        print("\n🚀 Pushing to GitHub...")
        push_to_github(exp_dir, args.exp_name)
    
    print(f"\n🎉 Successfully processed {args.exp_name}")
    return 0


if __name__ == "__main__":
    exit(main())