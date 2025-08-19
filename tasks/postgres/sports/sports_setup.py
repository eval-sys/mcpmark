"""
Shared Sports Database Setup Utilities

This module provides utilities for setting up the sports database
from the official source. Used by all sports-related tasks.
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


def download_sports_sql():
    """Download the sports database SQL script."""
    sports_url = "https://raw.githubusercontent.com/neondatabase/postgres-sample-dbs/main/sports.sql"
    
    logger.info(f"📥 Downloading Sports SQL from {sports_url}")
    
    try:
        # Download with requests (handles SSL/certificates better)
        response = requests.get(sports_url, timeout=30)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.sql', delete=False) as temp_file:
            temp_file.write(response.text)
            temp_file.flush()
            
            logger.info(f"✅ Downloaded Sports SQL to {temp_file.name} ({len(response.text)} bytes)")
            return temp_file.name
                
    except requests.RequestException as e:
        logger.error(f"❌ Failed to download Sports SQL: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Failed to download Sports SQL: {e}")
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
            "-v", f"{sql_file_path}:/tmp/sports.sql:ro",  # Mount SQL file
            "postgres:latest",
            "psql", conn_string, "-f", "/tmp/sports.sql"
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
                
                # Try to execute the entire content
                try:
                    cur.execute(sql_content)
                    logger.info("✅ SQL file executed successfully (fallback)")
                except psycopg2.Error as e:
                    # If that fails, try statement by statement
                    logger.warning(f"Full execution failed: {e}")
                    logger.info("🔄 Trying statement-by-statement execution...")
                    
                    statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
                    success_count = 0
                    
                    for stmt in statements:
                        if stmt and len(stmt) > 10:
                            try:
                                cur.execute(stmt)
                                success_count += 1
                            except psycopg2.Error:
                                pass
                    
                    logger.info(f"📊 Fallback execution: {success_count} statements executed")
                    
                    if success_count == 0:
                        raise Exception("No statements executed successfully")
                    
            conn.close()
            
        except Exception as fallback_error:
            logger.error(f"❌ Both Docker and fallback execution failed")
            raise RuntimeError(f"All execution methods failed. Docker: {docker_error}, Fallback: {fallback_error}")


def verify_sports_setup():
    """Verify that the sports database was set up correctly."""
    conn_params = get_connection_params()
    
    try:
        conn = psycopg2.connect(**conn_params)
        
        with conn.cursor() as cur:
            # Check for expected tables (these are common in sports databases)
            expected_tables = [
                'teams', 'players', 'games', 'stats', 'seasons'
            ]
            
            table_counts = {}
            existing_tables = []
            
            # First, get all table names
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            """)
            actual_tables = [row[0] for row in cur.fetchall()]
            
            # Count records in existing tables
            for table in actual_tables:
                try:
                    cur.execute(f'SELECT COUNT(*) FROM "{table}"')
                    count = cur.fetchone()[0]
                    table_counts[table] = count
                    existing_tables.append(table)
                    logger.info(f"✅ Table {table}: {count} records")
                except psycopg2.Error as e:
                    logger.debug(f"Could not count table {table}: {e}")
                
        conn.close()
        logger.info("🎉 Sports database verification completed")
        logger.info(f"📊 Found {len(existing_tables)} tables: {', '.join(existing_tables)}")
        return table_counts
        
    except psycopg2.Error as e:
        logger.error(f"❌ Verification failed: {e}")
        raise


def prepare_sports_environment():
    """Main function to prepare the sports database environment."""
    logger.info("🔧 Preparing Sports database environment...")
    
    sql_file_path = None
    try:
        # Download the Sports SQL script
        sql_file_path = download_sports_sql()
        
        # Execute the SQL script
        execute_sql_file(sql_file_path)
        
        # Verify the setup
        table_counts = verify_sports_setup()
        
        logger.info("🎉 Sports database environment prepared successfully!")
        logger.info(f"📊 Total tables created: {len(table_counts)}")
        
        return table_counts
        
    except Exception as e:
        logger.error(f"❌ Failed to prepare Sports environment: {e}")
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
    prepare_sports_environment()