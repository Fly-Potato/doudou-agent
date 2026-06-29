from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from agent_server.types import SessionId


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]  # OpenAI function-calling JSON Schema
    handler: Callable[..., Any]  # async (session_id: SessionId, **params) -> Any


class Plugin(ABC):
    """插件基类，所有方法默认空实现，插件按需覆盖"""

    @property
    @abstractmethod
    def name(self) -> str:
        """插件唯一标识"""
        ...

    @abstractmethod
    def register_tools(self) -> list[Tool]:
        """返回插件提供的工具列表，中枢在加载时调用一次"""
        ...

    async def on_load(self, config: dict[str, Any]) -> None:  # noqa: B027
        """插件加载时调用，传入该插件在 YAML 中声明的配置"""
        ...

    async def on_shutdown(self) -> None:  # noqa: B027
        """服务关闭时调用，释放资源"""
        ...

    async def on_message(
        self, session_id: SessionId, message: dict[str, Any]
    ) -> dict[str, Any] | None:
        """收到客户端消息后立即调用，可返回修改后的消息"""
        return None

    async def pre_llm_call(
        self, session_id: SessionId, messages: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """调用 LLM 前调用，可修改/注入消息列表"""
        return messages

    async def post_llm_call(
        self, session_id: SessionId, response: dict[str, Any]
    ) -> dict[str, Any]:
        """LLM 返回后调用，可修改响应"""
        return response

    async def on_error(self, session_id: SessionId, error: Exception) -> None:  # noqa: B027
        """任何环节出错时调用，用于日志/告警"""
        ...
