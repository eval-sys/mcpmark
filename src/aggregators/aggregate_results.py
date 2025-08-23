#!/usr/bin/env python3
"""
MCPMark Results Aggregator

Aggregates evaluation results and generates simplified summary.json and tasks_folders structure.
Supports both single-run and k-run experiments.

Usage:
    python -m src.aggregators.aggregate_results <exp_name> [--push] [--force]
"""

import json
import os
import argparse
import subprocess
import shutil
import statistics
import tempfile
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any

# Pipeline retry errors that indicate incomplete/invalid results
PIPELINE_RETRY_ERRORS = [
    "State Duplication Error",
    "MCP Network Error",
]


def discover_run_directories(exp_dir: Path) -> List[Path]:
    """Discover all run-N directories in an experiment."""
    run_dirs = sorted(
        [d for d in exp_dir.iterdir() if d.is_dir() and d.name.startswith("run-")]
    )
    return run_dirs


def discover_service_model_dirs(base_dir: Path) -> List[Path]:
    """Discover all service_model directories in a run directory."""
    return [d for d in base_dir.iterdir() if d.is_dir() and "__" in d.name]


def has_pipeline_errors(meta: Dict[str, Any]) -> bool:
    """Check if a task result contains pipeline errors."""
    error_msg = meta.get("execution_result", {}).get("error_message", "")
    if error_msg:
        return any(error in error_msg for error in PIPELINE_RETRY_ERRORS)
    return False


def collect_task_results_from_run(
    run_dir: Path, force: bool = False
) -> Dict[str, Dict[str, Any]]:
    """
    Collect all task results from a single run directory.
    Returns dict mapping "service_model__task_name" to task result.
    """
    results = {}

    for service_model_dir in run_dir.iterdir():
        if not service_model_dir.is_dir() or "__" not in service_model_dir.name:
            continue

        service_model = service_model_dir.name

        for task_dir in service_model_dir.iterdir():
            if not task_dir.is_dir():
                continue
            
            # Only process directories with '__' separator
            if "__" not in task_dir.name:
                continue

            meta_path = task_dir / "meta.json"
            if not meta_path.exists():
                continue

            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)

                # Skip results with pipeline errors unless force=True
                if not force and has_pipeline_errors(meta):
                    continue

                # Use directory name as task_name (category_id__task_id format)
                task_name = task_dir.name
                task_key = f"{service_model}__{task_name}"
                results[task_key] = {
                    "success": meta.get("execution_result", {}).get(
                        "success", False
                    ),
                    "error_message": meta.get("execution_result", {}).get(
                        "error_message"
                    ),
                    "agent_execution_time": meta.get("agent_execution_time", 0),
                    "task_execution_time": meta.get("task_execution_time", 0),
                    "token_usage": meta.get("token_usage", {}),
                    "turn_count": meta.get("turn_count", 0),
                    "meta": meta,  # Keep full meta for tasks_folders
                }
            except Exception as e:
                print(f"⚠️  Error reading {meta_path}: {e}")
                continue

    return results


def calculate_k_run_metrics(
    all_runs_results: Dict[str, Dict[str, Any]], k: int
) -> Dict[str, Any]:
    """
    Calculate pass@k, pass^k, and avg@k metrics for k-run experiments.
    """
    # Get all unique task keys
    all_task_keys = set()
    for run_results in all_runs_results.values():
        all_task_keys.update(run_results.keys())

    service_model_metrics = defaultdict(
        lambda: {
            "total_tasks": 0,
            "pass@1": [],  # Will store success rates across runs for avg calculation
            "pass@k": 0.0,  # At least 1 success in k runs
            "pass^k": 0.0,  # All k runs successful
            "total_agent_execution_time": 0.0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_tokens": 0,
            "total_turns": 0,
        }
    )

    # Process each task
    for task_key in all_task_keys:
        service_model = task_key.split("__")[0]

        # Collect success/failure and metrics across all runs for this task
        run_successes = []
        task_agent_times = []
        task_input_tokens = []
        task_output_tokens = []
        task_total_tokens = []
        task_turns = []

        for run_name in sorted(all_runs_results.keys()):
            run_results = all_runs_results[run_name]
            task_result = run_results.get(
                task_key,
                {
                    "success": False,
                    "agent_execution_time": 0,
                    "token_usage": {},
                    "turn_count": 0,
                },
            )

            run_successes.append(task_result["success"])
            task_agent_times.append(task_result.get("agent_execution_time", 0) or 0)

            token_usage = task_result.get("token_usage", {})
            task_input_tokens.append(token_usage.get("input_tokens", 0) or 0)
            task_output_tokens.append(token_usage.get("output_tokens", 0) or 0)
            task_total_tokens.append(token_usage.get("total_tokens", 0) or 0)
            task_turns.append(task_result.get("turn_count", 0) or 0)

        if not run_successes:
            continue

        service_model_metrics[service_model]["total_tasks"] += 1

        # Aggregate metrics across all runs for this task
        service_model_metrics[service_model]["total_agent_execution_time"] += sum(
            task_agent_times
        )
        service_model_metrics[service_model]["total_input_tokens"] += sum(
            task_input_tokens
        )
        service_model_metrics[service_model]["total_output_tokens"] += sum(
            task_output_tokens
        )
        service_model_metrics[service_model]["total_tokens"] += sum(task_total_tokens)
        service_model_metrics[service_model]["total_turns"] += sum(task_turns)

        # pass@1: Will be calculated as avg@k later (skip individual task counting)

        # pass@k: At least one success in k runs
        if any(run_successes):
            service_model_metrics[service_model]["pass@k"] += 1

        # pass^k: All k runs successful
        if all(run_successes):
            service_model_metrics[service_model]["pass^k"] += 1

    # Calculate final percentages and metrics
    for service_model, metrics in service_model_metrics.items():
        total = metrics["total_tasks"]
        total_runs = (
            total * k if total > 0 else 1
        )  # Total number of task runs across all k runs

        if total > 0:
            metrics["pass@k"] = round(metrics["pass@k"] / total, 4)
            metrics["pass^k"] = round(metrics["pass^k"] / total, 4)

            # Calculate average metrics per task
            metrics["avg_agent_execution_time"] = round(
                metrics["total_agent_execution_time"] / total_runs, 4
            )
            metrics["avg_input_tokens"] = round(
                metrics["total_input_tokens"] / total_runs, 4
            )
            metrics["avg_output_tokens"] = round(
                metrics["total_output_tokens"] / total_runs, 4
            )
            metrics["avg_total_tokens"] = round(metrics["total_tokens"] / total_runs, 4)
            metrics["avg_turns"] = round(metrics["total_turns"] / total_runs, 4)

            # Calculate pass@1 as average success rate across all runs for this service_model (old avg@k logic)
            service_model_success_rates = []
            for run_name in sorted(all_runs_results.keys()):
                run_results = all_runs_results[run_name]
                # Get success rate for this service_model in this run
                sm_tasks = [
                    k for k in run_results.keys() if k.startswith(f"{service_model}__")
                ]
                if sm_tasks:
                    successes = sum(1 for k in sm_tasks if run_results[k]["success"])
                    rate = successes / len(sm_tasks)
                    service_model_success_rates.append(rate)

            if service_model_success_rates:
                avg_rate = statistics.mean(service_model_success_rates)
                std_rate = (
                    statistics.stdev(service_model_success_rates)
                    if len(service_model_success_rates) > 1
                    else 0.0
                )
                metrics["pass@1"] = {
                    "avg": round(avg_rate, 4),
                    "std": round(std_rate, 4),
                }
            else:
                metrics["pass@1"] = {"avg": 0.0, "std": 0.0}

    return dict(service_model_metrics)


def aggregate_single_run_results(
    exp_dir: Path, force: bool = False
) -> Dict[str, Dict[str, Any]]:
    """Aggregate results for single-run experiment."""
    service_model_results = {}

    for service_model_dir in discover_service_model_dirs(exp_dir):
        service_model = service_model_dir.name

        # Collect task results
        total_tasks = 0
        successful_tasks = 0
        total_agent_execution_time = 0.0
        total_input_tokens = 0
        total_output_tokens = 0
        total_tokens = 0
        total_turns = 0

        for task_dir in service_model_dir.iterdir():
            if not task_dir.is_dir():
                continue

            meta_path = task_dir / "meta.json"
            if not meta_path.exists():
                continue

            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)

                # Skip results with pipeline errors unless force=True
                if not force and has_pipeline_errors(meta):
                    continue

                total_tasks += 1

                execution_result = meta.get("execution_result", {})
                if execution_result.get("success", False):
                    successful_tasks += 1

                total_agent_execution_time += meta.get("agent_execution_time", 0) or 0
                token_usage = meta.get("token_usage", {})
                total_input_tokens += token_usage.get("input_tokens", 0) or 0
                total_output_tokens += token_usage.get("output_tokens", 0) or 0
                total_tokens += token_usage.get("total_tokens", 0) or 0
                total_turns += meta.get("turn_count", 0) or 0

            except Exception as e:
                print(f"⚠️  Error reading {meta_path}: {e}")
                continue

        if total_tasks > 0:
            service_model_results[service_model] = {
                "total_tasks": total_tasks,
                "successful_tasks": successful_tasks,
                "pass@1": round(successful_tasks / total_tasks, 4),
                "total_agent_execution_time": total_agent_execution_time,
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
                "total_tokens": total_tokens,
                "total_turns": total_turns,
                "avg_agent_execution_time": round(
                    total_agent_execution_time / total_tasks, 4
                ),
                "avg_input_tokens": round(total_input_tokens / total_tasks, 4),
                "avg_output_tokens": round(total_output_tokens / total_tasks, 4),
                "avg_total_tokens": round(total_tokens / total_tasks, 4),
                "avg_turns": round(total_turns / total_tasks, 4),
            }

    return service_model_results


def create_simplified_summary(
    exp_name: str, service_model_results: Dict[str, Dict[str, Any]], k: int = 1
) -> Dict[str, Any]:
    """Create simplified 3-layer JSON structure."""

    summary = {
        "generated_at": datetime.now().isoformat(),
        "experiment_name": exp_name,
        "k": k,
    }

    # Extract all unique models and services
    all_models = set()
    all_services = set()

    for service_model in service_model_results.keys():
        if "__" in service_model:
            service, model = service_model.split("__", 1)
            all_services.add(service)
            all_models.add(model)

    # Create overall metrics (aggregated across all services)
    summary["overall"] = {}
    for model in sorted(all_models):
        model_metrics = {
            "total_tasks": 0,
            "total_agent_execution_time": 0.0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_tokens": 0,
            "total_turns": 0,
        }

        model_service_data = []

        for service_model, metrics in service_model_results.items():
            if "__" in service_model and service_model.split("__", 1)[1] == model:
                model_metrics["total_tasks"] += metrics["total_tasks"]
                model_metrics["total_agent_execution_time"] += metrics.get(
                    "total_agent_execution_time", 0
                )
                model_metrics["total_input_tokens"] += metrics.get(
                    "total_input_tokens", 0
                )
                model_metrics["total_output_tokens"] += metrics.get(
                    "total_output_tokens", 0
                )
                model_metrics["total_tokens"] += metrics.get("total_tokens", 0)
                model_metrics["total_turns"] += metrics.get("total_turns", 0)

                # For pass@1, collect from each service
                model_service_data.append(metrics)

        if model_service_data:
            # Calculate average metrics per task
            total_tasks = model_metrics["total_tasks"]
            if total_tasks > 0:
                # For k-run experiments, divide by total_tasks * k to get per-run-per-task averages
                total_runs = total_tasks * k
                model_metrics["avg_agent_execution_time"] = round(
                    model_metrics["total_agent_execution_time"] / total_runs, 4
                )
                model_metrics["avg_input_tokens"] = round(
                    model_metrics["total_input_tokens"] / total_runs, 4
                )
                model_metrics["avg_output_tokens"] = round(
                    model_metrics["total_output_tokens"] / total_runs, 4
                )
                model_metrics["avg_total_tokens"] = round(
                    model_metrics["total_tokens"] / total_runs, 4
                )
                model_metrics["avg_turns"] = round(
                    model_metrics["total_turns"] / total_runs, 4
                )

            if k > 1:
                # K-run format: pass@1 (now avg@k), plus pass@k, pass^k
                pass_1_data = [data["pass@1"] for data in model_service_data]
                pass_k_rates = [data["pass@k"] for data in model_service_data]
                pass_power_k_rates = [data["pass^k"] for data in model_service_data]

                # Aggregate pass@1 avg and std across services
                avg_values = [
                    data["avg"] for data in pass_1_data if isinstance(data, dict)
                ]
                std_values = [
                    data["std"] for data in pass_1_data if isinstance(data, dict)
                ]

                if avg_values:
                    model_metrics["pass@1"] = {
                        "avg": round(statistics.mean(avg_values), 4),
                        "std": round(
                            statistics.mean(std_values) if std_values else 0.0, 4
                        ),
                    }
                else:
                    model_metrics["pass@1"] = {"avg": 0.0, "std": 0.0}
                model_metrics[f"pass@{k}"] = round(
                    statistics.mean(pass_k_rates) if pass_k_rates else 0.0, 4
                )
                model_metrics[f"pass^{k}"] = round(
                    statistics.mean(pass_power_k_rates) if pass_power_k_rates else 0.0,
                    4,
                )
            else:
                # Single run: just pass@1
                pass_1_rates = [data["pass@1"] for data in model_service_data]
                model_metrics["pass@1"] = round(
                    statistics.mean(pass_1_rates) if pass_1_rates else 0.0, 4
                )

        summary["overall"][model] = model_metrics

    # Create per-service metrics
    for service in sorted(all_services):
        summary[service] = {}

        for model in sorted(all_models):
            service_model = f"{service}_{model}"
            if service_model in service_model_results:
                metrics = service_model_results[service_model].copy()

                # Format metrics according to k-run vs single-run
                if k > 1:
                    # K-run: keep pass@k, pass^k and new metrics (no avg@k)
                    formatted_metrics = {
                        "total_tasks": metrics["total_tasks"],
                        "pass@1": metrics["pass@1"],
                        f"pass@{k}": metrics["pass@k"],
                        f"pass^{k}": metrics["pass^k"],
                        "total_agent_execution_time": metrics.get(
                            "total_agent_execution_time", 0.0
                        ),
                        "total_input_tokens": metrics.get("total_input_tokens", 0),
                        "total_output_tokens": metrics.get("total_output_tokens", 0),
                        "total_tokens": metrics.get("total_tokens", 0),
                        "total_turns": metrics.get("total_turns", 0),
                        "avg_agent_execution_time": metrics.get(
                            "avg_agent_execution_time", 0.0
                        ),
                        "avg_input_tokens": metrics.get("avg_input_tokens", 0.0),
                        "avg_output_tokens": metrics.get("avg_output_tokens", 0.0),
                        "avg_total_tokens": metrics.get("avg_total_tokens", 0.0),
                        "avg_turns": metrics.get("avg_turns", 0.0),
                    }
                else:
                    # Single run: keep all metrics
                    formatted_metrics = {
                        "total_tasks": metrics["total_tasks"],
                        "pass@1": metrics["pass@1"],
                        "total_agent_execution_time": metrics.get(
                            "total_agent_execution_time", 0.0
                        ),
                        "total_input_tokens": metrics.get("total_input_tokens", 0),
                        "total_output_tokens": metrics.get("total_output_tokens", 0),
                        "total_tokens": metrics.get("total_tokens", 0),
                        "total_turns": metrics.get("total_turns", 0),
                        "avg_agent_execution_time": metrics.get(
                            "avg_agent_execution_time", 0.0
                        ),
                        "avg_input_tokens": metrics.get("avg_input_tokens", 0.0),
                        "avg_output_tokens": metrics.get("avg_output_tokens", 0.0),
                        "avg_total_tokens": metrics.get("avg_total_tokens", 0.0),
                        "avg_turns": metrics.get("avg_turns", 0.0),
                    }

                summary[service][model] = formatted_metrics

    return summary


def generate_tasks_folders(exp_dir: Path, k: int = 1, force: bool = False) -> str:
    """Generate tasks_folders directory structure."""

    if k > 1:
        tasks_folders_dir = exp_dir / "tasks_folders"
        run_dirs = discover_run_directories(exp_dir)
    else:
        tasks_folders_dir = exp_dir / "tasks_folders"
        run_dirs = [exp_dir]

    # Remove existing tasks_folders if it exists
    if tasks_folders_dir.exists():
        shutil.rmtree(tasks_folders_dir)

    tasks_folders_dir.mkdir(parents=True, exist_ok=True)

    # Collect all task data organized by model
    model_task_data = defaultdict(dict)

    for run_idx, run_dir in enumerate(run_dirs, 1):
        run_name = f"run-{run_idx}" if k > 1 else "run-1"

        for service_model_dir in discover_service_model_dirs(run_dir):
            service_model = service_model_dir.name

            if "__" not in service_model:
                continue

            service, model = service_model.split("__", 1)

            for task_dir in service_model_dir.iterdir():
                if not task_dir.is_dir():
                    continue
                
                # Only process directories with '__' separator
                if "__" not in task_dir.name:
                    continue

                meta_path = task_dir / "meta.json"
                if not meta_path.exists():
                    continue

                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)

                    # Skip results with pipeline errors unless force=True
                    if not force and has_pipeline_errors(meta):
                        continue

                    # Use directory name as task_name (category_id__task_id format)
                    task_name = task_dir.name

                    # Initialize task structure if not exists
                    if task_name not in model_task_data[model]:
                        model_task_data[model][task_name] = {
                            "task_name": task_name,
                            "service": service,
                            "model": model,
                            "runs": {},
                        }

                    # Store run result with original field names
                    execution_result = meta.get("execution_result", {})
                    model_task_data[model][task_name]["runs"][run_name] = {
                        "agent_execution_time": meta.get("agent_execution_time", 0),
                        "task_execution_time": meta.get("task_execution_time", 0),
                        "execution_result": execution_result,
                        "token_usage": meta.get("token_usage", {}),
                        "turn_count": meta.get("turn_count", 0),
                    }

                except Exception as e:
                    print(f"⚠️  Error reading {meta_path}: {e}")
                    continue

    # Create individual model directories and task files
    for model, tasks in model_task_data.items():
        model_dir = tasks_folders_dir / model
        model_dir.mkdir(exist_ok=True)

        for task_name, task_data in tasks.items():
            # Task name is already in category_id__task_id format, use as-is
            task_file = model_dir / f"{task_name}.json"

            with open(task_file, "w", encoding="utf-8") as f:
                json.dump(task_data, f, indent=2, ensure_ascii=False)

    return str(tasks_folders_dir)


def generate_readme_content(exp_name: str, summary: Dict[str, Any]) -> str:
    """Generate README.md content based on simplified summary structure."""
    content = []

    # Header
    content.append(f"# {exp_name} - Evaluation Results")
    content.append("")
    content.append(f"Generated: {summary.get('generated_at', 'N/A')}")
    content.append("")

    k = summary.get("k", 1)
    overall_data = summary.get("overall", {})

    if overall_data:
        # Overall Models Performance
        content.append("## Overall Models Performance")
        content.append("")
        content.append("Performance across all MCP services combined:")
        content.append("")

        if k > 1:
            content.append(
                f"| Model | Total Tasks | Pass@1 (avg ± std) | Pass@{k} | Pass^{k} | Avg Agent Time (s) |"
            )
            content.append(
                "|-------|-------------|--------|----------|----------|-------------------|"
            )

            def get_pass_1_value(x):
                pass_1 = x[1].get("pass@1", 0)
                if isinstance(pass_1, dict):
                    return pass_1.get("avg", 0)
                return pass_1

            sorted_models = sorted(
                overall_data.items(), key=get_pass_1_value, reverse=True
            )

            for model, metrics in sorted_models:
                tasks = metrics.get("total_tasks", 0)
                pass_1_data = metrics.get("pass@1", {"avg": 0, "std": 0})
                if isinstance(pass_1_data, dict):
                    pass_1_str = f"{pass_1_data['avg'] * 100:.1f}% ± {pass_1_data['std'] * 100:.1f}%"
                else:
                    pass_1_str = f"{pass_1_data * 100:.1f}%"
                pass_k = metrics.get(f"pass@{k}", 0) * 100
                pass_power_k = metrics.get(f"pass^{k}", 0) * 100
                avg_time = metrics.get("avg_agent_execution_time", 0)

                content.append(
                    f"| {model} | {tasks} | {pass_1_str} | {pass_k:.1f}% | {pass_power_k:.1f}% | {avg_time:.2f} |"
                )
        else:
            content.append(
                "| Model | Total Tasks | Pass@1 | Total Tokens | Total Turns | Avg Agent Time (s) |"
            )
            content.append(
                "|-------|-------------|--------|--------------|-------------|-------------------|"
            )

            def get_pass_1_value(x):
                pass_1 = x[1].get("pass@1", 0)
                if isinstance(pass_1, dict):
                    return pass_1.get("avg", 0)
                return pass_1

            sorted_models = sorted(
                overall_data.items(), key=get_pass_1_value, reverse=True
            )

            for model, metrics in sorted_models:
                tasks = metrics.get("total_tasks", 0)
                pass_1_data = metrics.get("pass@1", 0)
                if isinstance(pass_1_data, dict):
                    pass_1_str = f"{pass_1_data['avg'] * 100:.1f}% ± {pass_1_data['std'] * 100:.1f}%"
                else:
                    pass_1_str = f"{pass_1_data * 100:.1f}%"
                tokens = metrics.get("total_tokens", 0)
                turns = metrics.get("total_turns", 0)
                avg_time = metrics.get("avg_agent_execution_time", 0)

                content.append(
                    f"| {model} | {tasks} | {pass_1_str} | {tokens:,} | {turns} | {avg_time:.2f} |"
                )

        content.append("")

    # Per-service performance
    content.append("## Performance by MCP Service")
    content.append("")

    service_keys = [
        key
        for key in summary.keys()
        if key not in ["generated_at", "experiment_name", "k", "overall"]
    ]

    for service in sorted(service_keys):
        service_data = summary.get(service, {})
        if not service_data:
            continue

        content.append(f"### {service.capitalize()}")
        content.append("")

        if k > 1:
            content.append(
                f"| Model | Tasks | Pass@1 (avg ± std) | Pass@{k} | Pass^{k} | Avg Agent Time (s) |"
            )
            content.append(
                "|-------|-------|--------|----------|----------|-------------------|"
            )

            def get_pass_1_value(x):
                pass_1 = x[1].get("pass@1", 0)
                if isinstance(pass_1, dict):
                    return pass_1.get("avg", 0)
                return pass_1

            sorted_models = sorted(
                service_data.items(), key=get_pass_1_value, reverse=True
            )

            for model, metrics in sorted_models:
                tasks = metrics.get("total_tasks", 0)
                pass_1_data = metrics.get("pass@1", {"avg": 0, "std": 0})
                if isinstance(pass_1_data, dict):
                    pass_1_str = f"{pass_1_data['avg'] * 100:.1f}% ± {pass_1_data['std'] * 100:.1f}%"
                else:
                    pass_1_str = f"{pass_1_data * 100:.1f}%"
                pass_k = metrics.get(f"pass@{k}", 0) * 100
                pass_power_k = metrics.get(f"pass^{k}", 0) * 100
                avg_time = metrics.get("avg_agent_execution_time", 0)

                content.append(
                    f"| {model} | {tasks} | {pass_1_str} | {pass_k:.1f}% | {pass_power_k:.1f}% | {avg_time:.2f} |"
                )
        else:
            content.append(
                "| Model | Tasks | Pass@1 | Total Tokens | Total Turns | Avg Agent Time (s) |"
            )
            content.append(
                "|-------|-------|--------|--------------|-------------|-------------------|"
            )

            def get_pass_1_value(x):
                pass_1 = x[1].get("pass@1", 0)
                if isinstance(pass_1, dict):
                    return pass_1.get("avg", 0)
                return pass_1

            sorted_models = sorted(
                service_data.items(), key=get_pass_1_value, reverse=True
            )

            for model, metrics in sorted_models:
                tasks = metrics.get("total_tasks", 0)
                pass_1_data = metrics.get("pass@1", 0)
                if isinstance(pass_1_data, dict):
                    pass_1_str = f"{pass_1_data['avg'] * 100:.1f}% ± {pass_1_data['std'] * 100:.1f}%"
                else:
                    pass_1_str = f"{pass_1_data * 100:.1f}%"
                tokens = metrics.get("total_tokens", 0)
                turns = metrics.get("total_turns", 0)
                avg_time = metrics.get("avg_agent_execution_time", 0)

                content.append(
                    f"| {model} | {tasks} | {pass_1_str} | {tokens:,} | {turns} | {avg_time:.2f} |"
                )

        content.append("")

    return "\n".join(content)


def push_to_experiments_repo(
    exp_name: str, summary_file_path: Path, readme_content: str, tasks_folders_path: str
) -> bool:
    """Push results to eval-sys/mcpmark-experiments repository."""

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir = Path(temp_dir)

            print("📥 Cloning experiments repository...")
            subprocess.run(
                [
                    "git",
                    "clone",
                    "git@github.com:eval-sys/mcpmark-experiments.git",
                    str(temp_dir),
                ],
                check=True,
                capture_output=True,
            )

            # Copy summary.json
            dest_summary = temp_dir / "summary.json"
            shutil.copy2(summary_file_path, dest_summary)
            print("  📄 summary.json")

            # Create README.md
            readme_path = temp_dir / "README.md"
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(readme_content)
            print("  📄 README.md")

            # Copy tasks_folders
            if Path(tasks_folders_path).exists():
                dest_tasks_folders = temp_dir / "tasks_folders"
                if dest_tasks_folders.exists():
                    shutil.rmtree(dest_tasks_folders)
                shutil.copytree(tasks_folders_path, dest_tasks_folders)
                print("  📁 tasks_folders/")

            # Git operations
            os.chdir(temp_dir)
            subprocess.run(["git", "add", "."], check=True)

            # Check if there are changes
            result = subprocess.run(
                ["git", "diff", "--staged", "--name-only"],
                capture_output=True,
                text=True,
            )

            if not result.stdout.strip():
                print("✅ No changes to push (files are up to date)")
                return True

            # Commit and push
            commit_msg = f"Update experiment results for {exp_name}"
            subprocess.run(["git", "commit", "-m", commit_msg], check=True)

            print("🚀 Pushing to remote repository...")
            subprocess.run(["git", "push"], check=True)
            print("✅ Successfully pushed to experiments repository")

            return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Git operation failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Error pushing to experiments repo: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Aggregate mcpmark evaluation results and generate simplified summary"
    )
    parser.add_argument(
        "--exp-name", help="Experiment name (directory under ./results/)"
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push results to eval-sys/mcpmark-experiments repository",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Process incomplete/invalid results (ignore pipeline errors)",
    )

    args = parser.parse_args()

    # Validate experiment directory
    results_base = Path("./results")
    exp_dir = results_base / args.exp_name

    if not exp_dir.exists():
        print(f"❌ Error: Experiment directory {exp_dir} does not exist")
        return 1

    print(f"🔄 Processing experiment: {args.exp_name}")
    if args.force:
        print("⚠️  Using --force: including incomplete/invalid results")

    # Detect experiment type
    run_dirs = discover_run_directories(exp_dir)
    k = len(run_dirs) if run_dirs else 1

    if k > 1:
        print(f"📊 Detected {k}-run experiment structure")

        # Collect results from all runs
        all_runs_results = {}
        for run_dir in run_dirs:
            run_name = run_dir.name
            print(f"  Processing {run_name}...")
            run_results = collect_task_results_from_run(run_dir, args.force)
            all_runs_results[run_name] = run_results

        # Calculate k-run metrics
        service_model_metrics = calculate_k_run_metrics(all_runs_results, k)

    else:
        print("📊 Detected single-run experiment")
        service_model_metrics = aggregate_single_run_results(exp_dir, args.force)

    if not service_model_metrics:
        print("❌ No valid results found to aggregate")
        return 1

    # Generate simplified summary
    print("📋 Generating simplified summary...")
    summary = create_simplified_summary(args.exp_name, service_model_metrics, k)

    # Save summary.json
    if k > 1:
        summary_path = exp_dir / "summary.json"
    else:
        summary_path = exp_dir / "summary.json"

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"✅ Summary saved to: {summary_path}")

    # Generate tasks_folders
    print("📁 Generating tasks_folders...")
    tasks_folders_path = generate_tasks_folders(exp_dir, k, args.force)
    print(f"✅ Tasks folders created at: {tasks_folders_path}")

    # Push to repository if requested
    if args.push:
        print("\n🚀 Pushing to experiments repository...")

        readme_content = generate_readme_content(args.exp_name, summary)

        success = push_to_experiments_repo(
            args.exp_name, summary_path, readme_content, tasks_folders_path
        )

        if not success:
            print("❌ Failed to push to experiments repository")
            return 1

        print("🎉 Successfully pushed: summary.json, README.md, tasks_folders/")

    print(f"\n🎉 Processing complete for {args.exp_name}")
    return 0


if __name__ == "__main__":
    exit(main())
