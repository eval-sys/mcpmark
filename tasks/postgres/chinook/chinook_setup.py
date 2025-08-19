"""
Shared Chinook Database Setup Utilities

This module provides utilities for setting up the complete Chinook database
from the official source. Used by all Chinook tasks.
"""

import os
import logging
import tempfile
import subprocess
import requests
import psycopg2

logger = logging.getLogger(__name__)


def get_connection_params():
    """Get database connection parameters from environment variables."""
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", 5432)),
        "database": os.getenv("POSTGRES_DATABASE"),
        "user": os.getenv("POSTGRES_USERNAME"),
        "password": os.getenv("POSTGRES_PASSWORD"),
    }

def download_chinook_sql():
    """Download the official Chinook SQL script."""
    chinook_url = "https://raw.githubusercontent.com/neondatabase/postgres-sample-dbs/main/chinook.sql"

    logger.info(f"📥 Downloading Chinook SQL from {chinook_url}")

    try:
        # Download with requests (handles SSL/certificates better)
        response = requests.get(chinook_url, timeout=30)
        response.raise_for_status()  # Raise an exception for bad status codes

        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.sql', delete=False) as temp_file:
            temp_file.write(response.text)
            temp_file.flush()

            logger.info(f"✅ Downloaded Chinook SQL to {temp_file.name} ({len(response.text)} bytes)")
            return temp_file.name

    except requests.RequestException as e:
        logger.error(f"❌ Failed to download Chinook SQL: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Failed to download Chinook SQL: {e}")
        raise


def execute_sql_file_with_docker(sql_file_path):
    """Execute a SQL file using Docker with psql."""
    conn_params = get_connection_params()
    
    if not conn_params["database"]:
        raise ValueError("❌ No database specified in POSTGRES_DATABASE environment variable")
    
    logger.info(f"🗃️ Executing SQL file with Docker psql: {sql_file_path}")
    
    try:
        # Build the psql connection string
        conn_string = f"postgresql://{conn_params['user']}:{conn_params['password']}@{conn_params['host']}:{conn_params['port']}/{conn_params['database']}"
        
        # Docker command to run psql
        docker_cmd = [
            "docker", "run", "--rm",
            "--network", "host",  # Use host network to access localhost PostgreSQL
            "-v", f"{sql_file_path}:/tmp/chinook.sql:ro",  # Mount SQL file
            "postgres:latest",
            "psql", conn_string, "-f", "/tmp/chinook.sql"
        ]
        
        logger.info("🐳 Running psql in Docker container...")
        result = subprocess.run(
            docker_cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            logger.info("✅ SQL file executed successfully with Docker psql")
            if result.stdout.strip():
                logger.debug(f"psql output: {result.stdout}")
        else:
            logger.error(f"❌ Docker psql failed with exit code {result.returncode}")
            logger.error(f"Error output: {result.stderr}")
            raise RuntimeError(f"Docker psql execution failed")
            
    except subprocess.TimeoutExpired:
        logger.error("❌ Docker psql execution timed out")
        raise RuntimeError("Docker psql execution timed out")
    except Exception as e:
        logger.error(f"❌ Error executing SQL file with Docker: {e}")
        raise


def execute_sql_file(sql_file_path):
    """Execute a SQL file against the database."""
    try:
        # Try Docker approach first (most reliable for dump files)
        execute_sql_file_with_docker(sql_file_path)
    except Exception as docker_error:
        logger.warning(f"❌ Docker execution failed: {docker_error}")
        logger.info("🔄 Falling back to direct psycopg2 execution...")
        
        # Fallback to direct execution
        conn_params = get_connection_params()
        
        try:
            conn = psycopg2.connect(**conn_params)
            conn.autocommit = True
            
            with conn.cursor() as cur:
                with open(sql_file_path, 'r', encoding='utf-8') as f:
                    sql_content = f.read()
                
                # Filter out obvious pg_dump metadata and try to execute
                lines = sql_content.split('\n')
                filtered_lines = []
                
                for line in lines:
                    line = line.strip()
                    # Skip pg_dump metadata, comments, and empty lines
                    if (not line or 
                        line.startswith('--') or
                        line.startswith('Type:') or
                        line.startswith('Schema:') or
                        line.startswith('Owner:') or
                        'PostgreSQL database dump' in line):
                        continue
                    filtered_lines.append(line)
                
                # Join and split by semicolons for statement execution
                filtered_sql = '\n'.join(filtered_lines)
                statements = [stmt.strip() for stmt in filtered_sql.split(';') if stmt.strip()]
                
                success_count = 0
                for i, statement in enumerate(statements):
                    if statement and len(statement) > 10:  # Skip very short statements
                        try:
                            cur.execute(statement)
                            success_count += 1
                            logger.debug(f"✅ Statement {i+1}: SUCCESS")
                        except psycopg2.Error as e:
                            logger.debug(f"❌ Statement {i+1}: {e}")
                
                logger.info(f"📊 Fallback execution: {success_count} statements executed")
                
                if success_count == 0:
                    raise Exception("No statements executed successfully")
                    
            conn.close()
            logger.info("✅ SQL file executed successfully (fallback)")
            
        except Exception as fallback_error:
            logger.error(f"❌ Both Docker and fallback execution failed")
            raise RuntimeError(f"All execution methods failed. Docker: {docker_error}, Fallback: {fallback_error}")


def verify_chinook_setup():
    """Verify that the Chinook database was set up correctly."""
    conn_params = get_connection_params()

    try:
        conn = psycopg2.connect(**conn_params)

        with conn.cursor() as cur:
            # Check for expected tables
            expected_tables = [
                '"Artist"', '"Album"', '"Track"', '"Customer"',
                '"Employee"', '"Invoice"', '"InvoiceLine"', '"Genre"', '"MediaType"'
            ]

            table_counts = {}
            for table in expected_tables:
                cur.execute(f'SELECT COUNT(*) FROM {table}')
                count = cur.fetchone()[0]
                table_counts[table] = count
                logger.info(f"✅ Table {table}: {count} records")

        conn.close()
        logger.info("🎉 Chinook database verification completed")
        return table_counts

    except psycopg2.Error as e:
        logger.error(f"❌ Verification failed: {e}")
        raise


def prepare_chinook_environment():
    """Main function to prepare the Chinook database environment."""
    logger.info("🔧 Preparing Chinook database environment...")

    sql_file_path = None
    try:
        # Download the Chinook SQL script
        sql_file_path = download_chinook_sql()

        # Execute the SQL script
        execute_sql_file(sql_file_path)

        # Verify the setup
        table_counts = verify_chinook_setup()

        logger.info("🎉 Chinook database environment prepared successfully!")
        logger.info(f"📊 Total tables created: {len(table_counts)}")

        return table_counts

    except Exception as e:
        logger.error(f"❌ Failed to prepare Chinook environment: {e}")
        raise

    finally:
        # Clean up temporary file
        if sql_file_path and os.path.exists(sql_file_path):
            try:
                os.unlink(sql_file_path)
                logger.debug(f"🧹 Cleaned up temporary file: {sql_file_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file: {e}")


if __name__ == "__main__":
    # Allow running this module directly for testing
    logging.basicConfig(level=logging.INFO)
    prepare_chinook_environment()
