from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from doudou_agent_sdk.config import PluginConfig
from doudou_agent_sdk.types import SessionId, Skill, Tool


class Plugin(ABC):
    """插件基类 — 插件作者继承此类开发插件。

    子类必须覆盖 name，可用 @property 或类属性形式。

    可选的类属性：
        version: str = "0.1.0"
        description: str = ""
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """插件唯一标识"""
        ...

    version: str = '0.1.0'
    description: str = ''

    # ── 必须实现 ──────────────────────────────────

    @abstractmethod
    def register_tools(self) -> list[Tool]:
        """返回插件提供的工具列表"""

    # ── 可选覆盖 ──────────────────────────────────

    def register_skills(self) -> list[Skill]:
        """返回插件提供的技能列表"""
        return []

    def config_cls(self) -> type[PluginConfig] | None:
        """返回用于配置校验的 PluginConfig 子类，None 表示无需校验"""
        return None

    async def on_load(self, config: PluginConfig | dict[str, Any] | None = None) -> None:  # noqa: B027
        """插件加载时调用，config 来自外部插件的 PluginConfig 或空 dict"""

    async def on_shutdown(self) -> None:  # noqa: B027
        """服务关闭时调用，释放资源"""

    async def on_message(
        self, session_id: SessionId, message: dict[str, Any]
    ) -> dict[str, Any] | None:
        """收到客户端消息后立即调用，返回修改后的消息或 None"""
        return None

    async def pre_llm_call(
        self, session_id: SessionId, messages: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """调用 LLM 前调用，可修改消息列表"""
        return messages

    async def post_llm_call(
        self, session_id: SessionId, response: dict[str, Any]
    ) -> dict[str, Any]:
        """LLM 返回后调用，可修改响应"""
        return response

    async def on_error(self, session_id: SessionId, error: Exception) -> None:  # noqa: B027
        """任何环节出错时调用，用于日志/告警"""
