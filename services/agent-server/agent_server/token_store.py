from __future__ import annotations

import hashlib
import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_server.models import Token


class TokenStore:
    async def create_token(self, session: AsyncSession) -> str:
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        session.add(Token(token_hash=token_hash))
        await session.commit()
        return raw_token

    async def verify_token(self, session: AsyncSession, raw_token: str) -> bool:
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        result = await session.execute(select(Token).where(Token.token_hash == token_hash))
        return result.scalar_one_or_none() is not None

    async def list_tokens(self, session: AsyncSession) -> list[dict[str, object]]:
        result = await session.execute(select(Token).order_by(Token.id))
        tokens = result.scalars().all()
        return [
            {'id': t.id, 'created_at': t.created_at.isoformat() if t.created_at else None}
            for t in tokens
        ]

    async def delete_token(self, session: AsyncSession, token_id: int) -> bool:
        result = await session.execute(select(Token).where(Token.id == token_id))
        token = result.scalar_one_or_none()
        if token is None:
            return False
        await session.delete(token)
        await session.commit()
        return True
