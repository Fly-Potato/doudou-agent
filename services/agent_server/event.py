from __future__ import annotations

from typing import Any

from doudou_agent_sdk import Plugin

from schemas import SessionId


class EventBus:
    """按插件加载顺序串行调用钩子"""

    def __init__(self, plugins: list[Plugin]) -> None:
        self._plugins = plugins

    async def on_message(self, session_id: SessionId, message: dict[str, Any]) -> dict[str, Any]:
        for plugin in self._plugins:
            result = await plugin.on_message(session_id, message)
            if result is not None:
                message = result
        return message

    async def pre_llm_call(
        self, session_id: SessionId, messages: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        for plugin in self._plugins:
            messages = await plugin.pre_llm_call(session_id, messages)
        return messages

    async def post_llm_call(
        self, session_id: SessionId, response: dict[str, Any]
    ) -> dict[str, Any]:
        for plugin in self._plugins:
            response = await plugin.post_llm_call(session_id, response)
        return response

    async def on_error(self, session_id: SessionId, error: Exception) -> None:
        for plugin in self._plugins:
            await plugin.on_error(session_id, error)
