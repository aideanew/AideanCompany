# AB-P004 阶段0 冻结口径一页纸（freeze-scope）

> 任务编号：T-015 ｜ 冻结对象：AB-P004（素材资产化 + 公共知识库 + 整号订阅 + 引擎可插拔）
> 冻结日期：2026-09-13 ｜ 冻结人：pm-1
> 源文档（逐条对齐依据）：
> - `E:/Code/AideanBot/README.md`（下称 **README**）
> - `E:/Code/AideanBot/.docs/SPEC-素材资产化与公共知识库.md`（下称 **SPEC**）
> - `E:/Code/AideanBot/.docs/ADR/ADR-0004-知识库引擎可插拔.md`（下称 **ADR**）
>
> 铁律声明：本一页纸为 AB-P004 阶段0 冻结口径，是全部后续阶段的验收基准。逐条与源文档原文对齐，默认值不得擅改；任何口径变更必须走新阶段冻结，不得在实现中偷改。

## 冻结项（共 8 条）

### 冻结 1：同一套流水线（全局缓存 + 空间映射 + 公共库即系统空间）
- 抓取解析**只做一次**，结果进 `ContentAsset` 全局缓存；`ContentAsset` 唯一键为 `(source, external_id)`，`content_hash` 做版本（正文变化 → `version+1`，旧 doc 标过期，不静默覆盖）。
- `KnowledgeSpace` 只存 `KnowledgeDocument(asset_id → space_id)` 映射（`uq_doc_asset_space` 唯一），不存正文。
- 公共库 = `is_public=1` 的 **system 空间**（owner 为 system 用户），不是独立数据形态。

### 冻结 2：公共库语义默认 A 拷贝式
- 默认方案 **A 拷贝式**：用户空间拥有独立 KB，公共库内容通过 `copy` 复制进用户空间，**零检索改动**（`ask`/`citations` 现有链路不动）。
- 方案 **B 引用式扇出**仅列 M4，**本期不做、不测、不扣分**；`KnowledgeDocument.source=link` 字段仅预留，不启用。

### 冻结 3：引擎口径（ContentAsset 为唯一真源，引擎五槽位，Key 只走 env）
- `ContentAsset.content_markdown` 是**唯一真源**；引擎只做 建库 / 上传 / 检索，不参与抓取解析。
- 引擎默认顺序（5 槽位）：① 内置引擎（LangBot 系，`engine="builtin"`，默认全部用户）→ ② 主平台 RAGFlow 拓展系（`main`）→ ③ Coze → ④ Dify → ⑤ FastGPT。
- **Notion 按 CMS 对待**：存原文/元数据/导出归档，**不当默认检索引擎**。
- 第三方 API Key **只走 env**：`.env` 写真实值，`config.py` 用 `${VAR}` 引用（`kb_default_engine="builtin"`、`kb_engine_allowlist="builtin,main"`，SaaS 按 Key 到位逐个开）；Key 绝不写进文档、代码与 Git 历史。

### 冻结 4：三入口流程冻结（F1 / F2 / F3）
- **F1 单篇**：粘贴 URL → 先查 `ContentAsset` 缓存 → 未命中才抓取解析 → Asset upsert（`hit_count+1`，命中缓存提示"命中缓存，秒入库"）→ `Doc(asset,space)` → 引擎 upload → `READY` → SSE（`meta→delta→done citations` 含标题）。
- **F2 多号**：`POST /sources` 注册 biz → `POST /spaces/{id}/subscriptions` → `Job(sync_account)` + `JobItem`（Manifest Diff = `DISCOVERED − 已有 Asset`）→ worker 逐篇走 F1 → `SUCCEEDED`/`PARTIAL_SUCCESS`（可单篇重试：`GET /jobs/{id}` 进度 + `POST /jobs/{id}/retry`）。
- **F3 公共库**：`GET /spaces/public` → `POST /spaces/{id}/links` 批量 `copy` 进用户 KB → `citations.spaceName` 标注来源。

### 冻结 5：迁移冻结（SPEC 原话：共 1 个 Alembic 版本；实现口径注记见下 DEF-4）
- `KnowledgeSpace.is_public: bool = False`（公共库标记）
- `KnowledgeSpace.owner_type: str = "user|system"`
- `KnowledgeSpace.engine: str = "builtin"`（默认内置）+ `KnowledgeSpace.engine_kb_id`（与 `langbot_kb_uuid` **双写**）
- `ContentAsset.hit_count: int = 0`（复用计数，热点与清理依据）
- `KnowledgeDocument.source: str = "copy|link"`（默认 `copy`；`link` 预留给 M4 扇出，不启用）
- 原口径「合计 **1 个 Alembic 版本**；回滚策略登记数据库文档」。
- 口径注记（DEF-4，T-025 独立审查 2026-09-14，仅注记不改 SPEC 原文）：SPEC L36 原话为「1 个 Alembic 版本」；实际落地 3 个——`ab1004p0a`（P0 hit_count）/ `ab1004p1a`（P1 公共库 5 列）/ `ab1004d04a`（T-023 D-04 短链映射表，修复期新增）。随 T-023 短链修复必然漂移，回滚策略全量登记 AideanBot `.docs/数据库文档.md` §六~§八；本注记按「实现为准」如实登记，不追溯篡改 SPEC 原文。
- 纪律不变：`users.sub` 锚点不变、幂等键不变、余额/tier 不落库。

### 冻结 6：错误码冻结
- 复用既有错误码：`10006 / 20001 / 20002 / 20003 / 30003`。
- **整号级新增 `30005 PARTIAL_SUCCESS`（Job 级）**——仅用于 F2 整号订阅 Job 部分成功的状态表达。

### 冻结 7：执行顺序冻结（本项目严格串行，不得并行）
1. 阶段0 冻结（本一页纸）
2. P0 资产缓存（后端）
3. P1 公共库拷贝式（前后端）
4. P2 整号订阅（前后端）
5. P4 引擎可插拔（先端口抽取，再主平台；SaaS 三家按 Key 到位**逐个接**，不并行；顺序 Coze → Dify → FastGPT）
6. P5 UX 重建
7. 全链路测试
8. 修复闭环
9. 报告

### 冻结 8：机器门铁律（验收与证据）
- 每阶段完成标准以**验收命令退出码**为准；员工自述只作参考。
- 端口铁律：**3333 唯一**，禁止 3334 / 3335。
- 证据统一落 `.workbuddy/evidence/`（`p{0,1,2}_*.txt` / `adr0004_p*_*.txt`），台账登记，不混业务提交批。
- 门禁基线：`ruff / mypy / pytest / tsc / vitest` 全绿 + 运行（`202→READY→SSE` 帧级）+ 清理（探针空间可删；`DELETE 405` 未关单前登记豁免）。

---

## 逐条对照表（源文档原文行号 → 冻结点）

| 冻结点 | 源文档 | 原文位置（行号） | 原文要点（对齐依据） |
|---|---|---|---|
| 冻结 1 | SPEC | L24 | "抓取解析只做一次进 ContentAsset 全局缓存；KnowledgeSpace 只存 KnowledgeDocument(asset_id→space_id) 映射；公共 AI 库就是 is_public=1 的系统空间" |
| 冻结 1 | SPEC | L27 | `Source(biz) 1:N ArticleManifest → ContentAsset(source+external 唯一，hash 版本)` |
| 冻结 1 | SPEC | L34 | 现表零改动复用：`content_assets(uq_asset_source_external)`、`knowledge_documents(uq_doc_asset_space)` |
| 冻结 1 | SPEC | L54 | `content_hash(正文md)` 变化 → `version+1`，旧 doc 标过期，不静默覆盖 |
| 冻结 1 | README | L1, L5-L6 | 信息源（核心：公众号）→知识库→机器人闭环；全部文章/单篇两种方式 |
| 冻结 2 | SPEC | L15 | F3：`POST /spaces/{id}/links` 批量 `copy` 后本空间可问，`citations.spaceName` 标注来源 |
| 冻结 2 | SPEC | L20 | "引用式多库扇出问答（列 M4，见 §六 P3）" |
| 冻结 2 | SPEC | L83-L84 | 用户"选用" = `POST /links` 批量 copy；"引用式（link/扇出）列 M4，不默认启用" |
| 冻结 2 | SPEC | L106-L110 | P3 引用式扇出标注"可选 M4" |
| 冻结 3 | ADR | L9 | "默认顺序：① 本项目内置引擎（LangBot 系）② 主平台知识库（RAGFlow 拓展系）③ 第三方 SaaS API" |
| 冻结 3 | ADR | L17-L21 | 5 引擎槽位：E0 内置 LangBot 系 / E1 主平台 RAGFlow 拓展 / E2 Coze / E3 Dify / E4 FastGPT |
| 冻结 3 | ADR | L23 | "Notion 列 CMS（存原文/元数据，不当 RAG 引擎）" |
| 冻结 3 | ADR | L37 | "ContentAsset(content_markdown) 是唯一真源；引擎只收文件/文本上传，不参与抓取解析" |
| 冻结 3 | ADR | L40 | "第三方 API Key 只走 env/密钥服务 + 用户级 Key 加密列，不入库明文、不入码" |
| 冻结 3 | ADR | L61-L62 | `kb_default_engine="builtin"`；`kb_engine_allowlist="builtin,main"`（先开内置+主平台；SaaS 按 Key 到位逐个开） |
| 冻结 3 | ADR | L63-L67 | `coze/dify/fastgpt_api_key`、`main_kb_api_key` 均只走 env |
| 冻结 3 | README | L16 | "API Key 只经环境变量注入，禁止写入任何文档、代码与 Git 历史" |
| 冻结 4 | SPEC | L13 | F1 验收：`POST /spaces/{id}/docs {url}` → `202` → 轮询 `READY` → SSE citations 含标题 |
| 冻结 4 | SPEC | L64-L67 | F1 流程：粘贴 URL → resolve/extract/quality → Asset upsert(hit_count+1) → Doc → 引擎 upload → READY → SSE |
| 冻结 4 | SPEC | L71-L77 | F2 流程：`POST /sources {biz|profile_url}` → `POST /spaces/{id}/subscriptions` → `Job(sync_account)+JobItems(Manifest Diff = DISCOVERED − 已有 Asset)` → worker 逐篇走 F1 → `SUCCEEDED/PARTIAL_SUCCESS` + 单篇重试 |
| 冻结 4 | SPEC | L14, L81-L84 | F3：`GET /spaces/public`（AI前沿库 is_public=1）→ `POST /links` 批量 copy → `citations.spaceName` 标注来源 |
| 冻结 5 | SPEC | L36 | "新增迁移（1 个 Alembic 版本）" |
| 冻结 5 | SPEC | L38-L43 | `is_public: bool=False`；`owner_type: "user|system"`；`hit_count: int=0`；`source: "copy|link"`（默认 copy，link 预留 M4） |
| 冻结 5 | ADR | L38 | `KnowledgeSpace.engine: str="builtin|main|coze|dify|fastgpt"` + `engine_kb_id`（与 langbot_kb_uuid 并存，迁移时双写） |
| 冻结 5 | ADR | L81-L82 | P1：迁移 `engine/engine_kb_id`（`langbot_kb_uuid` 双写），建空间默认 `builtin`；"回滚策略登记数据库文档" |
| 冻结 5 | SPEC | L45 | 纪律：`users.sub` 锚点不变；幂等键不变；余额/tier 不落库 |
| 冻结 6 | SPEC | L124 | "错误码复用 10006/20001/20002/20003/30003，整号加 30005 PARTIAL_SUCCESS（Job 级）" |
| 冻结 6 | SPEC | L14 | F2 验收含 `PARTIAL_SUCCESS` 可单篇重试 |
| 冻结 7 | SPEC | L88-L104 | P0 资产缓存 → P1 公共库拷贝式（前置 P0）→ P2 整号订阅（前置 P0），逐步落地且可对照检查 |
| 冻结 7 | ADR | L74-L77 | P0 端口抽取（前置无，行为零变更） |
| 冻结 7 | ADR | L84-L87 | P2 主平台 RAGFlow 系（前置 P1） |
| 冻结 7 | ADR | L89-L92 | P3 SaaS 三家逐个接："顺序建议：Coze → Dify → FastGPT"，每家独立 evidence，不并行 |
| 冻结 7 | 任务包 T-015 | — | 串行链：阶段0→P0→P1→P2→P4→P5→全链路测试→修复闭环→报告；P5 UX 重建 / 全链路测试 / 修复闭环 / 报告为本任务包冻结项（源文档未编号，按任务包口径） |
| 冻结 8 | SPEC | L128 | "每阶段：门禁（ruff/mypy/pytest/tsc/vitest）+ 运行（202→READY→SSE 帧级）+ 端口（3333 唯一）+ 清理" |
| 冻结 8 | SPEC | L129 | "证据落 .workbuddy/evidence/p{0,1,2}_*.txt，台账登记，不混业务提交批" |
| 冻结 8 | ADR | L77, L82, L92 | 各阶段 evidence 命名：`adr0004_p0_*.txt` 等 |
| 冻结 8 | 任务包 T-015 | — | "验收命令退出码为准，员工自述只作参考；禁止 3334/3335"（任务包口径） |

---

**冻结人：pm-1**
