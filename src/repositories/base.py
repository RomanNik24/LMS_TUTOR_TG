from typing import Generic, TypeVar, Type, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from src.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)

class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def create(self, session: AsyncSession, **kwargs: Any) -> ModelType:
        """Создает новую запись в базе данных"""
        obj = self.model(**kwargs)
        session.add(obj)
        await session.flush()
        await session.refresh(obj)
        return obj

    async def get_by_id(self, session: AsyncSession, id: int) -> Optional[ModelType]:
        """Возвращает запись по ее ID"""
        stmt = select(self.model).where(self.model.id == id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, session: AsyncSession, id: int, **kwargs: Any) -> Optional[ModelType]:
        """Обновляет запись по ID и возвращает обновленный объект"""
        stmt = update(self.model).where(self.model.id == id).values(**kwargs).returning(self.model)
        result = await session.execute(stmt)
        await session.flush()
        return result.scalar_one_or_none()

    async def delete(self, session: AsyncSession, id: int) -> bool:
        """Удаляет запись по ID. Возвращает True если запись была удалена"""
        stmt = delete(self.model).where(self.model.id == id)
        result = await session.execute(stmt)
        await session.flush()
        return result.rowcount > 0
