# Lego database

A dataset containing information about various LEGO sets, their themes, parts, colors, and other associated data.

1. Create a `lego` database:

    ```sql
    CREATE DATABASE lego;
    ```

2. Download the source file:

    ```bash
    wget https://raw.githubusercontent.com/neondatabase/postgres-sample-dbs/main/lego.sql
    ```

3. Navigate to the directory where you downloaded the source file, and run the following command:

    ```bash
    psql -d "postgres://<user>:<password>@<hostname>/lego" -f lego.sql
    ```

4. Connect to the `lego` database:

    ```bash
    psql postgres://<user>:<password>@<hostname>/lego
    ```

5. Find the top 5 LEGO themes by the number of sets:

    ```sql
    SELECT lt.name AS theme_name, COUNT(ls.set_num) AS number_of_sets
    FROM lego_themes lt
    JOIN lego_sets ls ON lt.id = ls.theme_id
    GROUP BY lt.name
    ORDER BY number_of_sets DESC
    LIMIT 5;
    ```