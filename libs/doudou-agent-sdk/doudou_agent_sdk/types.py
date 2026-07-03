from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

type SessionId = str


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]  # OpenAI function-calling JSON Schema
    handler: Callable[..., Any]  # async (session_id: SessionId, **params) -> Any


@dataclass
class Skill:
    name: str
    description: str
    content: str
    tools: list[str] = field(default_factory=list)
