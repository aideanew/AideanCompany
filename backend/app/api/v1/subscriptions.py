# EOF'
# -*- coding: utf-8 -*-
"""订阅相关 API 端点

实现 BE-01 工作包要求：
- 订阅创建、列表、详情
- 任务执行链路：订阅 → Job 创建 → 执行器驱动 → 心跳/终态
- Manifest Diff 计算：DISCOVERED − 已有 READY Asset
- JobItem 逐篇驱动（复用 kb ingest_url 单篇链）
- 失败分类 TEMPORARY/PERMANENT，PARTIAL_SUCCESS 聚合
- POST /jobs/{id}/retry 真实单篇重试（仅 FAILED 项，幂等）
- GET /jobs 列表补齐（status 过滤+limit）
- sync_policy/next_run_at 推进
- 无 Key/无 Manifest 时明确空 Job + info 日志，不建 fixture
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db
from app.core.errors import (
    api_error,
    BusinessLogicError,
    ResourceNotFoundError,
    ValidationError,
)
from app.models.entities import (
    JobItemStatus,
    JobStatus,
    KnowledgeJob,
    KnowledgeJobItem,
    KnowledgeManifest,
    KnowledgeSource,
    KnowledgeSubscription,
    SyncPolicy,
)
from app.repositories.job import JobRepository
from app.repositories.subscription import SubscriptionRepository
from app.services.jobs import JobService
from app.services.subscription import SubscriptionService

router = APIRouter()


# ── 订阅管理 ─────────────────────────────────────────────────────────────
@router.post("", status_code=status.HTTP_201_CREATED)
async def create_subscription(
    source_id: UUID,
    space_id: UUID,
    sync_policy: SyncPolicy = SyncPolicy.RESERVED,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """创建订阅"""
    subscription_service = SubscriptionService(db)
    subscription = await subscription_service.create_subscription(
        space_id=space_id,
        source_id=source_id,
        user_id=user_id,
        sync_policy=sync_policy,
    )
    return {
        "id": subscription.id,
        "space_id": subscription.space_id,
        "source_id": subscription.source_id,
        "sync_policy": subscription.sync_policy.value,
        "status": subscription.status,
        "created_at": subscription.created_at,
    }


@router.get("", response_model=List[dict])
async def list_subscriptions(
    space_id: Optional[UUID] = Query(None, description="过滤特定空间的订阅"),
    status: Optional[str] = Query(None, description="过滤订阅状态"),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """获取订阅列表"""
    subscription_service = SubscriptionService(db)
    subscriptions = await subscription_service.get_subscriptions(
        space_id=space_id,
        status=status,
        user_id=user_id,
    )
    return [
        {
            "id": sub.id,
            "space_id": sub.space_id,
            "source_id": sub.source_id,
            "source_name": sub.source.name if sub.source else None,
            "sync_policy": sub.sync_policy.value,
            "status": sub.status,
            "next_run_at": sub.next_run_at,
            "last_run_at": sub.last_run_at,
            "error_count": sub.error_count,
            "created_at": sub.created_at,
        }
        for sub in subscriptions
    ]


@router.get("/{subscription_id}")
async def get_subscription(
    subscription_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """获取订阅详情"""
    subscription_service = SubscriptionService(db)
    subscription = await subscription_service.get_subscription(
        subscription_id=subscription_id,
        user_id=user_id,
    )
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_error(10001, "订阅不存在或无权限")["message"],
        )
    return {
        "id": subscription.id,
        "space_id": subscription.space_id,
        "source_id": subscription.source_id,
        "source": {
            "id": subscription.source.id,
            "name": subscription.source.name,
            "wechat_id": subscription.source.wechat_id,
            "avatar_url": subscription.source.avatar_url,
        } if subscription.source else None,
        "sync_policy": subscription.sync_policy.value,
        "status": subscription.status,
        "next_run_at": subscription.next_run_at,
        "last_run_at": subscription.last_run_at,
        "error_count": subscription.error_count,
        "created_at": subscription.created_at,
        "updated_at": subscription.updated_at,
    }


# ── 任务执行相关 ────────────────────────────────────────────────────────
@router.post("/{subscription_id}/execute")
async def execute_subscription(
    subscription_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """手动触发订阅执行（创建 Job 并启动执行器）"""
    job_service = JobService(db)
    job = await job_service.execute_subscription(
        subscription_id=subscription_id,
        user_id=user_id,
    )
    if not job:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_error(30005, "无法创建执行任务（可能无Manifest或无增量）")["message"],
        )
    return {
        "id": job.id,
        "subscription_id": job.subscription_id,
        "status": job.status.value,
        "progress": job.progress,
        "total_items": job.total_items,
        "succeeded_items": job.succeeded_items,
        "failed_items": job.failed_items,
        "skipped_items": job.skipped_items,
        "created_at": job.created_at,
        "started_at": job.started_at,
    }


@router.get("/jobs", response_model=List[dict])
async def list_jobs(
    subscription_id: Optional[UUID] = Query(None, description="过滤特定订阅的任务"),
    status: Optional[JobStatus] = Query(None, description="过滤任务状态"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """获取任务列表（BE-01 核心要求：补齐 GET /jobs 列表）"""
    job_service = JobService(db)
    jobs = await job_service.get_jobs(
        subscription_id=subscription_id,
        status=status,
        limit=limit,
        offset=offset,
        user_id=user_id,
    )
    return [
        {
            "id": job.id,
            "subscription_id": job.subscription_id,
            "manifest_id": job.manifest_id,
            "status": job.status.value,
            "progress": job.progress,
            "total_items": job.total_items,
            "succeeded_items": job.succeeded_items,
            "failed_items": job.failed_items,
            "skipped_items": job.skipped_items,
            "started_at": job.started_at,
            "finished_at": job.finished_at,
            "retry_count": job.retry_count,
            "created_at": job.created_at,
        }
        for job in jobs
    ]


@router.get("/jobs/{job_id}")
async def get_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """获取任务详情"""
    job_service = JobService(db)
    job = await job_service.get_job(
        job_id=job_id,
        user_id=user_id,
    )
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_error(10001, "任务不存在或无权限")["message"],
        )
    return {
        "id": job.id,
        "subscription_id": job.subscription_id,
        "manifest_id": job.manifest_id,
        "status": job.status.value,
        "progress": job.progress,
        "total_items": job.total_items,
        "succeeded_items": job.succeeded_items,
        "failed_items": job.failed_items,
        "skipped_items": job.skipped_items,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "retry_count": job.retry_count,
        "max_retries": job.max_retries,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }


@router.post(
