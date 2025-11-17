Create a gender statistics summary table for the HR team's annual workforce composition report. This is a simple analysis to understand the gender distribution in our employee database.

## Your Task:

**Create the gender statistics table** — build a table called `gender_statistics` in the `employees` schema with these exact columns:

* `gender` (varchar) — gender ('M' or 'F')
* `total_employees` (integer) — total number of employees of this gender
* `current_employees` (integer) — current employees of this gender (have active salary where to_date = '9999-01-01')
* `percentage_of_workforce` (decimal) — percentage of current workforce (current_employees / total current employees * 100)

## Requirements:

1. Calculate total employees by counting all employees of each gender from the `employees` table
2. Calculate current employees by counting employees with active salary records (to_date = '9999-01-01' in the `salaries` table)
3. Calculate the percentage based on current workforce only
4. The table should contain exactly 2 rows (one for 'M' and one for 'F')

This analysis will help HR understand the basic gender composition of our workforce for diversity reporting.
