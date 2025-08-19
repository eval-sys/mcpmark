#!/usr/bin/env python3

import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import sys

def verify_rls_implementation():
    """
    Verify that Row Level Security policies have been properly implemented.
    Tests various access scenarios across organizations and roles.
    """
    
    # Database connection parameters from environment
    db_params = {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': os.getenv('POSTGRES_PORT', '5432'),
        'user': os.getenv('POSTGRES_USER', 'postgres'),
        'password': os.getenv('POSTGRES_PASSWORD', 'password'),
        'database': os.getenv('POSTGRES_DB', 'postgres')
    }
    
    try:
        conn = psycopg2.connect(**db_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        print("Verifying RLS implementation...")
        
        # Test cases to verify RLS policies
        test_results = []
        
        # Test 1: Check if RLS is enabled on all tables
        print("\n1. Checking RLS enablement...")
        expected_tables = ['user_profiles', 'user_credentials', 'organization_profiles', 
                          'organization_memberships', 'projects', 'project_assignments']
        
        for table in expected_tables:
            cur.execute("""
                SELECT relrowsecurity 
                FROM pg_class 
                WHERE relname = %s AND relkind = 'r'
            """, (table,))
            result = cur.fetchone()
            
            if result and result[0]:
                test_results.append(f"✓ RLS enabled on {table}")
            else:
                test_results.append(f"✗ RLS NOT enabled on {table}")
        
        # Test 2: User can only see their own credentials
        print("\n2. Testing user credentials access...")
        
        # Set user context for Alice
        cur.execute("SET app.current_user_id = '11111111-1111-1111-1111-111111111111';")
        cur.execute("SELECT COUNT(*) FROM user_credentials;")
        alice_creds_count = cur.fetchone()[0]
        
        # Set user context for Bob
        cur.execute("SET app.current_user_id = '22222222-2222-2222-2222-222222222222';")
        cur.execute("SELECT COUNT(*) FROM user_credentials;")
        bob_creds_count = cur.fetchone()[0]
        
        if alice_creds_count == 1 and bob_creds_count == 1:
            test_results.append("✓ Users can only see their own credentials")
        else:
            test_results.append(f"✗ Credential access failed: Alice sees {alice_creds_count}, Bob sees {bob_creds_count}")
        
        # Test 3: Organization isolation
        print("\n3. Testing organization isolation...")
        
        # Alice (Company A owner) should only see Company A
        cur.execute("SET app.current_user_id = '11111111-1111-1111-1111-111111111111';")
        cur.execute("SELECT COUNT(*) FROM organization_profiles;")
        alice_orgs = cur.fetchone()[0]
        
        # Eve (Company B owner) should only see Company B
        cur.execute("SET app.current_user_id = '55555555-5555-5555-5555-555555555555';")
        cur.execute("SELECT COUNT(*) FROM organization_profiles;")
        eve_orgs = cur.fetchone()[0]
        
        if alice_orgs == 1 and eve_orgs == 1:
            test_results.append("✓ Organization isolation working")
        else:
            test_results.append(f"✗ Organization isolation failed: Alice sees {alice_orgs}, Eve sees {eve_orgs}")
        
        # Test 4: Project visibility based on role and assignment
        print("\n4. Testing project visibility...")
        
        # Alice (owner) should see all Company A projects
        cur.execute("SET app.current_user_id = '11111111-1111-1111-1111-111111111111';")
        cur.execute("SELECT COUNT(*) FROM projects;")
        alice_projects = cur.fetchone()[0]
        
        # Diana (viewer) should only see public projects in Company A
        cur.execute("SET app.current_user_id = '44444444-4444-4444-4444-444444444444';")
        cur.execute("SELECT COUNT(*) FROM projects;")
        diana_projects = cur.fetchone()[0]
        
        # Charlie (member) should see projects he's assigned to + public projects
        cur.execute("SET app.current_user_id = '33333333-3333-3333-3333-333333333333';")
        cur.execute("SELECT COUNT(*) FROM projects;")
        charlie_projects = cur.fetchone()[0]
        
        if alice_projects >= 3 and diana_projects >= 1 and charlie_projects >= 2:
            test_results.append("✓ Project visibility based on roles working")
        else:
            test_results.append(f"✗ Project visibility failed: Alice={alice_projects}, Diana={diana_projects}, Charlie={charlie_projects}")
        
        # Test 5: Sensitive billing data protection
        print("\n5. Testing billing data protection...")
        
        # Check if billing data is visible to non-owners
        try:
            cur.execute("SET app.current_user_id = '33333333-3333-3333-3333-333333333333';")  # Charlie (member)
            cur.execute("SELECT monthly_spend, billing_email FROM organization_profiles;")
            billing_data = cur.fetchall()
            
            # Check if sensitive billing fields are NULL or empty for non-owners
            billing_protected = all(row[0] is None or row[1] is None for row in billing_data)
            
            if billing_protected:
                test_results.append("✓ Billing data protected for non-owners")
            else:
                test_results.append("✗ Billing data not properly protected")
                
        except Exception as e:
            test_results.append(f"✗ Billing data test error: {e}")
        
        # Test 6: Multi-organization user access (Grace)
        print("\n6. Testing multi-organization access...")
        
        # Grace is member of Company A and admin of Company B
        cur.execute("SET app.current_user_id = '77777777-7777-7777-7777-777777777777';")
        cur.execute("SELECT COUNT(*) FROM organization_profiles;")
        grace_orgs = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM projects;")
        grace_projects = cur.fetchone()[0]
        
        if grace_orgs == 2 and grace_projects >= 2:
            test_results.append("✓ Multi-organization access working")
        else:
            test_results.append(f"✗ Multi-organization access failed: Grace sees {grace_orgs} orgs, {grace_projects} projects")
        
        # Test 7: INSERT/UPDATE permissions based on roles
        print("\n7. Testing write permissions...")
        
        try:
            # Test if viewer can update organization (should fail)
            cur.execute("SET app.current_user_id = '44444444-4444-4444-4444-444444444444';")  # Diana (viewer)
            cur.execute("""
                UPDATE organization_profiles 
                SET description = 'Updated by viewer' 
                WHERE org_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
            """)
            test_results.append("✗ Viewer was able to update organization (should be blocked)")
            
        except psycopg2.Error:
            test_results.append("✓ Viewer blocked from updating organization")
        
        # Test 8: Project assignment access
        print("\n8. Testing project assignment visibility...")
        
        # Charlie (member) should only see assignments for projects he can access
        cur.execute("SET app.current_user_id = '33333333-3333-3333-3333-333333333333';")
        cur.execute("SELECT COUNT(*) FROM project_assignments;")
        charlie_assignments = cur.fetchone()[0]
        
        if charlie_assignments >= 1:
            test_results.append("✓ Project assignment visibility working")
        else:
            test_results.append(f"✗ Project assignment visibility failed: Charlie sees {charlie_assignments} assignments")
        
        # Print results
        print("\n" + "="*50)
        print("RLS VERIFICATION RESULTS")
        print("="*50)
        
        passed = sum(1 for result in test_results if result.startswith("✓"))
        failed = sum(1 for result in test_results if result.startswith("✗"))
        
        for result in test_results:
            print(result)
        
        print(f"\nSummary: {passed} passed, {failed} failed")
        
        if failed == 0:
            print("\n🎉 All RLS policies implemented correctly!")
            return True
        else:
            print(f"\n❌ {failed} test(s) failed. Please review your RLS implementation.")
            return False
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Error during verification: {e}")
        return False

if __name__ == "__main__":
    success = verify_rls_implementation()
    sys.exit(0 if success else 1)