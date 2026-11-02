import secrets

from fastapi.testclient import TestClient

from main import app


def test_健康检查不需要认证且不恢复旧聊天接口(monkeypatch, tmp_path):
    monkeypatch.setenv('AGENT_SERVER_ADMIN_KEY', secrets.token_urlsafe(32))
    monkeypatch.setenv('AGENT_SERVER_DB_PATH', str(tmp_path / 'users.db'))
    with TestClient(app, base_url='https://testserver') as client:
        response = client.get('/health')
        assert response.status_code == 200, '健康检查应成功'
        assert response.json() == {'status': 'ok'}, '健康检查响应应稳定'
        assert client.post('/chat', json={}).status_code == 404, '骨架不应暴露旧聊天接口'
