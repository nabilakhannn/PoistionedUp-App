# PositionedUp — Master System Design & Client Journey
# Full Agency Automation Platform

**Last updated:** March 4, 2026 | **Author:** CTO (Claude) | **Slice:** 101
**Status:** Living document — updated after every slice

---

## 0. WHAT THIS APP IS

**PositionedUp** is a full-stack marketing agency operating system.

Agency owners and founders use this app to automate 90%+ of the work — research, content, ads, leads, reporting — for multiple clients simultaneously, each with their own isolated brand workspace.

**The promise to clients:** "We handle everything. You show up for 3 hours a month."

**Multi-tenant:** Any agency owner can sign up, add their clients, and the AI agents run autonomously. The client never logs in. They only receive polished deliverables.

---

## 1. CURRENT STATE — WHAT'S BUILT (Slices 1–101)

### Infrastructure
- FastAPI backend (Vercel) — 45+ routers, 200+ endpoints
- Next.js frontend (Vercel) — 47+ pages
- Supabase DB — 38 migrations, RLS on all tables
- OpenClaw agent runtime (Hostinger VPS) — 10 agents
- LangGraph pipeline (VPS) — 3-phase Research→Write→QA, every 2h
- E2E test suite — 60/60 Playwright tests passing (mocked backend, isolated from production)

### Agents (10 built)
| Agent | Role | Status |
|-------|------|--------|
| Jumbo | Orchestrator / lead | ✅ LIVE |
| Copywriter | Posts, hooks, ad copy | ✅ LIVE |
| QA Reviewer | 6-dimension quality scoring | ✅ LIVE |
| Trend Analyzer | Market research, trending | ✅ LIVE |
| Competitor Analyst | Competitor intel, threat scoring | ✅ LIVE |
| Visual Designer | Image briefs, carousel scripts | ✅ LIVE |
| Distributor | Schedule, platform optimization | ✅ LIVE |
| Analytics | Performance, weekly reports | ✅ LIVE |
| Brand Researcher | 8-section client intelligence | ✅ LIVE |
| Account Manager | Transcript analysis, action plans | ✅ LIVE |

### Slice History Summary
| Slice Range | What Was Built |
|-------------|---------------|
| 1–30 | Foundation: brand profiles, content pipeline, schedule, collections |
| 31–60 | Intelligence: trend analyzer, competitor analyst, QA agent, research sessions |
| 61–80 | Autonomy: Jumbo orchestrator, gateway bridge, autonomy controls, notifications |
| 81–87 | Distribution: auto-publish (Twitter/LinkedIn/Instagram), voice notes, starter kit |
| 88 | UX Overhaul: onboarding wizard, home inbox, 5-tab nav |
| 89 | SDK Orchestrator: 3-phase pipeline running on VPS every 2h |
| 90 | Marketing & Sales Command Center: 5-room nav, Agent Office, Kanban, Knowledge Base, Journal |
| 91a | Nano Banana 2 image gen: Claude Haiku prompt → Higgsfield primary → Gemini fallback |
| 91b | Zero-Setup Onboarding: name + URL → 30s auto-fill brand profile |
| 92c | Marketing Calendar + Competitor Embed |
| 92d | Notion sidebar + error visibility |
| 93 | Landing Page Generator (two-phase: Haiku blueprint → Sonnet HTML) |
| 94 | Pipeline Dashboard + Research Brief live feed |
| 95 | Lead Gen CRM: 3-engine enrichment, BANT, outreach, xlsx export |
| 97+98 | Client Intelligence System: Brand Researcher (5-layer), Account Manager, intake form, deliverables |
| 99 | Brand Intelligence Expansion: 8-section framework complete (Transformation, UVPs, Metaphors, Story, Belief) |
| 100 | Jumbo Brand Chat: brand-context-aware chat panel in Brand Intelligence Report; 6 quick actions; dossier injected into system prompt |
| 101 | Gemini-Style Agent Training + ICP Research: AgentTrainingPanel (Instructions textarea + Knowledge card grid), ICP Research 4-stage pipeline (Objective→Brand Snapshot→Research Questions→Apollo Filters), ICP tab in Sales room, E2E test infrastructure (60/60 Playwright tests, mocked backend) |

### What Each Deliverable Looks Like (Built)
| Deliverable | Format | Where |
|-------------|--------|-------|
| Brand Intelligence Dossier | Dark HTML (shareable) | /deliverables |
| Content posts | Text (LinkedIn/Twitter/Instagram) | Schedule queue |
| Carousels | Slide-by-slide text brief | agent_deliverables |
| Ad creatives | 40 variations (5 hook types × 8) | /ad-creative |
| Landing page | Full HTML page | /marketing → Landing Page tab |
| Proposal | Dark HTML (shareable) | /deliverables |
| Nurture sequence | 5 emails (HTML) | /deliverables |
| Lead list | .xlsx (Instantly-compatible) | /sales → Outreach tab |
| Enriched leads | Profile + BANT + icebreaker | /sales |
| Image assets | Generated via Nano Banana 2 | /marketing → Images |

---

## 2. THE FULL CLIENT JOURNEY (Target State)

The complete journey for every client has 7 phases.

```
PHASE 0          PHASE 1           PHASE 2           PHASE 3
Client Setup  →  Brand Intel   →   Strategy      →   Content Machine
(Day 1)          (Day 1-2)         (Week 1)           (Ongoing weekly)
                                        ↓
                              PHASE 4          PHASE 5       PHASE 6
                              Ad Machine   →   Sales     →   Reporting
                              (Week 2+)        Machine       (Monthly)
```

---

### PHASE 0 — CLIENT SETUP (Day 1, ~5 min)

**Who does it:** Agency owner (in the app)
**What happens:**
1. Agency owner clicks "Add Client" → creates `personal_brand` (is_client_brand=true)
2. Chooses intake method:
   - **Option A:** Just LinkedIn/website → Brand Researcher starts immediately
   - **Option B:** Send intake form link → client fills it online (no login needed)
   - **Option C:** Upload call recording → Account Manager transcribes + analyzes
3. System creates client workspace (brand_id, is_client_brand=true)

**Deliverable:** Client workspace created, intake link ready to share
**Agent doing it:** None (agency owner action)

---

### PHASE 1 — BRAND INTELLIGENCE RESEARCH (Day 1-2, automated ~90s)

**Who does it:** Brand Researcher agent (autonomous)
**What happens:** 8-section deep research runs automatically

#### The 8-Section Brand Intelligence Framework

**Section 1 — NICHE MARKET**
- Target market definition
- Market gaps (what's underserved)
- Customer segments: who / age / problems
- Audience target: who / age / specific issues
- Relevance topics (what they already follow/read)
- Power words + industry lingo specific to the niche

**Section 2 — TRANSFORMATION**
- BEFORE state (ZERO): What life looks like now (specific pain moments)
- AFTER state (DREAM): What life looks like after the transformation
- The emotional journey between the two

**Section 3 — NEW OPPORTUNITY**
- UVP 1, UVP 2, UVP 3 (unique value propositions)
- How they differ from competitors
- Tagline / niche statement

**Section 4 — METAPHORS**
- 3-5 analogies that make the message click
- Stories or comparisons that simplify complex ideas

**Section 5 — CONTENT STRATEGY**
- Platform priority (LinkedIn / Instagram / Twitter / YouTube)
- Content pillars (3-5)
- Posting frequency per platform
- Content formats per platform
- Channel acquisition strategy

**Section 6 — YOUR STORY**
- Background story (origin)
- Growth story & achievements
- Future goals & mission

**Section 7 — BELIEF FRAMEWORK**
- Belief statement (what they stand for)
- 3-5 false beliefs their ICA holds
- Counter-stories that break each false belief
- Bridge from false belief → new belief → offer

**Section 8 — REVENUE STREAMS**
- Main offer (type: service / consulting / digital / membership)
- Offer price + delivery model
- Secondary offers (upsells, downsells)
- Other income streams (affiliates, ads, partnerships)

**Deliverable:** Full Brand Intelligence Dossier (dark HTML, shareable link)
**Format:** 8-section expandable report with per-section Refresh button
**Agent:** Brand Researcher → reads playbook + training docs + runs web research

---

### PHASE 2 — STRATEGY GENERATION (Week 1, ~2 min)

**Who does it:** Offer Creator agent (autonomous after Phase 1 approved)

#### Offer Creation (Slice 102 — TODO)
- Reads full Brand Intelligence Dossier (all 8 sections)
- Has access to: Alex Hormozi books (uploaded to training), Agency SOPs
- Generates Grand Slam Offer document:
  - The core irresistible offer (using Value Equation)
  - Pricing structure recommendation
  - Guarantee / risk reversal
  - Bonus stacks
  - Delivery mechanism
  - Headline + sub-headline

**Deliverable:** Offer Document (dark HTML, structured expandable, shareable)
**Format:** Notion-style collapsible sections with inline edit + regenerate per section
**Agent:** Offer Creator (NEW — Slice 102)

#### Content Strategy Brief
- 90-day content roadmap
- Platform-specific cadence
- Hook bank seeding (first 20 hooks from all 8 research sections)
- Content calendar template

---

### PHASE 3 — CONTENT MACHINE (Ongoing, weekly)

**Who does it:** Copywriter + Visual Designer + QA Reviewer + Distributor agents
**What happens (automated weekly):**

#### Hook Library (Slice 103 — TODO)
- Brand Researcher generates 50+ hooks from all 8 sections, saved to DB
- Hooks organized by type: anxiety, benefit, story, competitor, belief, metaphor
- Each hook rated by predicted engagement
- **Partial coverage:** Jumbo Brand Chat (Slice 100) lets agency owner request 30 hooks on-demand

#### Content Production Pipeline (LIVE — VPS runs every 2h)
1. Trend Analyzer scans niche for trending topics
2. Copywriter picks best hook → writes post
3. Visual Designer creates image brief (if needed)
4. Image Generator creates image (Nano Banana 2)
5. QA Reviewer scores (80+ = pass)
6. Agency owner reviews in Home Inbox → Approve / Reject
7. Distributor schedules → auto-publishes

#### Content Types per Client (per month)
- 12-20 LinkedIn text posts
- 4-8 carousel posts (image + text)
- 4-8 short-form video scripts (Slice 102 — TODO)
- 4 Instagram Reels scripts (Slice 102 — TODO)
- 4 newsletter emails
- Ongoing: comment replies (Slice 103 — TODO)

#### Comment Strategy (Slice 103 — TODO)
- Competitor Analyst identifies top posts in niche
- Copywriter drafts 5 comments/week to post on others' content
- Agency owner approves → copies to clipboard (cannot auto-post comments)

**Deliverable:** Published content on LinkedIn/Instagram/Twitter/YouTube + content calendar
**Measurement:** Engagement rate, follower growth, reach (tracked in Analytics tab)

---

### PHASE 4 — AD MACHINE (Week 2 onwards)

**Who does it:** Visual Designer + Copywriter agents (+ agency owner connects ad account)

#### Ad Creative Generation (LIVE — Slice 83)
- 5 hook types × 8 variations = 40 ad creatives
- Platforms: Facebook, Instagram, LinkedIn
- Agency owner reviews → approves selected creatives

#### Ad Platform Connection (Slice 104 — TODO)
- Connect Meta Business Manager (OAuth per client brand)
- Upload approved creatives directly to Meta ad platform
- Set budget, audience, campaign objective inside the app
- LinkedIn Ads = Phase 2 (after Meta stable)

#### Landing Page (LIVE — Slice 93)
- Generated from brand dossier
- HTML page with hero copy from emotional pain journal
- Benefit section from benefit list
- FAQ from anxiety list
- Offer section from Hormozi framework

**Deliverable:** Live ad campaigns on Meta + landing page URL
**Measurement:** CTR, CPC, ROAS, conversions (needs ad platform API)

---

### PHASE 5 — SALES MACHINE (Ongoing)

**Who does it:** Lead Gen enrichment engine (LIVE — Slice 95)

#### Lead Generation (LIVE)
- 3-engine enrichment: personal LinkedIn → professional topics + achievements
- Company LinkedIn → hiring signals + pain points
- Website → company changes + growth signals
- BANT scoring (Budget/Authority/Need/Timing) — 0-4

#### Outreach (LIVE)
- AI-generated icebreaker (personalized to enrichment data)
- 3-message outreach sequence (LinkedIn DM + cold email)
- .xlsx export (Instantly.ai-compatible)

#### Nurture (LIVE)
- 5-email nurture sequence (from emotional journals + Hormozi)
- Account Manager generates on approval

**Deliverable:** Warm leads list + booked meetings
**Measurement:** Reply rate, meeting booked rate, pipeline value

---

### PHASE 6 — MONTHLY REPORTING (Slice 103 — TODO)

**Who does it:** Analytics agent
**What happens:**
- Pulls content metrics (engagement, reach, followers)
- Pulls lead metrics (leads enriched, outreach sent, replies)
- Generates monthly summary report

**Deliverable:** Monthly Performance Report (shareable HTML)
**Format:**
- Executive summary (3 bullets: wins / learnings / next month focus)
- Content performance (top 3 posts, platform breakdown)
- Lead generation summary
- Action items for next month

---

## 3. AGENT AUTONOMY MAP

Who does what, when, without the agency owner lifting a finger:

| Phase | Agent | Trigger | Human touchpoint |
|-------|-------|---------|-----------------|
| 0 | — | Owner adds client | Owner adds name + LinkedIn |
| 1 | Brand Researcher | Client added | Owner reviews dossier (5 min) |
| 2 | Offer Creator | Dossier approved | Owner reviews offer (5 min) — Slice 102 TODO |
| 3 | Copywriter | Every 2h (VPS) | Owner approves posts (10 min/day) |
| 3 | Visual Designer | Post approved | Automatic |
| 3 | QA Reviewer | Post drafted | Automatic |
| 3 | Distributor | Post approved | Automatic |
| 4 | Copywriter | Monthly | Owner reviews ad creatives (10 min) |
| 4 | Visual Designer | Monthly | Automatic |
| 5 | Lead Gen | Weekly | Owner reviews leads (15 min/week) |
| 6 | Analytics | Monthly | Owner sends report to client (1 click) |
| Ongoing | Account Manager | After each call | Owner approves action plan (10 min) |

**Agency owner's total weekly time per client: ~45 minutes**

---

## 4. GAP ANALYSIS — WHAT STILL NEEDS BUILDING

### Priority 1 (Core — Cannot Deliver Without These)

#### GAP B: Offer Creator Agent (Slice 102)
**Missing:** No offer_creator.py, no offer agent, no offer deliverable
**Impact:** No offer = no sales = agency can't show ROI
**Fix:** New agent + Hormozi-powered generation + Notion-style structured document
**Status:** TODO

#### GAP C: Hook Library Generator (Slice 103) — PARTIALLY CLOSED
**Partially closed by:** Slice 100 Jumbo Brand Chat (agency owner can request 30 hooks on-demand via "📎 30 Hooks" quick action)
**Missing:** Persistent hook library saved to DB, categorized by type, reusable across sessions
**Fix:** Service generates 50+ hooks from all 8 research sections, saves to DB, organized by type
**Status:** PARTIAL — on-demand via Jumbo Brand Chat; persistent library TODO (Slice 103)

### Priority 2 (High Value — Deliver After P1)

#### GAP D: Monthly Performance Report (Slice 104)
**Missing:** No report generator, no shareable client report
**Impact:** Clients can't see value → churn risk
**Fix:** Analytics agent generates HTML monthly report, shareable via share_token
**Status:** TODO

#### GAP E: Comment Strategy Generator (Slice 103)
**Missing:** No comment drafts for engaging on others' content
**Impact:** Missing key organic growth lever for LinkedIn
**Fix:** Competitor Analyst identifies top posts → Copywriter drafts 5 comments/week
**Status:** TODO

#### GAP F: Video Script Generator (Slice 103)
**Missing:** No short-form video scripts (Reels/TikTok/YouTube Shorts)
**Impact:** Video is #1 platform format right now
**Fix:** New content type: Copywriter generates script + hook + CTA (30-60s format)
**Status:** TODO

### Priority 3 (Scale)

#### GAP G: Ad Platform Integration — Meta First (Slice 105)
**Missing:** Can generate creatives but cannot upload to ad platform
**Impact:** Agency owner still has to manually upload ads
**Fix:** Meta Marketing API OAuth per client brand, stored in connectors table
**Status:** TODO

#### GAP I: Viral Content Analyzer (Slice 106)
**Missing:** No service to analyze what's performing in the client's niche
**Impact:** Missing data for trend-driven content
**Fix:** Perplexity searches top-performing posts → feeds Hook Library
**Status:** TODO

---

## 5. CLIENT-FACING DELIVERABLES (Complete List)

### What the client receives (via share links, no login needed):
| Deliverable | When Generated | Agent | Format |
|-------------|---------------|-------|--------|
| Intake Form | Day 0 (agency sends) | — | Web form |
| Brand Intelligence Dossier | Day 1-2 | Brand Researcher | Dark HTML, shareable |
| Grand Slam Offer Document | Week 1 | Offer Creator | Dark HTML, expandable sections |
| Content Strategy Brief | Week 1 | Strategist | Dark HTML, shareable |
| Sample Content (5 posts) | Week 1 | Copywriter | Text, shareable |
| Landing Page | Week 2 | Landing Page Gen | Full HTML, live URL |
| Ad Creatives (PDF/HTML) | Week 2 | Visual Designer + Copywriter | HTML gallery |
| Nurture Sequence (5 emails) | Week 2 | Account Manager | HTML preview |
| Monthly Report | Monthly | Analytics | Dark HTML, shareable |
| Proposal | Any time | Account Manager | Dark HTML, shareable |

**RULE: ALL outputs must have a Download button. Client never logs in.**

---

## 6. HOW IT'S MEASURED (Success Metrics per Client)

| Metric | Target | Where Tracked |
|--------|--------|--------------|
| Posts published / month | 12-20 | Schedule → Published |
| Avg engagement rate | >3% | Analytics tab |
| Profile views growth | +20%/month | Manual import (no API) |
| Followers growth | +5%/month | Manual import |
| Leads generated | 10+/month | Leads CRM |
| Outreach reply rate | >15% | Sequences tracker |
| Meetings booked | 3-5/month | Manual entry |
| Ad CTR | >2% | Ad platform (manual import) |
| Landing page conversion | >10% | Manual or via webhook |

---

## 7. RECOMMENDED BUILD ORDER (Slices 100–106)

### Slice 100 — Jumbo Brand Chat ✅ COMPLETE
- Brand-context-aware chat panel in Brand Intelligence Report
- 6 quick actions: 30 Hooks, Nurture Sequence, Offer Outline, 5 Posts, Comment Drafts, 90-Day Calendar
- Full 8-section dossier injected into Jumbo's system prompt (no tool call, fast responses)
- Copy button on all Jumbo responses

### Slice 101 — Gemini-Style Agent Training + ICP Research ✅ COMPLETE
- AgentTrainingPanel: Instructions textarea (saves as knowledge doc) + Knowledge card grid (Quick Note / PDF / URL)
- Intelligence page: each agent card has "Train" button expanding inline training panel
- IcpResearchPanel: 4-stage visible pipeline (Objective → Brand Snapshot → Research Questions → Apollo Filters)
- Stage 3 uses Perplexity for live ICP research; Stage 4 outputs Apollo.io filter sets + Apify hints
- `research_icp()` + `POST /leads/icp-research` + `GET /leads/icp-methodology` endpoints
- ICP tab added as first tab in Sales room
- E2E test infrastructure: `global-setup.ts`, `new-features-auth.spec.ts`, `new-features.spec.ts` — 60/60 passing
  - `page.route()` mocks all production API calls (decoupled from backend availability)
  - `page.addInitScript()` sets localStorage before React mounts (bypasses OnboardingGuard)

### Slice 102 — Offer Creator Agent
- New agent: Offer Creator (trained on Hormozi books + SOP docs)
- New service: offer_creator.py
- Reads complete 8-section dossier → generates Grand Slam Offer as structured document
- Components: Offer Name, Core Promise, Dream Outcome, Proof, Delivery Mechanism, Guarantee, Bonus Stack, Pricing
- Saved as client deliverable: download as HTML + shareable link

### Slice 103 — Hook Library + Comment Strategy + Video Scripts
- 50+ hooks from all 8 research sections, organized by type, saved to DB
- 5 comment drafts/week for niche engagement
- Hook rating by predicted engagement
- Quick Capture: agency owner adds their own hooks
- New content type: short-form video script (30-60s format, platform-specific)

### Slice 104 — Monthly Performance Report
- Analytics agent generates monthly summary
- Dark HTML, shareable link + download PDF
- Sections: wins, content performance, lead summary, next month plan

### Slice 105 — Meta Ads Integration
- Meta Marketing API OAuth (per client brand, stored in connectors table)
- Upload approved creatives to Meta
- Set campaign: objective, budget, audience
- View campaign status in app

### Slice 106 — Viral Content Analyzer
- Perplexity searches top-performing posts in client's niche
- Feeds hook library + content ideas
- Competitor Analyst adds "trending" data to dossier

---

## 8. TECHNICAL ARCHITECTURE NOTES

### Security (OWASP — maintained on all new slices)
- A01 IDOR: `.eq("user_id", user.id)` + `.eq("brand_id", brand_id)` on ALL queries
- A03 Injection: `_UUID_RE.match()` on all IDs, `_TOKEN_RE` on share tokens
- A07 Auth: `Depends(get_current_user)` on all private endpoints
- A10 SSRF: `validate_url_for_fetch()` before any HTTP fetch
- A04 Upload: 10MB cap on file uploads
- Public routes use 64-char random hex token (256-bit entropy)

### E2E Test Infrastructure (Slice 101)
- **Framework:** Playwright + `@playwright/test`
- **Auth:** `apps/web/tests/global-setup.ts` — logs in with real Supabase credentials, saves `storageState` to `playwright/.auth/user.json`
- **Mock pattern:** `page.route("https://api-iota-puce.vercel.app/**")` intercepts ALL backend calls per test — returns shape-correct JSON mocks. This means tests NEVER hit production backend and are not coupled to backend availability.
- **localStorage injection:** `page.addInitScript()` runs before React mounts — sets `onboarding_done=true` and `positionedup_current_brand_id` so `OnboardingGuard` and `BrandContext` see a valid state immediately.
- **Critical mock shapes:**
  - `/brands` → `{ brands: [FAKE_BRAND], total: 1 }` (NOT `{ data: [] }` — will crash `.filter()`)
  - `/notifications` → `[]` (array, not object)
  - `/stages` → `[]` (array)
  - `/deliverables` → `[]` (array)
  - `/schedule` → `{ draft: [], scheduled: [] }` (KanbanBoard shape)
  - `/pipeline/settings` → `{ enabled: false, run_interval_hours: 2, next_run_at: null, run_now: false }`
  - Default for unmatched endpoints → `[]` (safe: `.filter()/.map()` on array never crashes)
- **Test files:** `new-features-auth.spec.ts` (authenticated pages), `new-features.spec.ts` (public/general)
- **Result:** 60/60 tests passing

### Key Files
| Layer | Critical Files |
|-------|--------------|
| Agent orchestration | apps/api/app/services/tool_use_agents.py |
| Agent playbooks | apps/api/app/services/playbooks.py |
| Brand research | apps/api/app/services/client_researcher.py |
| Account management | apps/api/app/services/account_manager.py |
| Content pipeline | apps/api/app/services/jumbo_pipeline.py |
| Publishing | apps/api/app/services/publishing.py |
| Lead gen | apps/api/app/services/lead_gen.py |
| Main nav | apps/web/src/app/mission-control/constants.ts |
| Brand context | apps/web/src/lib/brand-context.tsx |
| API client | apps/web/src/lib/api/client.ts |
| E2E auth setup | apps/web/tests/global-setup.ts |
| E2E auth tests | apps/web/tests/new-features-auth.spec.ts |

### profile_json Schema (FULL — after Slice 99)
```json
{
  "positioning": "...",
  "voice": "...",
  "ica": "...",
  "offer": "...",
  "content_pillars": ["..."],
  "voice_adjectives": ["..."],
  "ica_summary": "...",
  "hormozi": {
    "dream_outcome": "...",
    "perceived_likelihood": "...",
    "time_to_result": "...",
    "effort_sacrifice": "...",
    "guarantee": "...",
    "risk_reversals": []
  },
  "anxiety_list": ["20 items"],
  "benefit_list": ["20 items"],
  "emotional_pain_journal": "500 words...",
  "emotional_win_journal": "500 words...",
  "competitors": [{"name": "...", "positioning": "...", "gap": "..."}],
  "competitor_gap": "...",
  "first_week_angles": [{"hook": "...", "angle_type": "...", "driven_by": "...", "offer_connection": "..."}],
  "transformation": {
    "zero_state": "Life BEFORE — specific pain moments",
    "dream_state": "Life AFTER — what the result looks like",
    "journey": "The emotional arc"
  },
  "uvps": ["UVP 1", "UVP 2", "UVP 3"],
  "tagline": "One memorable positioning line",
  "niche_statement": "I help [WHO] achieve [WHAT] without [OBJECTION]",
  "metaphors": ["analogy 1", "analogy 2", "analogy 3"],
  "your_story": {
    "background": "Origin story",
    "growth_achievements": "Key milestones + proof",
    "future_goals": "Where they're going",
    "mission": "Why they do it"
  },
  "belief_framework": {
    "belief_statement": "Core belief their methodology is built on",
    "false_beliefs": [
      {"belief": "False belief ICA holds", "counter_story": "Story that breaks it"}
    ]
  },
  "power_words": ["niche vocab 1", "word 2"],
  "industry_lingo": ["insider phrase 1", "phrase 2"],
  "market_gap": "The single underserved need this person can own",
  "customer_segments": [{"segment": "...", "age": "...", "problem": "..."}],
  "relevance_topics": ["topics/creators ICA already follows"]
}
```

---

## 9. KEY DECISIONS (LOCKED — March 2026)

### Q1: Content Platforms → ALL FOUR
LinkedIn + Instagram + Twitter/X + YouTube
- Video script generator needed (YouTube Shorts + Reels format)
- Platform-specific content adaptation per post
- Pipeline must produce format-aware content (character limits, hashtag rules)

### Q2: Approval Flow → AGENCY OWNER APPROVES EVERYTHING
- Multi-tenant SaaS — any agency owner can sign up and use the app
- Client NEVER logs in — they only receive finished deliverables
- Client interaction = download link / PDF / shareable HTML
- ALL generated outputs must have a Download button
- Approval = agency owner reviews in app → approves → agent executes or publishes

### Q3: Offer Document → STRUCTURED EXPANDABLE SECTIONS (Notion-style)
- Dark theme, each component is a named collapsible section
- 8 components: Offer Name, Core Promise, Dream Outcome, Proof, Delivery Mechanism, Guarantee, Bonus Stack, Pricing
- Inline edit + regenerate per section
- Download as PDF + shareable link

### Q4: Ad Platform → META FIRST (Facebook + Instagram)
- Meta Marketing API OAuth (per client brand)
- Upload approved creatives directly to Meta
- Set budget, audience, objective from inside the app
- LinkedIn Ads = Phase 2 (after Meta is stable)

---

## 10. PRODUCT VISION (FINAL — LOCKED)

**PositionedUp is a multi-tenant agency operating system.**

Any agency owner or founder can sign up, add their clients (or their own brand), and the AI agents autonomously handle:
- Brand research + positioning (8-section intelligence framework)
- Offer creation (Hormozi-powered)
- Content production (all 4 platforms)
- Ad creatives + campaign management (Meta first)
- Lead generation + outreach
- Monthly performance reporting

**The client never logs in.** They receive polished deliverables:
- Shareable HTML reports (open in browser, no login)
- Downloadable files (one click)
- Published content on their social profiles
- Booked meetings in their calendar

**Agency owner's time investment per client: ~45 min/week**

**What differentiates this from any other tool:** The agents are autonomous, coordinated, and trained on the agency's exact methodology. It's not a template tool — it's a done-for-you machine.

---

## 11. ENGINEERING RULES (Non-Negotiable)

1. **Every slice = pattern doc + project-log entry + gate format review**
2. **Every new endpoint = OWASP security check** (IDOR, Injection, SSRF, Auth)
3. **Every new service = unit tests** (minimum 10 tests per slice)
4. **TypeScript = 0 errors** before any slice is marked complete
5. **No client data without brand_id + user_id scoping**
6. **All public endpoints = 64-char hex share_token validation**
7. **All file uploads = 10MB cap + format validation**
8. **Download button on every generated deliverable**
9. **Scalable architecture** — every feature must work for 1 client or 1000 clients
10. **Gap analysis before every new slice**
