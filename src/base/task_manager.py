#!/usr/bin/env python3
"""
Enhanced Base Task Manager with Common Task Discovery Logic
===========================================================

This module provides an improved base class for task managers that consolidates
common task discovery patterns while maintaining flexibility for service-specific needs.
"""

import re
import subprocess
import sys
import time
from abc import ABC
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.logger import get_logger
from src.results_reporter import TaskResult

logger = get_logger(__name__)


@dataclass
class BaseTask:
    """Base class for evaluation tasks."""

    task_instruction_path: Path
    task_verification_path: Path
    service: str
    category: str
    task_id: str

    @property
    def name(self) -> str:
        """Return the task name in the format 'category/task_id'."""
        return f"{self.category}/task_{self.task_id}"

    def get_task_instruction(self) -> str:
        """Return the full text content of the task instruction file."""
        if not self.task_instruction_path.exists():
            raise FileNotFoundError(
                f"Task instruction file not found: {self.task_instruction_path}"
            )

        return self.task_instruction_path.read_text(encoding="utf-8")


class BaseTaskManager(ABC):
    """Enhanced base class for service-specific task managers with common discovery logic."""

    def __init__(
        self,
        tasks_root: Path,
        mcp_service: str = None,
        task_class: type = None,
        task_organization: str = None,
    ):
        """Initialize the base task manager.

        Args:
            tasks_root: Root directory containing all tasks
            mcp_service: MCP service name (e.g., 'notion', 'github', 'filesystem')
            task_class: Custom task class to use (defaults to BaseTask)
            task_organization: 'file' or 'directory' based task organization
        """
        self.tasks_root = tasks_root
        self.mcp_service = mcp_service or self.__class__.__name__.lower().replace(
            "taskmanager", ""
        )
        self.task_class = task_class or BaseTask
        self.task_organization = task_organization
        self._tasks_cache = None

    # =========================================================================
    # Common Task Discovery Implementation
    # =========================================================================

    def discover_all_tasks(self) -> List[BaseTask]:
        """Discover all available tasks for this service (common implementation)."""
        if self._tasks_cache is not None:
            return self._tasks_cache

        tasks = []
        service_dir = self.tasks_root / (
            self.mcp_service or self._get_service_directory_name()
        )

        if not service_dir.exists():
            logger.warning(
                f"{self.mcp_service.title()} tasks directory does not exist: {service_dir}"
            )
            return tasks

        # Scan categories
        for category_dir in service_dir.iterdir():
            if not self._is_valid_category_dir(category_dir):
                continue

            category_name = category_dir.name
            logger.info("Discovering tasks in category: %s", category_name)

            # Find tasks using service-specific logic
            task_files = self._find_task_files(category_dir)
            for task_files_info in task_files:
                task = self._create_task_from_files(category_name, task_files_info)
                if task:
                    tasks.append(task)
                    logger.debug("Found task: %s", task.name)

        # Sort and cache
        # Sort by category and a stringified task_id to handle both numeric IDs and slugs uniformly
        self._tasks_cache = sorted(tasks, key=lambda t: (t.category, str(t.task_id)))
        logger.info(
            "Discovered %d %s tasks across all categories",
            len(self._tasks_cache),
            self.mcp_service.title(),
        )
        return self._tasks_cache

    def get_categories(self) -> List[str]:
        """Get a list of all task categories (common implementation)."""
        tasks = self.discover_all_tasks()
        return sorted(list(set(task.category for task in tasks)))

    def filter_tasks(self, task_filter: str) -> List[BaseTask]:
        """Filter tasks based on category or specific task pattern (common implementation)."""
        all_tasks = self.discover_all_tasks()

        if not task_filter or task_filter.lower() == "all":
            return all_tasks

        # Check if it's a category filter
        categories = self.get_categories()
        if task_filter in categories:
            return [task for task in all_tasks if task.category == task_filter]

        # Check for specific task pattern (category/task_X)
        if "/" in task_filter:
            try:
                category, task_part = task_filter.split("/", 1)
                if task_part.startswith("task_"):
                    task_id = int(task_part.split("_")[1])
                    for task in all_tasks:
                        if task.category == category and task.task_id == task_id:
                            return [task]
            except (ValueError, IndexError):
                pass

        # Fallback: check for partial matches in task names or categories
        filtered_tasks = []
        for task in all_tasks:
            if (
                task_filter in task.category
                or task_filter in task.name
                or task_filter == str(task.task_id)
            ):
                filtered_tasks.append(task)

        return filtered_tasks

    # =========================================================================
    # Common Helper Methods
    # =========================================================================

    def extract_task_id(
        self, filename: str, pattern: Optional[str] = None
    ) -> Optional[int]:
        """Extract task ID from filename (common implementation).

        Args:
            filename: The filename to extract ID from
            pattern: Optional custom regex pattern (default: r'task_(\\d+)\\.md')

        Returns:
            Task ID or None if not found
        """
        if pattern is None:
            pattern = r"task_(\d+)\.md"

        match = re.match(pattern, filename)
        return int(match.group(1)) if match else None

    def get_task_instruction(self, task: BaseTask) -> str:
        """Get formatted task instruction (template method)."""
        base_instruction = self._read_task_instruction(task)
        return self._format_task_instruction(base_instruction)

    def execute_task(self, task: BaseTask, agent_result: Dict[str, Any]) -> TaskResult:
        """Execute task verification (template method)."""
        start_time = time.time()
        logger.info(f"| Verifying task ({self.mcp_service.title()}): {task.name}")

        try:
            # Check for any pre-execution conditions
            pre_check_result = self._pre_execution_check(task)
            if not pre_check_result["success"]:
                execution_time = time.time() - start_time
                return TaskResult(
                    task_name=task.name,
                    success=False,
                    execution_time=execution_time,
                    error_message=pre_check_result["error"],
                    category=task.category,
                    task_id=task.task_id,
                )

            # If agent execution failed, return the failure
            if not agent_result.get("success", False):
                execution_time = time.time() - start_time
                error_message = agent_result.get("error", "Agent execution failed")

                # Standardize MCP network errors
                error_message = self._standardize_error_message(error_message)

                # Log the agent failure so users can distinguish it from verification errors
                logger.error(f"| ✗ Agent execution failed for task")
                logger.error(f"| ⚠️ Error: {error_message}")
                logger.warning(
                    f"| - Skipping verification for task: {task.name} due to agent failure"
                )

                return TaskResult(
                    task_name=task.name,
                    success=False,
                    execution_time=execution_time,
                    error_message=error_message,
                    category=task.category,
                    task_id=task.task_id,
                )

            # Run verification using service-specific command
            verify_result = self.run_verification(task)

            # Process results
            success = verify_result.returncode == 0
            print(verify_result.stdout)
            error_message = (
                verify_result.stderr if not success and verify_result.stderr else None
            )
            execution_time = time.time() - start_time

            # Post-execution cleanup or tracking
            self._post_execution_hook(task, success)

            if success:
                logger.info(f"| Verification Result: \033[92m✓ PASSED\033[0m")
            else:
                logger.error(f"| Verification Result: \033[91m✗ FAILED\033[0m")
                if error_message:
                    logger.error(f"| Error: {error_message}")

            return TaskResult(
                task_name=task.name,
                success=success,
                execution_time=execution_time,
                error_message=error_message,
                model_output=agent_result.get("output", ""),
                category=task.category,
                task_id=task.task_id,
                token_usage=agent_result.get("token_usage", {}),
                turn_count=agent_result.get("turn_count", -1),
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Task verification failed: {e}", exc_info=True)
            return TaskResult(
                task_name=task.name,
                success=False,
                execution_time=execution_time,
                error_message=str(e),
                category=task.category,
                task_id=task.task_id,
            )

    def run_verification(self, task: BaseTask) -> subprocess.CompletedProcess:
        """Run the verification script for a task (can be overridden).

        Default implementation runs the verification command.
        Services can override this to add environment variables or custom logic.
        """
        return subprocess.run(
            self._get_verification_command(task),
            # capture_output=True,
            text=True,
            timeout=90,
        )

    # =========================================================================
    # Abstract Methods - Minimal Set Required
    # =========================================================================

    def _get_service_directory_name(self) -> str:
        """Return the service directory name (e.g., 'notion', 'github').

        Default implementation uses the service parameter if provided.
        """
        if self.mcp_service:
            return self.mcp_service
        raise NotImplementedError(
            "Must provide service parameter or implement _get_service_directory_name"
        )

    def _get_task_organization(self) -> str:
        """Return task organization type: 'directory' or 'file'.

        - 'directory': Tasks organized as task_X/description.md (Notion)
        - 'file': Tasks organized as task_X.md (GitHub, Filesystem)

        Default implementation uses the task_organization parameter if provided.
        """
        if self.task_organization:
            return self.task_organization
        raise NotImplementedError(
            "Must provide task_organization parameter or implement _get_task_organization"
        )

    # Note: _create_task_instance is no longer needed - use task_class parameter instead

    # =========================================================================
    # Hook Methods with Smart Defaults
    # =========================================================================

    def _is_valid_category_dir(self, category_dir: Path) -> bool:
        """Check if a directory is a valid category directory."""
        return (
            category_dir.is_dir()
            and not category_dir.name.startswith(".")
            and category_dir.name != "utils"
        )

    def _find_task_files(self, category_dir: Path) -> List[Dict[str, Any]]:
        """Find task files in a category directory (smart default implementation).

        Automatically handles both directory-based and file-based organization.
        """
        task_files: List[Dict[str, Any]] = []

        for task_dir in category_dir.iterdir():
            # Skip anything that is not a directory or is hidden
            if not task_dir.is_dir() or task_dir.name.startswith("."):
                continue

            description_path = task_dir / "description.md"
            verify_path = task_dir / "verify.py"

            # We consider a directory a valid task only if the two mandatory files exist
            if not (description_path.exists() and verify_path.exists()):
                logger.warning(
                    "Skipping %s – missing description.md or verify.py", task_dir
                )
                continue

            task_files.append(
                {
                    "task_name": task_dir.name,
                    "instruction_path": description_path,
                    "verification_path": verify_path,
                }
            )

        return task_files

    def _create_task_from_files(
        self, category_name: str, task_files_info: Dict[str, Any]
    ) -> Optional[BaseTask]:
        """Create a task from file information (default implementation)."""
        return self.task_class(
            task_instruction_path=task_files_info["description"],
            task_verification_path=task_files_info["verification"],
            mcp_service=self.mcp_service,
            category=category_name,
            task_id=task_files_info["task_id"],
        )

    def _read_task_instruction(self, task: BaseTask) -> str:
        """Read and return the task instruction content."""
        return task.get_task_instruction()

    def _format_task_instruction(self, base_instruction: str) -> str:
        """Format task instruction with Notion-specific additions."""
        return (
            base_instruction
            + "\n\nNote: Based on your understanding, solve the task all at once by yourself, don't ask for my opinions on anything."
        )

    def _get_verification_command(self, task: BaseTask) -> List[str]:
        """Get the command to run task verification (default implementation)."""
        return [sys.executable, str(task.task_verification_path)]

    def _pre_execution_check(self, task: BaseTask) -> Dict[str, Any]:
        """Perform pre-execution checks (default: always success)."""
        return {"success": True}

    def _post_execution_hook(self, task: BaseTask, success: bool) -> None:
        """Perform post-execution actions (default: no action)."""
        pass

    def _standardize_error_message(self, error_message: str) -> str:
        """Standardize error messages for consistent reporting."""
        from src.errors import standardize_error_message

        return standardize_error_message(error_message, mcp_service=self.mcp_service)
