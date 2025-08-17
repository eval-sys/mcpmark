import time
import json
import shutil

from datetime import datetime
from pathlib import Path
from typing import List, Optional

from src.logger import get_logger
from src.factory import MCPServiceFactory
from src.model_config import ModelConfig
from src.results_reporter import EvaluationReport, ResultsReporter, TaskResult
from src.agent import MCPAgent

PIPELINE_RETRY_ERRORS: List[str] = [
    "State Duplication Error",
    "MCP Network Error",
]

# Initialize logger
logger = get_logger(__name__)


class MCPEvaluator:
    def __init__(
        self,
        mcp_service: str,
        model: str,
        timeout: int = 300,
        exp_name: str = "test-run",
        output_dir: Path = None,
    ):
        # Main configuration
        self.mcp_service = mcp_service
        self.model = model
        self.timeout = timeout

        # Initialize model configuration
        model_config = ModelConfig(model)
        self.actual_model_name = model_config.actual_model_name
        self.base_url = model_config.base_url
        self.api_key = model_config.api_key

        # Initialize managers using the factory pattern (simplified)
        self.task_manager = MCPServiceFactory.create_task_manager(mcp_service)
        self.state_manager = MCPServiceFactory.create_state_manager(mcp_service)

        # Obtain static service configuration from state manager (e.g., notion_key)
        self.service_config = self.state_manager.get_service_config_for_agent()

        # Initialize agent for LLM and MCP server management. The agent will
        # automatically refresh its service configuration from the state
        # manager before each execution, so per-task manual updates are no
        # longer needed.
        self.agent = MCPAgent(
            model_name=self.actual_model_name,
            api_key=self.api_key,
            base_url=self.base_url,
            mcp_service=mcp_service,
            timeout=timeout,
            service_config=self.service_config,
            service_config_provider=self.state_manager.get_service_config_for_agent,
        )

        # Initialize results reporter
        self.results_reporter = ResultsReporter()

        # Output directory handling
        model_slug = self.model.replace(".", "-")
        self.base_experiment_dir = output_dir / exp_name / f"{mcp_service}_{model_slug}"
        self.base_experiment_dir.mkdir(parents=True, exist_ok=True)

    def _format_duration(self, seconds: float) -> str:
        """Format duration: <1s as ms, otherwise seconds."""
        return f"{(seconds * 1000):.2f}ms" if seconds < 1 else f"{seconds:.2f}s"

    def _get_task_output_dir(self, task) -> Path:
        """Return the directory path for storing this task's reports."""
        # Replace underscores with hyphens so the directory name is filesystem-friendly.
        category_slug = (
            task.category.replace("_", "-") if task.category else "uncategorized"
        )

        # Use the task identifier as-is (numeric or slug) – no "task-" prefix.
        task_slug = str(task.task_id)

        return self.base_experiment_dir / f"{category_slug}_{task_slug}"

    # ------------------------------------------------------------------
    # Resuming helpers
    # ------------------------------------------------------------------

    def _load_latest_task_result(self, task) -> Optional[TaskResult]:
        """Return the most recent TaskResult for *task* if it has been run before."""
        task_dir = self._get_task_output_dir(task)
        if not task_dir.exists():
            return None

        meta_path = task_dir / "meta.json"
        if not meta_path.exists():
            return None

        try:
            with meta_path.open("r", encoding="utf-8") as f:
                meta_data = json.load(f)

            # Reconstruct TaskResult from meta.json
            return TaskResult(
                task_name=meta_data["task_name"],
                success=meta_data["execution_result"]["success"],
                execution_time=meta_data["execution_time"],
                error_message=meta_data["execution_result"]["error_message"],
                category=task.category,
                task_id=task.task_id,
                # We don't need model_output for resume functionality
                model_output=None,
            )
        except Exception as exc:
            logger.warning("Failed to load existing result for %s: %s", task.name, exc)
        return None

    def _gather_all_task_results(self) -> List[TaskResult]:
        """Scan *all* task sub-directories and collect the latest TaskResult from each."""
        results: list[TaskResult] = []
        if not self.base_experiment_dir.exists():
            return results

        for task_dir in self.base_experiment_dir.iterdir():
            if not task_dir.is_dir():
                continue
            meta_path = task_dir / "meta.json"
            if not meta_path.exists():
                continue
            try:
                with meta_path.open("r", encoding="utf-8") as f:
                    meta_data = json.load(f)

                # Ignore legacy directories containing "_task-".
                # Only process the new format: <categorySlug>_<taskSlug>
                # ----------------------------------------------------------

                if "_task-" in task_dir.name:
                    # skip legacy directory
                    continue

                if "_" not in task_dir.name:
                    # malformed; skip
                    continue

                category_part, identifier_part = task_dir.name.split("_", 1)

                category = category_part.replace("-", "_")
                task_id = identifier_part  # keep slug as-is (string)

                result = TaskResult(
                    task_name=meta_data["task_name"],
                    success=meta_data["execution_result"]["success"],
                    execution_time=meta_data["execution_time"],
                    error_message=meta_data["execution_result"]["error_message"],
                    category=category,
                    task_id=task_id,
                    model_output=None,
                )
                results.append(result)
            except Exception as exc:
                logger.warning(
                    "Failed to parse existing report in %s: %s", task_dir, exc
                )
        return results

    def _run_single_task(self, task) -> TaskResult:
        """
        Runs a single task, including setup, agent execution, verification, and cleanup.
        """
        # Stage 1: Set up the initial state for the task
        setup_start_time = time.time()
        logger.info(
            "\n┌─ Stage 1: Setup ─────────────────────────────────────────────────────"
        )
        setup_success = self.state_manager.set_up(task)
        setup_time = time.time() - setup_start_time

        if not setup_success:
            logger.error(f"State setup failed for task: {task.name}")
            return TaskResult(
                task_name=task.name,
                success=False,
                execution_time=setup_time,
                error_message="State Duplication Error",
                category=task.category,
                task_id=task.task_id,
            )
        display_time = self._format_duration(setup_time)
        logger.info(
            f"└─ Completed in {display_time}\n"
        )

        # Stage 2: Execute the task using the agent
        logger.info(
            "┌─ Stage 2: Execute ───────────────────────────────────────────────────"
        )

        execute_start_time = time.time()

        # Get task instruction from task manager
        task_instruction = self.task_manager.get_task_instruction(task)

        # Execute with agent
        agent_result = self.agent.execute_sync(task_instruction)

        execute_time = time.time() - execute_start_time

        # ---------- Write messages.json to task_output_dir ----------
        task_output_dir = self._get_task_output_dir(task)
        task_output_dir.mkdir(parents=True, exist_ok=True)
        messages_path = task_output_dir / "messages.json"
        self.results_reporter.save_messages_json(
            agent_result.get("output", []), messages_path
        )

        # Set service-specific environment variables for verification scripts
        self.state_manager.set_verification_environment(str(messages_path))
        logger.info(
            f"└─ Completed in {self._format_duration(execute_time)}\n"
        )

        # Stage 3: Verify
        logger.info(
            "┌─ Stage 3: Verify ────────────────────────────────────────────────────"
        )
        verify_start_time = time.time()
        try:
            result = self.task_manager.execute_task(task, agent_result)
        finally:
            # Clean up environment variables
            import os
            os.environ.pop("MCP_MESSAGES", None)
            os.environ.pop("MCP_GITHUB_TOKEN", None)
        verify_time = time.time() - verify_start_time
        logger.info(
            f"└─ Completed in {self._format_duration(verify_time)}\n"
        )


        # Stage 4: Clean up
        logger.info(
            "┌─ Stage 4: Cleanup ───────────────────────────────────────────────────"
        )
        cleanup_start_time = time.time()
        self.state_manager.clean_up(task)
        cleanup_time = time.time() - cleanup_start_time
        logger.info(
            f"└─ Completed in {self._format_duration(cleanup_time)}\n"
        )

        return result

    def run_evaluation(self, task_filter: str) -> EvaluationReport:
        """
        Runs the full evaluation for the specified tasks.
        """
        tasks = self.task_manager.filter_tasks(task_filter)
        pipeline_start_time = time.time()

        results = []

        for task in tasks:
            # ------------------------ Resume check ------------------------
            existing_result = self._load_latest_task_result(task)

            # ------------------------------------------------------
            # Decide whether to skip or retry this task based on the
            # previous result and retryable pipeline errors.
            # ------------------------------------------------------
            retry_due_to_error = (
                existing_result is not None
                and not existing_result.success
                and existing_result.error_message in PIPELINE_RETRY_ERRORS
            )

            if existing_result and not retry_due_to_error:
                # Existing result is either successful or failed with a non-retryable error – skip.
                logger.info(
                    "↩️  Skipping already-completed task (resume): %s", task.name
                )
                results.append(existing_result)
                continue

            if retry_due_to_error:
                # Clean previous artifacts so that new results fully replace them.
                task_output_dir = self._get_task_output_dir(task)
                if task_output_dir.exists():
                    shutil.rmtree(task_output_dir)
                logger.info(
                    "🔄 Retrying task due to pipeline error (%s): %s",
                    existing_result.error_message,
                    task.name,
                )

            # -------------------- Execute new task -----------------------
            task_start = time.time()
            task_result = self._run_single_task(task)
            task_end = time.time()

            results.append(task_result)

            # ----------------------------------------------------------
            # Save results for this single task immediately for resume
            # ----------------------------------------------------------
            # Prepare directory & save
            task_output_dir = self._get_task_output_dir(task)
            task_output_dir.mkdir(parents=True, exist_ok=True)

            # Save messages.json (conversation trajectory)
            messages_path = task_output_dir / "messages.json"

            # ↓↓↓ 修改处 ↓↓↓
            if not messages_path.exists():  # 已经写过就跳过
                messages = (
                    task_result.model_output
                    if getattr(task_result, "model_output", None)
                    else []
                )
                self.results_reporter.save_messages_json(messages, messages_path)
            # ↑↑↑ 修改结束 ↑↑↑

            # Save meta.json (all other metadata)
            meta_path = task_output_dir / "meta.json"
            model_config = {
                "mcp_service": self.mcp_service,
                "model_name": self.actual_model_name,
                "timeout": self.timeout,
            }
            self.results_reporter.save_meta_json(
                task_result,
                model_config,
                datetime.fromtimestamp(task_start),
                datetime.fromtimestamp(task_end),
                meta_path,
            )

        pipeline_end_time = time.time()

        # --------------------------------------------------------------
        # Aggregate results – combine current `results` with any previously
        # saved TaskResults that ALSO match the current task_filter.
        # --------------------------------------------------------------

        # Helper: determine if a TaskResult matches the filter string
        def _matches_filter(tr: TaskResult, flt: str) -> bool:
            if flt.lower() == "all":
                return True
            if "/" in flt:
                # specific task (category/task_N)
                return tr.task_name == flt
            # category level
            return tr.category == flt

        # Pull existing reports from disk and merge
        existing_results = [
            r
            for r in self._gather_all_task_results()
            if _matches_filter(r, task_filter)
        ]

        # Merge, giving preference to fresh `results` (avoids duplicates)
        merged: dict[str, TaskResult] = {r.task_name: r for r in existing_results}
        merged.update({r.task_name: r for r in results})  # overwrite with latest run

        final_results = list(merged.values())

        aggregated_report = EvaluationReport(
            model_name=self.model,
            model_config={
                "mcp_service": self.mcp_service,
                "model_name": self.actual_model_name,
                "timeout": self.timeout,
            },
            start_time=datetime.fromtimestamp(pipeline_start_time),
            end_time=datetime.fromtimestamp(pipeline_end_time),
            total_tasks=len(final_results),
            successful_tasks=sum(1 for r in final_results if r.success),
            failed_tasks=sum(1 for r in final_results if not r.success),
            task_results=final_results,
            tasks_filter=task_filter,
        )

        # Save model-level summary
        summary_path = self.base_experiment_dir / "summary.json"
        self.results_reporter.save_model_summary(aggregated_report, summary_path)

        logger.info(
            "\n============================================================"
            "\nResults Summary"
            "\n============================================================"
        )
        logger.info(
            f"✓ Tasks passed: {aggregated_report.successful_tasks}/{aggregated_report.total_tasks} ({aggregated_report.success_rate:.1f}%)"
        )
        logger.info(
            f"⏱ Total time: {aggregated_report.execution_time.total_seconds():.1f}s"
        )

        return aggregated_report
