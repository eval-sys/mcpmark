# Chinook database

A sample database for a digital media store, including tables for artists, albums, media tracks, invoices, customers, and more.

1. Create a chinook database:

```
CREATE DATABASE chinook;
```

2. Download the source file:

```
wget https://raw.githubusercontent.com/neondatabase/postgres-sample-dbs/main/chinook.sql
```

3. Navigate to the directory where you downloaded the source file, and run the following command:

```
psql -d "postgres://<user>:<password>@<hostname>/chinook" -f chinook.sql
```
