# T-016 P0 资产缓存：现状分析与修复派工建议（t016-analysis.md）

> 任务编号 T-016-ANALYSIS ｜ 角色：gpt-6-astra（PM-1 分析+派工）｜ 2026-09-14
> 工作目录 E:/Code/AideanBot ｜ 基线提交 fae5473（2026-09-14 01:13，管理者代执行"P0 资产缓存"提交）
> 本文覆盖 00:37 旧版草稿（旧版停在错误解释器的 collection 阻断，已被取代）。

---

## 一、根因分析（命令输出原文）

### 1.1 现场状态交底（先说结论：P0 三用例的"3 failed"已被管理者 01:13 提交 fae5473 修复，当前 3/3 全绿）

| 层 | 当前盘上/提交状态 | 证据 |
|---|---|---|
| entities.py | ContentAsset.hit_count 列已加，随 fae5473 提交 | 磁盘 vs `git show fae5473:` 内容一致（仅 CRLF 行尾差异） |
| 迁移 ab1004p0a | PG 已对齐：`alembic_version=ab1004p0a`，`content_assets.hit_count integer default 0` 存在 | psql 原文见 §1.2 |
| asset.py | `hit()` / `mark_stale_docs()` / `upsert_content` hash 变化 version+1 且 hit_count 归零 | 代码 L35-89 |
| kb.py | ingest_url 先查后抓（`_find_source_by_anchor`→READY 复用 hit+1；未命中抓取→hash 比对→`mark_stale_docs`），响应追加 `hitCache`/`hitCount` | L114-192、L194-207 |
| test_p0_asset_cache.py | 已提交为**修复版**：URL_A 带 `?biz=` 锚、`_asset` 辅助函数修正、seeder 改 `upsert_by_sub` | 当前盘上=fae5473 版（`git diff` 空） |

### 1.2 机器证据（命令 + 原文）

**① 全量测试门禁（3 连跑，复现"连跑/回归"窗口）**
```
$ cd E:/Code/AideanBot/backend && uv run pytest tests/ -q
170 passed, 2 skipped, 2 warnings in 16.29s      # skipped=LangBot:5300 不可达冒烟 2 例（预期）
$ uv run pytest tests/ -q     # 再跑
170 passed, 2 skipped
$ uv run pytest tests/ -q     # 第 3 次
170 passed, 2 skipped
```
→ **ix_users_sub 唯一冲突：6+ 次全量连跑 + 单文件隔离，均无法复现。** 已提交 users 表 47 行中**没有** `sub-bt4`（`SELECT count(*) WHERE sub='sub-bt4' → 0`），固定 sub 盲插路径无冲突对象。

**② P0 单文件（当前=修复版）**
```
$ uv run pytest tests/test_p0_asset_cache.py -q
3 passed, 2 warnings in 0.50s
```

**③ 临时把 URL_A 改回裸短链（复现原始"3 failed"中的①③失败形态）**
```
URL_A = "https://mp.weixin.qq.com/s/p0-cache-001"   # 去掉 ?biz= 后重跑
FAILED tests/test_p0_asset_cache.py::test_p0_second_ingest_is_zero_fetch_reuse
FAILED tests/test_p0_asset_cache.py::test_p0_hit_count_counter_increments - a...
2 failed, 1 passed, 2 warnings in 0.56s
```
→ 还原后（`git diff` 空）3 passed。复现确认：**失败对"URL 是否携 biz 锚参数"敏感**。

**④ 缓存查找路径探针（diag4，savepoint 隔离下 1:1 复刻用例①）**
```
[after seeder]  SOURCE ext_id='MjM5MjgwNTQ1MQ=='（已提交残留行）
[ingest1] fetch=1 hitCache=False hitCount=0   ASSET ext='p0-cache-001' READY ver=1 hit=0
CACHE-LOOKUP → source=None（找不到 Source(ext='p0-cache-001') → 缓存必落空，重抓）
[ingest2] fetch=2 hitCache=False hitCount=0
结论: test① 期望 ingest2 fetch_count==1 → 实际 2 → FAIL
```

**⑤ PG 库残留（事务隔离破坏证据）**
```
$ psql -Atc "SELECT sub,email,created_at FROM users WHERE sub LIKE 'sub-p0%' ORDER BY created_at;"
sub-p0-ab004b|p0ab004b@test.local|P0-AB004B|2026-09-14 00:52:05.760852+08
$ psql -Atc "SELECT external_id, name, created_at FROM sources;"
MjM5MjgwNTQ1MQ==|麻籽研究所|2026-09-14 00:49:15.710221+08
counts: users|47  sources|1  assets|0  docs|0  spaces|0
```
→ 连库夹具 conftest 设计为"外层事务统一回滚、零残留"，但 users/sources 出现 00:49/00:52 时刻的**已提交残留行**（时间戳落在管理者代执行 P0 期间；`sub-p0-ab004b` 不是当前 fae5473 测试文件的 sub（当前用 `sub-p0-ab004`），疑似某代调试脚本直接 commit 后清理了脚本、未清理库行——具体提交源**待确认**，见 §三 风险 5）。

**⑥ 门禁**
```
$ uv run ruff check app/ tests/     → All checks passed!
$ uv run mypy app/services/kb.py app/repositories/asset.py app/models/entities.py → Success: no issues found
```

### 1.3 根因定级（原始"3 failed"三案逐一定性）

**R1｜用例②③ 的 `_asset` 辅助函数把 biz 字符串当 source_id 传入 → 误判"asset 不存在"（测试写法缺陷，已修）**
原实现：`AssetRepository.get_by_source_external(_biz_anchor(), _article_key(url))` —— 第一个参数是 `Source.id`（UUID），传 `"MjM5MjgwNTQ1MQ=="` 永远查空，`assert asset is not None` 必炸。修复版（fae5473）先 `select(Source).where(external_id==_biz_anchor())` 取真实 `source.id` 再查资产。§1.2④ 的 `CACHE-LOOKUP → source=None` 即此链路的活体演示。

**R2｜P0 缓存查找锚点与"裸短链"天然失配 → 用例①③ 在裸 URL 下必失败（测试数据缺陷 + 生产口径缺口，半修）**
- 落库侧：`_persist_document → _ensure_source(article.biz, ...)`，桩样本 `parse_biz(SAMPLE_RICH)='MjM5MjgwNTQ1MQ=='`（非空），故 source.external_id=**页面 biz**；
- 查找侧：`_find_source_by_anchor` 依次试 `_biz_from_url(url)`（只读 `?biz=` query 参数）与 `article_key`（URL 末段）；
- 裸短链 `https://mp.weixin.qq.com/s/p0-cache-001` 无 `?biz=` → 锚=`p0-cache-001` ≠ biz → **source 查不到 → 缓存必落空 → 二次 ingest 重抓**（fetch_count=2，用例①断言 ==1 失败；用例③ 同理 hit_count 恒 0）。
- 修复版给 URL_A 加了 `?biz=MjM5MjgwNTQ1MQ==&hid=h0` 使查找/落库锚一致——测试自洽了，但**生产真实形态未覆盖**：微信真实长链携带的是 `__biz`（非 `biz`），裸短链则无 biz query → 见 §二 B-01。

**R3｜机器门②（hash 变化 version+1+superseded）经 Service 门面实际不可达（生产设计缺口 D-2，测试靠绕道通过）**
`ingest_url` 的 READY 命中分支直接短路返回（`kb.py` L132-153），**从不重新抓取比对 hash**；"号主改文"路径（L163-168 `mark_stale_docs`）仅在"缓存未命中→重新抓取"时执行。因此：
- 同 URL 同空间反复 ingest 永远走命中分支，asset.version 永不递增；
- 当前修复版用例②是**绕道通过**：不经过 `svc.ingest_url`，直接调 `AssetRepository.upsert_content` + `mark_stale_docs` 断言 version+1/superseded（fae5473 文件 L125-158 注释自认"命中路径绕过 resolver"）。
- 定性：**repo 层语义已验证；Service 门面"改文感知"缺失**。与冻结口径"content_hash 变化→version+1，旧 doc 标过期"（freeze-scope 冻结1/SPEC L54）对照：机制存在于 upsert 内，但 P0 门面层没有触发它的"抓取比对"钩子（除非外部删缓存/换 URL 形态）。是否算 P0 缺口需管理者裁决——建议按 D-2 派 worker-b 出裁决材料，不在 P0 内强改。

**R4｜ix_users_sub 回归（管理者交底线索）：未复现，降级为"潜伏风险"而非现行根因**
- 触发条件推断（唯一能同时解释"既有用例冲突"与"savepoint commit 语义"假设的机制）：`SqlAlchemyUserStore.upsert_by_sub` 的 IntegrityError 分支执行 `self._session.rollback()`（user.py L84）。`join_transaction_mode="create_savepoint"` 下 session 级 rollback 仅回滚**当前 savepoint**，不会击穿外层事务——**该分支本身安全**；但若任何夹具/脚本把 session 绑在**无 savepoint 的裸连接**上（如直接 `async_sessionmaker(bind=engine)` 而非 bind=connection），IntegrityError 后的 `rollback()` 会终结外层事务，后续 INSERT 与提交态残行相撞即 `ix_users_sub` 冲突。
- 现状证据：`sub-bt4` 已提交行=0（§1.2①），固定 sub 盲插（test_repositories `_make_user`、test_chat_sse 等）当前无冲突对象；P0 新测试已改用 `upsert_by_sub("sub-p0-ab004")`（§1.2⑤ 的 `sub-p0-ab004b` 残行说明中间某代曾 commit 过 sub-p0-* 锚）。
- 结论：**P0 改动引入面=新增了"直接 commit + IntegrityError rollback"两条路径的组合暴露面，但冲突未发生**；处置=清残留 + 保测（见 B-03），不动 conftest 既有语义。

**R5｜test_spaces_api 顺序断言 flake（全量第 2 次跑出现过 1 次）**
`test_space_views_against_real_pg` 断言 docs 列表序 == `["pending","ready","failed"]`，依赖 `list_docs` 的 `order_by(KnowledgeDocument.created_at)`（space.py L139）——同事务内三行 `created_at` 同毫秒时排序非稳定。后续 3 次全量+2 次单跑未再出现 → **潜伏 flake，非 P0 引入**（P0 未触碰 space 域），并入 B-03 观察项。

### 1.4 一句话根因总表

| 案 | 根因 | 属性 | 现状 |
|---|---|---|---|
| ②③ "asset 不存在" | 测试辅助函数误传 biz 当 source_id | 测试写法缺陷 | 已修（fae5473） |
| ① 二次重抓 | 缓存查找锚与裸短链失配（`?biz=` 仅测试里加了） | 测试数据 + 生产口径缺口 | 测试半修；生产裸链场景待 B-01 裁决 |
| ② 经 Service 不可达 | READY 命中短路，无"改文比对"钩子 | 生产设计缺口 D-2 | 测试绕道通过；待裁决 |
| ix_users_sub | savepoint 语义下唯一可解释路径是"无 savepoint 绑定 + IntegrityError rollback"，且需提交态残行 | 潜伏风险 | 未复现；清残留+保测 |

---

## 二、派工清单（步骤号 / 角色 / 验收命令 / 机器门 grep 令牌）

### B-01｜worker-b（9902）｜裸短链缓存口径裁决 + （若裁决为缺口）修复
- 背景：生产真实微信 URL 形如 `mp.weixin.qq.com/s?__biz=…&mid=…`（长链 `__biz`）或裸短链 `/s/xxx`（无 biz query）。当前 `_biz_from_url` 只读 `biz`（kb.py L338-344），裸短链二次 ingest 必重抓，与 P0"命中复用 0 微信请求"目标不完全兑现。
- 动作（两步走，先裁决后动手）：
  1. 出裁决材料：用真实 `__biz` 长链 + 裸短链两种 URL 各跑一遍 `ingest_url`，记录 fetch_count/hitCache（测试写法可加，不改生产逻辑）；
  2. 若管理者裁"裸短链也应命中"→ 修 `kb._biz_from_url`/`_find_source_by_anchor` 补 `__biz` 与短链重定向锚（改 app/ 须在报告中登记）；若裁"P0 只保 biz-锚场景"→ 仅补注释+文档登记。
- 验收命令：`cd E:/Code/AideanBot/backend && uv run pytest tests/test_p0_asset_cache.py -q`（exit 0）
- 机器门 grep 令牌：`hitCache is True`、`fetch_count == 1`、`__biz`（仅当修复实施时出现）
- 约束：不改 conftest；不动 P1 在途文件（`public_library.py` / `ab1004p1a` 迁移，见 §三 风险 4）。

### B-02｜worker-b（9902）｜D-2"改文感知"裁决材料
- 动作：整理 R3 材料（READY 命中短路→version 永不递增的链路图 + 与 freeze-scope 冻结1/SPEC L54 的对照），给管理者一个二选一：P0 内补"命中前 hash 探测钩子"（改 kb.py，需登记）/ 登记为 P1-P2 缺口。
- 验收：材料落 `.workbuddy/evidence/p0_d2_material.md`；若实施修复，追加机器门用例 `svc.ingest_url` 改文路径 version+1（grep 令牌：`mark_stale_docs`、`version == old_version + 1`）。
- 当前不改生产代码（分析角色边界），产出为材料+建议。

### B-03｜worker-b（9902）｜清库残留 + 隔离回归保测
- 动作（只动库与测试，不动 conftest 既有语义）：
  1. 清已提交残行：`DELETE FROM users WHERE sub='sub-p0-ab004b'; DELETE FROM sources WHERE external_id='MjM5MjgwNTQ1MQ==';`（删前快照：§1.2⑤ 输出）；
  2. 给 test_repositories.`_make_user` 等固定 sub 夹具加"插前查后 upsert 降级"注释保测（不改 conftest.py）；
  3. `test_space_views_against_real_pg` 顺序断言改稳定序（对 results 排序或按 created_at+id tiebreak）——R5 flake 修复，属测试写法，允许。
- 验收命令：`uv run pytest tests/ -q`（170 passed/2 skipped，连跑 3 次全绿）
- 机器门 grep 令牌：`sub-bt4`、`ix_users_sub`（回归观察：任何出现即停查 savepoint 绑定）

### F-01｜worker-a / fe-2｜前端 hitCache toast（P1 阶段登记，不提前启动）
- 登记项：`POST /spaces/{id}/docs` 响应新增 `hitCache: true` 时展示"命中缓存，秒入库"toast（SPEC 冻结4 F1）；`hitCount` 可选展示。
- 启动条件：B-01/B-02 关单 + P0 全绿 + P1 公共库阶段开工后（避免与 `public_library.py`/P1 迁移在途面撞车）。
- 验收：前端 tsc/vitest 全绿；grep 令牌：`hitCache`、`命中缓存`。

### 派工顺序（严格串行，冻结 7 口径）
B-03（清残留，30min）→ B-01（裁决材料，管理者裁）→ B-02（裁决材料，管理者裁）→ 按裁决执行修复 → P0 全绿关单 → F-01 随 P1 开工。

---

## 三、风险点

1. **真实微信 URL 形态与测试锚点脱节**（最高）：测试里的 `?biz=` 参数微信不真实下发（真实为 `__biz`/裸短链）；P0 机器门目前"自洽但不反映生产"。B-01 裁决前 P0 不可宣告完成。
2. **hitCount 响应语义**：命中分支返回 `int(cached.hit_count or 0)`（kb.py L152）而 `hit()` 已先 +1 并 flush——即**响应里 hitCount 是递增后的值**；首抓返回 `hitCount=0`。前端 F-01 若按"展示当前累计命中数"实现无歧义；若按"本次是否命中"实现只看 hitCache。登记为契约说明，防 P1 误读。
3. **改文感知缺口（D-2）未裁决**：用户改文后本地缓存资产 hash 滞后，version/superseded 链只在非命中路径触发。风险=检索到旧版本正文。B-02 材料裁决前维持现状并登记。
4. **P1 在途面混排**：工作区已有未提交 P1 面（`M entities.py`、`M space.py`、`?? ab1004p1a_p1_public_library.py`、`?? public_library.py`、`?? evidence/p0_asset_cache_20260913.txt`）——与 fae5473 并行漂移。**worker-b 任何改动前先 `git stash` 或核对 HEAD，避免把 P1 在途面误带进 P0 提交**。
5. **PG 库脏态**（`sub-p0-ab004b` users 残行 + 1 条 sources 残行）：提交源待确认（疑 00:49-00:52 管理者代执行期直接 commit 的调试脚本，脚本已不在仓库——**待确认**）。不清理会持续作为唯一冲突"弹药"潜伏。
6. **R5 flake 未根治前全量门禁非 100% 稳定**：顺序断言依赖同毫秒 created_at 排序，偶发翻转；B-03-3 修复前全量跑出现单例失败先重跑一次确认。
7. **CRLF 行尾**：backend 盘上文件与提交版存在行尾差异（内容级一致），git status 会显示 M——提交前统一按 .gitattributes 处理，防 diff 噪音掩盖真实改动面。

---

## 四、分析角色自述登记

- 改测试文件（允许项）：无净改动——仅做"临时改回裸短链复现 R2"（§1.2③）后已还原，`git diff` 对 test_p0_asset_cache.py 为空（内容级）。
- 改 app/ 生产代码：**无**（边界内执行；B-01/B-02 若实施修复由 worker-b 登记）。
- 落盘文件：`E:/Code/AideanCompany/fleet/projects/AideanBot/AB-P004/t016-analysis.md`（本文件，覆盖 00:37 旧草稿）；诊断脚本 4 份在 `$LOCALAPPDATA/Temp/t016_diag*.py`（不随仓走）。
- 证据命令均可复跑：`cd E:/Code/AideanBot/backend && uv run pytest tests/ -q`（170 passed, 2 skipped）。
