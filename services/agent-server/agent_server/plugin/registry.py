from __future__ import annotations

import logging
from typing import Any

from agent_server.plugin.base import Tool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """合并所有插件的工具，提供名称查询和 OpenAI 格式转换"""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            logger.warning("工具 '%s' 被覆盖", tool.name)
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_definitions(self) -> list[dict[str, Any]]:
        """返回 OpenAI function-calling 格式的工具列表"""
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in self._tools.values()
        ]

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools
