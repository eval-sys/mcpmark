"""
Verification script for PostgreSQL Task 1: Employee Query
"""

import os
import sys
import psycopg2


def get_connection_params() -> dict:
    """Get database connection parameters."""
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", 5432)),
        "database": os.getenv("POSTGRES_DATABASE"),
        "user": os.getenv("POSTGRES_USERNAME"),
        "password": os.getenv("POSTGRES_PASSWORD"),
    }


def verify_query_results(conn) -> bool:
    """Verify the query was executed correctly."""
    with conn.cursor() as cur:
        # Check if a query was executed that returns the correct results
        cur.execute("""
            SELECT name, department, salary
            FROM employees
            WHERE department = 'Engineering' AND salary > 70000
            ORDER BY salary DESC
        """)

        results = cur.fetchall()

        # Expected results
        expected = [
            ("Bob Johnson", "Engineering", 80000.00),
            ("John Doe", "Engineering", 75000.00),
        ]

        if len(results) != len(expected):
            print(f"❌ Expected {len(expected)} results, got {len(results)}")
            return False

        for i, (actual, exp) in enumerate(zip(results, expected)):
            if actual[0] != exp[0] or actual[1] != exp[1] or float(actual[2]) != exp[2]:
                print(f"❌ Row {i + 1} mismatch: expected {exp}, got {actual}")
                return False

        print("✅ Query results are correct")
        return True


def main():
    """Main verification function."""
    print("🔍 Verifying PostgreSQL Task 1: Employee Query")
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
        success = verify_query_results(conn)

        conn.close()

        if success:
            print("\n🎉 Task 1 verification: PASS")
            sys.exit(0)
        else:
            print("\n❌ Task 1 verification: FAIL")
            sys.exit(1)

    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Verification error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
