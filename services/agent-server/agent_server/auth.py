from __future__ import annotations

import logging

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import async_sessionmaker

from agent_server.token_store import TokenStore

logger = logging.getLogger(__name__)


def _mask_token(token: str) -> str:
    if len(token) <= 6:
        return '***'
    return token[:4] + '***'


class TokenAuth:
    def __init__(
        self,
        store: TokenStore | None,
        session_factory: async_sessionmaker | None,
    ) -> None:
        self._store = store
        self._session_factory = session_factory

    async def __call__(self, request: Request) -> None:
        if self._store is None or self._session_factory is None:
            return

        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            logger.warning('认证失败: 缺少 Authorization 头')
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='缺少认证令牌')

        token = auth_header.removeprefix('Bearer ')

        async with self._session_factory() as session:
            valid = await self._store.verify_token(session, token)

        if not valid:
            logger.warning('认证失败: token=%s', _mask_token(token))
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='认证令牌无效')
