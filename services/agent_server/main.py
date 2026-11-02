import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, StringConstraints

from auth import Identity, IdentityDep, StoreDep, require_admin
from users import IssuedKey, User, UserStore, generate_key, hash_key


class CreateUser(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


@asynccontextmanager
async def lifespan(app: FastAPI):
    admin_key = os.environ.get('AGENT_SERVER_ADMIN_KEY', '')
    if not 32 <= len(admin_key) <= 4096 or any(not 33 <= ord(char) <= 126 for char in admin_key):
        raise RuntimeError(
            'AGENT_SERVER_ADMIN_KEY 必须为 32～4096 字符的可打印 ASCII 随机密钥，不能含空白'
        )
    app.state.admin_key_hash = hash_key(admin_key)
    app.state.users = UserStore(
        Path(os.environ.get('AGENT_SERVER_DB_PATH', str(Path(__file__).parent / 'data/users.db')))
    )
    yield


admin = APIRouter(prefix='/admin/users', dependencies=[Depends(require_admin)])


@admin.get('')
def list_users(store: StoreDep) -> list[User]:
    return store.list_users()


@admin.post('', status_code=201)
def create_user(body: CreateUser, store: StoreDep) -> IssuedKey:
    key = generate_key()
    user = store.create(body.name, key)
    return IssuedKey(**user.model_dump(), key=key)


@admin.post('/{user_id}/key')
def regenerate_key(user_id: str, store: StoreDep) -> IssuedKey:
    key = generate_key()
    user = store.set_key(user_id, hash_key(key))
    if user is None:
        raise HTTPException(404, '用户不存在')
    return IssuedKey(**user.model_dump(), key=key)


@admin.delete('/{user_id}/key', status_code=204)
def revoke_key(user_id: str, store: StoreDep) -> Response:
    if store.set_key(user_id, None) is None:
        raise HTTPException(404, '用户不存在')
    return Response(status_code=204)


def create_app() -> FastAPI:
    app = FastAPI(title='Doudou Agent', lifespan=lifespan)

    @app.middleware('http')
    async def prevent_auth_caching(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith(('/auth/', '/admin/')):
            response.headers['Cache-Control'] = 'no-store'
        return response

    @app.get('/health')
    def health() -> dict[str, str]:
        return {'status': 'ok'}

    @app.get('/auth/me')
    def current_identity(identity: IdentityDep) -> Identity:
        return identity

    app.include_router(admin)
    return app


app = create_app()
