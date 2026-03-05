"""
Slice 99: Brand Intelligence Expansion — 8-Section Framework Complete

14 tests across 3 classes:
  TestBrandResearcherExpansion  (6): 5 new sections in schema + refresh_section allows new keys
  TestPlaybookExpansion         (4): brand-researcher playbook covers all 8 sections
  TestFrontendExpansion         (4): client-research.ts types + brand-intelligence-report UI sections
"""

from pathlib import Path

REPO = Path(__file__).parents[3]
API  = REPO / "apps" / "api"
WEB  = REPO / "apps" / "web" / "src"

CLIENT_RESEARCHER   = API / "app" / "services" / "client_researcher.py"
PLAYBOOKS_SVC       = API / "app" / "services" / "playbooks.py"
CLIENT_RESEARCH_TS  = WEB / "lib" / "api" / "client-research.ts"
INTEL_REPORT        = WEB / "components" / "brand-intelligence-report.tsx"
MASTER_DOC          = REPO / "docs" / "compound" / "MASTER-SYSTEM-DESIGN.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════════
# TestBrandResearcherExpansion
# ═══════════════════════════════════════════════════════════════════════════


class TestBrandResearcherExpansion:
    """client_researcher.py system prompt has all 8 sections in output schema."""

    def test_transformation_in_schema(self):
        text = read(CLIENT_RESEARCHER)
        assert '"transformation"' in text or "'transformation'" in text, (
            '"transformation" field missing from _BRAND_RESEARCHER_SYSTEM schema — '
            "Brand Researcher cannot produce Section 2 (ZERO→DREAM)"
        )

    def test_uvps_in_schema(self):
        text = read(CLIENT_RESEARCHER)
        assert '"uvps"' in text or "'uvps'" in text, (
            '"uvps" field missing from schema — '
            "Brand Researcher cannot produce Section 3 (UVPs)"
        )

    def test_metaphors_in_schema(self):
        text = read(CLIENT_RESEARCHER)
        assert '"metaphors"' in text or "'metaphors'" in text, (
            '"metaphors" field missing from schema — '
            "Brand Researcher cannot produce Section 4 (Metaphors)"
        )

    def test_your_story_in_schema(self):
        text = read(CLIENT_RESEARCHER)
        assert '"your_story"' in text or "'your_story'" in text, (
            '"your_story" field missing from schema — '
            "Brand Researcher cannot produce Section 6 (Your Story)"
        )

    def test_belief_framework_in_schema(self):
        text = read(CLIENT_RESEARCHER)
        assert '"belief_framework"' in text or "'belief_framework'" in text, (
            '"belief_framework" field missing from schema — '
            "Brand Researcher cannot produce Section 7 (Belief Framework)"
        )

    def test_power_words_and_market_gap_in_schema(self):
        text = read(CLIENT_RESEARCHER)
        assert '"power_words"' in text and '"market_gap"' in text, (
            '"power_words" or "market_gap" missing from schema — '
            "Brand Researcher is missing niche intelligence fields"
        )

    def test_refresh_section_allows_transformation(self):
        text = read(CLIENT_RESEARCHER)
        assert '"transformation"' in text or "'transformation'" in text, (
            "transformation not in refresh_section allowed set — "
            "cannot refresh Section 2 independently"
        )

    def test_refresh_section_allows_belief_framework(self):
        text = read(CLIENT_RESEARCHER)
        assert '"belief_framework"' in text or "'belief_framework'" in text, (
            "belief_framework not in refresh_section allowed set — "
            "cannot refresh Section 7 independently"
        )

    def test_more_web_searches_instructed(self):
        text = read(CLIENT_RESEARCHER)
        # Should have at least 6 search steps now (was 5)
        assert "6" in text or "7" in text or "8" in text, (
            "research_client user_prompt should instruct 6+ web searches — "
            "8-section research requires more data than 5-layer version"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TestPlaybookExpansion
# ═══════════════════════════════════════════════════════════════════════════


class TestPlaybookExpansion:
    """brand-researcher playbook covers all 8 sections."""

    def test_playbook_has_8_sections(self):
        text = read(PLAYBOOKS_SVC)
        brand_researcher_section = text[text.find('"brand-researcher"'):]
        assert "Section 1" in brand_researcher_section and "Section 8" in brand_researcher_section, (
            "brand-researcher playbook does not have all 8 sections — "
            "agent will not know how to structure its research"
        )

    def test_playbook_has_transformation_section(self):
        text = read(PLAYBOOKS_SVC)
        assert "TRANSFORMATION" in text or "ZERO" in text or "DREAM STATE" in text, (
            "brand-researcher playbook missing TRANSFORMATION section — "
            "agent won't know to research BEFORE/AFTER state"
        )

    def test_playbook_has_belief_framework_section(self):
        text = read(PLAYBOOKS_SVC)
        assert "BELIEF FRAMEWORK" in text or "false_beliefs" in text or "False beliefs" in text, (
            "brand-researcher playbook missing BELIEF FRAMEWORK section — "
            "agent won't know to find false beliefs and counter-stories"
        )

    def test_playbook_has_power_words_mention(self):
        text = read(PLAYBOOKS_SVC)
        assert "power_words" in text or "Power words" in text or "Power Words" in text, (
            "brand-researcher playbook missing power_words — "
            "agent won't know to extract niche vocabulary"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TestFrontendExpansion
# ═══════════════════════════════════════════════════════════════════════════


class TestFrontendExpansion:
    """client-research.ts types and brand-intelligence-report.tsx have new sections."""

    def test_transformation_in_ts_interface(self):
        text = read(CLIENT_RESEARCH_TS)
        assert "transformation" in text and "zero_state" in text, (
            "ClientDossier missing 'transformation' interface in client-research.ts — "
            "TypeScript will not type-check new Section 2 fields"
        )

    def test_belief_framework_in_ts_interface(self):
        text = read(CLIENT_RESEARCH_TS)
        assert "BeliefFramework" in text or "belief_framework" in text, (
            "ClientDossier missing 'belief_framework' in client-research.ts — "
            "TypeScript will not type-check Section 7"
        )

    def test_refresh_section_type_includes_new_sections(self):
        text = read(CLIENT_RESEARCH_TS)
        assert '"transformation"' in text and '"belief_framework"' in text and '"uvps"' in text, (
            "RefreshSection type in client-research.ts missing new section names — "
            "UI refresh buttons will have TypeScript errors"
        )

    def test_ui_has_transformation_card(self):
        text = read(INTEL_REPORT)
        assert "ZERO STATE" in text or "zero_state" in text or "Transformation" in text, (
            "brand-intelligence-report.tsx missing Transformation section card — "
            "Section 2 (ZERO→DREAM) not visible to user"
        )

    def test_ui_has_belief_framework_card(self):
        text = read(INTEL_REPORT)
        assert "Belief Framework" in text or "belief_framework" in text or "false_beliefs" in text, (
            "brand-intelligence-report.tsx missing Belief Framework card — "
            "Section 7 not visible to user"
        )

    def test_master_doc_exists(self):
        assert MASTER_DOC.exists(), (
            "docs/compound/MASTER-SYSTEM-DESIGN.md missing — "
            "master system design document not saved permanently"
        )

    def test_master_doc_has_8_sections(self):
        text = read(MASTER_DOC)
        assert "8-Section" in text and "TRANSFORMATION" in text and "BELIEF FRAMEWORK" in text, (
            "MASTER-SYSTEM-DESIGN.md missing 8-section framework details — "
            "document is incomplete"
        )
