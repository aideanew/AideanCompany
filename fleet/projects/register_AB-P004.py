# -*- coding: utf-8 -*-
"""AB-P004 任务批次注册：T-015 ~ T-025，全部 DRAFT，逐个经 Manager 派工。"""
import json

T = r"E:\Code\AideanCompany\fleet\console\state\tasks.json"
t = json.load(open(T, encoding="utf-8"))
PID = "P-004"
WS = "E:/Code/AideanBot"
now = "2026-09-13 22:58:00"
DOC = "E:/Code/AideanCompany/fleet/projects/AideanBot/AB-P004"

def make(tid, title, assignee, detail, verify, reviewer=""):
    assert not any(x["id"] == tid for x in t["tasks"]), tid
    t["tasks"].append({
        "id": tid, "title": title, "assignee": assignee, "reviewer": reviewer,
        "workspace": WS, "project": PID, "detail": detail, "verify_cmd": verify,
        "state": "DRAFT", "created_at": now, "history": []})

make("T-015", "AB-P004 阶段0 冻结口径一页纸", "pm-1",
     "产品经理产出一页纸冻结文档，写入 " + DOC + "/freeze-scope-AB-P004.md（目录不存在则创建，中文撰写，单文件交付，除该 md 外不改任何其他文件）。先读 E:/Code/AideanBot/README.md、.docs/SPEC-素材资产化与公共知识库.md、.docs/ADR/ADR-0004-知识库引擎可插拔.md，然后按以下冻结口径输出一页纸（逐条原文对齐，不得擅改默认值）：\n"
     "1) 同一套流水线：抓取解析只做一次进 ContentAsset 全局缓存（source+external_id 唯一键，content_hash 做版本）；KnowledgeSpace 只存 KnowledgeDocument(asset_id→space_id 映射)；公共库 = is_public=1 的 system 空间。\n"
     "2) 公共库语义默认 A 拷贝式：用户空间独立 KB，零检索改动；B 引用式扇出只列 M4 不做，本期不测不扣分。\n"
     "3) 引擎口径：ContentAsset markdown 唯一真源，引擎只做建库/上传/检索；默认顺序 ①内置(LangBot系) ②主平台RAGFlow系 ③Coze ④Dify ⑤FastGPT；Notion 按 CMS 对待（存原文/元数据/导出归档），不当默认检索引擎；第三方 Key 只走 env（.env 写真实值，config 用 ${VAR} 引用，绝不写进文档/代码）。\n"
     "4) 三入口流程冻结：F1 单篇（URL→先查缓存→未命中才抓→Asset upsert hit_count+1→Doc→引擎 upload→READY→SSE citations）；F2 多号（POST /sources 注册 biz → POST /spaces/{id}/subscriptions → Job(sync_account)+JobItem(Manifest Diff: DISCOVERED−已有Asset) → worker 逐篇走 F1 → PARTIAL_SUCCESS 单篇重试）；F3 公共库（GET /spaces/public → POST /spaces/{id}/links 批量 copy 进用户 KB → citations.spaceName 标注来源）。\n"
     "5) 迁移冻结：KnowledgeSpace.is_public(bool)/owner_type(user|system)/engine(builtin默认)/engine_kb_id(与 langbot_kb_uuid 双写)、ContentAsset.hit_count、KnowledgeDocument.source(copy默认|link预留)，共 1 个 Alembic 版本，回滚策略登记数据库文档。\n"
     "6) 错误码冻结：复用 10006/20001/20002/20003/30003，整号级新增 30005 PARTIAL_SUCCESS（Job 级）。\n"
     "7) 执行顺序冻结（本项目严格串行）：阶段0冻结→P0资产缓存(后端)→P1公共库拷贝式(前后端)→P2整号订阅(前后端)→P4引擎可插拔(先端口抽取再主平台，SaaS 按 Key 到位逐个接，不并行)→P5 UX 重建→全链路测试→修复闭环→报告。\n"
     "8) 机器门铁律：每阶段完成标准以验收命令退出码为准，员工自述只作参考；端口铁律 3333 唯一，禁止 3334/3335；证据落 .workbuddy/evidence/。\n"
     "完成标准：一页纸 8 条全部落盘成文，末尾附「冻结人：pm-1」与逐条对照表（README/SPEC/ADR 原文行号→冻结点）。",
     "grep:" + DOC + "/freeze-scope-AB-P004.md:冻结,ContentAsset,is_public,30005,builtin",
     "reviewer-1")

make("T-016", "AB-P004 阶段1 P0 资产缓存（ingest_url 先查后抓+hit_count+版本管理+复用单测）", "worker-b",
     "后端 P0 资产缓存落地，工作目录 E:/Code/AideanBot（严格按冻结口径 " + DOC + "/freeze-scope-AB-P004.md 第1/3/5/6条）。改动范围：backend/app/services/kb.py 的 ingest_url 改为先查后抓：URL 归一（biz+article_key，复用 services/normalizer.py）→ 查 (source_id,external_id) 命中 READY 的 ContentAsset 直接复用并 hit_count+1（零微信请求）→ 未命中才抓取 → content_hash(正文md) 比对，号主改文则 version+1 且旧 KnowledgeDocument 标过期（不静默覆盖）→ raw_uri+content_markdown 落库 → 走 LangBot 引擎上传。新增 Alembic 迁移：ContentAsset.hit_count(int默认0)。同步更新 .docs/数据库文档.md（迁移预告+回滚纪律）与 .docs/API接口文档.md（F1 响应追加 hit_cache 布尔字段约定，命中时前端提示“命中缓存，秒入库”）。完成标准（机器门）：① ruff check + mypy + pytest 全绿（pytest 须含新增资产复用单测 ≥3 个：命中复用不抓、hash 变化 version+1 旧 doc 过期、hit_count 自增）；② 若运行环境可起服务则补 curl 证据（同一 URL 两次入库：第二次日志 0 次抓取、hit_count=2）落 .workbuddy/evidence/p0_asset_cache_20260913.txt，环境不可起则写单测证据并如实标注 BLOCKED 项；③ git 提交（feat 前缀中文 subject，不推远端）。报告按 SOUL 六节格式：任务清单/改动文件/验收命令记录含失败/返工记录/未完成事项/结论。",
     "cd E:/Code/AideanBot && python -m ruff check backend && python -m pytest backend/tests -q -k asset or cache or kb",
     "reviewer-1")

make("T-017", "AB-P004 阶段2 P1 公共库拷贝式（迁移+2端点+前端公共库分组/一键引入）", "worker-a",
     "P1 公共库拷贝式前后端联动，工作目录 E:/Code/AideanBot（前置 T-016 已 DONE，先 git 状态确认 P0 已落；严格按冻结口径第2/5/6条，引用式扇出不做）。后端（backend/）：Alembic 迁移新增 KnowledgeSpace.is_public/owner_type/engine/engine_kb_id 与 KnowledgeDocument.source(copy默认|link预留)；新增端点 GET /api/v1/spaces/public（列出 is_public=1 系统空间及其文档数/引擎/更新时间）与 POST /api/v1/spaces/{id}/links {public_space_id}（批量把公共空间 READY 资产 copy 进目标用户空间并建独立 doc，幂等：已 copy 的跳过并返回 copied/skipped 计数）。system 空间与 AI前沿库探针数据：建一个 is_public=1 的系统空间（owner_type=system）用于演示/测试，文档可用现有抓取或占位 markdown 直写 ContentAsset。前端（frontend/）：问答页 /chat 空间选择器加“公共库”分组（拉 /spaces/public）；/spaces/[id] 详情加“一键引入 AI 库”按钮+引入进度（copied/skipped/failed 计数与轮询 doc 状态）；引入后 SSE 问答 citations 需带 spaceName（AI前沿库）。完成标准（机器门）：① ruff/pytest 全绿；② 前端 npx tsc --noEmit + vitest 全绿（新增公共库分组/一键引入组件测试 ≥2 个）；③ curl 证据：GET /spaces/public 200 含 AI前沿库；POST /links 后目标空间 docCount 增加且 READY；SSE citations.spaceName=AI前沿库（抓不到真实 SSE 帧则如实标 BLOCKED）落 .workbuddy/evidence/p1_public_20260913.txt；④ 同步更新 .docs/API接口文档.md 与 数据库文档.md；⑤ git 提交。报告六节格式。",
     "cd E:/Code/AideanBot && python -m ruff check backend && python -m pytest backend/tests -q && npx tsc --noEmit",
     "reviewer-1")

make("T-018", "AB-P004 阶段3 P2 整号订阅（sources/subscriptions/jobs 端点+Diff worker+订阅管理页）", "worker-b",
     "P2 整号订阅后端，工作目录 E:/Code/AideanBot（前置 P1 已落；严格按冻结口径第4条 F2）。后端新增：POST /api/v1/sources {biz|profile_url}（注册公众号 Source，uq_source_type_external 幂等）；GET /api/v1/sources?type=wechat_oa；POST /api/v1/spaces/{id}/subscriptions {source_id, sync_policy}；GET /api/v1/spaces/{id}/subscriptions；GET /api/v1/jobs/{id}（Job 状态+JobItem 进度，轮询用）；POST /api/v1/jobs/{id}/retry（对 PARTIAL 的 Job 按 job_item 状态=FAILED 的单篇重试）。流程：订阅 → Job(kind=sync_account, idempotency_key 幂等) → Manifest Diff（ArticleManifest DISCOVERED 减已有 READY Asset）生成 JobItem → worker 逐篇走 P0 单篇流水线（命中缓存则 0 抓取）→ Job 终态 SUCCEEDED/PARTIAL_SUCCESS(30005)。错误码复用 20001/20002/20003/30003，整号级 30005。清单获取：走现有 redfox 清单源（resolver/services 现有能力），真实外部 Key 不可用时用 fixture 清单打桩并在证据中如实标注（不冒充真实抓取）。前端（frontend/）：/subscriptions 订阅管理页（订阅列表：号名/biz/同步策略/下次同步+任务进度条 Job 轮询 5s+PARTIAL 时“重试失败 N 篇”按钮）。完成标准（机器门）：① ruff/pytest 全绿（新增 Diff/幂等/重试单测 ≥3 个）；② tsc 全绿+新增订阅页组件测试；③ curl 证据：POST /sources→201、POST /subscriptions→Job 创建、GET /jobs/{id} 可见进度、PARTIAL 场景 retry 后可单篇补成功（可构造 1 篇低质 20003 演示 PARTIAL）落 .workbuddy/evidence/p2_subscription_20260913.txt；④ 更新 .docs/API接口文档.md；⑤ git 提交。报告六节格式。",
     "cd E:/Code/AideanBot && python -m ruff check backend && python -m pytest backend/tests -q",
     "reviewer-1")

make("T-019", "AB-P004 阶段4 引擎可插拔（KnowledgeEnginePort 端口抽取+engines 端点+前端切换器）", "worker-b",
     "P4 引擎可插拔架构，工作目录 E:/Code/AideanBot（严格按 ADR-0004，先通一家再逐个接，三家 SaaS 不并行写）。架构：新增 backend/app/providers/engine_port.py 定义 KnowledgeEnginePort(Protocol)：create_kb/upload_file/ingest_status/retrieve/delete_kb/delete_file 六方法；LangBotAdapter 搬运现状 providers/langbot 调用，行为零变更（202→READY→SSE 回归一致）；新增 RagflowAdapter 骨架（主平台 RAGFlow 系，kb 映射主平台库 id，未配置时明确报不可用，不假装可用）；Coze/Dify/FastGPT 只登记 allowlist 位（config 加 kb_default_engine/kb_engine_allowlist/coze_api_key/dify_api_key/fastgpt_api_key/main_kb_api_base/main_kb_api_key 全走 env 占位，.env 真实值由运维填，代码不写死任何 Key）。数据：KnowledgeSpace.engine 默认 builtin + engine_kb_id（与 langbot_kb_uuid 双写，P1 已迁字段则复用）；空间视图追加 engine/engineKbId；SSE citations 追加 engine。端点：GET /api/v1/engines（5 引擎位+Key 可用性：builtin 恒可用，其余按 env 是否配置返回 configured:bool）；PATCH /api/v1/spaces/{id}/engine {engine}（校验 allowlist 与 Key 可用性，未配 Key 则 403 提示找管理员；双写 engine_kb_id）。前端：空间设置页引擎切换器（内置✓/主平台/Coze/Dify/FastGPT，未配 Key 置灰+tooltip“请联系管理员配置”；切换确认模态“切换后新入库走新引擎，旧文档不动”；切换后显示 engineKbId 与状态）。SaaS 缺 URL 上传时用 ContentAsset markdown 转文件兜底（适配器 upload 接受 markdown 文本入参即视为契约④满足）。完成标准（机器门）：① ruff/mypy/pytest 全绿（既有测试不回归）；② 端口抽取单测：LangBotAdapter 六方法与现状调用 1:1 对照 ≥4 个；③ curl：GET /engines 返回 builtin configured=true；PATCH engine=builtin 200；engine=coze（Key 未配）403 带提示；④ tsc 全绿+引擎切换器测试；⑤ 更新 .docs/ADR/ADR-0004 实现状态与 .docs/API接口文档.md §六；⑥ git 提交。报告六节格式，SaaS 三家实接按 Key 到位逐个开，本期 Key 未到位的如实标 BLOCKED 不美化。",
     "cd E:/Code/AideanBot && python -m ruff check backend && python -m pytest backend/tests -q",
     "reviewer-1")

make("T-020", "AB-P004 阶段5 UX 重建（三入口统一心智+笨用户走查+遗漏清单）", "pm-1",
     "P5 UX 重建，pm-1 牵头出走查规格并落地（本任务交付物：走查报告+遗漏清单+前端改动，只改 E:/Code/AideanBot/frontend，不碰 backend）。三入口心智冻结：F1 单篇（粘贴→秒入库提示⚡）/F2 多号（订阅→进度条→部分成功→重试）/F3 公共库（浏览→一键引入→问答带来源）。按三类用户逐一走查并落盘走查记录到 " + DOC + "/ux-walkthrough-AB-P004.md：①小白乱输：空 URL、非文章 URL（期望 10006/20001 友好文案）、短链；②熟手连采 10 篇：批量粘贴/进度/去重提示；③挑剔鬼：断网（SSE 中断“内容可能不完整，请重试”）、后端重启（轮询 30003+重试按钮）、重复提交（幂等覆盖提示）、回退前进（刷新断点）。每步写四列：用户在想什么→期望→实际→落差；落差全部进遗漏清单（P0/P1/P2 三级排定），不许写“无问题”（无落差须给逐条已验证证据）。落地：/onboarding 引导页（3 步建库+断点续做横幅，GET /onboarding/steps 端点若后端无则前端本地记录并登记缺失端点到遗漏清单，不擅自加后端接口）；/ 工作台空态 CTA“创建第一个知识库”；加载/错误/成功四态补齐。完成标准（机器门）：① 走查文档 3×N 步全填+遗漏清单；② tsc 全绿+vitest 新增引导页/工作台测试；③ git 提交前端改动；④ 报告六节格式。",
     "grep:" + DOC + "/ux-walkthrough-AB-P004.md:遗漏清单,落差,断网",
     "reviewer-1")

make("T-021", "AB-P004 阶段6 全链路测试（一致性矩阵+六视角≥6轮+性能实测，只测不改）", "worker-c",
     "全链路测试（只测不改，发现缺陷一律登记不修），工作目录 E:/Code/AideanBot。前置：服务须可运行（docker compose 起 postgres+后端+前端 3333；3333 端口铁律，不得起 3334/3335），环境起不来的项如实标 BLOCKED。产出四份文档（全部落 " + DOC + "/，中文）：\n"
     "1) consistency-matrix.md 一致性矩阵：功能×页面×接口×存储×契约五处对照（功能：F1单篇/F2订阅/F3公共库/引擎切换/问答引用；页面：frontend/app 各页源码行号；接口：curl 原文；存储：docker exec aideanbot-postgres psql 查询原文，含 content_assets/knowledge_spaces/knowledge_documents/jobs/job_items 关键字段；契约：README 目标1-3+冻结口径）。字段名/单位/日期格式/空值/枚举逐项对照，不一致即缺陷 D-xx（附 curl 原文+文件行号证据）。\n"
     "2) perspectives.md 多视角挖遗漏 ≥6 轮：新用户（注册→3步建库）、老用户（断点/多空间）、产品（逐字对 README 五条目标）、前端（加载态/报错文案/浏览器控制台报错）、后端（非法 body 400、并发双提交幂等、重启丢数：重启后端后 Job/doc 状态仍在、端口铁律）、破坏者（XSS 注入 title/question 回显、超大 payload、路径穿越 space_id、绕过页面直调 API 带错 token 401）。每轮记录用例/期望/实际/判定。\n"
     "3) performance-baseline.md 性能基线（实测不许编数）：首屏体感分级（记录 navigate 到首屏可交互秒数+时间戳截图）；GET /spaces、GET /spaces/{id} 各连打 20 次记 p50/p95；200 篇量级：构造 200 条 doc（可用脚本直写 DB 后重启服务），列表页/统计卡渲染时长+截图；代码侧 grep 硬编码/复制粘贴块（同一逻辑 ≥2 处）/加一个字段需改几处（以新增 engineKbId 为例统计文件数），给最小改法建议（只建议不改）。\n"
     "4) asset-reuse.md 资产复用表：同一 URL 两次入库的微信抓取请求数（日志计数）与 hit_count（psql 原文）。\n"
     "缺陷全部进 defects.md（编号/视角/复现步骤/证据/等级 P0-P2/建议修复人：前端→worker-a 或 fe-2，后端→worker-b/be-2/be-3）。完成标准（机器门）：五份文件落盘，grep 自检：perspectives 6 个视角标题齐、consistency-matrix 五处列齐、performance-baseline 有 p95 数字。报告六节格式。",
     "grep:" + DOC + "/performance-baseline.md:p95",
     "reviewer-1")

make("T-022", "AB-P004 阶段7 修复闭环-前端侧（按 P0>P1>P2 修缺陷+回归交接）", "worker-a",
     "修复闭环前端侧（后端类缺陷见 T-023，两份清单来自 T-021 defects.md 的 建议修复人 列，按 P0 级优先、P1、P2 顺序修）。每个修复必须带机器证据：node --check 或 npx tsc --noEmit + 相关 vitest + curl 真调复测 + grep:相对路径:令牌，写入 " + DOC + "/fix-log-frontend.md 逐缺陷登记：缺陷号/根因/改动文件/证据命令+输出片段/复发风险。修完在 fix-log 末尾写“回归交接：缺陷清单+已修 N 个+未修原因”，供 T-024 回归。修不动的（依赖外部服务/需后端配合）如实写 BLOCKED 并注明卡点，不许美化。完成标准（机器门）：fix-log-frontend.md 每条 P0 缺陷有完整四段证据；git 提交。",
     "grep:" + DOC + "/fix-log-frontend.md:缺陷,证据",
     "reviewer-1")

make("T-023", "AB-P004 阶段7 修复闭环-后端侧（按 P0>P1>P2 修后端缺陷+回归交接）", "worker-b",
     "修复闭环后端侧：修 T-021 defects.md 中 建议修复人=后端 的缺陷，按 P0>P1>P2。每个修复带机器证据：python -m ruff check + 相关 pytest + curl 真调 + grep:相对路径:令牌，写入 " + DOC + "/fix-log-backend.md（四段式：缺陷号/根因/改动文件/证据命令+输出片段/复发风险）。迁移类修复必须带 Alembic 回滚说明。修不动的如实 BLOCKED 注明卡点。末尾写“回归交接”。完成标准（机器门）：fix-log-backend.md 每条 P0 缺陷有完整证据；pytest 全绿；git 提交。",
     "grep:" + DOC + "/fix-log-backend.md:缺陷,证据",
     "reviewer-1")

make("T-024", "AB-P004 阶段7 回归测试（原缺陷复测+阶段5/6 抽样重跑，只测不改）", "worker-c",
     "回归测试（只测不改）：输入=两份 fix-log（frontend/backend）+ defects.md。逐项复测已修缺陷（按原复现步骤+证据命令原样重跑），复发即 REWORK 打回并带证据（截图/日志原文）；同时抽样重跑阶段5 三入口走查（小白 3 用例）与阶段6 六视角中后端视角+破坏者视角共 2 轮。结果写 " + DOC + "/regression-AB-P004.md：缺陷号/复测判定(修复确认/复发/未修BLOCKED)/证据 三列+抽样轮结果。复发缺陷登记回 defects.md 状态列（REWORK 次数+1，上限 3 次，第 3 次标 ESCALATED 上报）。完成标准（机器门）：regression 文档每条已修缺陷有判定行；grep 自检含 REWORK/ESCALATED 关键词。报告六节格式。",
     "grep:" + DOC + "/regression-AB-P004.md:复测,BLOCKED",
     "reviewer-1")

make("T-025", "AB-P004 独立审查（四态判定 PASS/PARTIAL/REWORK/BLOCKED，只审不改）", "reviewer-1",
     "独立审查（只审不改）：审查范围=T-015~T-024 全部交付物（冻结口径/P0-P4 代码与测试/UX 走查/全链路测试表/修复回归）。对照验收：①每阶段机器门是否真过（抽跑 ruff/pytest/tsc 各一轮+抽验 grep 门文件存在）；②冻结口径 8 条逐条对照实现是否漂移；③缺陷闭环：P0 级是否全修或有 BLOCKED 依据、REWORK 上限 3 次是否被突破；④端口铁律 3333 唯一/密钥纪律（代码与文档 grep 无明文 Key）/证据目录 .workbuddy/evidence 台账；⑤文档同步：API接口文档/数据库文档/文档索引与实际实现一致。判定四态之一：PASS（全过）/PARTIAL（P2 级遗留有登记）/REWORK（P0/P1 级未闭环）/BLOCKED（环境或外部依赖卡死）。判定书写 " + DOC + "/review-verdict-AB-P004.md：首行必须是「判定：PASS|PARTIAL|REWORK|BLOCKED」四选一，其后逐条引用证据（文件行号/curl 原文/命令输出）。发现代码缺陷只登记不修改。",
     "grep:" + DOC + "/review-verdict-AB-P004.md:判定",
     "")

json.dump(t, open(T, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("registered T-015..T-025, total tasks:", len(t["tasks"]))
