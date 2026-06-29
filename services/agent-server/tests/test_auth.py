# tests/test_auth.py
from __future__ import annotations

import hashlib
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from agent_server.auth import TokenAuth


class TestTokenAuth:
    @pytest.mark.asyncio
    async def test_no_hash_configured_skips_check(self) -> None:
        """未配置 token_hash 时跳过认证"""
        auth = TokenAuth('')
        request = AsyncMock()
        request.headers = {}
        await auth(request)

    @pytest.mark.asyncio
    async def test_missing_header_returns_401(self) -> None:
        """缺少 Authorization 头返回 401"""
        auth = TokenAuth('abc123')
        request = AsyncMock()
        request.headers = {}

        with pytest.raises(HTTPException) as exc:
            await auth(request)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_wrong_scheme_returns_401(self) -> None:
        """非 Bearer scheme 返回 401"""
        auth = TokenAuth('abc123')
        request = AsyncMock()
        request.headers = {'Authorization': 'Basic xyz'}

        with pytest.raises(HTTPException) as exc:
            await auth(request)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_wrong_token_returns_401(self) -> None:
        """错误 token 返回 401"""
        auth = TokenAuth('abc123')
        request = AsyncMock()
        request.headers = {'Authorization': 'Bearer wrong-token'}

        with pytest.raises(HTTPException) as exc:
            await auth(request)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_correct_token_passes(self) -> None:
        """正确 token 通过认证"""
        token = 'my-secret-token'
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        auth = TokenAuth(token_hash)
        request = AsyncMock()
        request.headers = {'Authorization': f'Bearer {token}'}

        await auth(request)


class TestHealthEndpoint:
    def test_health_returns_ok(self) -> None:
        from agent_server.main import app

        client = TestClient(app)
        response = client.get('/health')
        assert response.status_code == 200
        assert response.json() == {'status': 'ok'}
