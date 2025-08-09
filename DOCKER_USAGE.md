# Docker Task Runner Usage Guide

## Overview

The MCP Arena Docker setup now supports efficient task execution with smart dependency management. Each task runs in an isolated container, and PostgreSQL is only started when needed.

## Quick Start

### Using the Task Runner Script (Recommended)

The `run-task.sh` script handles all Docker complexity for you:

```bash
# Run notion tasks (no postgres needed)
./run-task.sh --service notion --models o3 --exp-name test-1 --tasks all

# Run postgres tasks (automatically starts postgres)
./run-task.sh --service postgres --models gpt-4 --exp-name pg-test --tasks basic_queries

# Run specific GitHub task
./run-task.sh --service github --models claude-3 --exp-name gh-test --tasks harmony/fix_conflict

# Force rebuild Docker image
./run-task.sh --build --service notion --models o3 --exp-name test-2 --tasks all
```

### Manual Docker Commands

If you prefer manual control:

#### For Non-Postgres Services
```bash
# Build the image
docker build -t mcp-arena:latest .

# Run a task
docker run --rm \
  -v $(pwd)/results:/app/results \
  -v $(pwd)/.mcp_env:/app/.mcp_env:ro \
  -v $(pwd)/notion_state.json:/app/notion_state.json:ro \
  mcp-arena:latest \
  python3 -m pipeline --service notion --models o3 --exp-name test --tasks all
```

#### For Postgres Service
```bash
# The run-task.sh script handles postgres automatically, but if doing manually:

# Start postgres container
docker run -d \
  --name mcp-postgres \
  --network mcp-network \
  -e POSTGRES_DATABASE=postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=123456 \
  ghcr.io/cloudnative-pg/postgresql:17-bookworm

# Run postgres task
docker run --rm \
  --network mcp-network \
  -e POSTGRES_HOST=mcp-postgres \
  -v $(pwd)/results:/app/results \
  -v $(pwd)/.mcp_env:/app/.mcp_env:ro \
  mcp-arena:latest \
  python3 -m pipeline --service postgres --models o3 --exp-name pg-test --tasks all

# Stop and remove postgres when done
docker stop mcp-postgres && docker rm mcp-postgres
```

## Available Services

| Service | Requires Postgres | Description |
|---------|------------------|-------------|
| notion | No | Notion workspace tasks |
| github | No | GitHub repository tasks |
| filesystem | No | File system operations |
| playwright | No | Web automation tasks |
| postgres | Yes | PostgreSQL database tasks |

## Script Options

```
--service SERVICE    MCP service to use (default: notion)
--models MODELS     Comma-separated list of models (required)
--tasks TASKS       Tasks to run: "all", category, or "category/task" (default: all)
--exp-name NAME     Experiment name for results (required)
--timeout SECONDS   Timeout per task (default: 300)
--build            Force rebuild Docker image
--no-cleanup       Don't cleanup containers after completion
--help             Show help message
```

## Benefits

1. **Efficiency**: Only starts necessary containers
2. **Isolation**: Each task runs in a fresh container
3. **Resource Management**: Automatic cleanup of containers and networks
4. **Smart Dependencies**: PostgreSQL only starts for postgres service
5. **Parallel Support**: Can run multiple non-postgres tasks simultaneously

## Troubleshooting

### Permission Issues
```bash
chmod +x run-task.sh
```

### Docker Build Issues
```bash
# Force rebuild with no cache
./run-task.sh --build --service notion --models o3 --exp-name test --tasks all
```

### PostgreSQL Connection Issues
```bash
# Check if postgres is running
docker ps | grep postgres

# View postgres logs
docker logs mcp-postgres-task
```

### Cleanup Stuck Resources
```bash
# Stop all containers
docker stop $(docker ps -q)

# Remove task network
docker network rm mcp-task-network

# Remove postgres data volume (careful!)
docker volume rm mcp-postgres-data
```

## Environment Variables

Create `.mcp_env` file with your credentials:
```env
# Service credentials
SOURCE_NOTION_API_KEY=your-key
EVAL_NOTION_API_KEY=your-key
GITHUB_TOKEN=your-token
POSTGRES_PASSWORD=your-password

# Model API keys
OPENAI_API_KEY=your-key
ANTHROPIC_API_KEY=your-key
# ... etc
```

## Docker Compose Files

- `docker-compose.yml` - Full stack with postgres (for development/testing)

## Notes

- Results are saved to `./results/<exp-name>/`
- Each task runs in an ephemeral container
- Docker image is shared across all tasks
- PostgreSQL data persists in Docker volume