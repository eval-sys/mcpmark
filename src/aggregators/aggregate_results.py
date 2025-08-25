#!/usr/bin/env python3
"""
MCPMark Results Aggregator

Aggregates evaluation results and generates simplified summary.json and model_results/task_results structure.
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

# Model pricing per million tokens (input, output)
MODEL_PRICING = {
    "claude-4-1-opus": {"input": 15.0, "output": 75.0},
    "claude-4-sonnet": {"input": 3.0, "output": 15.0},
    "deepseek-chat": {"input": 0.27, "output": 1.1},
    "gemini-2-5-pro": {"input": 2.5, "output": 15.0},
    "gpt-5": {"input": 1.25, "output": 10.0},
    "o3": {"input": 2.0, "output": 0.5},
    "grok-4": {"input": 3.0, "output": 15.0},
    "k2": {"input": 0.15, "output": 2.0},
    "qwen-3-coder": {"input": 0.3, "output": 1.5},
}


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


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost based on model pricing and token usage."""
    # Find the pricing for this model
    pricing = None
    for model_key, model_pricing in MODEL_PRICING.items():
        if model_key in model:
            pricing = model_pricing
            break
    
    if not pricing:
        return 0.0
    
    # Calculate cost (pricing is per million tokens)
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return round(input_cost + output_cost, 4)


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
                    "success": meta.get("execution_result", {}).get("success", False),
                    "error_message": meta.get("execution_result", {}).get(
                        "error_message"
                    ),
                    "agent_execution_time": meta.get("agent_execution_time", 0),
                    "task_execution_time": meta.get("task_execution_time", 0),
                    "token_usage": meta.get("token_usage", {}),
                    "turn_count": meta.get("turn_count", 0),
                    "actual_model_name": meta.get("actual_model_name"),
                    "meta": meta,  # Keep full meta for model_results
                }
            except Exception as e:
                print(f"⚠️  Error reading {meta_path}: {e}")
                continue

    return results


def calculate_k_run_metrics(
    all_runs_results: Dict[str, Dict[str, Any]],
    k: int,
    single_run_models: List[str] = None,
) -> Dict[str, Any]:
    """
    Calculate pass@k, pass^k, and avg@k metrics for k-run experiments.
    For single_run_models, only use run-1 data and skip pass@k/pass^k metrics.
    """
    if single_run_models is None:
        single_run_models = []
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
            "actual_model_name": None,
        }
    )

    # Process each task
    for task_key in all_task_keys:
        # Extract service__model from service__model__category__task format
        parts = task_key.split("__")
        if len(parts) >= 2:
            service_model = f"{parts[0]}__{parts[1]}"
        else:
            continue

        # Check if this model is a single-run model
        is_single_run_model = any(model in service_model for model in single_run_models)

        # Collect success/failure and metrics across all runs for this task
        run_successes = []
        task_agent_times = []
        task_input_tokens = []
        task_output_tokens = []
        task_total_tokens = []
        task_turns = []

        # For single-run models, only use run-1 data
        runs_to_process = (
            ["run-1"] if is_single_run_model else sorted(all_runs_results.keys())
        )

        for run_name in runs_to_process:
            if run_name not in all_runs_results:
                # If run-1 doesn't exist for single-run model, skip this task
                if is_single_run_model:
                    continue
                else:
                    run_results = {}
            else:
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

        # Store actual_model_name from first available task result
        if service_model_metrics[service_model]["actual_model_name"] is None:
            for run_name in runs_to_process:
                if run_name in all_runs_results:
                    run_results = all_runs_results[run_name]
                    task_result = run_results.get(task_key)
                    if task_result and task_result.get("actual_model_name"):
                        service_model_metrics[service_model]["actual_model_name"] = task_result["actual_model_name"]
                        break

        # pass@1: Will be calculated as avg@k later (skip individual task counting)

        # For single-run models, only count pass@1 (success in run-1)
        # For k-run models, calculate pass@k and pass^k as usual
        if not is_single_run_model:
            # pass@k: At least one success in k runs
            if any(run_successes):
                service_model_metrics[service_model]["pass@k"] += 1

            # pass^k: All k runs successful
            if all(run_successes):
                service_model_metrics[service_model]["pass^k"] += 1

    # Calculate final percentages and metrics
    for service_model, metrics in service_model_metrics.items():
        total = metrics["total_tasks"]

        # Check if this is a single-run model
        is_single_run_model = any(model in service_model for model in single_run_models)

        if total > 0:
            # Only calculate pass@k and pass^k for non-single-run models
            if not is_single_run_model:
                metrics["pass@k"] = round(metrics["pass@k"] / total, 4)
                metrics["pass^k"] = round(metrics["pass^k"] / total, 4)
            else:
                # Remove pass@k and pass^k for single-run models
                metrics.pop("pass@k", None)
                metrics.pop("pass^k", None)

            # Calculate average metrics per task
            # For single-run models: divide by total (task count) since we only have 1 run per task
            # For k-run models: divide by total * k since we have k runs per task
            divisor = total if is_single_run_model else (total * k)

            metrics["avg_agent_execution_time"] = round(
                metrics["total_agent_execution_time"] / divisor, 4
            )
            metrics["avg_input_tokens"] = round(
                metrics["total_input_tokens"] / divisor, 4
            )
            metrics["avg_output_tokens"] = round(
                metrics["total_output_tokens"] / divisor, 4
            )
            metrics["avg_total_tokens"] = round(metrics["total_tokens"] / divisor, 4)
            metrics["avg_turns"] = round(metrics["total_turns"] / divisor, 4)

            # Calculate pass@1
            if is_single_run_model:
                # For single-run models, use only run-1 data
                if "run-1" in all_runs_results:
                    run_results = all_runs_results["run-1"]
                    sm_tasks = [
                        k
                        for k in run_results.keys()
                        if k.startswith(f"{service_model}__")
                    ]
                    if sm_tasks:
                        successes = sum(
                            1 for k in sm_tasks if run_results[k]["success"]
                        )
                        rate = successes / len(sm_tasks)
                        metrics["pass@1"] = {
                            "avg": round(rate, 4),
                            "std": 0.0  # Single run, so std is 0
                        }
                    else:
                        metrics["pass@1"] = {"avg": 0.0, "std": 0.0}
                else:
                    metrics["pass@1"] = {"avg": 0.0, "std": 0.0}
            else:
                # For k-run models, calculate as average success rate across all runs
                service_model_success_rates = []
                for run_name in sorted(all_runs_results.keys()):
                    run_results = all_runs_results[run_name]
                    # Get success rate for this service_model in this run
                    sm_tasks = [
                        k
                        for k in run_results.keys()
                        if k.startswith(f"{service_model}__")
                    ]
                    if sm_tasks:
                        successes = sum(
                            1 for k in sm_tasks if run_results[k]["success"]
                        )
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
        actual_model_name = None

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
                
                # Store actual_model_name from first available meta
                if actual_model_name is None and meta.get("actual_model_name"):
                    actual_model_name = meta.get("actual_model_name")

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
                "actual_model_name": actual_model_name,
            }

    return service_model_results


def create_simplified_summary(
    exp_name: str,
    service_model_results: Dict[str, Dict[str, Any]],
    k: int = 1,
    single_run_models: List[str] = None,
) -> Dict[str, Any]:
    """Create simplified 3-layer JSON structure."""
    if single_run_models is None:
        single_run_models = []

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
                # Check if this is a single-run model
                is_single_run_model = any(m in model for m in single_run_models)

                # For single-run models: divide by total_tasks since only 1 run per task
                # For k-run models: divide by total_tasks * k since k runs per task
                divisor = total_tasks if is_single_run_model else (total_tasks * k)

                model_metrics["avg_agent_execution_time"] = round(
                    model_metrics["total_agent_execution_time"] / divisor, 4
                )
                model_metrics["avg_input_tokens"] = round(
                    model_metrics["total_input_tokens"] / divisor, 4
                )
                model_metrics["avg_output_tokens"] = round(
                    model_metrics["total_output_tokens"] / divisor, 4
                )
                model_metrics["avg_total_tokens"] = round(
                    model_metrics["total_tokens"] / divisor, 4
                )
                model_metrics["avg_turns"] = round(
                    model_metrics["total_turns"] / divisor, 4
                )

                # Calculate per-run metrics for overall section
                runs_divisor = 1 if is_single_run_model else k
                per_run_input_tokens = model_metrics["total_input_tokens"] // runs_divisor
                per_run_output_tokens = model_metrics["total_output_tokens"] // runs_divisor
                per_run_cost = calculate_cost(model, per_run_input_tokens, per_run_output_tokens)
                
                model_metrics["per_run_input_tokens"] = per_run_input_tokens
                model_metrics["per_run_output_tokens"] = per_run_output_tokens
                model_metrics["per_run_cost"] = per_run_cost
                
                # Set actual_model_name from first available service data
                for service_model, metrics in service_model_results.items():
                    if "__" in service_model and service_model.split("__", 1)[1] == model:
                        if metrics.get("actual_model_name"):
                            model_metrics["actual_model_name"] = metrics["actual_model_name"]
                            break

            if k > 1:
                # K-run format: pass@1 (now avg@k), plus pass@k, pass^k
                pass_1_data = [data["pass@1"] for data in model_service_data]

                if is_single_run_model:
                    # For single-run models, pass@1 is a dict with avg and std=0
                    avg_values = [
                        data["avg"] for data in pass_1_data if isinstance(data, dict)
                    ]
                    if avg_values:
                        model_metrics["pass@1"] = {
                            "avg": round(statistics.mean(avg_values), 4),
                            "std": 0.0  # Single run across services, so std is 0
                        }
                    else:
                        model_metrics["pass@1"] = {"avg": 0.0, "std": 0.0}
                    # Don't add pass@k or pass^k metrics
                else:
                    # For k-run models, pass@1 is dict with avg/std
                    pass_k_rates = [
                        data.get("pass@k", 0)
                        for data in model_service_data
                        if "pass@k" in data
                    ]
                    pass_power_k_rates = [
                        data.get("pass^k", 0)
                        for data in model_service_data
                        if "pass^k" in data
                    ]

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
                        statistics.mean(pass_power_k_rates)
                        if pass_power_k_rates
                        else 0.0,
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
            service_model = f"{service}__{model}"
            if service_model in service_model_results:
                metrics = service_model_results[service_model].copy()

                # Check if this model is a single-run model
                is_single_run_model = any(m in model for m in single_run_models)

                # Calculate per-run metrics
                runs_divisor = 1 if is_single_run_model else k
                per_run_input_tokens = metrics.get("total_input_tokens", 0) // runs_divisor
                per_run_output_tokens = metrics.get("total_output_tokens", 0) // runs_divisor
                per_run_cost = calculate_cost(model, per_run_input_tokens, per_run_output_tokens)

                # Format metrics according to k-run vs single-run
                if k > 1:
                    # K-run: keep pass@k, pass^k and new metrics (no avg@k)
                    if is_single_run_model:
                        # Single-run model in k-run experiment: no pass@k/pass^k
                        formatted_metrics = {
                            "total_tasks": metrics["total_tasks"],
                            "pass@1": metrics["pass@1"],
                            "total_agent_execution_time": metrics.get(
                                "total_agent_execution_time", 0.0
                            ),
                            "total_input_tokens": metrics.get("total_input_tokens", 0),
                            "total_output_tokens": metrics.get(
                                "total_output_tokens", 0
                            ),
                            "total_tokens": metrics.get("total_tokens", 0),
                            "total_turns": metrics.get("total_turns", 0),
                            "avg_agent_execution_time": metrics.get(
                                "avg_agent_execution_time", 0.0
                            ),
                            "avg_input_tokens": metrics.get("avg_input_tokens", 0.0),
                            "avg_output_tokens": metrics.get("avg_output_tokens", 0.0),
                            "avg_total_tokens": metrics.get("avg_total_tokens", 0.0),
                            "avg_turns": metrics.get("avg_turns", 0.0),
                            "per_run_input_tokens": per_run_input_tokens,
                            "per_run_output_tokens": per_run_output_tokens,
                            "per_run_cost": per_run_cost,
                        }
                    else:
                        formatted_metrics = {
                            "total_tasks": metrics["total_tasks"],
                            "pass@1": metrics["pass@1"],
                            f"pass@{k}": metrics.get("pass@k", 0),
                            f"pass^{k}": metrics.get("pass^k", 0),
                            "total_agent_execution_time": metrics.get(
                                "total_agent_execution_time", 0.0
                            ),
                            "total_input_tokens": metrics.get("total_input_tokens", 0),
                            "total_output_tokens": metrics.get(
                                "total_output_tokens", 0
                            ),
                            "total_tokens": metrics.get("total_tokens", 0),
                            "total_turns": metrics.get("total_turns", 0),
                            "avg_agent_execution_time": metrics.get(
                                "avg_agent_execution_time", 0.0
                            ),
                            "avg_input_tokens": metrics.get("avg_input_tokens", 0.0),
                            "avg_output_tokens": metrics.get("avg_output_tokens", 0.0),
                            "avg_total_tokens": metrics.get("avg_total_tokens", 0.0),
                            "avg_turns": metrics.get("avg_turns", 0.0),
                            "per_run_input_tokens": per_run_input_tokens,
                            "per_run_output_tokens": per_run_output_tokens,
                            "per_run_cost": per_run_cost,
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
                        "per_run_input_tokens": per_run_input_tokens,
                        "per_run_output_tokens": per_run_output_tokens,
                        "per_run_cost": per_run_cost,
                    }

                # Add actual_model_name to service-level metrics
                formatted_metrics["actual_model_name"] = metrics.get("actual_model_name")
                summary[service][model] = formatted_metrics

    return summary


def generate_model_results(
    exp_dir: Path, k: int = 1, force: bool = False, single_run_models: List[str] = None
) -> str:
    """Generate model_results directory structure."""
    if single_run_models is None:
        single_run_models = []

    if k > 1:
        model_results_dir = exp_dir / "model_results"
        run_dirs = discover_run_directories(exp_dir)
    else:
        model_results_dir = exp_dir / "model_results"
        run_dirs = [exp_dir]

    # Remove existing model_results if it exists
    if model_results_dir.exists():
        shutil.rmtree(model_results_dir)

    model_results_dir.mkdir(parents=True, exist_ok=True)

    # Collect all task data organized by model
    model_task_data = defaultdict(dict)

    for run_idx, run_dir in enumerate(run_dirs, 1):
        run_name = f"run-{run_idx}" if k > 1 else "run-1"

        for service_model_dir in discover_service_model_dirs(run_dir):
            service_model = service_model_dir.name

            if "__" not in service_model:
                continue

            service, model = service_model.split("__", 1)

            # For single-run models, only process run-1
            is_single_run_model = any(m in model for m in single_run_models)
            if is_single_run_model and run_name != "run-1":
                continue

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
        model_dir = model_results_dir / model
        model_dir.mkdir(exist_ok=True)

        for task_name, task_data in tasks.items():
            # Task name is already in category_id__task_id format, use as-is
            task_file = model_dir / f"{task_name}.json"

            with open(task_file, "w", encoding="utf-8") as f:
                json.dump(task_data, f, indent=2, ensure_ascii=False)

    return str(model_results_dir)


def generate_task_results(
    exp_dir: Path, k: int = 1, force: bool = False, single_run_models: List[str] = None
) -> str:
    """Generate task_results directory structure with task-centric organization."""
    if single_run_models is None:
        single_run_models = []

    if k > 1:
        task_results_dir = exp_dir / "task_results"
        run_dirs = discover_run_directories(exp_dir)
    else:
        task_results_dir = exp_dir / "task_results"
        run_dirs = [exp_dir]

    # Remove existing task_results if it exists
    if task_results_dir.exists():
        shutil.rmtree(task_results_dir)

    task_results_dir.mkdir(parents=True, exist_ok=True)

    # Collect all task data organized by task ID
    task_data = defaultdict(
        lambda: {
            "task_id": None,
            "models": defaultdict(lambda: {"runs": [], "summary": {}}),
            "overview": {},
        }
    )

    for run_idx, run_dir in enumerate(run_dirs, 1):
        run_name = f"run-{run_idx}" if k > 1 else "run-1"

        for service_model_dir in discover_service_model_dirs(run_dir):
            service_model = service_model_dir.name

            if "__" not in service_model:
                continue

            service, model = service_model.split("__", 1)

            # For single-run models, only process run-1
            is_single_run_model = any(m in model for m in single_run_models)
            if is_single_run_model and run_name != "run-1":
                continue

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

                    # Set task_id if not already set
                    if task_data[task_name]["task_id"] is None:
                        task_data[task_name]["task_id"] = task_name

                    # Extract data for this run
                    execution_result = meta.get("execution_result", {})
                    token_usage = meta.get("token_usage", {})

                    run_data = {
                        "run": run_name,
                        "success": execution_result.get("success", False),
                        "token_usage": {
                            "input_tokens": token_usage.get("input_tokens", 0) or 0,
                            "output_tokens": token_usage.get("output_tokens", 0) or 0,
                            "total_tokens": token_usage.get("total_tokens", 0) or 0,
                        },
                        "agent_execution_time": meta.get("agent_execution_time", 0)
                        or 0,
                        "turn_count": meta.get("turn_count", 0) or 0,
                    }

                    # Add to model's run list
                    task_data[task_name]["models"][model]["runs"].append(run_data)

                except Exception as e:
                    print(f"⚠️  Error reading {meta_path}: {e}")
                    continue

    # Calculate overview statistics for each task and save JSON files
    for task_name, data in task_data.items():
        if not data["models"]:
            continue

        # Calculate overview statistics and per-model statistics
        total_runs = 0
        total_successes = 0
        total_input_tokens = 0
        total_output_tokens = 0
        total_tokens = 0
        total_agent_time = 0
        total_turns = 0

        for model, model_data in data["models"].items():
            runs = model_data["runs"]

            # Calculate per-model statistics
            model_successes = 0
            model_input_tokens = 0
            model_output_tokens = 0
            model_total_tokens = 0
            model_agent_time = 0
            model_turns = 0

            for run in runs:
                total_runs += 1
                if run["success"]:
                    total_successes += 1
                    model_successes += 1

                total_input_tokens += run["token_usage"]["input_tokens"]
                total_output_tokens += run["token_usage"]["output_tokens"]
                total_tokens += run["token_usage"]["total_tokens"]
                total_agent_time += run["agent_execution_time"]
                total_turns += run["turn_count"]

                model_input_tokens += run["token_usage"]["input_tokens"]
                model_output_tokens += run["token_usage"]["output_tokens"]
                model_total_tokens += run["token_usage"]["total_tokens"]
                model_agent_time += run["agent_execution_time"]
                model_turns += run["turn_count"]

            # Calculate model summary statistics
            num_runs = len(runs)
            if num_runs > 0:
                # Check if this is a single-run model
                is_single_run_model = any(m in model for m in single_run_models)

                model_summary = {
                    "total_runs": num_runs,
                    "successful_runs": model_successes,
                    "avg_agent_execution_time": round(model_agent_time / num_runs, 2),
                    "avg_input_tokens": round(model_input_tokens / num_runs, 2),
                    "avg_output_tokens": round(model_output_tokens / num_runs, 2),
                    "avg_total_tokens": round(model_total_tokens / num_runs, 2),
                    "avg_turn_count": round(model_turns / num_runs, 2),
                }

                # Add pass@k and pass^k for k-run experiments (but not for single-run models)
                if k > 1 and not is_single_run_model:
                    # pass@k: at least one success
                    model_summary[f"pass@{k}"] = 1.0 if model_successes > 0 else 0.0
                    # pass^k: all runs successful
                    model_summary[f"pass^{k}"] = (
                        1.0 if model_successes == num_runs else 0.0
                    )

                model_data["summary"] = model_summary

        # Set overview
        data["overview"] = {
            "total_models": len(data["models"]),
            "total_runs": total_runs,
            "avg_success_rate": round(total_successes / total_runs, 4)
            if total_runs > 0
            else 0.0,
            "avg_input_tokens": round(total_input_tokens / total_runs, 2)
            if total_runs > 0
            else 0.0,
            "avg_output_tokens": round(total_output_tokens / total_runs, 2)
            if total_runs > 0
            else 0.0,
            "avg_total_tokens": round(total_tokens / total_runs, 2)
            if total_runs > 0
            else 0.0,
            "avg_agent_execution_time": round(total_agent_time / total_runs, 2)
            if total_runs > 0
            else 0.0,
            "avg_turn_count": round(total_turns / total_runs, 2)
            if total_runs > 0
            else 0.0,
        }

        # Convert defaultdict to regular dict for JSON serialization
        # Also convert nested model defaultdicts
        models_dict = {}
        for model_name, model_data in data["models"].items():
            models_dict[model_name] = {
                "runs": model_data["runs"],
                "summary": model_data["summary"],
            }
        data["models"] = models_dict

        # Save JSON file
        task_file = task_results_dir / f"{task_name}.json"
        with open(task_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    return str(task_results_dir)


def generate_readme_content(
    exp_name: str, summary: Dict[str, Any], single_run_models: List[str] = None
) -> str:
    """Generate README.md content based on simplified summary structure."""
    if single_run_models is None:
        single_run_models = []

    content = []

    # Header
    content.append(f"# {exp_name} - Evaluation Results")
    content.append("")
    content.append(f"Generated: {summary.get('generated_at', 'N/A')}")
    content.append("")

    # Add note about single-run models if applicable
    k = summary.get("k", 1)
    if k > 1 and single_run_models:
        content.append("## Note on Evaluation Runs")
        content.append("")
        content.append(
            f"This evaluation includes Pass@{k} metrics for most models. However, the following models were only evaluated with Pass@1 due to cost constraints:"
        )
        content.append("")
        for model in single_run_models:
            content.append(f"- {model}")
        content.append("")
        content.append(
            f"For these models, Pass@{k} and Pass^{k} metrics are shown as '/' in the tables below."
        )
        content.append("")

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

                # Check if this is a single-run model
                is_single_run_model = any(m in model for m in single_run_models)

                if is_single_run_model:
                    pass_k_str = "/"
                    pass_power_k_str = "/"
                else:
                    pass_k = metrics.get(f"pass@{k}", 0) * 100
                    pass_power_k = metrics.get(f"pass^{k}", 0) * 100
                    pass_k_str = f"{pass_k:.1f}%"
                    pass_power_k_str = f"{pass_power_k:.1f}%"

                avg_time = metrics.get("avg_agent_execution_time", 0)

                content.append(
                    f"| {model} | {tasks} | {pass_1_str} | {pass_k_str} | {pass_power_k_str} | {avg_time:.2f} |"
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

                # Check if this is a single-run model
                is_single_run_model = any(m in model for m in single_run_models)

                if is_single_run_model:
                    pass_k_str = "/"
                    pass_power_k_str = "/"
                else:
                    pass_k = metrics.get(f"pass@{k}", 0) * 100
                    pass_power_k = metrics.get(f"pass^{k}", 0) * 100
                    pass_k_str = f"{pass_k:.1f}%"
                    pass_power_k_str = f"{pass_power_k:.1f}%"

                avg_time = metrics.get("avg_agent_execution_time", 0)

                content.append(
                    f"| {model} | {tasks} | {pass_1_str} | {pass_k_str} | {pass_power_k_str} | {avg_time:.2f} |"
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
    exp_name: str,
    summary_file_path: Path,
    readme_content: str,
    model_results_path: str,
    task_results_path: str = None,
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

            # Copy model_results
            if Path(model_results_path).exists():
                dest_model_results = temp_dir / "model_results"
                if dest_model_results.exists():
                    shutil.rmtree(dest_model_results)
                shutil.copytree(model_results_path, dest_model_results)
                print("  📁 model_results/")

            # Copy task_results if provided
            if task_results_path and Path(task_results_path).exists():
                dest_task_results = temp_dir / "task_results"
                if dest_task_results.exists():
                    shutil.rmtree(dest_task_results)
                shutil.copytree(task_results_path, dest_task_results)
                print("  📁 task_results/")

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
    parser.add_argument(
        "--single-run-models",
        type=str,
        help="Comma-separated list of models that only have single runs (e.g., claude-4-1-opus)",
    )

    args = parser.parse_args()

    # Parse single-run models
    single_run_models = []
    if args.single_run_models:
        single_run_models = [m.strip() for m in args.single_run_models.split(",")]
        print(f"📌 Single-run models: {', '.join(single_run_models)}")

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
        service_model_metrics = calculate_k_run_metrics(
            all_runs_results, k, single_run_models
        )

    else:
        print("📊 Detected single-run experiment")
        service_model_metrics = aggregate_single_run_results(exp_dir, args.force)

    if not service_model_metrics:
        print("❌ No valid results found to aggregate")
        return 1

    # Generate simplified summary
    print("📋 Generating simplified summary...")
    summary = create_simplified_summary(
        args.exp_name, service_model_metrics, k, single_run_models
    )

    # Save summary.json
    if k > 1:
        summary_path = exp_dir / "summary.json"
    else:
        summary_path = exp_dir / "summary.json"

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"✅ Summary saved to: {summary_path}")

    # Generate model_results
    print("📁 Generating model_results...")
    model_results_path = generate_model_results(
        exp_dir, k, args.force, single_run_models
    )
    print(f"✅ Model results created at: {model_results_path}")

    # Generate task_results
    print("📁 Generating task_results...")
    task_results_path = generate_task_results(exp_dir, k, args.force, single_run_models)
    print(f"✅ Task results created at: {task_results_path}")

    # Push to repository if requested
    if args.push:
        print("\n🚀 Pushing to experiments repository...")

        readme_content = generate_readme_content(
            args.exp_name, summary, single_run_models
        )

        # Also save README locally
        local_readme_path = exp_dir / "README.md"
        with open(local_readme_path, "w", encoding="utf-8") as f:
            f.write(readme_content)
        print(f"✅ README saved locally to: {local_readme_path}")

        success = push_to_experiments_repo(
            args.exp_name,
            summary_path,
            readme_content,
            model_results_path,
            task_results_path,
        )

        if not success:
            print("❌ Failed to push to experiments repository")
            return 1

        print(
            "🎉 Successfully pushed: summary.json, README.md, model_results/, task_results/"
        )

    print(f"\n🎉 Processing complete for {args.exp_name}")
    return 0


if __name__ == "__main__":
    exit(main())
