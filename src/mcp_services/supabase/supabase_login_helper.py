"""
Supabase Login Helper for MCPMark
===================================

Handles configuration and validation for Supabase MCP service.
"""

import os
from typing import Dict, Any, Optional

from src.base.login_helper import BaseLoginHelper
from src.logger import get_logger

logger = get_logger(__name__)


class SupabaseLoginHelper(BaseLoginHelper):
    """Login helper for Supabase MCP service.

    Validates PostgREST API URL and API key configuration.
    """

    def __init__(self):
        super().__init__("supabase")

    def prepare_credentials(self) -> Dict[str, Any]:
        """Prepare credentials for Supabase/PostgREST connection.

        Returns:
            Dictionary containing api_url, api_key, and postgres connection details
        """
        # Get PostgREST API configuration (from Supabase CLI)
        api_url = os.getenv("SUPABASE_API_URL", "http://localhost:54321")
        api_key = os.getenv("SUPABASE_API_KEY")

        # Get PostgreSQL connection details (Supabase CLI defaults)
        postgres_host = os.getenv("SUPABASE_DB_HOST", "localhost")
        postgres_port = int(os.getenv("SUPABASE_DB_PORT", "54322"))
        postgres_user = os.getenv("SUPABASE_DB_USER", "postgres")
        postgres_password = os.getenv("SUPABASE_DB_PASSWORD", "postgres")
        postgres_database = os.getenv("SUPABASE_DB_NAME", "postgres")

        if not api_key:
            logger.warning(
                "SUPABASE_API_KEY not set.\n"
                "Run 'supabase status' to get your anon or service_role key.\n"
                "Set SUPABASE_API_KEY in your .mcp_env file."
            )
            # Try to get it from supabase status
            api_key = self._get_key_from_supabase_status()

        return {
            "api_url": api_url,
            "api_key": api_key or "",
            "postgres_host": postgres_host,
            "postgres_port": postgres_port,
            "postgres_user": postgres_user,
            "postgres_password": postgres_password,
            "postgres_database": postgres_database,
        }

    def _get_key_from_supabase_status(self) -> Optional[str]:
        """Try to get anon key from supabase status command.

        Returns:
            Anon key if found, None otherwise
        """
        import subprocess

        try:
            result = subprocess.run(
                ["supabase", "status"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                # Parse output for anon key
                for line in result.stdout.split('\n'):
                    if 'anon key:' in line.lower():
                        # Extract the key after the colon
                        key = line.split(':', 1)[1].strip()
                        logger.info("Found anon key from 'supabase status'")
                        return key

        except (subprocess.SubprocessError, FileNotFoundError):
            logger.debug("Could not run 'supabase status' to get anon key")

        return None

    def test_credentials(self, credentials: Dict[str, Any]) -> bool:
        """Test if Supabase credentials are valid.

        Args:
            credentials: Dictionary with api_url, api_key, and postgres connection details

        Returns:
            True if credentials are valid
        """
        import requests
        import psycopg2

        api_url = credentials["api_url"]
        api_key = credentials.get("api_key", "")

        # Test PostgreSQL connection
        try:
            conn_params = {
                "host": credentials["postgres_host"],
                "port": credentials["postgres_port"],
                "user": credentials["postgres_user"],
                "password": credentials["postgres_password"],
                "database": credentials["postgres_database"],
            }
            conn = psycopg2.connect(**conn_params)
            conn.close()
            logger.info("✓ PostgreSQL connection successful")
        except Exception as e:
            logger.error(f"✗ PostgreSQL connection failed: {e}")
            return False

        # Test PostgREST API connection (optional - may not be running yet)
        try:
            headers = {}
            if api_key:
                headers["apikey"] = api_key
                headers["Authorization"] = f"Bearer {api_key}"

            response = requests.get(api_url, headers=headers, timeout=5)

            # Any response (including 404, 401) means the API is reachable
            logger.info(f"✓ PostgREST API reachable at {api_url} (status: {response.status_code})")
            return True

        except requests.exceptions.ConnectionError:
            logger.warning(
                f"⚠ PostgREST API not reachable at {api_url}.\n"
                "Make sure PostgREST is running (e.g., docker run -p 3000:3000 postgrest/postgrest)\n"
                "or use a cloud Supabase instance URL."
            )
            # Still return True as PostgreSQL connection works
            return True
        except Exception as e:
            logger.warning(f"⚠ PostgREST API test failed: {e}")
            # Still return True as PostgreSQL connection works
            return True

    def format_credentials_info(self, credentials: Dict[str, Any]) -> str:
        """Format credentials info for display.

        Args:
            credentials: Dictionary with connection details

        Returns:
            Formatted string describing the credentials
        """
        api_url = credentials["api_url"]
        has_api_key = bool(credentials.get("api_key"))
        postgres_host = credentials["postgres_host"]
        postgres_db = credentials["postgres_database"]

        return (
            f"Supabase Configuration:\n"
            f"  API URL: {api_url}\n"
            f"  API Key: {'✓ Configured' if has_api_key else '✗ Not set'}\n"
            f"  PostgreSQL: {postgres_host}/{postgres_db}"
        )
