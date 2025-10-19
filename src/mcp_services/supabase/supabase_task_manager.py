"""
Supabase Task Manager for MCPMark
===================================

Manages Supabase task discovery, execution, and verification.
Reuses Postgres tasks but accesses them via PostgREST/Supabase MCP.
"""

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.base.task_manager import BaseTask, BaseTaskManager
from src.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SupabaseTask(BaseTask):
    """Supabase-specific task with API information."""

    task_name: str = ""
    api_url: Optional[str] = None
    api_key: Optional[str] = None


class SupabaseTaskManager(BaseTaskManager):
    """Manages Supabase tasks for MCPMark evaluation.

    Uses the same task structure as Postgres tasks but accessed via
    PostgREST/Supabase MCP server.
    """

    def __init__(self, tasks_root: Path = None):
        """Initialize Supabase task manager.

        Args:
            tasks_root: Path to tasks directory
        """
        if tasks_root is None:
            tasks_root = Path(__file__).resolve().parents[3] / "tasks"

        super().__init__(
            tasks_root,
            mcp_service="supabase",
            task_class=SupabaseTask,
            task_organization="file",  # Supabase uses file-based tasks (like Postgres)
        )

    def _create_task_from_files(
        self, category_id: str, task_files_info: Dict[str, Any]
    ) -> Optional[SupabaseTask]:
        """Instantiate a `SupabaseTask` from the dictionary returned by `_find_task_files`."""
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

        return SupabaseTask(
            task_instruction_path=task_files_info["instruction_path"],
            task_verification_path=task_files_info["verification_path"],
            service="supabase",
            category_id=final_category_id,
            task_id=task_id,
            task_name=task_files_info["task_id"],
        )

    def _get_verification_command(self, task: SupabaseTask) -> List[str]:
        """Get verification command with Supabase API info."""
        cmd = [sys.executable, str(task.task_verification_path)]
        return cmd

    def run_verification(self, task: BaseTask) -> subprocess.CompletedProcess:
        """Run verification with Supabase environment."""
        env = os.environ.copy()

        # Pass Supabase connection info to verification script
        if hasattr(task, "api_url") and task.api_url:
            env["SUPABASE_API_URL"] = task.api_url

        if hasattr(task, "api_key") and task.api_key:
            env["SUPABASE_API_KEY"] = task.api_key

        return subprocess.run(
            self._get_verification_command(task),
            capture_output=True,
            text=True,
            timeout=300,
            env=env,
        )

    def _format_task_instruction(self, base_instruction: str) -> str:
        """Add Supabase-specific instructions."""
        return (
            base_instruction
            + "\n\nNote: Use Supabase MCP tools (PostgREST) to complete this task. The API connection is already configured."
        )
