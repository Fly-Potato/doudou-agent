from __future__ import annotations

import pytest

from settings import load_settings


def test_环境变量覆盖服务配置(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('AGENT_SERVER_HOST', '127.0.0.1')
    monkeypatch.setenv('AGENT_SERVER_PORT', '8888')
    monkeypatch.setenv('AGENT_SERVER_LLM_PROVIDER', 'openai')
    monkeypatch.setenv('AGENT_SERVER_SESSION_MAX_TOOL_ROUNDS', '4')
    monkeypatch.setenv('AGENT_SERVER_SESSION_TOOL_TIMEOUT_SEC', '12.5')
    monkeypatch.setenv('AGENT_SERVER_SESSION_HISTORY_MAX_MESSAGES', '20')
    monkeypatch.setenv('AGENT_SERVER_AUTH_DB_URL', 'sqlite+aiosqlite:///test.db')
    monkeypatch.setenv('AGENT_SERVER_TIMEZONE', 'Asia/Shanghai')
    monkeypatch.setenv('AGENT_SERVER_PLUGIN_EXTERNAL_DIRS', '/plugins;C:\\plugins')

    config = load_settings()

    assert config.server.host == '127.0.0.1'
    assert config.server.port == 8888
    assert config.llm.provider == 'openai'
    assert config.session.max_tool_rounds == 4
    assert config.session.tool_timeout_sec == 12.5
    assert config.session.history_max_messages == 20
    assert config.auth.db_url == 'sqlite+aiosqlite:///test.db'
    assert config.timezone == 'Asia/Shanghai'
    assert config.plugin.external_dirs == ['/plugins', 'C:\\plugins']


def test_未设置环境变量时使用默认配置(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        'AGENT_SERVER_HOST',
        'AGENT_SERVER_PORT',
        'AGENT_SERVER_LLM_PROVIDER',
        'AGENT_SERVER_SESSION_MAX_TOOL_ROUNDS',
        'AGENT_SERVER_SESSION_TOOL_TIMEOUT_SEC',
        'AGENT_SERVER_SESSION_HISTORY_MAX_MESSAGES',
        'AGENT_SERVER_AUTH_DB_URL',
        'AGENT_SERVER_TIMEZONE',
        'AGENT_SERVER_PLUGIN_EXTERNAL_DIRS',
    ):
        monkeypatch.delenv(name, raising=False)

    config = load_settings()

    assert config.server.host == '0.0.0.0'
    assert config.server.port == 8888
    assert config.llm.provider == 'deepseek'
    assert config.session.max_tool_rounds == 10
    assert config.session.tool_timeout_sec == 30.0
    assert config.session.history_max_messages == 50
    assert config.auth.db_url == 'sqlite+aiosqlite:///tokens.db'
    assert config.timezone == 'UTC'
    assert config.plugin.external_dirs == ['/plugins']


def test_非法数字环境变量给出中文错误(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('AGENT_SERVER_PORT', 'not-a-port')

    with pytest.raises(ValueError, match='AGENT_SERVER_PORT.*整数'):
        load_settings()
