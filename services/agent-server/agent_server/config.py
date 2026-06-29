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
    type: str = 'openai'
    model: str = 'gpt-4o'
    base_url: str = 'https://api.openai.com/v1'
    api_key: str = ''


@dataclass
class SessionConfig:
    max_tool_rounds: int = 10
    tool_timeout_sec: float = 30.0
    history_max_messages: int = 50


@dataclass
class AuthConfig:
    token_hash: str = ''


@dataclass
class PluginConfig:
    name: str
    enabled: bool = True
    config: dict = field(default_factory=dict)


@dataclass
class AppConfig:
    server: ServerConfig = field(default_factory=ServerConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    session: SessionConfig = field(default_factory=SessionConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    plugins: list[PluginConfig] = field(default_factory=list)


def _substitute_env_vars(text: str) -> str:
    def replacer(match: re.Match[str]) -> str:
        return os.environ.get(match.group(1), '')

    return re.sub(r'\$\{(\w+)\}', replacer, text)


def _apply_env_defaults(config: AppConfig) -> AppConfig:
    if not config.llm.api_key:
        config.llm.api_key = os.environ.get('OPENAI_API_KEY', '')
    return config


def load_config(path: str = 'agent-server.yaml') -> AppConfig:
    config_path = Path(path)
    if not config_path.exists():
        return _apply_env_defaults(AppConfig())

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
            type=llm.get('type', 'openai'),
            model=llm.get('model', 'gpt-4o'),
            base_url=llm.get('base_url', 'https://api.openai.com/v1'),
            api_key=llm.get('api_key', ''),
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
        app.auth = AuthConfig(token_hash=a.get('token_hash', ''))

    if 'plugins' in data:
        app.plugins = [
            PluginConfig(
                name=p['name'],
                enabled=p.get('enabled', True),
                config=p.get('config', {}),
            )
            for p in data['plugins']
            if isinstance(p, dict) and 'name' in p
        ]

    return _apply_env_defaults(app)
