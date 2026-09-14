# AB-P004 T-021 缺陷表（只登记不修；含视角/复现/证据/等级/建议修复人）

| 编号 | 视角 | 复现 | 证据 | 等级 | 建议修复人 |
|---|---|---|---|---|---|
| D-01 | 老用户 | /onboarding 引导页+断点续做缺失 | 无 /onboarding 路由（frontend/app 无该目录） | P1 | worker-a |
| D-02 | 破坏者 | 未登录直调 /api/v1/spaces | 10001 信封（预期），但 /spaces/public 未登录亦 10001（正确） | — 非缺陷 | — |
| D-03 | 产品 | SSO 登录需 code，e2e 无法真登录 | 无 SSO code → 业务端点仅 DB 直查验证 | P2(环境 BLOCKED) | worker-c 补 cookie |
| D-04 | 前端 | 短链对二次抓取非 0 请求（L-01） | kb._is_short_link 表面归一未落长链映射 | P2 | worker-b |
| D-05 | 产品 | worker 执行循环未接线（L-06） | JobItem 状态机通，逐篇 ingest 归 M3 | P1 | worker-b |

注：「明确不做」（引用扇出 M4、机器人主动发消息 M2、视频下载）一律不测不扣分。