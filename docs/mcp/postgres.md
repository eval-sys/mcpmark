# PostgreSQL

This guide walks you through preparing your PostgreSQL environment for MCPMark evaluation.

## 1. Setup PostgreSQL Environment

### 1.1 Start PostgreSQL with Docker

1. **Run PostgreSQL Container**
   Start a PostgreSQL instance using Docker:
   ```bash
   docker run -d \
     --name mcpmark-postgres \
     -e POSTGRES_PASSWORD=mysecretpassword \
     -e POSTGRES_USER=postgres \
     -p 5432:5432 \
     postgres
   ```

2. **Verify Container is Running**
   ```bash
   docker ps | grep mcpmark-postgres
   ```

---

### 1.2 Import Sample Databases

1. **Download Database Backups**
   Download the backup files from the provided source and place them in `./postgres_state/` directory.

2. **Create Databases and Restore from Backups**
   ```bash
   # Set the password environment variable
   export PGPASSWORD=mysecretpassword
   
   # Create and restore each database
   createdb -h localhost -U postgres employees
   pg_restore -h localhost -U postgres -d employees -v ./postgres_state/employees.backup
   
   createdb -h localhost -U postgres chinook
   pg_restore -h localhost -U postgres -d chinook -v ./postgres_state/chinook.backup
   
   createdb -h localhost -U postgres dvdrental
   pg_restore -h localhost -U postgres -d dvdrental -v ./postgres_state/dvdrental.backup
   
   createdb -h localhost -U postgres sports
   pg_restore -h localhost -U postgres -d sports -v ./postgres_state/sports.backup
   
   # Add other databases as needed
   ```

3. **Verify Databases are Imported**
   ```bash
   # List all databases
   PGPASSWORD=mysecretpassword psql -h localhost -U postgres -c "\l"
   ```

---

## 2. Configure Environment Variables

Configure environment variables: make sure the following enservice credentials are added in `.mcp_env`:
```env
## PostgreSQL Configuration
POSTGRES_HOST="localhost"
POSTGRES_PORT="5432"
POSTGRES_USER="postgres"
POSTGRES_PASSWORD="mysecretpassword"
```


## 3. Verify Connection

Verify the PostgreSQL setup is working correctly:

```bash
# Test connection using psql
PGPASSWORD=mysecretpassword psql -h localhost -U postgres -c "SELECT version();"
```


## 4. Common Operations

### Stop PostgreSQL Container
```bash
docker stop mcpmark-postgres
```

### Start PostgreSQL Container
```bash
docker start mcpmark-postgres
```

### Remove PostgreSQL Container (Clean Setup)
```bash
docker stop mcpmark-postgres
docker rm mcpmark-postgres
```

### Access PostgreSQL Shell
```bash
PGPASSWORD=mysecretpassword psql -h localhost -U postgres
```

## 5. Running Postgres Experiment

For single task or task group, run 
```bash
python -m pipeline --exp-name EXPNAME --mcp postgres --tasks POSTGRESTASK --models MODEL
```
Here *EXPNAME* refers to customized experiment name, *POSTGRESTASK* refers to the postgres task or task group selected (see `tasks/` for specific task information), *MODEL* refers to the selected model (see [Introduction Page](../introduction.md) for model supported), *K* refers to the time of independent experiments.


## 6. Troubleshooting

### Port Already in Use
If port 5432 is already in use, you can use a different port:
```bash
docker run -d \
   ```bash
   docker run -d \
     --name mcpmark-postgres \
     -e POSTGRES_PASSWORD=mysecretpassword \
     -e POSTGRES_USER=postgres \
     -p 5433:5432 \
     postgres
   ```
Remember to update `POSTGRES_PORT="5433"` in your `.mcp_env` file.

### Connection Refused
Ensure the Docker container is running and the port mapping is correct:
```bash
docker ps
docker logs mcpmark-postgres
```