"""
GitHub MCP Service for MCPMark
===============================

This module provides GitHub-specific MCP server integration for MCPMark evaluation.
Uses GitHub's official remote MCP server for streamable HTTP/SSE communication.

Updated to include initial state-based environment replication mechanism.
"""

from .github_login_helper import GitHubLoginHelper
from .github_task_manager import GitHubTaskManager, GitHubTask
from .github_state_manager import GitHubStateManager

__all__ = ["GitHubLoginHelper", "GitHubTaskManager", "GitHubTask", "GitHubStateManager"]
