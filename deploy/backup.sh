#!/bin/bash
# ============================================
# Database Backup Script with GCS Upload
# Run via cron: 0 3 * * * /opt/paco/deploy/backup.sh
# ============================================
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/opt/paco/backups}"
RETAIN_DAYS="${RETAIN_DAYS:-7}"
GCS_BUCKET="${GCS_BUCKET:-}"
DATE=$(date +%Y%m%d_%H%M%S)

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting backups..."

# --- PACO PostgreSQL ---
echo "  Backing up paco-postgres..."
if docker exec paco-postgres pg_dumpall -U paco > "$BACKUP_DIR/paco-postgres-$DATE.sql" 2>/dev/null; then
    gzip "$BACKUP_DIR/paco-postgres-$DATE.sql"
    echo -e "  ${GREEN}OK${NC} paco-postgres"
else
    echo -e "  ${YELLOW}SKIP${NC} paco-postgres (container not running)"
fi

# --- Gobierno PostgreSQL ---
echo "  Backing up gobierno-postgres..."
if docker exec gobierno-postgres pg_dumpall -U postgres > "$BACKUP_DIR/gobierno-postgres-$DATE.sql" 2>/dev/null; then
    gzip "$BACKUP_DIR/gobierno-postgres-$DATE.sql"
    echo -e "  ${GREEN}OK${NC} gobierno-postgres"
else
    echo -e "  ${YELLOW}SKIP${NC} gobierno-postgres (container not running)"
fi

# --- Redis (PACO) ---
echo "  Backing up paco-redis..."
if docker exec paco-redis redis-cli BGSAVE > /dev/null 2>&1; then
    sleep 2
    if docker cp paco-redis:/data/dump.rdb "$BACKUP_DIR/paco-redis-$DATE.rdb" 2>/dev/null; then
        gzip "$BACKUP_DIR/paco-redis-$DATE.rdb"
        echo -e "  ${GREEN}OK${NC} paco-redis"
    fi
else
    echo -e "  ${YELLOW}SKIP${NC} paco-redis (container not running)"
fi

# --- Redis (Gobierno) ---
echo "  Backing up gobierno-redis..."
if docker exec gobierno-redis redis-cli BGSAVE > /dev/null 2>&1; then
    sleep 2
    if docker cp gobierno-redis:/data/dump.rdb "$BACKUP_DIR/gobierno-redis-$DATE.rdb" 2>/dev/null; then
        gzip "$BACKUP_DIR/gobierno-redis-$DATE.rdb"
        echo -e "  ${GREEN}OK${NC} gobierno-redis"
    fi
else
    echo -e "  ${YELLOW}SKIP${NC} gobierno-redis (container not running)"
fi

# --- Upload to GCS ---
if [ -n "$GCS_BUCKET" ]; then
    echo ""
    echo "  Uploading to GCS ($GCS_BUCKET)..."
    if command -v gsutil &>/dev/null; then
        gsutil -m cp "$BACKUP_DIR"/*"$DATE"* "gs://$GCS_BUCKET/backups/$DATE/" 2>&1
        echo -e "  ${GREEN}OK${NC} Uploaded to gs://$GCS_BUCKET/backups/$DATE/"
    else
        echo -e "  ${YELLOW}gsutil not found. Install Google Cloud SDK for GCS uploads.${NC}"
    fi
else
    echo ""
    echo -e "  ${YELLOW}GCS_BUCKET not set. Skipping cloud upload.${NC}"
    echo "  Set GCS_BUCKET env var or edit this script to enable."
fi

# --- Cleanup old local backups ---
echo ""
echo "  Cleaning up local backups older than $RETAIN_DAYS days..."
find "$BACKUP_DIR" -type f -mtime +"$RETAIN_DAYS" -delete

# --- Summary ---
echo ""
echo "[$(date)] Backups complete:"
ls -lh "$BACKUP_DIR"/*"$DATE"* 2>/dev/null || echo "  No files found for this run"
echo ""
echo "Total local backup size: $(du -sh "$BACKUP_DIR" | cut -f1)"

# --- GCS lifecycle policy reminder ---
if [ -n "$GCS_BUCKET" ]; then
    echo ""
    echo "GCS lifecycle policy (apply once):"
    echo "  gsutil lifecycle set <(cat <<'EOF'"
    echo '  {"rule": [{"action": {"type": "SetStorageClass", "storageClass": "NEARLINE"}, "condition": {"age": 30}},'
    echo '            {"action": {"type": "Delete"}, "condition": {"age": 90}}]}'
    echo "  EOF"
    echo "  ) gs://$GCS_BUCKET"
fi
