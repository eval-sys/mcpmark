#!/bin/bash

# MCP Arena Task Runner
set -e

# Default values
SERVICE="notion"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --service) SERVICE="$2"; shift 2 ;;
        --help)
            cat << EOF
Usage: $0 [--service SERVICE] [PIPELINE_ARGS]

Run MCP Arena tasks in Docker containers.

Options:
    --service SERVICE    MCP service (notion|github|filesystem|playwright|postgres)
                        Default: notion
    
All other arguments are passed directly to the pipeline.

Examples:
    $0 --service notion --models o3 --exp-name test-1 --tasks all
    $0 --service postgres --models gpt-4 --exp-name pg-test --tasks basic_queries
EOF
            exit 0
            ;;
        *) break ;;  # Stop parsing, rest goes to pipeline
    esac
done

# Build image if doesn't exist
if ! docker images mcp-arena:latest -q | grep -q .; then
    echo "Building Docker image..."
    docker build -t mcp-arena:latest .
fi

# Run based on service type
if [ "$SERVICE" = "postgres" ]; then
    # For postgres: use docker-compose for both postgres and task
    echo "Starting PostgreSQL and running task..."
    docker compose run --rm \
        mcp-arena \
        python3 -m pipeline --service postgres "$@"
else
    # For other services: just run the container
    echo "Running $SERVICE task..."
    docker run --rm \
        -v $(pwd)/results:/app/results \
        -v $(pwd)/.mcp_env:/app/.mcp_env:ro \
        $([ -f notion_state.json ] && echo "-v $(pwd)/notion_state.json:/app/notion_state.json:ro") \
        mcp-arena:latest \
        python3 -m pipeline --service "$SERVICE" "$@"
fi