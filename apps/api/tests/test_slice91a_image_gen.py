"""
Slice 91a: Image Generation — Nano Banana 2 (Gemini 3.1 Flash Image via Higgsfield)

16 tests across 6 classes:
  TestMigration034          — 3  (file exists, generated_images table, RLS policy)
  TestConfig91a             — 2  (higgsfield_api_key, image_gen_model in config)
  TestImageGenService       — 4  (FORMAT_RATIOS, structure_prompt_only returns dict,
                                   all 9 keys present, fallback when no API key)
  TestImageGenRouter        — 3  (3 endpoints defined, JWT guard, UUID validation)
  TestToolDefinitions       — 2  (generate_image in TOOL_DEFINITIONS, correct schema)
  TestToolDispatch          — 2  (dispatcher handles generate_image, exec function exists)
"""

import json
import re
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO = Path(__file__).parents[3]
API = REPO / "apps" / "api"
WEB = REPO / "apps" / "web" / "src"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


MIGRATION = REPO / "infra" / "supabase" / "migrations" / "034_image_gen.sql"
IMAGE_GEN_SERVICE = API / "app" / "services" / "image_gen.py"
IMAGE_GEN_ROUTER = API / "app" / "routers" / "image_gen.py"
TOOL_AGENTS = API / "app" / "services" / "tool_use_agents.py"
CONFIG = API / "app" / "config.py"


# ═══════════════════════════════════════════════════════════════════════════
# TestMigration034
# ═══════════════════════════════════════════════════════════════════════════

class TestMigration034:
    """Migration 034 exists and contains the generated_images table + RLS."""

    def test_migration_file_exists(self):
        assert MIGRATION.exists(), "034_image_gen.sql not found"

    def test_migration_has_generated_images_table(self):
        sql = read(MIGRATION)
        assert "generated_images" in sql, "generated_images table missing from migration 034"
        assert "structured_prompt" in sql, "structured_prompt column missing"
        assert "image_url" in sql, "image_url column missing"

    def test_migration_has_rls_policy(self):
        sql = read(MIGRATION)
        assert "ROW LEVEL SECURITY" in sql or "ENABLE ROW LEVEL SECURITY" in sql, (
            "RLS must be enabled on generated_images"
        )
        assert "auth.uid()" in sql or "auth.uid" in sql, (
            "RLS policy must reference auth.uid()"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TestConfig91a
# ═══════════════════════════════════════════════════════════════════════════

class TestConfig91a:
    """New config fields are present in Settings class."""

    def test_higgsfield_api_key_in_config(self):
        text = read(CONFIG)
        assert "higgsfield_api_key" in text, (
            "higgsfield_api_key missing from config.py Settings"
        )

    def test_image_gen_model_in_config(self):
        text = read(CONFIG)
        assert "image_gen_model" in text, (
            "image_gen_model missing from config.py Settings"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TestImageGenService
# ═══════════════════════════════════════════════════════════════════════════

class TestImageGenService:
    """image_gen.py service has correct format ratios and prompt structure."""

    def test_format_ratios_has_all_four_formats(self):
        from app.services.image_gen import FORMAT_RATIOS
        for expected_key, expected_ratio in [
            ("square", "1:1"),
            ("landscape", "16:9"),
            ("portrait", "4:5"),
            ("story", "9:16"),
        ]:
            assert expected_key in FORMAT_RATIOS, (
                f"FORMAT_RATIOS missing '{expected_key}'"
            )
            assert FORMAT_RATIOS[expected_key] == expected_ratio, (
                f"FORMAT_RATIOS['{expected_key}'] should be '{expected_ratio}'"
            )

    def test_structure_prompt_only_returns_dict(self):
        """structure_prompt_only returns a dict even with no API key configured."""
        from app.services.image_gen import structure_prompt_only
        with patch("app.config.settings") as mock_settings:
            mock_settings.anthropic_api_key = ""  # No key — tests fallback path
            result = structure_prompt_only("A confident founder at her desk")
        assert isinstance(result, dict), "structure_prompt_only must return dict"

    def test_structure_prompt_returns_all_required_keys(self):
        """Fallback result has all 9 required keys."""
        from app.services.image_gen import structure_prompt_only
        with patch("app.config.settings") as mock_settings:
            mock_settings.anthropic_api_key = ""
            result = structure_prompt_only("test description")
        for key in ["subject", "composition", "camera", "lighting",
                    "color_palette", "mood", "style", "negative_prompt", "final_prompt"]:
            assert key in result, f"Key '{key}' missing from structure_prompt_only result"

    def test_generate_image_returns_dict_with_required_keys(self):
        """generate_image returns {url, structured_prompt, model_used, error}."""
        from app.services.image_gen import generate_image
        with patch("app.config.settings") as mock_settings:
            mock_settings.anthropic_api_key = ""
            mock_settings.higgsfield_api_key = ""
            mock_settings.gemini_api_key = ""
            mock_settings.image_gen_model = "gemini-test"
            result = generate_image("A person smiling")
        assert isinstance(result, dict)
        for key in ["url", "structured_prompt", "model_used", "error"]:
            assert key in result, f"Key '{key}' missing from generate_image result"


# ═══════════════════════════════════════════════════════════════════════════
# TestImageGenRouter
# ═══════════════════════════════════════════════════════════════════════════

class TestImageGenRouter:
    """image_gen.py router has all 3 endpoints with proper auth."""

    def _router(self) -> str:
        assert IMAGE_GEN_ROUTER.exists(), "apps/api/app/routers/image_gen.py not found"
        return read(IMAGE_GEN_ROUTER)

    def test_generate_endpoint_exists(self):
        text = self._router()
        assert "/image-gen/generate" in text, (
            "POST /image-gen/generate endpoint missing from router"
        )

    def test_structure_endpoint_exists(self):
        text = self._router()
        assert "/image-gen/structure" in text, (
            "POST /image-gen/structure endpoint missing from router"
        )

    def test_history_endpoint_exists(self):
        text = self._router()
        assert "/image-gen/history" in text, (
            "GET /image-gen/history endpoint missing from router"
        )

    def test_jwt_auth_used(self):
        text = self._router()
        assert "get_current_user" in text, (
            "Endpoints must use get_current_user JWT auth"
        )

    def test_uuid_validation_present(self):
        text = self._router()
        assert "_UUID_RE" in text, (
            "UUID regex validation missing from image_gen router (OWASP A03)"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TestToolDefinitions
# ═══════════════════════════════════════════════════════════════════════════

class TestToolDefinitions:
    """generate_image is registered in TOOL_DEFINITIONS with correct schema."""

    def test_generate_image_in_tool_definitions(self):
        from app.services.tool_use_agents import TOOL_DEFINITIONS
        tool_names = [t["name"] for t in TOOL_DEFINITIONS]
        assert "generate_image" in tool_names, (
            "generate_image not found in TOOL_DEFINITIONS"
        )

    def test_generate_image_has_required_schema(self):
        from app.services.tool_use_agents import TOOL_DEFINITIONS
        tool = next((t for t in TOOL_DEFINITIONS if t["name"] == "generate_image"), None)
        assert tool is not None
        props = tool["input_schema"]["properties"]
        assert "description" in props, "generate_image tool missing 'description' property"
        assert "style" in props, "generate_image tool missing 'style' property"
        assert "format" in props, "generate_image tool missing 'format' property"
        # description is required
        assert "description" in tool["input_schema"]["required"], (
            "'description' must be required in generate_image tool schema"
        )

    def test_generate_image_style_has_enum(self):
        from app.services.tool_use_agents import TOOL_DEFINITIONS
        tool = next((t for t in TOOL_DEFINITIONS if t["name"] == "generate_image"), None)
        props = tool["input_schema"]["properties"]
        assert "enum" in props["style"], "style property should have enum constraint"
        assert "photorealistic" in props["style"]["enum"]
        assert "cinematic" in props["style"]["enum"]


# ═══════════════════════════════════════════════════════════════════════════
# TestToolDispatch
# ═══════════════════════════════════════════════════════════════════════════

class TestToolDispatch:
    """_dispatch_tool correctly routes generate_image calls."""

    def test_dispatch_handles_generate_image_tool(self):
        text = read(TOOL_AGENTS)
        assert "generate_image" in text and "_exec_generate_image" in text, (
            "_dispatch_tool must handle 'generate_image' tool name via _exec_generate_image"
        )

    def test_exec_generate_image_returns_json_string(self):
        """_exec_generate_image returns a valid JSON string with url key."""
        from app.services.tool_use_agents import _exec_generate_image
        with patch("app.services.image_gen.generate_image") as mock_gen:
            mock_gen.return_value = {
                "url": "https://example.com/image.png",
                "structured_prompt": '{"final_prompt": "test"}',
                "model_used": "test-model",
                "error": None,
            }
            result = _exec_generate_image("A test image")
        parsed = json.loads(result)
        assert "url" in parsed, "_exec_generate_image must return JSON with 'url' key"

    def test_router_registered_in_main(self):
        main_text = read(API / "app" / "main.py")
        assert "image_gen" in main_text, "image_gen router not imported/registered in main.py"
        assert "image_gen.router" in main_text, "image_gen.router not added to app"
