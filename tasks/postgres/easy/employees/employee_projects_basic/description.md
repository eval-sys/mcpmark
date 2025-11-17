Create and manage a basic employee projects table to track company projects. The IT team needs you to build the database table structure and populate it with initial project data.

## Your Tasks:

1. **Create the employee_projects table** — build a new table in the `employees` schema:

   **Table: `employee_projects`**
   * `project_id` (integer, primary key, auto-increment)
   * `project_name` (varchar(100), not null)
   * `start_date` (date, not null)
   * `end_date` (date)
   * `budget` (decimal(10,2))
   * `status` (varchar(20), default 'active')

2. **Insert exactly this initial data into `employee_projects`**:
   * Project 1: name='Database Modernization', start_date='2024-01-15', end_date='2024-06-30', budget=250000.00, status='active'
   * Project 2: name='Employee Portal Upgrade', start_date='2024-02-01', end_date='2024-05-15', budget=180000.00, status='active'
   * Project 3: name='HR Analytics Dashboard', start_date='2023-11-01', end_date='2024-01-31', budget=120000.00, status='active'

This will establish the basic project tracking foundation for the company.
