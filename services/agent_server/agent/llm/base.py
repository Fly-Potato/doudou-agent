from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any


class LLMProvider(ABC):
    """LLM 提供者抽象接口，中枢通过此接口调用 LLM"""

    @abstractmethod
    async def chat_completion(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> AsyncIterator[dict[str, Any]]:
        """
        流式返回 dict:
          {"type": "token", "content": "..."}
          {"type": "tool_calls", "calls": [...]}
        """
        ...
