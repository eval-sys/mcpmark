"""
GitHub Login Helper for MCPMark
================================

This module provides GitHub token authentication and validation utilities.
Unlike browser-based services, GitHub uses token-based authentication.
"""

import json
import requests
from pathlib import Path
from typing import Optional, Dict, Any

from src.base.login_helper import BaseLoginHelper
from src.logger import get_logger

logger = get_logger(__name__)


class GitHubLoginHelper(BaseLoginHelper):
    """
    Utility helper for GitHub token authentication and validation.
    """

    def __init__(
        self,
        token: Optional[str] = None,
        state_path: Optional[Path] = None,
    ) -> None:
        """
        Initialize the GitHub login helper.

        Args:
            token: GitHub Personal Access Token
            state_path: Path to save authentication state
        """
        self.token = token
        self.state_path = state_path or Path.home() / ".mcpbench" / "github_auth.json"

        # Ensure state directory exists
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    def login_and_save_state(self, **kwargs) -> bool:
        """
        Validate GitHub token and save authentication state.

        Returns:
            bool: True if authentication successful, False otherwise
        """
        if not self.token:
            logger.error("No GitHub token provided")
            return False

        try:
            # Validate token by making an authenticated request
            session = requests.Session()
            session.headers.update({
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github.v3+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "MCPMark/1.0"
            })

            # Get user information
            response = session.get("https://api.github.com/user")

            if response.status_code != 200:
                logger.error(f"GitHub authentication failed: {response.status_code} {response.text}")
                return False

            user_info = response.json()
            logger.info(f"GitHub authentication successful for user: {user_info['login']}")

            # Get token scopes
            token_scopes = self._get_token_scopes(session)

            # Save authentication state
            auth_state = {
                "user": user_info,
                "token_scopes": token_scopes,
                "authenticated_at": self._get_current_timestamp()
            }
            self._save_auth_state(auth_state)

            # Verify required permissions
            if not self._verify_required_permissions(token_scopes):
                logger.warning("GitHub token may not have all required permissions")
                return False

            return True

        except Exception as e:
            logger.error(f"GitHub authentication error: {e}")
            return False

    def _get_token_scopes(self, session: requests.Session) -> list:
        """Get the scopes available to the current token."""
        try:
            response = session.get("https://api.github.com/user")
            scopes_header = response.headers.get("X-OAuth-Scopes", "")
            if scopes_header:
                return [scope.strip() for scope in scopes_header.split(",") if scope.strip()]
            return []
        except Exception as e:
            logger.warning(f"Could not determine token scopes: {e}")
            return []

    def _verify_required_permissions(self, scopes: list) -> bool:
        """
        Verify that the token has the minimum required permissions.

        For MCPMark GitHub tasks, we typically need:
        - repo (for repository access)
        - read:user (for user information)
        """
        required_scopes = ["repo"]  # Minimum requirement
        recommended_scopes = ["repo", "read:user", "read:org"]

        has_required = all(scope in scopes for scope in required_scopes)
        if not has_required:
            logger.error(f"Token missing required scopes. Required: {required_scopes}, Available: {scopes}")
            return False

        has_recommended = all(scope in scopes for scope in recommended_scopes)
        if not has_recommended:
            logger.warning(f"Token missing some recommended scopes. Recommended: {recommended_scopes}, Available: {scopes}")

        return True

    def _save_auth_state(self, auth_state: Dict[str, Any]):
        """Save authentication state to local file."""
        try:
            with open(self.state_path, 'w') as f:
                json.dump(auth_state, f, indent=2, default=str)

            # Set restrictive permissions (user read/write only)
            self.state_path.chmod(0o600)
            logger.info(f"Authentication state saved to: {self.state_path}")

        except Exception as e:
            logger.error(f"Failed to save authentication state: {e}")

    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"

    def get_saved_auth_state(self) -> Optional[Dict[str, Any]]:
        """Load and return saved authentication state."""
        try:
            if self.state_path.exists():
                with open(self.state_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load authentication state: {e}")
        return None

    def is_token_valid(self) -> bool:
        """Check if the current token is still valid."""
        if not self.token:
            return False

        try:
            session = requests.Session()
            session.headers.update({
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github.v3+json"
            })

            response = session.get("https://api.github.com/user")
            return response.status_code == 200

        except Exception:
            return False

    def get_rate_limit_info(self) -> Dict[str, Any]:
        """Get current rate limit information for the token."""
        if not self.token:
            return {}

        try:
            session = requests.Session()
            session.headers.update({
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github.v3+json"
            })

            response = session.get("https://api.github.com/rate_limit")
            if response.status_code == 200:
                return response.json()

        except Exception as e:
            logger.warning(f"Failed to get rate limit info: {e}")

        return {}

    def test_repository_access(self, owner: str, repo: str) -> bool:
        """Test if the token has access to a specific repository."""
        if not self.token:
            return False

        try:
            session = requests.Session()
            session.headers.update({
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github.v3+json"
            })

            response = session.get(f"https://api.github.com/repos/{owner}/{repo}")
            return response.status_code == 200

        except Exception:
            return False
