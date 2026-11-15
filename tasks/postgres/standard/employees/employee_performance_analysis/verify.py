"""
Verification script for PostgreSQL Task 1: Employee Performance Analysis
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

# Task-contract checks: validate the *declared* table schemas, not only rows.
# PostgreSQL's format_type(..., NULL) reports the base type independent of
# permissible typmods such as VARCHAR(255) and NUMERIC(18, 4).
_EXPECTED_OUTPUT_COLUMNS = {
    "employee_performance_analysis": {
        "employee_id": "bigint",
        "performance_category": "character varying",
        "salary_growth_rate": "numeric",
        "days_of_service": "integer",
        "promotion_count": "integer",
    },
    "department_salary_analysis": {
        "department_name": "character varying",
        "avg_current_salary": "numeric",
        "employee_count": "integer",
        "salary_range_spread": "integer",
    },
}


def verify_output_schema(conn) -> bool:
    """Enforce the exact output column names and PostgreSQL base types.

    Check only requirements explicitly specified by the task: column order,
    typmods, optional CHECK/UNIQUE constraints and nullability are not scored.
    Views are not accepted because the instructions require tables.
    """
    passed = True
    with conn.cursor() as cur:
        for table_name, expected in _EXPECTED_OUTPUT_COLUMNS.items():
            cur.execute("""
                SELECT a.attname, pg_catalog.format_type(a.atttypid, NULL)
                FROM pg_catalog.pg_attribute AS a
                JOIN pg_catalog.pg_class AS c ON c.oid = a.attrelid
                JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
                WHERE n.nspname = 'employees'
                  AND c.relname = %s
                  AND c.relkind IN ('r', 'p')
                  AND a.attnum > 0
                  AND NOT a.attisdropped
            """, (table_name,))
            observed = dict(cur.fetchall())
            if observed != expected:
                missing = sorted(set(expected) - set(observed))
                extra = sorted(set(observed) - set(expected))
                wrong_types = {
                    col: {"expected": expected[col], "actual": observed[col]}
                    for col in sorted(set(expected) & set(observed))
                    if observed[col] != expected[col]
                }
                print(f"❌ {table_name} output schema mismatch: "
                      f"missing={missing}, extra={extra}, wrong_types={wrong_types}")
                passed = False
            else:
                print(f"✅ {table_name} declared columns and types match the task contract")
    return passed


def verify_performance_results(conn) -> bool:
    """Verify the employee performance analysis results."""
    with conn.cursor() as cur:
        # Get actual results from the created table
        cur.execute("""
            SELECT employee_id, performance_category, salary_growth_rate, 
                   days_of_service, promotion_count
            FROM employees.employee_performance_analysis 
            ORDER BY employee_id
        """)
        actual_results = cur.fetchall()
        
        # Execute ground truth query - use first salary record as starting salary
        cur.execute("""
            WITH current_salary AS (
            SELECT employee_id, amount AS current_amount
            FROM (
                SELECT s.*,
                    ROW_NUMBER() OVER (PARTITION BY s.employee_id
                                        ORDER BY s.from_date DESC, s.amount DESC) AS rn
                FROM employees.salary s
                WHERE s.to_date = DATE '9999-01-01'
            ) x
            WHERE rn = 1
            ),
            first_salary AS (
            SELECT employee_id, amount AS first_amount
            FROM (
                SELECT s.*,
                    ROW_NUMBER() OVER (PARTITION BY s.employee_id
                                        ORDER BY s.from_date ASC, s.amount ASC) AS rn
                FROM employees.salary s
            ) x
            WHERE rn = 1
            ),
            title_counts AS (
            SELECT t.employee_id, COUNT(DISTINCT t.title) AS promotion_count
            FROM employees.title t
            GROUP BY t.employee_id
            ),
            base AS (
            SELECT e.id AS employee_id,
                    e.hire_date,
                    cs.current_amount,
                    fs.first_amount,
                    COALESCE(tc.promotion_count, 0) AS promotion_count
            FROM employees.employee e
            JOIN current_salary cs ON cs.employee_id = e.id
            JOIN first_salary  fs ON fs.employee_id = e.id
            LEFT JOIN title_counts tc ON tc.employee_id = e.id
            ),
            scored AS (
            SELECT
                employee_id,
                ((current_amount - first_amount) / NULLIF(first_amount, 0)::NUMERIC) * 100 AS salary_growth_rate,
                (CURRENT_DATE - hire_date)::INTEGER AS days_of_service,
                promotion_count
            FROM base
            )
            SELECT
            s.employee_id,
            CASE
                WHEN s.salary_growth_rate > 40 AND s.promotion_count > 1 THEN 'high_achiever'
                WHEN s.salary_growth_rate < 15 AND s.days_of_service > 3650 THEN 'needs_attention'
                ELSE 'steady_performer'
            END AS performance_category,
            s.salary_growth_rate,
            s.days_of_service,
            s.promotion_count AS promotion_count
            FROM scored s
            ORDER BY s.employee_id;
        """)
        expected_results = cur.fetchall()

        if len(actual_results) != len(expected_results):
            print(f"❌ Expected {len(expected_results)} performance results, got {len(actual_results)}")
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

        print(f"✅ Employee performance results are correct ({len(actual_results)} records)")
        return True

def verify_department_results(conn) -> bool:
    """Verify the department salary analysis results."""
    with conn.cursor() as cur:
        # Get actual results from the created table
        cur.execute("""
            SELECT department_name, avg_current_salary, employee_count, salary_range_spread
            FROM employees.department_salary_analysis
            ORDER BY department_name
        """)
        actual_results = cur.fetchall()

        # Execute ground truth query
        cur.execute("""
            WITH current_salary AS (
            SELECT employee_id, amount
            FROM (
                SELECT s.*,
                    ROW_NUMBER() OVER (PARTITION BY s.employee_id
                                        ORDER BY s.from_date DESC, s.amount DESC) AS rn
                FROM employees.salary s
                WHERE s.to_date = DATE '9999-01-01'
            ) x
            WHERE rn = 1
            ),
            current_dept AS (
            SELECT DISTINCT de.employee_id, de.department_id
            FROM employees.department_employee de
            WHERE de.to_date = DATE '9999-01-01'
            )
            SELECT 
            d.dept_name AS department_name,
            AVG(cs.amount)::DECIMAL AS avg_current_salary,
            COUNT(DISTINCT cd.employee_id) AS employee_count,
            (MAX(cs.amount) - MIN(cs.amount)) AS salary_range_spread
            FROM employees.department d
            JOIN current_dept cd ON cd.department_id = d.id
            JOIN current_salary cs ON cs.employee_id = cd.employee_id
            GROUP BY d.id, d.dept_name
            ORDER BY d.dept_name;
        """)
        expected_results = cur.fetchall()

        if len(actual_results) != len(expected_results):
            print(f"❌ Expected {len(expected_results)} department results, got {len(actual_results)}")
            return False

        mismatches = 0
        for i, (actual, expected) in enumerate(zip(actual_results, expected_results)):
            if not rows_match(actual, expected):
                print(f"❌ Row {i+1} mismatch: expected {expected}, got {actual}")
                mismatches += 1

        if mismatches > 0:
            print(f"❌ Total mismatches: {mismatches}")
            return False

        print(f"✅ Department salary results are correct ({len(actual_results)} records)")
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

        # Verify results
        success = (verify_output_schema(conn)
                   and verify_performance_results(conn)
                   and verify_department_results(conn))

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