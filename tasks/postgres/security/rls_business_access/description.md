Implement and debug Row Level Security (RLS) policies for a multi-tenant business application with complex organizational hierarchies.

## Your Mission:

You're tasked with implementing Row Level Security for a SaaS business platform that serves multiple organizations. The platform has a complex permission model where users can belong to multiple organizations with different roles, and access to data must be strictly controlled based on organizational membership and user roles.

## Business Context:

The platform manages:
- **User Profiles**: Individual user accounts that can belong to multiple organizations
- **User Credentials**: Sensitive authentication data (passwords, tokens, session data)
- **Organization Profiles**: Company/team information with different subscription tiers
- **Organization Membership**: User-organization relationships with roles (owner, admin, member, viewer)
- **Projects**: Work items that belong to organizations with team assignments
- **Project Assignments**: User assignments to specific projects with role-based access

## RLS Requirements:

### 1. User Profile Access Rules:
- Users can read/write their own profile data
- Organization admins can read basic profile info (name, email) of their members
- Organization owners can read full profile info of their members
- When listing users, non-owners should only see basic fields (name, email, role)

### 2. Organization Access Rules:
- Users can only see organizations they belong to
- Only owners and admins can modify organization details
- Billing information is only visible to owners
- Member counts and basic info visible to all members

### 3. Project Access Rules:
- Users can only see projects from organizations they belong to
- Project visibility depends on user's role in that organization:
  - Owners/Admins: All projects in their organizations
  - Members: Only projects they're assigned to
  - Viewers: Only public projects in their organizations

### 4. Sensitive Data Protection:
- User credentials are only accessible by the user themselves
- Organization billing data only accessible by owners
- Project financial data only accessible by owners and admins

## Technical Challenges:

You'll need to:

1. **Set up the schema** with proper foreign key relationships
2. **Create RLS policies** that handle multi-table joins efficiently
3. **Handle role hierarchy** where owners > admins > members > viewers
4. **Optimize performance** as RLS can impact query performance
5. **Debug permission issues** where users report they can't access data they should be able to see

## Expected Deliverables:

Create RLS policies that properly restrict access while maintaining performance. Your implementation should:

1. Enable RLS on all relevant tables
2. Create policies for SELECT, INSERT, UPDATE, DELETE operations
3. Handle the complex organizational hierarchy correctly
4. Provide different levels of data visibility (full vs. partial field access)
5. Create helper functions to check user permissions efficiently

## Test Scenarios:

Your RLS implementation will be tested with scenarios including:
- Cross-organization data isolation
- Role-based access within organizations  
- Partial field visibility for listing operations
- Performance with complex multi-table queries
- Edge cases like users with multiple roles across organizations

## Success Criteria:

- Users can only access data from organizations they belong to
- Role-based restrictions work correctly within organizations
- Sensitive fields are properly protected
- Performance remains acceptable for typical business queries
- No data leakage between organizations or unauthorized users

The verification system will test your RLS policies with multiple users, organizations, and permission scenarios to ensure complete data isolation and proper access control.