import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from supabase_auth.errors import AuthApiError

from app.auth.dependencies import get_current_user


def _fake_client(get_user_result=None, get_user_error: Exception | None = None) -> SimpleNamespace:
    get_user = AsyncMock(side_effect=get_user_error) if get_user_error else AsyncMock(return_value=get_user_result)
    return SimpleNamespace(auth=SimpleNamespace(get_user=get_user), postgrest=SimpleNamespace(auth=lambda *_: None))


async def test_missing_credentials_raises_401():
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=None)

    assert exc_info.value.status_code == 401


async def test_invalid_token_raises_401(monkeypatch):
    error = AuthApiError("invalid claim: missing sub claim", 401, None)
    client = _fake_client(get_user_error=error)
    monkeypatch.setattr("app.auth.dependencies.get_async_user_client", AsyncMock(return_value=client))

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad-token")
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=credentials)

    assert exc_info.value.status_code == 401


async def test_no_user_on_response_raises_401(monkeypatch):
    client = _fake_client(get_user_result=None)
    monkeypatch.setattr("app.auth.dependencies.get_async_user_client", AsyncMock(return_value=client))

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="expired-token")
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=credentials)

    assert exc_info.value.status_code == 401


async def test_valid_token_returns_current_user(monkeypatch):
    user_id = uuid.uuid4()
    response = SimpleNamespace(user=SimpleNamespace(id=str(user_id), email="analyst@driftwood.example"))
    client = _fake_client(get_user_result=response)
    monkeypatch.setattr("app.auth.dependencies.get_async_user_client", AsyncMock(return_value=client))

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="good-token")
    current_user = await get_current_user(credentials=credentials)

    assert current_user.id == user_id
    assert current_user.email == "analyst@driftwood.example"
    assert current_user.access_token == "good-token"
    assert current_user.client is client
