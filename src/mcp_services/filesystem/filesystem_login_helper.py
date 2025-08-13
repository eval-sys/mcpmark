"""
Filesystem Login Helper for MCPMark
====================================

This module provides a minimal login helper for the filesystem MCP service.
Since filesystem operations don't require authentication, this is a simple
pass-through implementation that satisfies the interface requirements.
"""

from pathlib import Path
from typing import Optional

from src.base.login_helper import BaseLoginHelper
from src.logger import get_logger

logger = get_logger(__name__)


class FilesystemLoginHelper(BaseLoginHelper):
    """
    Login helper for filesystem MCP service.

    The filesystem MCP server doesn't require authentication, so this
    implementation simply returns success for all login operations.
    """

    def __init__(self, state_path: Optional[Path] = None):
        """
        Initialize the filesystem login helper.

        Args:
            state_path: Path to save state (not used for filesystem)
        """
        super().__init__()
        self.state_path = state_path or Path.home() / ".mcpbench" / "filesystem_state.json"
        logger.info("Initialized FilesystemLoginHelper (no auth required)")

    def login(self, **kwargs) -> bool:
        """
        Perform login operation.

        Since filesystem doesn't require authentication, this always returns True.

        Returns:
            bool: Always True for filesystem service
        """
        logger.info("Filesystem service does not require authentication")
        return True

    def is_authenticated(self) -> bool:
        """
        Check if authenticated.

        Returns:
            bool: Always True for filesystem service
        """
        return True

    def get_credentials(self) -> dict:
        """
        Get credentials for the service.

        Returns:
            dict: Empty dict as no credentials needed
        """
        return {}
