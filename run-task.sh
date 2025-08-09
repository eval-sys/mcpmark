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

# For postgres service, ensure PostgreSQL container is running
if [ "$SERVICE" = "postgres" ]; then
    if ! docker ps --format '{{.Names}}' | grep -q "^mcp-postgres$"; then
        echo "Starting PostgreSQL container..."
        docker run -d \
            --name mcp-postgres \
            -e POSTGRES_DATABASE=postgres \
            -e POSTGRES_USER=postgres \
            -e POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-123456}" \
            -p 5432:5432 \
            ghcr.io/cloudnative-pg/postgresql:17-bookworm
        
        echo "Waiting for PostgreSQL to be ready..."
        sleep 5
    fi
    
    # Run with POSTGRES_HOST pointing to host machine
    docker run --rm \
        -e POSTGRES_HOST=host.docker.internal \
        -v $(pwd)/results:/app/results \
        -v $(pwd)/.mcp_env:/app/.mcp_env:ro \
        $([ -f notion_state.json ] && echo "-v $(pwd)/notion_state.json:/app/notion_state.json:ro") \
        mcp-arena:latest \
        python3 -m pipeline --service "$SERVICE" "$@"
else
    # For other services: just run the container
    docker run --rm \
        -v $(pwd)/results:/app/results \
        -v $(pwd)/.mcp_env:/app/.mcp_env:ro \
        $([ -f notion_state.json ] && echo "-v $(pwd)/notion_state.json:/app/notion_state.json:ro") \
        mcp-arena:latest \
        python3 -m pipeline --service "$SERVICE" "$@"
fi