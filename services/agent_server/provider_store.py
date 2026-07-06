from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import ProviderProfile


class ProviderStore:
    async def get_by_name(self, session: AsyncSession, name: str) -> ProviderProfile | None:
        result = await session.execute(select(ProviderProfile).where(ProviderProfile.name == name))
        return result.scalar_one_or_none()

    async def get_default(self, session: AsyncSession) -> ProviderProfile | None:
        result = await session.execute(
            select(ProviderProfile).where(ProviderProfile.is_default == True)  # noqa: E712
        )
        return result.scalar_one_or_none()
