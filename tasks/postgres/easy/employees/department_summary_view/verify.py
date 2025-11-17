"""
Verification script for PostgreSQL Task 6: Reporting and Automation System
"""

import os
import sys
import psycopg2
from decimal import Decimal

def rows_match(actual_row, expected_row):
    """
    Compare two rows with appropriate tolerance.
    For Decimal types: allows 0.1 tolerance
    For date types: convert to string for comparison
    For other types: requires exact match
    """
    if len(actual_row) != len(expected_row):
        return False
    
    for actual, expected in zip(actual_row, expected_row):
        if isinstance(actual, Decimal) and isinstance(expected, (Decimal, float, int)):
            if abs(float(actual) - float(expected)) > 0.1:
                return False
        elif hasattr(actual, 'strftime'):  # datetime.date or datetime.datetime
            if str(actual) != str(expected):
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

def verify_materialized_views(conn) -> bool:
    """Verify that materialized views were created and populated correctly."""
    with conn.cursor() as cur:
        # Check all departments' data accuracy
        cur.execute("""
            SELECT department_name, total_employees, avg_salary, total_payroll, manager_name
            FROM employees.exec_department_summary
            ORDER BY department_name
        """)
        view_data = cur.fetchall()
        
        # Get actual data for all departments
        cur.execute("""
            WITH current_salary AS (
            SELECT employee_id, amount
            FROM (
                SELECT s.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY s.employee_id
                        ORDER BY s.from_date DESC, s.amount DESC
                    ) AS rn
                FROM employees.salary s
                WHERE s.to_date = DATE '9999-01-01'
            ) x
            WHERE rn = 1
            ),
            current_dept AS (
            SELECT DISTINCT de.employee_id, de.department_id
            FROM employees.department_employee de
            WHERE de.to_date = DATE '9999-01-01'
            ),
            current_manager AS (
            SELECT department_id,
                    CONCAT(e.first_name, ' ', e.last_name) AS manager_name
            FROM (
                SELECT dm.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY dm.department_id
                        ORDER BY dm.from_date DESC, dm.employee_id
                    ) AS rn
                FROM employees.department_manager dm
                WHERE dm.to_date = DATE '9999-01-01'
            ) dm
            JOIN employees.employee e ON e.id = dm.employee_id
            WHERE dm.rn = 1
            )
            SELECT
            d.dept_name AS department_name,
            COUNT(cd.employee_id)::INT AS total_employees,
            AVG(cs.amount)::DECIMAL   AS avg_salary,
            COALESCE(SUM(cs.amount), 0)::BIGINT AS total_payroll,
            cm.manager_name
            FROM employees.department d
            LEFT JOIN current_dept   cd ON cd.department_id = d.id
            LEFT JOIN current_salary cs ON cs.employee_id = cd.employee_id
            LEFT JOIN current_manager cm ON cm.department_id = d.id
            GROUP BY d.id, d.dept_name, cm.manager_name
            ORDER BY d.dept_name;
        """)
        actual_data = cur.fetchall()
        
        if len(view_data) != len(actual_data):
            print(f"❌ Department count mismatch: view={len(view_data)}, actual={len(actual_data)}")
            return False
            
        for view_row, actual_row in zip(view_data, actual_data):
            if not rows_match(view_row, actual_row):
                print(f"❌ Department summary data incorrect for {view_row[0]}: view={view_row}, actual={actual_row}")
                return False
            
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

        # Verify all components
        success = verify_materialized_views(conn)

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