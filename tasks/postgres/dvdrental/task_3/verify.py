"""
Verification script for PostgreSQL Task 4: Film Inventory Management
"""

import os
import sys
import psycopg2
from decimal import Decimal

def rows_match(actual_row, expected_row):
    """Compare two rows with appropriate tolerance for decimals and floats."""
    if len(actual_row) != len(expected_row):
        return False
    
    for actual, expected in zip(actual_row, expected_row):
        if isinstance(actual, (Decimal, float)) and isinstance(expected, (Decimal, float)):
            # Use higher tolerance for floating point comparisons
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

def check_new_films(conn) -> bool:
    """Check if the two new films were added correctly."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT title, description, release_year, language_id, 
                   rental_duration, rental_rate, length, replacement_cost, 
                   rating
            FROM film 
            WHERE title IN ('Data Science Adventures', 'Cloud Computing Chronicles')
            ORDER BY title
        """)
        actual_films = cur.fetchall()
        
        expected_films = [
            ('Cloud Computing Chronicles', 'Exploring the world of distributed systems', 2024, 1, 7, Decimal('4.99'), 135, Decimal('18.99'), 'PG'),
            ('Data Science Adventures', 'A thrilling journey through machine learning algorithms', 2024, 1, 5, Decimal('4.389'), 120, Decimal('15.99'), 'PG-13')
        ]
        
        if len(actual_films) != len(expected_films):
            print(f"❌ Expected {len(expected_films)} new films, found {len(actual_films)}")
            return False
            
        mismatches = 0
        for i, (actual, expected) in enumerate(zip(actual_films, expected_films)):
            if not rows_match(actual, expected):
                print(f"❌ Film {i+1} mismatch: expected {expected}, got {actual}")
                mismatches += 1
                
        if mismatches > 0:
            print(f"❌ Total film mismatches: {mismatches}")
            return False
            
        print("✅ Both new films added correctly")
        return True

def check_inventory_records(conn) -> bool:
    """Check if inventory records were added for new films."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT f.title, i.store_id, COUNT(*) as count
            FROM film f
            JOIN inventory i ON f.film_id = i.film_id
            WHERE f.title IN ('Data Science Adventures', 'Cloud Computing Chronicles')
            GROUP BY f.title, i.store_id
            ORDER BY f.title, i.store_id
        """)
        actual_inventory = cur.fetchall()
        
        expected_inventory = [
            ('Cloud Computing Chronicles', 1, 3),
            ('Cloud Computing Chronicles', 2, 2), 
            ('Data Science Adventures', 1, 3),
            ('Data Science Adventures', 2, 2)
        ]
        
        if len(actual_inventory) != len(expected_inventory):
            print(f"❌ Expected {len(expected_inventory)} inventory groups, found {len(actual_inventory)}")
            return False
            
        mismatches = 0
        for i, (actual, expected) in enumerate(zip(actual_inventory, expected_inventory)):
            if not rows_match(actual, expected):
                print(f"❌ Inventory group {i+1} mismatch: expected {expected}, got {actual}")
                mismatches += 1
                
        if mismatches > 0:
            print(f"❌ Total inventory mismatches: {mismatches}")
            return False
                
        print("✅ Inventory records added correctly")
        return True

def check_available_films_table(conn) -> bool:
    """Check if available_films table was created and populated correctly."""
    with conn.cursor() as cur:
        # Get actual results from the created table
        cur.execute("""
            SELECT film_id, title, rental_rate, length
            FROM available_films
            ORDER BY rental_rate DESC, length DESC, title ASC
        """)
        actual_results = cur.fetchall()
        
        # Execute ground truth query
        cur.execute("""
            SELECT DISTINCT f.film_id, f.title, f.rental_rate, f.length
            FROM film f
            JOIN inventory i ON f.film_id = i.film_id
            WHERE f.rental_rate >= 3.00 AND f.rental_rate <= 5.00
            AND f.length > 100
            AND i.store_id = 1
            ORDER BY f.rental_rate DESC, f.length DESC, f.title ASC
        """)
        expected_results = cur.fetchall()
        
        if len(actual_results) != len(expected_results):
            print(f"❌ available_films table has {len(actual_results)} records, expected {len(expected_results)}")
            return False
            
        mismatches = 0
        for i, (actual, expected) in enumerate(zip(actual_results, expected_results)):
            if not rows_match(actual, expected):
                if mismatches < 5:  # Only show first 5 mismatches
                    print(f"❌ available_films row {i+1} mismatch: expected {expected}, got {actual}")
                mismatches += 1
                
        if mismatches > 0:
            print(f"❌ Total available_films mismatches: {mismatches}")
            return False
            
        print(f"✅ available_films table created and populated correctly ({len(actual_results)} records)")
        return True

def check_inventory_cleanup(conn) -> bool:
    """Check if inventory cleanup was performed correctly."""
    with conn.cursor() as cur:
        # Check that no inventory exists for films with replacement_cost > 25 AND rental_rate < 1
        # that also don't have rental records (safe to delete)
        cur.execute("""
            SELECT COUNT(*)
            FROM inventory i
            JOIN film f ON i.film_id = f.film_id
            WHERE f.replacement_cost > 25.00 AND f.rental_rate < 1.00
            AND NOT EXISTS (SELECT 1 FROM rental r WHERE r.inventory_id = i.inventory_id)
        """)
        
        remaining_count = cur.fetchone()[0]
        
        if remaining_count > 0:
            print(f"❌ Found {remaining_count} inventory records that should have been deleted (no rental history)")
            return False
            
        print("✅ Inventory cleanup completed correctly")
        return True

def check_summary_table(conn) -> bool:
    """Check if film_inventory_summary table was created and populated correctly."""
    with conn.cursor() as cur:
            
        # Get actual results from the created table
        cur.execute("""
            SELECT title, rental_rate, total_inventory, store1_count, store2_count
            FROM film_inventory_summary
        """)
        actual_results = cur.fetchall()
        
        # Execute ground truth query
        cur.execute("""
            SELECT f.title, f.rental_rate,
                   COUNT(i.inventory_id) as total_inventory,
                   COUNT(CASE WHEN i.store_id = 1 THEN 1 END) as store1_count,
                   COUNT(CASE WHEN i.store_id = 2 THEN 1 END) as store2_count
            FROM film f
            JOIN inventory i ON f.film_id = i.film_id
            GROUP BY f.film_id, f.title, f.rental_rate
            ORDER BY total_inventory DESC, f.title ASC
        """)
        expected_results = cur.fetchall()
        
        if len(actual_results) != len(expected_results):
            print(f"❌ film_inventory_summary table has {len(actual_results)} records, expected {len(expected_results)}")
            return False
            
        mismatches = 0
        for i, (actual, expected) in enumerate(zip(actual_results, expected_results)):
            if not rows_match(actual, expected):
                if mismatches < 5:  # Only show first 5 mismatches
                    print(f"❌ Summary row {i+1} mismatch: expected {expected}, got {actual}")
                mismatches += 1
                
        if mismatches > 0:
            print(f"❌ Total summary table mismatches: {mismatches}")
            return False
                
        print(f"✅ film_inventory_summary table created and populated correctly ({len(actual_results)} records)")
        return True

def main():
    """Main verification function."""
    print("=" * 70)
    print("PostgreSQL Task 4 Verification: Film Inventory Management")
    print("=" * 70)
    
    # Get connection parameters
    conn_params = get_connection_params()
    
    if not conn_params["database"]:
        print("❌ No database specified")
        sys.exit(1)
    
    try:
        # Connect to database
        conn = psycopg2.connect(**conn_params)
        
        # Verify all operations with short-circuit evaluation
        success = (
            check_new_films(conn) and 
            check_inventory_records(conn) and
            check_available_films_table(conn) and 
            check_inventory_cleanup(conn) and
            check_summary_table(conn)
        )
        
        conn.close()
        
        if success:
            print(f"\n🎉 Task verification: PASS")
            sys.exit(0)
        else:
            print(f"\n❌ Task verification: FAIL")
            sys.exit(1)
            
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Verification error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()