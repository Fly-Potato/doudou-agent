from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import openai

from agent.llm.base import LLMProvider


class OpenAIProvider(LLMProvider):
    """OpenAI 兼容 Provider，通过 base_url 适配 DeepSeek/Ollama/OpenRouter 等

    客户端在首次调用 chat_completion 时创建，允许服务器启动时不配置 API key。
    api_key 由 openai SDK 自动从 OPENAI_API_KEY 环境变量读取。
    """

    def __init__(self, model: str, base_url: str, **kwargs: Any) -> None:
        self._model = model
        self._base_url = base_url
        self._extra_kwargs = kwargs
        self._client: openai.AsyncOpenAI | None = None

    def _get_client(self) -> openai.AsyncOpenAI:
        if self._client is None:
            self._client = openai.AsyncOpenAI(base_url=self._base_url)
        return self._client

    async def chat_completion(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> AsyncIterator[dict[str, Any]]:
        client = self._get_client()
        stream = await client.chat.completions.create(
            model=self._model,
            messages=messages,
            tools=tools if tools else openai.NOT_GIVEN,
            stream=True,
            stream_options={'include_usage': True},
            **self._extra_kwargs,
        )

        accumulated_tool_calls: dict[int, dict[str, Any]] = {}
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta is None:
                continue

            if delta.content:
                yield {'type': 'token', 'content': delta.content}

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in accumulated_tool_calls:
                        accumulated_tool_calls[idx] = {
                            'id': '',
                            'type': 'function',
                            'function': {'name': '', 'arguments': ''},
                        }
                    entry = accumulated_tool_calls[idx]
                    if tc.id:
                        entry['id'] = tc.id
                    if tc.function:
                        if tc.function.name:
                            entry['function']['name'] += tc.function.name
                        if tc.function.arguments:
                            entry['function']['arguments'] += tc.function.arguments

        if accumulated_tool_calls:
            yield {
                'type': 'tool_calls',
                'calls': list(accumulated_tool_calls.values()),
            }
