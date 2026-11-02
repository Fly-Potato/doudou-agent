import hashlib
import secrets
import sqlite3
from contextlib import closing, contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field


class User(BaseModel):
    user_id: str
    name: str
    created_at: datetime
    active: bool


class IssuedKey(User):
    key: str = Field(repr=False)


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def generate_key() -> str:
    return 'du_' + secrets.token_urlsafe(32)


class UserStore:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        path.touch(mode=0o600, exist_ok=True)
        with self.connect() as connection:
            connection.execute(
                'CREATE TABLE IF NOT EXISTS users ('
                'user_id TEXT PRIMARY KEY, name TEXT NOT NULL, '
                'created_at TEXT NOT NULL, key_hash TEXT UNIQUE)'
            )
            # 保持版本值不变，实际写入数据库页以验证文件与目录的写权限。
            version = connection.execute('PRAGMA user_version').fetchone()[0]
            connection.execute(f'PRAGMA user_version = {version}')

    @contextmanager
    def connect(self):
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.row_factory = sqlite3.Row
            yield connection

    def create(self, name: str, key: str) -> User:
        user = User(user_id=str(uuid4()), name=name, created_at=datetime.now(UTC), active=True)
        with self.connect() as connection:
            connection.execute(
                'INSERT INTO users (user_id, name, created_at, key_hash) VALUES (?, ?, ?, ?)',
                (user.user_id, user.name, user.created_at.isoformat(), hash_key(key)),
            )
        return user

    def list_users(self) -> list[User]:
        with self.connect() as connection:
            rows = connection.execute(
                'SELECT user_id, name, created_at, key_hash IS NOT NULL AS active '
                'FROM users ORDER BY created_at, user_id'
            ).fetchall()
        return [User.model_validate(dict(row)) for row in rows]

    def find_user_id(self, key_hash: str) -> str | None:
        with self.connect() as connection:
            row = connection.execute(
                'SELECT user_id FROM users WHERE key_hash = ?', (key_hash,)
            ).fetchone()
        return row['user_id'] if row else None

    def set_key(self, user_id: str, key_hash: str | None) -> User | None:
        with self.connect() as connection:
            updated = connection.execute(
                'UPDATE users SET key_hash = ? WHERE user_id = ?', (key_hash, user_id)
            )
            if not updated.rowcount:
                return None
            row = connection.execute(
                'SELECT user_id, name, created_at, key_hash IS NOT NULL AS active '
                'FROM users WHERE user_id = ?',
                (user_id,),
            ).fetchone()
        return User.model_validate(dict(row))
