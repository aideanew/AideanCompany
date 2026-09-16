# AideanAgentFleet 小白运行手册（v1）

> 日期：2026-09-15
> 适用：本机 Windows + 控制台 5000 端口。
> 原则：小白只碰按钮和命令行两条路径；状态一律由控制台读写，手改 JSON 无效且会被完整性校验标红。

## 1. 冷启动（每次开机后）

1. 打开 PowerShell。
2. 进入项目：`cd E:\Code\AideanCompany`。
3. 启动全栈：`python fleet\tools\restart_console_v3.py`。
4. 浏览器打开 `http://127.0.0.1:5000`。
5. 看首页健康检查：全绿才算“可派工”。

环境变量（可选）：

```powershell
$env:FLEET_API_TOKEN="你的令牌"        # 设置后所有写接口需要 Bearer
$env:FLEET_ALLOW_CLI_EXEC="1"          # 允许 Runner 真实拉起 claude/codex/opencode
$env:TEST_FLEET_ENV="1"                # 测试环境：禁用 v3/gpt-6-astra
```

## 2. 派工

1. 「任务」页 → 找到任务 → 「派工（经Manager）」。
2. 被拦截时按页面提示处理（网关离线/前置未完成/schema 缺字段），不要手改 JSON。
3. 派工后任务进入 DOING；Manager 回执后转 SUBMITTED。

## 3. 验收与收口

1. SUBMITTED 后点「机器验收」：verify_cmd 真实执行，退出码即判定。
2. 验收通过 → 「送审」。
3. reviewer 判 PASS 后 → 「收口DONE」。
4. 收口被拒时页面会列出全部缺口（transcript/审查判定/证据文件），补齐再来。

注意：`grep:任务包文档:关键词` 形式的验收会被直接拒绝；必须指向真实产物或真实命令。

## 4. 失败与重试

- 429/超时/5xx：自动按 `model-pool.json → retry`（10 秒 × 10 次）重试。
- 401/402/403/quota/model_not_found：跳过退避直接切换候选，事件流见 `launch:model_switch`。
- 10 次失败：任务 BLOCKED，页面显示原因；处理后重新派工。

## 5. 崩溃恢复

1. 控制台重启后先跑：`python fleet\tools\lifecycle\shadow_sync.py`（影子同步 SQLite，不改动 tasks.json）。
2. 查看任务页状态：RUNNING/DOING 的任务按 lease 判断是否回收。
3. 不要手工把任务改成 DONE；用页面的验收/送审/收口流程重走。

## 6. 审计与安全

- 审计链校验：`GET /api/audit-chain`，`ok:false` 说明有人改过日志，停止操作并汇报。
- 密钥：只放 `secrets/.env`；设计文档只允许 `${VAR}` 占位；旧 Key 已视为泄露需轮换。
- 扫描：验证阶段执行 `python fleet\tools\verify\secret_scan.py`（待创建）与 `python fleet\tools\verify\recheck.py`。

## 7. 每日收尾

1. 备份三件套自动位置：`fleet/state/backups/`。
2. 检查 `fleet/reports/` 当日完成度报告。
3. 关闭浏览器即可；控制台进程可常驻，重启机器后按 §1 重新拉起。
