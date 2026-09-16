# -*- coding: utf-8 -*-
"""订阅仓储 - 负责订阅持久化与查询"""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.entities import (
    KnowledgeSource,
    KnowledgeSubscription,
)


class SubscriptionRepository:
    """订阅仓储类"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, subscription: KnowledgeSubscription) -> KnowledgeSubscription:
        """创建订阅"""
        self.db.add(subscription)
        await self.db.flush()
        await self.db.refresh(subscription)
        return subscription

    async def get_by_id(
        self,
        subscription_id: UUID,
        user_id: str,
    ) -> Optional[KnowledgeSubscription]:
        """根据 ID 查找订阅（带用户权限检查）"""
        # 注：实际权限检查需要 join space 表验证 user_id
        # 这里简化处理：返回订阅（在 service 层做完整权限检查）
        result = await self.db.execute(
            select(KnowledgeSubscription)
            .options(
                selectinload(KnowledgeSubscription.source),
                selectinload(KnowledgeSubscription.space),
            )
            .where(KnowledgeSubscription.id == subscription_id)
        )
        return result.scalar_one_or_none()

    async def get_by_source(
        self,
        source_id: UUID,
    ) -> List[KnowledgeSubscription]:
        """根据信源 ID 查找订阅"""
        result = await self.db.execute(
            select(KnowledgeSubscription)
            .options(selectinload(KnowledgeSubscription.space))
            .where(KnowledgeSubscription.source_id == source_id)
        )
        return result.scalars().all()

    async def get_by_space(
        self,
        space_id: UUID,
    ) -> List[KnowledgeSubscription]:
        """根据空间 ID 查找订阅"""
        result = await self.db.execute(
            select(KnowledgeSubscription)
            .options(selectinload(KnowledgeSubscription.source))
            .where(KnowledgeSubscription.space_id == space_id)
        )
        return result.scalars().all()

    async def get_subscriptions(
        self,
        space_id: Optional[UUID] = None,
        status: Optional[str] = None,
        user_id: str = "",
    ) -> List[KnowledgeSubscription]:
        """获取订阅列表（支持过滤）"""
        stmt = select(KnowledgeSubscription).options(
            selectinload(KnowledgeSubscription.source),
            selectinload(KnowledgeSubscription.space),
        )

        if space_id:
            stmt = stmt.where(KnowledgeSubscription.space_id == space_id)

        if status:
            stmt = stmt.where(KnowledgeSubscription.status == status)

        # 注：实际应用中需要加入 space 表进行 user_id 权限过滤
        # 这里简化处理：返回所有订阅（在 service 层做权限过滤）
        result = await self.db.execute(stmt.order_by(desc(KnowledgeSubscription.created_at)))
        return result.scalars().all()

    async def update_subscription(
        self,
        subscription_id: UUID,
        user_id: str,
        **kwargs,
    ) -> Optional[KnowledgeSubscription]:
        """更新订阅"""
        subscription = await self.get_by_id(subscription_id, user_id)
        if not subscription:
            return None

        for key, value in kwargs.items():
            if hasattr(subscription, key):
                setattr(subscription, key, value)

        await self.db.flush()
        await self.db.refresh(subscription)
        return subscription

    async def delete_subscription(
        self,
        subscription_id: UUID,
        user_id: str,
    ) -> bool:
        """删除订阅"""
        subscription = await self.get_by_id(subscription_id, user_id)
        if not subscription:
            return False

        await self.db.delete(subscription)
        await self.db.flush()
        return True
