"""Catalog repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.reference import CatalogItem
from src.repositories import BaseRepository


class CatalogRepository(BaseRepository[CatalogItem]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, CatalogItem)

    async def get_published(self) -> list[CatalogItem]:
        stmt = select(CatalogItem).where(CatalogItem.is_published).order_by(CatalogItem.sort_order)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_ordered(self) -> list[CatalogItem]:
        stmt = select(CatalogItem).order_by(CatalogItem.sort_order)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
