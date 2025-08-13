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
        default="notion",
        choices=supported_mcp_services,
        help="MCP service to use (default: notion)",
    )
    parser.add_argument(
        "--models",
        required=True,
        help="Comma-separated list of models to evaluate (e.g., 'o3,k2,gpt-4.1')",
    )
    parser.add_argument(
        "--tasks",
        default="all",
        help='Tasks to run: "all", a category name, or "category/task_name"',
    )
    parser.add_argument(
        "--exp-name",
        default=None,
        help="Experiment name; results are saved under results/<exp-name>/ (default: YYYY-MM-DD-HH-MM-SS)",
    )

    # Execution configuration
    parser.add_argument(
        "--timeout", type=int, default=300, help="Timeout in seconds for each task"
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

    # Generate default exp-name if not provided
    if args.exp_name is None:
        args.exp_name = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        logger.info(f"Using default experiment name: {args.exp_name}")

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

    logger.info(
        f"Running evaluation for {len(model_list)} model(s): {', '.join(model_list)}"
    )

    # Run evaluation for each model
    for i, model in enumerate(model_list, 1):
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Starting evaluation {i}/{len(model_list)}: {model}")
        logger.info(f"{'=' * 60}\n")

        # Initialize and run the evaluation pipeline for this model
        pipeline = MCPEvaluator(
            mcp_service=args.mcp,
            model=model,
            timeout=args.timeout,
            exp_name=args.exp_name,
            output_dir=args.output_dir,
        )

        pipeline.run_evaluation(args.tasks)
        logger.info(
            f"✓ Evaluation completed for {model}. Results saved in: {pipeline.base_experiment_dir}"
        )

    logger.info(f"\n{'=' * 60}")
    logger.info(f"✓ All evaluations completed for {len(model_list)} model(s)")
    logger.info(f"{'=' * 60}")


if __name__ == "__main__":
    main()
