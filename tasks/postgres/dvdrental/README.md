# DVD Rental Database

A sample database for a DVD rental store.

1. Download the source file:

```
wget https://github.com/robconery/dvdrental/raw/refs/heads/master/dvdrental.tar
```

2. Create the database:

```
CREATE DATABASE dvdrental;
```

3. Navigate to the directory where you downloaded the source file, and restore the database:

```
pg_restore -U <user> -h <hostname> -d dvdrental dvdrental.tar
```

Or with password:

```
PGPASSWORD=<password> pg_restore -U <user> -h <hostname> -d dvdrental dvdrental.tar
```


```
DROP INDEX idx_fk_customer_id;
```