from __future__ import annotations

import importlib

import pytest


def test_环境变量覆盖服务配置(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('AGENT_SERVER_SESSION_MAX_TOOL_ROUNDS', '4')
    monkeypatch.setenv('AGENT_SERVER_SESSION_TOOL_TIMEOUT_SEC', '12.5')
    monkeypatch.setenv('AGENT_SERVER_SESSION_HISTORY_MAX_MESSAGES', '20')
    monkeypatch.setenv('AGENT_SERVER_AUTH_DB_URL', 'sqlite+aiosqlite:///test.db')
    monkeypatch.setenv('AGENT_SERVER_TIMEZONE', 'Asia/Shanghai')

    import settings

    settings = importlib.reload(settings)

    assert settings.MAX_TOOL_ROUNDS == 4
    assert settings.TOOL_TIMEOUT_SEC == 12.5
    assert settings.HISTORY_MAX_MESSAGES == 20
    assert settings.AUTH_DB_URL == 'sqlite+aiosqlite:///test.db'
    assert settings.TIMEZONE == 'Asia/Shanghai'


def test_未设置环境变量时使用默认配置(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        'AGENT_SERVER_SESSION_MAX_TOOL_ROUNDS',
        'AGENT_SERVER_SESSION_TOOL_TIMEOUT_SEC',
        'AGENT_SERVER_SESSION_HISTORY_MAX_MESSAGES',
        'AGENT_SERVER_AUTH_DB_URL',
        'AGENT_SERVER_TIMEZONE',
    ):
        monkeypatch.delenv(name, raising=False)

    import settings

    settings = importlib.reload(settings)

    assert settings.MAX_TOOL_ROUNDS == 10
    assert settings.TOOL_TIMEOUT_SEC == 30.0
    assert settings.HISTORY_MAX_MESSAGES == 50
    assert settings.AUTH_DB_URL == 'sqlite+aiosqlite:///tokens.db'
    assert settings.TIMEZONE == 'UTC'
    assert not hasattr(settings, 'HOST')
    assert not hasattr(settings, 'PORT')
    assert not hasattr(settings, 'LLM_PROVIDER')
    assert not hasattr(settings, 'PLUGIN_EXTERNAL_DIRS')


def test_非法数字环境变量给出中文错误(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('AGENT_SERVER_SESSION_MAX_TOOL_ROUNDS', 'not-a-number')

    import settings

    with pytest.raises(ValueError, match='AGENT_SERVER_SESSION_MAX_TOOL_ROUNDS.*整数'):
        importlib.reload(settings)
