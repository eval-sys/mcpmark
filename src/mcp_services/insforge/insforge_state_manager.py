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

        # Store baseline tables (system tables that exist before any tasks run)
        self._baseline_tables = set(
            (t['schema'], t['name']) for t in self._get_all_tables()
        )
        logger.debug(f"Stored baseline: {len(self._baseline_tables)} tables")

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

        Restores from backup which may place tables in public or task-specific schema.

        Args:
            task: Task for which to create initial state

        Returns:
            InitialStateInfo object or None if creation failed
        """
        try:
            # Generate unique state ID for this task run
            state_id = f"{task.category_id}_{task.task_id}_{self._get_timestamp()}"
            schema_name = task.category_id

            logger.info(f"| Creating initial state for Insforge task: {task.name}")

            # Drop schema first (cleanup from previous runs)
            self._drop_schema(schema_name)

            # Get list of existing tables before restore (to track what we create)
            tables_before = self._get_all_tables()
            logger.info(f"| Tables before restore: {len(tables_before)}")

            # Note: Don't create schema here - pg_restore will create it from the backup

            # Restore from backup if backup exists (may create tables in public or task schema)
            if self._restore_from_backup(schema_name):
                logger.info(f"| ✓ Restored '{schema_name}' from backup")
            else:
                logger.info(f"| ○ No backup found for '{schema_name}'")
                # Run prepare_environment.py if it exists
                task_prepared = self._run_prepare_environment(task)
                if not task_prepared:
                    logger.debug(f"| No prepare_environment.py found for task {task.name}")

            # Get list of tables after restore (to track what we need to clean up)
            tables_after = self._get_all_tables()

            # Track ALL new tables created by the restore (compare before/after)
            tables_before_set = {(t['schema'], t['name']) for t in tables_before}
            created_tables = [
                t for t in tables_after
                if (t['schema'], t['name']) not in tables_before_set
            ]

            logger.info(f"| Tracked {len(created_tables)} new tables for cleanup")
            for t in created_tables:
                logger.debug(f"|   - {t['schema']}.{t['name']}")

            # Track the task context including created tables
            context = {
                "state_id": state_id,
                "category_id": task.category_id,
                "task_id": task.task_id,
                "task_name": task.name,
                "schema": schema_name,
                "created_tables": created_tables,  # Track all created tables
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

        Drops ALL tables created during task (both setup and agent-created)
        by comparing against baseline.

        Args:
            task: Task whose initial state should be cleaned up

        Returns:
            True if cleanup successful
        """
        try:
            logger.info(f"| Cleaning up initial state for task: {task.name}")

            if self._current_task_context:
                schema_name = self._current_task_context.get("schema")

                # Get ALL current tables
                all_current_tables = self._get_all_tables()

                # Find tables to drop: anything not in baseline
                tables_to_drop = [
                    t for t in all_current_tables
                    if (t['schema'], t['name']) not in self._baseline_tables
                ]

                logger.info(f"| Found {len(tables_to_drop)} tables to clean up (setup + agent-created)")

                # Drop individual tables
                for table_info in tables_to_drop:
                    try:
                        self._drop_table(table_info["schema"], table_info["name"])
                        logger.debug(f"| ✓ Dropped table: {table_info['schema']}.{table_info['name']}")
                    except Exception as e:
                        logger.warning(f"| Failed to drop table {table_info}: {e}")

                # Drop the task schema (may be empty if all tables were in public)
                if schema_name:
                    try:
                        self._drop_schema(schema_name)
                        logger.info(f"| ✓ Dropped schema: {schema_name}")
                    except Exception as e:
                        logger.warning(f"| Failed to drop schema {schema_name}: {e}")

                # Clear task context
                if self._current_task_context.get("task_name") == task.name:
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

    def _drop_schema(self, schema_name: str) -> None:
        """Drop schema and all its contents."""
        import psycopg2
        from psycopg2 import sql

        conn_params = {
            "host": "localhost",
            "port": 5432,
            "user": "postgres",
            "password": "postgres",
            "database": "insforge",
        }

        conn = psycopg2.connect(**conn_params)
        conn.autocommit = True
        try:
            with conn.cursor() as cur:
                cur.execute(
                    sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                        sql.Identifier(schema_name)
                    )
                )
                logger.debug(f"| Dropped schema: {schema_name}")
        finally:
            conn.close()

    def _create_schema(self, schema_name: str) -> None:
        """Create empty schema."""
        import psycopg2
        from psycopg2 import sql

        conn_params = {
            "host": "localhost",
            "port": 5432,
            "user": "postgres",
            "password": "postgres",
            "database": "insforge",
        }

        conn = psycopg2.connect(**conn_params)
        conn.autocommit = True
        try:
            with conn.cursor() as cur:
                cur.execute(
                    sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema_name))
                )
                logger.debug(f"| Created schema: {schema_name}")
        finally:
            conn.close()

    def _get_all_tables(self) -> List[Dict[str, str]]:
        """Get list of all user tables.

        Returns:
            List of dicts with 'schema' and 'name' keys
        """
        import psycopg2

        conn_params = {
            "host": "localhost",
            "port": 5432,
            "user": "postgres",
            "password": "postgres",
            "database": "insforge",
        }

        conn = psycopg2.connect(**conn_params)
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT table_schema, table_name
                    FROM information_schema.tables
                    WHERE table_type = 'BASE TABLE'
                    AND table_schema NOT IN ('information_schema', 'pg_catalog')
                    AND table_schema NOT LIKE 'pg_%'
                    AND table_name NOT LIKE '\\_%'
                    ORDER BY table_schema, table_name
                """)
                rows = cur.fetchall()
                return [{"schema": row[0], "name": row[1]} for row in rows]
        finally:
            conn.close()

    def _drop_table(self, schema_name: str, table_name: str) -> None:
        """Drop a specific table or materialized view."""
        import psycopg2
        from psycopg2 import sql

        conn_params = {
            "host": "localhost",
            "port": 5432,
            "user": "postgres",
            "password": "postgres",
            "database": "insforge",
        }

        conn = psycopg2.connect(**conn_params)
        conn.autocommit = True
        try:
            with conn.cursor() as cur:
                # Try dropping as table first
                cur.execute(
                    sql.SQL("DROP TABLE IF EXISTS {}.{} CASCADE").format(
                        sql.Identifier(schema_name),
                        sql.Identifier(table_name)
                    )
                )
                # Also try dropping as materialized view (in case agent created one)
                cur.execute(
                    sql.SQL("DROP MATERIALIZED VIEW IF EXISTS {}.{} CASCADE").format(
                        sql.Identifier(schema_name),
                        sql.Identifier(table_name)
                    )
                )
                logger.debug(f"| Dropped table/view: {schema_name}.{table_name}")
        finally:
            conn.close()

    def _restore_from_backup(self, category_name: str) -> bool:
        """Restore from backup file.

        Tables may be restored into public schema or category-specific schema
        depending on how the backup was created.

        Args:
            category_name: Name of category (e.g., 'employees', 'chinook', 'lego')

        Returns:
            True if backup was restored, False if no backup exists
        """
        # Path to backup file
        backup_dir = Path(__file__).parent.parent.parent.parent / "postgres_state"
        backup_file = backup_dir / f"{category_name}.backup"

        logger.debug(f"| Looking for backup at: {backup_file}")
        logger.debug(f"| Backup exists: {backup_file.exists()}")

        if not backup_file.exists():
            logger.info(f"| ○ No backup file found: {backup_file}")
            return False

        logger.info(f"| Restoring {category_name} from backup...")

        # Set up environment for pg_restore
        env = os.environ.copy()
        env["PGPASSWORD"] = "postgres"

        try:
            # Restore backup without schema filter (tables go to whatever schema they're in)
            result = subprocess.run(
                [
                    "pg_restore",
                    "-h", "localhost",
                    "-p", "5432",
                    "-U", "postgres",
                    "-d", "insforge",
                    "-v",
                    str(backup_file),
                ],
                env=env,
                capture_output=True,
                text=True,
                timeout=120,  # 2 minute timeout
            )

            if result.returncode != 0 and "ERROR" in result.stderr:
                logger.warning(f"| pg_restore had errors for {category_name}: {result.stderr}")
                return False

            logger.info(f"| ✓ {category_name} restored successfully")
            return True

        except subprocess.TimeoutExpired:
            logger.error(f"| ✗ Restore timed out for {category_name}")
            return False
        except Exception as e:
            logger.error(f"| ✗ Failed to restore {category_name}: {e}")
            return False

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

        # Set PostgreSQL connection details for direct database verification
        # (Insforge exposes its internal postgres database for verification)
        os.environ["POSTGRES_HOST"] = "localhost"
        os.environ["POSTGRES_PORT"] = "5432"
        os.environ["POSTGRES_DATABASE"] = "insforge"
        os.environ["POSTGRES_USERNAME"] = "postgres"
        os.environ["POSTGRES_PASSWORD"] = "postgres"

        if messages_path:
            os.environ["MCP_MESSAGES"] = str(messages_path)

        logger.debug("Verification environment variables set for Insforge (including direct postgres access)")
