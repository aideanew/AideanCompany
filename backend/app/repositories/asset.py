# -*- coding: utf-8 -*-
"""资产仓储 - 负责知识资产持久化与查询"""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import KnowledgeAsset


class AssetRepository:
    """资产仓储类"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, asset: KnowledgeAsset) -> KnowledgeAsset:
        """创建资产"""
        self.db.add(asset)
        await self.db.flush()
        await self.db.refresh(asset)
        return asset

    async def get_by_id(self, asset_id: UUID) -> Optional[KnowledgeAsset]:
        """根据 ID 查找资产"""
        result = await self.db.execute(
            select(KnowledgeAsset).where(KnowledgeAsset.id == asset_id)
        )
        return result.scalar_one_or_none()

    async def get_by_doc_id(self, doc_id: UUID) -> Optional[KnowledgeAsset]:
        """根据文档 ID 查找资产"""
        result = await self.db.execute(
            select(KnowledgeAsset).where(KnowledgeAsset.doc_id == doc_id)
        )
        return result.scalar_one_or_none()

    async def get_by_space(
        self,
        space_id: UUID,
    ) -> List[KnowledgeAsset]:
        """根据空间 ID 查找资产"""
        result = await self.db.execute(
            select(KnowledgeAsset).where(KnowledgeAsset.space_id == space_id)
        )
        return result.scalars().all()

    async def update(
        self,
        asset_id: UUID,
        **kwargs,
    ) -> Optional[KnowledgeAsset]:
        """更新资产"""
        result = await self.db.execute(
            select(KnowledgeAsset).where(KnowledgeAsset.id == asset_id)
        )
        asset = result.scalar_one_or_none()
        if not asset:
            return None

        for key, value in kwargs.items():
            if hasattr(asset, key):
                setattr(asset, key, value)

        await self.db.flush()
        await self.db.refresh(asset)
        return asset
EOF
__zcode_status=$?
if [ "$__zcode_status" -eq 0 ]; then pwd -P > '/c/Users/EDY/AppData/Local/Temp/zcode-653a7f14-2300-4b98-b553-e38def9138f8-cwd'; fi
exit "$__zcode_status"
