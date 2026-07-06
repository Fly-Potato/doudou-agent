from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class ServerConfig:
    host: str = '0.0.0.0'
    port: int = 8000


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
    db_url: str = ''


@dataclass
class PluginSettings:
    external_dirs: list[str] = field(default_factory=list)


@dataclass
class AppConfig:
    server: ServerConfig = field(default_factory=ServerConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    session: SessionConfig = field(default_factory=SessionConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    plugin: PluginSettings = field(default_factory=PluginSettings)
    timezone: str = 'UTC'  # ORM 默认时区，例如 'Asia/Shanghai'


def _substitute_env_vars(text: str) -> str:
    def replacer(match: re.Match[str]) -> str:
        return os.environ.get(match.group(1), '')

    return re.sub(r'\$\{(\w+)\}', replacer, text)


def load_config(path: str = 'agent-server.yaml') -> AppConfig:
    config_path = Path(path)
    if not config_path.exists():
        return AppConfig()

    raw = config_path.read_text(encoding='utf-8')
    raw = _substitute_env_vars(raw)
    data = yaml.safe_load(raw) or {}

    app = AppConfig()

    if 'server' in data:
        s = data['server']
        app.server = ServerConfig(host=s.get('host', '0.0.0.0'), port=s.get('port', 8000))

    if 'llm' in data:
        llm = data['llm']
        app.llm = LLMConfig(
            provider=llm.get('provider', 'deepseek'),
        )

    if 'session' in data:
        sess = data['session']
        app.session = SessionConfig(
            max_tool_rounds=sess.get('max_tool_rounds', 10),
            tool_timeout_sec=sess.get('tool_timeout_sec', 30.0),
            history_max_messages=sess.get('history_max_messages', 50),
        )

    if 'auth' in data:
        a = data['auth']
        app.auth = AuthConfig(db_url=a.get('db_url', ''))

    if 'plugin' in data:
        p = data['plugin']
        app.plugin = PluginSettings(
            external_dirs=p.get('external_dirs', []),
        )

    if 'timezone' in data:
        app.timezone = data['timezone']

    return app
