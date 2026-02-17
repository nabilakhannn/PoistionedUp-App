"""Dependency injection: Supabase clients and auth."""

from supabase import create_client, Client

from app.config import settings


def get_admin_client() -> Client:
    """Service-role client. Bypasses RLS. Use for backend-only operations."""
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
