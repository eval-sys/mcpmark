"""
Supabase State Manager for MCPMark
====================================

Manages database state for Supabase tasks using the same PostgreSQL backend
as Insforge, but accessed via PostgREST/Supabase MCP server.
"""

import os
import sys
import subprocess
import psycopg2
from psycopg2 import sql
from pathlib import Path
from typing import Optional, Dict, Any, List

from src.base.state_manager import BaseStateManager, InitialStateInfo
from src.base.task_manager import BaseTask
from src.logger import get_logger

logger = get_logger(__name__)


class SupabaseStateManager(BaseStateManager):
    """Manages Supabase/PostgREST database state for task evaluation.

    Uses the same PostgreSQL database as Insforge but exposes it via
    PostgREST API for the Supabase MCP server to access.
    """

    def __init__(
        self,
        api_url: str,
        api_key: str,
        postgres_host: str = "localhost",
        postgres_port: int = 54322,  # Supabase CLI default port
        postgres_user: str = "postgres",
        postgres_password: str = "postgres",
        postgres_database: str = "postgres",  # Supabase CLI default database
    ):
        """Initialize Supabase state manager.

        Args:
            api_url: PostgREST API URL from Supabase CLI (default: http://localhost:54321)
            api_key: API key from Supabase CLI (anon or service_role key)
            postgres_host: PostgreSQL host for direct database operations
            postgres_port: PostgreSQL port (Supabase CLI uses 54322)
            postgres_user: PostgreSQL username
            postgres_password: PostgreSQL password
            postgres_database: Main PostgreSQL database name
        """
        super().__init__(service_name="supabase")

        self.api_url = api_url.rstrip('/')
        self.api_key = api_key

        # PostgreSQL connection for state management (Supabase CLI instance)
        self.postgres_host = postgres_host
        self.postgres_port = postgres_port
        self.postgres_user = postgres_user
        self.postgres_password = postgres_password
        self.postgres_database = postgres_database

        # Track current task context for agent configuration
        self._current_task_context: Optional[Dict[str, Any]] = None

        # Validate connection on initialization
        try:
            self._test_connection()
            logger.info("Supabase state manager initialized successfully")
        except Exception as e:
            raise RuntimeError(f"Supabase initialization failed: {e}")

        # Store baseline tables (system tables that exist before any tasks run)
        self._baseline_tables = set(
            (t['schema'], t['name']) for t in self._get_all_tables()
        )
        logger.debug(f"Stored baseline: {len(self._baseline_tables)} tables")

    def _test_connection(self):
        """Test PostgreSQL connection."""
        try:
            conn_params = {
                "host": self.postgres_host,
                "port": self.postgres_port,
                "user": self.postgres_user,
                "password": self.postgres_password,
                "database": self.postgres_database,
            }
            conn = psycopg2.connect(**conn_params)
            conn.close()
            logger.debug("PostgreSQL connection test successful")
        except Exception as e:
            raise RuntimeError(f"Cannot connect to PostgreSQL: {e}")

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

            logger.info(f"| Creating initial state for Supabase task: {task.name}")

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
                "created_tables": created_tables,
            }

            return InitialStateInfo(
                state_id=state_id,
                state_url=self.api_url,
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
            task.api_url = self.api_url
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

        The script should use database operations to set up required state.

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
            "SUPABASE_API_URL": self.api_url,
            "SUPABASE_API_KEY": self.api_key,
            "POSTGRES_HOST": self.postgres_host,
            "POSTGRES_PORT": str(self.postgres_port),
            "POSTGRES_DATABASE": self.postgres_database,
            "POSTGRES_USERNAME": self.postgres_user,
            "POSTGRES_PASSWORD": self.postgres_password,
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
        conn_params = {
            "host": self.postgres_host,
            "port": self.postgres_port,
            "user": self.postgres_user,
            "password": self.postgres_password,
            "database": self.postgres_database,
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
        conn_params = {
            "host": self.postgres_host,
            "port": self.postgres_port,
            "user": self.postgres_user,
            "password": self.postgres_password,
            "database": self.postgres_database,
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
        conn_params = {
            "host": self.postgres_host,
            "port": self.postgres_port,
            "user": self.postgres_user,
            "password": self.postgres_password,
            "database": self.postgres_database,
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
        conn_params = {
            "host": self.postgres_host,
            "port": self.postgres_port,
            "user": self.postgres_user,
            "password": self.postgres_password,
            "database": self.postgres_database,
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
        # Path to backup file (same as used by Insforge/Postgres)
        backup_dir = Path(__file__).parent.parent.parent.parent / "postgres_state"
        backup_file = backup_dir / f"{category_name}.backup"

        logger.debug(f"| Looking for backup at: {backup_file}")

        if not backup_file.exists():
            logger.info(f"| ○ No backup file found: {backup_file}")
            return False

        logger.info(f"| Restoring {category_name} from backup...")

        # Set up environment for pg_restore
        env = os.environ.copy()
        env["PGPASSWORD"] = self.postgres_password

        try:
            # Restore backup
            result = subprocess.run(
                [
                    "pg_restore",
                    "-h", self.postgres_host,
                    "-p", str(self.postgres_port),
                    "-U", self.postgres_user,
                    "-d", self.postgres_database,
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
        connect to the Supabase/PostgREST endpoint.

        Returns:
            Dictionary containing API URL and API key
        """
        config = {
            "api_url": self.api_url,
            "api_key": self.api_key,
            "schema": "public",  # Default schema for PostgREST
        }

        # Include current task context if available
        if self._current_task_context:
            config["task_context"] = self._current_task_context
            # If task uses a specific schema, include it
            if self._current_task_context.get("schema"):
                config["schema"] = self._current_task_context["schema"]

        return config

    def set_verification_environment(self, messages_path: str = None) -> None:
        """Set environment variables needed for verification scripts.

        Args:
            messages_path: Optional path to messages.json file for verification
        """
        os.environ["SUPABASE_API_URL"] = self.api_url
        os.environ["SUPABASE_API_KEY"] = self.api_key

        # Set PostgreSQL connection details for direct database verification
        os.environ["POSTGRES_HOST"] = self.postgres_host
        os.environ["POSTGRES_PORT"] = str(self.postgres_port)
        os.environ["POSTGRES_DATABASE"] = self.postgres_database
        os.environ["POSTGRES_USERNAME"] = self.postgres_user
        os.environ["POSTGRES_PASSWORD"] = self.postgres_password

        if messages_path:
            os.environ["MCP_MESSAGES"] = str(messages_path)

        logger.debug("Verification environment variables set for Supabase (including direct postgres access)")
