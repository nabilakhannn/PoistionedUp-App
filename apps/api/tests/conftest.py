"""Shared test fixtures. Loads .env from project root."""

import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Load .env from project root (3 levels up from tests/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Add apps/api to path so imports work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(scope="session")
def supabase_url() -> str:
    url = os.environ.get("SUPABASE_URL", "")
    assert url, "SUPABASE_URL not set in .env"
    return url


@pytest.fixture(scope="session")
def supabase_anon_key() -> str:
    key = os.environ.get("SUPABASE_ANON_KEY", "")
    assert key, "SUPABASE_ANON_KEY not set in .env"
    return key


@pytest.fixture(scope="session")
def supabase_service_key() -> str:
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    assert key, "SUPABASE_SERVICE_ROLE_KEY not set in .env"
    return key
