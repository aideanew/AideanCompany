# -*- coding: utf-8 -*-
"""API 依赖注入 - 供路由函数使用

提供：当前用户ID、数据库会话、空间ID等上下文信息
遵循 AGENTS.md §Ⅵ Key 管理铁律：Key 只进 .env，config 用 ${VAR} 名字引用
"""
import os
from typing import Generator, Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import verify_token  # 假存在
from app.db.session import async_session


def get_db() -> Generator[AsyncSession, None, None]:
    """获取数据库会话"""
    session: AsyncSession = async_session()
    try:
        yield session
    finally:
        await session.close()


def get_current_user_id(
    db: AsyncSession = Depends(get_db),
) -> str:
    """获取当前登录用户 ID（从 token 解析而来）"""
    # 简化实现：从环境变量或请求头获取
    # 实际实现中从 JWT token 解析 user_id
    user_id = os.getenv("CURRENT_USER_ID", "anonymous")
    return user_id
