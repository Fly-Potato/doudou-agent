from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import openai

from agent.llm.base import LLMProvider


class OpenAICompatibleProvider(LLMProvider):
    """OpenAI 兼容格式的 Provider 基类

    id 和 base_url 由子类硬编码。
    chat_completion 接收 model 和 api_key 作为参数。
    """

    def __init__(self, **kwargs: Any) -> None:
        self._extra_kwargs = kwargs
        self._client: openai.AsyncOpenAI | None = None

    def _get_client(self, api_key: str) -> openai.AsyncOpenAI:
        if self._client is None or self._client.api_key != api_key:
            self._client = openai.AsyncOpenAI(
                base_url=self.base_url,
                api_key=api_key or None,
            )
        return self._client

    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        *,
        model: str,
        api_key: str,
    ) -> AsyncIterator[dict[str, Any]]:
        client = self._get_client(api_key)
        stream = await client.chat.completions.create(
            model=model,
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
