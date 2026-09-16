# -*- coding: utf-8 -*-
"""核心错误定义 - AideanAgentFleet 统一错误体系

遵循：HTTP 状态码 -> 应用错误码 -> 前端展示文案
约定：30000+ 为自定义应用错误码，与 AGENTS.md §Ⅵ 铁律一致
"""
from http import HTTPStatus


# ── 10001~19999：身份/鉴权/会话相关 ──────────────────────────────────────
# 10001：缺少会话凭据 / 会话不存在或已过期
# 10002：state 缺失、已过期或不匹配
# 10003：回调白名单不匹配
# 10005：输入参数校验失败
AUTH_ERRORS = {
    10001: ("10001", "缺少会话凭据", "请先登录"),
    10002: ("10002", "会话状态异常", "请重新登录后重试"),
    10003: ("10003", "回调白名单不匹配", "联系管理员配置回调白名单"),
    10005: ("10005", "请求参数校验失败", "请检查输入内容"),
}

# ── 20001~29999：资源/空间相关 ─────────────────────────────────────────────
# 20001：空间不存在或无权限（推荐 30004，不泄露存在性）
# 20002：空间已存在
# 20003：低质内容
# 20004：空间操作受限
RESOURCE_ERRORS = {
    20001: ("20001", "资源不存在或无权限", "资源不存在或无权访问"),
    20003: ("20003", "低质内容", "内容质量未通过检查，请修改后重试"),
}

# ── 30001~39999：业务/业务逻辑相关 ─────────────────────────────────────────
# 30001：知识空间不存在或已删除
# 30002：操作频率过快
# 30003：网络超时/服务不可达
# 30004：越权/非法操作——核心码，与 spaces.py get_space_view 口径一致
# 30005：同步冲突
# 30006：并发冲突
BUSINESS_ERRORS = {
    30001: ("30001", "资源不存在或无权限", "资源不存在或无权限，请联系管理员"),
    30004: ("30004", "越权/非法操作", "越权操作，禁止访问他人资源"),
    30005: ("30005", "同步冲突", "检测到并发冲突，请稍后重试"),
}

# ── 40001~49999：系统/运行时相关 ────────────────────────────────────────────
# 40001：服务不可用
# 40002：请求体已解析
# 40005：路由未找到
SYSTEM_ERRORS = {
    40001: ("40001", "服务不可用", "服务暂时不可用，请稍后重试"),
    40005: ("40005", "路由未找到", "请求路径不存在"),
}


def api_error(code: int, detail: str | None = None) -> dict:
    """生成规范化的 API 错误响应 envelope。

    格式：{"code": int, "message": str, "requestId": str}
    """
    prefix, default_msg, _ = _resolve_error(code)
    msg = detail or default_msg
    return {"code": code, "message": msg, "requestId": ""}


def _resolve_error(code: int) -> tuple:
    """根据错误码返回 (prefix, default_message) 元组。"""
    first_digit = code // 1000
    if first_digit == 1:
        return AUTH_ERRORS.get(code, (f"{code}", "未知身份错误",))
    if first_digit == 2:
        return RESOURCE_ERRORS.get(code, (f"{code}", "资源错误",))
    if first_digit == 3:
        return BUSINESS_ERRORS.get(code, (f"{code}", "业务错误",))
    if first_digit == 4:
        return SYSTEM_ERRORS.get(code, (f"{code}", "系统错误",))
    return (f"{code}", "未知错误",)


class ResourceNotFoundError(Exception):
    """资源未找到异常 - 推码 30001 / 404"""

    def __init__(self, message: str = "资源不存在"):
        self.message = message
        super().__init__(self.message)


class ResourcePermissionError(Exception):
    """资源权限错误异常 - 推码 30004 / 403"""

    def __init__(self, message: str = "无权访问该资源"):
        self.message = message
        super().__init__(self.message)


class ValidationError(Exception):
    """输入参数校验错误 - 推码 10005 / 400"""

    def __init__(self, message: str = "参数校验失败"):
        self.message = message
        super().__init__(self.message)


class BusinessLogicError(Exception):
    """业务逻辑错误 - 推码 30004/30005"""

    def __init__(self, message: str = "业务逻辑错误"):
        self.message = message
        super().__init__(self.message)
