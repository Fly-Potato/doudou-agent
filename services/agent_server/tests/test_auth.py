from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from auth import TokenAuth
from models import Base
from token_store import TokenStore


@pytest_asyncio.fixture
async def auth_with_token():
    engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    store = TokenStore()

    async with factory() as session:
        raw_token = await store.create_token(session)

    yield TokenAuth(store, factory), raw_token
    await engine.dispose()


class TestTokenAuth:
    async def test_no_store_skips_check(self) -> None:
        """未配置 DB 时跳过认证"""
        auth = TokenAuth(None, None)
        request = AsyncMock()
        request.headers = {}
        await auth(request)

    async def test_missing_header_returns_401(self, auth_with_token) -> None:
        """缺少 Authorization 头返回 401"""
        auth, _ = auth_with_token
        request = AsyncMock()
        request.headers = {}

        with pytest.raises(HTTPException) as exc:
            await auth(request)
        assert exc.value.status_code == 401

    async def test_wrong_scheme_returns_401(self) -> None:
        """非 Bearer scheme 返回 401"""
        engine = create_async_engine('sqlite+aiosqlite:///:memory:')
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        auth = TokenAuth(TokenStore(), factory)
        request = AsyncMock()
        request.headers = {'Authorization': 'Basic xyz'}

        with pytest.raises(HTTPException) as exc:
            await auth(request)
        assert exc.value.status_code == 401
        await engine.dispose()

    async def test_correct_token_passes(self, auth_with_token) -> None:
        """正确 token 通过认证"""
        auth, raw_token = auth_with_token
        request = AsyncMock()
        request.headers = {'Authorization': f'Bearer {raw_token}'}

        await auth(request)

    async def test_wrong_token_returns_401(self) -> None:
        """错误 token 返回 401"""
        engine = create_async_engine('sqlite+aiosqlite:///:memory:')
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        store = TokenStore()

        async with factory() as session:
            await store.create_token(session)

        auth = TokenAuth(store, factory)
        request = AsyncMock()
        request.headers = {'Authorization': 'Bearer wrong-token'}

        with pytest.raises(HTTPException) as exc:
            await auth(request)
        assert exc.value.status_code == 401
        await engine.dispose()
