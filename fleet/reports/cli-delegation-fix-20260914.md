# Fleet CLI 委托修复报告（M4 落地，2026-09-14）

## 1. 结论

partially completed —— 分配/配置/任务包/链路修复全部落盘并经机器验证；
4 个新任务包 T-026~T-029 已注册 DRAFT 待派工（派工动作属执行层，留给 Manager/Launcher 首跑）。

## 2. 异常根因回顾

worker 不调 claude/codex/opencode 不是提示词笔误，而是四层均未定义 CLI 环节：
提示词 0 提及且 §5 要求 worker 直接实现；SOUL 无 CLI 授权；通用基座无 CLI 工具集；M4 从未落地。
次要放大因素：SOUL 白名单（E:\Demo\import-test\demo\Test0912 不存在的目录）与任务目录 E:/Code/AideanBot 冲突。

## 3. CLI 实测（本机冒烟全过）

| CLI | 版本 | 登录 | 冒烟 |
|---|---|---|---|
| claude | 2.1.270 | OAuth loggedIn=true (firstParty) | `就绪` (exit 0, 10.8s) |
| codex | 0.153.4 | auth.json + 本机 15721 代理, provider=custom agnes-3.0-flash | `就绪` (exit 0, 15.2s) |
| opencode | 1.18.30 | 4 凭证 + config 含 sensenova/nvidia/modelscope/amd | `就绪` (exit 0, 29.9s) |

## 4. 本次改动清单

| 文件 | 改动 |
|---|---|
| fleet/configs/cli-delegation.md | 新建：CLI×角色×模型分配矩阵 + 命令模板 + 预检 + 证据要求 + 兜底顺序 |
| fleet/projects/AideanBot/BE-01/task-package-BE-01.md | 新建：订阅执行引擎闭环，worker-b × claude |
| fleet/projects/AideanBot/BE-03/task-package-BE-03.md | 新建：SaaS 集成 P3（前置 BE-01），be-2 × codex |
| fleet/projects/AideanBot/FE-01/task-package-FE-01.md | 新建：onboarding 与提问流程，worker-a × opencode(sensenova) |
| fleet/projects/AideanBot/FE-02/task-package-FE-02.md | 新建：交易管理页体系，fe-2 × opencode(nvidia) |
| fleet/console/console.py | COMMON_RULES 追加 CLI 委托 5 条（delegate_to 强制/transcript/codex 参数/证据/兜底） |
| profiles SOUL（worker-a/b/c, fe-2, be-2, be-3） | 重生成 v2：白名单统一 E:/Code/AideanBot + CLI 委托段（.bak-cli-fix-20260914 备份） |
| C:\Users\EDY\AppData\Local\hermes\SOUL.md + fleet/configs/manager-SOUL.md | 追加「四、CLI 委托派工」5 条（备份 .bak-cli-fix-20260914） |
| fleet/console/state/roster.json | worker-b/c, fe-2, be-2, be-3 白名单改 E:/Code/AideanBot，状态 edited(待重启烟测)（备份） |
| fleet/console/state/tasks.json | 注册 T-026~T-029 四包 DRAFT（备份） |

## 5. 分配矩阵（唯一权威见 cli-delegation.md）

| 任务 | 执行者 | CLI | 模型 | 理由 |
|---|---|---|---|---|
| T-026 BE-01 订阅闭环 | worker-b | claude | OAuth 订阅默认 | 关键路径配最强模型，与 b.ai 配额隔离 |
| T-027 BE-03 SaaS P3 | be-2 | codex | agnes-3.0-flash(15721 代理) | API 集成与 Manager/pm 同家族 |
| T-028 FE-01 onboarding/chat | worker-a | opencode | sensenova-6.8-flash-lite | 与原生模型同家族，Key 就绪 |
| T-029 FE-02 交易页体系 | fe-2 | opencode | nemotron-3-ultra | 不同 provider 避免同 Key 并发挤占 |
| 审查 | reviewer-1 | 不用 CLI | agnes-3.0-flash | 执行/审查隔离 |

## 6. 验证记录（真实输出）

- `python -m py_compile fleet/console/console.py` → exit 0；模块加载 COMMON_RULES 含 delegate_to=True；roster 9 角色、tasks 29（新增 4 DRAFT）。
- `ruff check backend`（backend\.venv）→ 3 个 E501（subscription.py 既有长行注释），非本次引入，已写入 T-026 任务包允许清单（执行者可顺手修复但非阻塞门）。
- `npx tsc --noEmit`（frontend）→ 0 错误。
- `pytest --co` → 194 tests collected，基线可跑。
- 三 CLI 冒烟 → 均回「就绪」。

## 7. 未完成事项与风险

1. T-026~T-029 未派工（DRAFT）——派工只经 Manager（`hermes --yolo -z` a2a_call 或控制台按钮），属执行动作。
2. 六个网关未重启——SOUL/config 改动需重启生效；启动前先逐角色烟测。
3. reviewer-1/worker-c 原生链路历史上多次 a2a 超时，审查首跑仍可能超时；升级原则照旧（管理者代审+机器门）。
4. ruff 3 个 E501 为存量问题，T-026 执行时可一并修复。
5. codex 的 skillshub 告警（ragflow-retriever SKILL.md 缺 frontmatter）不影响 exec，未处理。

## 8. 下一步（按序）

1. 重启控制台 + 六个 worker/reviewer 网关（fleet/start-fleet.ps1 或控制台角色页）。
2. 逐角色连通测试（烟测 8/8）。
3. 控制台派工 T-026（worker-b×claude）→ 机器门 → 送审；随后 T-028/T-029 并行、T-027 在 BE-01 DONE 后启动。
4. 全链路回归派 worker-c（原生，不用 CLI）。
