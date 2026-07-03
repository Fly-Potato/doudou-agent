from typing import Any

type SessionId = str


class Message:
    def __init__(
        self,
        role: str,
        content: str | None = None,
        tool_call_id: str | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
    ) -> None:
        self.role = role
        self.content = content
        self.tool_call_id = tool_call_id
        self.tool_calls = tool_calls

    def to_dict(self) -> dict[str, Any]:
        msg: dict[str, Any] = {'role': self.role}
        if self.content is not None:
            msg['content'] = self.content
        if self.tool_calls is not None:
            msg['tool_calls'] = self.tool_calls
        if self.tool_call_id is not None:
            msg['tool_call_id'] = self.tool_call_id
        return msg

    def __repr__(self) -> str:
        return f'Message(role={self.role!r}, content={self.content!r})'
