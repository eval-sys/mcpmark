# Employees database

A dataset containing details about employees, their departments, salaries, and more.

1. Create the database and schema:

```
CREATE DATABASE employees;
\c employees
CREATE SCHEMA employees;
```
2. Download the source file:

```
wget https://raw.githubusercontent.com/neondatabase/postgres-sample-dbs/main/employees.sql.gz
```

3. Navigate to the directory where you downloaded the source file, and run the following command:

```
pg_restore -d postgres://<user>:<password>@<hostname>/employees -Fc employees.sql.gz -c -v --no-owner --no-privileges
```

Database objects are created in the `employees` schema rather than the public schema.