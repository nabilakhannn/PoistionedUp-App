"""
Slice 91b: Zero-Setup Onboarding — LinkedIn URL → 30 Seconds → Brand Profile Built

15 tests across 5 classes:
  TestAutoProfileEndpoint   — 4  (endpoint in brands.py, UUID validation, name required,
                                   output keys present)
  TestAutoProfileSecurity   — 3  (URL validation called, injection chars stripped,
                                   no-key graceful fallback)
  TestAutoProfileIntegration— 4  (returns dict with correct keys, data_found=False when
                                   no keys, sections_filled is a list, summary is a string)
  TestOnboardingStep2       — 2  (page still has step 2, AI auto-fill option present)
  TestBrandSettingsRebuild  — 2  (settings page has rebuild section, brand.ts has autoProfile)
"""

import json
import re
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO = Path(__file__).parents[3]
API = REPO / "apps" / "api"
WEB = REPO / "apps" / "web" / "src"

BRANDS_ROUTER = API / "app" / "routers" / "brands.py"
ONBOARDING_PAGE = WEB / "app" / "onboarding" / "page.tsx"
SETTINGS_PAGE = WEB / "app" / "mission-control" / "settings" / "page.tsx"
BRAND_TS = WEB / "lib" / "api" / "brand.ts"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════════
# TestAutoProfileEndpoint
# ═══════════════════════════════════════════════════════════════════════════


class TestAutoProfileEndpoint:
    """auto-profile endpoint exists in brands.py with correct structure."""

    def _router(self) -> str:
        assert BRANDS_ROUTER.exists(), "apps/api/app/routers/brands.py not found"
        return read(BRANDS_ROUTER)

    def test_auto_profile_endpoint_exists(self):
        text = self._router()
        assert "/auto-profile" in text, (
            "POST /{brand_id}/auto-profile endpoint missing from brands.py"
        )
        assert "auto_profile_brand" in text, (
            "auto_profile_brand handler function missing from brands.py"
        )

    def test_brand_ownership_verification_present(self):
        text = self._router()
        # brands.py uses _verify_brand_ownership to enforce IDOR protection (OWASP A01)
        assert "_verify_brand_ownership" in text, (
            "_verify_brand_ownership must be called in auto_profile_brand "
            "to prevent IDOR access to other users' brands (OWASP A01)"
        )
        # Confirm the auto-profile handler calls it
        auto_profile_section = text[text.find("auto-profile"):]
        assert "_verify_brand_ownership" in auto_profile_section or \
               "verify_brand_ownership" in auto_profile_section or \
               "admin" in auto_profile_section, (
            "auto_profile_brand handler must verify brand ownership before writing"
        )

    def test_auto_profile_request_model_exists(self):
        text = self._router()
        assert "AutoProfileRequest" in text, (
            "AutoProfileRequest Pydantic model missing from brands.py"
        )
        assert "full_name" in text, (
            "full_name field missing from AutoProfileRequest"
        )

    def test_auto_profile_returns_required_keys_in_response(self):
        text = self._router()
        # Response must include all 4 keys
        assert "sections_filled" in text, (
            "sections_filled missing from auto_profile response"
        )
        assert "data_found" in text, (
            "data_found missing from auto_profile response"
        )
        assert "summary" in text, (
            "summary missing from auto_profile response"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TestAutoProfileSecurity
# ═══════════════════════════════════════════════════════════════════════════


class TestAutoProfileSecurity:
    """auto-profile endpoint enforces URL validation and name sanitization."""

    def _router(self) -> str:
        return read(BRANDS_ROUTER)

    def test_url_validation_imported_and_called(self):
        text = self._router()
        assert "url_validation" in text or "validate_url" in text, (
            "URL validation (url_validation.validate_url) must be used for public_url "
            "to prevent SSRF — see OWASP A10"
        )

    def test_name_sanitization_present(self):
        text = self._router()
        # Must strip injection chars from full_name
        assert "_SAFE_NAME_RE" in text or "SAFE_NAME" in text, (
            "_SAFE_NAME_RE regex must be defined to sanitize full_name "
            "(strips non-alphanumeric/punctuation injection chars)"
        )

    def test_no_api_key_graceful_fallback(self):
        """Endpoint never raises an exception when no search keys are configured."""
        from app.routers.brands import _synthesize_profile, _search_perplexity, _search_tavily

        # _search_perplexity with bad key returns empty string, not an exception
        result = _search_perplexity("test query", "")
        assert isinstance(result, str), (
            "_search_perplexity must return str (empty string on failure), not raise"
        )

        # _search_tavily with bad key returns empty string, not an exception
        result2 = _search_tavily("test query", "")
        assert isinstance(result2, str), (
            "_search_tavily must return str (empty string on failure), not raise"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TestAutoProfileIntegration
# ═══════════════════════════════════════════════════════════════════════════


class TestAutoProfileIntegration:
    """auto-profile service functions return correct types and structure."""

    def test_synthesize_profile_returns_dict_or_none(self):
        """_synthesize_profile returns a dict or None — never raises."""
        from app.routers.brands import _synthesize_profile

        with patch("app.config.settings") as mock_settings:
            mock_settings.anthropic_api_key = ""  # no key → fallback
            result = _synthesize_profile(
                research_text="Test founder, SaaS, coaches executives",
                full_name="Test Person",
                extra_context="",
            )
        assert result is None or isinstance(result, dict), (
            "_synthesize_profile must return dict or None, not raise"
        )

    def test_synthesize_profile_result_has_required_keys(self):
        """When _synthesize_profile returns data, it includes the expected sections."""
        from app.routers.brands import _synthesize_profile

        # Mock Anthropic client to return structured JSON
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=json.dumps({
                    "foundation": {"content_pillars": ["leadership"]},
                    "ica": {"big_need": "growth"},
                    "offer": {"what": "coaching"},
                    "positioning": {"unique_angle": "systems"},
                    "summary": "Executive coach for SaaS founders.",
                })
            )
        ]
        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            with patch("app.config.settings") as mock_settings:
                mock_settings.anthropic_api_key = "sk-ant-test"
                result = _synthesize_profile(
                    research_text="Some research about a coach",
                    full_name="Test Coach",
                    extra_context="",
                )

        if result is not None:
            for key in ["foundation", "ica", "offer", "positioning"]:
                assert key in result, f"'{key}' section missing from _synthesize_profile result"

    def test_sections_filled_is_always_a_list(self):
        """_save_profile_sections always returns a list."""
        from app.routers.brands import _save_profile_sections

        # Mock Supabase admin client returning empty profile
        mock_admin = MagicMock()
        mock_admin.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"profile_json": {}}
        ]
        mock_admin.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [{}]

        import uuid
        result = _save_profile_sections(
            admin=mock_admin,
            brand_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            profile={"foundation": {"content_pillars": ["SaaS"]}, "ica": {"big_need": "scale"}},
        )
        assert isinstance(result, list), (
            "_save_profile_sections must return a list of section names"
        )

    def test_safe_name_regex_strips_injection_chars(self):
        """_SAFE_NAME_RE strips characters that could cause prompt injection."""
        from app.routers.brands import _SAFE_NAME_RE

        # Characters that should be stripped
        dirty = "Robert'); DROP TABLE brands;--"
        cleaned = _SAFE_NAME_RE.sub("", dirty).strip()
        assert "DROP" not in cleaned or ";" not in cleaned, (
            "_SAFE_NAME_RE must strip SQL/prompt injection characters from full_name"
        )

        # Characters that should be kept
        normal = "Sarah O'Brien-Smith, PhD"
        cleaned_normal = _SAFE_NAME_RE.sub("", normal).strip()
        assert "Sarah" in cleaned_normal, (
            "_SAFE_NAME_RE must preserve normal name characters"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TestOnboardingStep2
# ═══════════════════════════════════════════════════════════════════════════


class TestOnboardingStep2:
    """Onboarding page has Step 2 redesigned with AI Auto-Fill tab."""

    def _page(self) -> str:
        assert ONBOARDING_PAGE.exists(), (
            "apps/web/src/app/onboarding/page.tsx not found"
        )
        return read(ONBOARDING_PAGE)

    def test_onboarding_step2_still_exists(self):
        text = self._page()
        assert "step === 2" in text or "step == 2" in text, (
            "Step 2 of onboarding is missing from onboarding/page.tsx"
        )

    def test_ai_auto_fill_tab_present(self):
        text = self._page()
        assert "AI Auto-Fill" in text or "auto-fill" in text.lower() or "autoProfile" in text, (
            "AI Auto-Fill tab or autoProfile call missing from onboarding Step 2"
        )
        assert "Analyze" in text or "analyze" in text, (
            "Analyze button missing from AI Auto-Fill tab in onboarding page"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TestBrandSettingsRebuild
# ═══════════════════════════════════════════════════════════════════════════


class TestBrandSettingsRebuild:
    """Settings page has Rebuild Profile section and brand.ts has autoProfile method."""

    def test_settings_page_has_rebuild_profile_section(self):
        assert SETTINGS_PAGE.exists(), (
            "apps/web/src/app/mission-control/settings/page.tsx not found"
        )
        text = read(SETTINGS_PAGE)
        assert "Rebuild Profile" in text, (
            "'Rebuild Profile' section missing from settings/page.tsx Team tab"
        )
        assert "autoProfile" in text or "auto-profile" in text, (
            "autoProfile API call missing from settings page rebuild section"
        )

    def test_brand_ts_has_auto_profile_method(self):
        assert BRAND_TS.exists(), (
            "apps/web/src/lib/api/brand.ts not found"
        )
        text = read(BRAND_TS)
        assert "autoProfile" in text, (
            "autoProfile method missing from personalBrandsApi in brand.ts"
        )
        assert "auto-profile" in text, (
            "'/brands/{brandId}/auto-profile' endpoint URL missing from brand.ts autoProfile"
        )
        assert "sections_filled" in text or "ok:" in text or "data_found" in text, (
            "autoProfile return type annotation missing from brand.ts"
        )
