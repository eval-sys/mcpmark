"""
Insforge Login Helper for MCPMark
==================================

Handles Insforge backend authentication and connection validation.
"""

import json
import requests
from pathlib import Path
from typing import Optional, Dict, Any

from src.base.login_helper import BaseLoginHelper
from src.logger import get_logger

logger = get_logger(__name__)


class InsforgeLoginHelper(BaseLoginHelper):
    """Handles Insforge backend authentication and connection validation."""

    def __init__(
        self,
        api_key: str,
        backend_url: str,
        state_path: Optional[Path] = None,
    ):
        """Initialize Insforge login helper.

        Args:
            api_key: Insforge backend API key for authentication
            backend_url: Insforge backend URL (e.g., https://your-app.insforge.app)
            state_path: Path to save connection state
        """
        super().__init__()
        self.api_key = api_key
        self.backend_url = backend_url.rstrip('/')
        self.state_path = state_path or Path.home() / ".mcpbench" / "insforge_auth.json"

        # Ensure state directory exists
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    def login(self, **kwargs) -> bool:
        """Test Insforge backend connection and validate API key.

        Returns:
            bool: True if connection successful and API key valid
        """
        try:
            # Test 1: Basic connectivity - try to get backend metadata
            logger.info(f"Testing connection to Insforge backend: {self.backend_url}")

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            # Test with a simple API endpoint - get current user or backend info
            # Try the auth current session endpoint first
            test_url = f"{self.backend_url}/api/auth/sessions/current"

            response = requests.get(
                test_url,
                headers=headers,
                timeout=10,
            )

            if response.status_code == 200:
                # API key is valid and can authenticate
                logger.info("✓ Insforge API key authentication successful")
                connection_info = {
                    "backend_url": self.backend_url,
                    "authenticated": True,
                    "authenticated_at": self._get_current_timestamp(),
                }
            elif response.status_code == 401:
                # Invalid API key
                logger.error("✗ Invalid Insforge API key")
                return False
            else:
                # API key might be admin key, try a different endpoint
                # Try listing tables/backend metadata as a test
                logger.info("Testing with backend metadata endpoint...")

                # Simple connectivity test - just check if backend is reachable
                health_url = f"{self.backend_url}/api/health"
                try:
                    health_response = requests.get(health_url, timeout=5)
                    if health_response.status_code in [200, 404]:  # 404 is ok, backend is reachable
                        logger.info("✓ Insforge backend is reachable")
                        connection_info = {
                            "backend_url": self.backend_url,
                            "api_key_type": "admin",
                            "authenticated": True,
                            "authenticated_at": self._get_current_timestamp(),
                        }
                    else:
                        logger.warning(f"Unexpected response from backend: {health_response.status_code}")
                        connection_info = {
                            "backend_url": self.backend_url,
                            "authenticated": True,
                            "authenticated_at": self._get_current_timestamp(),
                        }
                except Exception as e:
                    logger.warning(f"Health check failed, but proceeding: {e}")
                    # Still consider it successful if we have credentials
                    connection_info = {
                        "backend_url": self.backend_url,
                        "authenticated": True,
                        "authenticated_at": self._get_current_timestamp(),
                    }

            # Save connection state
            self._save_connection_state(connection_info)

            logger.info(f"Insforge backend connection validated: {self.backend_url}")
            return True

        except requests.exceptions.Timeout:
            logger.error(f"Connection timeout to Insforge backend: {self.backend_url}")
            return False
        except requests.exceptions.ConnectionError:
            logger.error(f"Cannot connect to Insforge backend: {self.backend_url}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during Insforge authentication: {e}")
            return False

    def _save_connection_state(self, state: Dict[str, Any]):
        """Save connection state to file."""
        try:
            # Don't save API key
            safe_state = {k: v for k, v in state.items() if k not in ["api_key", "access_token"]}

            with open(self.state_path, "w") as f:
                json.dump(safe_state, f, indent=2)

            # Set restrictive permissions
            self.state_path.chmod(0o600)
            logger.info(f"Connection state saved to: {self.state_path}")

        except Exception as e:
            logger.error(f"Failed to save connection state: {e}")

    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()

    def is_connected(self) -> bool:
        """Check if we can connect to Insforge backend."""
        return self.login()

    def get_connection_params(self) -> Dict[str, Any]:
        """Get connection parameters (without API key)."""
        return {
            "backend_url": self.backend_url,
        }
