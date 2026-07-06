from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any


class LLMProvider(ABC):
    """LLM 提供者抽象接口，中枢通过此接口调用 LLM

    子类必须覆盖 id 和 base_url（类型级硬编码）。
    model 和 api_key 由 chat_completion 的调用方传入。
    """

    @property
    @abstractmethod
    def id(self) -> str:
        """Provider 类型标识，如 'deepseek'，类级硬编码"""

    @property
    @abstractmethod
    def base_url(self) -> str:
        """API 端点地址，类级硬编码"""

    @abstractmethod
    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        *,
        model: str,
        api_key: str,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        流式返回 dict:
          {"type": "token", "content": "..."}
          {"type": "tool_calls", "calls": [...]}
        """
