"""
Playwright Task Manager for MCPBench
====================================

Simple task manager for Playwright MCP tasks.
Follows anti-over-engineering principles: keep it simple, do what's needed.
"""

import sys
from pathlib import Path
from typing import List, Optional
from importlib.machinery import SourceFileLoader
from subprocess import CompletedProcess

from src.base.task_manager import BaseTask, BaseTaskManager
from src.mcp_services.playwright.playwright_state_manager import PlaywrightStateManager


class PlaywrightTaskManager(BaseTaskManager):
    """Simple task manager for Playwright MCP tasks."""

    def __init__(self, tasks_root: Path = None, state_manager: Optional[PlaywrightStateManager] = None):
        """Initialize with tasks directory and (optionally) an existing state manager."""
        if tasks_root is None:
            tasks_root = Path(__file__).resolve().parents[3] / "tasks"

        super().__init__(tasks_root, service="playwright", task_class=BaseTask,
                         task_organization="directory")

        # Keep reference to the PlaywrightStateManager so we can hand over the
        # live Page instance to verification.
        if state_manager is not None:
            self.state_manager = state_manager
        else:
            # Try to reuse an existing global instance first (created during
            # execution phase); fall back to creating a new one if absent.
            self.state_manager = PlaywrightStateManager.get_global_instance() or PlaywrightStateManager()

    def _get_verification_command(self, task: BaseTask) -> List[str]:
        """Get verification command - just run the verify.py script."""
        return [sys.executable, str(task.task_verification_path)]

    def _format_task_instruction(self, base_instruction: str) -> str:
        """Add Playwright-specific note to instructions."""
        return base_instruction + "\n\nUse Playwright MCP tools to complete this web automation task."

    # ---------------------------------------------------------------------
    # Verification
    # ---------------------------------------------------------------------

    def run_verification(self, task: BaseTask) -> CompletedProcess:
        """Run the task's verify.py in-process so we can pass the live Page."""

        # Dynamically import the verify module so we can call verify_task() directly
        loader = SourceFileLoader(f"verify_{task.name.replace('/', '_')}", str(task.task_verification_path))
        verify_mod = loader.load_module()

        # Grab the active Page (if any) from the state manager
        page = None
        if hasattr(self, "state_manager") and self.state_manager:
            try:
                page = self.state_manager.get_last_page()
            except AttributeError:
                page = None

            # If last page is None but浏览器 context 仍在，开一个新 tab 保持同 session
            if page is None:
                try:
                    ctx = self.state_manager.get_current_context()
                    if ctx is not None:
                        page = ctx.new_page()
                        # 也记到 state_manager 方便后续调用
                        self.state_manager._remember_page(page)  # type: ignore
                except Exception:
                    page = None

        # Call verify_task – fall back gracefully if signature mismatch
        try:
            if page is not None:
                success = verify_mod.verify_task(page)
            else:
                success = verify_mod.verify_task()
        except TypeError:
            # Older verify.py that doesn't accept page parameter
            success = verify_mod.verify_task()
        except Exception as exc:
            return CompletedProcess(args=[str(task.task_verification_path)], returncode=1, stdout="", stderr=str(exc))

        return CompletedProcess(args=[str(task.task_verification_path)], returncode=0 if success else 1, stdout="", stderr="")