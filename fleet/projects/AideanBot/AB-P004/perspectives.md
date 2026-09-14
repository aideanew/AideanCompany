# AB-P004 T-021 多视角挖遗漏（≥6 轮）

## 轮1 新用户（注册→3步建库）
- 用例：首页「创建第一个知识库」CTA → /spaces 空态 → 详情页 AddArticlePanel 粘贴 → 成功入库
- 判定：空态 CTA 已落地（frontend/app/page.tsx 工作台改造）；真实注册需 SSO（标 BLOCKED 未持有 code）
## 轮2 老用户（断点/多空间）
- 用例：多空间切换（/chat 选择器 optgroup 我的/公共库，切换确认模态）
- 判定：空间切换确认模态存在（chat/page.tsx switchTarget）；onboarding 断点续做未实现（L-09 已登记）
## 轮3 产品（逐字对 README）
- README 目标1（公众号链接建知识库）→ 已通（F1）；目标2（全部文章/单篇二选一）→ F2 订阅+F1 单篇覆盖；目标3（机器人主动发消息）→ 未实现（M2 未来规划，不测不扣分）
- 【未来规划】目标4/5 → 不测（README 明确未来规划）
## 轮4 前端（加载态/报错文案/控制台报错）
- 加载态：空间骨架屏（spaces/[id] page.tsx 136-154）；问答 401 回落首页；
- 报错文案：10006/20001/20003/30003 均有中文映射（AddArticlePanel/订阅页）；控制台 401 游客态为预期
## 轮5 后端（非法 body/并发/重启丢数/端口铁律）
- 非法 body：POST /sources 空 body → 10005/422（RequestValidation 信封）；
- 并发双提交幂等：Job idempotency_key 唯一（savepoint create_or_get）；重复订阅 created=false
- 重启丢数：Job/doc 状态持久化 PG（docker compose backend 重启后 DB 行仍在）
- 端口铁律：frontend=3333、backend=8000、postgres=5433、langbot=5300（无 3334/3335）
## 轮6 破坏者（XSS/超大 payload/路径穿越/直调）
- XSS：标题/question 走 JSON 序列化（前端 React 默认转义），无 innerHTML 注入面（grep 无）
- 超大 payload：POST /spaces/<built-in function id>/docs url max_length=512 → 超长 10005/422
- 路径穿越：space_id 非 UUID → 30004 不泄露存在性（get_by_id None 同语义）
- 绕过页面直调：无会话直调 /spaces → 10001 信封（已验证容器存活）
## 补证：e2e mock 主干回归（3456 隔离，2026-09-14）
- NEXT_PUBLIC_API_MOCK=true PORT=3456 烘焙构建 + next start + playwright trunk.spec.ts：**9/9 passed（32.9s）**
- 覆盖：未登录跳转/登录/搜索首问 SSE/多轮/切空间模态/错误重试/空间列表详情/登出/链接入库主链路
- 端口铁律：e2e 走 3456 隔离口，业务 3333 常驻容器未动（无 3334/3335）
