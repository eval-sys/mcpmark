#!/usr/bin/env python3

import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import sys

def setup_rls_environment():
    """
    Set up a PostgreSQL environment with business tables and Row Level Security (RLS) policies.
    Creates a multi-tenant SaaS scenario with complex organizational hierarchies and role-based access.
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
        
        print("Setting up RLS business environment...")
        
        # Clean up existing tables and users
        cleanup_sql = """
            DROP TABLE IF EXISTS project_assignments CASCADE;
            DROP TABLE IF EXISTS projects CASCADE;
            DROP TABLE IF EXISTS organization_memberships CASCADE;
            DROP TABLE IF EXISTS organization_profiles CASCADE;
            DROP TABLE IF EXISTS user_credentials CASCADE;
            DROP TABLE IF EXISTS user_profiles CASCADE;
            DROP FUNCTION IF EXISTS current_user_id() CASCADE;
            DROP FUNCTION IF EXISTS user_org_role(uuid, uuid) CASCADE;
            DROP FUNCTION IF EXISTS can_access_organization(uuid) CASCADE;
        """
        cur.execute(cleanup_sql)
        
        # Create the core business schema
        
        # 1. User Profiles Table
        cur.execute("""
            CREATE TABLE user_profiles (
                user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                first_name VARCHAR(50) NOT NULL,
                last_name VARCHAR(50) NOT NULL,
                phone VARCHAR(20),
                bio TEXT,
                avatar_url TEXT,
                timezone VARCHAR(50) DEFAULT 'UTC',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT true,
                last_login TIMESTAMP,
                email_verified BOOLEAN DEFAULT false
            );
        """)
        
        # 2. User Credentials Table (highly sensitive)
        cur.execute("""
            CREATE TABLE user_credentials (
                credential_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES user_profiles(user_id) ON DELETE CASCADE,
                password_hash VARCHAR(255) NOT NULL,
                password_salt VARCHAR(100) NOT NULL,
                api_key_hash VARCHAR(255),
                session_token_hash VARCHAR(255),
                refresh_token_hash VARCHAR(255),
                two_factor_secret VARCHAR(32),
                backup_codes TEXT[],
                failed_login_attempts INTEGER DEFAULT 0,
                last_failed_login TIMESTAMP,
                password_reset_token VARCHAR(255),
                password_reset_expires TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # 3. Organization Profiles Table
        cur.execute("""
            CREATE TABLE organization_profiles (
                org_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                org_name VARCHAR(100) NOT NULL,
                org_slug VARCHAR(50) UNIQUE NOT NULL,
                description TEXT,
                website_url TEXT,
                industry VARCHAR(50),
                company_size VARCHAR(20),
                logo_url TEXT,
                subscription_tier VARCHAR(20) DEFAULT 'free', -- free, pro, enterprise
                billing_email VARCHAR(100),
                billing_address JSONB,
                monthly_spend DECIMAL(10,2) DEFAULT 0,
                usage_limits JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT true,
                trial_ends_at TIMESTAMP
            );
        """)
        
        # 4. Organization Memberships Table (junction table with roles)
        cur.execute("""
            CREATE TABLE organization_memberships (
                membership_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES user_profiles(user_id) ON DELETE CASCADE,
                org_id UUID REFERENCES organization_profiles(org_id) ON DELETE CASCADE,
                role VARCHAR(20) NOT NULL CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
                invited_by UUID REFERENCES user_profiles(user_id),
                invited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                joined_at TIMESTAMP,
                is_active BOOLEAN DEFAULT true,
                permissions JSONB DEFAULT '{}',
                UNIQUE(user_id, org_id)
            );
        """)
        
        # 5. Projects Table
        cur.execute("""
            CREATE TABLE projects (
                project_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                org_id UUID REFERENCES organization_profiles(org_id) ON DELETE CASCADE,
                project_name VARCHAR(100) NOT NULL,
                description TEXT,
                status VARCHAR(20) DEFAULT 'active', -- active, completed, archived, deleted
                visibility VARCHAR(20) DEFAULT 'private', -- public, private, internal
                created_by UUID REFERENCES user_profiles(user_id),
                budget DECIMAL(12,2),
                estimated_hours INTEGER,
                actual_hours INTEGER DEFAULT 0,
                start_date DATE,
                due_date DATE,
                priority VARCHAR(10) DEFAULT 'medium', -- low, medium, high, urgent
                tags TEXT[],
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # 6. Project Assignments Table
        cur.execute("""
            CREATE TABLE project_assignments (
                assignment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                project_id UUID REFERENCES projects(project_id) ON DELETE CASCADE,
                user_id UUID REFERENCES user_profiles(user_id) ON DELETE CASCADE,
                role VARCHAR(20) NOT NULL, -- lead, developer, designer, reviewer, observer
                assigned_by UUID REFERENCES user_profiles(user_id),
                assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                hourly_rate DECIMAL(8,2),
                estimated_hours INTEGER,
                actual_hours INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT true,
                UNIQUE(project_id, user_id)
            );
        """)
        
        print("Created 6 business tables with proper relationships")
        
        # Create helper functions for RLS policies
        
        # Function to get current user's UUID from session
        cur.execute("""
            CREATE OR REPLACE FUNCTION current_user_id()
            RETURNS UUID AS $$
            BEGIN
                -- In a real application, this would get the user ID from the session
                -- For testing, we'll use a session variable
                RETURN COALESCE(
                    current_setting('app.current_user_id', true)::UUID,
                    '00000000-0000-0000-0000-000000000000'::UUID
                );
            END;
            $$ LANGUAGE plpgsql SECURITY DEFINER;
        """)
        
        # Function to get user's role in a specific organization
        cur.execute("""
            CREATE OR REPLACE FUNCTION user_org_role(user_uuid UUID, org_uuid UUID)
            RETURNS TEXT AS $$
            DECLARE
                user_role TEXT;
            BEGIN
                SELECT role INTO user_role
                FROM organization_memberships
                WHERE user_id = user_uuid AND org_id = org_uuid AND is_active = true;
                
                RETURN COALESCE(user_role, 'none');
            END;
            $$ LANGUAGE plpgsql SECURITY DEFINER;
        """)
        
        # Function to check if user can access an organization
        cur.execute("""
            CREATE OR REPLACE FUNCTION can_access_organization(org_uuid UUID)
            RETURNS BOOLEAN AS $$
            BEGIN
                RETURN EXISTS (
                    SELECT 1 FROM organization_memberships
                    WHERE user_id = current_user_id() 
                    AND org_id = org_uuid 
                    AND is_active = true
                );
            END;
            $$ LANGUAGE plpgsql SECURITY DEFINER;
        """)
        
        print("Created helper functions for RLS")
        
        # Create sample data for testing
        
        # Sample users
        cur.execute("""
            INSERT INTO user_profiles (user_id, username, email, first_name, last_name) VALUES
            ('11111111-1111-1111-1111-111111111111', 'alice_owner', 'alice@company-a.com', 'Alice', 'Johnson'),
            ('22222222-2222-2222-2222-222222222222', 'bob_admin', 'bob@company-a.com', 'Bob', 'Smith'),
            ('33333333-3333-3333-3333-333333333333', 'charlie_member', 'charlie@company-a.com', 'Charlie', 'Brown'),
            ('44444444-4444-4444-4444-444444444444', 'diana_viewer', 'diana@company-a.com', 'Diana', 'Wilson'),
            ('55555555-5555-5555-5555-555555555555', 'eve_owner', 'eve@company-b.com', 'Eve', 'Davis'),
            ('66666666-6666-6666-6666-666666666666', 'frank_member', 'frank@company-b.com', 'Frank', 'Miller'),
            ('77777777-7777-7777-7777-777777777777', 'grace_freelancer', 'grace@freelance.com', 'Grace', 'Taylor');
        """)
        
        # Sample organizations
        cur.execute("""
            INSERT INTO organization_profiles (org_id, org_name, org_slug, subscription_tier, monthly_spend) VALUES
            ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'Company A Inc', 'company-a', 'enterprise', 2500.00),
            ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'Company B Ltd', 'company-b', 'pro', 500.00),
            ('cccccccc-cccc-cccc-cccc-cccccccccccc', 'Startup C', 'startup-c', 'free', 0.00);
        """)
        
        # Sample memberships
        cur.execute("""
            INSERT INTO organization_memberships (user_id, org_id, role, joined_at) VALUES
            ('11111111-1111-1111-1111-111111111111', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'owner', CURRENT_TIMESTAMP),
            ('22222222-2222-2222-2222-222222222222', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'admin', CURRENT_TIMESTAMP),
            ('33333333-3333-3333-3333-333333333333', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'member', CURRENT_TIMESTAMP),
            ('44444444-4444-4444-4444-444444444444', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'viewer', CURRENT_TIMESTAMP),
            ('55555555-5555-5555-5555-555555555555', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'owner', CURRENT_TIMESTAMP),
            ('66666666-6666-6666-6666-666666666666', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'member', CURRENT_TIMESTAMP),
            ('77777777-7777-7777-7777-777777777777', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'member', CURRENT_TIMESTAMP),
            ('77777777-7777-7777-7777-777777777777', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'admin', CURRENT_TIMESTAMP);
        """)
        
        # Sample projects
        cur.execute("""
            INSERT INTO projects (project_id, org_id, project_name, visibility, created_by, budget) VALUES
            ('dddddddd-dddd-dddd-dddd-dddddddddddd', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'Website Redesign', 'private', '11111111-1111-1111-1111-111111111111', 50000.00),
            ('eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'Mobile App', 'public', '22222222-2222-2222-2222-222222222222', 75000.00),
            ('ffffffff-ffff-ffff-ffff-ffffffffffff', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'Data Migration', 'private', '55555555-5555-5555-5555-555555555555', 25000.00),
            ('99999999-9999-9999-9999-999999999999', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'Internal Tool', 'internal', '11111111-1111-1111-1111-111111111111', 30000.00);
        """)
        
        # Sample project assignments
        cur.execute("""
            INSERT INTO project_assignments (project_id, user_id, role, assigned_by, hourly_rate) VALUES
            ('dddddddd-dddd-dddd-dddd-dddddddddddd', '33333333-3333-3333-3333-333333333333', 'developer', '11111111-1111-1111-1111-111111111111', 75.00),
            ('dddddddd-dddd-dddd-dddd-dddddddddddd', '77777777-7777-7777-7777-777777777777', 'designer', '11111111-1111-1111-1111-111111111111', 85.00),
            ('eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee', '22222222-2222-2222-2222-222222222222', 'lead', '11111111-1111-1111-1111-111111111111', 95.00),
            ('ffffffff-ffff-ffff-ffff-ffffffffffff', '66666666-6666-6666-6666-666666666666', 'developer', '55555555-5555-5555-5555-555555555555', 70.00);
        """)
        
        # Sample credentials (minimal for security)
        cur.execute("""
            INSERT INTO user_credentials (user_id, password_hash, password_salt) VALUES
            ('11111111-1111-1111-1111-111111111111', 'hash_alice', 'salt_alice'),
            ('22222222-2222-2222-2222-222222222222', 'hash_bob', 'salt_bob'),
            ('33333333-3333-3333-3333-333333333333', 'hash_charlie', 'salt_charlie'),
            ('44444444-4444-4444-4444-444444444444', 'hash_diana', 'salt_diana'),
            ('55555555-5555-5555-5555-555555555555', 'hash_eve', 'salt_eve'),
            ('66666666-6666-6666-6666-666666666666', 'hash_frank', 'salt_frank'),
            ('77777777-7777-7777-7777-777777777777', 'hash_grace', 'salt_grace');
        """)
        
        print("Created sample data with 7 users, 3 organizations, 4 projects")
        print("Environment setup complete!")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Error setting up environment: {e}")
        sys.exit(1)

if __name__ == "__main__":
    setup_rls_environment()