#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
# End-to-End Deployment Verification — PositionedUp
# Run this after deploying to verify everything works
#
# Usage:
#   bash deploy/verify-deployment.sh
#   OR from VPS:
#   bash /opt/openclaw/app/deploy/verify-deployment.sh
# ─────────────────────────────────────────────────────────

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASS=0
FAIL=0
WARN=0

pass()  { echo -e "  ${GREEN}PASS${NC} $1"; ((PASS++)); }
fail()  { echo -e "  ${RED}FAIL${NC} $1"; ((FAIL++)); }
warn()  { echo -e "  ${YELLOW}WARN${NC} $1"; ((WARN++)); }
info()  { echo -e "  ${BLUE}INFO${NC} $1"; }

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  PositionedUp — Deployment Verification"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── 1. Docker ────────────────────────────────────────────
echo "▸ Docker Environment"
if command -v docker &>/dev/null; then
    pass "Docker installed: $(docker --version 2>/dev/null | head -1)"
else
    fail "Docker not installed"
fi

if docker compose version &>/dev/null; then
    pass "Docker Compose available"
else
    fail "Docker Compose not available"
fi

# ── 2. Container Status ─────────────────────────────────
echo ""
echo "▸ Container Status"
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "openclaw-gateway"; then
    CONTAINER_STATUS=$(docker inspect --format='{{.State.Status}}' openclaw-gateway 2>/dev/null)
    if [ "$CONTAINER_STATUS" = "running" ]; then
        pass "openclaw-gateway container is running"
        UPTIME=$(docker inspect --format='{{.State.StartedAt}}' openclaw-gateway 2>/dev/null)
        info "Started at: $UPTIME"
    else
        fail "openclaw-gateway container status: $CONTAINER_STATUS"
    fi
else
    fail "openclaw-gateway container not found"
fi

# ── 3. Gateway Health ────────────────────────────────────
echo ""
echo "▸ Gateway Health"
GATEWAY_URL="http://127.0.0.1:18789"

if curl -sf "$GATEWAY_URL/health" &>/dev/null; then
    pass "Gateway health endpoint responding"
else
    fail "Gateway health endpoint not responding at $GATEWAY_URL/health"
fi

# ── 4. Environment Variables ─────────────────────────────
echo ""
echo "▸ Environment Variables (inside container)"
REQUIRED_VARS="OPENCLAW_GATEWAY_TOKEN OPENAI_API_KEY TELEGRAM_BOT_TOKEN TELEGRAM_OWNER_CHAT_ID"

for var in $REQUIRED_VARS; do
    VAL=$(docker exec openclaw-gateway printenv "$var" 2>/dev/null || echo "")
    if [ -n "$VAL" ] && [ "$VAL" != "CHANGE_ME_generate_with_openssl_rand_hex_32" ]; then
        pass "$var is set"
    else
        fail "$var is missing or has placeholder value"
    fi
done

OPTIONAL_VARS="POSITIONEDUP_API_URL AGENT_API_KEY POSTHOG_API_KEY GOOGLE_ACCESS_TOKEN"
for var in $OPTIONAL_VARS; do
    VAL=$(docker exec openclaw-gateway printenv "$var" 2>/dev/null || echo "")
    if [ -n "$VAL" ]; then
        pass "$var is set"
    else
        warn "$var is not set (optional)"
    fi
done

# ── 5. Firewall ──────────────────────────────────────────
echo ""
echo "▸ Firewall (UFW)"
if command -v ufw &>/dev/null; then
    UFW_STATUS=$(ufw status 2>/dev/null | head -1)
    if echo "$UFW_STATUS" | grep -qi "active"; then
        pass "UFW firewall is active"
        # Check that 18789 is NOT open publicly
        if ufw status 2>/dev/null | grep -q "18789"; then
            fail "Port 18789 is open in UFW — should only be accessible via SSH tunnel"
        else
            pass "Port 18789 is NOT publicly exposed (good — SSH tunnel only)"
        fi
    else
        warn "UFW firewall is not active"
    fi
else
    warn "UFW not installed"
fi

# ── 6. Fail2ban ──────────────────────────────────────────
echo ""
echo "▸ Fail2ban"
if systemctl is-active --quiet fail2ban 2>/dev/null; then
    pass "Fail2ban is running"
else
    warn "Fail2ban is not running"
fi

# ── 7. Telegram Bot Connectivity ─────────────────────────
echo ""
echo "▸ Telegram Bot"
BOT_TOKEN=$(docker exec openclaw-gateway printenv TELEGRAM_BOT_TOKEN 2>/dev/null || echo "")
if [ -n "$BOT_TOKEN" ] && [ "$BOT_TOKEN" != "123456789:ABCdefGhIjKlMnOpQrStUvWxYz" ]; then
    # Test bot API
    BOT_RESPONSE=$(curl -sf "https://api.telegram.org/bot$BOT_TOKEN/getMe" 2>/dev/null || echo "")
    if echo "$BOT_RESPONSE" | grep -q '"ok":true'; then
        BOT_NAME=$(echo "$BOT_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['username'])" 2>/dev/null || echo "unknown")
        pass "Telegram bot is valid: @$BOT_NAME"
    else
        fail "Telegram bot token is invalid or API unreachable"
    fi
else
    fail "Telegram bot token not configured"
fi

# ── 8. Brain API Connectivity ────────────────────────────
echo ""
echo "▸ Brain API Connection"
API_URL=$(docker exec openclaw-gateway printenv POSITIONEDUP_API_URL 2>/dev/null || echo "")
AGENT_KEY=$(docker exec openclaw-gateway printenv AGENT_API_KEY 2>/dev/null || echo "")

if [ -n "$API_URL" ]; then
    HEALTH=$(curl -sf "$API_URL/health" 2>/dev/null || echo "")
    if echo "$HEALTH" | grep -q '"status"'; then
        pass "Brain API is reachable at $API_URL"
    else
        fail "Brain API not responding at $API_URL"
    fi
else
    warn "POSITIONEDUP_API_URL not set — agents won't connect to Brain"
fi

# ── 9. Disk Space ────────────────────────────────────────
echo ""
echo "▸ System Resources"
DISK_USE=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')
if [ "$DISK_USE" -lt 80 ]; then
    pass "Disk usage: ${DISK_USE}%"
elif [ "$DISK_USE" -lt 90 ]; then
    warn "Disk usage: ${DISK_USE}% (getting high)"
else
    fail "Disk usage: ${DISK_USE}% (critical)"
fi

MEM_AVAIL=$(free -m | awk 'NR==2 {print $7}')
if [ "$MEM_AVAIL" -gt 512 ]; then
    pass "Available memory: ${MEM_AVAIL}MB"
elif [ "$MEM_AVAIL" -gt 256 ]; then
    warn "Available memory: ${MEM_AVAIL}MB (low)"
else
    fail "Available memory: ${MEM_AVAIL}MB (critical)"
fi

# ── 10. OpenClaw Agent Files ─────────────────────────────
echo ""
echo "▸ Agent Configuration"
AGENT_FILES="SOUL.md HEARTBEAT.md task_board.md openclaw.json"
for f in $AGENT_FILES; do
    if docker exec openclaw-gateway test -f "/home/openclaw/.openclaw/workspace/$f" 2>/dev/null; then
        pass "Found: $f"
    else
        fail "Missing: $f"
    fi
done

AGENT_DIRS="agents/jumbo agents/trend-analyzer agents/copywriter agents/visual-designer agents/distributor agents/analytics"
for d in $AGENT_DIRS; do
    if docker exec openclaw-gateway test -d "/home/openclaw/.openclaw/workspace/$d" 2>/dev/null; then
        pass "Agent dir: $d"
    else
        fail "Missing agent dir: $d"
    fi
done

# ── 11. Container Logs Check ─────────────────────────────
echo ""
echo "▸ Recent Logs (last 5 lines)"
docker logs openclaw-gateway --tail 5 2>&1 | while IFS= read -r line; do
    info "$line"
done

# ── Summary ──────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
TOTAL=$((PASS + FAIL + WARN))
echo -e "  Results: ${GREEN}${PASS} passed${NC}  ${RED}${FAIL} failed${NC}  ${YELLOW}${WARN} warnings${NC}  (${TOTAL} total)"

if [ "$FAIL" -eq 0 ]; then
    echo -e "  ${GREEN}✓ Deployment is healthy!${NC}"
else
    echo -e "  ${RED}✗ ${FAIL} issue(s) need attention${NC}"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

exit $FAIL
