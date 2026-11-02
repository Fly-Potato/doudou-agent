import secrets
from typing import Annotated, Literal

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from users import UserStore, hash_key

security = HTTPBearer(auto_error=False)


class Identity(BaseModel):
    role: Literal['admin', 'user']
    user_id: str | None = None


def get_store(request: Request) -> UserStore:
    return request.app.state.users


StoreDep = Annotated[UserStore, Depends(get_store)]


def authenticate(
    request: Request,
    store: StoreDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> Identity:
    if request.url.scheme != 'https' and (
        request.client is None or request.client.host not in ('127.0.0.1', '::1')
    ):
        raise HTTPException(403, '认证请求必须使用 HTTPS')
    if credentials and len(credentials.credentials) <= 4096:
        digest = hash_key(credentials.credentials)
        if secrets.compare_digest(digest, request.app.state.admin_key_hash):
            return Identity(role='admin')
        user_id = store.find_user_id(digest)
        if user_id is not None:
            return Identity(role='user', user_id=user_id)
    raise HTTPException(401, '密钥缺失或无效', headers={'WWW-Authenticate': 'Bearer'})


IdentityDep = Annotated[Identity, Depends(authenticate)]


def require_admin(identity: IdentityDep) -> None:
    if identity.role != 'admin':
        raise HTTPException(403, '需要管理员权限')
