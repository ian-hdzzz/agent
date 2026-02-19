#!/bin/bash
# ============================================
# Pre-deployment Resource Check
# Verify GCP VM has enough resources for PACO + Gobierno
# ============================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE} PACO + Gobierno - Resource Check${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

PASS=true

# Detect architecture
ARCH=$(uname -m)
IS_ARM64=false
if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
    IS_ARM64=true
fi
echo -e "  ${BLUE}Architecture:${NC} $ARCH (ARM64: $IS_ARM64)"

# Detect machine type (GCE)
if curl -sf -H "Metadata-Flavor: Google" "http://metadata.google.internal/" >/dev/null 2>&1; then
    MACHINE_TYPE=$(curl -sf -H "Metadata-Flavor: Google" \
        "http://metadata.google.internal/computeMetadata/v1/instance/machine-type" | awk -F/ '{print $NF}')
    echo -e "  ${BLUE}Machine type:${NC} $MACHINE_TYPE"

    # Detect disk type
    BOOT_DISK=$(curl -sf -H "Metadata-Flavor: Google" \
        "http://metadata.google.internal/computeMetadata/v1/instance/disks/0/type" 2>/dev/null || echo "unknown")
    echo -e "  ${BLUE}Boot disk type:${NC} $BOOT_DISK"

    if echo "$BOOT_DISK" | grep -qi "hyperdisk"; then
        echo -e "  ${GREEN}OK${NC} Hyperdisk detected"
    fi
fi
echo ""

# Check RAM
TOTAL_RAM_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
TOTAL_RAM_GB=$((TOTAL_RAM_KB / 1024 / 1024))
AVAIL_RAM_KB=$(grep MemAvailable /proc/meminfo | awk '{print $2}')
AVAIL_RAM_GB=$((AVAIL_RAM_KB / 1024 / 1024))

if [ "$TOTAL_RAM_GB" -ge 16 ]; then
    echo -e "  ${GREEN}OK${NC} RAM: ${TOTAL_RAM_GB}GB total, ${AVAIL_RAM_GB}GB available (need 16GB+)"
else
    echo -e "  ${RED}FAIL${NC} RAM: ${TOTAL_RAM_GB}GB total (need 16GB+)"
    PASS=false
fi

# Check CPU
CPU_COUNT=$(nproc)
if [ "$CPU_COUNT" -ge 4 ]; then
    echo -e "  ${GREEN}OK${NC} CPU: ${CPU_COUNT} vCPUs (need 4+, 8 recommended)"
else
    echo -e "  ${RED}FAIL${NC} CPU: ${CPU_COUNT} vCPUs (need 4+)"
    PASS=false
fi

# Check Disk
DISK_AVAIL=$(df -BG / | tail -1 | awk '{print $4}' | tr -d 'G')
if [ "$DISK_AVAIL" -ge 50 ]; then
    echo -e "  ${GREEN}OK${NC} Disk: ${DISK_AVAIL}GB available (need 50GB+)"
else
    echo -e "  ${RED}FAIL${NC} Disk: ${DISK_AVAIL}GB available (need 50GB+)"
    PASS=false
fi

# Check data disk
if mountpoint -q /opt/paco 2>/dev/null; then
    DATA_AVAIL=$(df -BG /opt/paco | tail -1 | awk '{print $4}' | tr -d 'G')
    echo -e "  ${GREEN}OK${NC} Data disk: ${DATA_AVAIL}GB available at /opt/paco"
else
    echo -e "  ${YELLOW}!!${NC} No separate data disk mounted at /opt/paco"
fi

# Check Docker
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version | awk '{print $3}' | tr -d ',')
    echo -e "  ${GREEN}OK${NC} Docker: ${DOCKER_VERSION}"
else
    echo -e "  ${RED}FAIL${NC} Docker: not installed"
    PASS=false
fi

# Check Docker Compose
if docker compose version &> /dev/null; then
    COMPOSE_VERSION=$(docker compose version --short)
    echo -e "  ${GREEN}OK${NC} Docker Compose: ${COMPOSE_VERSION}"
elif command -v docker-compose &> /dev/null; then
    COMPOSE_VERSION=$(docker-compose --version | awk '{print $4}' | tr -d ',')
    echo -e "  ${YELLOW}!!${NC} Docker Compose (legacy): ${COMPOSE_VERSION} - upgrade to v2"
else
    echo -e "  ${RED}FAIL${NC} Docker Compose: not installed"
    PASS=false
fi

# Check current Docker resource usage
echo ""
echo -e "${BLUE}Current Docker Usage:${NC}"
if docker info &> /dev/null; then
    RUNNING=$(docker ps -q | wc -l | tr -d ' ')
    echo "  Running containers: ${RUNNING}"
    echo ""
    if [ "$RUNNING" -gt 0 ]; then
        docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null | head -30
    fi
else
    echo -e "  ${YELLOW}!!${NC} Cannot access Docker daemon (run as root or add user to docker group)"
fi

# Check port availability
echo ""
echo -e "${BLUE}Port Availability:${NC}"

check_port() {
    local port=$1
    local service=$2
    if ss -tlnp 2>/dev/null | grep -q ":${port} " || netstat -tlnp 2>/dev/null | grep -q ":${port} "; then
        echo -e "  ${YELLOW}!!${NC} Port ${port} (${service}) - IN USE"
    else
        echo -e "  ${GREEN}OK${NC} Port ${port} (${service}) - available"
    fi
}

# PACO ports
check_port 8000 "PACO Backend"
check_port 3006 "PACO Frontend"
check_port 3001 "Langfuse"
check_port 5432 "PostgreSQL (PACO)"
check_port 6379 "Redis (PACO)"
check_port 8123 "ClickHouse HTTP"
check_port 9000 "ClickHouse Native"
check_port 3010 "CEA Tools MCP"
check_port 3011 "AGORA Tools MCP"

# Gobierno ports
check_port 9100 "Gobierno Orchestrator"
check_port 9101 "Agent Water-CEA"
check_port 9104 "Agent Vehicles"
check_port 9113 "Agent Citizen-Attention"
check_port 9190 "Voice Gateway"
check_port 16686 "Jaeger UI"

echo ""
if [ "$PASS" = true ]; then
    echo -e "${GREEN}All resource checks passed! Ready to deploy.${NC}"
    exit 0
else
    echo -e "${RED}Some resource checks failed. Please resize your VM.${NC}"
    echo ""
    echo "Recommended VM sizes:"
    echo "  e2-standard-4     (4 vCPU, 16 GB)  - minimum for PACO"
    echo "  e2-standard-8     (8 vCPU, 32 GB)  - comfortable headroom (x86)"
    echo "  n4a-standard-8    (8 vCPU, 64 GB)  - recommended (ARM64, best perf/\$)"
    echo ""
    if [ "$IS_ARM64" = true ]; then
        echo "  You're on ARM64. Ensure all Docker images support linux/arm64."
        echo "  Run: bash deploy/validate-arm64.sh"
    fi
    exit 1
fi
