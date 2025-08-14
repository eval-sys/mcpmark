"""
Filesystem State Manager for MCPMark
=====================================

This module handles filesystem state management for consistent task evaluation.
It manages test directories, file creation/cleanup, and environment isolation.
"""

import os
import shutil
import urllib.request
import zipfile
import tempfile
import ssl
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.base.state_manager import BaseStateManager
from src.base.task_manager import BaseTask
from src.logger import get_logger

logger = get_logger(__name__)


class FilesystemStateManager(BaseStateManager):
    """
    Manages filesystem state for task evaluation.

    This includes creating isolated test directories, tracking created resources,
    and cleaning up after task completion.
    """

    def _get_project_root(self) -> Path:
        """Find project root by looking for marker files."""
        current = Path(__file__).resolve()

        # Look for project root markers
        for parent in current.parents:
            if (parent / "pyproject.toml").exists() or (parent / "pipeline.py").exists():
                return parent

        # Fallback to old method if markers not found
        return Path(__file__).parent / "../../../"

    def __init__(self, test_root: Optional[Path] = None, cleanup_on_exit: bool = False):
        """
        Initialize filesystem state manager.

        Args:
            test_root: Root directory for test operations (from FILESYSTEM_TEST_ROOT env var)
            cleanup_on_exit: Whether to clean up test directories after tasks (default False for persistent environment)
        """
        super().__init__(service_name="filesystem")

        # Use provided test root or default to persistent test environment
        if test_root:
            self.test_root = Path(test_root)
        else:
            # Default to persistent test environment
            project_root = self._get_project_root()
            self.test_root = (project_root / "test_environments/desktop").resolve()

        self.cleanup_on_exit = cleanup_on_exit
        self.current_task_dir: Optional[Path] = None
        self.created_resources: List[Path] = []

        # Backup and restore functionality
        self.backup_dir: Optional[Path] = None
        self.backup_enabled = (
            True  # Enable backup/restore by default for task isolation
        )

        logger.info(
            f"Initialized FilesystemStateManager with persistent test environment: {self.test_root}"
        )

    def initialize(self, **kwargs) -> bool:
        """
        Initialize the filesystem environment.

        Ensures the persistent test environment exists and is accessible.

        Returns:
            bool: True if initialization successful
        """
        try:
            # Ensure test environment directory exists
            if not self.test_root.exists():
                logger.error(f"Persistent test environment not found: {self.test_root}")
                logger.error(
                    "Please ensure test_environments/desktop/ exists in the repository"
                )
                return False

            logger.info(f"Using persistent test environment: {self.test_root}")

            # Verify we can write to the directory
            test_file = self.test_root / ".mcpbench_test"
            test_file.write_text("test")
            test_file.unlink()

            return True

        except Exception as e:
            logger.error(f"Failed to initialize filesystem environment: {e}")
            return False

    def set_up(self, task: BaseTask) -> bool:
        """
        Set up filesystem environment for a specific task.

        Creates a backup of the current environment, then uses the backup
        as the working directory to keep the original unchanged.

        Args:
            task: The task for which to set up the state

        Returns:
            bool: True if setup successful
        """
        try:
            # Dynamically set test root based on task category
            self._set_dynamic_test_root(task)

            # Create backup of current test environment before task execution
            if self.backup_enabled:
                if not self._create_backup(task):
                    logger.error(f"Failed to create backup for task {task.name}")
                    return False

            # Use the backup directory as the working directory instead of the original
            self.current_task_dir = (
                self.backup_dir
            )  # Use backup directory for operations

            logger.info(
                f"| ✓ Using the backup environment for operations"
            )

            # Store the test directory path in the task object for use by task manager
            if hasattr(task, "__dict__"):
                task.test_directory = str(self.current_task_dir)

            # Set environment variable for verification scripts and MCP server
            os.environ["FILESYSTEM_TEST_DIR"] = str(self.current_task_dir)

            return True

        except Exception as e:
            logger.error(f"Failed to set up filesystem state for {task.name}: {e}")
            return False

    def _set_dynamic_test_root(self, task: BaseTask) -> None:
        """
        Dynamically set the test root directory based on the task category.

        Args:
            task: The task for which to set the test root
        """
        # Get the base test environments directory from environment variable
        base_test_root = os.getenv("FILESYSTEM_TEST_ROOT")
        if not base_test_root:
            # Fallback to default path
            project_root = self._get_project_root()
            base_test_root = str(project_root / "test_environments")

        base_test_path = Path(base_test_root)

        # If task has a category, append it to the base path
        if task.category:
            self.test_root = base_test_path / task.category
            # Store the current task category for URL selection
            self._current_task_category = task.category
            logger.info(f"| ✓ Setting test root to category-specific directory: {self.test_root}")
        else:
            # Use the base test environments directory
            self.test_root = base_test_path
            # For base directory, use 'desktop' as default category
            self._current_task_category = 'desktop'
            logger.info(f"| Setting test root to base directory: {self.test_root}")

        # Ensure the directory exists by downloading and extracting if needed
        if not self.test_root.exists():
            logger.warning(f"Test directory does not exist: {self.test_root}")
            if not self._download_and_extract_test_environment():
                logger.error(f"Failed to download and extract test environment for: {self.test_root}")
                raise RuntimeError(f"Test environment not available: {self.test_root}")
            logger.info(f"Downloaded and extracted test environment: {self.test_root}")


    def clean_up(self, task: Optional[BaseTask] = None, **kwargs) -> bool:
        """
        Clean up filesystem resources created during task execution.

        Since we operate on the backup directory, we just need to clean up the backup.

        Args:
            task: The task to clean up after (optional)
            **kwargs: Additional cleanup options

        Returns:
            bool: True if cleanup successful
        """
        try:
            cleanup_success = True

            # Clean up the backup directory since we operated on it
            if self.backup_enabled and self.backup_dir and self.backup_dir.exists():
                try:
                    shutil.rmtree(self.backup_dir)
                    logger.info(
                        f"| ✓ Cleaned up backup directory for task {task.name if task else 'unknown'}"
                    )
                    self.backup_dir = None
                except Exception as e:
                    logger.error(f"Failed to clean up backup directory: {e}")
                    cleanup_success = False
            else:
                logger.info("No backup directory to clean up")

            # Clear the resources list
            self.created_resources.clear()

            return cleanup_success

        except Exception as e:
            logger.error(f"Filesystem cleanup failed: {e}")
            return False

    def get_test_directory(self) -> Optional[Path]:
        """
        Get the current test directory path.

        Returns:
            Path to the current test directory, or None if not set up
        """
        return self.current_task_dir

    def get_service_config_for_agent(self) -> dict:
        """
        Get service-specific configuration for agent execution.

        Returns:
            Dictionary containing configuration needed by the agent/MCP server
        """
        service_config = {}

        # Add test directory if available
        if self.current_task_dir:
            service_config["test_directory"] = str(self.current_task_dir)

        return service_config

    def track_resource(self, resource_path: Path):
        """
        Track a resource for cleanup.

        Args:
            resource_path: Path to the resource to track
        """
        if resource_path not in self.created_resources:
            self.created_resources.append(resource_path)
            logger.debug(f"Tracking resource for cleanup: {resource_path}")

    def reset_test_environment(self) -> bool:
        """
        Reset the test environment to its original state.

        This method can be used for development/debugging purposes.
        In normal operation, the persistent environment is maintained.

        Returns:
            bool: True if reset successful
        """
        try:
            # Remove any sorting directories that might have been created
            sorting_dirs = ["has_test", "no_test", "organized", "backup"]
            for dir_name in sorting_dirs:
                dir_path = self.test_root / dir_name
                if dir_path.exists():
                    shutil.rmtree(dir_path)
                    logger.info(f"Removed sorting directory: {dir_path}")

            # Remove any temporary files that might have been created
            temp_files = ["hello_world.txt", "new_file.txt", "temp.txt"]
            for file_name in temp_files:
                file_path = self.test_root / file_name
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"Removed temporary file: {file_path}")

            logger.info("Test environment reset completed")
            return True
        except Exception as e:
            logger.error(f"Test environment reset failed: {e}")
            return False

    # =========================================================================
    # Backup and Restore Methods for Task Isolation
    # =========================================================================

    def _create_backup(self, task: BaseTask) -> bool:
        """
        Create a complete backup of the test environment before task execution.

        Args:
            task: The task for which to create backup

        Returns:
            bool: True if backup successful
        """
        try:
            # Create backup directory with task-specific name
            project_root = self._get_project_root()
            backup_root = (project_root / ".mcpmark_backups").resolve()
            backup_root.mkdir(exist_ok=True)

            task_id = f"{task.service}_{task.category}_{task.task_id}"
            self.backup_dir = backup_root / f"backup_{task_id}_{os.getpid()}"

            # Remove existing backup if it exists
            if self.backup_dir.exists():
                shutil.rmtree(self.backup_dir)

            # Create fresh backup by copying entire test environment
            shutil.copytree(self.test_root, self.backup_dir)

            logger.info(f"| ✓ Created backup for task {task.name}: {self.backup_dir}")
            return True

        except Exception as e:
            logger.error(f"Failed to create backup for task {task.name}: {e}")
            return False

    def _restore_from_backup(self, task: Optional[BaseTask] = None) -> bool:
        """
        Restore the test environment from backup.

        Args:
            task: The task to restore after (optional, for logging)

        Returns:
            bool: True if restore successful
        """
        try:
            if not self.backup_dir or not self.backup_dir.exists():
                logger.error("No backup directory available for restore")
                return False

            # Remove current test environment
            if self.test_root.exists():
                shutil.rmtree(self.test_root)

            # Restore from backup
            shutil.copytree(self.backup_dir, self.test_root)

            # Clean up backup directory
            shutil.rmtree(self.backup_dir)
            self.backup_dir = None

            task_name = task.name if task else "unknown"
            logger.info(
                f"✅ Restored test environment from backup after task {task_name}"
            )
            return True

        except Exception as e:
            task_name = task.name if task else "unknown"
            logger.error(f"Failed to restore from backup after task {task_name}: {e}")
            return False

    # =========================================================================
    # Abstract Method Implementations Required by BaseStateManager
    # =========================================================================

    def _create_initial_state(self, task: BaseTask) -> Optional[Dict[str, Any]]:
        """Create initial state for a task.

        For filesystem, this is handled in set_up() method by creating task directories.
        Returns the task directory path as state info.
        """
        if self.current_task_dir and self.current_task_dir.exists():
            return {"task_directory": str(self.current_task_dir)}
        return None

    def _store_initial_state_info(
        self, task: BaseTask, state_info: Dict[str, Any]
    ) -> None:
        """Store initial state information in the task object.

        For filesystem, we store the test directory path.
        """
        if state_info and "task_directory" in state_info:
            if hasattr(task, "__dict__"):
                task.test_directory = state_info["task_directory"]

    def _cleanup_task_initial_state(self, task: BaseTask) -> bool:
        """Clean up initial state for a specific task.

        For filesystem, this means removing the task directory.
        """
        if hasattr(task, "test_directory") and task.test_directory:
            task_dir = Path(task.test_directory)
            if task_dir.exists():
                try:
                    shutil.rmtree(task_dir)
                    logger.info(f"Cleaned up task directory: {task_dir}")
                    return True
                except Exception as e:
                    logger.error(f"Failed to clean up task directory: {e}")
                    return False
        return True

    def _cleanup_single_resource(self, resource: Dict[str, Any]) -> bool:
        """Clean up a single tracked resource.

        For filesystem, resources are paths to files/directories.
        """
        if "path" in resource:
            resource_path = Path(resource["path"])
            if resource_path.exists():
                try:
                    if resource_path.is_dir():
                        shutil.rmtree(resource_path)
                    else:
                        resource_path.unlink()
                    logger.info(f"Cleaned up resource: {resource_path}")
                    return True
                except Exception as e:
                    logger.error(f"Failed to clean up {resource_path}: {e}")
                    return False
        return True

    def _download_and_extract_test_environment(self) -> bool:
        """
        Download and extract test environment from a predefined URL.

        Automatically selects the appropriate URL based on task category.

        Returns:
            bool: True if download and extraction successful
        """
        try:
            # Define URL mapping for different test environment categories
            url_mapping = {
                'desktop': 'https://storage.mcpmark.ai/filesystem/desktop.zip',
                'file_context': 'https://storage.mcpmark.ai/filesystem/file_context.zip',
                'file_property': 'https://storage.mcpmark.ai/filesystem/file_property.zip',
                'folder_structure': 'https://storage.mcpmark.ai/filesystem/folder_structure.zip',
                'papers': 'https://storage.mcpmark.ai/filesystem/papers.zip',
                'student_database': 'https://storage.mcpmark.ai/filesystem/student_database.zip',
                'threestudio': 'https://storage.mcpmark.ai/filesystem/threestudio.zip',
                'votenet': 'https://storage.mcpmark.ai/filesystem/votenet.zip'
            }

            # Get the category from the current task context
            category = getattr(self, '_current_task_category', None)
            if not category:
                logger.error("No task category available for URL selection")
                return False

            # Select the appropriate URL based on category
            if category in url_mapping:
                test_env_url = url_mapping[category]
                logger.info(f"Selected URL for category '{category}': {test_env_url}")
            else:
                logger.error(f"No URL mapping found for category: {category}")
                return False

            # Allow override via environment variable
            test_env_url = os.getenv('TEST_ENVIRONMENT_URL', test_env_url)

            logger.info(f"Downloading test environment from: {test_env_url}")

            # Create a temporary directory for the download
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                zip_path = temp_path / "test_environment.zip"

                # Download the zip file with SSL context
                logger.info("Downloading test environment zip file...")

                # Create SSL context that handles certificate issues
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

                # Use SSL context for download
                with urllib.request.urlopen(test_env_url, context=ssl_context) as response:
                    with open(zip_path, 'wb') as f:
                        f.write(response.read())

                # Extract the zip file, filtering out macOS metadata
                logger.info("Extracting test environment...")
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    # Filter out macOS metadata files
                    for file_info in zip_ref.filelist:
                        # Skip __MACOSX folder and its contents
                        if '__MACOSX' in file_info.filename or file_info.filename.startswith('._'):
                            continue

                        # Extract only the actual files
                        zip_ref.extract(file_info, self.test_root.parent)

                logger.info(f"Successfully extracted test environment to: {self.test_root.parent}")

                # Verify the extracted directory exists
                if not self.test_root.exists():
                    logger.error(f"Extracted directory not found at expected path: {self.test_root}")
                    return False

                return True

        except Exception as e:
            logger.error(f"Failed to download and extract test environment: {e}")
            return False
