# agent_server/auth.py
from __future__ import annotations

import hashlib
import logging

from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)


def _mask_token(token: str) -> str:
    if len(token) <= 6:
        return "***"
    return token[:4] + "***"


class TokenAuth:
    """Token 认证：SHA-256 哈希比对"""

    def __init__(self, token_hash: str) -> None:
        self._token_hash = token_hash

    async def __call__(self, request: Request) -> None:
        if not self._token_hash:
            return

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            logger.warning("认证失败: 缺少 Authorization 头")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="缺少认证令牌"
            )

        token = auth_header.removeprefix("Bearer ")
        computed = hashlib.sha256(token.encode()).hexdigest()
        if computed != self._token_hash:
            logger.warning("认证失败: token=%s", _mask_token(token))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="认证令牌无效"
            )
