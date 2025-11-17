Create an executive department summary view to provide quick insights into departmental metrics for leadership dashboards. This view will consolidate key department statistics in one easily accessible place.

## Your Task:

**Create the executive department summary view** — build a materialized view called `exec_department_summary` in the `employees` schema with these exact columns:

* `department_name` (varchar) — department name
* `total_employees` (integer) — current active employee count (employees with active salary where to_date = '9999-01-01')
* `avg_salary` (decimal) — average current salary for active employees
* `total_payroll` (bigint) — total monthly payroll cost (sum of all current salaries in the department)
* `manager_name` (varchar) — current department manager's full name (first_name and last_name concatenated)

## Requirements:

1. Use materialized view to cache results for better performance
2. Join the following tables:
   - `departments` - for department information
   - `dept_emp` - for employee-department relationships
   - `employees` - for employee details
   - `salaries` - for current salary information
   - `dept_manager` - for current manager information
3. Only include current active employees (those with to_date = '9999-01-01' in both `dept_emp` and `salaries`)
4. Only include current managers (to_date = '9999-01-01' in `dept_manager`)
5. Order results by department_name

## After Creation:

Refresh the materialized view to populate it with current data.

This view will provide executives with a real-time snapshot of departmental workforce metrics and costs.
