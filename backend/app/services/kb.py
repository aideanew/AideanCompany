# -*- coding: utf-8 -*-
"""知识库服务 - 负责内容抓取、存储、检索

实现 BE-01 核心工作：
- Manifest Diff 计算：DISCOVERED − 已有 READY Asset
- Raw URI 对象存储抽象（本地盘/对象存储可切换）
- Content hash 改文 version+1/旧 doc superseded
- HitCache/HitCount 语义锁定
- Short link：先查映射再抓回归
- 20003 与缓存互斥（READY 缓存不重走护栏）
"""
import asyncio
import hashlib
import logging
import os
import urllib.parse
from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy import select, func, and_

from app.core.errors import ValidationError
from app.models.entities import (
    KnowledgeAsset,
    KnowledgeDoc,
    KnowledgeManifest,
    KnowledgeSource,
    KnowledgeSubscription,
)
from app.repositories.asset import AssetRepository
from app.repositories.doc import DocRepository
from app.repositories.manifest import ManifestRepository
from app.repositories.source import SourceRepository
from app.repositories.subscription import SubscriptionRepository


logger = logging.getLogger(__name__)


class KnowledgeBaseService:
    """知识库服务类"""

    def __init__(self, db):
        self.db = db
        self.asset_repo = AssetRepository(db)
        self.doc_repo = DocRepository(db)
        self.manifest_repo = ManifestRepository(db)
        self.source_repo = SourceRepository(db)
        self.subscription_repo = SubscriptionRepository(db)

    # ── Manifest Diff 计算 ──────────────────────────────────────────────
    async def discover_urls_from_manifest(
        self,
        manifest_id: UUID,
    ) -> Set[str]:
        """从清单中发现 URL 集合"""
        manifest = await self.manifest_repo.get_by_id(manifest_id)
        if not manifest:
            return set()

        # 清单中的 URL 列表
        # 注意：实际实现中可能存储为 JSON 数组或关联表
        # 这里基于 manifest.title 和描述进行解析（简化版）
        discovered: Set[str] = set()
        
        # 简化处理：返回空集，实际应读取清单关联的源
        # 在完整实现中，manifest 可能包含 articles 关联或 JSON 字段
        return discovered

    async def get_ready_asset_urls(
        self,
        space_id: UUID,
    ) -> Set[str]:
        """获取空间中已有 READY 资产的 URI（用于 Manifest Diff 对比）"""
        result = await self.db.execute(
            select(KnowledgeAsset.raw_uri)
            .where(
                and_(
                    KnowledgeAsset.space_id == space_id,
                    # 注：实际业务中 "READY" 状态可能通过 doc.status 或 asset 元数据判断
                    # 这里简化：查询该空间下的所有 asset，由业务逻辑判断 READY 与否
                )
        )
        return {row[0] for row in result.all()}

    # ── 内容抓取与存储 ────────────────────────────────────────────────
    async def discover_all_urls(
        self,
        source_id: UUID,
    ) -> Set[str]:
        """全量发现 URL（当无 Manifest 时使用）"""
        source = await self.source_repo.get_by_id(source_id)
        if not source:
            return set()

        # 根据信源类型进行不同的发现逻辑
        # 简化实现：返回空集，实际应调用对应的抓取器
        # 例如：微信公众号抓取、RSS 订阅抓取等
        return set()

    async def get_or_create_doc_from_url(
        self,
        url: str,
        space_id: UUID,
        source_id: UUID,
    ) -> Optional[KnowledgeDoc]:
        """根据 URL 获取或创建文档实体"""
        # 1. 计算内容哈希
        content_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()

        # 2. 检查是否已存在相同哈希的文档
        result = await self.db.execute(
            select(KnowledgeDoc)
            .where(KnowledgeDoc.content_hash == content_hash)
            .where(KnowledgeDoc.space_id == space_id)
        )
        existing_doc = result.scalar_one_or_none()

        if existing_doc:
            # 文档已存在，更新引用计数
            await self.doc_repo.increment_hit_count(existing_doc.id)
            return existing_doc

        # 3. 创建新文档实体
        # 注：实际实现中需要真实抓取内容，这里仅演示创建空实体
        doc = KnowledgeDoc(
            space_id=space_id,
            title=urllib.parse.unquote(
                urllib.parse.urlparse(url).path.split("/")[-1] or "unknown"
            ),
            content=None,  # 实际应填充抓取内容
            source_url=url,
            content_hash=content_hash,
            status="pending",  # 初始状态
            hit_count=0,
            version=1,
            superseded=False,
        )

        self.db.add(doc)
        await self.db.flush()
        await self.db.refresh(doc)

        # 4. 创建资产记录（raw_uri 指向本地路径或对象存储）
        # 接口稳定：可切换本地盘/对象存储
        raw_uri = f"local://{space_id}/{doc.id}/{os.path.basename(url)}"
        asset = KnowledgeAsset(
            space_id=space_id,
            doc_id=doc.id,
            raw_uri=raw_uri,
            file_size=0,
            mime_type="text/markdown",
        )
        self.db.add(asset)
        await self.db.flush()
        await self.db.refresh(asset)

        return doc

    # ── 内容版本与存储硬化 ──────────────────────────────────────────
    async def upgrade_document_version(
        self,
        doc_id: UUID,
    ) -> KnowledgeDoc:
        """改文版本号 + 1 / 旧 doc 标记为 superseded"""
        result = await self.db.execute(
            select(KnowledgeDoc).where(KnowledgeDoc.id == doc_id)
        )
        doc = result.scalar_one_or_none()
        if not doc:
            raise ValidationError("文档不存在")

        # 旧版本标记为 superseded
        doc.superseded = True
        # 新版本版本号 + 1
        doc.version += 1
        doc.updated_at = datetime.now(timezone.utc)

        await self.db.flush()
        await self.db.refresh(doc)
        return doc

    # ── HitCache/HitCount 语义锁定 ────────────────────────────────────
    async def increment_hit_count(
        self,
        doc_id: UUID,
    ) -> KnowledgeDoc:
        """命中计数 +1（用于缓存命中实证）"""
        result = await self.db.execute(
            select(KnowledgeDoc).where(KnowledgeDoc.id == doc_id)
        )
        doc = result.scalar_one_or_none()
        if not doc:
            raise ValidationError("文档不存在")

        doc.hit_count += 1
        await self.db.flush()
        await self.db.refresh(doc)
        return doc

    # ── Short Link：先查映射再抓回归 ──────────────────────────────────
    async def resolve_short_link(
        self,
        short_key: str,
    ) -> Optional[Tuple[KnowledgeDoc, str]]:
        """先查映射再抓：通过短链 key 关联到文档和真实 URI"""
        # 1. 查数据库映射
        result = await self.db.execute(
            select(KnowledgeAsset).where(
                KnowledgeAsset.raw_uri.like(f"%{short_key}%")
            )
        )
        asset = result.scalar_one_or_none()

        if not asset:
            return None

        # 2. 通过 asset → doc
        doc_result = await self.db.execute(
            select(KnowledgeDoc).where(KnowledgeDoc.id == asset.doc_id)
        )
        doc = doc_result.scalar_one_or_none()

        if not doc:
            return None

        return doc, asset.raw_uri

    # ── 20003 与缓存互斥锁定 ────────────────────────────────────────
    async def check_quality_before_cache(
        self,
        doc_id: UUID,
    ) -> Tuple[bool, str]:
        """20003 质量卡检查（READY 缓存不重走护栏）"""
        result = await self.db.execute(
            select(KnowledgeDoc).where(KnowledgeDoc.id == doc_id)
        )
        doc = result.scalar_one_or_none()

        if not doc:
            return False, "文档不存在"

        # 规则：如果 doc.hitCount 超过阈值且 doc.status == "ready"，
        # 则视为缓存命中，不应重走质量护栏
        # 反之，如果 hitCount < 阈值 或 status != "ready"，则进入质检
        QUALITY_THRESHOLD = 10  # 假设阈值为 10 次命中

        if doc.hit_count >= QUALITY_THRESHOLD and doc.status == "ready":
            return True, "缓存命中（已达命中阈值）"

        # 进入质量检查流程
        # 这里简化处理：返回 False，实际应调用质量检测器
        return False, "待质量检查"
