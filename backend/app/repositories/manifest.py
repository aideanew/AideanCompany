# -*- coding: utf-8 -*-
"""清单仓储 - 负知识清单持久化与查询"""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import KnowledgeManifest


class ManifestRepository:
    """清单仓储类"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, manifest: KnowledgeManifest) -> KnowledgeManifest:
        """创建清单"""
        self.db.add(manifest)
        await self.db.flush()
        await self.db.refresh(manifest)
        return manifest

    async def get_by_id(self, manifest_id: UUID) -> Optional[KnowledgeManifest]:
        """根据 ID 查找清单"""
        result = await self.db.execute(
            select(KnowledgeManifest).where(KnowledgeManifest.id == manifest_id)
        )
        return result.scalar_one_or_none()

    async def get_by_source(
        self,
        source_id: UUID,
    ) -> List[KnowledgeManifest]:
        """根据信源 ID 查找清单"""
        result = await self.db.execute(
            select(KnowledgeManifest)
            .where(KnowledgeManifest.source_id == source_id)
            .order_by(desc(KnowledgeManifest.fetched_at))
        )
        return result.scalars().all()

    async def get_latest_by_source(
        self,
        source_id: UUID,
    ) -> Optional[KnowledgeManifest]:
        """获取信源的最新清单"""
        result = await self.db.execute(
            select(KnowledgeManifest)
            .where(KnowledgeManifest.source_id == source_id)
            .order_by(desc(KnowledgeManifest.fetched_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def update(
        self,
        manifest_id: UUID,
        **kwargs,
    ) -> Optional[KnowledgeManifest]:
        """更新清单"""
        result = await self.db.execute(
            select(KnowledgeManifest).where(KnowledgeManifest.id == manifest_id)
        )
        manifest = result.scalar_one_or_none()
        if not manifest:
            return None

        for key, value in kwargs.items():
            if hasattr(manifest, key):
                setattr(manifest, key, value)

        await self.db.flush()
        await self.db.refresh(manifest)
        return manifest
EOF
__zcode_status=$?
if [ "$__zcode_status" -eq 0 ]; then pwd -P > '/c/Users/EDY/AppData/Local/Temp/zcode-7d10ddea-ae17-41c2-a192-bd58e5f27169-cwd'; fi
exit "$__zcode_status"
