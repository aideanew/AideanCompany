# -*- coding: utf-8 -*-
"""信源仓储 - 负责信息源持久化与查询"""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import KnowledgeSource


class SourceRepository:
    """信源仓储类"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, source: KnowledgeSource) -> KnowledgeSource:
        """创建信源"""
        self.db.add(source)
        await self.db.flush()
        await self.db.refresh(source)
        return source

    async def get_by_id(self, source_id: UUID) -> Optional[KnowledgeSource]:
        """根据 ID 查找信源"""
        result = await self.db.execute(
            select(KnowledgeSource).where(KnowledgeSource.id == source_id)
        )
        return result.scalar_one_or_none()

    async def get_by_wechat_id(
        self,
        wechat_id: str,
    ) -> Optional[KnowledgeSource]:
        """根据微信 ID 查找信源"""
        result = await self.db.execute(
            select(KnowledgeSource).where(KnowledgeSource.wechat_id == wechat_id)
        )
        return result.scalar_one_or_none()

    async def get_by_space(
        self,
        space_id: UUID,
    ) -> List[KnowledgeSource]:
        """根据空间 ID 查找信源"""
        result = await self.db.execute(
            select(KnowledgeSource).where(KnowledgeSource.space_id == space_id)
        )
        return result.scalars().all()

    async def update(
        self,
        source_id: UUID,
        **kwargs,
    ) -> Optional[KnowledgeSource]:
        """更新信源"""
        result = await self.db.execute(
            select(KnowledgeSource).where(KnowledgeSource.id == source_id)
        )
        source = result.scalar_one_or_none()
        if not source:
            return None

        for key, value in kwargs.items():
            if hasattr(source, key):
                setattr(source, key, value)

        await self.db.flush()
        await self.db.refresh(source)
        return source
EOF
__zcode_status=$?
if [ "$__zcode_status" -eq 0 ]; then pwd -P > '/c/Users/EDY/AppData/Local/Temp/zcode-bb46d492-479b-4ab9-a6de-b88e22d9ffad-cwd'; fi
exit "$__zcode_status"
