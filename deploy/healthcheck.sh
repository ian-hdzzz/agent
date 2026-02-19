#!/bin/bash
# ============================================
# PACO + Gobierno - Health Check & Auto-Restart
# ============================================
#
# Install as cron job:
#   echo "*/5 * * * * /opt/paco/deploy/healthcheck.sh" | crontab -
#
# Checks critical endpoints and restarts unhealthy containers.
# Logs to /var/log/paco-health.log
#
set -euo pipefail

LOG="/var/log/paco-health.log"
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
MAX_LOG_SIZE=10485760  # 10MB

# Rotate log if too large
if [ -f "$LOG" ] && [ "$(stat -f%z "$LOG" 2>/dev/null || stat -c%s "$LOG" 2>/dev/null)" -gt "$MAX_LOG_SIZE" ]; then
    mv "$LOG" "${LOG}.1"
fi

# Health check function
check_and_restart() {
    local name="$1"
    local container="$2"
    local url="$3"
    local timeout="${4:-5}"

    if curl -sf --max-time "$timeout" "$url" > /dev/null 2>&1; then
        return 0
    fi

    # Double-check before restarting
    sleep 3
    if curl -sf --max-time "$timeout" "$url" > /dev/null 2>&1; then
        return 0
    fi

    echo "[$TIMESTAMP] UNHEALTHY: $name ($container) - restarting" >> "$LOG"
    logger -t paco-health "UNHEALTHY: $name ($container) - restarting"

    if docker restart "$container" >> "$LOG" 2>&1; then
        echo "[$TIMESTAMP] RESTARTED: $container" >> "$LOG"
        logger -t paco-health "RESTARTED: $container"
    else
        echo "[$TIMESTAMP] RESTART FAILED: $container" >> "$LOG"
        logger -t paco-health "RESTART FAILED: $container"
    fi
}

# --- PACO Stack ---
check_and_restart "PACO Backend"    "paco-backend"          "http://127.0.0.1:8000/health"
check_and_restart "PACO Frontend"   "paco-frontend"         "http://127.0.0.1:3006"
check_and_restart "Langfuse"        "paco-langfuse"         "http://127.0.0.1:3001"
check_and_restart "CEA Tools"       "paco-cea-tools"        "http://127.0.0.1:3010/health"
check_and_restart "AGORA Tools"     "paco-agora-tools"      "http://127.0.0.1:3011/health"

# --- Gobierno Stack ---
check_and_restart "Orchestrator"    "gobierno-orchestrator"  "http://127.0.0.1:9100/health"

# Check a sample of agents (checking all 13 every 5 min is noisy)
MINUTE=$(date +%M)
case $((MINUTE % 15)) in
    0)
        check_and_restart "Agent Water"    "gobierno-agent-water-cea"        "http://127.0.0.1:9101/health"
        check_and_restart "Agent Transport" "gobierno-agent-transport-ameq"  "http://127.0.0.1:9102/health"
        check_and_restart "Agent Education" "gobierno-agent-education-usebeq" "http://127.0.0.1:9103/health"
        check_and_restart "Agent Vehicles" "gobierno-agent-vehicles"         "http://127.0.0.1:9104/health"
        ;;
    5)
        check_and_restart "Agent Psychology" "gobierno-agent-psychology-sejuve" "http://127.0.0.1:9105/health"
        check_and_restart "Agent Women"      "gobierno-agent-women-iqm"       "http://127.0.0.1:9106/health"
        check_and_restart "Agent Culture"    "gobierno-agent-culture"          "http://127.0.0.1:9107/health"
        check_and_restart "Agent Registry"   "gobierno-agent-registry-rpp"    "http://127.0.0.1:9108/health"
        ;;
    10)
        check_and_restart "Agent Labor"    "gobierno-agent-labor-cclq"        "http://127.0.0.1:9109/health"
        check_and_restart "Agent Housing"  "gobierno-agent-housing-iveq"      "http://127.0.0.1:9110/health"
        check_and_restart "Agent APPQRO"   "gobierno-agent-appqro"            "http://127.0.0.1:9111/health"
        check_and_restart "Agent Social"   "gobierno-agent-social-sedesoq"    "http://127.0.0.1:9112/health"
        check_and_restart "Agent Citizen"  "gobierno-agent-citizen-attention"  "http://127.0.0.1:9113/health"
        ;;
esac

# Check voice gateway
check_and_restart "Voice Gateway" "gobierno-voice-gateway" "http://127.0.0.1:9190/health"
