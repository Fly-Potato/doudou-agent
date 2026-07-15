from __future__ import annotations

import os


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == '':
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f'环境变量 {name} 必须是整数') from exc


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value == '':
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f'环境变量 {name} 必须是数字') from exc


MAX_TOOL_ROUNDS = _get_int('AGENT_SERVER_SESSION_MAX_TOOL_ROUNDS', 10)
TOOL_TIMEOUT_SEC = _get_float('AGENT_SERVER_SESSION_TOOL_TIMEOUT_SEC', 30.0)
HISTORY_MAX_MESSAGES = _get_int('AGENT_SERVER_SESSION_HISTORY_MAX_MESSAGES', 50)
AUTH_DB_URL = os.getenv('AGENT_SERVER_AUTH_DB_URL', 'sqlite+aiosqlite:///tokens.db')
TIMEZONE = os.getenv('AGENT_SERVER_TIMEZONE', 'UTC')
