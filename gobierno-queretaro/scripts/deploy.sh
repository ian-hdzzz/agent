#!/bin/bash
# ============================================
# Gobierno Querétaro - Deployment Script
# Build and deploy multi-agent system
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
COMPOSE_FILE="docker-compose.yml"
BUILD_ONLY=false
PULL_IMAGES=false
SPECIFIC_SERVICE=""

usage() {
    echo "Usage: $0 [OPTIONS] [SERVICE]"
    echo ""
    echo "Deploy the Gobierno Querétaro multi-agent system"
    echo ""
    echo "Options:"
    echo "  -b, --build-only    Build images without starting containers"
    echo "  -p, --pull          Pull base images before building"
    echo "  -f, --file FILE     Specify compose file (default: docker-compose.yml)"
    echo "  -h, --help          Show this help message"
    echo ""
    echo "Service (optional):"
    echo "  Specific service to build/deploy (e.g., 'orchestrator', 'agent-water-cea')"
    echo "  If not specified, all services will be deployed"
    echo ""
    echo "Examples:"
    echo "  $0                    # Deploy all services"
    echo "  $0 orchestrator       # Deploy only orchestrator"
    echo "  $0 -b                 # Build all images without starting"
    echo "  $0 -b agent-water-cea # Build only water-cea agent"
    exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -b|--build-only)
            BUILD_ONLY=true
            shift
            ;;
        -p|--pull)
            PULL_IMAGES=true
            shift
            ;;
        -f|--file)
            COMPOSE_FILE="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            SPECIFIC_SERVICE="$1"
            shift
            ;;
    esac
done

cd "$PROJECT_DIR"

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE} Gobierno Querétaro - Multi-Agent Deployment${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Check for .env file
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo -e "${YELLOW}Warning: .env file not found${NC}"
        echo "Creating .env from .env.example..."
        cp .env.example .env
        echo -e "${RED}Please edit .env and set your ANTHROPIC_API_KEY${NC}"
        exit 1
    else
        echo -e "${RED}Error: Neither .env nor .env.example found${NC}"
        exit 1
    fi
fi

# Check for ANTHROPIC_API_KEY
source .env
if [ -z "$ANTHROPIC_API_KEY" ] || [ "$ANTHROPIC_API_KEY" = "sk-ant-api03-xxx" ]; then
    echo -e "${RED}Error: ANTHROPIC_API_KEY not set in .env${NC}"
    exit 1
fi

# Pull base images if requested
if [ "$PULL_IMAGES" = true ]; then
    echo -e "${GREEN}Pulling base images...${NC}"
    docker pull python:3.12-slim
    docker pull redis:7-alpine
    docker pull postgres:15-alpine
fi

# Build command
BUILD_CMD="docker-compose -f $COMPOSE_FILE build"
if [ -n "$SPECIFIC_SERVICE" ]; then
    BUILD_CMD="$BUILD_CMD $SPECIFIC_SERVICE"
fi

echo -e "${GREEN}Building images...${NC}"
$BUILD_CMD

if [ "$BUILD_ONLY" = true ]; then
    echo ""
    echo -e "${GREEN}Build complete!${NC}"
    echo "Run '$0' (without -b) to start containers"
    exit 0
fi

# Start containers
START_CMD="docker-compose -f $COMPOSE_FILE up -d"
if [ -n "$SPECIFIC_SERVICE" ]; then
    START_CMD="$START_CMD $SPECIFIC_SERVICE"
fi

echo ""
echo -e "${GREEN}Starting containers...${NC}"
$START_CMD

# Wait for services to be healthy
echo ""
echo -e "${GREEN}Waiting for services to be healthy...${NC}"
sleep 5

# Check health of main services
echo ""
echo -e "${BLUE}Service Status:${NC}"

check_health() {
    local service=$1
    local port=$2
    local url="http://localhost:$port/health"

    if curl -s -f "$url" > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} $service (port $port)"
    else
        echo -e "  ${YELLOW}○${NC} $service (port $port) - starting..."
    fi
}

check_health "orchestrator" 9100
check_health "agent-water-cea" 9101
check_health "agent-transport-ameq" 9102
check_health "agent-education-usebeq" 9103
check_health "agent-vehicles" 9104
check_health "agent-psychology-sejuve" 9105
check_health "agent-women-iqm" 9106
check_health "agent-culture" 9107
check_health "agent-registry-rpp" 9108
check_health "agent-labor-cclq" 9109
check_health "agent-housing-iveq" 9110
check_health "agent-appqro" 9111
check_health "agent-social-sedesoq" 9112
check_health "agent-citizen-attention" 9113

echo ""
echo -e "${GREEN}Deployment complete!${NC}"
echo ""
echo "Endpoints:"
echo "  Orchestrator:    http://localhost:9100"
echo "  Route API:       http://localhost:9100/route"
echo "  Classify API:    http://localhost:9100/classify"
echo "  Agents list:     http://localhost:9100/agents"
echo ""
echo "Useful commands:"
echo "  docker-compose logs -f                  # Follow all logs"
echo "  docker-compose logs -f orchestrator     # Follow orchestrator logs"
echo "  docker-compose ps                       # Check container status"
echo "  docker-compose down                     # Stop all containers"
