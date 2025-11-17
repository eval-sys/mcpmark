"""
Verification script for PostgreSQL LEGO Task 4: Database Security and RLS Implementation
(Version 2 - Improved Robustness)
"""

import os
import sys
import psycopg2
import psycopg2.errors
from typing import Dict

def get_connection_params() -> Dict[str, any]:
    """Get database connection parameters from environment variables."""
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", 5432)),
        "database": os.getenv("POSTGRES_DATABASE"),
        "user": os.getenv("POSTGRES_USERNAME"),
        "password": os.getenv("POSTGRES_PASSWORD"),
    }

def verify_role_creation(conn) -> bool:
    """
    TASK 1 VERIFICATION: Check if theme_analyst role was created with proper permissions.
    """
    print("\n-- Verifying Task 1: Role Creation and Permissions --")
    with conn.cursor() as cur:
        # Check if role exists
        cur.execute("SELECT 1 FROM pg_roles WHERE rolname = 'theme_analyst';")
        if not cur.fetchone():
            print("❌ FAIL: The 'theme_analyst' role was not created.")
            return False
        print("✅ OK: Role 'theme_analyst' exists.")

        # Check SELECT permissions on reference and main tables
        all_tables = [
            'lego_themes', 'lego_colors', 'lego_parts', 'lego_part_categories',
            'lego_sets', 'lego_inventories', 'lego_inventory_parts'
        ]
        for table in all_tables:
            cur.execute(
                """
                SELECT has_table_privilege('theme_analyst', %s, 'SELECT');
                """,
                (table,)
            )
            if not cur.fetchone()[0]:
                print(f"❌ FAIL: 'theme_analyst' role is missing SELECT permission on '{table}'.")
                return False
        print("✅ OK: Role has correct SELECT permissions on all required tables.")

        # Check that no INSERT/UPDATE/DELETE permissions exist
        for table in all_tables:
            cur.execute(
                """
                SELECT 
                    has_table_privilege('theme_analyst', %s, 'INSERT') OR
                    has_table_privilege('theme_analyst', %s, 'UPDATE') OR
                    has_table_privilege('theme_analyst', %s, 'DELETE');
                """,
                (table, table, table)
            )
            if cur.fetchone()[0]:
                print(f"❌ FAIL: 'theme_analyst' role has unauthorized INSERT, UPDATE, or DELETE permission on '{table}'.")
                return False
        print("✅ OK: Role does not have modification permissions.")
        
        print("✅ PASS: 'theme_analyst' role created with correct permissions.")
        return True

def verify_rls_enabled(conn) -> bool:
    """
    TASK 2 VERIFICATION: Check if Row-Level Security is enabled on required tables.
    """
    print("\n-- Verifying Task 2: Row-Level Security Enablement --")
    tables_to_check = ['lego_sets', 'lego_inventories', 'lego_inventory_parts']
    with conn.cursor() as cur:
        for table in tables_to_check:
            cur.execute(
                "SELECT relrowsecurity FROM pg_class WHERE relname = %s;", (table,)
            )
            rls_enabled = cur.fetchone()
            if not rls_enabled or not rls_enabled[0]:
                print(f"❌ FAIL: RLS is not enabled on table '{table}'.")
                return False
            print(f"✅ OK: RLS is enabled on table '{table}'.")
    
    print("✅ PASS: Row-Level Security is enabled on all required tables.")
    return True

def main():
    """Main verification function."""
    print("=" * 60)
    print("LEGO Database Security and RLS Verification Script")
    print("=" * 60)

    conn_params = get_connection_params()
    if not conn_params.get("database"):
        print("❌ CRITICAL: POSTGRES_DATABASE environment variable not set.")
        sys.exit(1)

    conn = None
    try:
        conn = psycopg2.connect(**conn_params)
        
        results = [
            verify_role_creation(conn),
            verify_rls_enabled(conn),
        ]

        if all(results):
            print("\n🎉 Overall Result: PASS - All security tasks verified successfully!")
            sys.exit(0)
        else:
            print("\n❌ Overall Result: FAIL - One or more verification steps failed.")
            sys.exit(1)

    except psycopg2.OperationalError as e:
        print(f"❌ CRITICAL: Could not connect to the database. Check credentials and host. Details: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ CRITICAL: An unexpected error occurred. Details: {e}")
        sys.exit(1)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()
