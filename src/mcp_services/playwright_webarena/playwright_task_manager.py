"""
WebArena Playwright Task Manager for MCPMark
============================================

Simple task manager for WebArena-backed Playwright MCP tasks.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Dict, Any

from src.base.task_manager import BaseTask, BaseTaskManager


class PlaywrightTaskManager(BaseTaskManager):
    """Task manager for Playwright tasks against a WebArena environment."""

    def __init__(self, tasks_root: Path | None = None, base_url: str | None = None):
        if tasks_root is None:
            tasks_root = Path(__file__).resolve().parents[3] / "tasks"
        super().__init__(
            tasks_root,
            mcp_service="playwright_webarena",
            task_class=BaseTask,
            task_organization="directory",
        )
        self.base_url = base_url

    def _create_task_from_files(
        self, category_name: str, task_files_info: Dict[str, Any]
    ) -> BaseTask:
        # Preserve numeric ID when present (e.g. "task_1")
        try:
            task_id = int(task_files_info["task_name"].split("_")[1])
        except (IndexError, ValueError):
            task_id = task_files_info["task_name"]

        task = BaseTask(
            task_instruction_path=task_files_info["instruction_path"],
            task_verification_path=task_files_info["verification_path"],
            service="playwright_webarena",
            category=category_name,
            task_id=task_id,
        )
        # Attach base_url so agents can target the correct environment
        if self.base_url and hasattr(task, "__dict__"):
            task.base_url = self.base_url
        return task

    def _get_verification_command(self, task: BaseTask) -> List[str]:
        return [sys.executable, str(task.task_verification_path)]

    def _format_task_instruction(self, base_instruction: str) -> str:
        note = "Use Playwright MCP tools to complete this task."
        if self.base_url:
            note += f" Target environment: {self.base_url}"
        return base_instruction + "\n\n" + note
