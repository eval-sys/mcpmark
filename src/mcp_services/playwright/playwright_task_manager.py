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


class PlaywrightTask(BaseTask):
    """Playwright-specific task that uses directory name as task name."""
    


class PlaywrightTaskManager(BaseTaskManager):
    """Simple task manager for Playwright MCP tasks."""

    def __init__(self, tasks_root: Path = None):
        """Initialize with tasks directory."""
        if tasks_root is None:
            tasks_root = Path(__file__).resolve().parents[3] / "tasks"

        super().__init__(
            tasks_root,
            mcp_service="playwright",
            task_class=PlaywrightTask,
            task_organization="directory",
        )

    def _create_task_from_files(
        self, category_id: str, task_files_info: Dict[str, Any]
    ) -> PlaywrightTask:
        """Instantiate a `PlaywrightTask` from the dictionary returned by `_find_task_files`."""
        import json
        
        # Check for meta.json
        meta_path = task_files_info["instruction_path"].parent / "meta.json"
        final_category_id = category_id
        task_id = task_files_info["task_id"]
        
        if meta_path.exists():
            try:
                with open(meta_path, 'r') as f:
                    meta_data = json.load(f)
                    # Use values from meta.json if available
                    final_category_id = meta_data.get("category_id", category_id)
                    task_id = meta_data.get("task_id", task_id)
            except Exception as e:
                logger.warning(f"Failed to load meta.json from {meta_path}: {e}")

        return PlaywrightTask(
            task_instruction_path=task_files_info["instruction_path"],
            task_verification_path=task_files_info["verification_path"],
            service="playwright",
            category_id=final_category_id,
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
