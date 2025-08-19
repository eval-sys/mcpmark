Conduct a comprehensive security audit to identify PostgreSQL users with insufficient or dangling permissions in a business database environment.

## Your Mission:

You've been hired as a security consultant to audit the PostgreSQL database permissions for a growing e-commerce company. The company has experienced rapid growth and multiple teams have been granted database access over time. However, there's concern that some users may have incomplete permissions for their roles, while others may be "dangling" users with no meaningful access.

## Security Audit Requirements:

1. **Discover the database structure**: Identify all tables and their purposes
2. **Catalog all database users**: Find all non-system users in the database  
3. **Analyze current permissions**: Map each user's table-level permissions
4. **Identify security issues**:
   - Users with no table permissions (dangling users)
   - Users with incomplete permissions for their apparent roles
   - Missing permissions that could affect business operations

## Expected Deliverables:

Your audit must produce findings in a structured format that can be verified. Create a table called `security_audit_findings` with the following structure:

```sql
CREATE TABLE security_audit_findings (
    finding_id SERIAL PRIMARY KEY,
    finding_type VARCHAR(50) NOT NULL, -- 'DANGLING_USER', 'MISSING_PERMISSION', 'ROLE_MISMATCH'
    username VARCHAR(50) NOT NULL,
    table_name VARCHAR(50), -- NULL for dangling users
    missing_permission VARCHAR(20), -- 'SELECT', 'INSERT', 'UPDATE', 'DELETE', NULL for dangling
    business_justification TEXT NOT NULL,
    recommended_action TEXT NOT NULL,
    severity VARCHAR(10) NOT NULL -- 'HIGH', 'MEDIUM', 'LOW'
);
```

## Success Criteria:

Your audit should populate the `security_audit_findings` table with:
- All users that have zero table permissions
- All users missing permissions required for their inferred business role
- Specific actionable recommendations for each finding

Analyze usernames and infer their intended business roles, then determine what permissions they should have based on the available tables and typical business needs.

The verification process will check that your findings correctly identify the actual permission gaps in the system.