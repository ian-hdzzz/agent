#!/bin/bash
# ============================================
# PACO + Gobierno Queretaro - VM Setup Script
# Run once on a fresh Ubuntu 22.04/24.04 VM
# ============================================
#
# Usage:
#   curl -sSL <raw-url>/deploy/setup-vm.sh | bash
#   OR: ssh your-vm 'bash -s' < deploy/setup-vm.sh
#
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE} VM Setup - PACO + Gobierno Queretaro       ${NC}"
echo -e "${BLUE}============================================${NC}"

# --- System checks ---
if [ "$(id -u)" -ne 0 ]; then
    echo -e "${RED}Run as root: sudo bash setup-vm.sh${NC}"
    exit 1
fi

# Detect architecture and machine type
ARCH=$(uname -m)
IS_ARM64=false
if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
    IS_ARM64=true
fi

MACHINE_TYPE="unknown"
if curl -sf -H "Metadata-Flavor: Google" "http://metadata.google.internal/computeMetadata/v1/" >/dev/null 2>&1; then
    MACHINE_TYPE=$(curl -sf -H "Metadata-Flavor: Google" \
        "http://metadata.google.internal/computeMetadata/v1/instance/machine-type" | awk -F/ '{print $NF}')
fi

echo ""
echo "  Architecture:  $ARCH (ARM64: $IS_ARM64)"
echo "  Machine type:  $MACHINE_TYPE"
echo ""

# ========== [1/10] System packages ==========
echo -e "${GREEN}[1/10] Updating system packages...${NC}"
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get upgrade -y -qq

# ========== [2/10] Docker Engine ==========
echo -e "${GREEN}[2/10] Installing Docker...${NC}"
if command -v docker &>/dev/null; then
    echo "  Docker already installed: $(docker --version)"
else
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
fi

# Add current non-root user to docker group (if running via sudo)
if [ -n "${SUDO_USER:-}" ]; then
    usermod -aG docker "$SUDO_USER"
    echo "  Added $SUDO_USER to docker group"
fi

# ========== [3/10] Docker Compose v2 ==========
echo -e "${GREEN}[3/10] Verifying Docker Compose...${NC}"
if docker compose version &>/dev/null; then
    echo "  Docker Compose: $(docker compose version --short)"
else
    echo -e "${YELLOW}Docker Compose plugin not found. Installing...${NC}"
    apt-get install -y docker-compose-plugin
fi

# ========== [4/10] Docker daemon configuration ==========
echo -e "${GREEN}[4/10] Configuring Docker daemon...${NC}"
mkdir -p /etc/docker
cat > /etc/docker/daemon.json << 'DAEMON'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "5"
  },
  "live-restore": true,
  "userland-proxy": false,
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 65536,
      "Soft": 65536
    }
  }
}
DAEMON
systemctl restart docker
echo "  Docker daemon configured (log rotation, live-restore, ulimits)"

# ========== [5/10] Mount data disk ==========
echo -e "${GREEN}[5/10] Setting up data disk...${NC}"
DATA_DIR="/opt/paco"
DATA_DEVICE=""

# Auto-detect unformatted data disk
for dev in /dev/sdb /dev/nvme1n1 /dev/vdb; do
    if [ -b "$dev" ]; then
        DATA_DEVICE="$dev"
        break
    fi
done

if [ -n "$DATA_DEVICE" ]; then
    # Check if already mounted
    if mountpoint -q "$DATA_DIR" 2>/dev/null; then
        echo "  $DATA_DIR already mounted"
    else
        # Format if no filesystem
        if ! blkid "$DATA_DEVICE" &>/dev/null; then
            echo "  Formatting $DATA_DEVICE as ext4..."
            mkfs.ext4 -m 0 -F -E lazy_itable_init=0,lazy_journal_init=0 "$DATA_DEVICE"
        fi

        mkdir -p "$DATA_DIR"
        mount -o discard,defaults "$DATA_DEVICE" "$DATA_DIR"

        # Add to fstab for persistence
        UUID=$(blkid -s UUID -o value "$DATA_DEVICE")
        if ! grep -q "$UUID" /etc/fstab; then
            echo "UUID=$UUID $DATA_DIR ext4 discard,defaults,nofail 0 2" >> /etc/fstab
        fi
        echo "  Mounted $DATA_DEVICE at $DATA_DIR"
    fi
else
    echo -e "  ${YELLOW}No data disk detected. Using $DATA_DIR on boot disk.${NC}"
    mkdir -p "$DATA_DIR"
fi

# Create directory structure
echo "  Creating directory structure..."
mkdir -p "$DATA_DIR"/{paco,gobierno-queretaro,deploy,backups}
mkdir -p "$DATA_DIR/data"/{postgres-paco,postgres-gobierno,redis-paco,redis-gobierno,clickhouse}

echo "  Directory structure:"
echo "    $DATA_DIR/"
echo "      paco/                 (PACO stack)"
echo "      gobierno-queretaro/   (Gobierno stack)"
echo "      deploy/               (scripts)"
echo "      backups/              (local backup staging)"
echo "      data/                 (persistent volumes)"

# ========== [6/10] Firewall ==========
echo -e "${GREEN}[6/10] Configuring firewall (UFW)...${NC}"
if command -v ufw &>/dev/null; then
    ufw --force enable
    ufw default deny incoming
    ufw default allow outgoing
    ufw allow ssh
    ufw allow 80/tcp    # HTTP (Traefik)
    ufw allow 443/tcp   # HTTPS (Traefik)
    ufw reload
    echo "  Firewall: SSH, HTTP, HTTPS allowed. All other ports blocked."
else
    apt-get install -y -qq ufw
    ufw --force enable
    ufw default deny incoming
    ufw default allow outgoing
    ufw allow ssh
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw reload
    echo "  Firewall installed and configured."
fi

# ========== [7/10] Swap + kernel tuning ==========
echo -e "${GREEN}[7/10] Configuring swap and kernel parameters...${NC}"
if swapon --show | grep -q '/swapfile'; then
    echo "  Swap already exists"
else
    if [ ! -f /swapfile ]; then
        fallocate -l 4G /swapfile
        chmod 600 /swapfile
        mkswap /swapfile
        swapon /swapfile
        echo '/swapfile none swap sw 0 0' >> /etc/fstab
        echo "  4GB swap created"
    fi
fi

cat > /etc/sysctl.d/99-containers.conf << 'SYSCTL'
vm.swappiness=10
vm.overcommit_memory=1
net.core.somaxconn=65535
net.ipv4.ip_forward=1
fs.file-max=2097152
net.ipv4.tcp_tw_reuse=1
net.core.netdev_max_backlog=65536
SYSCTL
sysctl --system > /dev/null

# ========== [8/10] Security hardening ==========
echo -e "${GREEN}[8/10] Security hardening (sshd, fail2ban, unattended-upgrades)...${NC}"

# sshd hardening
if [ -f /etc/ssh/sshd_config ]; then
    # Only modify if not already hardened
    if ! grep -q "^PasswordAuthentication no" /etc/ssh/sshd_config; then
        sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
        sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
        sed -i 's/^#\?X11Forwarding.*/X11Forwarding no/' /etc/ssh/sshd_config
        systemctl restart sshd
        echo "  sshd hardened (no password auth, no root password login, no X11)"
    else
        echo "  sshd already hardened"
    fi
fi

# fail2ban
if ! command -v fail2ban-client &>/dev/null; then
    apt-get install -y -qq fail2ban
    cat > /etc/fail2ban/jail.local << 'JAIL'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
JAIL
    systemctl enable fail2ban
    systemctl restart fail2ban
    echo "  fail2ban installed and configured"
else
    echo "  fail2ban already installed"
fi

# unattended-upgrades
apt-get install -y -qq unattended-upgrades
dpkg-reconfigure -plow unattended-upgrades 2>/dev/null || true
echo "  unattended-upgrades enabled"

# ========== [9/10] Google Cloud Ops Agent ==========
echo -e "${GREEN}[9/10] Installing Google Cloud Ops Agent...${NC}"
if command -v google_cloud_ops_agent_engine &>/dev/null || systemctl is-active google-cloud-ops-agent &>/dev/null 2>&1; then
    echo "  Ops Agent already installed"
else
    if curl -sf -H "Metadata-Flavor: Google" "http://metadata.google.internal/" >/dev/null 2>&1; then
        curl -sSO https://dl.google.com/cloudagents/add-google-cloud-ops-agent-repo.sh
        bash add-google-cloud-ops-agent-repo.sh --also-install
        rm -f add-google-cloud-ops-agent-repo.sh
        echo "  Ops Agent installed"
    else
        echo -e "  ${YELLOW}Not running on GCE, skipping Ops Agent.${NC}"
    fi
fi

# ========== [10/10] Systemd service + utilities ==========
echo -e "${GREEN}[10/10] Setting up systemd service and utilities...${NC}"

apt-get install -y -qq git curl wget htop jq unzip

# Create systemd service for auto-start
cat > /etc/systemd/system/paco.service << 'SYSTEMD'
[Unit]
Description=PACO + Gobierno Queretaro Docker Stacks
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/paco
ExecStart=/opt/paco/deploy/deploy.sh all
ExecStop=/opt/paco/deploy/deploy.sh down
TimeoutStartSec=300
TimeoutStopSec=120

[Install]
WantedBy=multi-user.target
SYSTEMD

systemctl daemon-reload
systemctl enable paco.service
echo "  systemd service 'paco' created and enabled"

# Install healthcheck cron
if [ -f "$DATA_DIR/deploy/healthcheck.sh" ]; then
    chmod +x "$DATA_DIR/deploy/healthcheck.sh"
    (crontab -l 2>/dev/null | grep -v healthcheck; echo "*/5 * * * * $DATA_DIR/deploy/healthcheck.sh") | crontab -
    echo "  healthcheck cron installed (every 5 min)"
fi

# Install backup cron
if [ -f "$DATA_DIR/deploy/backup.sh" ]; then
    chmod +x "$DATA_DIR/deploy/backup.sh"
    (crontab -l 2>/dev/null | grep -v backup; echo "0 3 * * * $DATA_DIR/deploy/backup.sh >> /var/log/paco-backup.log 2>&1") | crontab -
    echo "  backup cron installed (daily at 3 AM)"
fi

echo ""
echo -e "${BLUE}============================================${NC}"
echo -e "${GREEN} VM Setup Complete!${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""
echo "System info:"
echo "  Arch:    $ARCH (ARM64: $IS_ARM64)"
echo "  Machine: $MACHINE_TYPE"
echo "  RAM:     $(free -h | awk '/^Mem:/{print $2}')"
echo "  CPUs:    $(nproc)"
echo "  Disk:    $(df -h / | awk 'NR==2{print $4}') free (boot)"
if mountpoint -q "$DATA_DIR" 2>/dev/null; then
echo "  Data:    $(df -h "$DATA_DIR" | awk 'NR==2{print $4}') free ($DATA_DIR)"
fi
echo "  Docker:  $(docker --version)"
echo ""
echo "Next steps:"
echo "  1. Clone repo:       git clone <repo-url> $DATA_DIR"
echo "  2. Sync secrets:     bash $DATA_DIR/deploy/sync-secrets.sh"
echo "  3. Deploy:           bash $DATA_DIR/deploy/deploy.sh"
echo "  4. Or use systemd:   systemctl start paco"
echo ""
if [ -n "${SUDO_USER:-}" ]; then
    echo -e "${YELLOW}Log out and back in for docker group to take effect.${NC}"
fi
