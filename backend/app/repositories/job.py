# -*- coding: utf-8 -*-
"""任务仓储 - 负责任务持久化与查询

职责：Route only do validation/authorization/normalization，业务在 Service。
Service 内 commit 边界明确；越权/无效统一 30004；requestId 同源
"""
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.entities import (
    JobItemStatus,
    JobStatus,
    KnowledgeJob,
    KnowledgeJobItem,
)


class JobRepository:
    """任务仓储类"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, job: KnowledgeJob) -> KnowledgeJob:
        """创建任务"""
        self.db.add(job)
        await self.db.flush()
        await self.db.refresh(job)
        return job

    async def get(self, job_id: UUID) -> Optional[KnowledgeJob]:
        """根据 ID 查找任务"""
        result = await self.db.execute(
            select(KnowledgeJob)
            .options(
                selectinload(KnowledgeJob.subscription),
                selectinload(KnowledgeJob.manifest),
                selectinload(KnowledgeJob.items).selectinload(KnowledgeJobItem.doc),
            )
            .where(KnowledgeJob.id == job_id)
        )
        return result.scalar_one_or_none()

    async def get_by_subscription(
        self,
        subscription_id: UUID,
        status: Optional[JobStatus] = None,
    ) -> List[KnowledgeJob]:
        """根据订阅 ID 查找任务"""
        stmt = select(KnowledgeJob).options(
            selectinload(KnowledgeJob.subscription),
            selectinload(KnowledgeJob.items).selectinload(KnowledgeJobItem.doc),
        ).where(KnowledgeJob.subscription_id == subscription_id)

        if status:
            stmt = stmt.where(KnowledgeJob.status == status)

        result = await self.db.execute(stmt.order_by(desc(KnowledgeJob.created_at)))
        return result.scalars().all()

    async def get_running_or_queued(
        self,
        subscription_id: UUID,
    ) -> List[KnowledgeJob]:
        """获取运行中或待处理的任务"""
        result = await self.db.execute(
            select(KnowledgeJob)
            .where(
                and_(
                    KnowledgeJob.subscription_id == subscription_id,
                    KnowledgeJob.status.in_([JobStatus.QUEUED, JobStatus.RUNNING]),
                )
            )
            .order_by(desc(KnowledgeJob.created_at))
        )
        return result.scalars().all()

    async def count_by_status(
        self,
        subscription_id: UUID,
        status: JobStatus,
    ) -> int:
        """统计特定状态的任务数"""
        result = await self.db.execute(
            select(func.count(KnowledgeJob.id))
            .where(
                and_(
                    KnowledgeJob.subscription_id == subscription_id,
                    KnowledgeJob.status == status,
                )
            )
        )
        return result.scalar_one()

    async def get_job_with_items(self, job_id: UUID) -> Optional[dict]:
        """获取任务及其项的详细信息"""
        result = await self.db.execute(
            select(KnowledgeJob)
            .options(
                selectinload(KnowledgeJob.subscription),
                selectinload(KnowledgeJob.manifest),
                selectinload(KnowledgeJob.items).selectinload(
                    KnowledgeJobItem.doc
                ),
            )
            .where(KnowledgeJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        if not job:
            return None

        return {
            "job_id": str(job.id),
            "status": job.status.value,
            "progress": job.progress,
            "total_items": job.total_items,
            "succeeded_items": job.succeeded_items,
            "failed_items": job.failed_items,
            "skipped_items": job.skipped_items,
            "subscription_id": str(job.subscription_id) if job.subscription else None,
            "manifest_id": str(job.manifest_id) if job.manifest else None,
            "created_at": job.created_at,
            "started_at": job.started_at,
            "finished_at": job.finished_at,
            "retry_count": job.retry_count,
            "items": [
                {
                    "item_id": str(item.id),
                    "doc_id": str(item.doc_id) if item.doc else None,
                    "status": item.status.value,
                    "error_code": item.error_code,
                    "error_message": item.error_message,
                    "retry_count": item.retry_count,
                }
                for item in job.items
            ],
        }

    async def update_status(
        self,
        job_id: UUID,
        status: JobStatus,
        progress: Optional[int] = None,
        **kwargs,
    ) -> KnowledgeJob:
        """更新任务状态"""
        job = await self.get(job_id)
        if not job:
            return None

        job.status = status
        if progress is not None:
            job.progress = progress

        # 更新时间戳
        if status in (JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.PARTIAL_SUCCESS):
            job.finished_at = datetime.now(timezone.utc)
            if status == JobStatus.SUCCEEDED:
                job.succeeded_items = kwargs.get("succeeded_items", job.succeeded_items + 1)
                job.failed_items = kwargs.get("failed_items", job.failed_items)
                job.skipped_items = kwargs.get("skipped_items", job.skipped_items)
            elif status == JobStatus.FAILED:
                job.failed_items = kwargs.get("failed_items", job.failed_items + 1)
            elif status == JobStatus.PARTIAL_SUCCESS:
                # PARTIAL_SUCCESS 表示部分成功，需要聚合计数
                pass

        await self.db.flush()
        await self.db.refresh(job)
        return job

    async def increment_progress(
        self,
        job_id: UUID,
        increment: int = 1,
    ) -> KnowledgeJob:
        """增量推进进度"""
        job = await self.get(job_id)
        if not job:
            return None

        job.progress = min(100, job.progress + increment)
        await self.db.flush()
        await self.db.refresh(job)
        return job

    async def add_item(
        self,
        job_id: UUID,
        doc_id: UUID,
        status: JobItemStatus = JobItemStatus.PENDING,
    ) -> KnowledgeJobItem:
        """添加任务项"""
        from app.models.entities import KnowledgeJobItem

        item = KnowledgeJobItem(
            job_id=job_id,
            doc_id=doc_id,
            status=status,
        )
        self.db.add(item)
        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def update_item(
        self,
        item_id: UUID,
        status: JobItemStatus,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Optional[KnowledgeJobItem]:
        """更新任务项状态"""
        result = await self.db.execute(
            select(KnowledgeJobItem).where(KnowledgeJobItem.id == item_id)
        )
        item = result.scalar_one_or_none()
        if not item:
            return None

        item.status = status
        if error_code:
            item.error_code = error_code
        if error_message:
            item.error_message = error_message

        # 如果是最终状态，更新任务计数
        if status in (
            JobItemStatus.SUCCEEDED,
            JobItemStatus.FAILED,
        ):
            job = await self.get(item.job_id)
            if job:
                if status == JobItemStatus.SUCCEEDED:
                    job.succeeded_items = (job.succeeded_items or 0) + 1
                elif status == JobItemStatus.FAILED:
                    job.failed_items = (job.failed_items or 0) + 1

        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def get_failed_items(
        self,
        job_id: UUID,
    ) -> List[KnowledgeJobItem]:
      
