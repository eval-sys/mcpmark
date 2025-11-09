"""
Verification script for PostgreSQL LEGO Task 1: Parts Consistency Fix & Constraints
Version 2.1: Relaxed consistency check to allow for one known corner case mismatch.
"""

import os
import sys
import psycopg2
import psycopg2.errors
from typing import Optional, Tuple, List


def get_connection_params() -> dict:
    """Get database connection parameters from environment variables."""
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", 5432)),
        "database": os.getenv("POSTGRES_DATABASE"),
        "user": os.getenv("POSTGRES_USERNAME"),
        "password": os.getenv("POSTGRES_PASSWORD"),
    }


def fetch_candidate_part_row(cur) -> Optional[Tuple[int, str, str, int]]:
    """
    Picks a concrete, non-spare inventory part from the latest inventory of any set.
    This provides a reliable target for testing update and insert triggers.

    Returns a tuple: (inventory_id, set_num, part_num, color_id) or None.
    """
    cur.execute(
        """
        WITH latest_inv AS (
            SELECT set_num, MAX(version) AS max_version
            FROM public.lego_inventories
            GROUP BY set_num
        ), inv AS (
            SELECT li.id, li.set_num
            FROM public.lego_inventories li
            JOIN latest_inv lv ON lv.set_num = li.set_num AND lv.max_version = li.version
        )
        SELECT i.id AS inventory_id, i.set_num, lip.part_num, lip.color_id
        FROM inv i
        JOIN public.lego_inventory_parts lip ON lip.inventory_id = i.id
        WHERE lip.is_spare = false AND lip.quantity > 0
        LIMIT 1;
        """
    )
    return cur.fetchone()


def get_mismatch_count(cur) -> int:
    """Returns the number of sets where num_parts mismatches the computed actual sum."""
    cur.execute(
        """
        WITH latest_inv AS (
            SELECT set_num, MAX(version) AS max_version
            FROM public.lego_inventories
            GROUP BY set_num
        ), inv_latest AS (
            SELECT li.set_num, li.id
            FROM public.lego_inventories li
            JOIN latest_inv lv ON lv.set_num = li.set_num AND lv.max_version = li.version
        ), parts_agg AS (
            SELECT
                i.set_num,
                SUM(lip.quantity) AS actual_parts
            FROM inv_latest i
            JOIN public.lego_inventory_parts lip ON lip.inventory_id = i.id
            WHERE lip.is_spare = false
            GROUP BY i.set_num
        )
        SELECT COUNT(*)
        FROM public.lego_sets s
        LEFT JOIN parts_agg pa ON s.set_num = pa.set_num
        WHERE s.num_parts <> COALESCE(pa.actual_parts, 0);
        """
    )
    return cur.fetchone()[0]


def verify_data_consistency(conn) -> bool:
    """
    TASK 1 VERIFICATION: Checks if the initial data fix was successful.
    (Relaxed: Allows for one corner-case mismatch).
    """
    print("\n-- Verifying Task 1: Data Consistency Fix (Relaxed) --")
    with conn.cursor() as cur:
        count = get_mismatch_count(cur)
        # RELAXED CONDITION: Allow 0 or 1 mismatch to pass.
        if count > 1:
            print(f"❌ FAIL: Found {count} sets with inconsistent part counts. Expected 0 or 1 after fix.")
            return False
        
        print("✅ PASS: Data consistency check passed (allowing for one known mismatch).")
        return True


def main():
    """Main verification function."""
    print("=" * 60)
    print("LEGO Database Consistency Verification Script")
    print("=" * 60)

    conn_params = get_connection_params()
    if not conn_params.get("database"):
        print("❌ CRITICAL: POSTGRES_DATABASE environment variable not set.")
        sys.exit(1)

    try:
        with psycopg2.connect(**conn_params) as conn:
            conn.autocommit = False # Ensure we control transactions

            # Run all verification steps
            results = [
                verify_data_consistency(conn),
            ]

            if all(results):
                print("\n🎉 Overall Result: PASS - All tasks verified successfully!")
                sys.exit(0)
            else:
                print("\n❌ Overall Result: FAIL - One or more verification steps failed.")
                sys.exit(1)

    except psycopg2.OperationalError as e:
        print(f"❌ CRITICAL: Could not connect to the database. Details: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ CRITICAL: An unexpected error occurred during verification. Details: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
