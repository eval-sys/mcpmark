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
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from src.errors import is_retryable_error
from src.aggregators.pricing import compute_cost_usd


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
                        # Use unified naming for both playwright and webarena variants
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
        # Normalize service name: treat playwright_webarena as playwright
        if service == "playwright_webarena":
            service = "playwright"
        
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
    """Calculate rich metrics (totals, averages, per-run aggregates, pass@k) for complete models."""
    summary = {
        "generated_at": datetime.now().isoformat(),
        "k": k,
        "overall": {},
    }

    # Initialize per-service sections mirroring overall structure
    for service in all_tasks.keys():
        summary[service] = {}

    # Helper to safely extract token usage numbers
    def get_token_counts(meta: Dict[str, Any]) -> Tuple[int, int, int]:
        tu = meta.get("token_usage", {}) or {}
        input_tokens = int(tu.get("input_tokens", 0) or 0)
        output_tokens = int(tu.get("output_tokens", 0) or 0)
        total_tokens = int(tu.get("total_tokens", input_tokens + output_tokens) or (input_tokens + output_tokens))
        return input_tokens, output_tokens, total_tokens

    for model, model_results in complete_models.items():
        is_single_run = any(srm in model for srm in single_run_models)
        runs_count = 1 if is_single_run else k

        total_tasks = sum(len(tasks) for tasks in all_tasks.values())

        # Aggregates across all services and runs
        total_agent_execution_time = 0.0
        total_input_tokens = 0
        total_output_tokens = 0
        total_tokens = 0
        total_turns = 0
        # For optional fields
        actual_model_name: Optional[str] = None
        # If cost info is not present in metas, leave as None
        per_run_cost: Optional[float] = None

        # For pass@1 per-run statistics across all services
        pass1_rates_per_run_overall: List[float] = []

        # For pass@k and pass^k across all services
        pass_k_task_success_any = 0
        pass_power_k_task_success_all = 0

        # Precompute successes per task across runs for overall
        # Also accumulate totals for tokens/time/turns
        for run_idx in range(1, runs_count + 1):
            run_name = f"run-{run_idx}"
            successes_this_run = 0

            for service, service_tasks in all_tasks.items():
                # service-level aggregates for this model (will compute fully below)
                for task in service_tasks:
                    meta = (
                        model_results
                        .get(service, {})
                        .get(run_name, {})
                        .get(task)
                    )

                    # In complete_models, meta should exist; still guard
                    if not meta:
                        continue

                    success = bool(meta.get("execution_result", {}).get("success", False))
                    if success:
                        successes_this_run += 1

                    # totals accumulation
                    total_agent_execution_time += float(meta.get("agent_execution_time", 0.0) or 0.0)
                    in_tok, out_tok, ttl_tok = get_token_counts(meta)
                    total_input_tokens += in_tok
                    total_output_tokens += out_tok
                    total_tokens += ttl_tok
                    total_turns += int(meta.get("turn_count", 0) or 0)

                    # capture actual model name if present
                    if actual_model_name is None:
                        actual_model_name = meta.get("actual_model_name") or None

                    # capture cost if present in any meta as per-run cost token (rare)
                    if per_run_cost is None:
                        # A few possible fields people use; if none present, stays None
                        possible_cost = meta.get("per_run_cost") or meta.get("run_cost") or meta.get("cost")
                        if isinstance(possible_cost, (int, float)):
                            per_run_cost = float(possible_cost)

            pass1_rates_per_run_overall.append(round(successes_this_run / total_tasks, 6))

        # Compute pass@k and pass^k across tasks (overall)
        if not is_single_run:
            for service, service_tasks in all_tasks.items():
                for task in service_tasks:
                    successes = []
                    for run_idx in range(1, runs_count + 1):
                        run_name = f"run-{run_idx}"
                        meta = (
                            model_results
                            .get(service, {})
                            .get(run_name, {})
                            .get(task)
                        )
                        success = bool(meta.get("execution_result", {}).get("success", False)) if meta else False
                        successes.append(success)
                    if any(successes):
                        pass_k_task_success_any += 1
                    if all(successes):
                        pass_power_k_task_success_all += 1

        # Build overall metrics entry
        denom = total_tasks * runs_count if total_tasks > 0 else 1
        avg_agent_execution_time = total_agent_execution_time / denom
        avg_input_tokens = total_input_tokens / denom
        avg_output_tokens = total_output_tokens / denom
        avg_total_tokens = total_tokens / denom
        avg_turns = total_turns / denom

        # pass@1 stats across runs
        if pass1_rates_per_run_overall:
            avg_pass1 = sum(pass1_rates_per_run_overall) / len(pass1_rates_per_run_overall)
            mean = avg_pass1
            variance = (
                sum((r - mean) ** 2 for r in pass1_rates_per_run_overall) / len(pass1_rates_per_run_overall)
            )
            std_pass1 = variance ** 0.5
        else:
            avg_pass1 = 0.0
            std_pass1 = 0.0

        # Compute per-run tokens and cost
        per_run_input_tokens = total_input_tokens / runs_count if runs_count else 0
        per_run_output_tokens = total_output_tokens / runs_count if runs_count else 0
        model_for_pricing = actual_model_name or model
        computed_per_run_cost = compute_cost_usd(model_for_pricing, per_run_input_tokens, per_run_output_tokens)

        overall_metrics = {
            "total_tasks": total_tasks,
            "total_agent_execution_time": total_agent_execution_time,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_tokens": total_tokens,
            "total_turns": total_turns,
            "avg_agent_execution_time": round(avg_agent_execution_time, 4),
            "avg_input_tokens": round(avg_input_tokens, 4),
            "avg_output_tokens": round(avg_output_tokens, 4),
            "avg_total_tokens": round(avg_total_tokens, 4),
            "avg_turns": round(avg_turns, 4),
            "per_run_input_tokens": per_run_input_tokens,
            "per_run_output_tokens": per_run_output_tokens,
            "per_run_cost": computed_per_run_cost if computed_per_run_cost is not None else (per_run_cost if per_run_cost is not None else None),
            "actual_model_name": actual_model_name or "",
            "pass@1": {
                "avg": round(avg_pass1, 4),
                "std": round(std_pass1, 4),
            },
        }
        if not is_single_run:
            overall_metrics[f"pass@{k}"] = round(pass_k_task_success_any / total_tasks, 4)
            overall_metrics[f"pass^{k}"] = round(pass_power_k_task_success_all / total_tasks, 4)

        summary["overall"][model] = overall_metrics

        # Per-service detailed metrics mirroring overall
        for service, service_tasks in all_tasks.items():
            service_total_tasks = len(service_tasks)
            if service_total_tasks == 0:
                continue

            s_total_agent_execution_time = 0.0
            s_total_input_tokens = 0
            s_total_output_tokens = 0
            s_total_tokens = 0
            s_total_turns = 0

            # per-run pass@1 for this service
            s_pass1_rates_per_run: List[float] = []

            # pass@k for this service
            s_pass_k_task_success_any = 0
            s_pass_power_k_task_success_all = 0

            for run_idx in range(1, runs_count + 1):
                run_name = f"run-{run_idx}"
                s_successes_this_run = 0

                for task in service_tasks:
                    meta = (
                        model_results
                        .get(service, {})
                        .get(run_name, {})
                        .get(task)
                    )
                    if not meta:
                        continue

                    success = bool(meta.get("execution_result", {}).get("success", False))
                    if success:
                        s_successes_this_run += 1

                    s_total_agent_execution_time += float(meta.get("agent_execution_time", 0.0) or 0.0)
                    in_tok, out_tok, ttl_tok = get_token_counts(meta)
                    s_total_input_tokens += in_tok
                    s_total_output_tokens += out_tok
                    s_total_tokens += ttl_tok
                    s_total_turns += int(meta.get("turn_count", 0) or 0)

                s_pass1_rates_per_run.append(round(s_successes_this_run / service_total_tasks, 6))

            if not is_single_run:
                for task in service_tasks:
                    successes = []
                    for run_idx in range(1, runs_count + 1):
                        run_name = f"run-{run_idx}"
                        meta = (
                            model_results
                            .get(service, {})
                            .get(run_name, {})
                            .get(task)
                        )
                        success = bool(meta.get("execution_result", {}).get("success", False)) if meta else False
                        successes.append(success)
                    if any(successes):
                        s_pass_k_task_success_any += 1
                    if all(successes):
                        s_pass_power_k_task_success_all += 1

            s_denom = service_total_tasks * runs_count if service_total_tasks > 0 else 1
            s_avg_agent_execution_time = s_total_agent_execution_time / s_denom
            s_avg_input_tokens = s_total_input_tokens / s_denom
            s_avg_output_tokens = s_total_output_tokens / s_denom
            s_avg_total_tokens = s_total_tokens / s_denom
            s_avg_turns = s_total_turns / s_denom

            if s_pass1_rates_per_run:
                s_mean = sum(s_pass1_rates_per_run) / len(s_pass1_rates_per_run)
                s_var = sum((r - s_mean) ** 2 for r in s_pass1_rates_per_run) / len(s_pass1_rates_per_run)
                s_std = s_var ** 0.5
            else:
                s_mean = 0.0
                s_std = 0.0

            # Compute per-run tokens and cost for this service
            s_per_run_input_tokens = s_total_input_tokens / runs_count if runs_count else 0
            s_per_run_output_tokens = s_total_output_tokens / runs_count if runs_count else 0
            s_computed_per_run_cost = compute_cost_usd(model_for_pricing, s_per_run_input_tokens, s_per_run_output_tokens)

            service_metrics = {
                "total_tasks": service_total_tasks,
                "total_agent_execution_time": s_total_agent_execution_time,
                "total_input_tokens": s_total_input_tokens,
                "total_output_tokens": s_total_output_tokens,
                "total_tokens": s_total_tokens,
                "total_turns": s_total_turns,
                "avg_agent_execution_time": round(s_avg_agent_execution_time, 4),
                "avg_input_tokens": round(s_avg_input_tokens, 4),
                "avg_output_tokens": round(s_avg_output_tokens, 4),
                "avg_total_tokens": round(s_avg_total_tokens, 4),
                "avg_turns": round(s_avg_turns, 4),
                "per_run_input_tokens": s_per_run_input_tokens,
                "per_run_output_tokens": s_per_run_output_tokens,
                "per_run_cost": s_computed_per_run_cost if s_computed_per_run_cost is not None else (per_run_cost if per_run_cost is not None else None),
                "actual_model_name": actual_model_name or "",
                "pass@1": {
                    "avg": round(s_mean, 4),
                    "std": round(s_std, 4),
                },
            }

            if not is_single_run:
                service_metrics[f"pass@{k}"] = round(s_pass_k_task_success_any / service_total_tasks, 4)
                service_metrics[f"pass^{k}"] = round(s_pass_power_k_task_success_all / service_total_tasks, 4)

            summary[service][model] = service_metrics

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
                        agent_time = float(meta.get("agent_execution_time", 0.0) or 0.0)
                        token_usage = meta.get("token_usage", {}) or {}
                        turn_count = int(meta.get("turn_count", 0) or 0)
                        success = bool(meta.get("execution_result", {}).get("success", False))
                        model_task_data["runs"].append({
                            "run": run_name,
                            "success": success,
                            "execution_time": agent_time,
                            "agent_execution_time": agent_time,
                            "token_usage": token_usage,
                            "turn_count": turn_count,
                        })
                
                if model_task_data["runs"]:
                    # Compute per-model summary across runs for this task
                    runs_list = model_task_data["runs"]
                    runs_count = len(runs_list)
                    successful_runs = sum(1 for r in runs_list if r.get("success"))

                    # Averages
                    total_agent_time = sum(float(r.get("agent_execution_time", r.get("execution_time", 0.0)) or 0.0) for r in runs_list)
                    avg_agent_time = round(total_agent_time / runs_count, 2)

                    def _tok(r, key):
                        tu = r.get("token_usage") or {}
                        return int(tu.get(key, 0) or 0)

                    total_input_tokens = 0
                    total_output_tokens = 0
                    total_total_tokens = 0
                    for r in runs_list:
                        in_tok = _tok(r, "input_tokens")
                        out_tok = _tok(r, "output_tokens")
                        ttl_tok = int((r.get("token_usage") or {}).get("total_tokens", in_tok + out_tok) or (in_tok + out_tok))
                        total_input_tokens += in_tok
                        total_output_tokens += out_tok
                        total_total_tokens += ttl_tok

                    avg_input_tokens = round(total_input_tokens / runs_count, 1)
                    avg_output_tokens = round(total_output_tokens / runs_count, 1)
                    avg_total_tokens = round(total_total_tokens / runs_count, 1)

                    total_turns = sum(int(r.get("turn_count", 0) or 0) for r in runs_list)
                    avg_turn_count = round(total_turns / runs_count, 2)

                    summary_obj = {
                        "total_runs": runs_count,
                        "successful_runs": successful_runs,
                        "avg_agent_execution_time": avg_agent_time,
                        "avg_input_tokens": avg_input_tokens,
                        "avg_output_tokens": avg_output_tokens,
                        "avg_total_tokens": avg_total_tokens,
                        "avg_turn_count": avg_turn_count,
                    }

                    # Include pass@k and pass^k only for multi-run models
                    if runs_count > 1:
                        summary_obj[f"pass@{runs_count}"] = 1.0 if successful_runs > 0 else 0.0
                        summary_obj[f"pass^{runs_count}"] = 1.0 if successful_runs == runs_count else 0.0

                    model_task_data["summary"] = summary_obj
                    task_data["models"][model] = model_task_data
            
            # Save task file
            task_file = task_results_dir / f"{task}.json"
            with open(task_file, "w") as f:
                json.dump(task_data, f, indent=2)


def generate_readme(exp_name: str, summary: Dict, k: int) -> str:
    """Generate README.md content with six tables: overall + 5 MCP services.
    Each table includes Total Tasks, Pass@1 (avg ± std), Avg Agent Time (s), and Pass@k/Pass^k (if k > 1).
    """

    def get_pass1_avg_std(metrics: Dict[str, Any]) -> Tuple[float, float]:
        p1 = metrics.get("pass@1")
        if isinstance(p1, dict):
            return float(p1.get("avg", 0.0) or 0.0), float(p1.get("std", 0.0) or 0.0)
        # Back-compat if older summaries exist
        return float(p1 or 0.0), 0.0

    def render_section(title: str, section_data: Dict[str, Any]) -> List[str]:
        lines_sec: List[str] = [
            f"## {title}",
            "",
        ]

        header = "| Model | Total Tasks | Pass@1 (avg ± std) |"
        sep = "|-------|-------------|--------------------|"
        # include pass@k headers if present (k>1)
        include_k = k > 1
        if include_k:
            header += f" Pass@{k} | Pass^{k} |"
            sep += "----------|----------|"
        # Add Per-Run Cost (USD) and Avg Agent Time (s) at the end
        header += " Per-Run Cost (USD) |"
        sep += "---------------------|"
        header += " Avg Agent Time (s) |"
        sep += "--------------------|"

        lines_sec.append(header)
        lines_sec.append(sep)

        # Sort by Pass@1 avg
        sorted_items = sorted(
            section_data.items(),
            key=lambda x: get_pass1_avg_std(x[1])[0],
            reverse=True
        )

        for model, metrics in sorted_items:
            pass1_avg, pass1_std = get_pass1_avg_std(metrics)
            avg_time = float(metrics.get("avg_agent_execution_time", 0.0) or 0.0)
            # Format per-run cost (up to 2 decimal places, trim trailing zeros)
            cost_val = metrics.get("per_run_cost")
            if isinstance(cost_val, (int, float)):
                rounded_cost = round(float(cost_val), 2)
                formatted_cost = f"{rounded_cost:.2f}".rstrip('0').rstrip('.')
                cost_str = f"${formatted_cost}"
            else:
                cost_str = "/"
            row = (
                f"| {model} | {metrics.get('total_tasks', 0)} | "
                f"{pass1_avg * 100:.1f}% ± {pass1_std * 100:.1f}% |"
            )
            if include_k:
                if f"pass@{k}" in metrics and f"pass^{k}" in metrics:
                    row += f" {metrics[f'pass@{k}'] * 100:.1f}% | {metrics[f'pass^{k}'] * 100:.1f}% |"
                else:
                    # Single-run models do not have pass@k or pass^k; show placeholders
                    row += " / | / |"
            # Append cost and avg agent time at the end
            row += f" {cost_str} |"
            row += f" {avg_time:.1f} |"
            lines_sec.append(row)

        lines_sec.append("")
        return lines_sec

    lines: List[str] = [
        f"# {exp_name} - Evaluation Results",
        "",
        f"Generated: {summary['generated_at']}",
        "",
    ]

    # Overall table
    lines.extend(render_section("Overall Performance", summary.get("overall", {})))

    # Service tables: infer service keys from summary
    reserved = {"overall", "generated_at", "k", "experiment_name"}
    service_keys = [key for key in summary.keys() if key not in reserved]
    # Keep stable order
    for service in sorted(service_keys):
        title = f"{service.capitalize()} Performance"
        lines.extend(render_section(title, summary.get(service, {})))

    return "\n".join(lines)


def push_to_github(exp_dir: Path, exp_name: str, branch: Optional[str] = None):
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

            # If a branch is specified, create/checkout it before staging changes. Otherwise, ensure main.
            if branch:
                try:
                    subprocess.run(["git", "fetch", "origin"], check=True)
                except subprocess.CalledProcessError:
                    # Non-fatal if fetch fails in some environments
                    pass
                subprocess.run(["git", "checkout", "-B", branch], check=True)
                print(f"  🌿 Using branch '{branch}'")
            else:
                # Default to main branch
                try:
                    subprocess.run(["git", "fetch", "origin"], check=True)
                except subprocess.CalledProcessError:
                    pass
                # Prefer main; if it doesn't exist locally, create tracking from origin/main
                result = subprocess.run(["git", "rev-parse", "--verify", "main"], capture_output=True)
                if result.returncode != 0:
                    # Try to checkout origin/main
                    try:
                        subprocess.run(["git", "checkout", "-B", "main", "origin/main"], check=True)
                    except subprocess.CalledProcessError:
                        # Fallback: create main if no origin/main
                        subprocess.run(["git", "checkout", "-B", "main"], check=True)
                else:
                    subprocess.run(["git", "checkout", "main"], check=True)
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
            if branch:
                subprocess.run(["git", "push", "--set-upstream", "origin", branch], check=True)
            else:
                subprocess.run(["git", "push", "--set-upstream", "origin", "main"], check=True)
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
    # Extra parser for push-related options
    push_parent = argparse.ArgumentParser(add_help=False)
    push_parent.add_argument(
        "--branch",
        type=str,
        help="If provided with --push, push to this new branch"
    )

    parser = argparse.ArgumentParser(
        description="Simplified MCPMark results aggregator"
    , parents=[push_parent])
    parser.add_argument("--exp-name", required=True, help="Experiment name")
    parser.add_argument("--k", type=int, default=4, help="Number of runs (default: 4)")
    parser.add_argument(
        "--single-run-models",
        type=str,
        help="Comma-separated list of models that only need run-1"
    )
    parser.add_argument("--push", action="store_true", help="Push to GitHub (default to main)")
    
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
    summary["experiment_name"] = args.exp_name
    
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
        push_to_github(exp_dir, args.exp_name, branch=args.branch)
    
    print(f"\n🎉 Successfully processed {args.exp_name}")
    return 0


if __name__ == "__main__":
    exit(main())