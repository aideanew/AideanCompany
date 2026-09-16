# FE-01 · onboarding 与提问流程

> 项目：AideanBot（P-004）｜依赖：以 T-020 冻结心智为准，可与 BE-01 并行（只改 frontend）｜执行者 worker-a（前端 A）｜审查 reviewer-1

## 1. 目标

落地三入口心智中的 F1 单篇 + 问答主流程：`/onboarding` 3 步建库引导（含断点续做横幅）→ 工作台空态 CTA
“创建第一个知识库” → `/chat` 提问（空间选择、流式回答、citations 带 spaceName/engine）→ 加载/错误/成功四态补齐。
后端缺失的 `GET /onboarding/steps` 若不存在，前端本地记录并登记到遗漏清单，不得擅自加后端接口。

## 2. 工作目录

`E:/Code/AideanBot`

## 3. 允许改动范围

- `frontend/app/onboarding/page.tsx`（引导 3 步 + 断点续做）
- `frontend/app/page.tsx`（工作台空态 CTA + 推荐位；仅允许动 CTA/推荐相关段）
- `frontend/app/chat/page.tsx`（空间选择 + 流式 + citations 展示；仅允许动选择/流式/引用相关段）
- `frontend/components/TopBar.tsx`（仅允许加 onboarding/chat 导航入口）
- `frontend/components/AddArticlePanel.tsx`（仅允许补命中缓存 `hitCache` 提示“命中缓存，秒入库”）
- `frontend/lib/api.ts`（仅允许为上述页面补已存在后端端点的调用封装，禁止新增后端契约假设）
- `frontend/tests/fe01-onboarding-chat.test.tsx`（新建，≥2 个组件测试）
- `E:/Code/AideanCompany/fleet/projects/AideanBot/FE-01/` 下的任务包与证据索引

## 4. 禁止改动

- 不改 `backend/` 任何文件。
- 不改 `frontend/app/spaces/**` 与 `frontend/app/subscriptions/**`（归 FE-02）。
- 不改 `EngineSwitcher.tsx` 与 `PublicLibraryPicker.tsx`（已有组件只读复用，确需改动必须先 BLOCKED 请示）。
- 不引外部 CDN；不改 Fleet 状态；不 commit、不 push。

## 5. 依赖

- T-020 UX 走查心智（F1/F2/F3 定义）与 `ux-walkthrough-AB-P004.md` 遗漏清单。
- 后端契约以现网 `frontend/lib/api.ts` 已有端点为准；契约未给的标“待确认”，不自造接口。

## 6. 实现范围

1. `/onboarding`：3 步（选入口→建空间/粘贴首篇→去问答验证），localStorage 断点续做横幅。
2. 工作台：无空间空态 CTA；有空间推荐位（继续上次/去问答）。
3. `/chat`：空间选择器可用；流式 delta 渲染 + 自动滚底；citations 显示 spaceName（engine 有则同显）。
4. 四态：加载骨架／错误重试／空态引导／成功反馈（含 `hitCache` 秒入库 toast）。
5. 组件测试 ≥2 个（引导步进 + 空态 CTA 或引用展示）。

## 7. 验收命令清单

```bash
cd E:/Code/AideanBot/frontend && npx tsc --noEmit
cd E:/Code/AideanBot/frontend && npx vitest run tests/fe01-onboarding-chat.test.tsx
cd E:/Code/AideanBot/frontend && npx vitest run
```

## 8. 证据路径

- CLI transcript：`E:/Code/AideanBot/.workbuddy/evidence/FE-01-cli.log`
- 运行证据：`E:/Code/AideanBot/.workbuddy/evidence/fe01_run_20260914.txt`
- 测试文件：`E:/Code/AideanBot/frontend/tests/fe01-onboarding-chat.test.tsx`

## 9. CLI 委托（本包强制）

```text
delegate_to: opencode run "<本包全文 + SOUL 六节报告要求 + CLI 证据要求>" --dir E:/Code/AideanBot -m sensenova/sensenova-6.8-flash-lite
```

cwd=`E:/Code/AideanBot`。CLI 全量输出落 `FE-01-cli.log`。

## 10. 报告格式

SOUL 六节 + 模型自述（含 CLI/模型/命令/cwd/exit）+ CLI 证据要求。阻塞回 BLOCKED。

## 11. 重试上限

机器门失败 REWORK 上限 3 次；第 3 次仍失败标 ESCALATED。

## 12. 完成标准（机器门）

- 3 条验收命令退出码全 0；新增测试 ≥2 个全过且全量 vitest 无回归；
- `FE-01-cli.log` 与 `fe01_run_20260914.txt` 落盘；
- reviewer-1 独立审查 PASS/PARTIAL。
