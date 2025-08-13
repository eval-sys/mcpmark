#!/bin/bash

# MCP Arena Full Benchmark Runner
# Runs all tasks across all MCP services for comprehensive model evaluation

set -e

# Default values
MODELS=""
EXP_NAME=""
USE_DOCKER=false
SERVICES="filesystem,notion,github,postgres,playwright"
PARALLEL=false
TIMEOUT=300

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --models)
            MODELS="$2"
            shift 2
            ;;
        --exp-name)
            EXP_NAME="$2"
            shift 2
            ;;
        --docker)
            USE_DOCKER=true
            shift
            ;;
        --services)
            SERVICES="$2"
            shift 2
            ;;
        --parallel)
            PARALLEL=true
            shift
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --help)
            cat << EOF
Usage: $0 --models MODELS --exp-name NAME [OPTIONS]

Run comprehensive benchmark across all MCP services.

Required Options:
    --models MODELS      Comma-separated list of models to evaluate
                        (e.g., "o3,gpt-4.1,claude-4-sonnet")
    --exp-name NAME     Experiment name for organizing results

Optional Options:
    --docker            Run tasks in Docker containers (recommended)
    --services SERVICES Comma-separated list of services to test
                        Default: filesystem,notion,github,postgres,playwright
    --parallel          Run services in parallel (experimental)
    --timeout SECONDS   Timeout per task in seconds (default: 300)

Examples:
    # Run all services with Docker
    $0 --models o3,gpt-4.1 --exp-name benchmark-1 --docker

    # Run specific services locally
    $0 --models o3 --exp-name test-1 --services filesystem,postgres

    # Run with parallel execution
    $0 --models claude-4 --exp-name parallel-test --docker --parallel

EOF
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Validate required arguments
if [ -z "$MODELS" ]; then
    print_error "Error: --models is required"
    exit 1
fi

if [ -z "$EXP_NAME" ]; then
    print_error "Error: --exp-name is required"
    exit 1
fi

# Check prerequisites
if [ "$USE_DOCKER" = true ]; then
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        exit 1
    fi
    
    # Always use Docker Hub image
    DOCKER_IMAGE="evalsysorg/mcpmark:latest"
    
    # Check if Docker image exists locally, pull only if not found
    if ! docker image inspect "$DOCKER_IMAGE" >/dev/null 2>&1; then
        print_status "Docker image not found locally, pulling from Docker Hub..."
        docker pull "$DOCKER_IMAGE" || {
            print_error "Failed to pull Docker image from Docker Hub"
            exit 1
        }
    else
        print_status "Using local Docker image: $DOCKER_IMAGE"
    fi
else
    # Check Python installation
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        exit 1
    fi
    
    # Check if dependencies are installed
    if ! python3 -c "import src.evaluator" 2>/dev/null; then
        print_warning "Python dependencies not installed"
        echo "Installing dependencies..."
        pip install -e . || {
            print_error "Failed to install dependencies"
            exit 1
        }
    fi
fi

# Check .mcp_env file
if [ ! -f .mcp_env ]; then
    print_warning ".mcp_env file not found. Some tasks may fail without API credentials."
    echo "Create one from .mcp_env.example: cp .mcp_env.example .mcp_env"
fi

# Convert comma-separated services to array
IFS=',' read -ra SERVICE_ARRAY <<< "$SERVICES"

# Summary
echo ""
print_status "MCP Arena Benchmark Configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Models:      $MODELS"
echo "Experiment:  $EXP_NAME"
echo "Services:    ${SERVICE_ARRAY[*]}"
echo "Docker:      $USE_DOCKER"
echo "Parallel:    $PARALLEL"
echo "Timeout:     ${TIMEOUT}s per task"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Create results directory
RESULTS_DIR="./results/${EXP_NAME}"
mkdir -p "$RESULTS_DIR"

# Log file for this run with timestamp and models
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
LOG_FILE="${RESULTS_DIR}/benchmark_${TIMESTAMP}.log"
echo "Benchmark started at $(date '+%Y-%m-%d %H:%M:%S')" > "$LOG_FILE"
echo "Models: $MODELS" >> "$LOG_FILE"
echo "Services: ${SERVICE_ARRAY[*]}" >> "$LOG_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >> "$LOG_FILE"

# Function to run a single service
run_service() {
    local service=$1
    local start_time=$(date +%s)
    local start_time_formatted=$(date '+%Y-%m-%d %H:%M:%S')
    
    print_status "[$start_time_formatted] Starting $service tasks..."
    
    if [ "$USE_DOCKER" = true ]; then
        # Run with Docker
        ./run-task.sh --service "$service" \
            --models "$MODELS" \
            --exp-name "$EXP_NAME" \
            --tasks all \
            --timeout "$TIMEOUT" 2>&1 | tee -a "$LOG_FILE"
    else
        # Run locally
        python3 -m pipeline \
            --service "$service" \
            --models "$MODELS" \
            --exp-name "$EXP_NAME" \
            --tasks all \
            --timeout "$TIMEOUT" 2>&1 | tee -a "$LOG_FILE"
    fi
    
    local exit_code=$?
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    if [ $exit_code -eq 0 ]; then
        print_success "$service completed in ${duration}s"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] $service: SUCCESS (${duration}s)" >> "${RESULTS_DIR}/summary.txt"
    else
        print_error "$service failed with exit code $exit_code"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] $service: FAILED (exit code $exit_code)" >> "${RESULTS_DIR}/summary.txt"
    fi
    
    return $exit_code
}

# Track overall results
TOTAL_SERVICES=${#SERVICE_ARRAY[@]}
COMPLETED_SERVICES=0
FAILED_SERVICES=0

# Main execution
BENCHMARK_START=$(date +%s)

if [ "$PARALLEL" = true ]; then
    print_status "Running services in parallel..."
    
    # Run all services in background
    for service in "${SERVICE_ARRAY[@]}"; do
        (
            run_service "$service"
        ) &
        pids+=($!)
    done
    
    # Wait for all background jobs and collect exit codes
    for pid in "${pids[@]}"; do
        if wait $pid; then
            ((COMPLETED_SERVICES++))
        else
            ((FAILED_SERVICES++))
        fi
    done
else
    print_status "Running services sequentially..."
    
    for service in "${SERVICE_ARRAY[@]}"; do
        if run_service "$service"; then
            ((COMPLETED_SERVICES++))
        else
            ((FAILED_SERVICES++))
            print_warning "Continuing despite failure in $service"
        fi
    done
fi

BENCHMARK_END=$(date +%s)
TOTAL_DURATION=$((BENCHMARK_END - BENCHMARK_START))

# Generate final summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
print_status "Benchmark Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Completed at:      $(date '+%Y-%m-%d %H:%M:%S')"
echo "Total Services:    $TOTAL_SERVICES"
echo "Completed:         $COMPLETED_SERVICES"
echo "Failed:            $FAILED_SERVICES"
echo "Total Duration:    ${TOTAL_DURATION}s ($(($TOTAL_DURATION / 60))m $(($TOTAL_DURATION % 60))s)"
echo "Results saved to:  $RESULTS_DIR"
echo "Log file:          $LOG_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check if results parser is available and generate dashboard
if [ -f "examples/results_parser.py" ]; then
    print_status "Generating performance dashboard..."
    python3 -m examples.results_parser --exp-name "$EXP_NAME" --service all 2>/dev/null || {
        print_warning "Could not generate dashboard"
    }
fi

# Final status
if [ $FAILED_SERVICES -eq 0 ]; then
    print_success "Benchmark completed successfully!"
    exit 0
else
    print_warning "Benchmark completed with $FAILED_SERVICES failed service(s)"
    exit 1
fi