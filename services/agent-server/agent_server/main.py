from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from agent_server.agent.loop import AgentLoop
from agent_server.auth import TokenAuth
from agent_server.config import load_config
from agent_server.event import EventBus
from agent_server.models import Base
from agent_server.plugin.manager import PluginManager
from agent_server.token_store import TokenStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    session_id: str
    content: str


_agent_loop: AgentLoop | None = None
_token_auth: TokenAuth | None = None


async def verify_token(request: Request) -> None:
    if _token_auth is not None:
        await _token_auth(request)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global _agent_loop, _token_auth

    config = load_config()

    _engine = None
    _session_factory = None
    _token_store = None
    if config.auth.db_url:
        _engine = create_async_engine(config.auth.db_url)
        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
        _token_store = TokenStore()

    plugin_manager = PluginManager()
    plugin_configs = [
        {'name': p.name, 'enabled': p.enabled, 'config': p.config} for p in config.plugins
    ]
    await plugin_manager.load_enabled(plugin_configs)

    _token_auth = TokenAuth(_token_store, _session_factory)
    _agent_loop = AgentLoop(
        config,
        plugin_manager.tool_registry,
        EventBus(plugin_manager.plugins),
    )
    logger.info('agent-server 启动完成，已加载 %d 个插件', len(plugin_manager.plugins))
    yield
    await plugin_manager.shutdown()
    if _engine is not None:
        await _engine.dispose()


app = FastAPI(title='agent-server', lifespan=lifespan)


@app.get('/health')
async def health() -> dict[str, str]:
    return {'status': 'ok'}


@app.post('/chat')
async def chat(
    body: ChatRequest,
    _: None = Depends(verify_token),
) -> StreamingResponse:
    if _agent_loop is None:
        raise RuntimeError('AgentLoop 尚未初始化')

    async def event_stream() -> AsyncIterator[str]:
        async for sse_event in _agent_loop.run(body.session_id, body.content):
            yield sse_event

    return StreamingResponse(
        event_stream(),
        media_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
        },
    )


# ── CLI 命令 ──────────────────────────────────────────────


async def _init_store(db_url: str):
    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    store = TokenStore()
    return engine, factory, store


async def _run_generate_token(db_url: str) -> None:
    engine, factory, store = await _init_store(db_url)
    try:
        async with factory() as session:
            token = await store.create_token(session)
        print(token)
    finally:
        await engine.dispose()


async def _run_list_tokens(db_url: str) -> None:
    engine, factory, store = await _init_store(db_url)
    try:
        async with factory() as session:
            tokens = await store.list_tokens(session)
        if not tokens:
            print('(暂无令牌)')
            return
        print(f'{"ID":<6}  {"创建时间":<35}')
        for t in tokens:
            print(f'{t["id"]:<6}  {t["created_at"]:<35}')
    finally:
        await engine.dispose()


async def _run_delete_token(db_url: str, token_id: int) -> None:
    engine, factory, store = await _init_store(db_url)
    try:
        async with factory() as session:
            ok = await store.delete_token(session, token_id)
        if ok:
            print(f'令牌 {token_id} 已删除')
        else:
            print(f'令牌 {token_id} 不存在', file=sys.stderr)
            sys.exit(1)
    finally:
        await engine.dispose()


def serve_cmd(_args: argparse.Namespace) -> None:
    import uvicorn

    config = load_config()
    uvicorn.run(
        'agent_server.main:app',
        host=config.server.host,
        port=config.server.port,
        reload=True,
    )


def generate_token_cmd(_args: argparse.Namespace) -> None:
    config = load_config()
    if not config.auth.db_url:
        print('错误: 未配置 auth.db_url', file=sys.stderr)
        sys.exit(1)
    asyncio.run(_run_generate_token(config.auth.db_url))


def list_tokens_cmd(_args: argparse.Namespace) -> None:
    config = load_config()
    if not config.auth.db_url:
        print('错误: 未配置 auth.db_url', file=sys.stderr)
        sys.exit(1)
    asyncio.run(_run_list_tokens(config.auth.db_url))


def delete_token_cmd(args: argparse.Namespace) -> None:
    config = load_config()
    if not config.auth.db_url:
        print('错误: 未配置 auth.db_url', file=sys.stderr)
        sys.exit(1)
    asyncio.run(_run_delete_token(config.auth.db_url, args.id))


def run() -> None:
    parser = argparse.ArgumentParser(prog='agent-server')
    subparsers = parser.add_subparsers(dest='command')

    sp = subparsers.add_parser('serve', help='启动 HTTP 服务')
    sp.set_defaults(func=serve_cmd)

    sp = subparsers.add_parser('generate-token', help='生成新令牌')
    sp.set_defaults(func=generate_token_cmd)

    sp = subparsers.add_parser('list-tokens', help='列出所有令牌')
    sp.set_defaults(func=list_tokens_cmd)

    sp = subparsers.add_parser('delete-token', help='删除指定令牌')
    sp.add_argument('id', type=int, help='令牌 ID')
    sp.set_defaults(func=delete_token_cmd)

    args = parser.parse_args()
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    run()
