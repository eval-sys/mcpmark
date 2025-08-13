"""
PostgreSQL State Manager for MCPMark
=====================================

Manages database state for PostgreSQL tasks including schema setup,
test data creation, and cleanup.
"""

import psycopg2
from psycopg2 import sql
from typing import Optional, Dict, Any, List

from src.base.state_manager import BaseStateManager, InitialStateInfo
from src.base.task_manager import BaseTask
from src.logger import get_logger

logger = get_logger(__name__)


class PostgresStateManager(BaseStateManager):
    """Manages PostgreSQL database state for task evaluation."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = None,
        username: str = None,
        password: str = None,
    ):
        """Initialize PostgreSQL state manager.

        Args:
            host: Database host
            port: Database port
            database: Main database name
            username: Database username
            password: Database password
            template_db: Template database for initial states
        """
        super().__init__(service_name="postgres")

        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password

        # Connection parameters
        self.conn_params = {
            "host": host,
            "port": port,
            "user": username,
            "password": password
        }

        # Track created databases for cleanup
        self.created_databases: List[str] = []

        # Track current task database for agent configuration
        self._current_task_database: Optional[str] = None

        # Validate connection on initialization
        try:
            self._test_connection()
            logger.info("PostgreSQL state manager initialized successfully")
        except Exception as e:
            raise RuntimeError(f"PostgreSQL initialization failed: {e}")

    def _test_connection(self):
        """Test database connection."""
        conn = psycopg2.connect(**self.conn_params, database="postgres")
        conn.close()

    def _create_initial_state(self, task: BaseTask) -> Optional[InitialStateInfo]:
        """Create initial database state for a task."""
        try:
            # Generate unique database name
            db_name = f"mcpbench_{task.category}_{task.task_id}_{self._get_timestamp()}"

            # Create database from template if exists, otherwise empty
            if self._database_exists(task.category):
                self._create_database_from_template(db_name, task.category)
                logger.info(f"Created database '{db_name}' from template '{task.category}'")
            else:
                self._create_empty_database(db_name)
                logger.info(f"Created empty database '{db_name}'")

            # Track for cleanup
            self.created_databases.append(db_name)
            self.track_resource('database', db_name, {'task': task.name})

            # Set up initial schema/data based on task category
            # self._setup_task_specific_data(db_name, task)

            return InitialStateInfo(
                state_id=db_name,
                state_url=f"postgresql://{self.username}@{self.host}:{self.port}/{db_name}",
                metadata={
                    'database': db_name,
                    'category': task.category,
                    'task_id': task.task_id
                }
            )

        except Exception as e:
            logger.error(f"Failed to create initial state for {task.name}: {e}")
            return None

    def _store_initial_state_info(self, task: BaseTask, state_info: InitialStateInfo) -> None:
        """Store database info in task object."""
        if hasattr(task, '__dict__'):
            task.database_name = state_info.state_id
            task.database_url = state_info.state_url
            # Store current task database for agent configuration
            self._current_task_database = state_info.state_id

    def _cleanup_task_initial_state(self, task: BaseTask) -> bool:
        """Clean up task database."""
        if hasattr(task, 'database_name') and task.database_name:
            try:
                self._drop_database(task.database_name)
                logger.info(f"Dropped database: {task.database_name}")

                # Remove from tracking
                self.created_databases = [db for db in self.created_databases if db != task.database_name]
                # Clear current task database
                if self._current_task_database == task.database_name:
                    self._current_task_database = None
                return True
            except Exception as e:
                logger.error(f"Failed to drop database {task.database_name}: {e}")
                return False
        return True

    def _cleanup_single_resource(self, resource: Dict[str, Any]) -> bool:
        """Clean up a single PostgreSQL resource."""
        if resource['type'] == 'database':
            try:
                self._drop_database(resource['id'])
                logger.info(f"Dropped database: {resource['id']}")
                return True
            except Exception as e:
                logger.error(f"Failed to drop database {resource['id']}: {e}")
                return False
        return False

    def _database_exists(self, db_name: str) -> bool:
        """Check if database exists."""
        conn = psycopg2.connect(**self.conn_params, database="postgres")
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s",
                    (db_name,)
                )
                return cur.fetchone() is not None
        finally:
            conn.close()

    def _create_database_from_template(self, new_db: str, template_db: str):
        """Create database from template."""
        conn = psycopg2.connect(**self.conn_params, database="postgres")
        conn.autocommit = True
        try:
            with conn.cursor() as cur:
                cur.execute(sql.SQL("""
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = %s AND pid <> pg_backend_pid()
                """), (template_db,))
                cur.execute(sql.SQL(
                    "CREATE DATABASE {} WITH TEMPLATE {}"
                ).format(
                    sql.Identifier(new_db),
                    sql.Identifier(template_db)
                ))
        finally:
            conn.close()

    def _create_empty_database(self, db_name: str):
        """Create empty database."""
        conn = psycopg2.connect(**self.conn_params, database="postgres")
        conn.autocommit = True
        try:
            with conn.cursor() as cur:
                cur.execute(sql.SQL(
                    "CREATE DATABASE {}"
                ).format(sql.Identifier(db_name)))
        finally:
            conn.close()

    def _drop_database(self, db_name: str):
        """Drop database."""
        conn = psycopg2.connect(**self.conn_params, database="postgres")
        conn.autocommit = True
        try:
            with conn.cursor() as cur:
                # Terminate connections
                cur.execute(sql.SQL("""
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = %s AND pid <> pg_backend_pid()
                """), (db_name,))

                # Drop database
                cur.execute(sql.SQL(
                    "DROP DATABASE IF EXISTS {}"
                ).format(sql.Identifier(db_name)))
        finally:
            conn.close()

    def _setup_task_specific_data(self, db_name: str, task: BaseTask):
        """Set up task-specific schema and data."""
        conn = psycopg2.connect(**self.conn_params, database=db_name)
        try:
            with conn.cursor() as cur:
                if task.category == "basic_queries":
                    self._setup_basic_queries_data(cur)
                elif task.category == "data_manipulation":
                    self._setup_data_manipulation_data(cur)
                elif task.category == "table_operations":
                    self._setup_table_operations_data(cur)
                # Add more categories as needed

            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to setup task data: {e}")
            raise
        finally:
            conn.close()

    def _setup_basic_queries_data(self, cursor):
        """Set up data for basic query tasks."""
        cursor.execute("""
            CREATE TABLE employees (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                department VARCHAR(50),
                salary DECIMAL(10, 2),
                hire_date DATE
            );

            INSERT INTO employees (name, department, salary, hire_date) VALUES
            ('John Doe', 'Engineering', 75000.00, '2020-01-15'),
            ('Jane Smith', 'Marketing', 65000.00, '2019-03-22'),
            ('Bob Johnson', 'Engineering', 80000.00, '2018-07-01'),
            ('Alice Brown', 'HR', 55000.00, '2021-02-10');
        """)

    def _setup_data_manipulation_data(self, cursor):
        """Set up data for data manipulation tasks."""
        cursor.execute("""
            CREATE TABLE products (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                category VARCHAR(50),
                price DECIMAL(10, 2),
                stock INTEGER DEFAULT 0
            );

            CREATE TABLE orders (
                id SERIAL PRIMARY KEY,
                product_id INTEGER REFERENCES products(id),
                quantity INTEGER NOT NULL,
                order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

    def _setup_table_operations_data(self, cursor):
        """Set up for table operation tasks."""
        # Start with minimal schema that tasks will modify
        cursor.execute("""
            CREATE TABLE test_table (
                id SERIAL PRIMARY KEY,
                data VARCHAR(255)
            );
        """)

    def _get_timestamp(self) -> str:
        """Get timestamp for unique naming."""
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d%H%M%S")

    def get_service_config_for_agent(self) -> dict:
        """Get configuration for agent execution."""
        config = {
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "password": self.password
        }

        # If there's a current task database, include it
        if hasattr(self, '_current_task_database') and self._current_task_database:
            config["current_database"] = self._current_task_database
            config["database_url"] = f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self._current_task_database}"
        else:
            # Fallback to default database
            config["database"] = self.database
            config["database_url"] = f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"

        return config
