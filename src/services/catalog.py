"""Catalog service."""


from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums import UserRole
from src.core.exceptions import NotFoundError, PermissionDeniedError
from src.db.models.reference import CatalogItem
from src.db.models.users import User
from src.repositories.catalog import CatalogRepository


class CatalogService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.catalog = CatalogRepository(session)

    async def list_published(self) -> list[CatalogItem]:
        return await self.catalog.get_published()

    async def list_all(self) -> list[CatalogItem]:
        return await self.catalog.get_all_ordered()

    async def create(self, actor: User, title: str, description: str, price_text: str | None, sort_order: int) -> CatalogItem:
        if actor.role not in (UserRole.OWNER, UserRole.MANAGER):
            raise PermissionDeniedError("create_catalog")
        item = await self.catalog.create(
            title=title,
            description=description,
            price_text=price_text,
            sort_order=sort_order,
            is_published=False,
        )
        await self.session.commit()
        return item

    async def update(self, actor: User, item_id: int, **fields) -> CatalogItem:
        if actor.role not in (UserRole.OWNER, UserRole.MANAGER):
            raise PermissionDeniedError("update_catalog")
        item = await self.catalog.get(item_id)
        if not item:
            raise NotFoundError("CatalogItem", item_id)
        for k, v in fields.items():
            setattr(item, k, v)
        await self.session.commit()
        return item

    async def delete(self, actor: User, item_id: int) -> None:
        if actor.role not in (UserRole.OWNER, UserRole.MANAGER):
            raise PermissionDeniedError("delete_catalog")
        item = await self.catalog.get(item_id)
        if not item:
            raise NotFoundError("CatalogItem", item_id)
        await self.catalog.delete(item)
        await self.session.commit()
