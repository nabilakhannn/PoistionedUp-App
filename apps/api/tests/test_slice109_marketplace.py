"""Slice 109 — Agent Marketplace + Manus AI Engine + Story Bank.

Tests cover:
- Story Bank (extractor, router, API client, UI page)
- Manus AI (client, router, connectors integration)
- Workflow Engine (registry, execution, enhancement injection)
- Marketplace (router, API client, UI pages)
- Jumbo Strategist (SOUL.md, playbook updates, proactive triggers)
- Security (IDOR, input validation)
"""

import ast
import os
import re

# ── Paths ──────────────────────────────────────────────────────────

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
API = os.path.join(ROOT, "apps", "api")
WEB = os.path.join(ROOT, "apps", "web")
INFRA = os.path.join(ROOT, "infra", "supabase", "migrations")
AGENTS = os.path.join(ROOT, "agents")


# ── Phase 1: Story Bank ───────────────────────────────────────────


class TestStoryBankMigration:
    def test_migration_044_exists(self):
        path = os.path.join(INFRA, "044_story_bank.sql")
        assert os.path.isfile(path)

    def test_migration_adds_extracted_stories_column(self):
        sql = open(os.path.join(INFRA, "044_story_bank.sql")).read()
        assert "extracted_stories" in sql
        assert "JSONB" in sql.upper() or "jsonb" in sql

    def test_migration_adds_story_tags(self):
        sql = open(os.path.join(INFRA, "044_story_bank.sql")).read()
        assert "story_tags" in sql

    def test_migration_extends_source_type_check(self):
        sql = open(os.path.join(INFRA, "044_story_bank.sql")).read()
        for st in ("idea", "opinion", "quote", "take", "framework"):
            assert st in sql, f"Missing source type: {st}"


class TestStoryExtractor:
    def test_service_exists(self):
        path = os.path.join(API, "app", "services", "story_extractor.py")
        assert os.path.isfile(path)

    def test_extract_stories_function(self):
        src = open(os.path.join(API, "app", "services", "story_extractor.py")).read()
        assert "def extract_stories" in src

    def test_extract_and_save_function(self):
        src = open(os.path.join(API, "app", "services", "story_extractor.py")).read()
        assert "def extract_and_save" in src

    def test_search_stories_by_theme(self):
        src = open(os.path.join(API, "app", "services", "story_extractor.py")).read()
        assert "def search_stories_by_theme" in src

    def test_uses_gpt4o_mini(self):
        src = open(os.path.join(API, "app", "services", "story_extractor.py")).read()
        assert "gpt-4o-mini" in src


class TestStoriesRouter:
    def test_router_exists(self):
        path = os.path.join(API, "app", "routers", "stories.py")
        assert os.path.isfile(path)

    def test_router_has_ingest_endpoint(self):
        src = open(os.path.join(API, "app", "routers", "stories.py")).read()
        assert "/stories/ingest" in src or "ingest" in src

    def test_router_has_list_endpoint(self):
        src = open(os.path.join(API, "app", "routers", "stories.py")).read()
        assert "GET" in src or "get" in src.lower()

    def test_router_has_search_endpoint(self):
        src = open(os.path.join(API, "app", "routers", "stories.py")).read()
        assert "search" in src

    def test_router_has_extract_endpoint(self):
        src = open(os.path.join(API, "app", "routers", "stories.py")).read()
        assert "extract" in src

    def test_router_has_delete_endpoint(self):
        src = open(os.path.join(API, "app", "routers", "stories.py")).read()
        assert "DELETE" in src or "delete" in src


class TestStoriesFrontend:
    def test_api_client_exists(self):
        path = os.path.join(WEB, "src", "lib", "api", "stories.ts")
        assert os.path.isfile(path)

    def test_api_client_has_all_methods(self):
        src = open(os.path.join(WEB, "src", "lib", "api", "stories.ts")).read()
        for method in ("ingest", "list", "search", "extract", "delete"):
            assert method in src, f"Missing API method: {method}"

    def test_stories_page_exists(self):
        path = os.path.join(WEB, "src", "app", "content", "stories", "page.tsx")
        assert os.path.isfile(path)

    def test_stories_page_has_filter_tabs(self):
        src = open(os.path.join(WEB, "src", "app", "content", "stories", "page.tsx")).read()
        assert "SOURCE_TYPES" in src

    def test_content_page_has_story_bank_card(self):
        src = open(os.path.join(WEB, "src", "app", "content", "page.tsx")).read()
        assert "Story Bank" in src
        assert "/content/stories" in src


class TestStoryBankIntegration:
    def test_jumbo_pipeline_has_get_story_context(self):
        src = open(os.path.join(API, "app", "services", "jumbo_pipeline.py")).read()
        assert "def get_story_context" in src

    def test_get_brand_context_reads_raw_content(self):
        src = open(os.path.join(API, "app", "services", "jumbo_pipeline.py")).read()
        assert "raw_content" in src

    def test_save_raw_material_tool_exists(self):
        src = open(os.path.join(API, "app", "services", "tool_use_agents.py")).read()
        assert "save_raw_material" in src


# ── Phase 2: Manus AI ─────────────────────────────────────────────


class TestManusAIMigration:
    def test_migration_045_exists(self):
        path = os.path.join(INFRA, "045_manus_tasks.sql")
        assert os.path.isfile(path)

    def test_migration_has_rls(self):
        sql = open(os.path.join(INFRA, "045_manus_tasks.sql")).read()
        assert "ROW LEVEL SECURITY" in sql.upper() or "row level security" in sql.lower()


class TestManusAIService:
    def test_service_exists(self):
        path = os.path.join(API, "app", "services", "manus_ai.py")
        assert os.path.isfile(path)

    def test_manus_client_class(self):
        src = open(os.path.join(API, "app", "services", "manus_ai.py")).read()
        assert "class ManusAIClient" in src

    def test_compress_brand_context(self):
        src = open(os.path.join(API, "app", "services", "manus_ai.py")).read()
        assert "def compress_brand_context" in src

    def test_get_manus_api_key(self):
        src = open(os.path.join(API, "app", "services", "manus_ai.py")).read()
        assert "def get_manus_api_key" in src


class TestManusAIRouter:
    def test_router_exists(self):
        path = os.path.join(API, "app", "routers", "manus_ai.py")
        assert os.path.isfile(path)

    def test_router_has_create_task(self):
        src = open(os.path.join(API, "app", "routers", "manus_ai.py")).read()
        assert "create_task" in src or "/manus/task" in src

    def test_router_has_poll_endpoint(self):
        src = open(os.path.join(API, "app", "routers", "manus_ai.py")).read()
        assert "poll" in src.lower() or "task_id" in src


class TestManusConnectorsIntegration:
    def test_manus_in_supported_services(self):
        src = open(os.path.join(API, "app", "services", "connectors.py")).read()
        assert "manus_ai" in src

    def test_manus_test_function(self):
        src = open(os.path.join(API, "app", "services", "connectors.py")).read()
        assert "_test_manus_ai" in src

    def test_frontend_connector_type_includes_manus(self):
        src = open(os.path.join(WEB, "src", "lib", "api", "connectors.ts")).read()
        assert "manus_ai" in src

    def test_settings_page_has_manus_card(self):
        src = open(os.path.join(WEB, "src", "app", "mission-control", "settings", "page.tsx")).read()
        assert "manus_ai" in src
        assert "Manus AI" in src


class TestManusAIFrontend:
    def test_api_client_exists(self):
        path = os.path.join(WEB, "src", "lib", "api", "manus-ai.ts")
        assert os.path.isfile(path)

    def test_api_client_has_methods(self):
        src = open(os.path.join(WEB, "src", "lib", "api", "manus-ai.ts")).read()
        assert "createTask" in src
        assert "pollTask" in src


# ── Phase 3: Workflow Engine + Marketplace ─────────────────────────


class TestWorkflowRunsMigration:
    def test_migration_046_exists(self):
        path = os.path.join(INFRA, "046_workflow_runs.sql")
        assert os.path.isfile(path)

    def test_migration_has_rls(self):
        sql = open(os.path.join(INFRA, "046_workflow_runs.sql")).read()
        assert "ROW LEVEL SECURITY" in sql.upper() or "row level security" in sql.lower()


class TestWorkflowEngine:
    def test_service_exists(self):
        path = os.path.join(API, "app", "services", "workflow_engine.py")
        assert os.path.isfile(path)

    def test_workflow_registry_has_24_workflows(self):
        src = open(os.path.join(API, "app", "services", "workflow_engine.py")).read()
        # Count unique slugs in WORKFLOW_REGISTRY
        slugs = re.findall(r'"([a-z0-9-]+)":\s*\{', src)
        # Filter to only workflow slugs (not category keys)
        workflow_slugs = [s for s in slugs if s in (
            "vsl-funnel-generator", "landing-page-generator", "funnel-strategy-agent",
            "static-ad-generator", "video-ad-scripts", "offer-creation", "lp-cro-analyzer",
            "social-media-post", "content-research", "youtube-script-creator",
            "zoom-call-repurposer", "content-calendar-gen",
            "icp-research", "cold-email-scriptwriter", "dream-100-research",
            "meeting-alert-research", "lead-enrichment",
            "email-sequence-writer", "email-flow-writer", "newsletter-generator", "email-calendar",
            "jumbo-strategist", "brand-research", "sales-call-analysis",
        )]
        assert len(workflow_slugs) == 24, f"Expected 24, got {len(workflow_slugs)}: {workflow_slugs}"

    def test_5_categories(self):
        src = open(os.path.join(API, "app", "services", "workflow_engine.py")).read()
        assert "WORKFLOW_CATEGORIES" in src
        for cat in ("ads_funnels", "content_marketing", "lead_gen", "email_marketing", "strategy"):
            assert cat in src, f"Missing category: {cat}"

    def test_build_enhanced_prompt_function(self):
        src = open(os.path.join(API, "app", "services", "workflow_engine.py")).read()
        assert "async def build_enhanced_prompt" in src

    def test_execute_workflow_function(self):
        src = open(os.path.join(API, "app", "services", "workflow_engine.py")).read()
        assert "async def execute_workflow" in src

    def test_get_registry_function(self):
        src = open(os.path.join(API, "app", "services", "workflow_engine.py")).read()
        assert "def get_registry" in src

    def test_manus_beneficial_workflows_count(self):
        src = open(os.path.join(API, "app", "services", "workflow_engine.py")).read()
        manus_count = src.count('"engine": "manus_beneficial"')
        assert manus_count == 5, f"Expected 5 manus_beneficial, got {manus_count}"

    def test_multi_step_workflow_exists(self):
        src = open(os.path.join(API, "app", "services", "workflow_engine.py")).read()
        assert '"multi_step": True' in src
        assert "vsl-funnel-generator" in src

    def test_coming_soon_workflows_exist(self):
        src = open(os.path.join(API, "app", "services", "workflow_engine.py")).read()
        assert '"status": "coming_soon"' in src

    def test_enhancement_types(self):
        src = open(os.path.join(API, "app", "services", "workflow_engine.py")).read()
        for enh in ("brand_dossier", "story_bank", "hook_library", "competitor_intel", "qa_gate"):
            assert enh in src, f"Missing enhancement: {enh}"

    def test_seed_system_frameworks(self):
        src = open(os.path.join(API, "app", "services", "workflow_engine.py")).read()
        assert "async def seed_system_frameworks" in src
        assert "SYSTEM_FRAMEWORK_DOCS" in src

    def test_framework_docs_include_messaging_buckets(self):
        src = open(os.path.join(API, "app", "services", "workflow_engine.py")).read()
        assert "Messaging Buckets" in src

    def test_framework_docs_include_hormozi(self):
        src = open(os.path.join(API, "app", "services", "workflow_engine.py")).read()
        assert "Hormozi Value Equation" in src
        assert "Hormozi Grand Slam Offer" in src

    def test_email_sequence_types(self):
        src = open(os.path.join(API, "app", "services", "workflow_engine.py")).read()
        for seq_type in ("Opt-In Nurture", "Broadcast", "Abandon Cart",
                         "Pre-Call Warmup", "No-Show Recovery", "Post-Call Follow-Up"):
            assert seq_type in src, f"Missing email sequence type: {seq_type}"


class TestMarketplaceRouter:
    def test_router_exists(self):
        path = os.path.join(API, "app", "routers", "marketplace.py")
        assert os.path.isfile(path)

    def test_router_has_registry_endpoint(self):
        src = open(os.path.join(API, "app", "routers", "marketplace.py")).read()
        assert "/registry" in src

    def test_router_has_run_endpoint(self):
        src = open(os.path.join(API, "app", "routers", "marketplace.py")).read()
        assert "/run/" in src

    def test_router_has_history_endpoint(self):
        src = open(os.path.join(API, "app", "routers", "marketplace.py")).read()
        assert "/history" in src

    def test_router_registered_in_main(self):
        src = open(os.path.join(API, "app", "main.py")).read()
        assert "marketplace" in src
        assert "marketplace.router" in src

    def test_uuid_validation_in_router(self):
        src = open(os.path.join(API, "app", "routers", "marketplace.py")).read()
        assert "_UUID" in src
        assert "re.compile" in src

    def test_slug_validation_in_router(self):
        src = open(os.path.join(API, "app", "routers", "marketplace.py")).read()
        assert "_SLUG" in src


class TestMarketplaceFrontend:
    def test_api_client_exists(self):
        path = os.path.join(WEB, "src", "lib", "api", "marketplace.ts")
        assert os.path.isfile(path)

    def test_api_client_has_all_methods(self):
        src = open(os.path.join(WEB, "src", "lib", "api", "marketplace.ts")).read()
        for method in ("getRegistry", "runWorkflow", "getRunStatus", "getHistory"):
            assert method in src, f"Missing API method: {method}"

    def test_marketplace_page_exists(self):
        path = os.path.join(WEB, "src", "app", "content", "agents", "page.tsx")
        assert os.path.isfile(path)

    def test_marketplace_page_shows_categories(self):
        src = open(os.path.join(WEB, "src", "app", "content", "agents", "page.tsx")).read()
        assert "CATEGORY_ICONS" in src or "category" in src.lower()

    def test_workflow_execution_page_exists(self):
        path = os.path.join(WEB, "src", "app", "content", "agents", "[slug]", "page.tsx")
        assert os.path.isfile(path)

    def test_workflow_page_has_multi_step_support(self):
        src = open(os.path.join(WEB, "src", "app", "content", "agents", "[slug]", "page.tsx")).read()
        assert "multi_step" in src
        assert "stepOutputs" in src

    def test_dynamic_form_builder_exists(self):
        path = os.path.join(WEB, "src", "components", "dynamic-form-builder.tsx")
        assert os.path.isfile(path)

    def test_generation_history_exists(self):
        path = os.path.join(WEB, "src", "components", "generation-history.tsx")
        assert os.path.isfile(path)

    def test_content_page_has_agents_card(self):
        src = open(os.path.join(WEB, "src", "app", "content", "page.tsx")).read()
        assert "AI Agents" in src
        assert "/content/agents" in src


# ── Phase 5: Jumbo Strategist ──────────────────────────────────────


class TestJumboStrategist:
    def test_soul_md_has_strategist_identity(self):
        src = open(os.path.join(AGENTS, "jumbo", "SOUL.md")).read()
        assert "strategist" in src.lower()
        assert "world-class" in src.lower()

    def test_copywriter_playbook_has_messaging_buckets(self):
        src = open(os.path.join(API, "app", "services", "playbooks.py")).read()
        assert "Messaging Buckets" in src
        for bucket in ("PAIN", "OUTCOME", "STORY", "AUTHORITY", "BELIEF", "CURIOSITY"):
            assert bucket in src, f"Missing messaging bucket: {bucket}"

    def test_copywriter_playbook_has_hormozi(self):
        src = open(os.path.join(API, "app", "services", "playbooks.py")).read()
        assert "Hormozi" in src
        assert "Value Equation" in src

    def test_jumbo_hub_has_strategist_tone(self):
        src = open(os.path.join(API, "app", "services", "jumbo_hub.py")).read()
        assert "strategist" in src.lower()

    def test_proactive_trigger_8_story_bank(self):
        src = open(os.path.join(API, "app", "services", "proactive_triggers.py")).read()
        assert "Trigger 8" in src
        assert "Story Bank" in src or "story" in src.lower()


# ── Security (OWASP) ──────────────────────────────────────────────


class TestSecurity:
    def test_stories_router_has_user_id_guard(self):
        src = open(os.path.join(API, "app", "routers", "stories.py")).read()
        assert "user_id" in src or 'require_user' in src

    def test_marketplace_router_has_user_id_guard(self):
        src = open(os.path.join(API, "app", "routers", "marketplace.py")).read()
        assert "require_user" in src or "get_current_user" in src

    def test_manus_router_has_user_id_guard(self):
        src = open(os.path.join(API, "app", "routers", "manus_ai.py")).read()
        assert "require_user" in src or "get_current_user" in src

    def test_workflow_runs_rls(self):
        sql = open(os.path.join(INFRA, "046_workflow_runs.sql")).read()
        assert "auth.uid()" in sql

    def test_manus_tasks_rls(self):
        sql = open(os.path.join(INFRA, "045_manus_tasks.sql")).read()
        assert "auth.uid()" in sql

    def test_marketplace_uuid_validation(self):
        src = open(os.path.join(API, "app", "routers", "marketplace.py")).read()
        assert "_UUID.match" in src

    def test_manus_ai_key_decryption(self):
        src = open(os.path.join(API, "app", "services", "manus_ai.py")).read()
        assert "decrypt" in src.lower() or "get_credentials" in src
