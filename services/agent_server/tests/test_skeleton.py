from fastapi.testclient import TestClient

from main import app


def test_骨架仅提供健康检查():
    with TestClient(app) as client:
        response = client.get('/health')
        assert response.status_code == 200, '健康检查应成功'
        assert response.json() == {'status': 'ok'}, '健康检查响应应稳定'
        assert client.post('/chat', json={}).status_code == 404, '骨架不应暴露旧聊天接口'
