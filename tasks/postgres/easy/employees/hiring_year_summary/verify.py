"""
Verification script for PostgreSQL Task 3: Employee Demographics Report
"""

import os
import sys
import psycopg2
from decimal import Decimal

def rows_match(actual_row, expected_row):
    """
    Compare two rows with appropriate tolerance.
    For Decimal types: allows 0.1 tolerance
    For other types: requires exact match
    """
    if len(actual_row) != len(expected_row):
        return False
    
    for actual, expected in zip(actual_row, expected_row):
        if isinstance(actual, Decimal) and isinstance(expected, Decimal):
            if abs(float(actual) - float(expected)) > 0.1:
                return False
        elif actual != expected:
            return False
    
    return True

def get_connection_params() -> dict:
    """Get database connection parameters."""
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", 5432)),
        "database": os.getenv("POSTGRES_DATABASE"),
        "user": os.getenv("POSTGRES_USERNAME"),
        "password": os.getenv("POSTGRES_PASSWORD")
    }

def verify_hiring_year_results(conn) -> bool:
    """Verify the hiring year summary results."""
    with conn.cursor() as cur:
        # Get actual results from the created table
        cur.execute("""
            SELECT hire_year, employees_hired, still_employed, retention_rate
            FROM employees.hiring_year_summary
            ORDER BY hire_year
        """)
        actual_results = cur.fetchall()
        
        # Execute ground truth query
        cur.execute("""
            WITH current_emp AS (
            SELECT DISTINCT s.employee_id
            FROM employees.salary s
            WHERE s.to_date = DATE '9999-01-01'
            ),
            base AS (
            SELECT e.id, EXTRACT(YEAR FROM e.hire_date)::INT AS hire_year
            FROM employees.employee e
            WHERE e.hire_date IS NOT NULL
            )
            SELECT
            b.hire_year,
            COUNT(*)::INT AS employees_hired,
            COUNT(*) FILTER (WHERE ce.employee_id IS NOT NULL)::INT AS still_employed,
            (COUNT(*) FILTER (WHERE ce.employee_id IS NOT NULL))::DECIMAL
                / NULLIF(COUNT(*), 0) * 100 AS retention_rate
            FROM base b
            LEFT JOIN current_emp ce ON ce.employee_id = b.id
            GROUP BY b.hire_year
            ORDER BY b.hire_year;
        """)
        expected_results = cur.fetchall()

        if len(actual_results) != len(expected_results):
            print(f"❌ Expected {len(expected_results)} hiring year results, got {len(actual_results)}")
            return False

        mismatches = 0
        for i, (actual, expected) in enumerate(zip(actual_results, expected_results)):
            if not rows_match(actual, expected):
                if mismatches < 5:  # Only show first 5 mismatches
                    print(f"❌ Row {i+1} mismatch: expected {expected}, got {actual}")
                mismatches += 1

        if mismatches > 0:
            print(f"❌ Total mismatches: {mismatches}")
            return False

        print(f"✅ Hiring year summary results are correct ({len(actual_results)} records)")
        return True

def main():
    """Main verification function."""
    print("=" * 50)

    # Get connection parameters
    conn_params = get_connection_params()

    if not conn_params["database"]:
        print("❌ No database specified")
        sys.exit(1)

    try:
        # Connect to database
        conn = psycopg2.connect(**conn_params)

        # Verify all four analysis results
        success = verify_hiring_year_results(conn)

        conn.close()

        if success:
            print("\n🎉 Task verification: PASS")
            sys.exit(0)
        else:
            print("\n❌ Task verification: FAIL")
            sys.exit(1)

    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Verification error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()