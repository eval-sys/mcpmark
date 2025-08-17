"""
PostgreSQL Task Manager for MCPMark
====================================

Manages PostgreSQL task discovery, execution, and verification.
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
class PostgresTask(BaseTask):
    """PostgreSQL-specific task with database information."""

    task_name: str = ""
    database_name: Optional[str] = None
    database_url: Optional[str] = None
    expected_queries: Optional[List[str]] = None
    expected_tables: Optional[List[str]] = None


class PostgresTaskManager(BaseTaskManager):
    """Manages PostgreSQL tasks for MCPMark evaluation."""

    def __init__(self, tasks_root: Path = None):
        """Initialize PostgreSQL task manager.

        Args:
            tasks_root: Path to tasks directory
        """
        if tasks_root is None:
            tasks_root = Path(__file__).resolve().parents[3] / "tasks"

        super().__init__(
            tasks_root,
            mcp_service="postgres",
            task_class=PostgresTask,
            task_organization="file",  # PostgreSQL uses file-based tasks
        )

    def _create_task_from_files(
        self, category_name: str, task_files_info: Dict[str, Any]
    ) -> Optional[PostgresTask]:
        """Instantiate a `PostgresTask` from the dictionary returned by `_find_task_files`."""

        return PostgresTask(
            task_instruction_path=task_files_info["instruction_path"],
            task_verification_path=task_files_info["verification_path"],
            service="postgres",
            category=category_name,
            task_id=task_files_info["task_name"],
            task_name=task_files_info["task_name"],
        )

    def _get_verification_command(self, task: PostgresTask) -> List[str]:
        """Get verification command with database info."""
        cmd = [sys.executable, str(task.task_verification_path)]

        # Pass database name as argument if available
        if task.database_name:
            cmd.append(task.database_name)

        return cmd

    def run_verification(self, task: BaseTask) -> subprocess.CompletedProcess:
        """Run verification with PostgreSQL environment."""
        env = os.environ.copy()

        # Pass database connection info to verification script
        if hasattr(task, "database_name") and task.database_name:
            env["POSTGRES_DATABASE"] = task.database_name

        if hasattr(task, "database_url") and task.database_url:
            env["DATABASE_URL"] = task.database_url

        return subprocess.run(
            self._get_verification_command(task),
            capture_output=True,
            text=True,
            timeout=90,
            env=env,
        )

    def _format_task_instruction(self, base_instruction: str) -> str:
        """Add PostgreSQL-specific instructions."""
        return (
            base_instruction
            + "\n\nNote: Use PostgreSQL MCP tools to complete this task. The database connection is already configured."
        )
