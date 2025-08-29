#!/usr/bin/env python3
"""
MCPMark Unified Evaluation Pipeline
===================================

This script provides an automated evaluation pipeline for testing Large Language Models (LLMs)
on various Multi-Step Cognitive Processes (MCP) services like Notion, GitHub, and PostgreSQL.
"""

import argparse
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

from src.logger import get_logger
from src.evaluator import MCPEvaluator
from src.factory import MCPServiceFactory
from src.model_config import ModelConfig


# Initialize logger
logger = get_logger(__name__)


def main():
    """Main entry point for the evaluation pipeline."""
    parser = argparse.ArgumentParser(description="MCPMark Unified Evaluation Pipeline.")

    supported_mcp_services = MCPServiceFactory.get_supported_mcp_services()
    supported_models = ModelConfig.get_supported_models()

    # Main configuration
    parser.add_argument(
        "--mcp",
        default="filesystem",
        choices=supported_mcp_services,
        help="MCP service to use (default: filesystem)",
    )
    parser.add_argument(
        "--models",
        required=True,
        help="Comma-separated list of models to evaluate (e.g., 'o3,k2,gpt-4.1')",
    )
    parser.add_argument(
        "--tasks",
        default="all",
        help='Tasks to run: (1). "all"; (2). "category"; or (3). "category/task".',
    )
    parser.add_argument(
        "--exp-name",
        default=None,
        help="Experiment name; results are saved under results/<exp-name>/ (default: YYYY-MM-DD-HH-MM-SS)",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=4,
        help="Number of evaluation runs (default: 1)",
    )

    # Execution configuration
    parser.add_argument(
        "--timeout", type=int, default=3600, help="Timeout in seconds for agent execution"
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        default=False,
        help="Use streaming execution (default: False, uses non-streaming)",
    )

    # Output configuration
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./results"),
        help="Directory to save results",
    )

    # Load arguments and environment variables
    args = parser.parse_args()
    load_dotenv(dotenv_path=".mcp_env", override=False)

    # Validate k parameter and exp-name requirement
    if args.k > 1 and args.exp_name is None:
        parser.error("--exp-name is required when k > 1")

    # Generate default exp-name if not provided
    if args.exp_name is None:
        args.exp_name = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

    # Parse models (no validation - allow unsupported models)
    model_list = [m.strip() for m in args.models.split(",") if m.strip()]
    if not model_list:
        parser.error("No valid models provided")

    # Log warning for unsupported models but don't error
    unsupported_models = [m for m in model_list if m not in supported_models]
    if unsupported_models:
        logger.warning(
            f"Using unsupported models: {', '.join(unsupported_models)}. Will use OPENAI_BASE_URL and OPENAI_API_KEY from environment."
        )

    logger.info("MCPMark Evaluation")
    logger.info(f"Experiment: {args.exp_name} | {len(model_list)} Model(s): {', '.join(model_list)}")
    if args.k > 1:
        logger.info(f"Running {args.k} evaluation runs for pass@k metrics")

    # Run k evaluation runs
    for run_idx in range(1, args.k + 1):
        if args.k > 1:
            logger.info(f"\n{'=' * 80}")
            logger.info(f"Starting Run {run_idx}/{args.k}")
            logger.info(f"{'=' * 80}\n")
            
            # For k-runs, create run-N subdirectory
            run_exp_name = f"run-{run_idx}"
            run_output_dir = args.output_dir / args.exp_name
        else:
            # For single run (k=1), maintain backward compatibility
            # Use run-1 subdirectory for consistency
            run_exp_name = "run-1"
            run_output_dir = args.output_dir / args.exp_name

        # Run evaluation for each model
        for i, model in enumerate(model_list, 1):
            logger.info(f"\n{'=' * 60}")
            if args.k > 1:
                logger.info(f"Run {run_idx}/{args.k} | Model {i}/{len(model_list)}: {model}")
            else:
                logger.info(f"Starting evaluation {i}/{len(model_list)}: {model}")
            logger.info(f"{'=' * 60}\n")

            # Initialize and run the evaluation pipeline for this model
            pipeline = MCPEvaluator(
                mcp_service=args.mcp,
                model=model,
                timeout=args.timeout,
                exp_name=run_exp_name,
                output_dir=run_output_dir,
                stream=args.stream,
            )

            pipeline.run_evaluation(args.tasks)
            logger.info(
                f"📁 Results: {pipeline.base_experiment_dir}"
            )

    logger.info(f"\n{'=' * 60}")
    if args.k > 1:
        logger.info(f"✓ All {args.k} runs completed for {len(model_list)} model(s)")
        logger.info(f"Run `python -m src.aggregators.aggregate_results --exp-name {args.exp_name}` to compute all metrics")
    else:
        logger.info(f"✓ All evaluations completed for {len(model_list)} model(s)")
    logger.info(f"{'=' * 60}")


if __name__ == "__main__":
    main()
