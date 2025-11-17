#!/usr/bin/env python3
"""
Simple Results Aggregator - Aggregate specific result directories
Usage: python -m src.aggregators.aggregate_specific_results --result-dir results/exp/model__service --k 4
"""

import json
import argparse
from pathlib import Path
from collections import defaultdict
from typing import Dict, Any, Tuple, List
from datetime import datetime
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from src.aggregators.pricing import compute_cost_usd


def collect_results_from_dir(result_dir: Path, k: int) -> Dict[str, Any]:
    """Collect all results from a specific result directory."""
    results = {}

    for run_idx in range(1, k + 1):
        run_dir = result_dir / f"run-{run_idx}"
        if not run_dir.exists():
            print(f"⚠️  Warning: {run_dir} does not exist, skipping")
            continue

        run_results = {}
        for task_dir in run_dir.iterdir():
            if not task_dir.is_dir():
                continue

            meta_path = task_dir / "meta.json"
            if meta_path.exists():
                with open(meta_path) as f:
                    meta = json.load(f)
                    run_results[task_dir.name] = meta

        results[f"run-{run_idx}"] = run_results

    return results


def get_token_counts(meta: Dict[str, Any]) -> Tuple[int, int, int]:
    """Extract token counts from meta."""
    tu = meta.get("token_usage", {}) or {}
    input_tokens = int(tu.get("input_tokens", 0) or 0)
    output_tokens = int(tu.get("output_tokens", 0) or 0)
    total_tokens = int(tu.get("total_tokens", input_tokens + output_tokens) or (input_tokens + output_tokens))
    return input_tokens, output_tokens, total_tokens


def calculate_metrics(results: Dict, k: int, model_name: str) -> Dict:
    """Calculate metrics from results."""

    # Get all unique task names
    all_tasks = set()
    for run_name, run_data in results.items():
        all_tasks.update(run_data.keys())
    all_tasks = sorted(all_tasks)

    total_tasks = len(all_tasks)
    actual_runs = len(results)

    print(f"\n📊 Analysis:")
    print(f"  Total unique tasks: {total_tasks}")
    print(f"  Runs found: {actual_runs} (expected: {k})")

    # Aggregates
    total_agent_execution_time = 0.0
    total_input_tokens = 0
    total_output_tokens = 0
    total_tokens = 0
    total_turns = 0

    actual_model_name = None

    # Per-run pass@1
    pass1_rates_per_run = []

    # For pass@k
    pass_k_task_success_any = 0
    pass_power_k_task_success_all = 0

    for run_idx in range(1, actual_runs + 1):
        run_name = f"run-{run_idx}"
        successes_this_run = 0

        for task in all_tasks:
            meta = results.get(run_name, {}).get(task)

            if not meta:
                continue

            success = bool(meta.get("execution_result", {}).get("success", False))
            if success:
                successes_this_run += 1

            total_agent_execution_time += float(meta.get("agent_execution_time", 0.0) or 0.0)
            in_tok, out_tok, ttl_tok = get_token_counts(meta)
            total_input_tokens += in_tok
            total_output_tokens += out_tok
            total_tokens += ttl_tok
            total_turns += int(meta.get("turn_count", 0) or 0)

            if actual_model_name is None:
                actual_model_name = meta.get("actual_model_name") or None

        pass1_rate = successes_this_run / total_tasks if total_tasks > 0 else 0
        pass1_rates_per_run.append(pass1_rate)
        print(f"  Run {run_idx}: {successes_this_run}/{total_tasks} = {pass1_rate*100:.1f}%")

    # Calculate pass@k
    for task in all_tasks:
        successes = []
        for run_idx in range(1, actual_runs + 1):
            run_name = f"run-{run_idx}"
            meta = results.get(run_name, {}).get(task)
            success = bool(meta.get("execution_result", {}).get("success", False)) if meta else False
            successes.append(success)

        if any(successes):
            pass_k_task_success_any += 1
        if all(successes):
            pass_power_k_task_success_all += 1

    # Averages
    denom = total_tasks * actual_runs if total_tasks > 0 else 1
    avg_agent_execution_time = total_agent_execution_time / denom
    avg_input_tokens = total_input_tokens / denom
    avg_output_tokens = total_output_tokens / denom
    avg_total_tokens = total_tokens / denom
    avg_turns = total_turns / denom

    # Pass@1 stats
    if pass1_rates_per_run:
        avg_pass1 = sum(pass1_rates_per_run) / len(pass1_rates_per_run)
        mean = avg_pass1
        variance = sum((r - mean) ** 2 for r in pass1_rates_per_run) / len(pass1_rates_per_run)
        std_pass1 = variance ** 0.5
    else:
        avg_pass1 = 0.0
        std_pass1 = 0.0

    # Cost calculation
    per_run_input_tokens = total_input_tokens / actual_runs if actual_runs else 0
    per_run_output_tokens = total_output_tokens / actual_runs if actual_runs else 0
    model_for_pricing = actual_model_name or model_name
    per_run_cost = compute_cost_usd(model_for_pricing, per_run_input_tokens, per_run_output_tokens)

    summary = {
        "generated_at": datetime.now().isoformat(),
        "model": model_name,
        "actual_model_name": actual_model_name or model_name,
        "runs": actual_runs,
        "total_tasks": total_tasks,
        "total_agent_execution_time": round(total_agent_execution_time, 2),
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "total_tokens": total_tokens,
        "total_turns": total_turns,
        "avg_agent_execution_time": round(avg_agent_execution_time, 4),
        "avg_input_tokens": round(avg_input_tokens, 2),
        "avg_output_tokens": round(avg_output_tokens, 2),
        "avg_total_tokens": round(avg_total_tokens, 2),
        "avg_turns": round(avg_turns, 2),
        "per_run_input_tokens": round(per_run_input_tokens, 2),
        "per_run_output_tokens": round(per_run_output_tokens, 2),
        "per_run_cost": round(per_run_cost, 4) if per_run_cost else None,
        "pass@1": {
            "avg": round(avg_pass1, 4),
            "std": round(std_pass1, 4),
            "per_run": [round(r, 4) for r in pass1_rates_per_run]
        },
    }

    if actual_runs > 1:
        summary[f"pass@{actual_runs}"] = round(pass_k_task_success_any / total_tasks, 4)
        summary[f"pass^{actual_runs}"] = round(pass_power_k_task_success_all / total_tasks, 4)

    return summary


def main():
    parser = argparse.ArgumentParser(description="Simple results aggregator for specific directories")
    parser.add_argument("--result-dir", required=True, help="Path to result directory (e.g., results/exp/model__service)")
    parser.add_argument("--k", type=int, default=4, help="Number of runs (default: 4)")
    parser.add_argument("--output", help="Output JSON file path (default: <result-dir>/summary.json)")

    args = parser.parse_args()

    result_dir = Path(args.result_dir)
    if not result_dir.exists():
        print(f"❌ Result directory {result_dir} does not exist")
        return 1

    # Extract model name from directory name
    model_name = result_dir.name.replace("__", "-")

    print(f"🔄 Processing: {result_dir}")
    print(f"📋 Model: {model_name}")

    # Collect results
    results = collect_results_from_dir(result_dir, args.k)

    if not results:
        print("❌ No results found")
        return 1

    # Calculate metrics
    summary = calculate_metrics(results, args.k, model_name)

    # Save summary
    output_path = Path(args.output) if args.output else result_dir / "summary.json"
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n✅ Summary saved to: {output_path}")
    print(f"\n📈 Results:")
    print(f"  Pass@1: {summary['pass@1']['avg']*100:.1f}% ± {summary['pass@1']['std']*100:.1f}%")
    if f"pass@{args.k}" in summary:
        print(f"  Pass@{args.k}: {summary[f'pass@{args.k}']*100:.1f}%")
        print(f"  Pass^{args.k}: {summary[f'pass^{args.k}']*100:.1f}%")
    print(f"  Per-run cost: ${summary['per_run_cost']:.4f}" if summary['per_run_cost'] else "  Per-run cost: N/A")
    print(f"  Avg agent time: {summary['avg_agent_execution_time']:.2f}s")
    print(f"  Avg turns: {summary['avg_turns']:.2f}")
    print(f"\n📊 Token Usage:")
    avg_tokens_per_run = summary['total_tokens'] / summary['runs'] if summary['runs'] > 0 else 0
    print(f"  Avg tokens per run: {avg_tokens_per_run:,.0f}")
    print(f"  Avg tokens per turn: {summary['avg_total_tokens'] / summary['avg_turns']:.0f}" if summary['avg_turns'] > 0 else "  Avg tokens per turn: N/A")
    print(f"  Total tokens (all runs): {summary['total_tokens']:,}")
    print(f"  Total turns (all runs): {summary['total_turns']:,}")

    return 0


if __name__ == "__main__":
    exit(main())
