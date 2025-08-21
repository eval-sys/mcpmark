#!/usr/bin/env python3
"""
K-Run Aggregator for MCPBench
Aggregates results from multiple evaluation runs to compute pass@k, pass^k, and avg@k metrics.
"""

import json
import argparse
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any, Set, Tuple, Optional

# Import pipeline retry errors from evaluator
PIPELINE_RETRY_ERRORS: List[str] = [
    "State Duplication Error",
    "MCP Network Error",
]


def discover_run_directories(exp_dir: Path) -> List[Path]:
    """Discover all run-N directories in an experiment."""
    run_dirs = sorted([
        d for d in exp_dir.iterdir()
        if d.is_dir() and d.name.startswith("run-")
    ])
    return run_dirs


def extract_run_index(run_dir: Path) -> int:
    """Extract the run index from a run directory name (e.g., 'run-3' -> 3)."""
    try:
        return int(run_dir.name.split("-")[1])
    except (IndexError, ValueError):
        return 0


def collect_task_results_from_run(run_dir: Path) -> Dict[str, Dict[str, Any]]:
    """
    Collect all task results from a single run directory.
    Returns a dictionary mapping "service_model/task_name" to task result.
    """
    results = {}
    
    # Find all service_model directories in this run
    for service_model_dir in run_dir.iterdir():
        if not service_model_dir.is_dir() or not "_" in service_model_dir.name:
            continue
            
        service_model = service_model_dir.name
        
        # Find all task results in this service_model directory
        for task_dir in service_model_dir.iterdir():
            if not task_dir.is_dir():
                continue
                
            meta_path = task_dir / "meta.json"
            if not meta_path.exists():
                continue
                
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    
                task_name = meta.get("task_name", "")
                if task_name:
                    # Create unique key for this task
                    task_key = f"{service_model}/{task_name}"
                    results[task_key] = {
                        "success": meta.get("execution_result", {}).get("success", False),
                        "error_message": meta.get("execution_result", {}).get("error_message"),
                        "execution_time": meta.get("execution_time", 0),
                        "token_usage": meta.get("token_usage", {}),
                        "turn_count": meta.get("turn_count", 0) or 0,
                    }
            except Exception as e:
                print(f"Error reading {meta_path}: {e}")
                continue
                
    return results


def calculate_pass_k_metrics(
    all_runs_results: Dict[str, Dict[str, Dict[str, Any]]], 
    k: int
) -> Dict[str, Any]:
    """
    Calculate pass@k, pass^k, and avg@k metrics for all tasks.
    
    Args:
        all_runs_results: Dictionary mapping run names to their task results
        k: Number of runs
        
    Returns:
        Dictionary with aggregated metrics for each task and overall statistics
    """
    # Get all unique task keys across all runs
    all_task_keys = set()
    for run_results in all_runs_results.values():
        all_task_keys.update(run_results.keys())
    
    # Calculate metrics for each task
    task_metrics = {}
    for task_key in sorted(all_task_keys):
        successes = []
        execution_times = []
        token_usages = []
        turn_counts = []
        
        # Collect results from each run
        for run_idx in range(1, k + 1):
            run_name = f"run-{run_idx}"
            if run_name in all_runs_results:
                task_result = all_runs_results[run_name].get(task_key)
                if task_result:
                    success = 1 if task_result["success"] else 0
                    successes.append(success)
                    execution_times.append(task_result.get("execution_time", 0) or 0)
                    token_usages.append(task_result.get("token_usage", {}))
                    turn_counts.append(task_result.get("turn_count", 0) or 0)
                else:
                    # Task not found in this run (might be incomplete)
                    successes.append(0)
                    execution_times.append(0)
                    token_usages.append({})
                    turn_counts.append(0)
        
        # Calculate metrics
        success_count = sum(successes)
        task_metrics[task_key] = {
            "pass@k": 1 if success_count > 0 else 0,  # At least one success
            "pass^k": 1 if success_count == k else 0,  # All k runs succeed
            "avg@k": success_count / k,  # Average success rate
            "pass@1": successes[0] if successes else 0,  # First run result
            "individual_results": successes,  # All run results
            "success_count": success_count,
            "avg_execution_time": sum(execution_times) / k if k > 0 else 0,
            "avg_turn_count": sum(turn_counts) / k if k > 0 else 0,
        }
        
        # Calculate average token usage
        total_input_tokens = sum(
            tu.get("input_tokens", 0) for tu in token_usages if tu
        )
        total_output_tokens = sum(
            tu.get("output_tokens", 0) for tu in token_usages if tu
        )
        task_metrics[task_key]["avg_token_usage"] = {
            "input_tokens": total_input_tokens / k if k > 0 else 0,
            "output_tokens": total_output_tokens / k if k > 0 else 0,
            "total_tokens": (total_input_tokens + total_output_tokens) / k if k > 0 else 0,
        }
    
    return task_metrics


def aggregate_by_service_model(task_metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Aggregate task metrics by service_model combination."""
    service_model_metrics = defaultdict(lambda: {
        "tasks": [],
        "pass@k_count": 0,
        "pass^k_count": 0,
        "avg@k_sum": 0,
        "total_tasks": 0,
    })
    
    for task_key, metrics in task_metrics.items():
        # Extract service_model from task_key
        if "/" in task_key:
            parts = task_key.split("/", 1)
            service_model = parts[0]
            task_name = parts[1]
            
            sm_metrics = service_model_metrics[service_model]
            sm_metrics["tasks"].append(task_name)
            sm_metrics["pass@k_count"] += metrics["pass@k"]
            sm_metrics["pass^k_count"] += metrics["pass^k"]
            sm_metrics["avg@k_sum"] += metrics["avg@k"]
            sm_metrics["total_tasks"] += 1
    
    # Calculate final metrics
    final_metrics = {}
    for service_model, sm_metrics in service_model_metrics.items():
        total = sm_metrics["total_tasks"]
        if total > 0:
            # Calculate pass@1 (from run-1 results)
            pass_1_count = 0
            for task_key, metrics in task_metrics.items():
                if "/" in task_key and task_key.startswith(service_model + "/"):
                    pass_1_count += metrics.get("pass@1", 0)
            
            final_metrics[service_model] = {
                "total_tasks": total,
                "pass@1": round(pass_1_count / total, 4),
                "pass@k": round(sm_metrics["pass@k_count"] / total, 4),
                "pass^k": round(sm_metrics["pass^k_count"] / total, 4),
                "avg@k": round(sm_metrics["avg@k_sum"] / total, 4),
            }
    
    return final_metrics


def generate_k_run_summary(
    exp_name: str,
    k: int,
    all_runs_results: Dict[str, Dict[str, Dict[str, Any]]],
    task_metrics: Dict[str, Any],
    service_model_metrics: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate a comprehensive summary of k-run evaluation."""
    
    # Calculate overall statistics
    total_tasks = len(task_metrics)
    pass_1_count = sum(1 for m in task_metrics.values() if m.get("pass@1", 0) == 1)
    pass_k_count = sum(1 for m in task_metrics.values() if m["pass@k"] == 1)
    pass_caret_k_count = sum(1 for m in task_metrics.values() if m["pass^k"] == 1)
    avg_k_sum = sum(m["avg@k"] for m in task_metrics.values())
    
    overall_metrics = {
        "pass@1": round(pass_1_count / total_tasks, 4) if total_tasks > 0 else 0,
        "pass@k": round(pass_k_count / total_tasks, 4) if total_tasks > 0 else 0,
        "pass^k": round(pass_caret_k_count / total_tasks, 4) if total_tasks > 0 else 0,
        "avg@k": round(avg_k_sum / total_tasks, 4) if total_tasks > 0 else 0,
    }
    
    summary = {
        "experiment_name": exp_name,
        "k": k,
        "total_runs": len(all_runs_results),
        "total_unique_tasks": total_tasks,
        "overall_metrics": overall_metrics,
        "service_model_breakdown": service_model_metrics,
        "detailed_task_metrics": task_metrics,
    }
    
    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Aggregate k-run evaluation results and compute pass@k metrics"
    )
    parser.add_argument(
        "--exp-name",
        required=True,
        help="Experiment name (directory under ./results/)"
    )
    parser.add_argument(
        "--k",
        type=int,
        default=None,
        help="Number of runs (auto-detected if not specified)"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output file path for k-run summary (default: <exp-dir>/k_run_summary.json)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed metrics"
    )
    
    args = parser.parse_args()
    
    # Define paths
    results_base = Path("./results")
    exp_dir = results_base / args.exp_name
    
    if not exp_dir.exists():
        print(f"Error: Experiment directory {exp_dir} does not exist")
        return 1
    
    print(f"Processing k-run experiment: {args.exp_name}")
    print(f"Looking for run directories in: {exp_dir}")
    
    # Discover run directories
    run_dirs = discover_run_directories(exp_dir)
    
    if not run_dirs:
        print("No run directories found. This might not be a k-run experiment.")
        return 1
    
    # Auto-detect k if not specified
    k = args.k if args.k is not None else len(run_dirs)
    print(f"Found {len(run_dirs)} run directories, using k={k}")
    
    if len(run_dirs) < k:
        print(f"Warning: Only {len(run_dirs)} runs found but k={k} specified")
        k = len(run_dirs)
    
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
    
    if not any(all_runs_results.values()):
        print("No task results found in any run")
        return 1
    
    # Calculate pass@k metrics
    print("\nCalculating pass@k metrics...")
    task_metrics = calculate_pass_k_metrics(all_runs_results, k)
    
    # Aggregate by service_model
    service_model_metrics = aggregate_by_service_model(task_metrics)
    
    # Generate summary
    summary = generate_k_run_summary(
        args.exp_name, k, all_runs_results, task_metrics, service_model_metrics
    )
    
    # Save summary
    output_path = Path(args.output) if args.output else exp_dir / "k_run_summary.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ K-run summary saved to: {output_path}")
    
    # Print summary statistics
    print(f"\n📊 K-Run Evaluation Summary (k={k}):")
    print(f"{'=' * 50}")
    
    overall = summary["overall_metrics"]
    print(f"Overall Metrics:")
    print(f"  pass@1: {overall['pass@1']:.2%} (run-1 success rate)")
    print(f"  pass@{k}: {overall['pass@k']:.2%} (at least 1 success in {k} runs)")
    print(f"  pass^{k}: {overall['pass^k']:.2%} (all {k} runs succeed)")
    print(f"  avg@{k}: {overall['avg@k']:.2%} (average success rate)")
    
    if args.verbose and service_model_metrics:
        print(f"\n{'=' * 50}")
        print("Service/Model Breakdown:")
        for sm, metrics in service_model_metrics.items():
            print(f"\n{sm}:")
            print(f"  Tasks: {metrics['total_tasks']}")
            print(f"  pass@1: {metrics['pass@1']:.2%}")
            print(f"  pass@{k}: {metrics['pass@k']:.2%}")
            print(f"  pass^{k}: {metrics['pass^k']:.2%}")
            print(f"  avg@{k}: {metrics['avg@k']:.2%}")
    
    return 0


if __name__ == "__main__":
    exit(main())