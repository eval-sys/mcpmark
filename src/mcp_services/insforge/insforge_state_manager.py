"""
Insforge State Manager for MCPMark
===================================

Manages backend state for Insforge tasks including setup via prepare_environment.py
and resource cleanup tracking.
"""

import os
import sys
import subprocess
import requests
from pathlib import Path
from typing import Optional, Dict, Any, List

from src.base.state_manager import BaseStateManager, InitialStateInfo
from src.base.task_manager import BaseTask
from src.logger import get_logger

logger = get_logger(__name__)


class InsforgeStateManager(BaseStateManager):
    """Manages Insforge backend state for task evaluation."""

    def __init__(
        self,
        api_key: str,
        backend_url: str,
    ):
        """Initialize Insforge state manager.

        Args:
            api_key: Insforge backend API key for authentication
            backend_url: Insforge backend URL (e.g., https://your-app.insforge.app)
        """
        super().__init__(service_name="insforge")

        self.api_key = api_key
        self.backend_url = backend_url.rstrip('/')

        # HTTP headers for API requests
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Track current task context for agent configuration
        self._current_task_context: Optional[Dict[str, Any]] = None

        # Validate connection on initialization
        try:
            self._test_connection()
            logger.info("Insforge state manager initialized successfully")
        except Exception as e:
            raise RuntimeError(f"Insforge initialization failed: {e}")

    def _test_connection(self):
        """Test backend connection."""
        try:
            # Simple connectivity test - try any endpoint
            response = requests.get(
                f"{self.backend_url}/api/health",
                timeout=5,
            )
            # Any response (even 404) means backend is reachable
            logger.debug(f"Insforge backend connectivity test: {response.status_code}")
        except requests.exceptions.RequestException:
            # Try with API key
            try:
                response = requests.get(
                    f"{self.backend_url}/api/auth/sessions/current",
                    headers=self.headers,
                    timeout=5,
                )
                logger.debug(f"Insforge backend auth test: {response.status_code}")
            except Exception as inner_e:
                raise RuntimeError(f"Cannot connect to Insforge backend: {inner_e}")

    def _create_initial_state(self, task: BaseTask) -> Optional[InitialStateInfo]:
        """Create initial backend state for a task.

        This runs prepare_environment.py script if it exists in the task directory.
        The script should use Insforge MCP tools or HTTP API to set up tables, data, etc.

        Args:
            task: Task for which to create initial state

        Returns:
            InitialStateInfo object or None if creation failed
        """
        try:
            # Generate unique state ID for this task run
            state_id = f"{task.category_id}_{task.task_id}_{self._get_timestamp()}"

            logger.info(f"| Creating initial state for Insforge task: {task.name}")

            # Run prepare_environment.py if it exists
            task_prepared = self._run_prepare_environment(task)

            if not task_prepared:
                logger.debug(f"| No prepare_environment.py found for task {task.name}")

            # Track the task context
            context = {
                "state_id": state_id,
                "category_id": task.category_id,
                "task_id": task.task_id,
                "task_name": task.name,
            }

            return InitialStateInfo(
                state_id=state_id,
                state_url=self.backend_url,
                metadata=context,
            )

        except Exception as e:
            logger.error(f"Failed to create initial state for {task.name}: {e}")
            return None

    def _store_initial_state_info(
        self, task: BaseTask, state_info: InitialStateInfo
    ) -> None:
        """Store backend info in task object for agent access."""
        if hasattr(task, "__dict__"):
            task.backend_url = self.backend_url
            task.api_key = self.api_key
            task.state_id = state_info.state_id

            # Store current task context for agent configuration
            self._current_task_context = state_info.metadata

    def _cleanup_task_initial_state(self, task: BaseTask) -> bool:
        """Clean up task-specific resources.

        Note: Actual cleanup of created resources is delegated to prepare_environment.py
        cleanup scripts or handled by _cleanup_tracked_resources.

        Args:
            task: Task whose initial state should be cleaned up

        Returns:
            True if cleanup successful
        """
        try:
            logger.info(f"| Cleaning up initial state for task: {task.name}")

            # Clear current task context
            if (self._current_task_context and
                self._current_task_context.get("task_name") == task.name):
                self._current_task_context = None

            logger.info(f"| ✓ Initial state cleanup completed for {task.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to cleanup task initial state for {task.name}: {e}")
            return False

    def _cleanup_single_resource(self, resource: Dict[str, Any]) -> bool:
        """Clean up a single tracked resource.

        This is a placeholder for resource-specific cleanup logic.
        Tasks should handle their own cleanup via cleanup scripts.

        Args:
            resource: Resource dictionary with type, id, and metadata

        Returns:
            True if cleanup successful
        """
        resource_type = resource["type"]
        resource_id = resource["id"]

        logger.debug(f"| Cleanup for {resource_type} {resource_id} (handled by task scripts)")
        return True

    def _run_prepare_environment(self, task: BaseTask) -> bool:
        """Run prepare_environment.py script if it exists in the task directory.

        The script should use Insforge MCP tools or HTTP API to set up required state.

        Args:
            task: Task for which to prepare environment

        Returns:
            True if script ran successfully, False if script doesn't exist
        """
        task_dir = task.task_instruction_path.parent
        prepare_script = task_dir / "prepare_environment.py"

        if not prepare_script.exists():
            logger.debug(f"No prepare_environment.py found for task {task.name}")
            return False

        logger.info(f"| Running prepare_environment.py for task {task.name}")

        # Set up environment variables for the script
        env = os.environ.copy()
        env.update({
            "INSFORGE_BACKEND_URL": self.backend_url,
            "INSFORGE_API_KEY": self.api_key,
        })

        try:
            # Run the prepare_environment.py script
            result = subprocess.run(
                [sys.executable, str(prepare_script)],
                cwd=str(task_dir),  # Run from task directory
                env=env,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            if result.returncode == 0:
                logger.info(f"| ✓ Environment preparation completed for {task.name}")
                if result.stdout.strip():
                    logger.debug(f"| prepare_environment.py output: {result.stdout}")
                return True
            else:
                logger.error(f"| ✗ Environment preparation failed for {task.name}")
                logger.error(f"| Error output: {result.stderr}")
                raise RuntimeError(f"prepare_environment.py failed with exit code {result.returncode}")

        except subprocess.TimeoutExpired:
            logger.error(f"✗ Environment preparation timed out for {task.name}")
            raise RuntimeError("prepare_environment.py execution timed out")
        except Exception as e:
            logger.error(f"✗ Failed to run prepare_environment.py for {task.name}: {e}")
            raise

    def _get_timestamp(self) -> str:
        """Get timestamp for unique naming."""
        from datetime import datetime

        return datetime.now().strftime("%Y%m%d%H%M%S")

    def get_service_config_for_agent(self) -> dict:
        """Get configuration for agent execution.

        This configuration is passed to the agent/MCP server so it can
        connect to the Insforge backend.

        Returns:
            Dictionary containing backend URL and API key
        """
        config = {
            "backend_url": self.backend_url,
            "api_key": self.api_key,
        }

        # Include current task context if available
        if self._current_task_context:
            config["task_context"] = self._current_task_context

        return config

    def set_verification_environment(self, messages_path: str = None) -> None:
        """Set environment variables needed for verification scripts.

        Args:
            messages_path: Optional path to messages.json file for verification
        """
        os.environ["INSFORGE_BACKEND_URL"] = self.backend_url
        os.environ["INSFORGE_API_KEY"] = self.api_key

        if messages_path:
            os.environ["MCP_MESSAGES"] = str(messages_path)

        logger.debug("Verification environment variables set for Insforge")
