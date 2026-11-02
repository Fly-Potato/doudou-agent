import logging
import os
import secrets
import sqlite3

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from main import create_app


class AuthHeaders(dict):
    # 断言失败时也不能在测试输出中暴露凭据。
    def __repr__(self):
        return "{'Authorization': '[已脱敏]'}"


def headers(key):
    return AuthHeaders(Authorization=f'Bearer {key.get_secret_value()}')


@pytest.fixture
def configured(monkeypatch, tmp_path):
    admin = SecretStr(secrets.token_urlsafe(32))
    db = tmp_path / 'users.db'
    monkeypatch.setenv('AGENT_SERVER_ADMIN_KEY', admin.get_secret_value())
    monkeypatch.setenv('AGENT_SERVER_DB_PATH', str(db))
    return admin, db


@pytest.fixture
def client(configured):
    with TestClient(create_app(), base_url='https://testserver') as client:
        yield client


def create_user(client, admin, name='测试用户'):
    response = client.post('/admin/users', headers=headers(admin), json={'name': name})
    assert response.status_code == 201, '管理员应能创建用户'
    body = response.json()
    key = SecretStr(body.pop('key'))
    return body, key


@pytest.mark.parametrize('value', [None, '', '不足长度', ' ' * 32, '密' * 32, 'A' * 32 + '\n'])
def test_管理员密钥缺失或过短时拒绝启动(monkeypatch, tmp_path, value):
    monkeypatch.delenv('AGENT_SERVER_ADMIN_KEY', raising=False)
    if value is not None:
        monkeypatch.setenv('AGENT_SERVER_ADMIN_KEY', value)
    monkeypatch.setenv('AGENT_SERVER_DB_PATH', str(tmp_path / 'users.db'))
    with pytest.raises(RuntimeError, match='AGENT_SERVER_ADMIN_KEY'):
        with TestClient(create_app(), base_url='https://testserver'):
            pytest.fail('缺少安全管理员密钥时不应启动')


def test_匿名错误凭据和查询参数不能认证(client, configured):
    admin, _ = configured
    wrong = SecretStr(secrets.token_urlsafe(32))
    for auth in [{}, headers(wrong), {'Authorization': 'Basic invalid'}]:
        response = client.get('/auth/me', headers=auth)
        assert response.status_code == 401, '无效凭据应拒绝认证'
        assert response.headers['www-authenticate'] == 'Bearer', '应声明认证方式'
    response = client.get('/auth/me', params={'key': '不接受查询参数认证'})
    assert response.status_code == 401, '查询参数不应作为认证凭据'
    assert client.get('/health').status_code == 200, '健康检查应可匿名访问'


def test_管理员与用户身份隔离(client, configured):
    admin, _ = configured
    first, first_key = create_user(client, admin, '用户甲')
    second, second_key = create_user(client, admin, '用户乙')
    assert first['user_id'] != second['user_id'], '不同密钥应对应独立用户'
    assert client.get('/auth/me', headers=headers(admin)).json() == {
        'role': 'admin',
        'user_id': None,
    }, '应识别管理员身份'
    for user, key in [(first, first_key), (second, second_key)]:
        response = client.get('/auth/me', headers=headers(key))
        assert response.json() == {'role': 'user', 'user_id': user['user_id']}, '身份应来自密钥'
        for method, path, kwargs in [
            ('GET', '/admin/users', {}),
            ('POST', '/admin/users', {'json': {'name': '越权'}}),
            ('POST', f'/admin/users/{second["user_id"]}/key', {}),
            ('DELETE', f'/admin/users/{second["user_id"]}/key', {}),
        ]:
            response = client.request(method, path, headers=headers(key), **kwargs)
            assert response.status_code == 403, '普通密钥不得访问管理接口'


def test_重置密钥保留身份且旧密钥立即失效(client, configured):
    admin, _ = configured
    user, old_key = create_user(client, admin)
    response = client.post(f'/admin/users/{user["user_id"]}/key', headers=headers(admin))
    assert response.status_code == 200, '重置应成功'
    rotated = response.json()
    new_key = SecretStr(rotated.pop('key'))
    assert rotated == user, '重置不应改变用户身份或元数据'
    assert client.get('/auth/me', headers=headers(old_key)).status_code == 401, '旧密钥应立即失效'
    assert client.get('/auth/me', headers=headers(new_key)).json()['user_id'] == user['user_id'], (
        '新密钥应关联原用户'
    )


def test_撤销密钥保留用户且可重新生成(client, configured):
    admin, _ = configured
    user, key = create_user(client, admin)
    path = f'/admin/users/{user["user_id"]}/key'
    assert client.delete(path, headers=headers(admin)).status_code == 204, '应能撤销密钥'
    assert client.get('/auth/me', headers=headers(key)).status_code == 401, '已撤销密钥应失效'
    users = client.get('/admin/users', headers=headers(admin)).json()
    assert users[0]['user_id'] == user['user_id'], '撤销不应删除用户'
    assert users[0]['active'] is False, '应标记用户当前无有效密钥'
    response = client.post(path, headers=headers(admin))
    new_key = SecretStr(response.json()['key'])
    assert client.get('/auth/me', headers=headers(new_key)).status_code == 200, '应能重新启用用户'


def test_重启后身份持久且数据库和响应不泄露密钥(client, configured, caplog):
    admin, db = configured
    with caplog.at_level(logging.DEBUG):
        user, key = create_user(client, admin)
        response = client.get('/admin/users', headers=headers(admin))
        assert response.headers['cache-control'] == 'no-store', '身份响应不得缓存'
        assert set(response.json()[0]) == {'user_id', 'name', 'created_at', 'active'}, (
            '列表只能包含非敏感用户元数据'
        )
        rejected = client.get('/auth/me', headers=headers(SecretStr(secrets.token_urlsafe(32))))
        assert rejected.status_code == 401, '错误凭据应拒绝且不泄露密钥'
    with TestClient(create_app(), base_url='https://testserver') as restarted:
        response = restarted.get('/auth/me', headers=headers(key))
        assert response.json()['user_id'] == user['user_id'], '重启后应保留用户身份'
    content = db.read_bytes()
    assert all(k.get_secret_value().encode() not in content for k in [admin, key]), (
        '数据库不得保存原始密钥'
    )
    assert all(k.get_secret_value() not in caplog.text for k in [admin, key]), '日志不得输出密钥'
    with sqlite3.connect(db) as connection:
        row = connection.execute('SELECT key_hash FROM users').fetchone()
        assert len(row[0]) == 64, '应只保存密钥哈希'


def test_输入与不存在用户的边界(client, configured):
    admin, _ = configured
    for name in ['', '   ', '长' * 81]:
        response = client.post('/admin/users', headers=headers(admin), json={'name': name})
        assert response.status_code == 422, '名称应非空且有长度限制'
    for method in ['POST', 'DELETE']:
        response = client.request(method, '/admin/users/missing/key', headers=headers(admin))
        assert response.status_code == 404, '不存在的用户应返回明确错误'


def test_管理员轮换不改变普通用户(configured, monkeypatch):
    original_admin, _ = configured
    with TestClient(create_app(), base_url='https://testserver') as client:
        user, key = create_user(client, original_admin)
    replacement = SecretStr(secrets.token_urlsafe(32))
    monkeypatch.setenv('AGENT_SERVER_ADMIN_KEY', replacement.get_secret_value())
    with TestClient(create_app(), base_url='https://testserver') as client:
        assert client.get('/auth/me', headers=headers(original_admin)).status_code == 401, (
            '重启轮换管理员密钥后旧密钥应失效'
        )
        assert client.get('/admin/users', headers=headers(replacement)).status_code == 200, (
            '新管理员密钥应有效'
        )
        assert client.get('/auth/me', headers=headers(key)).json()['user_id'] == user['user_id'], (
            '管理员密钥轮换不应影响用户'
        )


def test_不安全传输被拒绝但本机开发可用(configured):
    admin, _ = configured
    with TestClient(create_app(), base_url='http://testserver') as remote:
        response = remote.get('/auth/me', headers=headers(admin))
        assert response.status_code == 403, '远程认证必须通过 HTTPS'
    with TestClient(create_app(), client=('127.0.0.1', 50000)) as local:
        assert local.get('/auth/me', headers=headers(admin)).status_code == 200, (
            '回环地址应允许本机开发'
        )


def test_存储不可用时拒绝启动(configured, monkeypatch, tmp_path):
    blocker = tmp_path / '不是目录'
    blocker.write_text('阻止创建数据库目录')
    monkeypatch.setenv('AGENT_SERVER_DB_PATH', str(blocker / 'users.db'))
    with pytest.raises(OSError):
        with TestClient(create_app()):
            pytest.fail('数据库不可用时不能静默跳过认证')


@pytest.mark.skipif(
    os.name != 'posix' or os.geteuid() == 0, reason='目录权限测试需要非 root 的 POSIX 环境'
)
def test_已有数据库目录不可写时拒绝启动(configured):
    _, db = configured
    with TestClient(create_app()):
        pass
    db.parent.chmod(0o500)
    try:
        with pytest.raises(sqlite3.OperationalError):
            with TestClient(create_app()):
                pytest.fail('已有库无法写入时必须在启动阶段失败')
    finally:
        db.parent.chmod(0o700)
