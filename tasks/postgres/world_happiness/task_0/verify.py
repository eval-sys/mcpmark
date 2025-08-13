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
            SELECT country_or_region, score, gdp_per_capita
            FROM results
        """)

        results = cur.fetchall()

        # Expected results
        expected = [
            ("Guatemala", 6.44, 0.80),
            ("El Salvador", 6.25, 0.79),
            ("Uzbekistan", 6.17, 0.75),
            ("Nicaragua", 6.11, 0.69),
            ("Kosovo", 6.10, 0.88),
            ("Jamaica", 5.89, 0.83),
            ("Honduras", 5.86, 0.64),
            ("Bolivia", 5.78, 0.78),
            ("Paraguay", 5.74, 0.86),
            ("Pakistan", 5.65, 0.68),
            ("Philippines", 5.63, 0.81),
            ("Moldova", 5.53, 0.69),
            ("Tajikistan", 5.47, 0.49),
        ]

        if len(results) != len(expected):
            print(f"❌ Expected {len(expected)} results, got {len(results)}")
            return False

        for i, (actual, exp) in enumerate(zip(results, expected)):
            if (
                actual[0] != exp[0]
                or float(actual[1]) != exp[1]
                or float(actual[2]) != exp[2]
            ):
                print(f"❌ Row {i + 1} mismatch: expected {exp}, got {actual}")
                return False

        print("✅ Query results are correct")
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
        success = verify_query_results(conn)

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
