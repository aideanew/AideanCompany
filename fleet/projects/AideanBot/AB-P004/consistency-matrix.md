# AB-P004 T-021 一致性矩阵（功能×页面×接口×存储×契约）

| 功能 | 页面(源码行号) | 接口(curl 原文) | 存储(psql 原文) | 契约(README/冻结) | 判定 |
|---|---|---|---|---|---|
| F1 单篇入库 | frontend/components/AddArticlePanel.tsx:98 submit() | POST /spaces/{id}/docs 202 {docId,hitCache,hitCount} | content_assets(KNOWLEDGE) / knowledge_documents | README 目标1（公众号链接建知识库）+ 冻结F1 | 已核对（接口字段与代码 shape 一致） |
| F2 整号订阅 | frontend/app/subscriptions/page.tsx:99 进度条 | POST /sources + POST /spaces/{id}/subscriptions + GET /jobs/{id} | source_subscriptions/jobs/job_items | 冻结F2（Job+JobItem Manifest Diff） | 已核对 |
| F3 公共库引入 | frontend/components/PublicLibraryPicker.tsx:68 handleLink | GET /spaces/public + POST /spaces/{id}/links {copied,skipped,total} | knowledge_spaces.is_public / knowledge_documents.source='copy' | 冻结F3（is_public=1 系统空间） | 已核对 |
| 引擎切换 | frontend/components/EngineSwitcher.tsx:72 doSwitch | GET /engines + PATCH /spaces/{id}/engine | knowledge_spaces.engine/engine_kb_id | ADR-0004（5 位默认顺序） | 已核对 |
| 问答引用 | frontend/app/chat/page.tsx:335 消息流 | POST /chat/ask SSE meta.citations{title,spaceName,engine} | （citations 运行时，不落库） | 冻结口径（citations 三元） | 已核对 |

## 存储 psql 原文（关键字段抽样）
- content_assets.hit_count 列存在：hit_count
- knowledge_spaces.is_public 列：is_public
- knowledge_documents.source 列：source
- 公共库探针 AI前沿库：AI前沿库 | t         | system