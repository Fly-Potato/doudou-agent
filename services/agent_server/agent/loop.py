# agent_server/agent/loop.py
from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from agent.llm import LLMProvider
from agent.session import SessionManager
from config import AppConfig
from event import EventBus
from plugin.registry import ToolRegistry
from schemas import Message, SessionId

logger = logging.getLogger(__name__)


class AgentLoop:
    """AI 对话循环：接收消息 → 调 LLM → 调度工具 → 流式返回 SSE 事件"""

    def __init__(
        self,
        config: AppConfig,
        registry: ToolRegistry,
        event_bus: EventBus,
    ) -> None:
        self._config = config
        self._registry = registry
        self._event_bus = event_bus
        self._sessions = SessionManager(max_messages=config.session.history_max_messages)

    async def run(
        self,
        session_id: SessionId,
        user_content: str,
        *,
        provider: LLMProvider,
        model: str,
        api_key: str,
    ) -> AsyncIterator[str]:
        """执行 Agent 循环，yield SSE 格式的事件字符串"""
        tool_rounds = 0
        max_rounds = self._config.session.max_tool_rounds
        timeout = self._config.session.tool_timeout_sec

        try:
            # 1-2. 接收消息，运行 on_message 钩子
            message: dict[str, Any] = {'role': 'user', 'content': user_content}
            message = await self._event_bus.on_message(session_id, message)
            self._sessions.add_message(session_id, Message(**message))

            while tool_rounds < max_rounds:
                # 3-4. 获取历史，运行 pre_llm_call 钩子
                history = self._sessions.get_history(session_id)
                messages = [m.to_dict() for m in history]
                messages = await self._event_bus.pre_llm_call(session_id, messages)

                # 5. 调用 LLM
                tools = self._registry.list_definitions()
                full_content = ''
                tool_calls: list[dict[str, Any]] | None = None

                async for chunk in provider.chat_completion(
                    messages, tools, model=model, api_key=api_key
                ):
                    if chunk['type'] == 'token':
                        full_content += chunk['content']
                        data = json.dumps({'content': chunk['content']}, ensure_ascii=False)
                        yield f'event: token\ndata: {data}\n\n'
                    elif chunk['type'] == 'tool_calls':
                        tool_calls = chunk['calls']
                        yield (
                            'event: tool_call\n'
                            f'data: {json.dumps({"calls": tool_calls}, ensure_ascii=False)}\n\n'
                        )

                if tool_calls:
                    # 6. 执行工具
                    tool_rounds += 1
                    self._sessions.add_message(
                        session_id,
                        Message(
                            role='assistant',
                            content=full_content or None,
                            tool_calls=tool_calls,
                        ),
                    )

                    for tc in tool_calls:
                        name = tc['function']['name']
                        tool = self._registry.get(name)
                        if tool is None:
                            tool_result = f"工具 '{name}' 未找到"
                        else:
                            try:
                                arguments = json.loads(tc['function']['arguments'])
                                result = await asyncio.wait_for(
                                    tool.handler(session_id, **arguments),
                                    timeout=timeout,
                                )
                                tool_result = json.dumps(result, ensure_ascii=False)
                            except TimeoutError:
                                tool_result = f"工具 '{name}' 执行超时"
                            except Exception as e:
                                tool_result = f"工具 '{name}' 执行出错: {e}"

                        data = json.dumps({'tool': name, 'result': tool_result}, ensure_ascii=False)
                        yield f'event: tool_result\ndata: {data}\n\n'
                        self._sessions.add_message(
                            session_id,
                            Message(
                                role='tool',
                                content=tool_result,
                                tool_call_id=tc['id'],
                            ),
                        )
                else:
                    # 7-9. 文本响应
                    self._sessions.add_message(
                        session_id,
                        Message(role='assistant', content=full_content),
                    )
                    yield (
                        'event: done\n'
                        f'data: {json.dumps({"session_id": session_id}, ensure_ascii=False)}\n\n'
                    )
                    return

            # 超过最大工具调用轮数
            err = {'code': 'MAX_ROUNDS', 'message': '工具调用轮数超限'}
            data = json.dumps(err, ensure_ascii=False)
            yield f'event: error\ndata: {data}\n\n'

        except Exception as e:
            logger.exception('AgentLoop 出错: session=%s', session_id)
            await self._event_bus.on_error(session_id, e)
            data = json.dumps({'code': 'INTERNAL_ERROR', 'message': str(e)}, ensure_ascii=False)
            yield f'event: error\ndata: {data}\n\n'
