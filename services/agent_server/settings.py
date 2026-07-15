from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class ServerConfig:
    host: str = '0.0.0.0'
    port: int = 8888


@dataclass
class LLMConfig:
    provider: str = 'deepseek'


@dataclass
class SessionConfig:
    max_tool_rounds: int = 10
    tool_timeout_sec: float = 30.0
    history_max_messages: int = 50


@dataclass
class AuthConfig:
    db_url: str = 'sqlite+aiosqlite:///tokens.db'


@dataclass
class PluginSettings:
    external_dirs: list[str] = field(default_factory=lambda: ['/plugins'])


@dataclass
class AppConfig:
    server: ServerConfig = field(default_factory=ServerConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    session: SessionConfig = field(default_factory=SessionConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    plugin: PluginSettings = field(default_factory=PluginSettings)
    timezone: str = 'UTC'  # ORM 默认时区，例如 'Asia/Shanghai'


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


def _get_paths(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name)
    if value is None:
        return list(default)
    return [item for item in value.split(os.pathsep) if item]


def load_settings() -> AppConfig:
    """从环境变量加载 agent-server 配置。"""
    return AppConfig(
        server=ServerConfig(
            host=os.getenv('AGENT_SERVER_HOST', '0.0.0.0'),
            port=_get_int('AGENT_SERVER_PORT', 8888),
        ),
        llm=LLMConfig(
            provider=os.getenv('AGENT_SERVER_LLM_PROVIDER', 'deepseek'),
        ),
        session=SessionConfig(
            max_tool_rounds=_get_int('AGENT_SERVER_SESSION_MAX_TOOL_ROUNDS', 10),
            tool_timeout_sec=_get_float('AGENT_SERVER_SESSION_TOOL_TIMEOUT_SEC', 30.0),
            history_max_messages=_get_int('AGENT_SERVER_SESSION_HISTORY_MAX_MESSAGES', 50),
        ),
        auth=AuthConfig(
            db_url=os.getenv('AGENT_SERVER_AUTH_DB_URL', 'sqlite+aiosqlite:///tokens.db'),
        ),
        plugin=PluginSettings(
            external_dirs=_get_paths('AGENT_SERVER_PLUGIN_EXTERNAL_DIRS', ['/plugins']),
        ),
        timezone=os.getenv('AGENT_SERVER_TIMEZONE', 'UTC'),
    )
