"""
Verification script for PostgreSQL Task 5: Database Schema and Data Operations
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


def verify_project_data(conn) -> bool:
    """Verify that project data was inserted and updated correctly."""
    with conn.cursor() as cur:
        # Check project data after updates
        cur.execute("""
            SELECT project_name, start_date, end_date, budget, status
            FROM employees.employee_projects
            ORDER BY project_name
        """)
        projects = cur.fetchall()
        
        if len(projects) != 3:
            print(f"❌ Expected 3 projects, found {len(projects)}")
            return False
            
        # Expected final state after all updates
        expected = {
            'Database Modernization': ('2024-01-15', '2024-06-30', 250000.00, 'active'),
            'Employee Portal Upgrade': ('2024-02-01', '2024-05-15', 180000.00, 'active'),
            'HR Analytics Dashboard': ('2023-11-01', '2024-01-31', 120000.00, 'active')
        }
        
        for project in projects:
            name = project[0]
            if name not in expected:
                print(f"❌ Unexpected project: {name}")
                return False
                
            exp = expected[name]
            # Use rows_match for comparison
            expected_row = (name,) + exp
            if not rows_match(project, expected_row):
                print(f"❌ Project {name} data mismatch: expected {expected_row}, got {project}")
                return False
                
        print("✅ Project data is correct")
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
        success = verify_project_data(conn)

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