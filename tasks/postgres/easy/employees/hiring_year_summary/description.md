Create a hiring year summary table to help HR track employee retention trends over the years. This analysis shows how many employees were hired each year and how many are still with the company.

## Your Task:

**Create the hiring year summary table** — build a table called `hiring_year_summary` in the `employees` schema with these exact columns:

* `hire_year` (integer) — year employees were hired
* `employees_hired` (integer) — number of employees hired that year
* `still_employed` (integer) — how many from that year are still employed (have active salary where to_date = '9999-01-01')
* `retention_rate` (decimal) — percentage still employed (still_employed / employees_hired * 100)

## Requirements:

1. Extract the hire year from the `hire_date` column in the `employees` table
2. Count total employees hired in each year
3. Determine which employees are still employed by checking for active salary records (to_date = '9999-01-01' in the `salaries` table)
4. Order results by hire_year in ascending order

This analysis will help HR understand retention patterns and identify years with particularly high or low retention rates.
