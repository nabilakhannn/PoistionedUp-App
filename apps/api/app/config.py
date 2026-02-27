from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings

# .env lives at project root (two levels up from apps/api/)
# In containers this path may not exist, which is fine: pydantic-settings
# falls back to real environment variables set by the hosting platform.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    # Supabase
    supabase_url: str = "http://127.0.0.1:54321"
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_db_url: str = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"

    # API
    port: int = 8000  # Railway/Render inject PORT automatically
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "https://positionedup.com",
        "https://www.positionedup.com",
        "https://positionedup.vercel.app",
        "https://poistioned-up-app.vercel.app",
        "https://poistioned-up-app-git-main-nabilas-projects-db41bc0c.vercel.app",
        "https://web-tau-dun-23.vercel.app",
        "https://web-nabilas-projects-db41bc0c.vercel.app",
    ]

    # LLM
    openai_api_key: str = ""
    anthropic_api_key: str = ""  # Optional: enables Claude models for Standard/Premium tiers

    # Real-time research
    tavily_api_key: str = ""  # Optional: better search quality. Free tier: 1000 searches/month

    # LangGraph
    langgraph_db_uri: str = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"

    # Cost governance
    max_tokens_per_step: int = 32000
    max_tokens_per_workflow: int = 200000
    max_workflows_per_user_per_day: int = 10
    max_tokens_per_user_per_day: int = 500000  # ~$5 daily ceiling at GPT-4o rates

    # Agent Bridge (OpenClaw agents calling into PositionedUp)
    agent_api_key: str = ""  # Set a strong random key for agent-to-API auth

    # OpenClaw Gateway (PositionedUp calling into agent runtime)
    openclaw_gateway_url: str = ""  # e.g. http://localhost:18789 or https://agents.positionedup.com
    openclaw_gateway_token: str = ""  # Must match OPENCLAW_GATEWAY_TOKEN on VPS
    openclaw_mock_mode: bool = False  # Set to true for local dev without VPS

    # PostHog analytics
    posthog_api_key: str = ""  # Server-side PostHog project API key
    posthog_host: str = "https://us.i.posthog.com"

    # Observability
    log_level: str = "INFO"  # DEBUG for local, INFO for production

    # OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    notion_client_id: str = ""
    notion_client_secret: str = ""
    notion_redirect_uri: str = "http://localhost:8000/oauth/notion/callback"

    model_config = {
        "env_file": str(_ENV_FILE),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
