"""
Verification script for PostgreSQL Task 1: Employee Query
"""

import os
import sys
import psycopg2
from decimal import Decimal


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
            SELECT *
            FROM results
        """)

        results = cur.fetchall()

        # Expected results
        expected = [
            (
                10,
                "Neon",
                "Ne",
                20.18,
                10,
                10,
                10,
                2,
                18,
                "gas",
                None,
                True,
                None,
                True,
                None,
                "Noble Gas",
                0.51,
                None,
                21.5645,
                0.0009,
                24.703,
                27.07,
                8,
                "Ramsay and Travers",
                1898,
                1.03,
                2,
                8,
            )
        ]

        if len(results) != len(expected):
            print(f"❌ Expected {len(expected)} results, got {len(results)}")
            return False

        for i, (actual, exp) in enumerate(zip(results, expected)):
            for a, e in zip(actual, exp):
                if isinstance(a, Decimal):
                    a = float(a)
                if a != e:
                    print(f"❌ Row {i + 1} mismatch: expected {e}, got {a}")
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
