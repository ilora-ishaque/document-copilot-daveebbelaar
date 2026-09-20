import uuid
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import AsyncClient
from supabase_auth.errors import AuthApiError

from app.database.supabase import get_async_user_client

_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    """The authenticated Supabase user for one request, plus a client already
    scoped to their access token for RLS-enforced queries."""

    id: uuid.UUID
    email: str
    access_token: str
    client: AsyncClient


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> CurrentUser:
    """Verify the `Authorization: Bearer <supabase_jwt>` header against
    Supabase Auth. Raises 401 on any missing, malformed, or expired token."""
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")

    token = credentials.credentials
    client = await get_async_user_client(token)

    try:
        response = await client.auth.get_user(token)
    except AuthApiError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token") from exc

    if response is None or response.user.email is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")

    return CurrentUser(
        id=uuid.UUID(response.user.id),
        email=response.user.email,
        access_token=token,
        client=client,
    )
