import argparse
import os
import json
from typing import Dict, List, Set, Tuple

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from matplotlib.patches import Patch
from pathlib import Path

import src.evaluator

# ---------------------------------------------------------------------------
# Console styling helpers
# ---------------------------------------------------------------------------

# Simple ANSI color helper (no extra dependency required)


class ANSI:
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    RESET = "\033[0m"


def warn(msg: str):
    """Print warning message in yellow with [WARN] prefix."""
    print(f"{ANSI.CYAN}⚠️  [WARN]{ANSI.RESET} {msg}")


def info(msg: str):
    """Print info message with [INFO] prefix."""
    print(f"[INFO] {msg}")


# ---------------------------------------------------------------------------
# Task discovery helpers
# ---------------------------------------------------------------------------


def discover_all_tasks(service: str, tasks_root: Path = Path("tasks")) -> Set[str]:
    """Return set of expected task identifiers for the given service.

    Each task identifier is in the form "<category>/task_<id>".
    """
    service_root = tasks_root / service
    expected: Set[str] = set()

    if not service_root.exists():
        return expected

    for category_dir in service_root.iterdir():
        if not category_dir.is_dir() or category_dir.name.startswith("."):
            continue

        category_dash = category_dir.name.replace("_", "-")

        for task_dir in category_dir.iterdir():
            if task_dir.is_dir() and task_dir.name.startswith("task_"):
                task_dash = task_dir.name.replace("_", "-")  # task_1 -> task-1
                expected.add(f"{category_dash}_{task_dash}")

    return expected


# ---------------------------------------------------------------------------
# Model validation and metric gathering
# ---------------------------------------------------------------------------


def validate_and_gather_metrics(
    model_path: str,
    expected_tasks: Set[str],
) -> Tuple[bool, Dict[str, float] | None, str | None]:
    """Validate that all tasks are present and without retry errors, then gather metrics.

    Returns (is_valid, metrics_dict_or_none, model_name_for_command).
    """
    task_dirs: List[str] = [
        d for d in os.listdir(model_path) if os.path.isdir(os.path.join(model_path, d))
    ]

    found_tasks: Set[str] = set()
    success_count = 0
    turn_counts: List[int] = []
    token_counts: List[int] = []

    has_retry_error = False

    for task in task_dirs:
        task_identifier = task  # e.g. habit-tracker_task-1
        meta_path = os.path.join(model_path, task, "meta.json")
        if not os.path.isfile(meta_path):
            continue

        found_tasks.add(task_identifier)

        with open(meta_path, "r") as f:
            meta = json.load(f)

        # Check pipeline errors
        error_msg = meta.get("execution_result", {}).get("error_message")
        if error_msg and any(
            err in error_msg for err in src.evaluator.PIPELINE_RETRY_ERRORS
        ):
            has_retry_error = True

        # Collect metrics
        if meta.get("execution_result", {}).get("success"):
            success_count += 1

        turn = meta.get("turn_count")
        if turn is not None:
            turn_counts.append(turn)

        total_tokens = meta.get("token_usage", {}).get("total_tokens")
        if total_tokens is not None:
            token_counts.append(total_tokens)

    # Validate completion
    is_complete = expected_tasks.issubset(found_tasks)
    is_valid = is_complete and not has_retry_error

    if not is_valid:
        return False, None, None

    total_tasks = len(expected_tasks)
    success_rate = success_count / total_tasks if total_tasks else 0
    avg_turns = sum(turn_counts) / len(turn_counts) if turn_counts else 0
    avg_tokens = sum(token_counts) / len(token_counts) if token_counts else 0

    metrics = {
        "success_rate": success_rate,
        "avg_turns": avg_turns,
        "avg_tokens": avg_tokens,
        "task_count": total_tasks,
    }

    return True, metrics, None


def plot_metrics(
    metrics: Dict[str, Dict[str, float]], exp_name: str, service: str, show: bool
):
    """Create a bar chart visualizing success rate and avg tokens; annotate avg turns."""

    # Sort by success-rate (desc)
    sorted_items = sorted(
        metrics.items(), key=lambda x: x[1]["success_rate"], reverse=True
    )
    models = [m for m, _ in sorted_items]
    success_rates = [item[1]["success_rate"] for item in sorted_items]
    avg_tokens = [item[1]["avg_tokens"] for item in sorted_items]
    avg_turns = [item[1]["avg_turns"] for item in sorted_items]

    # Styling
    sns.set_theme(style="whitegrid")
    # Adopt matplotlib tab10 palette for clear contrasting colors
    palette = sns.color_palette("tab10")
    success_color, token_color = palette[2], palette[0]

    x = np.arange(len(models))
    # Make bars thinner for better aesthetics
    width = min(0.25, 0.5 / max(1, len(models)))

    # Increase figure width with number of models
    fig_width = max(8, len(models) * 2.5)
    fig, ax1 = plt.subplots(figsize=(fig_width, 6))

    # Success rate (left y-axis)
    bars_success = ax1.bar(
        x - width / 2, success_rates, width, color=success_color, label="Success Rate"
    )
    ax1.set_ylabel("Success Rate")
    ax1.set_ylim(0, 1)

    # Avg token usage (right y-axis)
    ax2 = ax1.twinx()
    bars_tokens = ax2.bar(
        x + width / 2, avg_tokens, width, color=token_color, label="Avg Tokens"
    )
    ax2.set_ylabel("Average Tokens")

    # Annotate avg turns on token bars
    for idx, bar in enumerate(bars_tokens):
        ax2.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{avg_turns[idx]:.1f}",
            ha="center",
            va="bottom",
            fontsize=11,
            fontweight="bold",
            color="black",
        )

    # X-axis labels, title and subtitle
    ax1.set_xticks(x)
    ax1.set_xticklabels(models, rotation=45, ha="right")
    ax1.set_xlabel("Model")
    plt.suptitle(f"{exp_name} – {service} Summary", fontsize=16, fontweight="bold")
    plt.title(
        "Numbers above token bars indicate average turns",
        fontsize=10,
        style="italic",
        pad=20,
    )

    # Legend (positioned to avoid overlap with subtitle)
    handles = [
        Patch(color=success_color, label="Success Rate"),
        Patch(color=token_color, label="Avg Tokens"),
    ]
    ax1.legend(
        handles=handles,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.25),
        ncol=2,
        frameon=False,
    )

    # Add some padding around the plot
    plt.subplots_adjust(top=0.82, bottom=0.15)
    fig.tight_layout()

    # Always save figure
    save_dir = os.path.join("results", exp_name)
    os.makedirs(save_dir, exist_ok=True)
    output_name = os.path.join(save_dir, f"summary_{service}.png")
    plt.savefig(output_name, dpi=300, bbox_inches="tight")
    info(f"Figure saved to {output_name}")

    if show:
        plt.show()


def main():
    parser = argparse.ArgumentParser(
        description="Parse experiment results and visualize metrics."
    )
    parser.add_argument(
        "--exp-name",
        required=True,
        help="Name of the experiment folder inside ./results, e.g. MCP-RUN-FINAL",
    )
    parser.add_argument(
        "--mcp",
        required=True,
        help="Service prefix to filter model folders, e.g. notion",
    )
    parser.add_argument(
        "--results-dir",
        default="results",
        help="Root results directory (default: ./results)",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Display the plot interactively in addition to saving it",
    )

    args = parser.parse_args()

    exp_path = os.path.join(args.results_dir, args.exp_name)
    if not os.path.isdir(exp_path):
        raise FileNotFoundError(f"Experiment directory not found: {exp_path}")

    # Identify model directories starting with the given service prefix
    model_dirs = [
        d
        for d in os.listdir(exp_path)
        if os.path.isdir(os.path.join(exp_path, d)) and d.startswith(args.mcp)
    ]

    # Discover expected tasks for this service
    expected_tasks = discover_all_tasks(args.mcp)
    if not expected_tasks:
        print(
            f"[ERROR] Could not discover any tasks for service '{args.mcp}'. Exiting."
        )
        return

    metrics: Dict[str, Dict[str, float]] = {}

    for model_dir in model_dirs:
        model_name = (
            model_dir.split("_", 1)[1]
            if "_" in model_dir
            else model_dir[len(args.mcp) :]
        )
        model_path = os.path.join(exp_path, model_dir)

        is_valid, model_metrics, _ = validate_and_gather_metrics(
            model_path, expected_tasks
        )

        if is_valid and model_metrics is not None:
            metrics[model_name] = model_metrics
            info(f"{model_name}: {model_metrics}")
        else:
            cmd = (
                f"python pipeline.py --mcp {args.mcp} --tasks all "
                f"--models {model_name} --exp-name {args.exp_name}"
            )
            retry_errs = ", ".join(src.evaluator.PIPELINE_RETRY_ERRORS)
            warn(
                (
                    f"Model '{model_name}' results are incomplete or contain pipeline errors ({retry_errs}).\n"
                    f"Resume evaluation with:\n    {cmd}\n"
                )
            )

    if not metrics:
        print("[ERROR] No metrics collected; aborting plot.")
        return

    plot_metrics(metrics, args.exp_name, args.mcp, show=args.show)


if __name__ == "__main__":
    main()
