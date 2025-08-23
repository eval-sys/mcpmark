"""
WebArena Playwright Task Manager for MCPMark
============================================

Simple task manager for WebArena-backed Playwright MCP tasks.
"""

from __future__ import annotations
import sys
import os
import subprocess
from pathlib import Path
from typing import List, Dict, Any

from src.logger import get_logger
from src.base.task_manager import BaseTask, BaseTaskManager
logger = get_logger(__name__)

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

    def _create_task_from_files(
        self, category_id: str, task_files_info: Dict[str, Any]
    ) -> BaseTask:
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

        task = BaseTask(
            task_instruction_path=task_files_info["instruction_path"],
            task_verification_path=task_files_info["verification_path"],
            service="playwright_webarena",
            category_id=final_category_id,
            task_id=task_id,
        )
        
        return task


    # NEW: 注入统一前缀（基于 state manager 注入的 task.base_url）
    def get_task_instruction(self, task: BaseTask) -> str:
        base_instruction = task.get_task_instruction().strip()
        base_url = getattr(task, "base_url", None)
        prefix = f"Navigate to {base_url.rstrip('/')} and complete the following task."
        # 前缀 + 原始任务说明
        return self._format_task_instruction(f"{prefix}\n\n{base_instruction}")

    def _get_verification_command(self, task: BaseTask) -> List[str]:
        return [sys.executable, str(task.task_verification_path)]

    # 将 base_url 通过环境变量传给 verify.py
    def run_verification(self, task: BaseTask) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        base_url = getattr(task, "base_url", None)
        if base_url:
            env["WEBARENA_BASE_URL"] = base_url.rstrip("/")
        return subprocess.run(
            self._get_verification_command(task),
            capture_output=True,
            text=True,
            timeout=300,
            env=env,
        )

    def _format_task_instruction(self, base_instruction: str) -> str:
        note = "Use Playwright MCP tools to complete this task."
        return (base_instruction 
                + "\n\n" 
                + note + "\n\nNote: Based on your understanding, solve the task all at once by yourself, don't ask for my opinions on anything.")