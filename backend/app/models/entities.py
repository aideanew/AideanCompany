# -*- coding: utf-8 -*-
"""实体模型定义 - 基于 SQLAlchemy ORM

映射到 PostgreSQL 数据库表结构：
- knowledge_spaces: 知识空间表
- knowledge_docs: 知识文档表  
- knowledge_assets: 知识资产表
- knowledge_sources: 信息源表
- knowledge_subscriptions: 订阅表
- knowledge_jobs: 任务表
- knowledge_job_items: 任务项表
- knowledge_manifests: 清单表
"""
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


# ── 公共基类 ──────────────────────────────────────────────────────────────
class BaseModel(Base):
    """基础模型，提供通用字段"""
    __abstract__ = True
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    created_at = Column(DateTime(timezone=True), server_default="NOW()", nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default="NOW()", onupdate="NOW()", nullable=False)


# ── 空间相关 ─────────────────────────────────────────────────────────────
class KnowledgeSpace(BaseModel):
    """知识空间表"""
    __tablename__ = "knowledge_spaces"
    
    user_id = Column(String(255), nullable=False, index=True)  # 关联到用户表
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, server_default="'active'")
    doc_count = Column(Integer, nullable=False, server_default="0")
    langbot_kb_uuid = Column(String(36), nullable=True, unique=True)  # LangBot 知识库 UUID
    langbot_bot_uuid = Column(String(36), nullable=True)  # LangBot 机器人 UUID
    langbot_pipeline_uuid = Column(String(36), nullable=True)  # LangBot 流水线 UUID
    
    # 关系
    docs = relationship("KnowledgeDoc", back_populates="space", cascade="all, delete-orphan")
    assets = relationship("KnowledgeAsset", back_populates="space", cascade="all, delete-orphan")
    sources = relationship("KnowledgeSource", back_populates="space", cascade="all, delete-orphan")
    subscriptions = relationship("KnowledgeSubscription", back_populates="space", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_space_user_name", "user_id", "name", unique=True),
    )


class KnowledgeDoc(BaseModel):
    """知识文档表"""
    __tablename__ = "knowledge_docs"
    
    space_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_spaces.id"), nullable=False, index=True)
    title = Column(String(512), nullable=False)
    content = Column(Text, nullable=True)
    source_url = Column(String(2048), nullable=True)  # 原始来源 URL
    content_hash = Column(String(64), nullable=False, index=True)  # SHA256 内容哈希
    status = Column(String(20), nullable=False, server_default="'pending'")  # pending/ready/failed
    langbot_file_id = Column(String(36), nullable=True)  # LangBot 文件 ID
    hit_count = Column(Integer, nullable=False, server_default="0")  # 被引用次数
    version = Column(Integer, nullable=False, server_default="1")  # 内容版本号
    superseded = Column(Boolean, nullable=False, server_default="false")  # 是否被新版本覆盖
    
    # 关系
    space = relationship("KnowledgeSpace", back_populates="docs")
    assets = relationship("KnowledgeAsset", back_populates="doc", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_doc_space_status", "space_id", "status"),
        Index("ix_doc_content_hash", "content_hash"),
        UniqueConstraint("space_id", "content_hash", name="uq_space_content_hash"),
    )


# ── 资产相关 ─────────────────────────────────────────────────────────────
class KnowledgeAsset(BaseModel):
    """知识资产表 - 实际存储的文档内容"""
    __tablename__ = "knowledge_assets"
    
    space_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_spaces.id"), nullable=False, index=True)
    doc_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_docs.id"), nullable=False, index=True)
    raw_uri = Column(String(2048), nullable=False)  # 存储路径（本地/S3/OSS等）
    file_size = Column(Integer, nullable=False, server_default="0")
    mime_type = Column(String(128), nullable=False, server_default="'text/markdown'")
    
    # 关系
    space = relationship("KnowledgeSpace", back_populates="assets")
    doc = relationship("KnowledgeDoc", back_populates="assets")
    
    __table_args__ = (
        Index("ix_asset_space_doc", "space_id", "doc_id"),
        UniqueConstraint("space_id", "doc_id", name="uq_space_doc_asset"),
    )


# ── 信息源相关 ───────────────────────────────────────────────────────────
class KnowledgeSource(BaseModel):
    """信息源表 - 用户订阅的公众号/RSS等"""
    __tablename__ = "knowledge_sources"
    
    space_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_spaces.id"), nullable=False, index=True)
    name = Column(String(128), nullable=False)  # 公众号名称
    description = Column(Text, nullable=True)
    avatar_url = Column(String(2048), nullable=True)
    qrcode_url = Column(String(2048), nullable=True)
    wechat_id = Column(String(64), nullable=True, unique=True)  # 公众号原始ID
    status = Column(String(20), nullable=False, server_default="'active'")  # active/inactive
    last_fetch_at = Column(DateTime(timezone=True), nullable=True)
    fetch_interval_minutes = Column(Integer, nullable=False, server_default="1440")  # 默认24小时
    
    # 关系
    space = relationship("KnowledgeSpace", back_populates="sources")
    subscriptions = relationship("KnowledgeSubscription", back_populates="source", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_source_space_name", "space_id", "name"),
        UniqueConstraint("space_id", "wechat_id", name="uq_space_wechat_id"),
    )


# ── 订阅相关 ─────────────────────────────────────────────────────────────
class SyncPolicy(PyEnum):
    """同步策略枚举"""
    RESERVED = "RESERVED"   # 首次全量，之后增量
    FULL = "FULL"           # 每次全量
    INCREMENTAL = "INCREMENTAL"  # 每次增量（仅 NEW/UPDATED "")


class KnowledgeSubscription(BaseModel):
    """订阅表 - 用户订阅的信息源"""
    __tablename__ = "knowledge_subscriptions"
    
    space_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_spaces.id"), nullable=False, index=True)
    source_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_sources.id"), nullable=False, index=True)
    sync_policy = Column(Enum(SyncPolicy), nullable=False, server_default="'RESERVED'")
    next_run_at = Column(DateTime(timezone=True), nullable=True)  # 下次同步时间
    last_run_at = Column(DateTime(timezone=True), nullable=True)  # 上次同步时间
    status = Column(String(20), nullable=False, server_default="'active'")  # active/paused/failed
    error_count = Column(Integer, nullable=False, server_default="0")  # 连续失败次数
    
    # 关系
    space = relationship("KnowledgeSpace", back_populates="subscriptions")
    source = relationship("KnowledgeSource", back_populates="subscriptions")
    jobs = relationship("KnowledgeJob", back_populates="subscription", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_subscription_space_source", "space_id", "source_id"),
        UniqueConstraint("space_id", "source_id", name="uq_space_source_subscription"),
    )


# ── 任务相关 ─────────────────────────────────────────────────────────────
class JobStatus(PyEnum):
    """任务状态枚举"""
    QUEUED = "QUEUED"       # 已入队，待执行
    RUNNING = "RUNNING"     # 正在执行中
    SUCCEEDED = "SUCCEEDED" # 执行成功
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"  # 部分成功（部分项失败）
    FAILED = "FAILED"       # 执行失败
    CANCELLED = "CANCELLED" # 已取消


class JobItemStatus(PyEnum):
    """任务项状态枚举"""
    PENDING = "PENDING"     # 待处理
    PROCESSING = "PROCESSING"  # 正在处理
    SUCCEEDED = "SUCCEEDED"  # 处理成功
    FAILED = "FAILED"       # 处理失败
    SKIPPED = "SKIPPED"     # 被跳过


class KnowledgeJob(BaseModel):
    """任务表 - 订阅执行的具体任务实例"""
    __tablename
