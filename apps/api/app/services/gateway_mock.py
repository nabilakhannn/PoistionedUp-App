"""Mock OpenClaw Gateway: realistic demo data for local development.

When OPENCLAW_MOCK_MODE=true, the gateway client delegates to these
functions instead of making real HTTP calls to the VPS. This lets the
Gateway Dashboard and Agent Chat work in dev without a running gateway.

All data is synthetic but structurally identical to real gateway responses.
"""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

# ── Mock Agent Personas ───────────────────────────────────────

_MOCK_AGENTS: List[Dict[str, Any]] = [
    {
        "id": "jumbo",
        "name": "Jumbo (Orchestrator)",
        "status": "active",
        "model": "gpt-4o",
        "workspace": "./agents/jumbo",
        "channels": ["telegram"],
        "is_default": True,
    },
    {
        "id": "trend-analyzer",
        "name": "Trend Analyzer",
        "status": "idle",
        "model": "gpt-4o-mini",
        "workspace": "./agents/trend-analyzer",
        "channels": [],
        "is_default": False,
    },
    {
        "id": "copywriter",
        "name": "Copywriter",
        "status": "idle",
        "model": "gpt-4o",
        "workspace": "./agents/copywriter",
        "channels": [],
        "is_default": False,
    },
    {
        "id": "visual-designer",
        "name": "Visual Designer",
        "status": "idle",
        "model": "gpt-4o",
        "workspace": "./agents/visual-designer",
        "channels": [],
        "is_default": False,
    },
    {
        "id": "distributor",
        "name": "Distributor",
        "status": "idle",
        "model": "gpt-4o-mini",
        "workspace": "./agents/distributor",
        "channels": [],
        "is_default": False,
    },
    {
        "id": "analytics",
        "name": "Analytics",
        "status": "idle",
        "model": "gpt-4o-mini",
        "workspace": "./agents/analytics",
        "channels": [],
        "is_default": False,
    },
]

# ── Mock Chat Responses ───────────────────────────────────────

_MOCK_RESPONSES: Dict[str, List[str]] = {
    "jumbo": [
        "I'm Jumbo, the orchestrator. I coordinate all 6 agents in the PositionedUp squad. "
        "I can delegate research to the Trend Analyzer, content creation to the Copywriter, "
        "visuals to the Visual Designer, distribution to the Distributor, and analytics tracking "
        "to the Analytics agent. What would you like me to work on?",
        "Great question! Let me delegate that to the appropriate specialist agent. "
        "I'll create a task and assign it. You can track progress in the Orchestrator tab.",
        "All agents are currently idle and ready for tasks. The weekly trend research "
        "is scheduled for Saturday 10 AM EST. Would you like me to run it now instead?",
    ],
    "trend-analyzer": [
        "I specialize in researching market trends, competitor intelligence, and audience insights. "
        "I use web search and the knowledge base to find actionable data for your content strategy.",
        "Based on my latest research, the top trending topics in personal branding for 2026 are: "
        "AI-augmented thought leadership, authentic vulnerability in corporate content, "
        "and short-form video storytelling on LinkedIn.",
    ],
    "copywriter": [
        "I'm the Copywriter agent. I create LinkedIn posts, Twitter threads, video scripts, "
        "and other content following your brand voice and the Writing Rules Engine. "
        "I always check against your Voice DNA profile before finalizing.",
        "Here's a draft LinkedIn post based on your brand voice:\n\n"
        "The best leaders don't have all the answers.\n\n"
        "They have the courage to ask better questions.\n\n"
        "In my 10 years building teams, the turning point was always the same: "
        "the moment I stopped pretending and started listening.\n\n"
        "What's the hardest question you've asked your team this week?",
    ],
    "visual-designer": [
        "I handle visual content creation including image concepts, carousel layouts, "
        "and brand-consistent design suggestions. I work with your brand colors and style guide.",
    ],
    "distributor": [
        "I manage content distribution across platforms. I can schedule posts to LinkedIn, "
        "Twitter/X, and other channels. I always verify content is approved before posting.",
    ],
    "analytics": [
        "I track content performance metrics across all platforms. I can generate reports "
        "on engagement rates, audience growth, and content effectiveness.",
    ],
}

_start_time = datetime.now(timezone.utc)


# ── Mock Functions ────────────────────────────────────────────


async def mock_check_health() -> Dict[str, Any]:
    """Return mock healthy gateway status."""
    uptime_secs = (datetime.now(timezone.utc) - _start_time).total_seconds()
    hours = int(uptime_secs // 3600)
    mins = int((uptime_secs % 3600) // 60)

    return {
        "connected": True,
        "status": "healthy",
        "latency_ms": round(random.uniform(1.0, 5.0), 1),
        "gateway_url": "mock://localhost (demo mode)",
        "version": "1.0.0-mock",
        "uptime": f"{hours}h {mins}m",
        "agents_loaded": len(_MOCK_AGENTS),
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "mock_mode": True,
    }


async def mock_list_agents() -> List[Dict[str, Any]]:
    """Return the 6-agent squad with mock statuses."""
    return [dict(a) for a in _MOCK_AGENTS]


async def mock_get_sessions() -> List[Dict[str, Any]]:
    """Return a few mock active sessions."""
    now = datetime.now(timezone.utc)
    return [
        {
            "id": f"sess-{uuid.uuid4().hex[:8]}",
            "agent_id": "jumbo",
            "status": "active",
            "created_at": (now - timedelta(minutes=15)).isoformat(),
            "last_activity": (now - timedelta(minutes=2)).isoformat(),
            "message_count": 7,
        },
        {
            "id": f"sess-{uuid.uuid4().hex[:8]}",
            "agent_id": "trend-analyzer",
            "status": "active",
            "created_at": (now - timedelta(hours=1)).isoformat(),
            "last_activity": (now - timedelta(minutes=30)).isoformat(),
            "message_count": 3,
        },
    ]


async def mock_send_message(
    agent_id: str,
    message: str,
    *,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Return a mock agent response based on agent persona."""
    responses = _MOCK_RESPONSES.get(agent_id, [
        f"[Mock] Agent '{agent_id}' received your message. "
        "This is a demo response — connect a real gateway to get live agent responses.",
    ])

    response_text = random.choice(responses)

    return {
        "session_id": session_id or f"sess-{uuid.uuid4().hex[:8]}",
        "status": "delivered",
        "response": response_text,
        "agent_id": agent_id,
        "message_id": f"msg-{uuid.uuid4().hex[:8]}",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
