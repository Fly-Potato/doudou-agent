from __future__ import annotations

import zoneinfo
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


# 模块级时区，由 configure_timezone() 初始化
_configured_tz = zoneinfo.ZoneInfo('UTC')


def configure_timezone(tz_name: str) -> None:
    """由 main.py 在启动时调用，设置 ORM 模型使用的时区"""
    global _configured_tz
    _configured_tz = zoneinfo.ZoneInfo(tz_name)


def _now() -> datetime:
    """使用配置的时区返回当前时间"""
    return datetime.now(_configured_tz)


class Token(Base):
    __tablename__ = 'tokens'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
    )


class ProviderProfile(Base):
    __tablename__ = 'provider_profiles'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    api_key: Mapped[str] = mapped_column(String(256), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
    )
