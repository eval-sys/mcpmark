"""
PostgreSQL Data Loading Utilities for MCPMark Tasks
===================================================

Common utilities for loading data into PostgreSQL databases from CSV files
and setting up schemas in prepare_environment.py scripts.
"""

import csv
import os
import psycopg2
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


def get_connection_params() -> dict:
    """Get database connection parameters from environment variables."""
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", 5432)),
        "database": os.getenv("POSTGRES_DATABASE"),
        "user": os.getenv("POSTGRES_USERNAME"),
        "password": os.getenv("POSTGRES_PASSWORD"),
    }


def execute_schema_sql(conn, schema_sql: str):
    """Execute schema SQL with proper error handling."""
    with conn.cursor() as cur:
        cur.execute(schema_sql)
        conn.commit()
        logger.info("✅ Database schema created successfully")


def load_csv_to_table(
    conn, 
    csv_file_path: Path, 
    table_name: str, 
    columns: Optional[List[str]] = None,
    skip_header: bool = True
):
    """
    Load CSV data into a PostgreSQL table.
    
    Args:
        conn: Database connection
        csv_file_path: Path to CSV file
        table_name: Target table name
        columns: List of column names (if None, uses all columns)
        skip_header: Whether to skip the first row
    """
    if not csv_file_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_file_path}")
    
    with conn.cursor() as cur:
        with open(csv_file_path, 'r', encoding='utf-8') as f:
            csv_reader = csv.reader(f)
            
            # Skip header if needed
            if skip_header:
                next(csv_reader)
            
            # Build COPY command
            if columns:
                copy_sql = f"COPY {table_name} ({', '.join(columns)}) FROM STDIN WITH CSV"
            else:
                copy_sql = f"COPY {table_name} FROM STDIN WITH CSV"
            
            # Reset file pointer and copy data
            f.seek(0)
            if skip_header:
                next(csv.reader(f))  # Skip header again
            
            cur.copy_expert(copy_sql, f)
            
        conn.commit()
        logger.info(f"✅ Loaded data from {csv_file_path.name} into {table_name}")


def insert_data_from_dict(conn, table_name: str, data: List[Dict[str, Any]]):
    """
    Insert data from a list of dictionaries into a table.
    
    Args:
        conn: Database connection
        table_name: Target table name
        data: List of dictionaries with column_name: value pairs
    """
    if not data:
        return
    
    # Get column names from first record
    columns = list(data[0].keys())
    placeholders = ', '.join(['%s'] * len(columns))
    columns_str = ', '.join(columns)
    
    insert_sql = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
    
    with conn.cursor() as cur:
        for row in data:
            values = [row[col] for col in columns]
            cur.execute(insert_sql, values)
        
        conn.commit()
        logger.info(f"✅ Inserted {len(data)} rows into {table_name}")


def create_table_with_data(
    conn, 
    table_name: str, 
    schema_sql: str, 
    data: Optional[List[Dict[str, Any]]] = None,
    data_from_csv: Optional[Path] = None
):
    """
    Create a table and optionally load data.
    
    Args:
        conn: Database connection
        table_name: Table name
        schema_sql: CREATE TABLE SQL statement
        data: Optional list of dictionaries to insert
        data_from_csv: Optional CSV file to load
    """
    with conn.cursor() as cur:
        # Create table
        cur.execute(schema_sql)
        logger.info(f"✅ Created table {table_name}")
        
        # Load data if provided
        if data:
            insert_data_from_dict(conn, table_name, data)
        elif data_from_csv:
            load_csv_to_table(conn, data_from_csv, table_name)


def setup_database_with_config(setup_config: Dict[str, Any]):
    """
    Set up database using a configuration dictionary.
    
    Args:
        setup_config: Dictionary with 'tables' key containing table configurations
        
    Example config:
    {
        "tables": {
            "artists": {
                "schema": "CREATE TABLE artists (id SERIAL PRIMARY KEY, name VARCHAR(120))",
                "data": [{"id": 1, "name": "Iron Maiden"}],
                "data_from_csv": "data/artists.csv"  # alternative to data
            }
        }
    }
    """
    conn_params = get_connection_params()
    if not conn_params["database"]:
        raise ValueError("❌ No database specified in POSTGRES_DATABASE environment variable")
    
    try:
        conn = psycopg2.connect(**conn_params)
        
        for table_name, config in setup_config["tables"].items():
            schema_sql = config["schema"]
            data = config.get("data")
            csv_file_path = None
            
            # Handle CSV file path
            if "data_from_csv" in config:
                csv_file_path = Path(config["data_from_csv"])
                if not csv_file_path.is_absolute():
                    # Assume relative to current working directory (task directory)
                    csv_file_path = Path.cwd() / csv_file_path
            
            create_table_with_data(
                conn, 
                table_name, 
                schema_sql, 
                data=data, 
                data_from_csv=csv_file_path
            )
        
        conn.close()
        logger.info("🎉 Database setup completed successfully")
        
    except psycopg2.Error as e:
        logger.error(f"❌ Database error during setup: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Setup error: {e}")
        raise