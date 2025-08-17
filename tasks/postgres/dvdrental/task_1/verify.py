"""
Verification script for PostgreSQL Task 1: Customer Payment Query Optimization
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
        "password": os.getenv("POSTGRES_PASSWORD")
    }

def check_payment_customer_id_index(conn) -> bool:
    """Check if there's any index on payment.customer_id column."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT indexname, indexdef 
            FROM pg_indexes 
            WHERE schemaname = 'public' 
            AND tablename = 'payment'
            AND indexdef LIKE '%customer_id%'
        """)
        indexes = cur.fetchall()
        print(indexes)
        return len(indexes) > 0, indexes

def main():
    """Main verification function."""
    print("=" * 60)
    print("PostgreSQL Task 1 Verification: Customer Payment Query Optimization")
    print("=" * 60)
    
    # Get connection parameters
    conn_params = get_connection_params()
    
    if not conn_params["database"]:
        print("❌ No database specified")
        sys.exit(1)
    
    try:
        # Connect to database
        conn = psycopg2.connect(**conn_params)
        
        print("\n🔍 Checking for customer_id index on payment table...")
        
        # Check if any index exists on payment.customer_id
        has_index, indexes = check_payment_customer_id_index(conn)
        
        if has_index:
            print("✅ Found index(es) on payment.customer_id:")
            for index_name, index_def in indexes:
                print(f"   - {index_name}: {index_def}")
        else:
            print("❌ No index found on payment.customer_id column")
        
        conn.close()
        
        if has_index:
            print(f"\n🎉 Task verification: PASS")
            print(f"   - Index on payment.customer_id exists")
            sys.exit(0)
        else:
            print(f"\n❌ Task verification: FAIL")
            print(f"   - No index found on payment.customer_id")
            print(f"   - Create an index on payment(customer_id) to optimize the queries")
            sys.exit(1)
            
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Verification error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()