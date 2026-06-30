from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from agent_server.models import Base
from agent_server.token_store import TokenStore


@pytest.fixture
async def store_and_session():
    engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    store = TokenStore()
    async with factory() as session:
        yield store, session
    await engine.dispose()


class TestTokenStore:
    async def test_create_token_returns_raw_token(self, store_and_session):
        """生成 token 返回原始值"""
        store, session = store_and_session
        raw = await store.create_token(session)
        assert len(raw) > 20
        assert isinstance(raw, str)

    async def test_verify_valid_token(self, store_and_session):
        """有效 token 验证通过"""
        store, session = store_and_session
        raw = await store.create_token(session)
        valid = await store.verify_token(session, raw)
        assert valid

    async def test_verify_invalid_token(self, store_and_session):
        """无效 token 验证失败"""
        store, session = store_and_session
        valid = await store.verify_token(session, 'invalid-token')
        assert not valid

    async def test_list_tokens(self, store_and_session):
        """列出所有 token"""
        store, session = store_and_session
        await store.create_token(session)
        await store.create_token(session)
        tokens = await store.list_tokens(session)
        assert len(tokens) == 2
        assert all('id' in t and 'created_at' in t for t in tokens)

    async def test_delete_existing_token(self, store_and_session):
        """删除存在的 token 成功"""
        store, session = store_and_session
        await store.create_token(session)
        tokens = await store.list_tokens(session)
        token_id = tokens[0]['id']
        deleted = await store.delete_token(session, token_id)
        assert deleted
        remaining = await store.list_tokens(session)
        assert len(remaining) == 0

    async def test_delete_non_existent_token(self, store_and_session):
        """删除不存在的 token 返回 False"""
        store, session = store_and_session
        deleted = await store.delete_token(session, 999)
        assert not deleted
