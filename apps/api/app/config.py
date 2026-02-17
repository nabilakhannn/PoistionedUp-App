from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings

# .env lives at project root (two levels up from apps/api/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    # Supabase
    supabase_url: str = "http://127.0.0.1:54321"
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_db_url: str = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"

    # API
    api_port: int = 8000
    cors_origins: List[str] = ["http://localhost:3000"]

    # LLM
    openai_api_key: str = ""

    # Real-time research
    tavily_api_key: str = ""  # Optional: better search quality. Free tier: 1000 searches/month

    # LangGraph
    langgraph_db_uri: str = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"

    # Agent Zero
    agent_zero_enabled: bool = False
    agent_zero_docker_image: str = "agent0ai/agent-zero:latest"
    agent_zero_timeout_seconds: int = 120

    # Cost governance
    max_tokens_per_step: int = 32000
    max_tokens_per_workflow: int = 200000
    max_workflows_per_user_per_day: int = 10

    # Observability
    log_level: str = "DEBUG"

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
