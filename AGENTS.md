# 全局规则（AI IDE 执行本舰队工作的流程规则文件）

> 本文件是 AI IDE（ZCode / Cursor 等）在本工作区执行任务的**流程规则与行为规范**。每次会话自动读取。
> 配套文件：[启动说明.md](启动说明.md)（开机/重启/日常操作）· [默认基础配置.md](默认基础配置.md)（端口/模型/角色/门禁基线）。

## 一、语言（最高优先级，对所有会话生效）
- **全局使用中文**：所有对话回复、分析说明、报告、总结一律用中文输出。
- 代码、命令、文件路径、标识符、报错原文保持原样（不翻译）。
- 生成的面向用户的文档/注释/提交信息默认中文，除非任务明确要求其他语言。

## 二、项目背景（AideanAgentFleet 舰队）
- 本仓库是 Hermes A2A 多 Agent 舰队：控制台(5000) + Manager(9900) + 8 员工网关(9901-9911) + 贪吃蛇演示(5410/5411)。
- 核心目录：`fleet\console`（控制台源码+state 状态）、`fleet\configs`（SOUL 模板/配置备份）、`fleet\tools`（new-project / export-fleet / import-fleet 脚本）、`fleet\reports`（六节报告）、`E:\Demo\*`（项目工作区白名单）。
- 修改 `console.py` 后需重启控制台生效；修改 profile `config.yaml`/`SOUL.md` 后需重启对应网关；**修改 `config.yaml` 后 `.env` 不用重启**（按会话加载）。
- `new-project.ps1` 内嵌 `C:\Program Files\Python313\python.exe` 绝对路径——换 Python 版本/换电脑时记得改这一行（import-fleet 的路径改写会处理 fleet 内文件，但装机时注意）。

## 三、角色名册（2026-09-13 基线）
| 角色 | ID | 端口 | 流程权限 | 模型 |
|---|---|---|---|---|
| Manager | default | 9900 | 总调度（唯一入口） | agnes-3.0-flash |
| 产品经理 | pm-1 | 9907 | worker（产出文档） | agnes-3.0-flash |
| 前端一组 | worker-a | 9901 | worker | sensenova-6.8-flash-lite |
| 前端二组 | fe-2 | 9908 | worker | sensenova-6.8-flash-lite |
| 后端一组 | worker-b | 9902 | worker | qwen3.8-flash（需10808代理） |
| 后端二组 | be-2 | 9909 | worker | qwen3.8-flash（同上） |
| 后端三组 | be-3 | 9910 | worker | qwen3.8-flash（同上） |
| 测试工程师 | worker-c | 9903 | worker | DeepSeek-V4-Flash-0731（ModelScope 免费档） |
| 审查员 | reviewer-1 | 9911 | reviewer（只审不改） | agnes-3.0-flash |
- 全员 NVIDIA nemotron-3-ultra 兜底（worker 侧 fallback_providers）。**注意**：真机核验发现仅 worker-a/b/c 的 config 有 `fallback_providers` 段并引用 NVIDIA 变量，其余 5 个 profile 该段为空——名册口径与此文档 §2/§8 的占位登记已注明该不一致，改兜底策略时先对齐。

## 四、Key 管理铁律
- API Key 只进 `.env`（config 用 `${VAR}` 名字引用）。`.env` 里写真实值、**禁止 `${VAR}` 字面量**（dotenv 不做插值——2026-09-13 曾因此 be 系 401）。绝不写进 config/roster/日志/脚本/报告。
- 2026-09-13：迁移事故的模型 Key 已全部回填（主 AGNES/EXA/OPENROUTER，pm-1/fe-2/be-2/be-3/reviewer-1 各自变量，worker-a SENSENOVA、worker-b BAI、worker-c MODELSCOPE，worker-c 的 EXA 刚同步）。占位清单见[默认基础配置.md §8](默认基础配置.md)（GPT_GE/APIFREE/NVIDIA 兜底三项缺失不影响当前运行）。
- 每个角色实际消费的 Key 以其 profile config 的 `${VAR}` 为准（不是供应商名）：pm-1→PM_1_KEY、fe-2→FE_2_KEY、be-2→BE_2_KEY、be-3→BE_3_KEY、reviewer-1→REVIEWER_1_KEY。
- be 系三角色（worker-b/be-2/be-3）走 10808 代理——代理变量在**各自 profile .env**（主 .env 没有）；改坏即 401，排查先 curl 直测 Key 本体。
- 重启任何网关前，先跑一轮控制台烟测（角色页逐个「连通测试」）确认 8/8 就绪。

## 五、执行流程（AI IDE 接到舰队相关任务时的标准动作）
1. **先探后动**：任何派工/送审操作前，先探目标角色端口（`http://127.0.0.1:<port>/.well-known/agent-card.json`）是否 200；离线先启动，不要绕过拦截。
2. **派工只经 Manager**：网页控制台或 `hermes --yolo -z`（Manager a2a_call），绝不直连 Worker 执行任务。
3. **机器门判定**：任务 PASS 与否只看验收命令退出码（`grep:相对路径:令牌` 模式优先）；员工自述只作参考。
4. **状态机不可跳步**：DRAFT→ASSIGNED→DOING→SUBMITTED→REVIEWING→DONE/PARTIAL/REWORK/BLOCKED；非法迁移直接拒绝。依赖门已由 DAG 调度器接管（`fleet\dispatcher\scheduler.py` 的 `topological_ready` + 控制台 `/api/ready-wave`，推荐波每角色 1 并发，循环依赖/脏引用自动检出）——调度器只推荐、不自动派工，派工仍需人工点按钮走 `/tasks/<id>/dispatch` 完整拦截链（离线/依赖/状态机）。
5. **429 处置**：控制台派工线程自带退避重试（60s→120s 共 2 次）；手动操作遇到 429 等 60-120 秒再试；ModelScope 免费档当日配额耗尽则换角色/次日再跑。
6. **高危动作必须停下等用户批准**：删文件/删库、git push --force、发布生产、修改 Hermes 自身配置、任何花钱操作。
7. **报告纪律**：项目收口必须产出六节报告（任务清单/改动文件/验收命令记录含失败/返工记录/未完成事项/结论）到 `fleet\reports\`，并附执行就绪总表；六节之后必须附加**完成度报告**——逐角色（含 Manager 自身与补位执行者）列出「角色 | 模型提供商 | 模型 | 任务 | 评价」五列表格，评价只允许五档：圆满完成无返工 / 完成有返工 / 部分完成有缺口 / 受阻未产出 / 未派工（判定依据=机器门证据，模型信息=员工自述+名册交叉核对）。详见 manager-SOUL.md 工作循环第 8 条。

## 六、PowerShell 5.1 坑位备忘（写脚本前必读）
- 无 BOM 的 UTF-8 脚本中文会按 GBK 解析 → `.ps1` 必须 UTF-8 **带 BOM**。
- here-string 内嵌 Python/路径时警惕双重转义（`\f`→换页符事故）；路径一律用正斜杠。
- git/外部命令的 stderr 在 `$ErrorActionPreference=Stop` 下会被当错误 → 用 `2>&1 | Out-Null` 包裹。
- dotenv 不做 `${VAR}` 插值 → .env 里写真实值，`${VAR}` 只允许出现在 config.yaml。

## 七、阶段路线快照
- **已完成**：R0（残留清理+密钥卫生+MCP 归属+审查员重建）；M1 最小闭环；Test0912 贪吃蛇真实项目闭环（含返工+诚信考验）。
- **M2 待办**（Test091220-待办清单）：用户填 README 契约 → Manager 用 agnes 串行小任务跑全自动首跑（正式大任务再切 gpt-6-astra，3 行切换见方案文档 §2）。
- 后续：M3 Git 分支隔离 → M4 三基座（需 CLI 登录）→ M5 开机自启+巡检 → M6 预算门 → M7 多机。
