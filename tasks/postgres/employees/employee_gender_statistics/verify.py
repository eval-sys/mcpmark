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

def verify_gender_statistics_results(conn) -> bool:
    """Verify the gender statistics results."""
    with conn.cursor() as cur:
        # Get actual results from the created table
        cur.execute("""
            SELECT gender, total_employees, current_employees, percentage_of_workforce
            FROM employees.gender_statistics
            ORDER BY gender
        """)
        actual_results = cur.fetchall()
        
        # Execute ground truth query
        cur.execute("""
            WITH current_emp AS (
            SELECT DISTINCT s.employee_id
            FROM employees.salary s
            WHERE s.to_date = DATE '9999-01-01'
            ),
            total_current AS (
            SELECT COUNT(*) AS cnt
            FROM current_emp
            )
            SELECT
            e.gender::varchar AS gender,
            COUNT(*) AS total_employees,
            COUNT(*) FILTER (WHERE ce.employee_id IS NOT NULL) AS current_employees,
            (COUNT(*) FILTER (WHERE ce.employee_id IS NOT NULL))::DECIMAL
                / NULLIF((SELECT cnt FROM total_current), 0) * 100 AS percentage_of_workforce
            FROM employees.employee e
            LEFT JOIN current_emp ce ON ce.employee_id = e.id
            WHERE e.gender IN ('M','F')
            GROUP BY e.gender
            ORDER BY gender;
        """)
        expected_results = cur.fetchall()

        if len(actual_results) != len(expected_results):
            print(f"❌ Expected {len(expected_results)} gender statistics results, got {len(actual_results)}")
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

        print(f"✅ Gender statistics results are correct ({len(actual_results)} records)")
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
        success = verify_gender_statistics_results(conn)

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