# ─────────────────────────────────────────────────────────
# OpenClaw VPS Dockerfile — PositionedUp Agent Squad
# Hostinger / Hetzner / Any Ubuntu VPS with Docker
# ─────────────────────────────────────────────────────────
FROM node:22-bookworm

# System dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      socat curl ca-certificates git python3 python3-pip && \
    rm -rf /var/lib/apt/lists/*

# ── Install Python analytics deps (PostHog) ──────────────
RUN pip3 install --break-system-packages posthog python-dotenv

# ── Install OpenClaw globally ─────────────────────────────
RUN npm install -g openclaw@latest

# ── Create non-root user (reuse existing GID 1000 from node image) ──
RUN useradd -u 1001 -g 1000 -m -s /bin/bash openclaw

# ── Set up workspace directories ─────────────────────────
RUN mkdir -p /home/openclaw/.openclaw/workspace && \
    chown -R openclaw:node /home/openclaw/.openclaw

# ── Copy agent configs into workspace ─────────────────────
COPY --chown=openclaw:node agents/ /home/openclaw/.openclaw/workspace/agents/
COPY --chown=openclaw:node openclaw.json /home/openclaw/.openclaw/workspace/openclaw.json
COPY --chown=openclaw:node SOUL.md /home/openclaw/.openclaw/workspace/SOUL.md
COPY --chown=openclaw:node AGENTS.md /home/openclaw/.openclaw/workspace/AGENTS.md
COPY --chown=openclaw:node HEARTBEAT.md /home/openclaw/.openclaw/workspace/HEARTBEAT.md
COPY --chown=openclaw:node task_board.md /home/openclaw/.openclaw/workspace/task_board.md
COPY --chown=openclaw:node AGENT_BRIDGE_PLAYBOOK.md /home/openclaw/.openclaw/workspace/AGENT_BRIDGE_PLAYBOOK.md
COPY --chown=openclaw:node analytics/ /home/openclaw/.openclaw/workspace/analytics/

# ── Copy workspace sub-directories ────────────────────────
RUN mkdir -p /home/openclaw/.openclaw/workspace/drafts \
             /home/openclaw/.openclaw/workspace/assets \
             /home/openclaw/.openclaw/workspace/archive \
             /home/openclaw/.openclaw/workspace/research && \
    chown -R openclaw:node /home/openclaw/.openclaw/workspace

USER openclaw
WORKDIR /home/openclaw/.openclaw/workspace

ENV HOME=/home/openclaw
ENV NODE_ENV=production
ENV TERM=xterm-256color

# Default command: start the OpenClaw gateway (loopback = only accessible via SSH tunnel)
CMD ["openclaw", "gateway", "--bind", "loopback", "--port", "18789"]
