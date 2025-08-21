# Installation and Docker Task Usage Guideline

## Overview

The MCPMark setup supports installation through either pip or MCPMark Docker (recommended) after cloning the code repository.

### Pip Installtion
```bash
pip install -e .
```

The MCPMark Docker setup provides a simple way to run evaluation tasks in isolated containers. PostgreSQL is automatically handled when needed.

## 1. Quick Start

### 1.1 Docker Image

The official Docker image is automatically pulled from Docker Hub on first use.
The image is hosted at: https://hub.docker.com/r/evalsysorg/mcpmark

**Image Management:**
- The scripts automatically download the image when it's not found locally
- To manually update to the latest version:
  ```bash
  docker pull evalsysorg/mcpmark:latest
  ```
- For local development/testing, you can build your own docker:
  ```bash
   # Creates evalsysorg/mcpmark:latest locally
  ./build-docker.sh
  ```

## 2. Running MCP Experiments

### 2.1 Running Individual MCP Experiment 

The `run-task.sh` script provides simplified Docker usage:

```bash
# Run filesystem tasks (filesystem is the default mcp service)
./run-task.sh --models MODEL_NAME --k K

# Run github/notion/postgres/playwright/playwright_webarena with specific task
./run-task.sh --mcp MCPSERVICE --models MODEL_NAME --exp-name EXPNAME --tasks TASK --k K
```

where *MODEL_NAME* refers to the model choice from the supported models (see [Introduction Page](./introduction.md) for more information), *EXPNAME* refers to customized experiment name, *TASK* refers to specific task or task group (see `tasks/` for more information), *K* refers to the time of independent experiments.


Additionally, the `run-benchmark.sh` script evaluates models across all MCP services:

```bash
# Run all services with Docker (recommended)
./run-benchmark.sh --models MODEL --exp-name EXPNAME --docker

# Run specific services
./run-benchmark.sh --models MODEL --exp-name EXPNAME --mcps MCPSERVICES --docker

# Run with parallel execution for faster results
./run-benchmark.sh --models MODEL --exp-name EXPNAME --docker --parallel

# Run locally without Docker
./run-benchmark.sh --models MODEL --exp-name EXPNAME --mcps MCPSERVICES
```

Here *MCPSERVICES* refers to group of MCP services, separated by comma (e.g. *filesystem,postgres*)

The benchmark script:
- Runs all or selected MCP services automatically
- Supports progress tracking and timing
- Generates summary reports and logs
- Supports parallel service execution
- Continues running even if some services fail
- Automatically generates performance dashboards

### Manual Docker Commands

#### For Non-Postgres Services
Suppose Notion is the service:
```bash
# Build the image first
./build-docker.sh

# Run a task
docker run --rm \
  -v $(pwd)/results:/app/results \
  -v $(pwd)/.mcp_env:/app/.mcp_env:ro \
  -v $(pwd)/notion_state.json:/app/notion_state.json:ro \
  evalsysorg/mcpmark:latest \
  python3 -m pipeline --mcp notion --models MODEL --exp-name EXPNAME --tasks TASK --k K
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
  evalsysorg/mcpmark:latest \
  python3 -m pipeline --mcp postgres --models MODEL --exp-name EXPNAME --tasks TASK --k K

# Stop and remove postgres when done
docker stop mcp-postgres && docker rm mcp-postgres
```

## Script Usage

### Benchmark Runner (`run-benchmark.sh`)

```
./run-benchmark.sh --models MODELS --exp-name NAME [OPTIONS]

Required Options:
    --models MODELS      Comma-separated list of models to evaluate
    --exp-name NAME     Experiment name for organizing results

Optional Options:
    --docker            Run tasks in Docker containers (recommended)
    --mcps SERVICES Comma-separated list of services to test
                        Default: filesystem,notion,github,postgres,playwright
    --parallel          Run services in parallel (experimental)
    --timeout SECONDS   Timeout per task in seconds (default: 300)
```

### Individual Task Runner (`run-task.sh`)

```
./run-task.sh [--mcp SERVICE] [PIPELINE_ARGS]

Options:
    --mcp SERVICE    MCP service (notion|github|filesystem|playwright|postgres)
                        Default: filesystem

Environment Variables:
    DOCKER_MEMORY_LIMIT  Memory limit for container (default: 4g)
    DOCKER_CPU_LIMIT     CPU limit for container (default: 2)
    DOCKER_IMAGE_VERSION Docker image tag to use (default: latest)

All other arguments are passed directly to the pipeline command.

Pipeline arguments (see python3 -m pipeline --help):
  --mcp {notion,github,filesystem,playwright,postgres,playwright_webarena}
                        MCP service to use (default: filesystem)
  --models MODELS       Comma-separated list of models to evaluate (e.g., 'o3,k2,gpt-4.1')
  --tasks TASKS         Tasks to run: "all", a category name, or "category/task_name"
  --exp-name EXP_NAME   Experiment name; results are saved under results/<exp-name>/ (default: YYYY-MM-DD-HH-MM-SS)
  --k K                 Number of evaluation runs for pass@k metrics (default: 1)
  --timeout TIMEOUT     Timeout in seconds for each task
  --output-dir OUTPUT_DIR
                        Directory to save results
```

## Docker Benefits

1. **Efficiency**: Only starts necessary containers
2. **Isolation**: Each task runs in a fresh container
3. **Resource Management**: Automatic cleanup of containers and networks
4. **Smart Dependencies**: PostgreSQL only starts for postgres service
5. **Parallel Support**: Can run multiple services simultaneously for faster benchmarks
6. **Comprehensive Testing**: Benchmark script runs all services with one command
7. **Progress Tracking**: Colored output with timing and status information
8. **Automatic Reporting**: Generates summary reports and performance dashboards

## Common Troubleshooting

### Permission Issues
```bash
chmod +x run-task.sh
```

### Docker Build Issues
```bash
# Force rebuild with no cache
./run-task.sh --build --mcp MCPSERVICE --models MODEL_NAME --exp-name EXPNAME --tasks TASK
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

Please refer to [Quick Start](./quickstart.md) for setting up API key for specific model.

## Docker Compose Files

- `docker-compose.yml` - Full stack with postgres (for development/testing)

## Notes

- Results are saved under `./results/<exp-name>/`.
- Each task runs in an ephemeral container.
- Docker image is shared across all tasks.
- PostgreSQL data persists in Docker volume.
