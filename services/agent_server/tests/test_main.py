from __future__ import annotations

import argparse

import pytest
from pydantic import ValidationError

from main import ChatRequest, build_parser, serve_cmd


def test_chat请求必须显式提供_provider() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(session_id='s1', content='你好')


def test_serve命令必须提供_host和_port() -> None:
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(['serve'])

    args = parser.parse_args(['serve', '--host', '127.0.0.1', '--port', '9000'])

    assert args.host == '127.0.0.1'
    assert args.port == 9000


def test_serve命令使用传入的_host和_port(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(app: str, **kwargs: object) -> None:
        captured['app'] = app
        captured.update(kwargs)

    monkeypatch.setattr('uvicorn.run', fake_run)

    serve_cmd(argparse.Namespace(host='127.0.0.1', port=9000))

    assert captured == {
        'app': 'main:app',
        'host': '127.0.0.1',
        'port': 9000,
        'reload': True,
    }
