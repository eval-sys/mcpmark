#!/bin/bash

# MCP Arena Task Runner
# Runs evaluation tasks in Docker containers with smart dependency management

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
SERVICE="notion"
DOCKER_IMAGE="mcp-arena:latest"
NETWORK_NAME="mcp-task-network"
POSTGRES_CONTAINER="mcp-postgres-task"

# Function to print colored messages
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Run MCP Arena evaluation tasks in Docker containers.

Options:
    --service SERVICE       MCP service to use (notion, github, filesystem, playwright, postgres)
                           Default: notion
    --models MODELS        Comma-separated list of models to evaluate (required)
    --tasks TASKS          Tasks to run: "all", category name, or "category/task_name"
                           Default: all
    --exp-name NAME        Experiment name for results (required)
    --timeout SECONDS      Timeout in seconds for each task
                           Default: 300
    --build                Force rebuild of Docker image
    --no-cleanup           Don't cleanup containers after completion
    --help                 Show this help message

Examples:
    # Run all notion tasks
    $0 --service notion --models o3 --exp-name test-1 --tasks all

    # Run postgres tasks (automatically starts postgres container)
    $0 --service postgres --models gpt-4 --exp-name pg-test --tasks basic_queries

    # Run specific task with multiple models
    $0 --service github --models "o3,gpt-4,claude-3" --exp-name github-test --tasks harmony/fix_conflict

EOF
    exit 0
}

# Parse command line arguments
FORCE_BUILD=false
NO_CLEANUP=false
MODELS=""
TASKS="all"
EXP_NAME=""
TIMEOUT=300

while [[ $# -gt 0 ]]; do
    case $1 in
        --service)
            SERVICE="$2"
            shift 2
            ;;
        --models)
            MODELS="$2"
            shift 2
            ;;
        --tasks)
            TASKS="$2"
            shift 2
            ;;
        --exp-name)
            EXP_NAME="$2"
            shift 2
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --build)
            FORCE_BUILD=true
            shift
            ;;
        --no-cleanup)
            NO_CLEANUP=true
            shift
            ;;
        --help)
            usage
            ;;
        *)
            print_error "Unknown option: $1"
            usage
            ;;
    esac
done

# Validate required arguments
if [ -z "$MODELS" ]; then
    print_error "Missing required argument: --models"
    usage
fi

if [ -z "$EXP_NAME" ]; then
    print_error "Missing required argument: --exp-name"
    usage
fi

# Validate service
if [[ ! "$SERVICE" =~ ^(notion|github|filesystem|playwright|postgres)$ ]]; then
    print_error "Invalid service: $SERVICE"
    usage
fi

# Function to build Docker image
build_image() {
    print_info "Building Docker image..."
    
    if [ "$FORCE_BUILD" = true ]; then
        docker build -t $DOCKER_IMAGE . --no-cache
    else
        docker build -t $DOCKER_IMAGE .
    fi
    
    print_success "Docker image built: $DOCKER_IMAGE"
}

# Function to create Docker network
create_network() {
    if ! docker network inspect $NETWORK_NAME >/dev/null 2>&1; then
        print_info "Creating Docker network: $NETWORK_NAME"
        docker network create $NETWORK_NAME
    else
        print_info "Using existing network: $NETWORK_NAME"
    fi
}

# Function to start PostgreSQL container
start_postgres() {
    print_info "Starting PostgreSQL container..."
    
    # Check if postgres container already exists
    if docker ps -a --format '{{.Names}}' | grep -q "^${POSTGRES_CONTAINER}$"; then
        # Check if it's running
        if docker ps --format '{{.Names}}' | grep -q "^${POSTGRES_CONTAINER}$"; then
            print_info "PostgreSQL container already running"
        else
            print_info "Starting existing PostgreSQL container"
            docker start $POSTGRES_CONTAINER
        fi
    else
        # Create and start new postgres container
        docker run -d \
            --name $POSTGRES_CONTAINER \
            --network $NETWORK_NAME \
            -e POSTGRES_DATABASE=postgres \
            -e POSTGRES_USER=postgres \
            -e POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-123456}" \
            -v mcp-postgres-data:/var/lib/postgresql/data \
            ghcr.io/cloudnative-pg/postgresql:17-bookworm
    fi
    
    # Wait for postgres to be healthy
    print_info "Waiting for PostgreSQL to be ready..."
    for i in {1..30}; do
        if docker exec $POSTGRES_CONTAINER pg_isready -U postgres >/dev/null 2>&1; then
            print_success "PostgreSQL is ready"
            return 0
        fi
        sleep 1
    done
    
    print_error "PostgreSQL failed to start"
    return 1
}

# Function to stop PostgreSQL container
stop_postgres() {
    if [ "$NO_CLEANUP" = false ] && [ "$SERVICE" = "postgres" ]; then
        print_info "Stopping PostgreSQL container..."
        docker stop $POSTGRES_CONTAINER >/dev/null 2>&1 || true
        docker rm $POSTGRES_CONTAINER >/dev/null 2>&1 || true
    fi
}

# Function to run task in container
run_task() {
    local container_name="mcp-task-$(date +%s)-$$"
    
    print_info "Running task in container: $container_name"
    print_info "Service: $SERVICE | Models: $MODELS | Tasks: $TASKS"
    
    # Prepare Docker run command
    local docker_cmd="docker run --rm"
    docker_cmd="$docker_cmd --name $container_name"
    docker_cmd="$docker_cmd --network $NETWORK_NAME"
    
    # Mount required volumes
    docker_cmd="$docker_cmd -v $(pwd)/results:/app/results"
    docker_cmd="$docker_cmd -v $(pwd)/.mcp_env:/app/.mcp_env:ro"
    
    # Mount notion_state.json if it exists
    if [ -f "notion_state.json" ]; then
        docker_cmd="$docker_cmd -v $(pwd)/notion_state.json:/app/notion_state.json:ro"
    fi
    
    # Set environment variables
    if [ "$SERVICE" = "postgres" ]; then
        docker_cmd="$docker_cmd -e POSTGRES_HOST=$POSTGRES_CONTAINER"
    fi
    
    # Add the image and command
    docker_cmd="$docker_cmd $DOCKER_IMAGE"
    docker_cmd="$docker_cmd python3 -m pipeline"
    docker_cmd="$docker_cmd --service $SERVICE"
    docker_cmd="$docker_cmd --models $MODELS"
    docker_cmd="$docker_cmd --tasks \"$TASKS\""
    docker_cmd="$docker_cmd --exp-name $EXP_NAME"
    docker_cmd="$docker_cmd --timeout $TIMEOUT"
    
    # Execute the command
    print_info "Executing: $docker_cmd"
    eval $docker_cmd
    
    print_success "Task completed successfully"
}

# Function to cleanup
cleanup() {
    if [ "$NO_CLEANUP" = false ]; then
        print_info "Cleaning up..."
        
        # Stop postgres if it was started for this task
        if [ "$SERVICE" = "postgres" ]; then
            stop_postgres
        fi
        
        # Remove network if no containers are using it
        if docker network inspect $NETWORK_NAME >/dev/null 2>&1; then
            local containers=$(docker network inspect $NETWORK_NAME --format '{{len .Containers}}')
            if [ "$containers" = "0" ]; then
                print_info "Removing network: $NETWORK_NAME"
                docker network rm $NETWORK_NAME >/dev/null 2>&1 || true
            fi
        fi
    fi
}

# Trap to ensure cleanup on exit
trap cleanup EXIT

# Main execution
main() {
    print_info "Starting MCP Arena Task Runner"
    print_info "Configuration:"
    echo "  Service: $SERVICE"
    echo "  Models: $MODELS"
    echo "  Tasks: $TASKS"
    echo "  Experiment: $EXP_NAME"
    echo "  Timeout: $TIMEOUT seconds"
    
    # Check if .mcp_env exists
    if [ ! -f ".mcp_env" ]; then
        print_warning ".mcp_env file not found. Make sure to set environment variables."
    fi
    
    # Build Docker image if needed
    if ! docker images --format '{{.Repository}}:{{.Tag}}' | grep -q "^${DOCKER_IMAGE}$" || [ "$FORCE_BUILD" = true ]; then
        build_image
    else
        print_info "Using existing Docker image: $DOCKER_IMAGE"
    fi
    
    # Create Docker network
    create_network
    
    # Start PostgreSQL if needed
    if [ "$SERVICE" = "postgres" ]; then
        start_postgres
    fi
    
    # Run the task
    run_task
    
    print_success "All tasks completed!"
}

# Run main function
main