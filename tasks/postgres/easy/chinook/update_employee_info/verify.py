"""
Verification script for PostgreSQL Task 3: Employee Hierarchy Management
"""

import os
import sys
import psycopg2
from decimal import Decimal

def rows_match(actual_row, expected_row):
    """
    Compare two rows with appropriate tolerance.
    For Decimal types: allows 0.01 tolerance
    For other types: requires exact match
    """
    if len(actual_row) != len(expected_row):
        return False
    
    for actual, expected in zip(actual_row, expected_row):
        if isinstance(actual, Decimal) and isinstance(expected, Decimal):
            if abs(float(actual) - float(expected)) > 0.01:
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

def verify_employee_count_and_titles(conn) -> bool:
    """Verify the final employee count and title changes."""
    with conn.cursor() as cur:
        # Check the final verification query results
        cur.execute("""
            SELECT 
                COUNT(*) as total_employees,
                COUNT(CASE WHEN "Title" = 'CEO' THEN 1 END) as ceo_count,
                COUNT(CASE WHEN "Title" = 'IT Specialist' THEN 1 END) as it_specialist_count
            FROM "Employee"
        """)
        result = cur.fetchone()
        
        total_employees, ceo_count, it_specialist_count = result
        
        if total_employees != 8:
            print(f"❌ Expected 8 total employees, got {total_employees}")
            return False
            
        if ceo_count != 1:
            print(f"❌ Expected 1 CEO, got {ceo_count}")
            return False
            
        if it_specialist_count != 2:
            print(f"❌ Expected 2 IT Specialists, got {it_specialist_count}")
            return False
            
        print("✅ Employee count and title verification passed")
        return True

def verify_specific_employees(conn) -> bool:
    """Verify specific employee records and modifications."""
    with conn.cursor() as cur:
        # Check all employee fields in one query
        cur.execute("""
            SELECT "EmployeeId", "LastName", "FirstName", "Title", "ReportsTo", "BirthDate", 
                   "HireDate", "Address", "City", "State", "Country", "PostalCode", 
                   "Phone", "Fax", "Email"
            FROM "Employee" 
            WHERE "EmployeeId" IN (1, 2)
            ORDER BY "EmployeeId"
        """)
        employees = cur.fetchall()
        
        from datetime import datetime
        
        expected = [
            # Andrew Adams (ID 1) - Title changes to 'CEO', phone stays original, ReportsTo stays None
            (1, 'Adams', 'Andrew', 'CEO', None, datetime(1962, 2, 18), datetime(2002, 8, 14),
             '11120 Jasper Ave NW', 'Edmonton', 'AB', 'Canada', 'T5K 2N1', '+1 (780) 428-9482', '+1 (780) 428-3457', 'andrew@chinookcorp.com'),
            # Nancy Edwards (ID 2) - Phone changes, title stays 'Sales Manager', ReportsTo stays 1
            (2, 'Edwards', 'Nancy', 'Sales Manager', 1, datetime(1958, 12, 8), datetime(2002, 5, 1),
             '825 8 Ave SW', 'Calgary', 'AB', 'Canada', 'T2P 2T3', '+1 (403) 555-9999', '+1 (403) 262-3322', 'nancy@chinookcorp.com'),
        ]
        
        if len(employees) != 2:
            print(f"❌ Expected 2 key employees, found {len(employees)}")
            return False
            
        # Full field comparison for all employees using rows_match
        for actual, expected_emp in zip(employees, expected):
            if not rows_match(actual, expected_emp):
                print(f"❌ Employee {actual[0]} row mismatch: expected {expected_emp}, got {actual}")
                return False
        
        print("✅ Specific employee verification passed - all fields match exactly")
        return True

def main():
    """Main verification function."""
    print("=" * 50)
    print("Verifying Task 3: Employee Hierarchy Management")
    print("=" * 50)

    # Get connection parameters
    conn_params = get_connection_params()

    if not conn_params["database"]:
        print("❌ No database specified")
        sys.exit(1)

    try:
        # Connect to database
        conn = psycopg2.connect(**conn_params)

        # Run verification checks with short-circuit evaluation
        success = (
            verify_employee_count_and_titles(conn) and
            verify_specific_employees(conn)
                  )
        conn.close()

        if success:
            print("\n🎉 Task verification: PASS")
            print("All employee hierarchy management operations completed correctly!")
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