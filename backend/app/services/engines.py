# -*- coding: utf-8 -*-
"""引擎服务 - 负责引擎路由、多引擎接线体系

实现 BE-03 工作包要求：
- 引擎路由：kb/chat 全面按 space.engine 路由
- builtin（LangBot）保持原行为零变更回归
- 非 builtin 按 Key 到位逐个开：E1 RAGFlow / E2 Coze / E3 Dify / E4 FastGPT
- Key 未配时 10004 置灰语义（不可用矩阵）
- engine_kb_id 双写回归
- citations.engine 全链回归
- 密钥纪律：只走 env，不入库明文
"""
import os
from typing import Dict, List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ValidationError
from app.models.entities import KnowledgeSpace, KnowledgeSource
from app.repositories.space import SpaceRepository
from app.services.kb import KnowledgeBaseService


class EngineService:
    """引擎服务类"""

    # 引擎三态定义（与 AGENTS.md §Ⅵ 和规划文档保持一致）
    ENGINE_STATUS_UNKNOWN = "unknown"  # 未知/未配置
    ENGINE_STATUS_UNAVAILABLE = "unavailable"  # 不可用（Key 未配）
    ENGINE_STATUS_ALLOWLISTED = "allowlisted"  # 已加白名单，待 Key 配置
    ENGINE_STATUS_CONFIGURED = "configured"  # 已配置 Key，可用
    
    # 支持的引擎列表（内置 + SaaS）
    ENGINES = {
        "builtin": {  # LangBot 内置
            "name": "builtin",
            "display_name": "主平台",
            "description": "主平台内置引擎，基于 LangBot，无需额外配置",
            "is_builtin": True,
            "is_default": True,
            "min_upload": True,
            "min_retrieve": True,
            "requires_key": False,
            "key_env": None,
        },
        "main": {  # 主平台 RAGFlow (E1)
            "name": "main",
            "display_name": "RAGFlow",
            "description": "主平台自建 RAGFlow 引擎",
            "is_builtin": False,
            "is_default": False,
            "min_upload": True,
            "min_retrieve": True,
            "requires_key": True,
            "key_env": "HERMES_CUSTOM_API_RAGFLOW_API_KEY",
        },
        "coze": {  # Coze (E2)
            "name": "coze",
            "display_name": "Coze",
            "description": "Coze 智能体平台",
            "is_builtin": False,
            "is_default": False,
            "min_upload": True,
            "min_retrieve": True,
            "requires_key": True,
            "key_env": "HERMES_CUSTOM_API_COZE_API_KEY",
        },
        "dify": {  # Dify (E3)
            "name": "dify",
            "display_name": "Dify",
            "description": "Dify LLM 应用开发平台",
            "is_builtin": False,
            "is_default": False,
            "min_upload": True,
            "min_retrieve": True,
            "requires_key": True,
            "key_env": "HERMES_CUSTOM_API_DIFY_API_KEY",
        },
        "fastgpt": {  # FastGPT (E4)
            "name": "fastgpt",
            "display_name": "FastGPT",
            "description": "FastGPT 知识库问答系统",
            "is_builtin": False,
            "is_default": False,
            "min_upload": True,
            "min_retrieve": True,
            "requires_key": True,
            "key_env": "HERMES_CUSTOM_API_FASTGPT_API_KEY",
        },
    }

    def __init__(self, db: AsyncSession):
        self.db = db
        self.space_repo = SpaceRepository(db)
        self.kb_service = KnowledgeBaseService(db)

    async def list_engines(
        self,
        user_id: str = "",
    ) -> List[Dict]:
        """获取所有引擎的状态列表（三态语义）"""
        engines_status = []
        
        for engine_key, engine_def in self.ENGINES.items():
            # 确定引擎状态
            status = self._get_engine_status(engine_key)
            
            engines_status.append({
                "name": engine_def["name"],
                "display_name": engine_def["display_name"],
                "status": status,  # configured / allowlisted / unavailable
                "key_status": self._get_key_status(engine_key),
                "allowlisted": self._is_allowlisted(engine_key),
                "is_default": engine_def["is_default"],
                "description": engine_def["description"],
                "min_upload": engine_def["min_upload"],
                "min_retrieve": engine_def["min_retrieve"],
                "is_builtin": engine_def["is_builtin"],
                "requires_key": engine_def["requires_key"],
            })
        
        return engines_status

    async def get_engine_status(
        self,
        engine_name: str,
        user_id: str = "",
    ) -> Optional[Dict]:
        """获取单个引擎的详细状态"""
        if engine_name not in self.ENGINES:
            return None
            
        engine_def = self.ENGINES[engine_name]
        status = self._get_engine_status(engine_name)
        
        return {
            "name": engine_def["name"],
            "display_name": engine_def["display_name"],
            "status": status,
            "key_status": self._get_key_status(engine_name),
            "allowlisted": self._is_allowlisted(engine_name),
            "is_default": engine_def["is_default"],
            "description": engine_def["description"],
            "min_upload": engine_def["min_upload"],
            "min_retrieve": engine_def["min_retrieve"],
            "is_builtin": engine_def["is_builtin"],
            "requires_key": engine_def["requires_key"],
            "key_env": engine_def["key_env"],  # 用于调试，实际不返回真实值
        }

    async def switch_engine(
        self,
        engine_name: str,
        space_id: UUID,
        user_id: str,
        db: AsyncSession,
    ) -> Dict:
        """切换引擎：设置 space.engine 字段，新入库走新引擎，旧文档不动"""
        # 验证引擎存在
        if engine_name not in self.ENGINES:
            raise ValidationError(f"不支持的引擎: {engine_name}")
        
        # 验证引擎可用状态（已配置 Key 或不需要 Key）
        status = self._get_engine_status(engine_name)
        if status == EngineService.ENGINE_STATUS_UNAVAILABLE:
            raise ValidationError(
                f"引擎 {engine_name} 未配置 Key，请联系管理员"
            )
        
        # 获取空间并验证权限
        space = await self.space_repo.get_by_id(space_id, user_id)
        if not space:
            raise ValidationError(f"空间不存在或无权限: {space_id}")
        
        # 记录引擎切换（新入库走新引擎，旧文档不动）
        await self.db.execute(
            update(KnowledgeSpace)
            .where(KnowledgeSpace.id == space_id)
            .values(engine=engine_name)
        )
        await self.db.commit()
        
        # TODO: 更新 engine_kb_id（如果需要，在 KB 服务中处理双写回归）
        
        return {
            "space_id": str(space_id),
            "engine": engine_name,
            "message": f"引擎已切换为 {self.ENGINES[engine_name]['display_name']}",
            "note": "新入库将使用新引擎，旧文档保持原引擎不变",
        }

    def _get_engine_status(
        self,
        engine_name: str,
    ) -> str:
        """获取引擎的三态状态"""
        engine_def = self.ENGINES[engine_name]
        
        # 不需要 Key 的引擎（builtin）默认 configured
        if not engine_def["requires_key"]:
            return EngineService.ENGINE_STATUS_CONFIGURED
        
        # 需要 Key 的引擎，检查环境变量
        key_env = engine_def.get("key_env")
        if not key_env:
            # 没有配置 key_env，视为不可用（保守策略）
            return EngineService.ENGINE_STATUS_UNAVAILABLE
            
        # 检查环境变量是否已设置（真实值而非占位符）
        key_value = os.getenv(key_env)
        if not key_value or key_value.startswith("<") or "FILL_ME" in key_value:
            # 未配置或仍为占位符
            return EngineService.ENGINE_STATUS_UNAVAILABLE
        
        # Key 已配置
        return EngineService.ENGINE_STATUS_CONFIGURED

    def _get_key_status(
        self,
        engine_name: str,
    ) -> str:
        """获取 Key 状态点（用于前端展示）"""
        engine_def = self.ENGINES[engine_name]
        
        if not engine_def["requires_key"]:
            return "configured"  # 不需要 Key 视为已配置
        
        key_env = engine_def.get("key_env")
        if not key_env:
            return "unavailable"
            
        key_value = os.getenv(key_env)
        if not key_value or key_value.startswith("<") or "FILL_ME" in key_value:
            return "unavailable"  # 未配置
        
        return "configured"  # 已配置

    def _is_allowlisted(
        self,
 
