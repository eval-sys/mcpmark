"""
PostgreSQL Login Helper for MCPMark
====================================

Handles PostgreSQL authentication and connection validation.
"""

import json
import psycopg2
from pathlib import Path
from typing import Optional, Dict, Any

from src.base.login_helper import BaseLoginHelper
from src.logger import get_logger

logger = get_logger(__name__)

class PostgresLoginHelper(BaseLoginHelper):
    """Handles PostgreSQL authentication and connection validation."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = None,
        username: str = None,
        password: str = None,
        state_path: Optional[Path] = None
    ):
        """Initialize PostgreSQL login helper.

        Args:
            host: Database host
            port: Database port
            database: Database name
            username: Database username
            password: Database password
            state_path: Path to save connection state
        """
        super().__init__()
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.state_path = state_path or Path.home() / ".mcpbench" / "postgres_auth.json"

        # Ensure state directory exists
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    def login(self, **kwargs) -> bool:
        """Test PostgreSQL connection and save state.

        Returns:
            bool: True if connection successful
        """
        try:
            # Test connection
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.username,
                password=self.password,
                connect_timeout=10
            )

            # Execute test query
            with conn.cursor() as cur:
                cur.execute("SELECT version()")
                version = cur.fetchone()[0]
                logger.info(f"PostgreSQL connection successful: {version}")

                # Check permissions
                cur.execute("""
                    SELECT has_database_privilege(%s, 'CREATE')
                """, (self.database,))
                can_create = cur.fetchone()[0]

                if not can_create:
                    logger.warning("User does not have CREATE privilege on database")

            conn.close()

            # Save connection state
            self._save_connection_state({
                "host": self.host,
                "port": self.port,
                "database": self.database,
                "username": self.username,
                "version": version,
                "can_create": can_create,
                "authenticated_at": self._get_current_timestamp()
            })

            return True

        except psycopg2.Error as e:
            logger.error(f"PostgreSQL connection failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during PostgreSQL login: {e}")
            return False

    def _save_connection_state(self, state: Dict[str, Any]):
        """Save connection state to file."""
        try:
            # Don't save password
            safe_state = {k: v for k, v in state.items() if k != 'password'}

            with open(self.state_path, 'w') as f:
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
        """Check if we can connect to PostgreSQL."""
        return self.login()

    def get_connection_params(self) -> Dict[str, Any]:
        """Get connection parameters (without password)."""
        return {
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "user": self.username
        }
