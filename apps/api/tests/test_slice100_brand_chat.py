"""
Slice 100: Jumbo Brand Chat — Brand-Context-Aware AI Chat

10 tests across 3 classes:
  TestBrandChatService  (4): service exists, send_chat_message function, dossier injection, _trim_dossier
  TestBrandChatRouter   (3): router registered, UUID guard, POST endpoint
  TestFrontendBrandChat (3): component exists, API client exists, quick actions defined
"""

from pathlib import Path

REPO = Path(__file__).parents[3]
API  = REPO / "apps" / "api"
WEB  = REPO / "apps" / "web" / "src"

BRAND_CHAT_SVC    = API / "app" / "services" / "brand_chat.py"
BRAND_CHAT_ROUTER = API / "app" / "routers" / "brand_chat.py"
MAIN_PY           = API / "app" / "main.py"
BRAND_CHAT_TS     = WEB / "lib" / "api" / "brand-chat.ts"
JUMBO_CHAT_TSX    = WEB / "components" / "jumbo-brand-chat.tsx"
INTEL_REPORT      = WEB / "components" / "brand-intelligence-report.tsx"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════════
# TestBrandChatService
# ═══════════════════════════════════════════════════════════════════════════


class TestBrandChatService:
    """apps/api/app/services/brand_chat.py exists with correct structure."""

    def test_service_file_exists(self):
        assert BRAND_CHAT_SVC.exists(), (
            "apps/api/app/services/brand_chat.py missing — "
            "Jumbo Brand Chat service not created"
        )

    def test_send_chat_message_function(self):
        text = read(BRAND_CHAT_SVC)
        assert "async def send_chat_message" in text, (
            "send_chat_message() function missing from brand_chat.py — "
            "no way to call Jumbo with brand context"
        )

    def test_dossier_injected_into_system_prompt(self):
        text = read(BRAND_CHAT_SVC)
        assert "dossier_json" in text and "_JUMBO_CHAT_SYSTEM" in text, (
            "Dossier injection pattern missing — "
            "_JUMBO_CHAT_SYSTEM must contain {dossier_json} placeholder"
        )

    def test_trim_dossier_helper_exists(self):
        text = read(BRAND_CHAT_SVC)
        assert "_trim_dossier" in text, (
            "_trim_dossier() helper missing — "
            "dossier must be trimmed to keep system prompt under token limit"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TestBrandChatRouter
# ═══════════════════════════════════════════════════════════════════════════


class TestBrandChatRouter:
    """apps/api/app/routers/brand_chat.py and registration in main.py."""

    def test_router_file_exists(self):
        assert BRAND_CHAT_ROUTER.exists(), (
            "apps/api/app/routers/brand_chat.py missing — "
            "no endpoint for POST /brand-chat/{brand_id}"
        )

    def test_uuid_guard_in_router(self):
        text = read(BRAND_CHAT_ROUTER)
        assert "_UUID_RE" in text or "UUID_RE" in text or "uuid" in text.lower(), (
            "UUID validation missing from brand_chat router — "
            "brand_id injection vulnerability (A03)"
        )

    def test_router_registered_in_main(self):
        text = read(MAIN_PY)
        assert "brand_chat" in text, (
            "brand_chat router not imported/registered in main.py — "
            "endpoint will return 404"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TestFrontendBrandChat
# ═══════════════════════════════════════════════════════════════════════════


class TestFrontendBrandChat:
    """Frontend: brand-chat.ts API client + jumbo-brand-chat.tsx component."""

    def test_api_client_exists(self):
        assert BRAND_CHAT_TS.exists(), (
            "apps/web/src/lib/api/brand-chat.ts missing — "
            "frontend has no API client for Jumbo Brand Chat"
        )

    def test_component_exists(self):
        assert JUMBO_CHAT_TSX.exists(), (
            "apps/web/src/components/jumbo-brand-chat.tsx missing — "
            "chat UI not created"
        )

    def test_quick_actions_defined(self):
        text = read(BRAND_CHAT_TS)
        assert "QUICK_ACTIONS" in text and "hooks" in text and "nurture" in text, (
            "QUICK_ACTIONS array missing from brand-chat.ts — "
            "quick action buttons won't have prompts"
        )

    def test_chat_panel_in_intel_report(self):
        text = read(INTEL_REPORT)
        assert "JumboBrandChat" in text, (
            "JumboBrandChat not added to brand-intelligence-report.tsx — "
            "chat panel not visible in Brand Intelligence Report"
        )
