#!/bin/bash

# Build Docker image for MCP Arena
set -e

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Building MCPMark Docker image...${NC}"

# Build the Docker image with both tags for convenience
docker build -t mcpmark:latest -t evalsysorg/mcpmark:latest . "$@"

# Check if build was successful
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Docker image built successfully${NC}"
    echo "  Local tag: mcpmark:latest"
    echo "  Docker Hub tag: evalsysorg/mcpmark:latest"
    
    # Show image info
    echo ""
    echo "Image details:"
    docker images mcpmark:latest --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
    
    echo ""
    echo "You can now run tasks using:"
    echo "  ./run-task.sh --service notion --models o3 --exp-name test --tasks all"
else
    echo "Docker build failed!"
    exit 1
fi