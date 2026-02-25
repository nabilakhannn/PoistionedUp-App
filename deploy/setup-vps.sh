#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
# OpenClaw VPS Setup Script — PositionedUp Agent Squad
# Run this on your Hostinger VPS after SSH-ing in as root
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/YOUR_REPO/deploy/setup-vps.sh | bash
#   OR
#   scp deploy/setup-vps.sh root@YOUR_VPS_IP:~/setup-vps.sh
#   ssh root@YOUR_VPS_IP 'bash ~/setup-vps.sh'
# ─────────────────────────────────────────────────────────

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log()   { echo -e "${GREEN}[+]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[x]${NC} $1"; }
info()  { echo -e "${BLUE}[i]${NC} $1"; }

# ── Step 1: System Update ────────────────────────────────
log "Step 1/7: Updating system packages..."
apt-get update -qq
apt-get upgrade -y -qq
apt-get install -y -qq git curl ca-certificates ufw fail2ban

# ── Step 2: Install Docker ────────────────────────────────
if command -v docker &>/dev/null; then
    log "Docker already installed: $(docker --version)"
else
    log "Step 2/7: Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    log "Docker installed: $(docker --version)"
fi

# Verify Docker Compose
if docker compose version &>/dev/null; then
    log "Docker Compose: $(docker compose version)"
else
    error "Docker Compose not found. Install manually."
    exit 1
fi

# ── Step 3: Security Hardening ────────────────────────────
log "Step 3/7: Configuring firewall (UFW)..."
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
# Do NOT open port 18789 publicly. Access via SSH tunnel only.
ufw --force enable
log "Firewall configured. Only SSH (22) is open."

# Enable fail2ban for SSH brute force protection
systemctl enable fail2ban
systemctl start fail2ban
log "Fail2ban enabled for SSH protection."

# ── Step 4: Create project directory ──────────────────────
DEPLOY_DIR="/opt/openclaw"
log "Step 4/7: Setting up project directory at $DEPLOY_DIR..."
mkdir -p "$DEPLOY_DIR"
cd "$DEPLOY_DIR"

# ── Step 5: Create persistent directories ─────────────────
log "Step 5/7: Creating persistent directories..."
mkdir -p /var/openclaw/config
mkdir -p /var/openclaw/workspace
mkdir -p /var/openclaw/workspace/drafts
mkdir -p /var/openclaw/workspace/assets
mkdir -p /var/openclaw/workspace/archive
mkdir -p /var/openclaw/workspace/research
chown -R 1000:1000 /var/openclaw

# ── Step 6: Generate secrets ──────────────────────────────
log "Step 6/7: Generating security tokens..."
GATEWAY_TOKEN=$(openssl rand -hex 32)
info "Your gateway token (save this): $GATEWAY_TOKEN"

# ── Step 7: Summary ──────────────────────────────────────
log "Step 7/7: Setup complete!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}VPS is ready for OpenClaw deployment!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Next steps:"
echo "  1. Clone your repo:  git clone YOUR_REPO_URL $DEPLOY_DIR/app"
echo "  2. Copy env:         cp $DEPLOY_DIR/app/deploy/env.example $DEPLOY_DIR/app/deploy/.env"
echo "  3. Edit secrets:     nano $DEPLOY_DIR/app/deploy/.env"
echo "  4. Build + start:    cd $DEPLOY_DIR/app && docker compose -f deploy/docker-compose.yml up -d --build"
echo "  5. Check logs:       docker compose -f deploy/docker-compose.yml logs -f"
echo ""
echo "To access the dashboard from your laptop:"
echo "  ssh -N -L 18789:127.0.0.1:18789 root@YOUR_VPS_IP"
echo "  Then open: http://127.0.0.1:18789"
echo "  Paste gateway token: $GATEWAY_TOKEN"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
