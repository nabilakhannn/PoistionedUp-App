#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
# Telegram Bot Setup & Verification — PositionedUp
#
# This script helps you:
#   1. Verify your Telegram bot token works
#   2. Find your Telegram user/chat ID
#   3. Send a test message from the bot
#
# Prerequisites:
#   - Create a bot via @BotFather on Telegram (/newbot)
#   - Have the bot token ready
#
# Usage:
#   bash deploy/telegram-setup.sh
# ─────────────────────────────────────────────────────────

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  PositionedUp — Telegram Bot Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── Step 1: Get bot token ────────────────────────────────
echo -e "${BLUE}Step 1: Bot Token${NC}"
echo ""
echo "If you haven't created a bot yet:"
echo "  1. Open Telegram and search for @BotFather"
echo "  2. Send /newbot"
echo "  3. Choose a name: 'PositionedUp Agent'"
echo "  4. Choose a username: 'positionedup_agent_bot'"
echo "  5. Copy the token it gives you"
echo ""

if [ -n "${TELEGRAM_BOT_TOKEN:-}" ]; then
    echo -e "${GREEN}Using TELEGRAM_BOT_TOKEN from environment${NC}"
    BOT_TOKEN="$TELEGRAM_BOT_TOKEN"
else
    read -rp "Paste your bot token: " BOT_TOKEN
fi

if [ -z "$BOT_TOKEN" ]; then
    echo -e "${RED}No token provided. Exiting.${NC}"
    exit 1
fi

# ── Step 2: Verify bot token ────────────────────────────
echo ""
echo -e "${BLUE}Step 2: Verifying bot token...${NC}"

RESPONSE=$(curl -sf "https://api.telegram.org/bot$BOT_TOKEN/getMe" 2>/dev/null || echo '{"ok":false}')

if echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['ok']" 2>/dev/null; then
    BOT_USERNAME=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['username'])")
    BOT_NAME=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['first_name'])")
    echo -e "${GREEN}✓ Bot verified: @${BOT_USERNAME} (${BOT_NAME})${NC}"
else
    echo -e "${RED}✗ Invalid bot token. Please check and try again.${NC}"
    exit 1
fi

# ── Step 3: Find chat ID ────────────────────────────────
echo ""
echo -e "${BLUE}Step 3: Finding your Chat ID${NC}"
echo ""
echo "To find your chat ID:"
echo "  1. Open Telegram"
echo "  2. Send any message to @${BOT_USERNAME}"
echo "  3. Press Enter here after sending the message"
echo ""
read -rp "Press Enter after you've sent a message to the bot... "

UPDATES=$(curl -sf "https://api.telegram.org/bot$BOT_TOKEN/getUpdates" 2>/dev/null || echo '{"ok":false,"result":[]}')

CHAT_ID=$(echo "$UPDATES" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if data['ok'] and data['result']:
    # Get the most recent message's chat ID
    latest = data['result'][-1]
    msg = latest.get('message', latest.get('edited_message', {}))
    chat = msg.get('chat', {})
    chat_id = chat.get('id', '')
    username = chat.get('username', 'unknown')
    first_name = chat.get('first_name', 'unknown')
    print(f'{chat_id}|{username}|{first_name}')
else:
    print('')
" 2>/dev/null || echo "")

if [ -n "$CHAT_ID" ]; then
    IFS='|' read -r OWNER_ID OWNER_USER OWNER_NAME <<< "$CHAT_ID"
    echo -e "${GREEN}✓ Found your chat!${NC}"
    echo -e "  Name: ${OWNER_NAME}"
    echo -e "  Username: @${OWNER_USER}"
    echo -e "  Chat ID: ${GREEN}${OWNER_ID}${NC}"
else
    echo -e "${YELLOW}⚠ No messages found. Make sure you sent a message to @${BOT_USERNAME}${NC}"
    echo "You can also get your chat ID by messaging @userinfobot on Telegram"
    read -rp "Enter your chat ID manually: " OWNER_ID
fi

if [ -z "${OWNER_ID:-}" ]; then
    echo -e "${RED}No chat ID. Exiting.${NC}"
    exit 1
fi

# ── Step 4: Send test message ────────────────────────────
echo ""
echo -e "${BLUE}Step 4: Sending test message...${NC}"

TEST_MSG="🤖 *PositionedUp Agent Squad — Connected!*

Your Telegram channel is now linked to the OpenClaw gateway.

*Bot:* @${BOT_USERNAME}
*Owner:* Chat ID ${OWNER_ID}
*Status:* Ready for deployment

Jumbo and the squad will message you here for:
• Task approvals & content reviews
• Weekly trend reports
• Performance insights
• Alert notifications"

SEND_RESULT=$(curl -sf -X POST "https://api.telegram.org/bot$BOT_TOKEN/sendMessage" \
    -H "Content-Type: application/json" \
    -d "{
        \"chat_id\": \"$OWNER_ID\",
        \"text\": $(python3 -c "import json; print(json.dumps('''$TEST_MSG'''))"),
        \"parse_mode\": \"Markdown\"
    }" 2>/dev/null || echo '{"ok":false}')

if echo "$SEND_RESULT" | python3 -c "import sys,json; assert json.load(sys.stdin)['ok']" 2>/dev/null; then
    echo -e "${GREEN}✓ Test message sent! Check your Telegram.${NC}"
else
    echo -e "${RED}✗ Failed to send test message. Check bot permissions.${NC}"
fi

# ── Summary ──────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}Setup Complete!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Add these to your deploy/.env file:"
echo ""
echo -e "  ${YELLOW}TELEGRAM_BOT_TOKEN=${BOT_TOKEN}${NC}"
echo -e "  ${YELLOW}TELEGRAM_OWNER_CHAT_ID=${OWNER_ID}${NC}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
