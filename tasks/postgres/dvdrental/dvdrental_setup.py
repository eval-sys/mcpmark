"""
Shared DVD Rental Database Setup Utilities

This module provides utilities for setting up the DVD rental database
from the official source. Used by all dvdrental-related tasks.
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


def download_dvdrental_backup():
    """Download the DVD rental database backup file."""
    dvdrental_url = "https://github.com/robconery/dvdrental/raw/refs/heads/master/dvdrental.tar"
    
    logger.info(f"📥 Downloading DVD Rental backup from {dvdrental_url}")
    
    try:
        # Download with requests (handles SSL/certificates better)
        response = requests.get(dvdrental_url, timeout=60)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        # Create a temporary file for the tar backup
        with tempfile.NamedTemporaryFile(suffix='.tar', delete=False) as temp_file:
            temp_file.write(response.content)
            temp_file.flush()
            
            logger.info(f"✅ Downloaded DVD Rental backup to {temp_file.name} ({len(response.content)} bytes)")
            return temp_file.name
                
    except requests.RequestException as e:
        logger.error(f"❌ Failed to download DVD Rental backup: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Failed to download DVD Rental backup: {e}")
        raise


def execute_backup_with_docker(backup_file_path):
    """Restore the DVD rental database using Docker with pg_restore."""
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
            "-v", f"{backup_file_path}:/tmp/dvdrental.tar:ro",  # Mount backup file
            "postgres:latest",
            "pg_restore", "-d", conn_string, "/tmp/dvdrental.tar", 
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


def post_restore_cleanup():
    """Perform post-restore cleanup as mentioned in the README."""
    conn_params = get_connection_params()
    
    try:
        conn = psycopg2.connect(**conn_params)
        conn.autocommit = True
        
        with conn.cursor() as cur:
            # Drop the problematic index as mentioned in the README
            try:
                cur.execute("DROP INDEX IF EXISTS idx_fk_customer_id;")
                logger.info("✅ Dropped idx_fk_customer_id index as recommended")
            except psycopg2.Error as e:
                logger.debug(f"Index drop failed (might not exist): {e}")
        
        conn.close()
        
    except psycopg2.Error as e:
        logger.warning(f"⚠️ Post-restore cleanup failed: {e}")


def execute_backup(backup_file_path):
    """Execute the backup file against the database."""
    try:
        # Try Docker approach first (most reliable for tar backups)
        execute_backup_with_docker(backup_file_path)
        
        # Perform post-restore cleanup
        post_restore_cleanup()
        
    except Exception as docker_error:
        logger.warning(f"❌ Docker execution failed: {docker_error}")
        logger.error(f"❌ DVD Rental backup restore failed")
        raise RuntimeError(f"DVD Rental backup restore failed: {docker_error}")


def verify_dvdrental_setup():
    """Verify that the DVD rental database was set up correctly."""
    conn_params = get_connection_params()
    
    try:
        conn = psycopg2.connect(**conn_params)
        
        with conn.cursor() as cur:
            # Check for expected DVD rental tables
            expected_tables = [
                'actor', 'address', 'category', 'city', 'country', 'customer',
                'film', 'film_actor', 'film_category', 'inventory', 'language',
                'payment', 'rental', 'staff', 'store'
            ]
            
            # Get all table names
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            """)
            actual_tables = [row[0] for row in cur.fetchall()]
            
            table_counts = {}
            
            # Count records in all tables
            for table in actual_tables:
                try:
                    cur.execute(f'SELECT COUNT(*) FROM "{table}"')
                    count = cur.fetchone()[0]
                    table_counts[table] = count
                    logger.info(f"✅ Table {table}: {count} records")
                except psycopg2.Error as e:
                    logger.debug(f"Could not count table {table}: {e}")
            
            # Check if we have the expected core tables
            missing_tables = [t for t in expected_tables if t not in actual_tables]
            if missing_tables:
                logger.warning(f"⚠️ Missing expected tables: {missing_tables}")
            else:
                logger.info("✅ All expected DVD rental tables found")
                
        conn.close()
        logger.info("🎉 DVD Rental database verification completed")
        logger.info(f"📊 Found {len(table_counts)} tables")
        return table_counts
        
    except psycopg2.Error as e:
        logger.error(f"❌ Verification failed: {e}")
        raise


def prepare_dvdrental_environment():
    """Main function to prepare the DVD rental database environment."""
    logger.info("🔧 Preparing DVD Rental database environment...")
    
    backup_file_path = None
    try:
        # Download the DVD Rental backup
        backup_file_path = download_dvdrental_backup()
        
        # Execute the backup
        execute_backup(backup_file_path)
        
        # Verify the setup
        table_counts = verify_dvdrental_setup()
        
        logger.info("🎉 DVD Rental database environment prepared successfully!")
        logger.info(f"📊 Total tables created: {len(table_counts)}")
        
        return table_counts
        
    except Exception as e:
        logger.error(f"❌ Failed to prepare DVD Rental environment: {e}")
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
    prepare_dvdrental_environment()