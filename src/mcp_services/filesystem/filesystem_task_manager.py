"""
Simplified Filesystem Task Manager using Enhanced Base Class
============================================================

This module shows how the filesystem task manager can be simplified
using the enhanced base task manager.
"""

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any

from src.base.task_manager import BaseTask, BaseTaskManager
from src.logger import get_logger

logger = get_logger(__name__)


@dataclass
class FilesystemTask(BaseTask):
    """Filesystem-specific task with additional fields."""

    test_directory: Optional[str] = None
    expected_files: Optional[List[str]] = None
    expected_directories: Optional[List[str]] = None

    @property
    def name(self) -> str:
        """Return the task name in the format 'category/task_id'."""
        # Handle both numeric task_id and string task_id for filesystem tasks
        if isinstance(self.task_id, int) or (
            isinstance(self.task_id, str) and self.task_id.isdigit()
        ):
            return f"{self.category}/task_{self.task_id}"
        else:
            # For arbitrary task names, use the task_id directly
            return f"{self.category}/{self.task_id}"


class FilesystemTaskManager(BaseTaskManager):
    """Simplified filesystem task manager using enhanced base class."""

    def __init__(self, tasks_root: Path = None):
        """Initialize filesystem task manager."""
        if tasks_root is None:
            tasks_root = Path(__file__).resolve().parents[3] / "tasks"

        super().__init__(
            tasks_root,
            mcp_service="filesystem",
            task_class=FilesystemTask,
            task_organization="directory",
        )

    # Override only what's needed for filesystem-specific behavior
    def _create_task_from_files(
        self, category_name: str, task_files_info: Dict[str, Any]
    ) -> BaseTask:
        """Instantiate a `BaseTask` from the dictionary returned by `_find_task_files`."""
        # Support arbitrary task names, not just task_n format
        task_name = task_files_info["task_name"]

        # Try to extract numeric ID from task_n format for backward compatibility
        task_id = task_name
        if task_name.startswith("task_") and "_" in task_name:
            try:
                numeric_id = int(task_name.split("_")[1])
                task_id = numeric_id
            except (IndexError, ValueError):
                # Keep the original task_name as task_id if parsing fails
                pass

        return self.task_class(
            task_instruction_path=task_files_info["instruction_path"],
            task_verification_path=task_files_info["verification_path"],
            service="filesystem",
            category=category_name,
            task_id=task_id,
        )

    def run_verification(self, task: BaseTask) -> subprocess.CompletedProcess:
        """Run verification with filesystem-specific environment."""
        env = os.environ.copy()

        # Pass test directory to verification script
        # Priority: task.test_directory (set by state manager) > environment variable
        test_dir = None
        if hasattr(task, "test_directory") and task.test_directory:
            test_dir = task.test_directory
        else:
            test_dir = os.getenv("FILESYSTEM_TEST_DIR")

        if test_dir:
            env["FILESYSTEM_TEST_DIR"] = test_dir
            logger.debug(f"Setting FILESYSTEM_TEST_DIR to: {test_dir}")

        return subprocess.run(
            self._get_verification_command(task),
            capture_output=True,
            text=True,
            timeout=90,
            env=env,
        )

    def filter_tasks(self, task_filter: str) -> List[BaseTask]:
        """Filter tasks based on category or specific task pattern with support for arbitrary task names."""
        all_tasks = self.discover_all_tasks()

        if not task_filter or task_filter.lower() == "all":
            return all_tasks

        # Check if it's a category filter
        categories = self.get_categories()
        if task_filter in categories:
            return [task for task in all_tasks if task.category == task_filter]

        # Check for specific task pattern (category/task_X or category/arbitrary_name)
        if "/" in task_filter:
            try:
                category, task_part = task_filter.split("/", 1)
                # Handle both task_X format and arbitrary task names
                if task_part.startswith("task_"):
                    # Try to extract numeric ID for backward compatibility
                    try:
                        task_id = int(task_part.split("_")[1])
                        for task in all_tasks:
                            if task.category == category and task.task_id == task_id:
                                return [task]
                    except (ValueError, IndexError):
                        # Fallback to string matching
                        for task in all_tasks:
                            if (
                                task.category == category
                                and str(task.task_id) == task_part
                            ):
                                return [task]
                else:
                    # Handle arbitrary task names
                    for task in all_tasks:
                        if task.category == category and str(task.task_id) == task_part:
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
