Set up basic database security with role-based access control and Row-Level Security (RLS) for the LEGO database.

## Your Tasks:

### 1. Create Database Role and Permissions

Create a new database role called `theme_analyst` with the following permissions:

* `SELECT` permissions on all reference tables: `lego_themes`, `lego_colors`, `lego_parts`, `lego_part_categories`
* `SELECT` permissions on main data tables: `lego_sets`, `lego_inventories`, `lego_inventory_parts`
* No `INSERT`, `UPDATE`, or `DELETE` permissions on any tables

### 2. Enable Row-Level Security

Enable RLS on the following tables:

* `lego_sets`
* `lego_inventories`
* `lego_inventory_parts`

## Requirements:

- Use `CREATE ROLE` to create the `theme_analyst` role
- Use `GRANT SELECT` statements to assign the appropriate permissions
- Use `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` to enable RLS on each table

## Expected Outcome:

After completing these tasks:
- The `theme_analyst` role should exist with read-only access to specified tables
- Row-Level Security should be enabled (but not yet enforced with policies) on the three main data tables
- The role should have no write permissions on any table

This sets up the foundation for implementing theme-based data isolation policies.
