#!/bin/bash

# MCP Arena Task Runner
set -e

# Default values
SERVICE="notion"
NETWORK_NAME="mcp-network"
POSTGRES_CONTAINER="mcp-postgres"

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

# Check if Docker image exists
if ! docker images mcp-arena:latest -q | grep -q .; then
    echo "Error: Docker image 'mcp-arena:latest' not found!"
    echo "Please build it first by running: ./build-docker.sh"
    exit 1
fi

# Create network if doesn't exist
if ! docker network ls --format '{{.Name}}' | grep -q "^${NETWORK_NAME}$"; then
    echo "Creating Docker network: $NETWORK_NAME"
    docker network create $NETWORK_NAME
fi

# For postgres service, ensure PostgreSQL container is running
if [ "$SERVICE" = "postgres" ]; then
    if ! docker ps --format '{{.Names}}' | grep -q "^${POSTGRES_CONTAINER}$"; then
        echo "Starting PostgreSQL container..."
        docker run -d \
            --name $POSTGRES_CONTAINER \
            --network $NETWORK_NAME \
            -e POSTGRES_DB=postgres \
            -e POSTGRES_USER=postgres \
            -e POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-123456}" \
            postgres:15
        
        echo "Waiting for PostgreSQL to be ready..."
        for i in {1..10}; do
            if docker exec $POSTGRES_CONTAINER pg_isready -U postgres >/dev/null 2>&1; then
                echo "PostgreSQL is ready!"
                break
            fi
            sleep 1
        done
    else
        echo "PostgreSQL container already running"
    fi
    
    # Run task with network connection to postgres
    docker run --rm \
        --network $NETWORK_NAME \
        -e POSTGRES_HOST=$POSTGRES_CONTAINER \
        -e POSTGRES_PORT=5432 \
        -e POSTGRES_USERNAME=postgres \
        -e POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-123456}" \
        -e POSTGRES_DATABASE=postgres \
        -v $(pwd)/results:/app/results \
        -v $(pwd)/.mcp_env:/app/.mcp_env:ro \
        $([ -f notion_state.json ] && echo "-v $(pwd)/notion_state.json:/app/notion_state.json:ro") \
        mcp-arena:latest \
        python3 -m pipeline --service "$SERVICE" "$@"
else
    # For other services: just run the container (no network needed)
    docker run --rm \
        -v $(pwd)/results:/app/results \
        -v $(pwd)/.mcp_env:/app/.mcp_env:ro \
        $([ -f notion_state.json ] && echo "-v $(pwd)/notion_state.json:/app/notion_state.json:ro") \
        mcp-arena:latest \
        python3 -m pipeline --service "$SERVICE" "$@"
fi

echo "Task completed!"