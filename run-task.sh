#!/bin/bash

# MCPMark Task Runner
# Enable strict error handling
set -euo pipefail

# Default values
SERVICE="filesystem"
NETWORK_NAME="mcp-network"
POSTGRES_CONTAINER="mcp-postgres"

# Resource limits (can be overridden by environment variables)
DOCKER_MEMORY_LIMIT="${DOCKER_MEMORY_LIMIT:-4g}"
DOCKER_CPU_LIMIT="${DOCKER_CPU_LIMIT:-2}"

# Cleanup function
cleanup() {
    if [ "${SERVICE:-}" = "postgres" ]; then
        if docker ps --format '{{.Names}}' | grep -q "^${POSTGRES_CONTAINER}$"; then
            echo "Cleaning up PostgreSQL container..."
            docker stop "$POSTGRES_CONTAINER" >/dev/null 2>&1 || true
            docker rm "$POSTGRES_CONTAINER" >/dev/null 2>&1 || true
        fi
    fi
}

# Set up cleanup on exit
trap cleanup EXIT

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --mcp) SERVICE="$2"; shift 2 ;;
        --help)
            cat << EOF
Usage: $0 [--mcp SERVICE] [PIPELINE_ARGS]

Run MCPMark tasks in Docker containers.

Options:
    --mcp SERVICE    MCP service (notion|github|filesystem|playwright|postgres)
                        Default: filesystem

Environment Variables:
    DOCKER_MEMORY_LIMIT  Memory limit for container (default: 4g)
    DOCKER_CPU_LIMIT     CPU limit for container (default: 2)
    DOCKER_IMAGE_VERSION Docker image tag to use (default: latest)

All other arguments are passed directly to the pipeline.

Examples:
    $0 --mcp notion --models o3 --exp-name test-1 --tasks all
    $0 --mcp postgres --models gpt-4 --exp-name pg-test --tasks basic_queries
EOF
            exit 0
            ;;
        *) break ;;  # Stop parsing, rest goes to pipeline
    esac
done

# Docker image tag can be overridden by environment variable
DOCKER_IMAGE_REPO="evalsysorg/mcpmark"
DOCKER_IMAGE_VERSION="${DOCKER_IMAGE_VERSION:-latest}"
DOCKER_IMAGE="${DOCKER_IMAGE_REPO}:${DOCKER_IMAGE_VERSION}"

# Check if Docker image exists locally, pull only if not found
if ! docker image inspect "$DOCKER_IMAGE" >/dev/null 2>&1; then
    echo "Docker image not found locally, pulling from Docker Hub..."
    docker pull "$DOCKER_IMAGE" || {
        echo "Error: Failed to pull Docker image from Docker Hub"
        echo "Please check your internet connection or Docker Hub access"
        exit 1
    }
else
    echo "Using local Docker image: $DOCKER_IMAGE"
fi

# Check if .mcp_env exists (warn but don't fail)
if [ ! -f .mcp_env ]; then
    echo "Warning: .mcp_env file not found. Some tasks may fail without API credentials."
fi

# Create network if doesn't exist
if ! docker network ls --format '{{.Name}}' | grep -q "^${NETWORK_NAME}$"; then
    echo "Creating Docker network: $NETWORK_NAME"
    docker network create "$NETWORK_NAME" || {
        echo "Error: Failed to create Docker network"
        exit 1
    }
fi

# Service-specific configurations
if [ "$SERVICE" = "postgres" ]; then
    # For postgres service, ensure PostgreSQL container is running
    if ! docker ps --format '{{.Names}}' | grep -q "^${POSTGRES_CONTAINER}$"; then
        echo "Starting PostgreSQL container..."
        docker run -d \
            --name "$POSTGRES_CONTAINER" \
            --network "$NETWORK_NAME" \
            -e POSTGRES_DATABASE=postgres \
            -e POSTGRES_USER=postgres \
            -e POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-password}" \
            pgvector/pgvector:0.8.0-pg17-bookworm

        echo "Waiting for PostgreSQL to be ready..."
        for i in {1..10}; do
            if docker exec "$POSTGRES_CONTAINER" pg_isready -U postgres >/dev/null 2>&1; then
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
        --memory="$DOCKER_MEMORY_LIMIT" \
        --cpus="$DOCKER_CPU_LIMIT" \
        --network "$NETWORK_NAME" \
        -e POSTGRES_HOST="$POSTGRES_CONTAINER" \
        -e POSTGRES_PORT=5432 \
        -e POSTGRES_USERNAME=postgres \
        -e POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-password}" \
        -e POSTGRES_DATABASE=postgres \
        -v "$(pwd)/results:/app/results" \
        -v "$(pwd)/postgres_state:/app/postgres_state" \
        $([ -f .mcp_env ] && echo "-v $(pwd)/.mcp_env:/app/.mcp_env:ro") \
        "$DOCKER_IMAGE" \
        python3 -m pipeline --mcp "$SERVICE" "$@"
elif [ "$SERVICE" = "filesystem" ]; then
    # For filesystem service, mount test_environments
    docker run --rm \
        --memory="$DOCKER_MEMORY_LIMIT" \
        --cpus="$DOCKER_CPU_LIMIT" \
        -v "$(pwd)/results:/app/results" \
        -v "$(pwd)/test_environments:/app/test_environments" \
        $([ -f .mcp_env ] && echo "-v $(pwd)/.mcp_env:/app/.mcp_env:ro") \
        "$DOCKER_IMAGE" \
        python3 -m pipeline --mcp "$SERVICE" "$@"
else
    # For other services (notion, github, playwright, etc.)
    docker run --rm \
        --memory="$DOCKER_MEMORY_LIMIT" \
        --cpus="$DOCKER_CPU_LIMIT" \
        -v "$(pwd)/results:/app/results" \
        -v "$(pwd)/test_environments:/app/test_environments" \
        $([ -f .mcp_env ] && echo "-v $(pwd)/.mcp_env:/app/.mcp_env:ro") \
        $([ -f notion_state.json ] && echo "-v $(pwd)/notion_state.json:/app/notion_state.json:ro") \
        "$DOCKER_IMAGE" \
        python3 -m pipeline --mcp "$SERVICE" "$@"
fi

echo "Task completed!"
