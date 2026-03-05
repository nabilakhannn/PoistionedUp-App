"""Lead Generation Service — Slice 95.

3-engine enrichment pipeline based on Cameron Sullivan / Outskill lead gen methodology:
  1. Personal LinkedIn posts  → professional_topics, recent_achievements
  2. Company LinkedIn posts   → hiring_signals, pain_points
  3. Company website          → company_changes, industries_served, growth_signals

BANT scoring (0-4) is auto-computed from enrichment signals.
Outreach generation uses Claude Sonnet 4.6 with brand voice + transcript context.

All functions are stateless; the router handles DB persistence.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx

from app.config import settings
from app.utils.url_validation import validate_url_for_fetch

logger = logging.getLogger("app.services.lead_gen")

_PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"

# Regex for cleaning AI output to safe strings
_SAFE_NAME_RE = re.compile(r"[^\w\s\-\.\,]")

# Titles that indicate decision-maker authority (BANT: Authority)
_DM_TITLE_KEYWORDS = (
    "ceo", "coo", "cto", "cfo", "cmo", "cso", "vp ", "vice president",
    "director", "head of", "founder", "co-founder", "owner", "partner",
    "president", "managing director", "chief",
)


# ── Perplexity helper ──────────────────────────────────────────────────────


def _perplexity_search(query: str, max_tokens: int = 800) -> str:
    """Run a Perplexity sonar-pro search. Returns plain text result."""
    safe_query = re.sub(r"[<>\"';&]", "", query).strip()[:300]

    if not settings.perplexity_api_key:
        return f"[Perplexity unavailable — no key configured. Query: {safe_query!r}]"

    try:
        resp = httpx.post(
            _PERPLEXITY_URL,
            json={
                "model": "sonar-pro",
                "messages": [{"role": "user", "content": safe_query}],
                "max_tokens": max_tokens,
            },
            headers={
                "Authorization": f"Bearer {settings.perplexity_api_key}",
                "Content-Type": "application/json",
            },
            timeout=20.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as exc:
        logger.warning("Perplexity search failed for %r: %s", safe_query, exc)
        return f"[search unavailable: {exc}]"


def _claude_haiku(prompt: str, max_tokens: int = 512) -> str:
    """Call Claude Haiku for cheap classification/extraction tasks."""
    if not settings.anthropic_api_key:
        return "{}"

    try:
        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            },
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.json()["content"][0]["text"]
    except Exception as exc:
        logger.warning("Claude Haiku call failed: %s", exc)
        return "{}"


def _claude_sonnet(prompt: str, max_tokens: int = 1500) -> str:
    """Call Claude Sonnet 4.6 for quality writing tasks."""
    if not settings.anthropic_api_key:
        return "{}"

    try:
        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            },
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            timeout=45.0,
        )
        resp.raise_for_status()
        return resp.json()["content"][0]["text"]
    except Exception as exc:
        logger.warning("Claude Sonnet call failed: %s", exc)
        return "{}"


def _extract_json(text: str) -> Any:
    """Extract first JSON object or array from LLM output."""
    try:
        # Try direct parse first
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    # Find JSON block in markdown
    m = re.search(r"```(?:json)?\s*([\[\{].*?[\]\}])\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # Find raw JSON object
    m = re.search(r"(\{.*\})", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    return {}


# ── Lead generation ────────────────────────────────────────────────────────


def generate_leads_from_icp(brand_id: str, user_id: str, count: int = 10) -> List[Dict]:
    """Generate real professionals matching the brand's ICP.

    Uses all 3 ICP layers from the brand profile:
    - Firmographics: company niche, target market
    - Demographics:  job title, seniority, department
    - Psychographics: pain points, what the brand solves

    Returns a list of lead dicts (not yet saved to DB — router handles upsert).
    Raises ValueError if brand profile or ICP section is incomplete.
    """
    from app.deps import get_admin_client

    # 1. Fetch brand profile
    sb = get_admin_client()
    result = (
        sb.table("personal_brands")
        .select("profile_json")
        .eq("id", brand_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise ValueError("Brand not found")

    profile_json = result.data[0].get("profile_json") or {}
    ica = profile_json.get("ica") or {}
    if not ica:
        raise ValueError(
            "Complete ICP in brand profile first — "
            "go to Settings → Brand Profile → ICA section"
        )

    # 2. Extract 3 ICP layers
    foundation = profile_json.get("foundation") or {}
    offer = profile_json.get("offer") or {}

    icp_desc = f"""
Firmographics (company characteristics):
- Industry/niche: {foundation.get("niche", "") or ica.get("target_market", "")}
- Target market: {ica.get("target_market", "")}
- Company size: {ica.get("company_size", "")}

Demographics (person characteristics):
- Job title/role: {ica.get("job_title", "") or ica.get("demographics", {}).get("title", "")}
- Seniority: {ica.get("seniority", "") or ica.get("demographics", {}).get("seniority", "senior+")}
- Department: {ica.get("department", "")}

Psychographics (problems and goals):
- Pain points: {ica.get("pain_points", "")}
- Goals: {ica.get("goals", "")}
- What we solve: {offer.get("value_proposition", "")}
""".strip()

    # 3. Perplexity search for real professionals
    count_capped = min(count, 20)
    search_query = (
        f"Find {count_capped} real professionals who match this ideal customer profile. "
        f"Return their full name, job title, company name, LinkedIn URL if available, "
        f"location, and company website. "
        f"ICP Description:\n{icp_desc}\n\n"
        f"Return as a JSON array with fields: "
        f"full_name, title, company, linkedin_url, location, company_website, email"
    )

    raw = _perplexity_search(search_query, max_tokens=1500)

    # 4. Claude Haiku parses + cleans the output
    parse_prompt = f"""
Extract and return a clean JSON array from this research output.
Each item must have these fields (use null for missing):
full_name, title, company, linkedin_url, location, company_website, email

Output only valid JSON array. No markdown, no explanation.
Cap at {count_capped} items.

Research output:
{raw[:3000]}
"""
    parsed_text = _claude_haiku(parse_prompt, max_tokens=1000)
    leads_raw = _extract_json(parsed_text)

    if not isinstance(leads_raw, list):
        leads_raw = []

    # 5. Sanitise and return
    leads = []
    for item in leads_raw[:count_capped]:
        if not isinstance(item, dict):
            continue
        full_name = _SAFE_NAME_RE.sub("", str(item.get("full_name") or "")).strip()
        if not full_name:
            continue
        leads.append({
            "full_name": full_name[:255],
            "title": str(item.get("title") or "")[:255],
            "company": str(item.get("company") or "")[:255],
            "linkedin_url": str(item.get("linkedin_url") or "")[:500] or None,
            "company_website": str(item.get("company_website") or "")[:500] or None,
            "location": str(item.get("location") or "")[:255],
            "email": str(item.get("email") or "")[:255] or None,
            "source": "generated",
            "status": "cold",
        })

    return leads


# ── Enrichment ─────────────────────────────────────────────────────────────


def enrich_lead(lead: Dict) -> Dict:
    """Run 3-engine enrichment on a lead.

    Returns enrichment JSONB dict + bant_score (0-4).
    Each step degrades gracefully — partial enrichment is better than nothing.
    """
    name = lead.get("full_name", "")
    company = lead.get("company", "")
    email = lead.get("email", "")
    company_website = lead.get("company_website", "")
    title = str(lead.get("title") or "").lower()

    enrichment: Dict[str, Any] = {
        "professional_topics": [],
        "recent_achievements": [],
        "hiring_signals": [],
        "pain_points": [],
        "company_changes": [],
        "industries_served": [],
        "growth_signals": [],
    }

    # ── Step 1: Personal LinkedIn ─────────────────────────────────────────
    if name and company:
        linkedin_query = (
            f'"{name}" "{company}" LinkedIn posts interests achievements 2024 2025'
        )
        linkedin_raw = _perplexity_search(linkedin_query, max_tokens=600)

        extract_prompt = f"""
From this research about {name} at {company}, extract:
1. professional_topics: list of topics they post/comment about most (their interests)
2. recent_achievements: list of specific achievements in last 1-3 months (funding, promotions, launches)

Return JSON only:
{{"professional_topics": ["topic1", "topic2"], "recent_achievements": ["achievement1"]}}

Research:
{linkedin_raw[:2000]}
"""
        result = _extract_json(_claude_haiku(extract_prompt, max_tokens=300))
        if isinstance(result, dict):
            enrichment["professional_topics"] = result.get("professional_topics") or []
            enrichment["recent_achievements"] = result.get("recent_achievements") or []

    # ── Step 2: Company LinkedIn ──────────────────────────────────────────
    if company:
        company_query = (
            f'"{company}" LinkedIn hiring job openings expanding challenges 2024 2025'
        )
        company_raw = _perplexity_search(company_query, max_tokens=600)

        extract_prompt = f"""
From this research about {company}, extract:
1. hiring_signals: evidence the company is growing/hiring (job posts, "we're expanding", etc.)
2. pain_points: direct problem statements the company has publicly admitted

Return JSON only:
{{"hiring_signals": ["signal1"], "pain_points": ["pain1"]}}

Research:
{company_raw[:2000]}
"""
        result = _extract_json(_claude_haiku(extract_prompt, max_tokens=300))
        if isinstance(result, dict):
            enrichment["hiring_signals"] = result.get("hiring_signals") or []
            enrichment["pain_points"] = result.get("pain_points") or []

    # ── Step 3: Company website ───────────────────────────────────────────
    website_url = company_website
    if not website_url and email and "@" in email:
        domain = email.split("@")[1].lower().strip()
        # Skip free email providers
        free_domains = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com"}
        if domain not in free_domains:
            website_url = f"https://{domain}"

    if website_url:
        try:
            safe_url = validate_url_for_fetch(website_url)
            resp = httpx.get(
                safe_url,
                follow_redirects=True,
                timeout=10.0,
                headers={"User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0)"},
            )
            resp.raise_for_status()
            # Strip HTML tags for plain text
            html = resp.text[:8000]
            plain_text = re.sub(r"<[^>]+>", " ", html)
            plain_text = re.sub(r"\s+", " ", plain_text).strip()[:4000]

            extract_prompt = f"""
From this company website content for {company}, extract:
1. company_changes: recent product launches, rebrands, new markets, partnerships
2. industries_served: who their customers are (for matched social proof)
3. growth_signals: open roles by dept, new office mentions, growth language

Return JSON only:
{{"company_changes": ["change1"], "industries_served": ["industry1"], "growth_signals": ["signal1"]}}

Website content:
{plain_text}
"""
            result = _extract_json(_claude_haiku(extract_prompt, max_tokens=400))
            if isinstance(result, dict):
                enrichment["company_changes"] = result.get("company_changes") or []
                enrichment["industries_served"] = result.get("industries_served") or []
                enrichment["growth_signals"] = result.get("growth_signals") or []
        except ValueError as exc:
            logger.debug("Website fetch blocked (SSRF guard) for %s: %s", website_url, exc)
        except Exception as exc:
            logger.debug("Website fetch failed for %s: %s", website_url, exc)

    # ── Step 4: BANT scoring ──────────────────────────────────────────────
    bant_score = 0

    # Budget: funding or revenue signals in enrichment
    budget_signals = " ".join(str(enrichment.get("recent_achievements") or [])).lower()
    if any(kw in budget_signals for kw in ("funding", "raised", "series", "revenue", "million", "acquisition")):
        bant_score += 1

    # Authority: decision-maker title
    if any(kw in title for kw in _DM_TITLE_KEYWORDS):
        bant_score += 1

    # Need: company has public pain points
    if enrichment.get("pain_points"):
        bant_score += 1

    # Timing: recent trigger event
    timing_signals = " ".join([
        *map(str, enrichment.get("recent_achievements") or []),
        *map(str, enrichment.get("hiring_signals") or []),
        *map(str, enrichment.get("company_changes") or []),
    ]).lower()
    if timing_signals and any(kw in timing_signals for kw in (
        "2025", "2024", "recently", "just", "new", "launch", "hire", "expand", "opened"
    )):
        bant_score += 1

    import datetime
    enrichment["last_enriched_at"] = datetime.datetime.utcnow().isoformat() + "Z"

    return {"enrichment": enrichment, "bant_score": bant_score}


# ── Outreach generation ────────────────────────────────────────────────────


def generate_outreach(lead: Dict, enrichment: Dict, brand_profile: Dict) -> Dict:
    """Generate personalised outreach content for a lead.

    Uses brand voice + ICP from profile + enrichment signals.
    If lead has a transcript, it is injected as additional context.

    Returns: { icebreaker, linkedin_dm, cold_email: {subject, body}, sequence: [...] }
    """
    name = lead.get("full_name", "this person")
    first_name = name.split()[0] if name else "there"
    company = lead.get("company", "")
    title = lead.get("title", "")
    transcript = lead.get("transcript", "")

    # Build enrichment context string
    enrichment_lines = []
    if enrichment.get("professional_topics"):
        enrichment_lines.append(f"Posts about: {', '.join(enrichment['professional_topics'][:3])}")
    if enrichment.get("recent_achievements"):
        enrichment_lines.append(f"Recent achievement: {enrichment['recent_achievements'][0]}")
    if enrichment.get("hiring_signals"):
        enrichment_lines.append(f"Hiring signal: {enrichment['hiring_signals'][0]}")
    if enrichment.get("pain_points"):
        enrichment_lines.append(f"Pain point: {enrichment['pain_points'][0]}")
    if enrichment.get("company_changes"):
        enrichment_lines.append(f"Company change: {enrichment['company_changes'][0]}")
    if enrichment.get("growth_signals"):
        enrichment_lines.append(f"Growth signal: {enrichment['growth_signals'][0]}")

    enrichment_context = "\n".join(enrichment_lines) if enrichment_lines else "No enrichment data available"

    # Brand profile context
    ica = brand_profile.get("ica") or {}
    offer = brand_profile.get("offer") or {}
    messaging = brand_profile.get("messaging") or {}

    brand_context = f"""
Brand value proposition: {offer.get("value_proposition", "")}
Who we help: {ica.get("target_market", "")}
Key pain point we solve: {ica.get("pain_points", "")}
Tone / voice: {messaging.get("tone", "professional, direct, warm")}
Unique angle: {messaging.get("unique_angle", "")}
""".strip()

    # Transcript context
    transcript_section = ""
    if transcript and transcript.strip():
        transcript_section = f"""
Additional context from call/meeting notes:
{transcript[:1000]}
"""

    prompt = f"""You are writing highly personalised cold outreach for {name}, {title} at {company}.

LEAD ENRICHMENT SIGNALS:
{enrichment_context}

BRAND CONTEXT:
{brand_context}
{transcript_section}

TASK: Generate personalised outreach in 4 parts. Return as JSON only.

1. icebreaker: A 1-2 sentence opener that references one SPECIFIC verifiable fact about this person or their company. Never generic. Never "I came across your profile." Make it feel like you did your homework.

2. linkedin_dm: A 3-paragraph LinkedIn connection message (keep under 300 characters for connection request note — tight and personal). Include icebreaker, brief value statement, and soft CTA.

3. cold_email: {{ subject: "hyper-relevant subject only THEY would understand", body: "3-paragraph email: open with icebreaker, present relevant problem + how we solve it, close with single clear CTA. Under 150 words." }}

4. sequence: Array of exactly 3 messages:
  - {{ "label": "Message 1 (Connect)", "day": 1, "channel": "linkedin", "message": "...", "sent_at": null }}
  - {{ "label": "Message 2 (Day 3 — Value)", "day": 3, "channel": "linkedin", "message": "...", "sent_at": null }}
  - {{ "label": "Message 3 (Day 7 — CTA)", "day": 7, "channel": "email", "message": "...", "sent_at": null }}

Return JSON only. No markdown, no explanation.
"""

    raw = _claude_sonnet(prompt, max_tokens=1500)
    result = _extract_json(raw)

    if not isinstance(result, dict):
        result = {}

    # Validate sequence structure
    sequence = result.get("sequence") or []
    if not isinstance(sequence, list) or len(sequence) != 3:
        sequence = [
            {"label": "Message 1 (Connect)", "day": 1, "channel": "linkedin", "message": "", "sent_at": None},
            {"label": "Message 2 (Day 3 — Value)", "day": 3, "channel": "linkedin", "message": "", "sent_at": None},
            {"label": "Message 3 (Day 7 — CTA)", "day": 7, "channel": "email", "message": "", "sent_at": None},
        ]

    cold_email = result.get("cold_email") or {}
    if not isinstance(cold_email, dict):
        cold_email = {"subject": "", "body": ""}

    return {
        "icebreaker": str(result.get("icebreaker") or ""),
        "outreach_draft": {
            "linkedin_dm": str(result.get("linkedin_dm") or ""),
            "cold_email": {
                "subject": str(cold_email.get("subject") or ""),
                "body": str(cold_email.get("body") or ""),
            },
        },
        "sequence": sequence,
    }


# ── ICP Research ────────────────────────────────────────────────────────────


ICP_METHODOLOGY = """# Sales Lead Research System Prompt Template

## 1. Objective
Research and identify the best-fit target audience (ICP) and decision-makers for the product/service.
Goal: Define exact parameters for lead generation and outreach.
Tools: Leads will be sourced from Apollo.io using an Apify scraper.

## 2. Brand & Product Snapshot
- Founder + positioning (brand story)
- Mission and philosophy
- Product: name, pricing, key features/benefits
- Goal: target number of paying users
- Platform + deliverables (what customers get)

## 3. Research Questions
1. Who are the ideal companies and decision-makers?
2. What industries, company sizes, regions, and job titles benefit most?
3. What are their main pain points and motivations?
4. What data points should be collected for effective outreach?
5. How to ensure compatibility with Apollo.io filters and fields?

## 4. Output / Report Structure
**Executive Summary: Who to target and why**

**Company Filters (Apollo.io):**
- Industry: [e.g., SaaS, agencies, consulting, online business]
- Size: [e.g., 1-10, 11-50 employees]
- Revenue: [e.g., $10k-$100K]
- Location: [e.g., US, UK, SA, AU, CA]

**Contact Filters (Apollo.io):**
- Titles: [e.g., Founder, CEO, Owner, Director]
- Seniority: [e.g., Owner, CXO, Director, Manager]

**Keywords/Tech:** [e.g., automation, AI, n8n, Zapier, productivity]

➡️ Final Input for Apify Scraper: The unique URL generated by Apollo.io after applying these filters.
"""


def research_icp(brand_id: str, user_id: str, overrides: Optional[Dict] = None) -> Dict:
    """4-stage ICP research using the Sales Lead Research System Prompt Template.

    Stage 1: Objective — what you're trying to achieve
    Stage 2: Brand & Product Snapshot — who you are
    Stage 3: Research Questions — Perplexity answers using brand context
    Stage 4: Output / Apollo Filters — company + contact + keyword filters

    Returns: {"stages": [...], "brand_id": str}
    """
    from app.deps import get_admin_client

    overrides = overrides or {}

    # Load brand profile (IDOR-safe)
    sb = get_admin_client()
    brand_result = (
        sb.table("personal_brands")
        .select("*")
        .eq("id", brand_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not brand_result.data:
        raise ValueError(f"Brand {brand_id} not found")

    brand = brand_result.data[0]
    profile = brand.get("profile_json") or {}

    stages = []

    # ── Stage 1: Objective ──────────────────────────────────────────────────
    product_name = (
        overrides.get("product_name")
        or profile.get("offer_name")
        or brand.get("name", "this product")
    )
    pricing = overrides.get("pricing") or profile.get("pricing_tier") or "contact for pricing"
    brief_desc = (
        profile.get("transformation_zero_to_dream")
        or profile.get("market_gap")
        or "transforming their business"
    )
    lead_db = overrides.get("lead_database") or "Apollo.io"
    scraping_tool = overrides.get("scraping_tool") or "Apify"

    objective = {
        "product_service_name": product_name,
        "pricing": pricing,
        "brief_description": brief_desc,
        "lead_database": lead_db,
        "scraping_tool": scraping_tool,
        "goal": f"Research and identify the best-fit target audience (ICP) and decision-makers for {product_name}.",
    }
    stages.append({"id": 1, "name": "Objective", "status": "complete", "result": objective})

    # ── Stage 2: Brand & Product Snapshot ──────────────────────────────────
    snapshot = {
        "founder": profile.get("founder_name") or brand.get("name", ""),
        "positioning": profile.get("your_story") or "",
        "mission": profile.get("market_gap") or "",
        "philosophy": profile.get("tagline") or "",
        "product": product_name,
        "pricing": pricing,
        "key_features": (profile.get("uvps") or profile.get("benefit_list") or [])[:5],
        "ideal_outcome": profile.get("transformation_zero_to_dream") or "",
        "platform": overrides.get("platform") or profile.get("platform") or "",
    }
    stages.append({"id": 2, "name": "Brand & Product Snapshot", "status": "complete", "result": snapshot})

    # ── Stage 3: Research Questions ─────────────────────────────────────────
    niche = profile.get("niche") or profile.get("target_audience") or "business owners"
    pain_points_raw = profile.get("anxiety_list") or profile.get("pain_points") or []
    pain_str = ", ".join(str(p) for p in pain_points_raw[:5]) if pain_points_raw else "manual processes, scaling challenges, lack of systems"

    research_query = (
        f"Who are the best B2B target companies and decision-makers for {product_name}? "
        f"The product serves {niche} who struggle with: {pain_str}. "
        f"What industries, company sizes (1-50 employees), regions, and job titles should be targeted? "
        f"What are their main motivations and pain points? "
        f"Return JSON with: ideal_industries (list), company_size_ranges (list), "
        f"target_regions (list), job_titles (list), seniority_levels (list), "
        f"pain_points (list), motivations (list), keywords (list)"
    )
    research_raw = _perplexity_search(research_query, max_tokens=1200)

    parse_prompt = f"""Extract structured ICP research from this text. Return valid JSON only.

Text: {research_raw[:3000]}

Return this exact JSON structure:
{{"ideal_industries": ["industry1", "industry2"], "company_size_ranges": ["1-10 employees", "11-50 employees"], "target_regions": ["United States", "United Kingdom"], "job_titles": ["Founder", "CEO"], "seniority_levels": ["C-Suite", "Director"], "pain_points": ["pain1", "pain2"], "motivations": ["motivation1"], "keywords": ["keyword1"]}}"""

    research_json = _extract_json(_claude_haiku(parse_prompt, max_tokens=800))

    if not research_json or not isinstance(research_json, dict):
        # Fallback from brand profile
        research_json = {
            "ideal_industries": profile.get("customer_segments") or ["Digital marketing agencies", "Personal brands", "Consulting firms"],
            "company_size_ranges": ["1-10 employees", "11-50 employees"],
            "target_regions": ["United States", "United Kingdom", "Canada", "Australia"],
            "job_titles": ["Founder", "CEO", "Owner", "Director of Marketing"],
            "seniority_levels": ["C-Suite", "Director", "Owner"],
            "pain_points": pain_points_raw[:5] or ["Time-consuming manual work", "Lack of systems", "Inconsistent lead flow"],
            "motivations": (profile.get("benefit_list") or ["Save time", "Scale revenue", "Automate operations"])[:5],
            "keywords": (profile.get("industry_lingo") or ["automation", "AI", "lead generation"])[:8],
        }

    stages.append({"id": 3, "name": "Research Questions", "status": "complete", "result": research_json})

    # ── Stage 4: Output / Apollo Filters ───────────────────────────────────
    industries = research_json.get("ideal_industries") or []
    titles = research_json.get("job_titles") or []
    seniority = research_json.get("seniority_levels") or []
    sizes = research_json.get("company_size_ranges") or ["1-10 employees", "11-50 employees"]
    regions = research_json.get("target_regions") or []
    keywords = research_json.get("keywords") or []

    apollo_filters = {
        "company_filters": {
            "industry": industries[:6],
            "size": sizes[:3],
            "revenue": ["$0-$1M", "$1M-$10M"],
            "location": regions[:5],
        },
        "contact_filters": {
            "job_titles": titles[:6],
            "seniority": seniority[:4],
        },
        "keywords_tech": keywords[:8],
        "apollo_search_hint": (
            f"Apollo.io filters → Industry: {', '.join(industries[:3])} | "
            f"Size: {', '.join(sizes)} | "
            f"Titles: {', '.join(titles[:4])} | "
            f"Location: {', '.join(regions[:3])}"
        ),
        "apify_scraper": "Use Apollo Export → Apify Apollo.io Scraper → paste the Apollo search URL",
    }
    stages.append({"id": 4, "name": "Output / Apollo Filters", "status": "complete", "result": apollo_filters})

    return {"stages": stages, "brand_id": brand_id}
