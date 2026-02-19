#!/bin/bash
# ============================================
# ARM64 / N4A Axion Validation Script
# Run locally (Mac M-series) before provisioning
# ============================================
#
# Usage:
#   bash deploy/validate-arm64.sh
#
# Checks:
#   1. N4A availability in northamerica-south1
#   2. ARM64 Docker builds for all stacks
#   3. Decision gate: N4A vs E2 fallback
#
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

BLOCKERS=()
WARNINGS=()

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE} ARM64 / N4A Axion Validation               ${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# --- Step 1: Check N4A availability in northamerica-south1 ---
echo -e "${GREEN}[1/3] Checking N4A availability in northamerica-south1...${NC}"

if ! command -v gcloud &>/dev/null; then
    echo -e "${YELLOW}  gcloud CLI not installed. Skipping region check.${NC}"
    echo "  Install: https://cloud.google.com/sdk/docs/install"
    WARNINGS+=("gcloud not available - could not verify N4A in region")
else
    N4A_RESULT=$(gcloud compute machine-types list \
        --filter="name=n4a-standard-8" \
        --zones=northamerica-south1-a,northamerica-south1-b,northamerica-south1-c \
        --format="value(name,zone)" 2>/dev/null || true)

    if [ -z "$N4A_RESULT" ]; then
        echo -e "${RED}  N4A-standard-8 NOT available in northamerica-south1${NC}"
        BLOCKERS+=("N4A not available in northamerica-south1")
    else
        echo -e "${GREEN}  N4A-standard-8 available:${NC}"
        echo "$N4A_RESULT" | while read -r line; do
            echo "    $line"
        done
    fi
fi

# --- Step 2: Test ARM64 Docker builds ---
echo ""
echo -e "${GREEN}[2/3] Testing ARM64 Docker builds...${NC}"

if ! command -v docker &>/dev/null; then
    echo -e "${RED}  Docker not installed. Cannot validate ARM64 builds.${NC}"
    BLOCKERS+=("Docker not installed")
else
    # Ensure buildx is available
    if ! docker buildx version &>/dev/null; then
        echo -e "${RED}  Docker buildx not available.${NC}"
        BLOCKERS+=("Docker buildx not available")
    else
        # Create/use a builder that supports ARM64
        BUILDER_NAME="arm64-validator"
        if ! docker buildx inspect "$BUILDER_NAME" &>/dev/null; then
            echo "  Creating buildx builder for ARM64..."
            docker buildx create --name "$BUILDER_NAME" --use --platform linux/arm64,linux/amd64 >/dev/null 2>&1
        else
            docker buildx use "$BUILDER_NAME" >/dev/null 2>&1
        fi

        # Test Gobierno Orchestrator
        echo ""
        echo "  Testing: gobierno-queretaro/orchestrator (ARM64)..."
        if docker buildx build --platform linux/arm64 --load \
            -t test-arm64-orchestrator \
            -f "$PROJECT_DIR/gobierno-queretaro/orchestrator/Dockerfile" \
            "$PROJECT_DIR/gobierno-queretaro" 2>&1 | tail -5; then
            echo -e "  ${GREEN}OK${NC} gobierno-queretaro/orchestrator"
        else
            echo -e "  ${RED}FAIL${NC} gobierno-queretaro/orchestrator"
            BLOCKERS+=("Orchestrator Dockerfile failed ARM64 build")
        fi

        # Test Gobierno Vehicles Agent (has agentlightning dependency)
        echo ""
        echo "  Testing: gobierno-queretaro/agents/vehicles (ARM64)..."
        if docker buildx build --platform linux/arm64 --load \
            -t test-arm64-vehicles \
            -f "$PROJECT_DIR/gobierno-queretaro/agents/vehicles/Dockerfile" \
            "$PROJECT_DIR/gobierno-queretaro" 2>&1 | tail -5; then
            echo -e "  ${GREEN}OK${NC} gobierno-queretaro/agents/vehicles"
        else
            echo -e "  ${RED}FAIL${NC} gobierno-queretaro/agents/vehicles"
            BLOCKERS+=("Vehicles agent failed ARM64 build (check agentlightning/a2a-sdk)")
        fi

        # Test PACO Backend
        echo ""
        echo "  Testing: paco/backend (ARM64)..."
        if docker buildx build --platform linux/arm64 --load \
            -t test-arm64-paco-backend \
            -f "$PROJECT_DIR/paco/backend/Dockerfile" \
            "$PROJECT_DIR/paco/backend" 2>&1 | tail -5; then
            echo -e "  ${GREEN}OK${NC} paco/backend"
        else
            echo -e "  ${RED}FAIL${NC} paco/backend"
            BLOCKERS+=("PACO backend failed ARM64 build")
        fi

        # Test Langfuse image (pre-built, just pull)
        echo ""
        echo "  Testing: langfuse/langfuse:latest (ARM64 pull)..."
        if docker run --rm --platform linux/arm64 langfuse/langfuse:latest echo "OK" 2>&1; then
            echo -e "  ${GREEN}OK${NC} langfuse/langfuse:latest"
        else
            echo -e "  ${RED}FAIL${NC} langfuse/langfuse:latest"
            BLOCKERS+=("Langfuse image not available for ARM64")
        fi

        # Test ClickHouse image
        echo ""
        echo "  Testing: clickhouse/clickhouse-server:24.12 (ARM64 pull)..."
        if docker run --rm --platform linux/arm64 clickhouse/clickhouse-server:24.12 echo "OK" 2>&1; then
            echo -e "  ${GREEN}OK${NC} clickhouse/clickhouse-server:24.12"
        else
            echo -e "  ${RED}FAIL${NC} clickhouse/clickhouse-server:24.12"
            BLOCKERS+=("ClickHouse image not available for ARM64")
        fi

        # Cleanup test images
        echo ""
        echo "  Cleaning up test images..."
        docker rmi test-arm64-orchestrator test-arm64-vehicles test-arm64-paco-backend 2>/dev/null || true
    fi
fi

# --- Step 3: Decision gate ---
echo ""
echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE} Decision Gate                               ${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

if [ ${#WARNINGS[@]} -gt 0 ]; then
    echo -e "${YELLOW}Warnings:${NC}"
    for w in "${WARNINGS[@]}"; do
        echo -e "  ${YELLOW}!${NC} $w"
    done
    echo ""
fi

if [ ${#BLOCKERS[@]} -gt 0 ]; then
    echo -e "${RED}BLOCKERS FOUND (${#BLOCKERS[@]}):${NC}"
    for b in "${BLOCKERS[@]}"; do
        echo -e "  ${RED}X${NC} $b"
    done
    echo ""
    echo -e "${YELLOW}RECOMMENDATION: Use E2 fallback${NC}"
    echo ""
    echo "Deploy with E2:"
    echo "  Machine type: e2-standard-8 (8 vCPU, 32 GB RAM)"
    echo "  Boot disk:    pd-balanced 100GB"
    echo "  Data disk:    pd-balanced 200GB"
    echo ""
    echo "Commands:"
    echo "  gcloud compute instances create paco-prod \\"
    echo "    --zone=northamerica-south1-a \\"
    echo "    --machine-type=e2-standard-8 \\"
    echo "    --image-family=ubuntu-2404-lts-amd64 \\"
    echo "    --image-project=ubuntu-os-cloud \\"
    echo "    --boot-disk-size=100GB \\"
    echo "    --boot-disk-type=pd-balanced \\"
    echo "    --tags=http-server,https-server"
    echo ""
    echo "  gcloud compute disks create paco-data \\"
    echo "    --zone=northamerica-south1-a \\"
    echo "    --size=200GB \\"
    echo "    --type=pd-balanced"
    exit 1
else
    echo -e "${GREEN}ALL CHECKS PASSED!${NC}"
    echo ""
    echo -e "${GREEN}RECOMMENDATION: Deploy with N4A Axion (ARM64)${NC}"
    echo ""
    echo "  Machine type: n4a-standard-8 (8 vCPU, 64 GB RAM)"
    echo "  Boot disk:    hyperdisk-balanced 100GB"
    echo "  Data disk:    hyperdisk-balanced 200GB"
    echo "  Cost:         ~\$225/month"
    echo ""
    echo "Commands:"
    echo "  gcloud compute instances create paco-prod \\"
    echo "    --zone=northamerica-south1-a \\"
    echo "    --machine-type=n4a-standard-8 \\"
    echo "    --image-family=ubuntu-2404-lts-arm64 \\"
    echo "    --image-project=ubuntu-os-cloud \\"
    echo "    --boot-disk-size=100GB \\"
    echo "    --boot-disk-type=hyperdisk-balanced \\"
    echo "    --tags=http-server,https-server"
    echo ""
    echo "  gcloud compute disks create paco-data \\"
    echo "    --zone=northamerica-south1-a \\"
    echo "    --size=200GB \\"
    echo "    --type=hyperdisk-balanced"
    echo ""
    echo "Next steps:"
    echo "  1. Create VM with commands above"
    echo "  2. Attach data disk: gcloud compute instances attach-disk paco-prod --disk=paco-data"
    echo "  3. SSH in and run: bash deploy/setup-vm.sh"
    exit 0
fi
