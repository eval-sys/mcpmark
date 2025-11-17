"""
Verification script for Vector Database DBA Analysis task.

This script verifies that the candidate has properly analyzed the vector database
and stored their findings in appropriate result tables.
"""

import logging
import psycopg2
import os
import sys
from typing import Dict, Any

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


def verify_vector_analysis_columns(conn) -> Dict[str, Any]:
    """Verify the vector_analysis_columns table exists, has correct columns, and contains actual vector columns from the database."""
    results = {'passed': False, 'issues': []}
    expected_columns = [
        'schema', 'table_name', 'column_name', 'dimensions', 'data_type', 'has_constraints', 'rows'
    ]
    try:
        with conn.cursor() as cur:
            # Check if table exists
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'vector_analysis_columns'
                );
            """)
            if not cur.fetchone()[0]:
                results['issues'].append("vector_analysis_columns table not found")
                return results

            # Check columns
            cur.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'vector_analysis_columns'
                ORDER BY column_name;
            """)
            actual_columns = {row[0] for row in cur.fetchall()}
            missing = set(expected_columns) - actual_columns
            extra = actual_columns - set(expected_columns)
            if missing:
                results['issues'].append(f"Missing columns: {missing}")
            if extra:
                results['issues'].append(f"Unexpected columns: {extra}")

            # Check for data
            cur.execute("SELECT COUNT(*) FROM vector_analysis_columns;")
            count = cur.fetchone()[0]
            if count == 0:
                results['issues'].append("No rows found in vector_analysis_columns")
                return results

            # Get actual vector columns from the database
            cur.execute("""
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE data_type = 'USER-DEFINED'
                AND udt_name = 'vector'
                ORDER BY table_name, column_name;
            """)
            actual_vector_columns = set(cur.fetchall())

            # Get what the agent found
            cur.execute("""
                SELECT table_name, column_name
                FROM vector_analysis_columns
                ORDER BY table_name, column_name;
            """)
            found_vector_columns = set(cur.fetchall())

            # Check if agent found the actual vector columns
            missing_vectors = actual_vector_columns - found_vector_columns
            extra_vectors = found_vector_columns - actual_vector_columns

            if missing_vectors:
                results['issues'].append(f"Missing: {missing_vectors}")
            if extra_vectors:
                results['issues'].append(f"Non-existing: {extra_vectors}")

            if not missing and not extra and count > 0 and not missing_vectors and not extra_vectors:
                results['passed'] = True

    except psycopg2.Error as e:
        results['issues'].append(f"Database error: {e}")
    except Exception as e:
        results['issues'].append(f"Verification error: {e}")
    return results


def verify_vector_analysis_storage_consumption(conn) -> Dict[str, Any]:
    """Verify the vector_analysis_storage_consumption table exists, has correct columns, and analyzes actual vector tables."""
    results = {'passed': False, 'issues': []}
    expected_columns = [
        'schema', 'table_name', 'total_size_bytes', 'vector_data_bytes', 'regular_data_bytes', 'vector_storage_pct', 'row_count'
    ]
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'vector_analysis_storage_consumption'
                );
            """)
            if not cur.fetchone()[0]:
                results['issues'].append("vector_analysis_storage_consumption table not found")
                return results

            cur.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'vector_analysis_storage_consumption'
                ORDER BY column_name;
            """)
            actual_columns = {row[0] for row in cur.fetchall()}
            missing = set(expected_columns) - actual_columns
            extra = actual_columns - set(expected_columns)
            if missing:
                results['issues'].append(f"Missing columns: {missing}")
            if extra:
                results['issues'].append(f"Unexpected columns: {extra}")

            cur.execute("SELECT COUNT(*) FROM vector_analysis_storage_consumption;")
            count = cur.fetchone()[0]
            if count == 0:
                results['issues'].append("No rows found in vector_analysis_storage_consumption")
                return results

            # Get actual tables with vector columns
            cur.execute("""
                SELECT DISTINCT table_name
                FROM information_schema.columns
                WHERE data_type = 'USER-DEFINED'
                AND udt_name = 'vector'
                ORDER BY table_name;
            """)
            actual_vector_tables = {row[0] for row in cur.fetchall()}

            # Get what the agent analyzed
            cur.execute("""
                SELECT DISTINCT table_name
                FROM vector_analysis_storage_consumption
                ORDER BY table_name;
            """)
            analyzed_tables = {row[0] for row in cur.fetchall()}

            # Check if agent analyzed the actual vector tables
            missing_tables = actual_vector_tables - analyzed_tables
            if missing_tables:
                results['issues'].append(f"Agent missed analyzing vector tables: {missing_tables}")

            # Check that analyzed tables actually have vector columns
            extra_tables = analyzed_tables - actual_vector_tables
            if extra_tables:
                results['issues'].append(f"Agent analyzed non-vector tables: {extra_tables}")

            if not missing and not extra and count > 0 and not missing_tables and not extra_tables:
                results['passed'] = True

    except psycopg2.Error as e:
        results['issues'].append(f"Database error: {e}")
    except Exception as e:
        results['issues'].append(f"Verification error: {e}")
    return results


def verify_vector_analysis_indices(conn) -> Dict[str, Any]:
    """Verify the vector_analysis_indices table exists, has correct columns, and identifies actual vector indexes."""
    results = {'passed': False, 'issues': []}
    expected_columns = [
        'schema', 'table_name', 'column_name', 'index_name', 'index_type', 'index_size_bytes'
    ]
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'vector_analysis_indices'
                );
            """)
            if not cur.fetchone()[0]:
                results['issues'].append("vector_analysis_indices table not found")
                return results

            cur.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'vector_analysis_indices'
                ORDER BY column_name;
            """)
            actual_columns = {row[0] for row in cur.fetchall()}
            missing = set(expected_columns) - actual_columns
            extra = actual_columns - set(expected_columns)
            if missing:
                results['issues'].append(f"Missing columns: {missing}")
            if extra:
                results['issues'].append(f"Unexpected columns: {extra}")

            cur.execute("SELECT COUNT(*) FROM vector_analysis_indices;")
            count = cur.fetchone()[0]
            if count == 0:
                results['issues'].append("No rows found in vector_analysis_indices")
                return results

            # Get actual vector indexes from the database (exclude ground truth table indexes)
            cur.execute("""
                SELECT schemaname, tablename, indexname
                FROM pg_indexes
                WHERE (indexdef ILIKE '%hnsw%' OR indexdef ILIKE '%ivfflat%')
                AND tablename NOT LIKE '%analysis%'
                ORDER BY tablename, indexname;
            """)
            actual_vector_indexes = set(cur.fetchall())

            # Get what the agent found
            cur.execute("""
                SELECT schema, table_name, index_name
                FROM vector_analysis_indices
                ORDER BY table_name, index_name;
            """)
            found_indexes = set(cur.fetchall())

            # Check if agent found the actual vector indexes
            missing_indexes = actual_vector_indexes - found_indexes
            if missing_indexes:
                results['issues'].append(f"Agent missed vector indexes: {missing_indexes}")

            # Allow agent to find more indexes than just vector ones (they might include related indexes)
            # but at least they should find the vector-specific ones

            if not missing and not extra and count > 0 and not missing_indexes:
                results['passed'] = True

    except psycopg2.Error as e:
        results['issues'].append(f"Database error: {e}")
    except Exception as e:
        results['issues'].append(f"Verification error: {e}")
    return results


def verify_no_extra_analysis_tables(conn) -> Dict[str, Any]:
    """Check that only the required analysis tables exist (no legacy/extra analysis tables)."""
    results = {'passed': True, 'issues': []}  # Start with passed=True, more lenient
    required = {
        'vector_analysis_columns',
        'vector_analysis_storage_consumption',
        'vector_analysis_indices',
    }
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name LIKE 'vector_analysis_%';
            """)
            analysis_tables = {row[0] for row in cur.fetchall()}

            # Only flag as issue if there are analysis tables that don't match our required set
            # Exclude ground truth tables from this check
            analysis_tables_filtered = {t for t in analysis_tables if not t.startswith('expected_') and not t.startswith('vector_analysis_results')}
            extra = analysis_tables_filtered - required
            if extra:
                results['issues'].append(f"Found unexpected analysis tables: {extra}")
                results['passed'] = False

    except Exception as e:
        results['issues'].append(f"Verification error: {e}")
        results['passed'] = False
    return results



def main():
    """Main verification function for vector analysis deliverables."""

    conn_params = get_connection_params()
    if not conn_params["database"]:
        print("No database specified")
        sys.exit(1)
    try:
        conn = psycopg2.connect(**conn_params)
        checks = [
            ("vector_analysis_columns", verify_vector_analysis_columns),
            ("vector_analysis_storage_consumption", verify_vector_analysis_storage_consumption),
            ("vector_analysis_indices", verify_vector_analysis_indices),
            ("no_extra_analysis_tables", verify_no_extra_analysis_tables),
        ]
        passed_checks = 0
        all_issues = []
        for i, (desc, check_func) in enumerate(checks, 1):
            result = check_func(conn)
            if result['passed']:
                print(f"  PASSED")
                passed_checks += 1
            else:
                print(f"  FAILED")
                for issue in result['issues']:
                    print(f"    - {issue}")
                all_issues.extend(result['issues'])
            print()
        conn.close()
        total_checks = len(checks)
        print(f"Results: {passed_checks}/{total_checks} checks passed")
        if passed_checks == total_checks:
            sys.exit(0)
        elif passed_checks >= total_checks * 0.75:
            sys.exit(0)
        else:
            sys.exit(1)
    except psycopg2.Error as e:
        print(f"Database connection error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Verification error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
