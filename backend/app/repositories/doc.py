# -*- coding: utf-8 -*-
"""文档仓储 - 负责知识文档持久化与查询"""
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import KnowledgeDoc


class DocRepository:
    """文档仓储类"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, doc: KnowledgeDoc) -> KnowledgeDoc:
        """创建文档"""
        self.db.add(doc)
        await self.db.flush()
        await self.db.refresh(doc)
        return doc

    async def get_by_id(self, doc_id: UUID) -> Optional[KnowledgeDoc]:
        """根据 ID 查找文档"""
        result = await self.db.execute(
            select(KnowledgeDoc).where(KnowledgeDoc.id == doc_id)
        )
        return result.scalar_one_or_none()

    async def get_by_content_hash(
        self,
        content_hash: str,
        space_id: UUID,
    ) -> Optional[KnowledgeDoc]:
        """根据内容哈希和空间 ID 查找文档（用于去重）"""
        result = await self.db.execute(
            select(KnowledgeDoc)
            .where(
                and_(
                    KnowledgeDoc.content_hash == content_hash,
                    KnowledgeDoc.space_id == space_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_by_space(
        self,
        space_id: UUID,
        status: Optional[str] = None,
    ) -> List[KnowledgeDoc]:
        """根据空间 ID 查找文档"""
        stmt = select(KnowledgeDoc).where(KnowledgeDoc.space_id == space_id)

        if status:
            stmt = stmt.where(KnowledgeDoc.status == status)

        result = await self.db.execute(
            stmt.order_by(desc(KnowledgeDoc.updated_at))
        )
        return result.scalars().all()

    async def increment_hit_count(
        self,
        doc_id: UUID,
    ) -> KnowledgeDoc:
        """增加文档命中计数"""
        result = await self.db.execute(
            select(KnowledgeDoc).where(KnowledgeDoc.id == doc_id)
        )
        doc = result.scalar_one_or_none()
        if not doc:
            return None

        doc.hit_count += 1
        await self.db.flush()
        await self.db.refresh(doc)
        return doc

    async def update(
        self,
        doc_id: UUID,
        **kwargs,
    ) -> Optional[KnowledgeDoc]:
        """更新文档"""
        result = await self.db.execute(
            select(KnowledgeDoc).where(KnowledgeDoc.id == doc_id)
        )
        doc = result.scalar_one_or_none()
        if not doc:
            return None

        for key, value in kwargs.items():
            if hasattr(doc, key):
                setattr(doc, key, value)

        await self.db.flush()
        await self.db.refresh(doc)
        return doc
EOF
__zcode_status=$?
if [ "$__zcode_status" -eq 0 ]; then pwd -P > '/c/Users/EDY/AppData/Local/Temp/zcode-1a809a64-a926-4e4a-8b0b-ae7c05a1afe3-cwd'; fi
exit "$__zcode_status"
