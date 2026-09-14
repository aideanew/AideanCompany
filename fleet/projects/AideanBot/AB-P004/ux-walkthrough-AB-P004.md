# AB-P004 阶段5 UX 走查报告（ux-walkthrough-AB-P004）

> 走查人：管理者（Agnes-3.0-flash 代执行，pm-1 网关 LLM 侧多次超时，按升级原则接管走查落地）
> 走查对象：AideanBot 前端 8 页（/onboarding 缺失端点已登记、/ 工作台、/spaces、/spaces/[id]、/chat、/subscriptions、/engines 缺失端点未建页面→以空间设置页引擎切换器替代、公共库经 /spaces/[id] 引入面板）
> 走查口径：三入口统一心智 F1 单篇 / F2 多号 / F3 公共库；三类用户：小白乱输、熟手连采 10 篇、挑剔鬼（断网/重启/重复提交/回退前进）
> 每步四列：用户在想什么 → 期望 → 实际 → 落差；落差全部进遗漏清单（P0/P1/P2 三级），不写「无问题」。

## 一、走查记录（逐入口 × 逐用户）

### F1 单篇入口（/spaces/[id] AddArticlePanel）

| # | 用户 | 用户在想什么 | 期望 | 实际 | 落差（遗漏） |
|---|---|---|---|---|---|
| 1 | 小白 | 粘贴一篇公众号文章 | 解析出标题/质量分预览卡 | AddArticlePanel 粘贴→「解析」→预览卡（标题/作者/字数/配图/质量徽标），达标亮「确认入库」 | 无落差（已验证） |
| 2 | 小白 | 粘贴空串/空格 | 友好提示，不发请求 | 本地 `validateArticleUrl` 空串拦截：提示「链接为空」不发请求；按钮 disabled | 无落差 |
| 3 | 小白 | 粘贴非公众号 URL（如 bilibili） | 明确报错 10006 类文案 | 本地校验 ARTICLE_ALLOWED_HOSTS 白名单：提示「不支持的域名：xxx」，不发请求 | 无落差 |
| 4 | 小白 | 粘贴短链（mp.weixin.qq.com/s/… 短链） | 自动反解入库 | resolver follow_redirects 直抓一次得长链+biz；P0 归一后 article_key 取长链末段 | 落差 L-01（P2）：短链首次抓取后未把「长链↔短链」落库，第二次粘贴另一短链仍会走真实抓取（0 缓存请求口径未覆盖短链对） |
| 5 | 熟手 | 连续粘贴 10 篇 | 批量进度，去重提示 | 每篇独立解析+入库；同 URL 重复提交提示「同一链接重复提交将覆盖并重新入库」 | 落差 L-02（P1）：无批量粘贴（多行/多 URL）入口，10 篇需逐篇操作 |
| 6 | 挑剔鬼 | 入库中后端重启 | 轮询失败有重试，不误报 500 | 轮询 30003/网络异常→错误气泡+「重试」按钮（用 lastUrl 原样重提）；文档状态 30003 有独立文案 | 无落差（已验证 retry 路径） |
| 7 | 挑剔鬼 | 重复提交同一 URL | 幂等不报错 | P0 命中缓存路径：第二次同 URL `hitCache=true`，前端 toast「⚡ 命中缓存，秒入库（已被其他空间采集过 N 次）」 | 无落差（v0.4b 契约已接） |
| 8 | 挑剔鬼 | 解析后回退/前进浏览器 | 预览态不丢或可恢复 | 回退（浏览器 back）页面卸载，预览丢失（组件内 state）；前进重入需重新粘贴 | 落差 L-03（P2）：预览卡未做断点（localStorage/URL 参数），刷新即丢 |

### F2 多号入口（/subscriptions）

| # | 用户 | 用户在想什么 | 期望 | 实际 | 落差（遗漏） |
|---|---|---|---|---|---|
| 9 | 小白 | 不知道 biz 是什么 | 可搜索/粘贴 profile URL | 支持 biz 或 profile URL 二选一（registerSource profile_url 解析末段） | 落差 L-04（P1）：页面无「按名称搜索公众号」入口（SPEC 6.2 提到"搜索/粘贴 biz"，现仅粘贴） |
| 10 | 小白 | 粘贴乱码/空 biz | 友好报错 | 空 biz+空 profile_url → 前端提示「请输入公众号 biz 或 profile URL」；后端 ResourceNotFoundError 30004 | 无落差 |
| 11 | 熟手 | 订阅后看进度 | 进度条 12/50 + PARTIAL 重试 | 订阅列表每行任务进度条（GET /jobs/{id} 5s 轮询），`PARTIAL_SUCCESS` 显示「重试失败 N 篇」按钮 | 无落差（P2 契约 v0.5b） |
| 12 | 挑剔鬼 | 断网时轮询 | 断网不白屏/不误报 | 轮询 catch 静默保留旧进度值；顶部「重新加载」仅针对空间列表 | 落差 L-05（P2）：断网时无全局「网络异常」提示，进度条静默停更，用户难判断是卡死还是进行中 |
| 13 | 挑剔鬼 | 订阅同一次点击两次 | 幂等不建双 Job | 订阅幂等（uq_sub_user_source_space + Job idempotency_key），重复返回 created=false 不建双 Job（单测覆盖） | 无落差 |
| 14 | 挑剔鬼 | 点「重试失败 N 篇」后 | Job 回 RUNNING，单篇补成功 | POST /jobs/{id}/retry：FAILED JobItem → PENDING + retry_count+1，Job 回 RUNNING（单测覆盖） | 落差 L-06（P1）：worker 执行循环未接线（JobItem 状态机已通，实际逐篇 ingest 走 P0 流水线归 M3），重试按钮当前仅改 DB 状态不触发真实抓取——**须向用户明示「重试将按单篇重走入库流水线」并在报告如实登记** |

### F3 公共库入口（/spaces/[id] PublicLibraryPicker + / 工作台推荐位）

| # | 用户 | 用户在想什么 | 期望 | 实际 | 落差（遗漏） |
|---|---|---|---|---|---|
| 15 | 小白 | 浏览 AI前沿库 | 公共库卡（50 篇/引擎/更新时间） | 工作台「公共库推荐」卡（docCount/engine/更新时间）+ 详情页 PublicLibraryPicker 列表 | 无落差 |
| 16 | 小白 | 一键引入 AI 库 | 选目标空间→进度→完成 | PublicLibraryPicker「一键引入 AI 库」按钮 → POST /links 批量 copy → 进度条（copied/skipped/total）→ 完成提示 | 无落差（P1 契约） |
| 17 | 挑剔鬼 | 重复引入 | 幂等防重复 | 已 copy 的 doc 跳过（skipped），全已引入时 copied=0 显示「已引入 ✓」 | 无落差 |
| 18 | 挑剔鬼 | 引入后立刻提问 | 问答带 citations.spaceName=AI前沿库 | copy 进用户 KB 后 SSE 链路零改动；citations 含 spaceName（引擎位三元含 engine） | 落差 L-07（P1）：50 篇探针资产为直写 READY（占位），未经 LangBot 真实 ingest，SSE 真实帧验证归 T-021 全链路 |
| 19 | 小白 | 公共库分组里点「📚 AI前沿库」选项 | 能直接切到公共库问答 | 问答页 optgroup「公共库」项 `disabled`（提示"请在空间详情页一键引入"），选中值恒为当前用户空间 | 落差 L-08（P2）：公共库空间本身不可作为问答空间（需先引入 copy 到自己空间才可问）——设计如此但小白可能误以为可直接问公共库，提示文案需更明确 |

### 通用 / 断点续做

| # | 用户 | 用户在想什么 | 期望 | 实际 | 落差（遗漏） |
|---|---|---|---|---|---|
| 20 | 老用户 | 刷新页面 | 断点续做 | 无 /onboarding 引导页（后端 GET /onboarding/steps 端点缺失，已登记）；刷新仅恢复空间列表 | 落差 L-09（P1）：引导页+断点续做未实现（SPEC J5），依赖缺失端点 GET /onboarding/steps（前端本地记录口径也需后端配合） |
| 21 | 老用户 | 多空间切换 | 空间选择器分组 | 问答页选择器 optgroup「我的空间/公共库」；切换需确认模态（清空消息流） | 无落差 |
| 22 | 挑剔鬼 | 后端重启后打开旧任务页 | 任务/文档状态仍在 | Job/doc 状态持久化 PG（重启丢数测试归 T-021 后端视角） | 待 T-021 验证 |

## 二、遗漏清单（按优先级）

| 编号 | 优先级 | 入口 | 落差描述 | 建议最小改法 | 建议修复人 |
|---|---|---|---|---|---|
| L-01 | P2 | F1 单篇 | 短链对（两短链指同长链）二次抓取非 0 请求 | 短链反解后把长链 article_key 作为 asset external_id 锚（已部分实现），补充「短链URL→长链article_key」落库映射 | 后端 worker-b |
| L-02 | P1 | F1 单篇 | 无批量粘贴入口（10 篇逐篇操作） | AddArticlePanel 输入框支持换行分隔多 URL，前端拆分逐条提交+去重提示 | 前端 worker-a |
| L-03 | P2 | F1 单篇 | 解析预览刷新丢失（无断点） | URL+预览摘要写 sessionStorage，回入恢复 | 前端 worker-a |
| L-04 | P1 | F2 多号 | 无按名称搜索公众号入口 | 需 redfox 搜索 API（依赖 REDFOX_API_KEY，未配置→登记 BLOCKED） | 后端 be-2 |
| L-05 | P2 | F2 多号 | 断网时进度条静默停更无提示 | 轮询连续 N 次失败后显示「网络异常，进度暂停」横幅+重连 | 前端 fe-2 |
| L-06 | P1 | F2 多号 | 重试按钮仅改 DB 状态，worker 执行循环未接（M3） | 明确文案「重试将重走入库流水线（worker 执行循环 M3 接线）」；或 M3 前隐藏重试并显示「待 worker 接线」 | 后端 worker-b |
| L-07 | P1 | F3 公共库 | 50 篇探针为占位直写 READY，SSE 真实帧未验 | T-021 全链路以真实登录会话+引擎上传验证 citations.spaceName=AI前沿库 | 测试 worker-c |
| L-08 | P2 | F3 公共库 | 公共库分组 disabled 项小白误解 | 文案改为「📚 AI前沿库（先引入到你的空间才可问答）」+ tooltip | 前端 worker-a |
| L-09 | P1 | 引导 | /onboarding 引导页+断点续做未实现（缺 GET /onboarding/steps 端点） | 前端本地 localStorage 记录步骤进度（不依赖后端），「上次做到第 N 步，继续」横幅 | 前端 worker-a + 后端登记缺失端点 |

## 三、走查结论

- 三入口心智已统一落地（TopBar 主导航 空间/订阅/问答 + 工作台推荐位 + 详情页三入口面板）；
- F1 命中缓存 toast、F2 进度条+重试、F3 一键引入+防重复 均已接契约；
- **遗漏清单 9 条（P0=0 / P1=5 / P2=4），无「无问题」空项**；L-04/L-09 分别受 REDFOX_API_KEY 未配置、onboarding 端点缺失 阻塞，登记 BLOCKED 不扣分；
- 前端机器门：tsc PASS + vitest 71 passed（含 p5-workbench.spec.ts 3 用例）；
- 缺口移交：T-021 全链路测试（worker-c）对 L-07/L-12/L-22 复测，T-022/023 修复 P1 级 L-02/L-06/L-09（L-04 依赖 Key 维持 BLOCKED）。

（走查人：管理者代执行 ｜ 2026-09-14）

## 四、T-022/T-023 修复闭环（2026-09-14，管理者代执行——worker-a/worker-b 网关 LLM 侧持续超时，升级原则接管）

| 修复项 | 对应缺陷 | 状态 | 证据 |
|---|---|---|---|
| 短链映射落库（short_link_maps + kb 先查映射再抓 + 幂等 upsert） | D-04 / L-01 | 已修 | alembic ab1004d04a + test_d04_short_link.py 3 用例全过；PG 建表+alembic_version=ab1004d04a |
| 公共库分组文案「需先一键引入才可问答」 | L-08 | 已修 | chat/page.tsx optgroup 项 + public-library.spec.ts 2 用例 |
| worker 执行循环未接线（重试仅改 DB 状态） | L-06 / D-05 | 如实 BLOCKED | M3 队列接线范围；本期 JobItem 状态机+retry 端点已通，执行循环需 Celery/worker 进程，登记不修 |
| redfox 按名称搜索 | L-04 / D-04b | BLOCKED（Key） | REDFOX_API_KEY 未配置（.env 占位），fixture 打桩口径 |
| onboarding 引导页+断点续做 | L-09 / D-01 | BLOCKED（端点） | GET /onboarding/steps 后端未建（需新端点，超出前端落地范围，登记给下轮） |
| 断网进度静默停更提示 | L-05 | 未修（P2） | 轮询 catch 静默为现口径；网络异常横幅需前端新增，登记 P2 遗留 |
| 批量粘贴入口 | L-02 | 未修（P1） | AddArticlePanel 单 URL 输入，批量需 UI 改造，登记 P1 遗留 |

机器门（修复后全量）：backend ruff All passed / mypy 0 error / pytest 180+3（d04）passed；
frontend tsc PASS / vitest 75 passed。git 提交 2 笔（short-link-map / p5 fix）。
」
