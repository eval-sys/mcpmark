#!/usr/bin/env python3

import os
import psycopg2
import sys

def verify_security_audit():
    """
    Verify that the security audit correctly identified all permission issues.
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
        cur = conn.cursor()
        
        print("Verifying security audit findings...")
        
        # Check if security_audit_findings table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'security_audit_findings'
            );
        """)
        
        if not cur.fetchone()[0]:
            print("❌ FAIL: security_audit_findings table not found")
            return False
        
        # Get all findings
        cur.execute("SELECT * FROM security_audit_findings ORDER BY finding_id;")
        findings = cur.fetchall()
        
        if not findings:
            print("❌ FAIL: No findings in security_audit_findings table")
            return False
        
        print(f"Found {len(findings)} audit findings")
        
        # Expected issues based on the setup:
        expected_issues = {
            # Dangling users (should have 0 permissions)
            'dangling_users': {'temp_contractor', 'old_employee', 'test_account'},
            
            # Users missing critical permissions for their roles
            'permission_gaps': {
                ('analytics_user', 'user_profiles', 'SELECT'),  # Revoked access
                ('marketing_user', 'product_catalog', 'SELECT'),  # Revoked access  
                ('finance_user', 'user_profiles', 'SELECT'),  # Revoked access
                ('developer_user', 'product_catalog', 'SELECT'),  # Revoked access
                ('backup_user', 'order_management', 'SELECT'),  # Revoked access
            }
        }
        
        found_dangling = set()
        found_permission_gaps = set()
        
        # Analyze findings
        for finding in findings:
            finding_type = finding[1]
            username = finding[2]
            table_name = finding[3]
            missing_permission = finding[4]
            
            if finding_type == 'DANGLING_USER':
                found_dangling.add(username)
            elif finding_type in ['MISSING_PERMISSION', 'ROLE_MISMATCH']:
                if table_name and missing_permission:
                    found_permission_gaps.add((username, table_name, missing_permission))
        
        # Verify dangling users
        missing_dangling = expected_issues['dangling_users'] - found_dangling
        extra_dangling = found_dangling - expected_issues['dangling_users']
        
        print(f"\n=== Dangling Users ===")
        print(f"Expected: {expected_issues['dangling_users']}")
        print(f"Found: {found_dangling}")
        
        if missing_dangling:
            print(f"❌ Missing dangling users: {missing_dangling}")
        if extra_dangling:
            print(f"ℹ️  Extra dangling users found: {extra_dangling}")
        
        # Verify permission gaps
        missing_gaps = expected_issues['permission_gaps'] - found_permission_gaps
        
        print(f"\n=== Permission Gaps ===")
        print(f"Expected gaps: {len(expected_issues['permission_gaps'])}")
        print(f"Found gaps: {len(found_permission_gaps)}")
        
        if missing_gaps:
            print(f"❌ Missing permission gaps:")
            for gap in missing_gaps:
                print(f"   - {gap[0]} missing {gap[2]} on {gap[1]}")
        
        # Additional validation: Check findings structure
        structure_valid = True
        for i, finding in enumerate(findings):
            if len(finding) != 7:  # Should have 7 columns
                print(f"❌ FAIL: Finding {i+1} has wrong number of columns")
                structure_valid = False
                continue
                
            finding_type, username, table_name, missing_permission, justification, action, severity = finding[1:]
            
            if not finding_type:
                print(f"❌ FAIL: Finding {i+1} missing finding_type")
                structure_valid = False
            
            if not username:
                print(f"❌ FAIL: Finding {i+1} missing username") 
                structure_valid = False
            
            if not justification:
                print(f"❌ FAIL: Finding {i+1} missing business_justification")
                structure_valid = False
                
            if not action:
                print(f"❌ FAIL: Finding {i+1} missing recommended_action")
                structure_valid = False
                
            if severity not in ['HIGH', 'MEDIUM', 'LOW']:
                print(f"❌ FAIL: Finding {i+1} invalid severity: {severity}")
                structure_valid = False
        
        # Calculate score
        score = 0
        max_score = 100
        
        # Points for finding dangling users (30 points)
        dangling_score = (len(found_dangling & expected_issues['dangling_users']) / len(expected_issues['dangling_users'])) * 30
        score += dangling_score
        
        # Points for finding permission gaps (50 points)
        gap_score = (len(found_permission_gaps & expected_issues['permission_gaps']) / len(expected_issues['permission_gaps'])) * 50
        score += gap_score
        
        # Points for proper structure (20 points)
        if structure_valid:
            score += 20
        
        print(f"\n=== Verification Results ===")
        print(f"Dangling users score: {dangling_score:.1f}/30")
        print(f"Permission gaps score: {gap_score:.1f}/50") 
        print(f"Structure score: {20 if structure_valid else 0}/20")
        print(f"Total Score: {score:.1f}/100")
        
        if score >= 80:
            print("✅ PASS: Security audit successfully identified most critical issues")
            return True
        elif score >= 60:
            print("⚠️  PARTIAL: Security audit identified some issues but missed important findings")
            return False
        else:
            print("❌ FAIL: Security audit failed to identify critical security issues")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Error during verification: {e}")
        return False
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    success = verify_security_audit()
    sys.exit(0 if success else 1)