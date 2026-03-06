"""
Slice 107: Full UX Overhaul — Jumbo Hub + Agents Page + Getting Started + Orphan Archive

15 tests across 5 classes:
  TestJumboHubService        (3): service exists, required functions, system prompt
  TestJumboHubRouter         (4): router exists, endpoints registered, main.py wired, Pydantic schemas
  TestJumboHubFrontend       (3): API client, hook, page components
  TestAgentsPageExtraction   (2): agents page exists, constants moved
  TestOrphanArchive          (3): _archived folder exists, tsconfig excludes it, nav updated
"""

from pathlib import Path

REPO = Path(__file__).parents[3]
API  = REPO / "apps" / "api"
WEB  = REPO / "apps" / "web" / "src"

JUMBO_HUB_SVC    = API / "app" / "services" / "jumbo_hub.py"
JUMBO_HUB_ROUTER = API / "app" / "routers" / "jumbo_hub.py"
MAIN_PY          = API / "app" / "main.py"
MIGRATION_SQL    = REPO / "infra" / "supabase" / "migrations" / "042_jumbo_conversations.sql"

JUMBO_HUB_TS       = WEB / "lib" / "api" / "jumbo-hub.ts"
JUMBO_HUB_HOOK     = WEB / "components" / "jumbo-hub" / "use-jumbo-chat.ts"
JUMBO_HUB_SIDEBAR  = WEB / "components" / "jumbo-hub" / "conversation-sidebar.tsx"
JUMBO_HUB_CHAT     = WEB / "components" / "jumbo-hub" / "chat-area.tsx"
JUMBO_HUB_SAVE     = WEB / "components" / "jumbo-hub" / "save-as-note-form.tsx"
JUMBO_HUB_INDEX    = WEB / "components" / "jumbo-hub" / "index.ts"
INTELLIGENCE_PAGE  = WEB / "app" / "intelligence" / "page.tsx"

AGENTS_PAGE = WEB / "app" / "studio" / "agents" / "page.tsx"
GETTING_STARTED = WEB / "components" / "getting-started-checklist.tsx"
NAV_BAR = WEB / "app" / "nav-bar.tsx"
TSCONFIG = REPO / "apps" / "web" / "tsconfig.json"
ARCHIVED_DIR = WEB / "app" / "_archived"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════════
# TestJumboHubService
# ═══════════════════════════════════════════════════════════════════════════


class TestJumboHubService:
    """apps/api/app/services/jumbo_hub.py — chat service with IDOR + caps."""

    def test_service_file_exists(self):
        assert JUMBO_HUB_SVC.exists(), "jumbo_hub.py service not created"

    def test_required_functions(self):
        text = read(JUMBO_HUB_SVC)
        for fn in [
            "create_conversation",
            "chat",
            "list_conversations",
            "get_conversation",
            "archive_conversation",
            "save_as_note",
        ]:
            assert f"def {fn}" in text, f"Function {fn!r} missing from jumbo_hub.py"

    def test_system_prompt_has_brand_context(self):
        text = read(JUMBO_HUB_SVC)
        assert "get_brand_context" in text, (
            "jumbo_hub.py should inject brand context via get_brand_context()"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TestJumboHubRouter
# ═══════════════════════════════════════════════════════════════════════════


class TestJumboHubRouter:
    """apps/api/app/routers/jumbo_hub.py — 6 JWT-protected endpoints."""

    def test_router_file_exists(self):
        assert JUMBO_HUB_ROUTER.exists(), "jumbo_hub.py router not created"

    def test_all_endpoints_registered(self):
        text = read(JUMBO_HUB_ROUTER)
        for endpoint in [
            "/hub/conversations",        # POST create + GET list
            "/hub/conversations/{",      # GET one + POST chat + PATCH archive
            "/hub/save-note",            # POST save-as-note
        ]:
            assert endpoint in text, (
                f"Endpoint pattern {endpoint!r} missing from jumbo_hub.py router"
            )

    def test_router_registered_in_main(self):
        text = read(MAIN_PY)
        assert "jumbo_hub" in text, (
            "jumbo_hub router not imported/registered in main.py"
        )

    def test_pydantic_schemas_defined(self):
        text = read(JUMBO_HUB_ROUTER)
        for schema in [
            "CreateConversationRequest",
            "ChatRequest",
            "SaveNoteRequest",
        ]:
            assert schema in text, (
                f"Pydantic schema {schema!r} missing from jumbo_hub.py router"
            )


# ═══════════════════════════════════════════════════════════════════════════
# TestJumboHubFrontend
# ═══════════════════════════════════════════════════════════════════════════


class TestJumboHubFrontend:
    """Frontend: API client, custom hook, page components."""

    def test_api_client_exists(self):
        assert JUMBO_HUB_TS.exists(), "jumbo-hub.ts API client missing"
        text = read(JUMBO_HUB_TS)
        assert "jumboHubApi" in text, "jumboHubApi object not exported"

    def test_custom_hook_exists(self):
        assert JUMBO_HUB_HOOK.exists(), "use-jumbo-chat.ts hook missing"
        text = read(JUMBO_HUB_HOOK)
        assert "useJumboChat" in text, "useJumboChat function not exported"

    def test_page_components_exist(self):
        for path in [JUMBO_HUB_SIDEBAR, JUMBO_HUB_CHAT, JUMBO_HUB_SAVE, JUMBO_HUB_INDEX]:
            assert path.exists(), f"{path.name} missing from jumbo-hub/ components"
        # Intelligence page should be the Jumbo Hub shell now
        text = read(INTELLIGENCE_PAGE)
        assert "JumboHub" in text or "jumbo-hub" in text.lower() or "useJumboChat" in text, (
            "intelligence/page.tsx should delegate to Jumbo Hub components"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TestAgentsPageExtraction
# ═══════════════════════════════════════════════════════════════════════════


class TestAgentsPageExtraction:
    """Agents tab extracted to /studio/agents/page.tsx."""

    def test_agents_page_exists(self):
        assert AGENTS_PAGE.exists(), (
            "studio/agents/page.tsx not created — AgentsTab not extracted"
        )

    def test_agents_page_has_constants(self):
        text = read(AGENTS_PAGE)
        assert "AGENT_EMOJIS" in text, "AGENT_EMOJIS missing from agents page"
        assert "AGENT_DESCRIPTIONS" in text, "AGENT_DESCRIPTIONS missing from agents page"
        assert "DEFAULT_AGENTS" in text, "DEFAULT_AGENTS missing from agents page"


# ═══════════════════════════════════════════════════════════════════════════
# TestOrphanArchive
# ═══════════════════════════════════════════════════════════════════════════


class TestOrphanArchive:
    """11 orphan pages archived to _archived/, tsconfig excludes them."""

    def test_archived_directory_exists(self):
        assert ARCHIVED_DIR.exists(), "_archived/ directory not created"
        # Check a sample of archived folders
        for name in ["brand", "content", "schedule", "performance"]:
            assert (ARCHIVED_DIR / name).exists(), (
                f"_archived/{name} not found — orphan page not archived"
            )

    def test_tsconfig_excludes_archived(self):
        text = read(TSCONFIG)
        assert "_archived" in text, (
            "tsconfig.json should exclude _archived directory"
        )

    def test_nav_updated_studio_to_jumbo(self):
        text = read(NAV_BAR)
        # Slice 108 redesign: Jumbo is now a special accent link (not a PRIMARY_NAV item)
        assert "Jumbo" in text, "Nav should reference Jumbo somewhere"
        assert "/jumbo" in text, "Nav should link to /jumbo"
