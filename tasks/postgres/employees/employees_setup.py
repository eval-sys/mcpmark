"""
Shared Employees Database Setup Utilities

This module provides utilities for setting up the employees database
from the official source. Used by all employees-related tasks.
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


def download_employees_backup():
    """Download the employees database backup file."""
    employees_url = "https://raw.githubusercontent.com/neondatabase/postgres-sample-dbs/main/employees.sql.gz"
    
    logger.info(f"📥 Downloading Employees backup from {employees_url}")
    
    try:
        # Download with requests (handles SSL/certificates better)
        response = requests.get(employees_url, timeout=60)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        # Create a temporary file for the compressed backup
        with tempfile.NamedTemporaryFile(suffix='.sql.gz', delete=False) as temp_file:
            temp_file.write(response.content)
            temp_file.flush()
            
            logger.info(f"✅ Downloaded Employees backup to {temp_file.name} ({len(response.content)} bytes)")
            return temp_file.name
                
    except requests.RequestException as e:
        logger.error(f"❌ Failed to download Employees backup: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Failed to download Employees backup: {e}")
        raise


def execute_backup_with_docker(backup_file_path):
    """Restore the employees database using Docker with pg_restore."""
    conn_params = get_connection_params()
    
    if not conn_params["database"]:
        raise ValueError("❌ No database specified in POSTGRES_DATABASE environment variable")
    
    logger.info(f"🗃️ Restoring backup with Docker pg_restore: {backup_file_path}")
    
    try:
        # Build the connection string for pg_restore
        conn_string = f"postgresql://{conn_params['user']}:{conn_params['password']}@{conn_params['host']}:{conn_params['port']}/{conn_params['database']}"
        
        # Docker command to run pg_restore
        docker_cmd = [
            "docker", "run", "--rm",
            "--network", "host",  # Use host network to access localhost PostgreSQL
            "-v", f"{backup_file_path}:/tmp/employees.sql.gz:ro",  # Mount backup file
            "postgres:latest",
            "pg_restore", "-d", conn_string, "-Fc", "/tmp/employees.sql.gz", 
            "-c", "-v", "--no-owner", "--no-privileges"
        ]
        
        logger.info("🐳 Running pg_restore in Docker container...")
        result = subprocess.run(
            docker_cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout for large restore
        )
        
        if result.returncode == 0:
            logger.info("✅ Backup restored successfully with Docker pg_restore")
            if result.stdout.strip():
                logger.debug(f"pg_restore output: {result.stdout}")
        else:
            logger.error(f"❌ Docker pg_restore failed with exit code {result.returncode}")
            logger.error(f"Error output: {result.stderr}")
            raise RuntimeError(f"Docker pg_restore execution failed")
            
    except subprocess.TimeoutExpired:
        logger.error("❌ Docker pg_restore execution timed out")
        raise RuntimeError("Docker pg_restore execution timed out")
    except Exception as e:
        logger.error(f"❌ Error executing backup with Docker: {e}")
        raise


def execute_backup(backup_file_path):
    """Execute the backup file against the database."""
    try:
        # Try Docker approach first (most reliable for compressed backups)
        execute_backup_with_docker(backup_file_path)
    except Exception as docker_error:
        logger.warning(f"❌ Docker execution failed: {docker_error}")
        logger.info("🔄 Falling back to manual extraction and execution...")
        
        # Fallback: try to decompress and execute manually
        try:
            import gzip
            
            # Decompress the file
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.sql', delete=False) as temp_sql:
                with gzip.open(backup_file_path, 'rt', encoding='utf-8') as gz_file:
                    temp_sql.write(gz_file.read())
                    temp_sql.flush()
                
                # Now try to execute the SQL
                conn_params = get_connection_params()
                conn = psycopg2.connect(**conn_params)
                conn.autocommit = True
                
                with conn.cursor() as cur:
                    with open(temp_sql.name, 'r', encoding='utf-8') as f:
                        sql_content = f.read()
                    
                    # Try to execute the entire content
                    try:
                        cur.execute(sql_content)
                        logger.info("✅ Backup executed successfully (fallback)")
                    except psycopg2.Error as e:
                        logger.error(f"❌ Fallback execution failed: {e}")
                        raise
                
                conn.close()
                os.unlink(temp_sql.name)  # Clean up decompressed file
                
        except Exception as fallback_error:
            logger.error(f"❌ Both Docker and fallback execution failed")
            raise RuntimeError(f"All execution methods failed. Docker: {docker_error}, Fallback: {fallback_error}")


def verify_employees_setup():
    """Verify that the employees database was set up correctly."""
    conn_params = get_connection_params()
    
    try:
        conn = psycopg2.connect(**conn_params)
        
        with conn.cursor() as cur:
            # Check for expected tables in employees schema
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'employees' AND table_type = 'BASE TABLE'
            """)
            employees_tables = [row[0] for row in cur.fetchall()]
            
            # Also check public schema
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            """)
            public_tables = [row[0] for row in cur.fetchall()]
            
            table_counts = {}
            all_tables = employees_tables + public_tables
            
            # Count records in all tables
            for table in all_tables:
                try:
                    schema = 'employees' if table in employees_tables else 'public'
                    cur.execute(f'SELECT COUNT(*) FROM "{schema}"."{table}"')
                    count = cur.fetchone()[0]
                    table_counts[f"{schema}.{table}"] = count
                    logger.info(f"✅ Table {schema}.{table}: {count} records")
                except psycopg2.Error as e:
                    logger.debug(f"Could not count table {schema}.{table}: {e}")
                
        conn.close()
        logger.info("🎉 Employees database verification completed")
        logger.info(f"📊 Found {len(table_counts)} tables")
        return table_counts
        
    except psycopg2.Error as e:
        logger.error(f"❌ Verification failed: {e}")
        raise


def prepare_employees_environment():
    """Main function to prepare the employees database environment."""
    logger.info("🔧 Preparing Employees database environment...")
    
    backup_file_path = None
    try:
        # Download the Employees backup
        backup_file_path = download_employees_backup()
        
        # Execute the backup
        execute_backup(backup_file_path)
        
        # Verify the setup
        table_counts = verify_employees_setup()
        
        logger.info("🎉 Employees database environment prepared successfully!")
        logger.info(f"📊 Total tables created: {len(table_counts)}")
        
        return table_counts
        
    except Exception as e:
        logger.error(f"❌ Failed to prepare Employees environment: {e}")
        raise
        
    finally:
        # Clean up temporary file
        if backup_file_path and os.path.exists(backup_file_path):
            try:
                os.unlink(backup_file_path)
                logger.debug(f"🧹 Cleaned up temporary file: {backup_file_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file: {e}")


if __name__ == "__main__":
    # Allow running this module directly for testing
    logging.basicConfig(level=logging.INFO)
    prepare_employees_environment()