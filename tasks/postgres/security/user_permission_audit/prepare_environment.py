#!/usr/bin/env python3

import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import sys

def setup_security_environment():
    """
    Set up a security-focused PostgreSQL environment with business tables and users with various permissions.
    Creates a scenario where some users have dangling or insufficient permissions for realistic security analysis.
    """

    # Database connection parameters from environment
    db_params = {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': os.getenv('POSTGRES_PORT', '5432'),
        'user': os.getenv('POSTGRES_USER', 'postgres'),
        'password': os.getenv('POSTGRES_PASSWORD', 'password'),
        'database': os.getenv('POSTGRES_DATABASE', 'postgres')
    }

    postgres_params = db_params.copy()
    postgres_params['database'] = 'postgres'

    try:
        conn_postgres = psycopg2.connect(**postgres_params)
        conn_postgres.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur_postgres = conn_postgres.cursor()

        current_db = db_params['database']
        cur_postgres.execute("SELECT datname FROM pg_database WHERE datname LIKE %s AND datname != %s;", ('%user_permission_audit%', current_db))
        audit_databases = cur_postgres.fetchall()

        if audit_databases:
            for db_row in audit_databases:
                db_name = db_row[0]
                try:
                    cur_postgres.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s;", (db_name,))
                    # TODO: Not sure why we have to drop database in order to drop the following users
                    cur_postgres.execute(f"DROP DATABASE IF EXISTS {db_name};")
                    print(f"Dropped database: {db_name}")
                except Exception as e:
                    print(f"Warning: Could not drop database {db_name}: {e}")

        users_to_drop = [
            'analytics_user', 'marketing_user', 'customer_service', 'finance_user',
            'product_manager', 'security_auditor', 'developer_user', 'backup_user',
            'temp_contractor', 'old_employee', 'test_account'
        ]

        for user in users_to_drop:
            try:
                cur_postgres.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE usename = %s;", (user,))
                cur_postgres.execute(f"DROP USER IF EXISTS {user};")
            except Exception as e:
                print(f"Warning: Could not drop user {user}: {e}")

        cur_postgres.close()
        conn_postgres.close()

    except Exception as e:
        print(f"Warning: Could not clean up users: {e}")

    try:
        conn = psycopg2.connect(**db_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        print("Setting up security audit environment...")

        # Create business tables with realistic structure

        # 1. User Profiles Table
        cur.execute("""
            DROP TABLE IF EXISTS user_profiles CASCADE;
            CREATE TABLE user_profiles (
                user_id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                first_name VARCHAR(50) NOT NULL,
                last_name VARCHAR(50) NOT NULL,
                phone VARCHAR(20),
                address TEXT,
                city VARCHAR(50),
                state VARCHAR(2),
                zip_code VARCHAR(10),
                date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT true,
                profile_picture_url TEXT,
                bio TEXT
            );
        """)

        # 2. User Credentials Table (sensitive data)
        cur.execute("""
            DROP TABLE IF EXISTS user_credentials CASCADE;
            CREATE TABLE user_credentials (
                credential_id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES user_profiles(user_id) ON DELETE CASCADE,
                password_hash VARCHAR(255) NOT NULL,
                salt VARCHAR(100) NOT NULL,
                login_attempts INTEGER DEFAULT 0,
                last_login TIMESTAMP,
                password_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                password_expires TIMESTAMP,
                is_locked BOOLEAN DEFAULT false,
                two_factor_enabled BOOLEAN DEFAULT false,
                two_factor_secret VARCHAR(32),
                backup_codes TEXT[],
                security_questions JSONB
            );
        """)

        # 3. User Activity Analysis Table (analytics data)
        cur.execute("""
            DROP TABLE IF EXISTS user_stat_analysis CASCADE;
            CREATE TABLE user_stat_analysis (
                analysis_id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES user_profiles(user_id) ON DELETE CASCADE,
                session_id VARCHAR(100),
                page_views INTEGER DEFAULT 0,
                time_spent_minutes INTEGER DEFAULT 0,
                actions_performed JSONB,
                device_info JSONB,
                ip_address INET,
                location_data JSONB,
                referrer_url TEXT,
                conversion_events JSONB,
                analysis_date DATE DEFAULT CURRENT_DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 4. Product Catalog Table
        cur.execute("""
            DROP TABLE IF EXISTS product_catalog CASCADE;
            CREATE TABLE product_catalog (
                product_id SERIAL PRIMARY KEY,
                product_name VARCHAR(100) NOT NULL,
                description TEXT,
                category VARCHAR(50),
                price DECIMAL(10,2) NOT NULL,
                cost DECIMAL(10,2),
                sku VARCHAR(50) UNIQUE,
                inventory_count INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                supplier_info JSONB,
                weight_kg DECIMAL(6,2),
                dimensions JSONB
            );
        """)

        # 5. Order Management Table
        cur.execute("""
            DROP TABLE IF EXISTS order_management CASCADE;
            CREATE TABLE order_management (
                order_id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES user_profiles(user_id),
                order_number VARCHAR(50) UNIQUE NOT NULL,
                order_status VARCHAR(20) DEFAULT 'pending',
                total_amount DECIMAL(12,2) NOT NULL,
                tax_amount DECIMAL(12,2),
                shipping_amount DECIMAL(12,2),
                discount_amount DECIMAL(12,2) DEFAULT 0,
                payment_method VARCHAR(50),
                payment_status VARCHAR(20) DEFAULT 'pending',
                shipping_address JSONB,
                billing_address JSONB,
                order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                shipped_date TIMESTAMP,
                delivered_date TIMESTAMP,
                tracking_number VARCHAR(100)
            );
        """)

        # 6. Financial Transactions Table (sensitive financial data)
        cur.execute("""
            DROP TABLE IF EXISTS financial_transactions CASCADE;
            CREATE TABLE financial_transactions (
                transaction_id SERIAL PRIMARY KEY,
                order_id INTEGER REFERENCES order_management(order_id),
                user_id INTEGER REFERENCES user_profiles(user_id),
                transaction_type VARCHAR(20) NOT NULL,
                amount DECIMAL(12,2) NOT NULL,
                currency VARCHAR(3) DEFAULT 'USD',
                payment_gateway VARCHAR(50),
                gateway_transaction_id VARCHAR(100),
                credit_card_last_four CHAR(4),
                bank_account_last_four CHAR(4),
                transaction_status VARCHAR(20) DEFAULT 'pending',
                processed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fee_amount DECIMAL(8,2),
                refund_amount DECIMAL(12,2) DEFAULT 0,
                notes TEXT
            );
        """)

        # 7. Audit Logs Table (system audit trail)
        cur.execute("""
            DROP TABLE IF EXISTS audit_logs CASCADE;
            CREATE TABLE audit_logs (
                log_id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES user_profiles(user_id),
                action_type VARCHAR(50) NOT NULL,
                table_name VARCHAR(50),
                record_id INTEGER,
                old_values JSONB,
                new_values JSONB,
                ip_address INET,
                user_agent TEXT,
                session_id VARCHAR(100),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN DEFAULT true,
                error_message TEXT
            );
        """)

        print("Created 7 business tables")

        # Create PostgreSQL users with different roles

        # 1. Analytics User - should have read access to analytics data
        cur.execute("CREATE USER analytics_user WITH PASSWORD 'analytics123';")

        # 2. Marketing User - should have read access to user profiles and analytics
        cur.execute("CREATE USER marketing_user WITH PASSWORD 'marketing456';")

        # 3. Customer Service User - should have read/write access to profiles and orders
        cur.execute("CREATE USER customer_service WITH PASSWORD 'service789';")

        # 4. Finance User - should have access to financial data
        cur.execute("CREATE USER finance_user WITH PASSWORD 'finance321';")

        # 5. Product Manager - should have access to product catalog
        cur.execute("CREATE USER product_manager WITH PASSWORD 'product654';")

        # 6. Security Auditor - should have read access to audit logs
        cur.execute("CREATE USER security_auditor WITH PASSWORD 'audit987';")

        # 7. Developer User - should have limited development access
        cur.execute("CREATE USER developer_user WITH PASSWORD 'dev123456';")

        # 8. Backup User - should have read access for backup purposes
        cur.execute("CREATE USER backup_user WITH PASSWORD 'backup789';")

        # 9-11. Dangling users with no proper permissions
        cur.execute("CREATE USER temp_contractor WITH PASSWORD 'temp123';")
        cur.execute("CREATE USER old_employee WITH PASSWORD 'old456';")
        cur.execute("CREATE USER test_account WITH PASSWORD 'test789';")

        print("Created 11 users (8 functional, 3 dangling)")

        # Grant appropriate permissions to each user

        # Analytics User - Read access to analytics and user profiles
        cur.execute("GRANT SELECT ON user_stat_analysis TO analytics_user;")
        cur.execute("GRANT SELECT ON user_profiles TO analytics_user;")

        # Marketing User - Read access to profiles and analytics
        cur.execute("GRANT SELECT ON user_profiles TO marketing_user;")
        cur.execute("GRANT SELECT ON user_stat_analysis TO marketing_user;")
        cur.execute("GRANT SELECT ON product_catalog TO marketing_user;")

        # Customer Service - Read/Write access to profiles and orders
        cur.execute("GRANT SELECT, UPDATE ON user_profiles TO customer_service;")
        cur.execute("GRANT SELECT, INSERT, UPDATE ON order_management TO customer_service;")
        cur.execute("GRANT SELECT ON product_catalog TO customer_service;")

        # Finance User - Access to financial data and orders
        cur.execute("GRANT SELECT ON financial_transactions TO finance_user;")
        cur.execute("GRANT SELECT ON order_management TO finance_user;")
        cur.execute("GRANT SELECT ON user_profiles TO finance_user;")

        # Product Manager - Full access to product catalog
        cur.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON product_catalog TO product_manager;")
        cur.execute("GRANT SELECT ON order_management TO product_manager;")

        # Security Auditor - Read access to audit logs and user credentials
        cur.execute("GRANT SELECT ON audit_logs TO security_auditor;")
        cur.execute("GRANT SELECT ON user_credentials TO security_auditor;")
        cur.execute("GRANT SELECT ON user_profiles TO security_auditor;")

        # Developer - Limited access for development
        cur.execute("GRANT SELECT ON user_profiles TO developer_user;")
        cur.execute("GRANT SELECT ON product_catalog TO developer_user;")

        # Backup User - Read access to most tables for backup
        cur.execute("GRANT SELECT ON user_profiles TO backup_user;")
        cur.execute("GRANT SELECT ON product_catalog TO backup_user;")
        cur.execute("GRANT SELECT ON order_management TO backup_user;")
        cur.execute("GRANT SELECT ON audit_logs TO backup_user;")

        print("Granted initial permissions")

        # Now introduce security gaps by removing some permissions

        # Remove analytics_user's access to user_profiles (creating incomplete access)
        cur.execute("REVOKE SELECT ON user_profiles FROM analytics_user;")

        # Remove marketing_user's access to product_catalog (missing needed access)
        cur.execute("REVOKE SELECT ON product_catalog FROM marketing_user;")

        # Remove finance_user's access to user_profiles (incomplete financial analysis capability)
        cur.execute("REVOKE SELECT ON user_profiles FROM finance_user;")

        # Remove developer_user's access to product_catalog (limited development capability)
        cur.execute("REVOKE SELECT ON product_catalog FROM developer_user;")

        # Remove backup_user's access to order_management (incomplete backup coverage)
        cur.execute("REVOKE SELECT ON order_management FROM backup_user;")

        # Grant sequence permissions where needed
        cur.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO customer_service;")
        cur.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO product_manager;")

        print("Introduced 5 security gaps by revoking permissions")
        print("Environment setup complete!")
        print("\nSecurity issues to find:")
        print("- Users with incomplete permissions for their roles")
        print("- Dangling users with no table access")
        print("- Missing permissions that affect business operations")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"Error setting up environment: {e}")
        sys.exit(1)

if __name__ == "__main__":
    setup_security_environment()
