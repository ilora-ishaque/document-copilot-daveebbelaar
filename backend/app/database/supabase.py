from functools import lru_cache

from supabase import AsyncClient, Client, create_async_client, create_client

from app.config import settings


@lru_cache
def get_service_client() -> Client:
    """Admin client using the service-role key. Bypasses RLS — use only for
    privileged writes that are explicitly tied to an authenticated user."""
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def get_user_client(access_token: str) -> Client:
    """Anon-key client scoped to one user's request. PostgREST enforces RLS
    as that user, so prefer this over the service client wherever possible."""
    client = create_client(settings.supabase_url, settings.supabase_anon_key)
    client.postgrest.auth(access_token)
    return client


async def get_async_user_client(access_token: str) -> AsyncClient:
    """Async counterpart to `get_user_client`, for use in request-path code
    (e.g. the `get_current_user` FastAPI dependency and async route handlers)
    so token verification and RLS-scoped queries don't block the event loop."""
    client = await create_async_client(settings.supabase_url, settings.supabase_anon_key)
    client.postgrest.auth(access_token)
    return client
