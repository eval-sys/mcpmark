"""
Playwright Task Manager for MCPMark
====================================

Simple task manager for Playwright MCP tasks.
Follows anti-over-engineering principles: keep it simple, do what's needed.
"""

import sys
import os
import subprocess
from pathlib import Path
from typing import List, Dict, Any

from src.base.task_manager import BaseTask, BaseTaskManager
from src.logger import get_logger

logger = get_logger(__name__)


class PlaywrightTaskManager(BaseTaskManager):
    """Simple task manager for Playwright MCP tasks."""

    def __init__(self, tasks_root: Path = None):
        """Initialize with tasks directory."""
        if tasks_root is None:
            tasks_root = Path(__file__).resolve().parents[3] / "tasks"

        super().__init__(
            tasks_root,
            mcp_service="playwright",
            task_class=BaseTask,
            task_organization="directory",
        )

    def _create_task_from_files(
        self, category_name: str, task_files_info: Dict[str, Any]
    ) -> BaseTask:
        """Instantiate a `BaseTask` from the dictionary returned by `_find_task_files`."""
        # Extract numeric ID from folder name like "task_1" so that the default
        # `BaseTask.name` ("{category}/task_{task_id}") matches the original path
        # pattern used by the CLI filter, e.g. "form_interaction/task_1".
        try:
            task_id = int(task_files_info["task_name"].split("_")[1])
        except (IndexError, ValueError):
            # Fallback to entire slug when it is not in the expected format
            task_id = task_files_info["task_name"]

        return BaseTask(
            task_instruction_path=task_files_info["instruction_path"],
            task_verification_path=task_files_info["verification_path"],
            service="playwright",
            category=category_name,
            task_id=task_id,
        )

    def _get_verification_command(self, task: BaseTask) -> List[str]:
        """Get verification command - just run the verify.py script."""
        return [sys.executable, str(task.task_verification_path)]

    def run_verification(self, task: BaseTask) -> subprocess.CompletedProcess:
        """Run verification with Playwright-specific environment."""
        env = os.environ.copy()

        # Pass messages.json path and working directory to verification script
        messages_path = os.getenv("MCP_MESSAGES")
        work_dir = os.getenv("PLAYWRIGHT_WORK_DIR")
        
        if messages_path:
            env["MCP_MESSAGES"] = messages_path
            logger.debug(f"Setting MCP_MESSAGES to: {messages_path}")
        
        if work_dir:
            env["PLAYWRIGHT_WORK_DIR"] = work_dir
            logger.debug(f"Setting PLAYWRIGHT_WORK_DIR to: {work_dir}")

        return subprocess.run(
            self._get_verification_command(task),
            capture_output=True,
            text=True,
            timeout=90,
            env=env,
        )

    def _format_task_instruction(self, base_instruction: str) -> str:
        """Add Playwright-specific note to instructions."""
        return (
            base_instruction
            + "\n\nUse Playwright MCP tools to complete this web automation task."
        )
