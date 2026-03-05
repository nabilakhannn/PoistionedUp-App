"""
Slice 95: Lead Gen CRM + Full Sales Room

15 tests across 6 classes:
  TestLeadGenService       (4): service file, generate_leads_from_icp, enrich_lead, generate_outreach
  TestLeadsRouter          (3): router file, IDOR guard, UUID validation on id + brand_id
  TestNewsletterRouter     (2): newsletter router file, POST /newsletter/generate in main.py
  TestLeadsCRMComponent    (3): leads-crm, outreach-queue, sequences-tracker components exist
  TestNewsletterComponents (2): newsletter-engine.tsx exists and uses newsletterApi
  TestLeadsApiClient       (2): leads.ts typed with bant_score + sequence; newsletter.ts exists
"""

from pathlib import Path

REPO = Path(__file__).parents[3]
API  = REPO / "apps" / "api"
WEB  = REPO / "apps" / "web" / "src"

LEAD_GEN_SERVICE  = API / "app" / "services" / "lead_gen.py"
LEADS_ROUTER      = API / "app" / "routers" / "leads.py"
NEWSLETTER_ROUTER = API / "app" / "routers" / "newsletter.py"
MAIN_PY           = API / "app" / "main.py"

LEADS_CRM         = WEB / "components" / "leads-crm.tsx"
OUTREACH_QUEUE    = WEB / "components" / "outreach-queue.tsx"
SEQUENCES_TRACKER = WEB / "components" / "sequences-tracker.tsx"
NEWSLETTER_ENGINE = WEB / "components" / "newsletter-engine.tsx"

LEADS_API_CLIENT  = WEB / "lib" / "api" / "leads.ts"
NEWSLETTER_CLIENT = WEB / "lib" / "api" / "newsletter.ts"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════════
# TestLeadGenService
# ═══════════════════════════════════════════════════════════════════════════


class TestLeadGenService:
    """lead_gen.py service has the 3 public functions and security patterns."""

    def test_service_file_exists(self):
        assert LEAD_GEN_SERVICE.exists(), (
            "apps/api/app/services/lead_gen.py not found — "
            "must be created with generate_leads_from_icp, enrich_lead, generate_outreach"
        )

    def test_generate_leads_from_icp(self):
        text = read(LEAD_GEN_SERVICE)
        assert "generate_leads_from_icp" in text, (
            "generate_leads_from_icp() missing from lead_gen.py — "
            "uses Perplexity sonar-pro to find real professionals matching the brand ICP"
        )
        assert "ica" in text, (
            "lead_gen.py must read brand profile 'ica' section to build ICP context — "
            "ICA = Ideal Customer Avatar defines demographics + pain points"
        )

    def test_enrich_lead_3_engine(self):
        text = read(LEAD_GEN_SERVICE)
        assert "enrich_lead" in text, (
            "enrich_lead() missing from lead_gen.py — "
            "must run 3 enrichment steps: personal LinkedIn, company LinkedIn, website"
        )
        # 7-field enrichment model
        assert "professional_topics" in text, (
            "professional_topics field missing from lead_gen.py — "
            "extracted from personal LinkedIn posts (enrichment field 1)"
        )
        assert "pain_points" in text, (
            "pain_points field missing from lead_gen.py — "
            "extracted from company LinkedIn posts (enrichment field 4)"
        )
        assert "bant_score" in text, (
            "bant_score missing from lead_gen.py — "
            "auto-computed 0-4 score (Budget/Authority/Need/Timing) returned by enrich_lead()"
        )
        assert "validate_url_for_fetch" in text, (
            "validate_url_for_fetch() missing from lead_gen.py — "
            "SSRF guard required before any httpx website fetch (OWASP A10)"
        )

    def test_generate_outreach(self):
        text = read(LEAD_GEN_SERVICE)
        assert "generate_outreach" in text, (
            "generate_outreach() missing from lead_gen.py — "
            "generates icebreaker + LinkedIn DM + cold email + 3-message sequence"
        )
        assert "icebreaker" in text, (
            "icebreaker key missing from lead_gen.py — "
            "1-2 sentence hyper-personalized opener anchored to a specific enrichment fact"
        )
        assert "sequence" in text, (
            "sequence key missing from lead_gen.py — "
            "3-message cadence: Message 1 (Connect), Message 2 (Day 3), Message 3 (Day 7)"
        )
        assert "sent_at" in text, (
            "sent_at field missing from sequence in lead_gen.py — "
            "each sequence message must include sent_at: null for tracking (gap 26)"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TestLeadsRouter
# ═══════════════════════════════════════════════════════════════════════════


class TestLeadsRouter:
    """leads.py router has all 9 endpoints with auth + IDOR + UUID guards."""

    def test_router_file_exists(self):
        assert LEADS_ROUTER.exists(), (
            "apps/api/app/routers/leads.py not found — "
            "must expose GET/POST /leads, /leads/generate, /leads/enrich/{id}, "
            "/leads/outreach/{id}, PATCH /leads/{id}, DELETE /leads/{id}, GET /leads/export"
        )

    def test_idor_guard_on_all_queries(self):
        text = read(LEADS_ROUTER)
        assert "user.id" in text and "leads" in text, (
            "IDOR guard missing from leads.py — "
            "all DB queries must filter .eq('user_id', user.id) (OWASP A01)"
        )
        assert "get_current_user" in text, (
            "get_current_user dependency missing from leads.py — "
            "all endpoints must require JWT authentication (OWASP A07)"
        )

    def test_uuid_validation_on_ids(self):
        text = read(LEADS_ROUTER)
        assert "_UUID_RE" in text, (
            "_UUID_RE pattern missing from leads.py — "
            "both lead_id and brand_id parameters must be validated as UUIDs (OWASP A03)"
        )
        assert "openpyxl" in text or "xlsx" in text.lower(), (
            "openpyxl / xlsx export missing from leads.py — "
            "GET /leads/export must return Instantly.ai-compatible .xlsx file (gap 24)"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TestNewsletterRouter
# ═══════════════════════════════════════════════════════════════════════════


class TestNewsletterRouter:
    """newsletter.py router has GET /newsletter/draft + POST /newsletter/generate."""

    def test_newsletter_router_exists(self):
        assert NEWSLETTER_ROUTER.exists(), (
            "apps/api/app/routers/newsletter.py not found — "
            "must expose GET /newsletter/draft and POST /newsletter/generate"
        )
        text = read(NEWSLETTER_ROUTER)
        assert "/newsletter/generate" in text or "generate" in text, (
            "POST /newsletter/generate endpoint missing from newsletter.py — "
            "writes 400-600 word newsletter from latest research_brief"
        )
        assert "research_briefs" in text, (
            "newsletter.py must query research_briefs table — "
            "newsletter content is derived from the latest pipeline research brief"
        )

    def test_newsletter_router_registered_in_main(self):
        text = read(MAIN_PY)
        assert "newsletter" in text, (
            "newsletter router not registered in main.py — "
            "must add: from app.routers import newsletter + app.include_router(newsletter.router)"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TestLeadsCRMComponent
# ═══════════════════════════════════════════════════════════════════════════


class TestLeadsCRMComponent:
    """Frontend Sales room tab components exist and have the right shape."""

    def test_leads_crm_component_exists(self):
        assert LEADS_CRM.exists(), (
            "apps/web/src/components/leads-crm.tsx not found — "
            "table-first lead list with Kanban toggle, bulk actions, enrichment, and detail panel"
        )
        text = read(LEADS_CRM)
        assert "leadsApi" in text, (
            "leadsApi not imported in leads-crm.tsx — "
            "component must call leadsApi.list(), enrich(), generateOutreach(), update(), etc."
        )
        assert "bant_score" in text or "BantDots" in text or "bant" in text.lower(), (
            "BANT score display missing from leads-crm.tsx — "
            "each lead row must show 0-4 BANT dots for outreach prioritisation"
        )

    def test_outreach_queue_component_exists(self):
        assert OUTREACH_QUEUE.exists(), (
            "apps/web/src/components/outreach-queue.tsx not found — "
            "Outreach tab: derived view from leads with outreach_draft, grouped by channel"
        )
        text = read(OUTREACH_QUEUE)
        assert "outreach_draft" in text or "outreachDraft" in text or "leadsApi" in text, (
            "outreach-queue.tsx must read outreach_draft from leads (via leadsApi.list) — "
            "no separate DB table needed; derived view from leads table"
        )

    def test_sequences_tracker_component_exists(self):
        assert SEQUENCES_TRACKER.exists(), (
            "apps/web/src/components/sequences-tracker.tsx not found — "
            "Sequences tab: per-lead 3-message tracker with sent_at checkbox"
        )
        text = read(SEQUENCES_TRACKER)
        assert "sent_at" in text, (
            "sent_at tracking missing from sequences-tracker.tsx — "
            "checkbox must toggle sent_at between null and ISO timestamp via PATCH /leads/{id}"
        )
        assert "leadsApi" in text, (
            "leadsApi not imported in sequences-tracker.tsx — "
            "must call leadsApi.list() and leadsApi.update() to toggle sent_at"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TestNewsletterComponents
# ═══════════════════════════════════════════════════════════════════════════


class TestNewsletterComponents:
    """newsletter-engine.tsx exists and uses newsletterApi correctly."""

    def test_newsletter_engine_exists(self):
        assert NEWSLETTER_ENGINE.exists(), (
            "apps/web/src/components/newsletter-engine.tsx not found — "
            "Newsletter tab: generate + editable draft + copy to clipboard"
        )

    def test_newsletter_engine_uses_api(self):
        text = read(NEWSLETTER_ENGINE)
        assert "newsletterApi" in text, (
            "newsletterApi not imported in newsletter-engine.tsx — "
            "must call newsletterApi.getDraft() on mount and newsletterApi.generate() on button click"
        )
        assert "getDraft" in text, (
            "newsletterApi.getDraft() not called in newsletter-engine.tsx — "
            "must load existing draft on mount so user doesn't lose previous generation"
        )
        assert "generate" in text, (
            "newsletterApi.generate() not called in newsletter-engine.tsx — "
            "Generate button must call this and update the editable textarea"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TestLeadsApiClient
# ═══════════════════════════════════════════════════════════════════════════


class TestLeadsApiClient:
    """leads.ts and newsletter.ts API clients follow project patterns."""

    def test_leads_api_client_typed_correctly(self):
        assert LEADS_API_CLIENT.exists(), (
            "apps/web/src/lib/api/leads.ts not found — "
            "must export Lead interface + leadsApi with list/create/generate/enrich/update/remove"
        )
        text = read(LEADS_API_CLIENT)
        assert "bant_score" in text, (
            "bant_score missing from Lead interface in leads.ts — "
            "BANT score (0-4) must be typed for UI display"
        )
        assert "sent_at" in text, (
            "sent_at missing from SequenceMessage interface in leads.ts — "
            "each sequence message must have sent_at: string | null for tracking (gap 26)"
        )
        assert "exportXlsx" in text or "export" in text.lower(), (
            "exportXlsx method missing from leadsApi in leads.ts — "
            "must download .xlsx via Blob URL (not anchor tag — Vercel auth gap 2)"
        )
        assert "apiFetch" in text, (
            "apiFetch not used in leads.ts — "
            "must follow project API client pattern from ./client"
        )

    def test_newsletter_api_client_exists(self):
        assert NEWSLETTER_CLIENT.exists(), (
            "apps/web/src/lib/api/newsletter.ts not found — "
            "must export newsletterApi with getDraft(brandId) and generate(brandId)"
        )
        text = read(NEWSLETTER_CLIENT)
        assert "newsletterApi" in text, (
            "newsletterApi not exported from newsletter.ts — "
            "components import this object to call generate + getDraft"
        )
        assert "getDraft" in text and "generate" in text, (
            "newsletterApi must have both getDraft() and generate() methods — "
            "getDraft for initial load; generate for triggering new newsletter creation"
        )
