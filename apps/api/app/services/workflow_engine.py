"""Workflow Engine — Slice 109.

Registry of all 24 agent workflows + execution engine + enhancement injection.
Built-in AI (Claude Sonnet 4.6 + Perplexity + Gemini) is the PRIMARY engine.
Manus AI is optional BYOK for 5 research-heavy workflows only.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from app.config import settings
from app.deps import get_admin_client

logger = logging.getLogger("app.services.workflow_engine")

# ── Workflow Registry ─────────────────────────────────────────────────────

WORKFLOW_CATEGORIES = {
    "ads_funnels": {"name": "Ads & Funnels", "icon": "rocket", "order": 1},
    "content_marketing": {"name": "Content Marketing", "icon": "pencil", "order": 2},
    "lead_gen": {"name": "Lead Generation", "icon": "users", "order": 3},
    "email_marketing": {"name": "Email Marketing", "icon": "envelope", "order": 4},
    "strategy": {"name": "Strategy & Coaching", "icon": "lightbulb", "order": 5},
}

WORKFLOW_REGISTRY: Dict[str, Dict[str, Any]] = {
    # ── Ads & Funnels (7) ─────────────────────────────────────
    "vsl-funnel-generator": {
        "name": "VSL Funnel Generator",
        "category": "ads_funnels",
        "icon": "rocket",
        "tags": ["VSL", "Funnels"],
        "description": "7-step VSL funnel: context -> landing page -> script -> emails -> ads.",
        "status": "active",
        "multi_step": True,
        "steps": [
            {"name": "Context Window", "prompt_key": "vsl_step1_context"},
            {"name": "Landing Page", "prompt_key": "vsl_step2_landing_page"},
            {"name": "VSL Script", "prompt_key": "vsl_step3_vsl_script"},
            {"name": "Opt-In Emails (20)", "prompt_key": "vsl_step4_optin_emails"},
            {"name": "Broadcast Emails", "prompt_key": "vsl_step5_broadcast"},
            {"name": "Static Ads", "prompt_key": "vsl_step6_static_ads"},
            {"name": "Video Ad Scripts", "prompt_key": "vsl_step7_video_ads"},
        ],
        "inputs": [
            {"name": "offer_type", "type": "select", "label": "Offer Type",
             "options": ["B2B Service", "B2C Product", "Course/Info", "SaaS", "Agency"], "required": True},
            {"name": "target_market", "type": "select", "label": "Market",
             "options": ["B2B", "B2C", "Both"], "required": True},
            {"name": "offer_description", "type": "textarea", "label": "Describe your offer", "required": True},
        ],
        "base_prompt": (
            "You are a world-class direct response copywriter and funnel architect. "
            "Build a complete VSL funnel for the following offer.\n\n"
            "Offer Type: {offer_type}\nMarket: {target_market}\n"
            "Offer: {offer_description}\n\n"
        ),
        "estimated_tokens": 15000,
        "engine": "builtin",
        "enhancements": ["brand_dossier", "story_bank", "hook_library", "qa_gate"],
    },
    "landing-page-generator": {
        "name": "Landing Page Generator",
        "category": "ads_funnels",
        "icon": "globe",
        "tags": ["Landing Page", "Copy"],
        "description": "AI writes sales copy + full HTML/Tailwind landing page.",
        "status": "active",
        "multi_step": False,
        "inputs": [
            {"name": "page_type", "type": "select", "label": "Page Type",
             "options": ["B2B Sales Page", "B2C Sales Page", "Adaptive", "Opt-In Page"], "required": True},
            {"name": "offer_description", "type": "textarea", "label": "Describe your offer", "required": True},
            {"name": "generate_html", "type": "select", "label": "Output Format",
             "options": ["Copy Only", "Full HTML + Tailwind"], "required": True},
        ],
        "base_prompt": (
            "You are a conversion-focused landing page copywriter. "
            "Write compelling sales copy for a {page_type}.\n\n"
            "Offer: {offer_description}\n\n"
            "Output format: {generate_html}\n"
        ),
        "estimated_tokens": 5000,
        "engine": "builtin",
        "enhancements": ["brand_dossier", "story_bank", "qa_gate"],
    },
    "funnel-strategy-agent": {
        "name": "Funnel Strategy Agent",
        "category": "ads_funnels",
        "icon": "funnel",
        "tags": ["Strategy", "Funnels"],
        "description": "Design your complete funnel architecture with traffic sources and conversion points.",
        "status": "active",
        "multi_step": False,
        "inputs": [
            {"name": "business_model", "type": "select", "label": "Business Model",
             "options": ["Service-Based", "Product-Based", "Course/Info", "SaaS", "Agency"], "required": True},
            {"name": "current_traffic", "type": "textarea", "label": "Current traffic sources & volume", "required": True},
            {"name": "revenue_goal", "type": "text", "label": "Monthly revenue goal", "required": True},
        ],
        "base_prompt": (
            "You are a funnel strategist. Design a complete funnel architecture.\n\n"
            "Business Model: {business_model}\nCurrent Traffic: {current_traffic}\n"
            "Revenue Goal: {revenue_goal}\n\n"
            "Include: traffic sources, opt-in offer, nurture sequence, sales mechanism, upsells."
        ),
        "estimated_tokens": 4000,
        "engine": "builtin",
        "enhancements": ["brand_dossier", "competitor_intel"],
    },
    "static-ad-generator": {
        "name": "Static Ad Generator",
        "category": "ads_funnels",
        "icon": "image",
        "tags": ["Ads", "Creative"],
        "description": "40 ad variations across 5 hook types. Bulk creative engine.",
        "status": "active",
        "multi_step": False,
        "inputs": [
            {"name": "topic", "type": "textarea", "label": "Ad topic or angle", "required": True},
            {"name": "platform", "type": "select", "label": "Platform",
             "options": ["Facebook/Instagram", "LinkedIn", "Twitter/X", "Google", "All"], "required": True},
        ],
        "base_prompt": (
            "Generate compelling ad creative variations for the following.\n\n"
            "Topic: {topic}\nPlatform: {platform}\n"
        ),
        "estimated_tokens": 6000,
        "engine": "builtin",
        "enhancements": ["brand_dossier", "hook_library"],
    },
    "video-ad-scripts": {
        "name": "Video Ad Scripts",
        "category": "ads_funnels",
        "icon": "video",
        "tags": ["Video", "Ads"],
        "description": "Short-form video ad scripts optimized for UGC, talking head, or animated.",
        "status": "active",
        "multi_step": False,
        "inputs": [
            {"name": "ad_style", "type": "select", "label": "Ad Style",
             "options": ["UGC Testimonial", "Talking Head", "Problem-Solution", "Story-Based"], "required": True},
            {"name": "product_description", "type": "textarea", "label": "Product/service description", "required": True},
            {"name": "duration", "type": "select", "label": "Duration",
             "options": ["15 seconds", "30 seconds", "60 seconds", "90 seconds"], "required": True},
        ],
        "base_prompt": (
            "Write a {duration} {ad_style} video ad script.\n\n"
            "Product: {product_description}\n\n"
            "Include: hook (first 3 seconds), problem, solution, CTA."
        ),
        "estimated_tokens": 2000,
        "engine": "builtin",
        "enhancements": ["brand_dossier", "hook_library"],
    },
    "offer-creation": {
        "name": "Offer Creation (Hormozi)",
        "category": "ads_funnels",
        "icon": "trophy",
        "tags": ["Offer", "Grand Slam"],
        "description": "Build an irresistible Grand Slam Offer using the Hormozi Value Equation.",
        "status": "active",
        "multi_step": False,
        "inputs": [
            {"name": "current_offer", "type": "textarea", "label": "Describe your current offer", "required": True},
            {"name": "price_point", "type": "text", "label": "Current or desired price point", "required": True},
            {"name": "biggest_objection", "type": "textarea", "label": "Biggest objection you hear", "required": True},
        ],
        "base_prompt": (
            "You are Alex Hormozi's strategist. Apply the Grand Slam Offer framework and Value Equation.\n\n"
            "Value = (Dream Outcome x Perceived Likelihood) / (Time Delay x Effort & Sacrifice)\n\n"
            "Current Offer: {current_offer}\nPrice: {price_point}\n"
            "Biggest Objection: {biggest_objection}\n\n"
            "Create: 1) Dream Outcome amplification, 2) Likelihood boosters (guarantees, proof), "
            "3) Time compression tactics, 4) Effort reduction (done-for-you elements), "
            "5) Bonus stack, 6) Irresistible naming, 7) Price anchoring strategy."
        ),
        "estimated_tokens": 4000,
        "engine": "builtin",
        "enhancements": ["brand_dossier", "story_bank"],
    },
    "lp-cro-analyzer": {
        "name": "LP CRO Analyzer",
        "category": "ads_funnels",
        "icon": "chart",
        "tags": ["CRO", "Analysis"],
        "description": "Analyze a live landing page URL for conversion rate optimization opportunities.",
        "status": "active",
        "multi_step": False,
        "inputs": [
            {"name": "page_url", "type": "text", "label": "Landing page URL to analyze", "required": True},
            {"name": "conversion_goal", "type": "select", "label": "Conversion Goal",
             "options": ["Lead Capture", "Sales", "Free Trial", "Demo Booking", "Download"], "required": True},
        ],
        "base_prompt": (
            "Analyze this landing page for conversion rate optimization.\n\n"
            "URL: {page_url}\nGoal: {conversion_goal}\n\n"
            "Score each: headline, CTA, social proof, urgency, mobile UX, load speed, trust signals. "
            "Provide specific rewrite suggestions for weak areas."
        ),
        "estimated_tokens": 4000,
        "engine": "manus_beneficial",
        "enhancements": ["brand_dossier"],
    },

    # ── Content Marketing (5) ─────────────────────────────────
    "social-media-post": {
        "name": "Social Media Post",
        "category": "content_marketing",
        "icon": "share",
        "tags": ["Social", "Content"],
        "description": "Generate platform-optimized posts using your brand voice and hook library.",
        "status": "active",
        "multi_step": False,
        "inputs": [
            {"name": "topic", "type": "textarea", "label": "Post topic or angle", "required": True},
            {"name": "platform", "type": "select", "label": "Platform",
             "options": ["LinkedIn", "Twitter/X", "Instagram", "All"], "required": True},
            {"name": "post_style", "type": "select", "label": "Style",
             "options": ["Educational", "Story", "Hot Take", "Listicle", "Case Study"], "required": True},
        ],
        "base_prompt": (
            "Write a {post_style} post for {platform} about:\n{topic}\n\n"
            "Follow platform best practices. Include a strong hook in the first line."
        ),
        "estimated_tokens": 2000,
        "engine": "builtin",
        "enhancements": ["brand_dossier", "story_bank", "hook_library", "qa_gate"],
    },
    "content-research": {
        "name": "Content Research",
        "category": "content_marketing",
        "icon": "search",
        "tags": ["Research", "Trends"],
        "description": "Deep research on topics, competitors, and trending angles for your niche.",
        "status": "active",
        "multi_step": False,
        "inputs": [
            {"name": "research_topic", "type": "textarea", "label": "What to research", "required": True},
            {"name": "depth", "type": "select", "label": "Depth",
             "options": ["Quick scan", "Standard", "Deep dive"], "required": True},
        ],
        "base_prompt": (
            "Research the following topic thoroughly for content creation.\n\n"
            "Topic: {research_topic}\nDepth: {depth}\n\n"
            "Find: trending angles, competitor content, statistics, unique perspectives, content gaps."
        ),
        "estimated_tokens": 5000,
        "engine": "manus_beneficial",
        "enhancements": ["brand_dossier", "competitor_intel"],
    },
    "youtube-script-creator": {
        "name": "YouTube Script Creator",
        "category": "content_marketing",
        "icon": "video",
        "tags": ["YouTube", "Scripts"],
        "description": "Full YouTube video scripts with hooks, retention bumps, and CTAs.",
        "status": "active",
        "multi_step": False,
        "inputs": [
            {"name": "video_topic", "type": "textarea", "label": "Video topic", "required": True},
            {"name": "video_length", "type": "select", "label": "Target Length",
             "options": ["Short (5-8 min)", "Medium (10-15 min)", "Long (20-30 min)"], "required": True},
            {"name": "style", "type": "select", "label": "Style",
             "options": ["Educational", "Story-driven", "Listicle", "Interview Prep"], "required": True},
        ],
        "base_prompt": (
            "Write a {video_length} {style} YouTube script about:\n{video_topic}\n\n"
            "Include: title options (3), thumbnail concepts (2), hook (first 30 seconds), "
            "retention bumps every 2-3 minutes, pattern interrupts, end CTA."
        ),
        "estimated_tokens": 5000,
        "engine": "builtin",
        "enhancements": ["brand_dossier", "story_bank", "hook_library"],
    },
    "zoom-call-repurposer": {
        "name": "Zoom Call Repurposer",
        "category": "content_marketing",
        "icon": "mic",
        "tags": ["Repurpose", "Transcripts"],
        "description": "Turn Zoom call transcripts into 10+ content pieces across platforms.",
        "status": "coming_soon",
        "multi_step": False,
        "inputs": [
            {"name": "transcript", "type": "textarea", "label": "Paste call transcript", "required": True},
        ],
        "base_prompt": "Repurpose this transcript into multiple content pieces.\n\nTranscript:\n{transcript}",
        "estimated_tokens": 8000,
        "engine": "builtin",
        "enhancements": ["brand_dossier", "hook_library"],
    },
    "content-calendar-gen": {
        "name": "Content Calendar Generator",
        "category": "content_marketing",
        "icon": "calendar",
        "tags": ["Calendar", "Planning"],
        "description": "Generate a 30-day content calendar with topics, hooks, and platform assignments.",
        "status": "active",
        "multi_step": False,
        "inputs": [
            {"name": "content_pillars", "type": "textarea", "label": "Your content pillars (3-5 topics)", "required": True},
            {"name": "platforms", "type": "select", "label": "Platforms",
             "options": ["LinkedIn Only", "Twitter/X Only", "LinkedIn + Twitter", "All Platforms"], "required": True},
            {"name": "posts_per_week", "type": "select", "label": "Posts per week",
             "options": ["3", "5", "7", "10", "14"], "required": True},
        ],
        "base_prompt": (
            "Create a 30-day content calendar.\n\n"
            "Pillars: {content_pillars}\nPlatforms: {platforms}\n"
            "Frequency: {posts_per_week} posts/week\n\n"
            "For each post: day, platform, pillar, topic, hook/angle, content type. "
            "Use Messaging Buckets rotation: Pain, Outcome, Story, Authority, Belief, Curiosity."
        ),
        "estimated_tokens": 5000,
        "engine": "builtin",
        "enhancements": ["brand_dossier", "story_bank"],
    },

    # ── Lead Generation (5) ────────────────────────────────────
    "icp-research": {
        "name": "ICP Research",
        "category": "lead_gen",
        "icon": "target",
        "tags": ["ICP", "Research"],
        "description": "4-stage deep research to define your ideal customer profile with Apollo filters.",
        "status": "active",
        "multi_step": False,
        "inputs": [
            {"name": "product_description", "type": "textarea", "label": "Describe your product/service", "required": True},
            {"name": "current_clients", "type": "textarea", "label": "Describe your best clients (optional)", "required": False},
        ],
        "base_prompt": (
            "Research the ideal customer profile for this business.\n\n"
            "Product: {product_description}\n"
            "Best Clients: {current_clients}\n"
        ),
        "estimated_tokens": 6000,
        "engine": "manus_beneficial",
        "enhancements": ["brand_dossier"],
    },
    "cold-email-scriptwriter": {
        "name": "Cold Email Scriptwriter",
        "category": "lead_gen",
        "icon": "envelope",
        "tags": ["Cold Email", "Outreach"],
        "description": "Generate personalized cold email sequences that convert.",
        "status": "active",
        "multi_step": False,
        "inputs": [
            {"name": "target_persona", "type": "textarea", "label": "Who are you emailing?", "required": True},
            {"name": "offer_summary", "type": "textarea", "label": "What are you offering?", "required": True},
            {"name": "sequence_length", "type": "select", "label": "Sequence Length",
             "options": ["3 emails", "5 emails", "7 emails"], "required": True},
        ],
        "base_prompt": (
            "Write a cold email outreach sequence.\n\n"
            "Target: {target_persona}\nOffer: {offer_summary}\n"
            "Length: {sequence_length}\n\n"
            "Each email: subject line, preview text, body (under 150 words), CTA."
        ),
        "estimated_tokens": 4000,
        "engine": "builtin",
        "enhancements": ["brand_dossier", "story_bank", "hook_library"],
    },
    "dream-100-research": {
        "name": "Dream 100 Research",
        "category": "lead_gen",
        "icon": "star",
        "tags": ["Dream 100", "Partnerships"],
        "description": "Research and build your Dream 100 list of ideal partners and prospects.",
        "status": "coming_soon",
        "multi_step": False,
        "inputs": [
            {"name": "niche", "type": "textarea", "label": "Your niche/industry", "required": True},
            {"name": "partnership_type", "type": "select", "label": "Partnership Type",
             "options": ["Podcast Guests", "JV Partners", "Affiliate Partners", "Clients", "All"], "required": True},
        ],
        "base_prompt": "Research Dream 100 prospects for {partnership_type} in {niche}.",
        "estimated_tokens": 8000,
        "engine": "manus_beneficial",
        "enhancements": ["brand_dossier"],
    },
    "meeting-alert-research": {
        "name": "Meeting Alert Research",
        "category": "lead_gen",
        "icon": "bell",
        "tags": ["Meetings", "Prep"],
        "description": "Pre-meeting research briefs on prospects before sales calls.",
        "status": "coming_soon",
        "multi_step": False,
        "inputs": [
            {"name": "prospect_name", "type": "text", "label": "Prospect name", "required": True},
            {"name": "company_name", "type": "text", "label": "Company name", "required": True},
        ],
        "base_prompt": "Research {prospect_name} at {company_name} before a sales call.",
        "estimated_tokens": 3000,
        "engine": "builtin",
        "enhancements": ["brand_dossier"],
    },
    "lead-enrichment": {
        "name": "Lead Enrichment",
        "category": "lead_gen",
        "icon": "database",
        "tags": ["Enrichment", "Data"],
        "description": "Enrich lead data with professional details, pain points, and outreach angles.",
        "status": "active",
        "multi_step": False,
        "inputs": [
            {"name": "lead_name", "type": "text", "label": "Lead name", "required": True},
            {"name": "company", "type": "text", "label": "Company", "required": True},
            {"name": "linkedin_url", "type": "text", "label": "LinkedIn URL (optional)", "required": False},
        ],
        "base_prompt": (
            "Enrich this lead with professional data and outreach angles.\n\n"
            "Name: {lead_name}\nCompany: {company}\nLinkedIn: {linkedin_url}\n"
        ),
        "estimated_tokens": 3000,
        "engine": "manus_beneficial",
        "enhancements": ["brand_dossier"],
    },

    # ── Email Marketing (4) ────────────────────────────────────
    "email-sequence-writer": {
        "name": "Email Sequence Writer",
        "category": "email_marketing",
        "icon": "mail",
        "tags": ["Email", "Sequences"],
        "description": "Complete email sequences for nurture, abandon, pre-call, and more.",
        "status": "active",
        "multi_step": False,
        "inputs": [
            {"name": "sequence_type", "type": "select", "label": "Sequence Type",
             "options": [
                 "Opt-In Nurture (20 emails)",
                 "Broadcast (5/week)",
                 "Abandon Cart (10 emails)",
                 "Pre-Call Warmup (3 emails)",
                 "No-Show Recovery (10 emails)",
                 "Post-Call Follow-Up (10 emails)",
             ], "required": True},
            {"name": "offer_description", "type": "textarea", "label": "Describe your offer", "required": True},
        ],
        "base_prompt": (
            "Write a complete {sequence_type} email sequence.\n\n"
            "Offer: {offer_description}\n\n"
            "For each email: subject line, preview text, body, CTA. "
            "Use storytelling, social proof, and urgency appropriately."
        ),
        "estimated_tokens": 8000,
        "engine": "builtin",
        "enhancements": ["brand_dossier", "story_bank", "hook_library", "qa_gate"],
    },
    "email-flow-writer": {
        "name": "Email Flow Writer",
        "category": "email_marketing",
        "icon": "flow",
        "tags": ["Automation", "Flows"],
        "description": "Design automated email flows with triggers, delays, and conditional logic.",
        "status": "active",
        "multi_step": False,
        "inputs": [
            {"name": "flow_type", "type": "select", "label": "Flow Type",
             "options": ["Welcome Series", "Re-engagement", "Upsell/Cross-sell", "Winback", "Custom"], "required": True},
            {"name": "trigger_event", "type": "text", "label": "Trigger event (e.g., signup, purchase)", "required": True},
        ],
        "base_prompt": (
            "Design an automated email flow.\n\n"
            "Type: {flow_type}\nTrigger: {trigger_event}\n\n"
            "Include: trigger, delay timing, conditional branches, email content for each step."
        ),
        "estimated_tokens": 4000,
        "engine": "builtin",
        "enhancements": ["brand_dossier"],
    },
    "newsletter-generator": {
        "name": "Newsletter Generator",
        "category": "email_marketing",
        "icon": "newspaper",
        "tags": ["Newsletter", "Content"],
        "description": "Generate engaging newsletters with curated content and personal insights.",
        "status": "active",
        "multi_step": False,
        "inputs": [
            {"name": "newsletter_topic", "type": "textarea", "label": "This week's theme or topic", "required": True},
            {"name": "format", "type": "select", "label": "Format",
             "options": ["Single Story Deep Dive", "Curated Roundup (5 items)", "Personal Letter + Tips"], "required": True},
        ],
        "base_prompt": (
            "Write a newsletter.\n\nTopic: {newsletter_topic}\nFormat: {format}\n\n"
            "Include: compelling subject line, preview text, full body with sections, CTA."
        ),
        "estimated_tokens": 3000,
        "engine": "builtin",
        "enhancements": ["brand_dossier", "story_bank", "hook_library"],
    },
    "email-calendar": {
        "name": "Email Calendar",
        "category": "email_marketing",
        "icon": "calendar",
        "tags": ["Calendar", "Planning"],
        "description": "Plan your email marketing calendar for the next 30 days.",
        "status": "coming_soon",
        "multi_step": False,
        "inputs": [
            {"name": "email_list_size", "type": "text", "label": "List size", "required": True},
            {"name": "sends_per_week", "type": "select", "label": "Sends per week",
             "options": ["2", "3", "5", "7"], "required": True},
        ],
        "base_prompt": "Plan a 30-day email calendar.\n\nList: {email_list_size}\nFrequency: {sends_per_week}/week",
        "estimated_tokens": 3000,
        "engine": "builtin",
        "enhancements": ["brand_dossier"],
    },

    # ── Strategy & Coaching (3) ────────────────────────────────
    "jumbo-strategist": {
        "name": "Jumbo Strategist",
        "category": "strategy",
        "icon": "brain",
        "tags": ["Strategy", "Business"],
        "description": "Your AI business strategist. Ask anything about positioning, pricing, or growth.",
        "status": "active",
        "multi_step": False,
        "inputs": [
            {"name": "question", "type": "textarea", "label": "What do you need help with?", "required": True},
            {"name": "context", "type": "textarea", "label": "Additional context (optional)", "required": False},
        ],
        "base_prompt": (
            "You are a world-class business strategist with deep expertise in positioning, pricing, "
            "offer creation, and growth. Answer this question:\n\n{question}\n\nContext: {context}"
        ),
        "estimated_tokens": 3000,
        "engine": "builtin",
        "enhancements": ["brand_dossier", "story_bank", "competitor_intel"],
    },
    "brand-research": {
        "name": "Brand Research",
        "category": "strategy",
        "icon": "search",
        "tags": ["Brand", "Research"],
        "description": "Deep brand research: positioning, voice, competitive analysis.",
        "status": "active",
        "multi_step": False,
        "inputs": [
            {"name": "research_focus", "type": "select", "label": "Research Focus",
             "options": ["Full Brand Audit", "Competitive Positioning", "Voice & Messaging", "Market Gaps"], "required": True},
        ],
        "base_prompt": (
            "Conduct brand research with focus on: {research_focus}\n\n"
            "Analyze: positioning, messaging, target audience alignment, competitive advantages, gaps."
        ),
        "estimated_tokens": 5000,
        "engine": "builtin",
        "enhancements": ["brand_dossier", "competitor_intel"],
    },
    "sales-call-analysis": {
        "name": "Sales Call Analysis",
        "category": "strategy",
        "icon": "phone",
        "tags": ["Sales", "Analysis"],
        "description": "Analyze sales call transcripts for objections, opportunities, and coaching.",
        "status": "active",
        "multi_step": False,
        "inputs": [
            {"name": "transcript", "type": "textarea", "label": "Paste call transcript", "required": True},
            {"name": "call_outcome", "type": "select", "label": "Outcome",
             "options": ["Closed Won", "Closed Lost", "Follow-Up", "No Decision"], "required": True},
        ],
        "base_prompt": (
            "Analyze this sales call transcript.\n\n"
            "Outcome: {call_outcome}\n\nTranscript:\n{transcript}\n\n"
            "Identify: 1) Key objections raised, 2) Missed opportunities, "
            "3) Strongest moments, 4) Coaching recommendations, "
            "5) Follow-up action items."
        ),
        "estimated_tokens": 5000,
        "engine": "builtin",
        "enhancements": ["brand_dossier", "story_bank"],
    },
}


# ── Enhancement injection ─────────────────────────────────────────────────

async def build_enhanced_prompt(
    workflow: Dict[str, Any],
    inputs: Dict[str, str],
    brand_id: str,
    user_id: str,
) -> str:
    """Inject brand dossier, story bank, hooks, and competitor intel into the workflow prompt."""
    # Format base prompt with user inputs (safe: missing keys become empty)
    safe_inputs = {k: inputs.get(k, "") for k in _extract_placeholders(workflow["base_prompt"])}
    try:
        base = workflow["base_prompt"].format(**safe_inputs)
    except (KeyError, IndexError):
        base = workflow["base_prompt"]

    parts = [base]
    enhancements = workflow.get("enhancements", [])

    if "brand_dossier" in enhancements:
        try:
            from app.services.jumbo_pipeline import get_brand_context
            ctx = get_brand_context(brand_id)
            if ctx:
                dossier_parts = []
                for key in ["name", "voice", "positioning", "ica", "niche"]:
                    if ctx.get(key):
                        dossier_parts.append(f"{key.replace('_', ' ').title()}: {ctx[key]}")
                if ctx.get("anxiety_list"):
                    dossier_parts.append(f"Client Fears: {', '.join(ctx['anxiety_list'][:5])}")
                if ctx.get("benefit_list"):
                    dossier_parts.append(f"Client Desires: {', '.join(ctx['benefit_list'][:5])}")
                if ctx.get("power_words"):
                    dossier_parts.append(f"Power Words: {', '.join(ctx['power_words'][:10])}")
                if dossier_parts:
                    parts.append(f"\n\n## Brand Intelligence\n" + "\n".join(dossier_parts))
        except Exception as e:
            logger.warning("brand_dossier enhancement failed: %s", e)

    if "story_bank" in enhancements:
        try:
            from app.services.jumbo_pipeline import get_story_context
            stories = get_story_context(brand_id, user_id, inputs.get("topic", inputs.get("research_topic", "")))
            if stories:
                parts.append(f"\n\n## Your Personal Stories & Material\n{stories}")
        except Exception as e:
            logger.warning("story_bank enhancement failed: %s", e)

    if "hook_library" in enhancements:
        try:
            from app.services.jumbo_pipeline import get_hooks_for_brand
            hooks = get_hooks_for_brand(brand_id)
            if hooks:
                parts.append(f"\n\n## Your Proven Hooks\n{hooks}")
        except Exception as e:
            logger.warning("hook_library enhancement failed: %s", e)

    if "competitor_intel" in enhancements:
        try:
            from app.services.jumbo_pipeline import get_competitor_context
            intel = get_competitor_context(brand_id)
            if intel:
                parts.append(f"\n\n## Competitive Intelligence\n{intel}")
        except Exception as e:
            logger.warning("competitor_intel enhancement failed: %s", e)

    return "\n".join(parts)


def _extract_placeholders(template: str) -> List[str]:
    """Extract {placeholder} names from a template string."""
    import re
    return re.findall(r"\{(\w+)\}", template)


# ── Step prompt builder (multi-step workflows) ────────────────────────────

def build_step_prompt(
    workflow: Dict[str, Any],
    step_index: int,
    inputs: Dict[str, str],
    previous_outputs: List[str],
) -> str:
    """Build prompt for a specific step in a multi-step workflow."""
    step = workflow["steps"][step_index]
    step_name = step["name"]

    prompt_parts = [
        f"## Step {step_index + 1}: {step_name}\n",
        f"You are working on step {step_index + 1} of {len(workflow['steps'])} "
        f"in the {workflow['name']} workflow.\n",
    ]

    # Include original inputs
    for key, val in inputs.items():
        if val:
            prompt_parts.append(f"{key.replace('_', ' ').title()}: {val}")

    # Include previous step outputs as context
    if previous_outputs:
        prompt_parts.append("\n## Previous Steps Completed:")
        for i, output in enumerate(previous_outputs):
            prev_step = workflow["steps"][i]
            # Truncate previous outputs to prevent context overflow
            truncated = output[:3000] + "..." if len(output) > 3000 else output
            prompt_parts.append(f"\n### {prev_step['name']}:\n{truncated}")

    prompt_parts.append(f"\nNow generate the {step_name}. Be thorough and specific.")

    return "\n".join(prompt_parts)


# ── Execution engine ──────────────────────────────────────────────────────

async def execute_workflow(
    workflow_slug: str,
    inputs: Dict[str, str],
    brand_id: str,
    user_id: str,
    engine: str = "builtin",
    step_index: Optional[int] = None,
    previous_outputs: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Execute a workflow and return result. Saves to workflow_runs table."""
    workflow = WORKFLOW_REGISTRY.get(workflow_slug)
    if not workflow:
        return {"error": f"Unknown workflow: {workflow_slug}", "status": "failed"}

    if workflow.get("status") == "coming_soon":
        return {"error": "This workflow is coming soon.", "status": "failed"}

    start_time = time.time()
    run_id = str(uuid.uuid4())

    try:
        # Build the enhanced prompt
        if workflow.get("multi_step") and step_index is not None:
            prompt = build_step_prompt(
                workflow, step_index, inputs, previous_outputs or []
            )
            # Still add enhancements for step 1
            if step_index == 0:
                enhanced = await build_enhanced_prompt(workflow, inputs, brand_id, user_id)
                prompt = enhanced + "\n\n" + prompt
        else:
            prompt = await build_enhanced_prompt(workflow, inputs, brand_id, user_id)

        # Execute via built-in AI
        if engine == "builtin" or engine != "manus":
            result = await _run_builtin(prompt, user_id, brand_id)
        else:
            result = await _run_manus(prompt, workflow_slug, user_id, brand_id)

        duration_ms = int((time.time() - start_time) * 1000)

        # Save to workflow_runs
        await _save_workflow_run(
            run_id=run_id,
            user_id=user_id,
            brand_id=brand_id,
            workflow_slug=workflow_slug,
            inputs=inputs,
            output=result.get("content", ""),
            status="completed" if result.get("success") else "failed",
            engine=engine,
            duration_ms=duration_ms,
            tokens_used=result.get("tokens_used", 0),
        )

        return {
            "run_id": run_id,
            "status": "completed",
            "content": result.get("content", ""),
            "engine": engine,
            "duration_ms": duration_ms,
            "tokens_used": result.get("tokens_used", 0),
            "model_used": result.get("model_used", ""),
        }

    except Exception as e:
        logger.error("Workflow execution failed: %s – %s", workflow_slug, e)
        duration_ms = int((time.time() - start_time) * 1000)
        await _save_workflow_run(
            run_id=run_id,
            user_id=user_id,
            brand_id=brand_id,
            workflow_slug=workflow_slug,
            inputs=inputs,
            output=str(e),
            status="failed",
            engine=engine,
            duration_ms=duration_ms,
        )
        return {
            "run_id": run_id,
            "status": "failed",
            "error": str(e),
            "engine": engine,
            "duration_ms": duration_ms,
        }


async def _run_builtin(prompt: str, user_id: str, brand_id: str) -> Dict[str, Any]:
    """Execute using built-in AI (Claude Sonnet 4.6 via sdk_agents)."""
    from app.services.sdk_agents import run_copywriter_task

    result = run_copywriter_task(
        prompt=prompt,
        brand_context="",  # Already injected via enhancements
        model="gpt-4o",
        user_id=user_id,
        brand_id=brand_id,
        use_tool_use=False,
    )
    return {
        "success": result.success,
        "content": result.content,
        "tokens_used": result.tokens_used,
        "model_used": result.model_used,
        "error": result.error,
    }


async def _run_manus(
    prompt: str, workflow_slug: str, user_id: str, brand_id: str,
) -> Dict[str, Any]:
    """Execute using Manus AI (optional BYOK)."""
    from app.services.manus_ai import ManusAIClient, get_manus_api_key

    api_key = get_manus_api_key(user_id)
    if not api_key:
        # Fallback to built-in if no Manus key
        logger.info("No Manus key — falling back to built-in for %s", workflow_slug)
        return await _run_builtin(prompt, user_id, brand_id)

    client = ManusAIClient(api_key)
    task = await client.create_task(
        prompt=prompt,
        mode="agent",
        profile="quality",
    )
    task_id = task.get("task_id")
    if not task_id:
        return await _run_builtin(prompt, user_id, brand_id)

    # Poll until complete (max 10 minutes)
    import asyncio
    for _ in range(120):  # 120 * 5s = 10 min
        await asyncio.sleep(5)
        status = await client.poll_task(task_id)
        if status.get("status") == "completed":
            return {
                "success": True,
                "content": status.get("result_text", ""),
                "tokens_used": 0,
                "model_used": "manus-ai",
            }
        if status.get("status") == "failed":
            return {
                "success": False,
                "content": "",
                "error": status.get("error", "Manus task failed"),
                "model_used": "manus-ai",
            }

    return {
        "success": False,
        "content": "",
        "error": "Manus task timed out after 10 minutes",
        "model_used": "manus-ai",
    }


# ── Persistence helpers ───────────────────────────────────────────────────

async def _save_workflow_run(
    run_id: str,
    user_id: str,
    brand_id: str,
    workflow_slug: str,
    inputs: Dict[str, Any],
    output: str,
    status: str,
    engine: str,
    duration_ms: int,
    tokens_used: int = 0,
) -> None:
    """Save a workflow run to the database."""
    try:
        sb = get_admin_client()
        sb.table("workflow_runs").insert({
            "id": run_id,
            "user_id": user_id,
            "brand_id": brand_id,
            "workflow_slug": workflow_slug,
            "inputs": inputs,
            "output": output[:50000],  # Cap at 50K chars
            "status": status,
            "engine": engine,
            "duration_ms": duration_ms,
            "tokens_used": tokens_used,
        }).execute()
    except Exception as e:
        logger.error("Failed to save workflow run: %s", e)


async def get_workflow_run(run_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Get a single workflow run (IDOR-safe)."""
    try:
        sb = get_admin_client()
        result = sb.table("workflow_runs").select("*").eq(
            "id", run_id
        ).eq("user_id", user_id).single().execute()
        return result.data
    except Exception:
        return None


async def get_workflow_history(
    user_id: str,
    brand_id: str,
    workflow_slug: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """Get workflow run history for a user."""
    try:
        sb = get_admin_client()
        query = sb.table("workflow_runs").select("*").eq(
            "user_id", user_id
        ).eq("brand_id", brand_id).order(
            "created_at", desc=True,
        ).limit(limit).offset(offset)
        if workflow_slug:
            query = query.eq("workflow_slug", workflow_slug)
        result = query.execute()
        return result.data or []
    except Exception as e:
        logger.error("Failed to get workflow history: %s", e)
        return []


def get_registry() -> Dict[str, Any]:
    """Return the full workflow registry for the frontend."""
    return {
        "categories": WORKFLOW_CATEGORIES,
        "workflows": {
            slug: {
                "slug": slug,
                "name": w["name"],
                "category": w["category"],
                "icon": w.get("icon", ""),
                "tags": w.get("tags", []),
                "description": w["description"],
                "status": w["status"],
                "multi_step": w.get("multi_step", False),
                "steps": [{"name": s["name"]} for s in w.get("steps", [])],
                "inputs": w.get("inputs", []),
                "estimated_tokens": w.get("estimated_tokens", 0),
                "engine": w.get("engine", "builtin"),
                "enhancements": w.get("enhancements", []),
            }
            for slug, w in WORKFLOW_REGISTRY.items()
        },
    }


# ── Framework docs seeding ────────────────────────────────────────────────

SYSTEM_FRAMEWORK_DOCS = [
    {
        "title": "Messaging Buckets Framework",
        "doc_type": "framework",
        "agent_scope": ["copywriter", "jumbo"],
        "content": (
            "6 content categories for structured messaging:\n"
            "1. PAIN - address fears, frustrations, current struggles\n"
            "2. OUTCOME - paint the dream result, transformation\n"
            "3. STORY - personal stories, client stories, relatable narratives\n"
            "4. AUTHORITY - credentials, experience, results, social proof\n"
            "5. BELIEF - shift limiting beliefs, reframe objections\n"
            "6. CURIOSITY - open loops, tease insights, create intrigue\n\n"
            "Every piece of content should hit 1-2 buckets. "
            "Rotate across all 6 for maximum audience resonance."
        ),
    },
    {
        "title": "Hormozi Value Equation",
        "doc_type": "framework",
        "agent_scope": ["copywriter", "jumbo"],
        "content": (
            "Value = (Dream Outcome x Perceived Likelihood of Achievement) / "
            "(Time Delay x Effort & Sacrifice)\n\n"
            "To increase value:\n"
            "- Amplify Dream Outcome (bigger transformation)\n"
            "- Increase Perceived Likelihood (guarantees, proof, testimonials)\n"
            "- Decrease Time Delay (faster results)\n"
            "- Decrease Effort & Sacrifice (done-for-you, easy implementation)\n\n"
            "Apply to: offers, landing pages, ad copy, email sequences."
        ),
    },
    {
        "title": "Hormozi Grand Slam Offer",
        "doc_type": "framework",
        "agent_scope": ["copywriter", "jumbo"],
        "content": (
            "Grand Slam Offer Framework:\n"
            "1. Identify the Dream Outcome your client wants\n"
            "2. List all perceived problems preventing that outcome\n"
            "3. For each problem, create a solution (your deliverables)\n"
            "4. Name each solution compellingly (Trim & Stack)\n"
            "5. Add bonuses that solve secondary problems\n"
            "6. Create urgency/scarcity (deadlines, limited spots)\n"
            "7. Add a strong guarantee (outcome-based, not refund-based)\n"
            "8. Price anchor high, then reveal actual price\n\n"
            "Result: An offer so good people feel stupid saying no."
        ),
    },
    {
        "title": "VSL Script Framework",
        "doc_type": "framework",
        "agent_scope": ["copywriter"],
        "content": (
            "Video Sales Letter structure:\n"
            "1. Pattern Interrupt Hook (first 5 seconds)\n"
            "2. Big Promise / Dream Outcome\n"
            "3. Credibility & Authority\n"
            "4. Problem Agitation (their current pain)\n"
            "5. Solution Introduction\n"
            "6. Mechanism (how/why it works)\n"
            "7. Social Proof & Results\n"
            "8. The Offer (Grand Slam format)\n"
            "9. Bonus Stack\n"
            "10. Risk Reversal / Guarantee\n"
            "11. Urgency / Scarcity\n"
            "12. CTA (clear, single next step)\n"
            "13. PS / Final Reminder"
        ),
    },
    {
        "title": "Email Sequence Framework",
        "doc_type": "framework",
        "agent_scope": ["copywriter"],
        "content": (
            "Email types and structures:\n\n"
            "OPT-IN NURTURE (20 emails over 30 days):\n"
            "- Emails 1-3: Welcome + quick win + credibility\n"
            "- Emails 4-8: Pain agitation + story + belief shifting\n"
            "- Emails 9-14: Solution reveal + mechanism + proof\n"
            "- Emails 15-18: Offer + objection handling\n"
            "- Emails 19-20: Urgency + final CTA\n\n"
            "ABANDON CART (10 emails):\n"
            "- Email 1 (1hr): Reminder + remove friction\n"
            "- Email 2 (24hr): FAQ / objection handling\n"
            "- Email 3 (48hr): Social proof / testimonial\n"
            "- Email 4-8 (days 3-7): Value reframe + bonuses\n"
            "- Email 9-10 (days 8-10): Scarcity + final offer\n\n"
            "PRE-CALL (3 emails before scheduled call):\n"
            "- Email 1 (immediately): Confirmation + homework\n"
            "- Email 2 (24hr before): Case study + excitement\n"
            "- Email 3 (2hr before): Reminder + agenda preview"
        ),
    },
    {
        "title": "B2B Sales Page Framework",
        "doc_type": "framework",
        "agent_scope": ["lp-builder"],
        "content": (
            "B2B Sales Page structure:\n"
            "1. Hero: Problem-aware headline + credibility badges\n"
            "2. Social Proof Bar: logos of clients/press\n"
            "3. Problem Section: 3-4 specific pain points\n"
            "4. Solution: How your product solves each pain\n"
            "5. Features → Benefits mapping (3-4 sections)\n"
            "6. Case Study / ROI proof\n"
            "7. Pricing or CTA (demo/consultation)\n"
            "8. FAQ (5-7 questions)\n"
            "9. Final CTA with guarantee"
        ),
    },
    {
        "title": "B2C Sales Page Framework",
        "doc_type": "framework",
        "agent_scope": ["lp-builder"],
        "content": (
            "B2C Sales Page structure:\n"
            "1. Hero: Outcome-driven headline + aspirational image\n"
            "2. Before/After transformation story\n"
            "3. Problem agitation (emotional, personal)\n"
            "4. Solution introduction + mechanism\n"
            "5. Social Proof: testimonials, results, numbers\n"
            "6. Offer breakdown (what's included)\n"
            "7. Bonus stack\n"
            "8. Money-back guarantee\n"
            "9. Urgency/scarcity element\n"
            "10. Final CTA + PS"
        ),
    },
    {
        "title": "Adaptive Sales Page Framework",
        "doc_type": "framework",
        "agent_scope": ["lp-builder"],
        "content": (
            "Adaptive Sales Page (works for both B2B and B2C):\n"
            "1. Hero: Awareness-matched headline (problem or solution aware)\n"
            "2. Empathy bridge (show you understand their world)\n"
            "3. Unique mechanism (your proprietary approach)\n"
            "4. Proof stack (testimonials + data + case studies)\n"
            "5. Offer + pricing (tiered if possible)\n"
            "6. Risk reversal (guarantee matched to objections)\n"
            "7. FAQ addressing top 5 objections\n"
            "8. Dual CTA (primary action + softer alternative)\n\n"
            "Adaptive rules:\n"
            "- B2B: emphasize ROI, efficiency, competitive edge\n"
            "- B2C: emphasize transformation, emotion, simplicity"
        ),
    },
    {
        "title": "Call Presupposition Analysis",
        "doc_type": "framework",
        "agent_scope": ["copywriter", "jumbo"],
        "content": (
            "Call Presupposition Analysis Framework:\n"
            "When analyzing sales calls or coaching calls, extract:\n\n"
            "1. EXPLICIT NEEDS: What the prospect/client directly stated they need\n"
            "2. IMPLICIT NEEDS: What they need but haven't articulated\n"
            "3. PRESUPPOSITIONS: What beliefs/assumptions underlie their statements\n"
            "4. OBJECTIONS: Stated and unstated concerns\n"
            "5. BUYING SIGNALS: Indicators of readiness to commit\n"
            "6. EMOTIONAL DRIVERS: Fear, desire, frustration, aspiration\n"
            "7. DECISION CRITERIA: What factors they'll use to decide\n\n"
            "Use this to: craft follow-up content, write case studies, "
            "improve sales scripts, create targeted nurture sequences."
        ),
    },
    {
        "title": "Opt-In VSL Funnel Architecture",
        "doc_type": "framework",
        "agent_scope": ["copywriter"],
        "content": (
            "Complete VSL Funnel Architecture:\n\n"
            "TRAFFIC → Opt-In Page → Thank You Page (VSL) → Sales Page → Checkout\n\n"
            "Step 1: Opt-In Page\n"
            "- Headline: specific result + timeframe\n"
            "- 3-5 bullet points of what they'll learn\n"
            "- Simple form (name + email)\n\n"
            "Step 2: Thank You / VSL Page\n"
            "- Auto-play VSL (10-45 min)\n"
            "- CTA appears at pitch point\n"
            "- Urgency element below video\n\n"
            "Step 3: Email Nurture (20 emails)\n"
            "- Follows opt-in nurture framework\n"
            "- Drives back to VSL page\n\n"
            "Step 4: Broadcast Emails (ongoing)\n"
            "- 5/week: value + occasional pitch\n"
            "- Messenger Buckets rotation"
        ),
    },
]


async def seed_system_frameworks() -> int:
    """Seed system framework docs. Idempotent — skips existing titles."""
    try:
        sb = get_admin_client()
        existing = sb.table("knowledge_documents").select("title").eq(
            "scope", "system"
        ).execute()
        existing_titles = {d["title"] for d in (existing.data or [])}

        seeded = 0
        for doc in SYSTEM_FRAMEWORK_DOCS:
            if doc["title"] in existing_titles:
                continue
            sb.table("knowledge_documents").insert({
                "title": doc["title"],
                "doc_type": doc["doc_type"],
                "content": doc["content"],
                "scope": "system",
                "platform": "all",
            }).execute()
            seeded += 1
            logger.info("Seeded framework doc: %s", doc["title"])

        return seeded
    except Exception as e:
        logger.error("Failed to seed framework docs: %s", e)
        return 0
