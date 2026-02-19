#!/bin/bash
# ============================================
# PACO + Gobierno Queretaro - Deploy Script
# Production deployment with backup, secrets, and rollback
# ============================================
#
# Usage:
#   cd /opt/paco    (or ~/agents-maria)
#   bash deploy/deploy.sh              # Deploy everything
#   bash deploy/deploy.sh paco         # Deploy only PACO
#   bash deploy/deploy.sh gobierno     # Deploy only Gobierno
#   bash deploy/deploy.sh traefik      # Install Traefik routes only
#   bash deploy/deploy.sh down         # Stop everything
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

TARGET="${1:-all}"

# Traefik dynamic config directory
TRAEFIK_CONFIG_DIR="/etc/easypanel/traefik/config"

# Compose files: base + prod overrides
GOBIERNO_COMPOSE="-f $PROJECT_DIR/gobierno-queretaro/docker-compose.yml"
PACO_COMPOSE="-f $PROJECT_DIR/paco/docker-compose.yml"

if [ -f "$PROJECT_DIR/gobierno-queretaro/docker-compose.prod.yml" ]; then
    GOBIERNO_COMPOSE="$GOBIERNO_COMPOSE -f $PROJECT_DIR/gobierno-queretaro/docker-compose.prod.yml"
fi
if [ -f "$PROJECT_DIR/paco/docker-compose.prod.yml" ]; then
    PACO_COMPOSE="$PACO_COMPOSE -f $PROJECT_DIR/paco/docker-compose.prod.yml"
fi

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE} PACO + Gobierno - Deployment               ${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# --- Pre-flight checks ---
preflight() {
    if ! command -v docker &>/dev/null; then
        echo -e "${RED}Docker not installed. Run setup-vm.sh first.${NC}"
        exit 1
    fi
    if ! docker compose version &>/dev/null; then
        echo -e "${RED}Docker Compose plugin not found.${NC}"
        exit 1
    fi

    echo -e "${GREEN}Pre-flight checks:${NC}"
    echo "  RAM:   $(free -h | awk '/^Mem:/{print $2}') total, $(free -h | awk '/^Mem:/{print $7}') available"
    echo "  CPUs:  $(nproc)"
    echo "  Disk:  $(df -h / | awk 'NR==2{print $4}') free"
    echo "  Docker: $(docker --version | cut -d' ' -f3)"
    echo ""

    # Warn if low resources
    local avail_mb
    avail_mb=$(free -m | awk '/^Mem:/{print $7}')
    if [ "$avail_mb" -lt 4096 ]; then
        echo -e "${YELLOW}Warning: Less than 4GB RAM available ($avail_mb MB). Deployment may be tight.${NC}"
    fi
}

# --- Pre-deploy backup ---
pre_deploy_backup() {
    if [ -f "$SCRIPT_DIR/backup.sh" ]; then
        echo -e "${GREEN}Running pre-deploy backup...${NC}"
        bash "$SCRIPT_DIR/backup.sh" || echo -e "${YELLOW}Backup had warnings (continuing deploy)${NC}"
        echo ""
    fi
}

# --- Git sync ---
git_sync() {
    echo -e "${GREEN}Syncing from origin/main...${NC}"
    cd "$PROJECT_DIR"
    PREV_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "none")

    if git remote get-url origin &>/dev/null; then
        git fetch origin main
        git reset --hard origin/main
        NEW_COMMIT=$(git rev-parse HEAD)
        echo "  Previous: ${PREV_COMMIT:0:8}"
        echo "  Current:  ${NEW_COMMIT:0:8}"
    else
        echo -e "  ${YELLOW}No git remote configured, skipping sync.${NC}"
    fi
    echo ""
}

# --- Sync secrets ---
sync_secrets() {
    if [ -f "$SCRIPT_DIR/sync-secrets.sh" ]; then
        # Only auto-sync if on GCE
        if curl -sf -H "Metadata-Flavor: Google" "http://metadata.google.internal/" >/dev/null 2>&1; then
            echo -e "${GREEN}Syncing secrets from GCP Secret Manager...${NC}"
            bash "$SCRIPT_DIR/sync-secrets.sh"
            echo ""
        fi
    fi
}

# --- Setup .env files ---
setup_env() {
    local dir=$1
    local name=$2
    if [ ! -f "$dir/.env" ]; then
        if [ -f "$dir/.env.example" ]; then
            cp "$dir/.env.example" "$dir/.env"
            echo -e "${YELLOW}Created $name/.env from .env.example${NC}"
            echo -e "${RED}  >> Edit $dir/.env with your API keys before continuing!${NC}"
            return 1
        else
            echo -e "${RED}No .env or .env.example in $dir${NC}"
            return 1
        fi
    fi
    echo -e "  ${GREEN}OK${NC} $name/.env exists"
    return 0
}

# --- Deploy PACO ---
deploy_paco() {
    echo -e "${GREEN}Deploying PACO stack...${NC}"
    cd "$PROJECT_DIR/paco"

    if ! setup_env "$PROJECT_DIR/paco" "paco"; then
        echo -e "${RED}Fix paco/.env and re-run.${NC}"
        return 1
    fi

    docker compose $PACO_COMPOSE up -d --build
    echo -e "  ${GREEN}OK${NC} PACO stack started (8 containers)"
}

# --- Deploy Gobierno ---
deploy_gobierno() {
    echo -e "${GREEN}Deploying Gobierno Queretaro stack...${NC}"
    cd "$PROJECT_DIR/gobierno-queretaro"

    if ! setup_env "$PROJECT_DIR/gobierno-queretaro" "gobierno-queretaro"; then
        echo -e "${RED}Fix gobierno-queretaro/.env and re-run.${NC}"
        return 1
    fi

    # Validate ANTHROPIC_API_KEY is set
    set -a
    source .env
    set +a
    if [ -z "${ANTHROPIC_API_KEY:-}" ] || [ "$ANTHROPIC_API_KEY" = "sk-ant-api03-xxx" ]; then
        echo -e "${RED}Error: Set ANTHROPIC_API_KEY in gobierno-queretaro/.env${NC}"
        return 1
    fi

    docker compose $GOBIERNO_COMPOSE up -d --build
    echo -e "  ${GREEN}OK${NC} Gobierno stack started (18 containers)"
}

# --- Install Traefik routes ---
install_traefik_routes() {
    echo -e "${GREEN}Installing Traefik routes...${NC}"

    if [ ! -d "$TRAEFIK_CONFIG_DIR" ]; then
        for dir in /etc/easypanel/traefik/config /etc/traefik/config /opt/easypanel/traefik/config; do
            if [ -d "$dir" ]; then
                TRAEFIK_CONFIG_DIR="$dir"
                break
            fi
        done

        if [ ! -d "$TRAEFIK_CONFIG_DIR" ]; then
            echo -e "${YELLOW}Traefik config directory not found.${NC}"
            echo "  Services accessible via 127.0.0.1 ports only."
            return 0
        fi
    fi

    # Check for placeholder domains
    if grep -q 'YOUR-DOMAIN' "$SCRIPT_DIR/traefik/paco-routes.yml"; then
        echo -e "${YELLOW}Warning: Traefik route files still have YOUR-DOMAIN placeholders.${NC}"
        echo "  Edit deploy/traefik/*.yml with your actual domains first."
        return 0
    fi

    sudo cp "$SCRIPT_DIR/traefik/paco-routes.yml" "$TRAEFIK_CONFIG_DIR/paco-routes.yml"
    sudo cp "$SCRIPT_DIR/traefik/gobierno-routes.yml" "$TRAEFIK_CONFIG_DIR/gobierno-routes.yml"

    echo -e "  ${GREEN}OK${NC} Routes installed to $TRAEFIK_CONFIG_DIR"
}

# --- Health checks ---
check_health() {
    local name=$1
    local url=$2
    local max_retries=5
    local retry=0

    while [ $retry -lt $max_retries ]; do
        if curl -sf "$url" > /dev/null 2>&1; then
            echo -e "  ${GREEN}OK${NC} $name"
            return 0
        fi
        retry=$((retry + 1))
        sleep 3
    done
    echo -e "  ${YELLOW}!!${NC} $name (not ready)"
    return 1
}

verify_health() {
    local failed=0
    echo ""
    echo -e "${BLUE}Health Checks:${NC}"
    echo ""

    if [ "$TARGET" = "all" ] || [ "$TARGET" = "paco" ]; then
        echo "PACO:"
        check_health "PACO Backend     (8000)" "http://127.0.0.1:8000/health" || failed=$((failed + 1))
        check_health "Langfuse         (3001)" "http://127.0.0.1:3001" || failed=$((failed + 1))
        check_health "PACO Frontend    (3006)" "http://127.0.0.1:3006" || failed=$((failed + 1))
        check_health "CEA Tools MCP    (3010)" "http://127.0.0.1:3010/health" || true
        check_health "AGORA Tools MCP  (3011)" "http://127.0.0.1:3011/health" || true
        echo ""
    fi

    if [ "$TARGET" = "all" ] || [ "$TARGET" = "gobierno" ]; then
        echo "Gobierno Queretaro:"
        check_health "Orchestrator     (9100)" "http://127.0.0.1:9100/health" || failed=$((failed + 1))
        check_health "Jaeger UI        (16686)" "http://127.0.0.1:16686" || true

        for port in 9101 9104 9113; do
            check_health "Agent (port $port)" "http://127.0.0.1:$port/health" || true
        done
        echo ""
    fi

    return $failed
}

# --- Rollback ---
rollback() {
    if [ -n "${PREV_COMMIT:-}" ] && [ "$PREV_COMMIT" != "none" ]; then
        echo -e "${RED}Health checks failed! Rolling back to ${PREV_COMMIT:0:8}...${NC}"
        cd "$PROJECT_DIR"
        git reset --hard "$PREV_COMMIT"

        if [ "$TARGET" = "all" ] || [ "$TARGET" = "paco" ]; then
            cd "$PROJECT_DIR/paco"
            docker compose $PACO_COMPOSE up -d --build
        fi
        if [ "$TARGET" = "all" ] || [ "$TARGET" = "gobierno" ]; then
            cd "$PROJECT_DIR/gobierno-queretaro"
            docker compose $GOBIERNO_COMPOSE up -d --build
        fi

        echo -e "${YELLOW}Rolled back to ${PREV_COMMIT:0:8}. Check logs for issues.${NC}"
    else
        echo -e "${RED}Health checks failed! No previous commit to rollback to.${NC}"
    fi
}

# --- Stop everything ---
stop_all() {
    echo -e "${YELLOW}Stopping all stacks...${NC}"

    cd "$PROJECT_DIR/paco"
    docker compose $PACO_COMPOSE down 2>/dev/null || true

    cd "$PROJECT_DIR/gobierno-queretaro"
    docker compose $GOBIERNO_COMPOSE down 2>/dev/null || true

    echo -e "${GREEN}All stacks stopped.${NC}"
    exit 0
}

# --- Main ---
preflight

PREV_COMMIT=""

case "$TARGET" in
    all)
        pre_deploy_backup
        git_sync
        sync_secrets
        deploy_paco
        echo ""
        deploy_gobierno
        echo ""
        install_traefik_routes
        ;;
    paco)
        deploy_paco
        ;;
    gobierno)
        deploy_gobierno
        ;;
    traefik|routes)
        install_traefik_routes
        ;;
    down|stop)
        stop_all
        ;;
    *)
        echo "Usage: $0 [all|paco|gobierno|traefik|down]"
        exit 1
        ;;
esac

# Wait for containers to initialize
echo ""
echo -e "${GREEN}Waiting 30s for services to start...${NC}"
sleep 30

if ! verify_health; then
    rollback
    exit 1
fi

# Prune old images
echo -e "${GREEN}Pruning unused Docker images...${NC}"
docker image prune -f --filter "until=168h" 2>/dev/null || true

echo ""
echo -e "${BLUE}============================================${NC}"
echo -e "${GREEN} Deployment Complete!${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""
echo "Container status:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(paco|gobierno)" | head -30
echo ""
echo "Useful commands:"
echo "  docker compose $PACO_COMPOSE logs -f              # PACO logs"
echo "  docker compose $GOBIERNO_COMPOSE logs -f           # Gobierno logs"
echo "  bash deploy/deploy.sh down                         # Stop all"
echo "  bash deploy/backup.sh                              # Run backup"
