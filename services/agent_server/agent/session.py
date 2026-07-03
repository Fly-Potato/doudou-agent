# agent_server/agent/session.py
from __future__ import annotations

from schemas import Message, SessionId


class SessionManager:
    """管理会话消息历史，按 session_id 隔离，支持消息数量裁剪"""

    def __init__(self, max_messages: int = 50) -> None:
        self._sessions: dict[SessionId, list[Message]] = {}
        self._max_messages = max_messages

    def get_history(self, session_id: SessionId) -> list[Message]:
        return self._sessions.setdefault(session_id, [])

    def add_message(self, session_id: SessionId, message: Message) -> None:
        history = self.get_history(session_id)
        history.append(message)
        if len(history) > self._max_messages:
            self._sessions[session_id] = history[-self._max_messages :]

    def remove_session(self, session_id: SessionId) -> None:
        self._sessions.pop(session_id, None)

    def __len__(self) -> int:
        return len(self._sessions)
