# -*- coding: utf-8 -*-
"""引擎管理 API 端点

实现 BE-03 工作包要求：
- 引擎三态语义：configured / allowlisted / available
- GET /engines：返回 each engine 的 configured/allowlisted/available 状态
- PATCH /engine：切换引擎（新入库走新引擎，旧文档不动）
- engine_kb_id 双写回归
- citations.engine 全链回归
- 密钥只走 env，禁止入库明文
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user_id
from app.core.errors import api_error
from app.models.entities import KnowledgeSpace
from app.repositories.space import SpaceRepository
from app.services.engines import EngineService

router = APIRouter(prefix="/engines", tags=["engines"])


@router.get("")
async def list_engines(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
"""获取引擎列表（三态语义）

返回格式：
[
  {
    "name": "builtin",        # internal name
    "display_name": "主平台", # 展示名称
    "status": "configured",   # configured / allowlisted / available
    "key_status": "configured", # Key 状态点
    "allowlisted": True,      # 是否在白名单中
    "is_default": True,       # 是否为默认引擎
    "description": "主平台内置引擎，无需额外 Key",
    "min_upload": true,       # 是否支持最小上传通路
    "min_retrieve": true,     # 是否支持最小检索通路
  }
]
"""
    engine_service = EngineService(db)
    engines = await engine_service.list_engines(user_id=user_id)
    return engines


@router.post("", status_code=status.HTTP_201_CREATED)
async def configure_engine(
    engine_name: str = Query(..., description="引擎名称"),
    api_key: Optional[str] = Query(None, description="API Key（仅在 .env 中配置，严禁明文入库）"),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
"""配置引擎 Key

注意：
1. Key 只能在 .env 环境变量中配置，不可入库明文
2. 配置成功后 engine 状态从 unavailable → allowlisted → configured
3. 未配 Key 时 engine 置灰（10004），禁止可点后 500
"""
    try:
        result = await EngineService.configure_engine(
            engine_name=engine_name,
            api_key=api_key,
            user_id=user_id,
            db=db,
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_error(30005, str(e))["message"],
        )


@router.get("/{engine_name}")
async def get_engine_status(
    engine_name: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
"""获取单个引擎的详细状态"""
    engine_service = EngineService(db)
    status = await engine_service.get_engine_status(
        engine_name=engine_name,
        user_id=user_id,
    )
    if not status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_error(10001, "引擎不存在")["message"],
        )
    return status


@router.post("/{engine_name}/switch")
async def switch_engine(
    engine_name: str,
    space_id: UUID = Query(..., description="切换空间的目标空间ID"),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
"""切换引擎（新入库走新引擎，旧文档不动）

流程：
1. 验证用户对 space_id 的访问权限
2. 记录 space.engine 字段为新引擎名
3. 旧文档/资产保持不动（不自动迁移）
4. 新文档使用新引擎路由
"""
    engine_service = EngineService(db)
    result = await engine_service.switch_engine(
        engine_name=engine_name,
        space_id=space_id,
        user_id=user_id,
        db=db,
    )
    return result
