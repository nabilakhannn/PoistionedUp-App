"""
Seed script -- creates test data for local development.

Run: cd apps/api && source .venv/bin/activate && python -m scripts.seed

Creates:
  - 1 test user (test@example.com / testpass123)
  - 1 profile with sample voice/audience
  - 3 resources (1 link, 1 note, 1 transcript; 1 gold)
  - Resource chunks for each
  - 1 completed workflow with content assets
  - 1 queued workflow (for testing worker)
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "testpass123"


def main():
    admin = create_client(SUPABASE_URL, SERVICE_ROLE_KEY)

    # ── 1. Create test user ──────────────────────────────────
    print("Creating test user...")
    try:
        resp = admin.auth.admin.create_user({
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "email_confirm": True,
        })
        user_id = resp.user.id
        print(f"  Created: {TEST_EMAIL} (id: {user_id})")
    except Exception as e:
        if "already been registered" in str(e) or "already exists" in str(e):
            # User exists -- find their ID
            users = admin.auth.admin.list_users()
            user_id = next(u.id for u in users if u.email == TEST_EMAIL)
            print(f"  Already exists: {TEST_EMAIL} (id: {user_id})")
        else:
            raise

    # ── 2. Create profile ────────────────────────────────────
    print("Creating profile...")
    admin.table("profiles").upsert({
        "user_id": user_id,
        "profile_json": {
            "channel_name": "TechExplorer",
            "niche": "Technology & AI",
            "audience": {
                "age_range": "25-40",
                "interests": ["artificial intelligence", "startups", "productivity"],
                "pain_points": ["information overload", "keeping up with AI"],
            },
            "voice": {
                "tone": "conversational, curious, slightly contrarian",
                "avoid": ["clickbait", "hype without substance", "jargon without explanation"],
                "signature_phrases": ["Here's what nobody's talking about", "Let me break this down"],
            },
            "guardrails": {
                "banned_topics": ["politics", "religion"],
                "max_script_length_words": 3000,
                "preferred_hook_types": ["curiosity", "contrarian", "data"],
            },
        },
    }).execute()
    print("  Profile created with voice + audience settings.")

    # ── 3. Create resources ──────────────────────────────────
    print("Creating resources...")

    res_link = admin.table("resources").insert({
        "user_id": user_id,
        "type": "link",
        "title": "OpenAI o3 announcement",
        "source_url": "https://openai.com/blog/o3",
        "tags": ["ai", "openai", "reasoning"],
        "is_gold": True,
        "content_text": "OpenAI announced o3, a new reasoning model that achieves breakthrough performance on ARC-AGI benchmarks...",
    }).execute()

    res_note = admin.table("resources").insert({
        "user_id": user_id,
        "type": "note",
        "title": "My take on AI agents",
        "tags": ["ai", "agents", "opinion"],
        "is_gold": False,
        "content_text": "I think AI agents are overhyped right now. Most 'agents' are just prompt chains. Real agents need to handle failure, retry, and adapt. The ones that work are narrow and domain-specific.",
    }).execute()

    res_transcript = admin.table("resources").insert({
        "user_id": user_id,
        "type": "transcript",
        "title": "Competitor video: Why AI won't replace developers",
        "source_url": "https://youtube.com/watch?v=example",
        "tags": ["competitors", "ai", "development"],
        "is_gold": False,
        "content_text": "Today we're going to talk about why AI won't replace developers. First, let me show you what happened when I tried to build an entire app with AI...",
    }).execute()

    print(f"  Created 3 resources (1 gold)")

    # ── 4. Create resource chunks ────────────────────────────
    print("Creating resource chunks...")
    for i, res in enumerate([res_link, res_note, res_transcript]):
        res_id = res.data[0]["id"]
        text = res.data[0]["content_text"]
        # Simple chunking: split into ~100 char chunks for demo
        chunks = [text[j:j+100] for j in range(0, len(text), 100)]
        for idx, chunk in enumerate(chunks):
            admin.table("resource_chunks").insert({
                "resource_id": res_id,
                "chunk_index": idx,
                "chunk_text": chunk,
            }).execute()
    print(f"  Chunks created for all resources.")

    # ── 5. Create workflows ──────────────────────────────────
    print("Creating workflows...")

    # Completed workflow (for UI development)
    wf_done = admin.table("workflows").insert({
        "user_id": user_id,
        "status": "approved",
        "goal_text": "Create a video about AI agents that actually work vs hype",
        "current_step": "approval",
        "active_version": 1,
        "settings": {
            "sources": {"youtube": True, "reddit": True, "newsletters": True, "news": True},
        },
        "profile_snapshot": {"channel_name": "TechExplorer", "niche": "Technology & AI"},
    }).execute()

    wf_done_id = wf_done.data[0]["id"]

    # Queued workflow (for testing worker)
    wf_queued = admin.table("workflows").insert({
        "user_id": user_id,
        "status": "queued",
        "goal_text": "Explore the future of coding with AI pair programmers",
        "settings": {
            "sources": {"youtube": True, "reddit": True, "newsletters": True},
        },
        "profile_snapshot": {"channel_name": "TechExplorer", "niche": "Technology & AI"},
    }).execute()

    print(f"  Created 2 workflows (1 approved, 1 queued)")

    # ── 6. Create content assets for completed workflow ──────
    print("Creating content assets...")

    admin.table("content_assets").insert({
        "workflow_id": wf_done_id, "type": "youtube_long", "version": 1,
        "status": "approved",
        "content_json": {
            "title": "AI Agents Are a Lie (Here's What Actually Works)",
            "hook": "Everyone's talking about AI agents. But 90% of them are fake.",
            "script": "HOOK: Everyone's talking about AI agents...\n\nACT 1: The hype...\n\nACT 2: What actually works...\n\nACT 3: The future...\n\nCTA: Subscribe for more honest AI takes.",
            "word_count": 2800,
        },
    }).execute()

    for i in range(3):
        admin.table("content_assets").insert({
            "workflow_id": wf_done_id, "type": "youtube_short", "version": 1,
            "status": "approved",
            "content_json": {
                "title": f"AI Agents Short #{i+1}",
                "hook": f"Short hook {i+1}",
                "script": f"Short script content {i+1}",
                "cta": "Follow for more",
            },
        }).execute()

    admin.table("content_assets").insert({
        "workflow_id": wf_done_id, "type": "title_set", "version": 1,
        "status": "approved",
        "content_json": {
            "titles": [
                "AI Agents Are a Lie (Here's What Actually Works)",
                "I Tested Every AI Agent. Most Are Fake.",
                "The Truth About AI Agents Nobody Tells You",
            ],
        },
    }).execute()

    admin.table("content_assets").insert({
        "workflow_id": wf_done_id, "type": "description", "version": 1,
        "status": "approved",
        "content_json": {"text": "In this video I break down the AI agent hype..."},
    }).execute()

    admin.table("content_assets").insert({
        "workflow_id": wf_done_id, "type": "tags", "version": 1,
        "status": "approved",
        "content_json": {"tags": ["AI agents", "artificial intelligence", "AI hype", "tech"]},
    }).execute()

    print(f"  Created 7 content assets for completed workflow.")

    # ── 7. Create audit events ───────────────────────────────
    print("Creating audit events...")
    for event in ["workflow_created", "topic_selected", "hook_selected", "approved"]:
        admin.table("audit_events").insert({
            "user_id": user_id, "workflow_id": wf_done_id,
            "event_type": event, "payload": {},
        }).execute()
    print(f"  Created 4 audit events.")

    # ── 8. Create usage costs ────────────────────────────────
    print("Creating usage costs...")
    steps = [
        ("signal_research", "gpt-4o", 2000, 1500, 0.035),
        ("gap_analysis_topic_candidates", "gpt-4o", 3000, 2000, 0.050),
        ("hook_lab", "gpt-4o", 1500, 1000, 0.025),
        ("script_generation", "gpt-4o", 4000, 3000, 0.070),
        ("editor", "gpt-4o-mini", 3000, 2000, 0.003),
        ("testing", "gpt-4o-mini", 2000, 500, 0.001),
    ]
    for step_id, model, inp, out, cost in steps:
        admin.table("usage_costs").insert({
            "workflow_id": wf_done_id, "user_id": user_id,
            "step_id": step_id, "model_name": model,
            "input_tokens": inp, "output_tokens": out,
            "estimated_cost": cost,
        }).execute()
    print(f"  Created 6 usage cost records (total: $0.184)")

    # ── Done ─────────────────────────────────────────────────
    print("\n✓ Seed complete!")
    print(f"  Login: {TEST_EMAIL} / {TEST_PASSWORD}")
    print(f"  User ID: {user_id}")
    print(f"  Completed workflow: {wf_done_id}")
    print(f"  Queued workflow: {wf_queued.data[0]['id']}")


if __name__ == "__main__":
    main()
