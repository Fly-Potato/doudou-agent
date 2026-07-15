# tests/test_agent_loop.py
from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import pytest
from doudou_agent_sdk import Tool

from agent.loop import AgentLoop
from event import EventBus
from plugin.registry import ToolRegistry
from schemas import SessionId
from settings import AppConfig


class MockProvider:
    """可编程的假 LLM Provider"""

    id = 'mock'
    base_url = 'https://mock.test'

    def __init__(self, *chunk_lists: list[dict[str, Any]]) -> None:
        self._chunk_lists = list(chunk_lists)
        self._call_idx = 0

    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        *,
        model: str = '',
        api_key: str = '',
    ) -> AsyncIterator[dict[str, Any]]:
        chunks = self._chunk_lists[self._call_idx]
        self._call_idx += 1
        for c in chunks:
            yield c


def make_config(**overrides: Any) -> AppConfig:
    config = AppConfig()
    for key, value in overrides.items():
        if hasattr(config.session, key):
            setattr(config.session, key, value)
    return config


class TestAgentLoop:
    @pytest.mark.asyncio
    async def test_basic_text_response(self) -> None:
        provider = MockProvider(
            [
                {'type': 'token', 'content': '你好，'},
                {'type': 'token', 'content': '有什么可以帮你的？'},
            ]
        )

        config = make_config()
        registry = ToolRegistry()
        event_bus = EventBus([])
        loop = AgentLoop(config, registry, event_bus)

        events: list[str] = []
        async for event_str in loop.run(
            'sess-1', '你好', provider=provider, model='mock', api_key=''
        ):
            events.append(event_str)

        token_events = [e for e in events if e.startswith('event: token')]
        done_events = [e for e in events if e.startswith('event: done')]
        assert len(token_events) == 2
        assert len(done_events) == 1

    @pytest.mark.asyncio
    async def test_tool_calling_flow(self) -> None:
        async def echo_handler(session_id: SessionId, **params: object) -> dict:
            return {'echo': params.get('text', '')}

        tool = Tool(
            name='echo',
            description='回显',
            parameters={
                'type': 'object',
                'properties': {'text': {'type': 'string'}},
                'required': ['text'],
            },
            handler=echo_handler,
        )

        registry = ToolRegistry()
        registry.register(tool)

        provider = MockProvider(
            # 第一次调用 LLM: 返回 tool_calls
            [
                {
                    'type': 'tool_calls',
                    'calls': [
                        {
                            'id': 'call_1',
                            'type': 'function',
                            'function': {
                                'name': 'echo',
                                'arguments': json.dumps({'text': 'hello'}),
                            },
                        }
                    ],
                }
            ],
            # 第二次调用 LLM: 返回最终文本
            [
                {'type': 'token', 'content': '回显结果: hello'},
            ],
        )

        config = make_config()
        event_bus = EventBus([])
        loop = AgentLoop(config, registry, event_bus)

        events: list[str] = []
        async for event_str in loop.run(
            'sess-2', '帮我回显 hello', provider=provider, model='mock', api_key=''
        ):
            events.append(event_str)

        tool_call_events = [e for e in events if 'event: tool_call' in e]
        tool_result_events = [e for e in events if 'event: tool_result' in e]
        token_events = [e for e in events if e.startswith('event: token')]
        done_events = [e for e in events if e.startswith('event: done')]

        assert len(tool_call_events) == 1
        assert len(tool_result_events) == 1
        assert len(token_events) == 1
        assert len(done_events) == 1

    @pytest.mark.asyncio
    async def test_max_rounds_exceeded(self) -> None:
        provider = MockProvider(
            *(
                [
                    {
                        'type': 'tool_calls',
                        'calls': [
                            {
                                'id': f'call_{i}',
                                'type': 'function',
                                'function': {
                                    'name': 'echo',
                                    'arguments': json.dumps({'text': 'x'}),
                                },
                            }
                        ],
                    }
                ]
                for i in range(5)
            )
        )

        async def echo_handler(session_id: SessionId, **params: object) -> dict:
            return {'ok': True}

        tool = Tool(
            name='echo',
            description='',
            parameters={'type': 'object', 'properties': {'text': {'type': 'string'}}},
            handler=echo_handler,
        )

        registry = ToolRegistry()
        registry.register(tool)

        config = make_config(max_tool_rounds=3)
        event_bus = EventBus([])
        loop = AgentLoop(config, registry, event_bus)

        events: list[str] = []
        async for event_str in loop.run(
            'sess-3', 'test', provider=provider, model='mock', api_key=''
        ):
            events.append(event_str)

        error_events = [e for e in events if 'MAX_ROUNDS' in e]
        assert len(error_events) == 1
