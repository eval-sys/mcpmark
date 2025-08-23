"""
GitHub Task Manager for MCPMark Evaluation Pipeline
====================================================

This module provides utilities for discovering, filtering, and managing
GitHub-based evaluation tasks.

The task manager is responsible for:
- Task discovery and filtering
- Task verification and result processing
- Task-specific logic (NOT LLM execution)
"""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.base.task_manager import BaseTask, BaseTaskManager
from src.logger import get_logger

logger = get_logger(__name__)


@dataclass
class GitHubTask(BaseTask):
    """Represents a single evaluation task for GitHub service."""

    # GitHub-specific fields
    repository_url: Optional[str] = None
    branch_name: Optional[str] = None
    pr_number: Optional[int] = None
    issue_number: Optional[int] = None
    expected_actions: Optional[List[str]] = None  # Expected GitHub actions to verify

    # Directory-based task slug (e.g., "update_readme")
    task_name: str = ""

    # No need to override name property, inherited from BaseTask


class GitHubTaskManager(BaseTaskManager):
    """Manages task discovery, filtering, and verification for GitHub-based MCPMark evaluation."""

    def __init__(self, tasks_root: Path = None):
        """Initialize GitHub task manager.

        Args:
            tasks_root: Path to the tasks directory
        """
        if tasks_root is None:
            tasks_root = Path(__file__).resolve().parents[3] / "tasks"

        # Call parent constructor
        super().__init__(
            tasks_root,
            mcp_service="github",
            task_class=GitHubTask,
            task_organization="file",
        )  # GitHub uses file-based tasks

    # =========================================================================
    # Service-specific implementations
    # =========================================================================
    # No custom task discovery methods needed; relying entirely on BaseTaskManager defaults.

    def _create_task_from_files(
        self, category_id: str, task_files_info: Dict[str, Any]
    ) -> Optional[GitHubTask]:
        """Instantiate a GitHubTask from the dictionary yielded by _find_task_files."""
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

        return GitHubTask(
            task_instruction_path=task_files_info["instruction_path"],
            task_verification_path=task_files_info["verification_path"],
            service="github",
            category_id=final_category_id,
            task_id=task_id,
            task_name=task_files_info["task_id"],
        )

    def _get_verification_command(self, task: GitHubTask) -> List[str]:
        """Get the verification command for GitHub tasks."""
        return [sys.executable, str(task.task_verification_path)]

    def get_task_instruction(self, task: GitHubTask) -> str:
        """Return task instruction prefixed with repository context.

        Adds an English prefix to every GitHub task instruction so that the
        agent knows **exactly** which repository to operate on, following the
        pattern requested by the user:

            Please execute the following task in my repository {owner}/{repo_name}:

        If the repository URL has not yet been injected into the ``task`` (for
        example when the state manager has not run), we fall back to a more
        generic prefix without owner/repo placeholder.
        """
        # Read the original task description first
        base_instruction = task.get_task_instruction()

        # Derive the owner/repo pair from the repository URL if available
        prefix: str
        if task.repository_url:
            # Example URL: https://github.com/owner/repo_name.git (or without .git)
            url_parts = task.repository_url.rstrip("/").replace(".git", "").split("/")
            if len(url_parts) >= 2:
                owner, repo_name = url_parts[-2], url_parts[-1]
                prefix = f"Please execute the following task in my repository {owner}/{repo_name}:"
            else:
                prefix = "Please execute the following task:"
        else:
            prefix = "Please execute the following task:"

        # Compose instruction with prefix
        instruction_with_prefix = f"{prefix}\n\n{base_instruction.strip()}"
        
        # Apply the common formatting suffix from base class
        return self._format_task_instruction(instruction_with_prefix)
