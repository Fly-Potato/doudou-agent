from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent_server.agent.loop import AgentLoop
from agent_server.auth import TokenAuth
from agent_server.config import load_config
from agent_server.event import EventBus
from agent_server.plugin.manager import PluginManager

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
    plugin_manager = PluginManager()

    plugin_configs = [
        {'name': p.name, 'enabled': p.enabled, 'config': p.config} for p in config.plugins
    ]
    await plugin_manager.load_enabled(plugin_configs)

    _token_auth = TokenAuth(config.auth.token_hash)
    _agent_loop = AgentLoop(
        config,
        plugin_manager.tool_registry,
        EventBus(plugin_manager.plugins),
    )
    logger.info('agent-server 启动完成，已加载 %d 个插件', len(plugin_manager.plugins))
    yield
    await plugin_manager.shutdown()


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


def run() -> None:
    import uvicorn

    config = load_config()
    uvicorn.run(
        'agent_server.main:app',
        host=config.server.host,
        port=config.server.port,
        reload=True,
    )


if __name__ == '__main__':
    run()
