from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from models import Base, Token, configure_timezone
from token_store import TokenStore


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

    async def test_created_at_timezone_is_utc(self, store_and_session):
        """created_at 默认使用 UTC 时区"""
        before = datetime.now(UTC)
        configure_timezone('UTC')
        store, session = store_and_session
        await store.create_token(session)
        result = await session.execute(select(Token).order_by(Token.id))
        token = result.scalars().first()
        assert token is not None
        # SQLite 不保留 tzinfo，但时间值应接近当前 UTC 时间
        offset = abs((token.created_at - before.replace(tzinfo=None)).total_seconds())
        assert offset < 5, f'created_at 偏移过大: {offset} 秒'

    async def test_configured_timezone_affects_created_at(self, store_and_session):
        """切换时区后 created_at 的时间偏移不同"""
        configure_timezone('UTC')
        store, session = store_and_session
        await store.create_token(session)
        configure_timezone('Asia/Shanghai')
        await store.create_token(session)

        result = await session.execute(select(Token).order_by(Token.id))
        tokens = result.scalars().all()
        assert len(tokens) == 2
        # UTC token 和 Asia/Shanghai token 应相差约 8 小时
        diff = (tokens[1].created_at - tokens[0].created_at).total_seconds()
        assert 28000 < diff < 29000, f'预期 8 小时偏移，实际 {diff} 秒'
        configure_timezone('UTC')

    async def test_delete_non_existent_token(self, store_and_session):
        """删除不存在的 token 返回 False"""
        store, session = store_and_session
        deleted = await store.delete_token(session, 999)
        assert not deleted
