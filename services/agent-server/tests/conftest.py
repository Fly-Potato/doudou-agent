# tests/conftest.py
from __future__ import annotations

from agent_server.plugin.base import Plugin, Tool


class DummyPlugin(Plugin):
    """测试用假插件，注册一个 echo 工具 + 记录钩子调用"""

    def __init__(self) -> None:
        self._load_called = False
        self._hook_counts: dict[str, int] = {}

    @property
    def name(self) -> str:
        return "dummy"

    def register_tools(self) -> list[Tool]:
        async def echo(session_id: str, **params: object) -> dict[str, object]:
            return {"echo": params.get("text", "")}

        return [
            Tool(
                name="echo",
                description="回显输入内容",
                parameters={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "要回显的文本"}
                    },
                    "required": ["text"],
                },
                handler=echo,
            )
        ]

    async def on_load(self, config: dict) -> None:
        self._load_called = True

    async def pre_llm_call(self, session_id, messages):
        self._hook_counts.setdefault("pre_llm_call", 0)
        self._hook_counts["pre_llm_call"] += 1
        return messages

    async def on_error(self, session_id, error):
        self._hook_counts.setdefault("on_error", 0)
        self._hook_counts["on_error"] += 1
