"""
Slice 92c: Marketing Calendar + Competitor Embed

10 tests across 4 classes:
  TestMarketingCalendarComponent  — 3  (file exists, imports scheduleApi, calls getCalendar)
  TestCompetitorIntelComponent    — 3  (file exists, imports competitorsApi, has Full Dashboard link)
  TestMarketingPageUpdate         — 2  (calendar placeholder gone, competitors placeholder gone)
  TestBackendEndpointShapes       — 2  (schedule /calendar endpoint, competitors /intelligence endpoint)
"""

from pathlib import Path

REPO = Path(__file__).parents[3]
API = REPO / "apps" / "api"
WEB = REPO / "apps" / "web" / "src"

MARKETING_CALENDAR = WEB / "components" / "marketing-calendar.tsx"
COMPETITOR_EMBED = WEB / "components" / "competitor-intel-embed.tsx"
MARKETING_PAGE = WEB / "app" / "marketing" / "page.tsx"
SCHEDULE_ROUTER = API / "app" / "routers" / "schedule.py"
COMPETITORS_ROUTER = API / "app" / "routers" / "competitors.py"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════════
# TestMarketingCalendarComponent
# ═══════════════════════════════════════════════════════════════════════════


class TestMarketingCalendarComponent:
    """marketing-calendar.tsx exists and uses scheduleApi correctly."""

    def test_calendar_component_file_exists(self):
        assert MARKETING_CALENDAR.exists(), (
            "apps/web/src/components/marketing-calendar.tsx not found — "
            "MarketingCalendar component must be created"
        )

    def test_calendar_imports_schedule_api(self):
        text = read(MARKETING_CALENDAR)
        assert "scheduleApi" in text, (
            "marketing-calendar.tsx must import scheduleApi from @/lib/api/schedule"
        )
        assert "schedule" in text.lower(), (
            "marketing-calendar.tsx must reference schedule API module"
        )

    def test_calendar_calls_get_calendar(self):
        text = read(MARKETING_CALENDAR)
        assert "getCalendar" in text, (
            "MarketingCalendar must call scheduleApi.getCalendar() to fetch month items"
        )
        assert "brandId" in text, (
            "MarketingCalendar must accept and use brandId prop for brand-scoped queries"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TestCompetitorIntelComponent
# ═══════════════════════════════════════════════════════════════════════════


class TestCompetitorIntelComponent:
    """competitor-intel-embed.tsx exists and uses competitorsApi correctly."""

    def test_competitor_embed_file_exists(self):
        assert COMPETITOR_EMBED.exists(), (
            "apps/web/src/components/competitor-intel-embed.tsx not found — "
            "CompetitorIntelEmbed component must be created"
        )

    def test_competitor_embed_imports_competitors_api(self):
        text = read(COMPETITOR_EMBED)
        assert "competitorsApi" in text, (
            "competitor-intel-embed.tsx must import competitorsApi"
        )
        assert "getIntelligenceFeed" in text, (
            "CompetitorIntelEmbed must call competitorsApi.getIntelligenceFeed() for stats"
        )

    def test_competitor_embed_has_full_dashboard_link(self):
        text = read(COMPETITOR_EMBED)
        assert "/mission-control/competitors" in text, (
            "CompetitorIntelEmbed must include 'Full Dashboard →' link to "
            "/mission-control/competitors for the deep-dive view"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TestMarketingPageUpdate
# ═══════════════════════════════════════════════════════════════════════════


class TestMarketingPageUpdate:
    """Marketing page no longer shows placeholder text for Calendar or Competitors tabs."""

    def _page(self) -> str:
        assert MARKETING_PAGE.exists(), "apps/web/src/app/marketing/page.tsx not found"
        return read(MARKETING_PAGE)

    def test_calendar_placeholder_removed(self):
        text = self._page()
        assert "Coming in Slice 91" not in text, (
            "Calendar tab still shows 'Coming in Slice 91' placeholder — "
            "replace with MarketingCalendar component"
        )
        assert "MarketingCalendar" in text, (
            "marketing/page.tsx must render <MarketingCalendar brandId={...} /> in calendar tab"
        )

    def test_competitors_placeholder_removed(self):
        text = self._page()
        assert "This tab will surface a summary here in Slice 91" not in text, (
            "Competitors tab still shows placeholder text — "
            "replace with CompetitorIntelEmbed component"
        )
        assert "CompetitorIntelEmbed" in text, (
            "marketing/page.tsx must render <CompetitorIntelEmbed brandId={...} /> in competitors tab"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TestBackendEndpointShapes
# ═══════════════════════════════════════════════════════════════════════════


class TestBackendEndpointShapes:
    """Backend endpoints used by the new components already exist and have correct paths."""

    def test_schedule_calendar_endpoint_exists(self):
        assert SCHEDULE_ROUTER.exists(), "apps/api/app/routers/schedule.py not found"
        text = read(SCHEDULE_ROUTER)
        assert "/calendar" in text, (
            "GET /schedule/calendar endpoint missing from schedule.py — "
            "MarketingCalendar relies on this to fetch items by date range"
        )
        assert "start" in text and "end" in text, (
            "/schedule/calendar endpoint must accept 'start' and 'end' query parameters"
        )

    def test_competitors_intelligence_endpoint_exists(self):
        assert COMPETITORS_ROUTER.exists(), "apps/api/app/routers/competitors.py not found"
        text = read(COMPETITORS_ROUTER)
        assert "/intelligence" in text, (
            "GET /competitors/intelligence endpoint missing from competitors.py — "
            "CompetitorIntelEmbed relies on this for feed stats"
        )
        assert "IntelligenceFeed" in text or "active_competitors" in text, (
            "/competitors/intelligence must return IntelligenceFeed with active_competitors field"
        )
