# Project Steward: 终极架构设计方案 (Hybrid Edition)

## 需求描述
"""
我希望搭建MCP或Skills构建一个文件管理工具，你需要考虑IDE如何高效查找文件内容、更新文件。最终输出可执行的高效设计方案供我选择。

## 参考
1. 参考本项目" RepoMapper/ "。克隆自" https://github.com/pdavis68/RepoMapper "
2. 参考本项目" repomix/ "。克隆自" https://github.com/yamadashy/repomix# "
3. 参考" Skills "实现方案。相关网址记录在本项目" skills.md "
4. 参考" MCP "服务创建规则。

## 全局要求
1. 接收到指令后读取相关文件。
2. 执行编辑操作后修改相关文件。
3. 更新后同步到相关文件。
4. 所有文件保存到项目" docs/ "目录内。

## 功能
1. 项目目录结构
2. 开发计划及当前开发进度
3. 错误记录
4. 记忆功能
5. 项目说明文档
6. 项目部署说明

### 1. 项目目录结构
项目目录结构包括项目内全部的目录和文件(递归)，每个目录和文件必须包含说明，每个文件中的核心方法/函数必须要有说明。
- 1) ** 创建项目递归结构及各目录文件详细说明 **
- 2) ** 更新项目递归结构及各目录文件详细说明 **
- 3) ** 读取项目递归结构及各目录文件详细说明 **

### 2. 开发计划及当前开发进度
- 1) ** 对话中提炼的全局规则 **
- 2) ** 详细的项目多级开发计划 **
		多级开发计划最多包括八级，最少包括三级。
		最小级的开发计划中，必须包括该计划关联的所有代码文件(项目相对路径)的说明。
- 3) ** 每个开发计划的详情 **
		每个开发计划必须包括：当前开发进度、锁定状态、任务模块、任务名称、负责人、状态、开始时间、完成时间、备注
		开发进度：已完成、未完成、进行中 三种状态。
		锁定状态：已锁定、未锁定 两种状态。当处于已锁定状态时，不允许IDE主动编辑。

### 3. 错误记录
- 1) ** 错误记录格式 **
		发生场景、报错描述、报错原因、关联目录文件组、修复方案、修复效果
		发生场景：在什么情况下发现的错误
		报错描述：报错展示的信息
		报错原因：分析原因，如果是不确定的原因，需要注明
		关联目录文件组：多个文件的项目相对路径
		修复方案：当前采用的修复方案
		修复效果：有效、无效
		注意事项：相关备注信息

### 4. 记忆功能
- 1) ** 用户需求总结 **
- 2) ** 对话历史摘要 **
- 3) ** 编辑历史摘要 **

### 5. 项目说明文档
- 1) ** 项目简介 **
- 2) ** 部署详细步骤 **
- 3) ** 项目架构说明 **
- 4) ** 关键文件说明 **
- 5) ** 项目核心功能 **
- 6) ** 竞品功能分析 **
- 7) ** 整体分析和未来规划 **
"""

## 1. 核心理念

本项目采用 **"混合编排 (Hybrid Orchestration)"** 架构，结合 **Skills (大脑/编排)** 与 **Scripts (肌肉/执行)** 的优势，构建一个“重量级”、高可靠的文件管理与辅助开发系统。
本设计深度借鉴了开源项目 `RepoMapper` 的核心技术优势，确保系统的高性能与可扩展性。

### 关键原则
1.  **Code as Truth (代码即真理)**: 业务逻辑和功能说明必须存在于**代码注释 (Docstrings)** 中，而非外部数据库。
2.  **File as Database (文件即数据库)**: 项目状态（进度、锁、错误日志）存储为 Markdown 文件，保持透明性和可读性。
3.  **Separation of Concerns (关注点分离)**: Skills 负责流程控制与触发，Scripts 负责确定性计算与文件操作。
4.  **Enforced Consistency (强制一致性)**: 通过“文档校验回路”和“自动化扫描”，确保文档与代码的强一致性。

### 技术借鉴 (From RepoMapper)
1.  **AST-Based Parsing (Tree-sitter)**: 摒弃正则表达式，采用 `tree-sitter` 进行多语言 AST 解析，确保精准提取类、函数及 Docstrings，无惧代码格式变化。
2.  **Persistent Caching (DiskCache)**: 引入文件级缓存机制（如 `diskcache`），利用文件 `mtime` 进行增量扫描，实现毫秒级响应，避免重复解析。
3.  **Context Optimization (Importance Ranking)**: 引入 PageRank 或引用计数算法，识别项目核心文件（重要性排序），在注入上下文时优先展示高权重文件，防止 Token 溢出。
4.  **Minimalist Server (FastMCP)**: 即使采用 Script 方案，底层设计仍保持接口化，保留未来低成本迁移至 FastMCP 的能力。

### 技术借鉴 (From Repomix)
1.  **XML-First Context**: 采用 XML 标签隔离文件内容，提升 LLM 解析准确度。
2.  **Semantic Compression**: 利用 Tree-sitter 提取 AST 摘要，实现高密度上下文。
3.  **Security Pre-check**: 内置敏感信息扫描，防止密钥泄露。
4.  **Worker Pool Concurrency**: 预留并发处理能力，应对大规模文件扫描。

---

## 2. 系统架构

### Layer 1: Core CLI (`steward.py`)
**定位**: 核心执行引擎，Python 编写，提供确定性的原子能力。

#### 核心组件
1.  **Scanner Engine (扫描引擎)**:
    *   基于 `ast` (Python) 和 `tree-sitter`。
    *   **功能**: 深度解析 AST，提取类/函数 Docstrings，生成 `structure.md`。
    *   **兜底策略**: 若发现无注释函数，在输出中标记 `⚠️ [MISSING DOCSTRING]`。
2.  **Lock Manager (锁管理器)**:
    *   **功能**: 维护 `docs/roadmap.md` 中的任务状态。
    *   **机制**: 软锁定 (Soft Locking)。建立 `Task ID <-> File Paths` 的映射。
3.  **Docstring Validator (文档校验器)**:
    *   **功能**: 这里的 Linter。检查代码是否包含规范的 Docstring。
    *   **用途**: 在代码提交前强制运行，作为质量门禁。
4.  **Context Injector (上下文注入器)**:
    *   **功能**: 运行时数据融合。
    *   **逻辑**: 读取 `roadmap.md` -> 获取任务关联文件 -> 在 `structure.md` (缓存) 中查找描述 -> 返回融合视图。


#### CLI 接口定义 (Commands)
| 命令 | 说明 |
| :--- | :--- |
| `python steward.py scan` | 触发全量/增量扫描，更新 `structure.md`。 |
| `python steward.py roadmap --task <id>` | 读取任务详情，并自动注入关联文件的 Docstring 说明。 |
| `python steward.py lock --task <id> --files <paths>` | 开启任务，激活软锁定追踪。 |
| `python steward.py commit --task <id>` | 提交任务，写入关联文件，释放追踪。 |
| `python steward.py log --error <msg> --context <ctx>` | 结构化记录错误到 `errors.md`。 |
| `python steward.py validate <file_path>` | 校验指定文件的 Docstring 完整性。 |

---

### Layer 2: Skills (`.claude/skills/*.md`)
**定位**: 业务流程编排，定义 "When" 和 "How"。

#### 1. `project-planner` (项目策划师)
*   **触发词**: "制定计划", "下一步", "更新进度"
*   **流程**:
    1.  运行 `python steward.py roadmap` 获取现状（含文件说明）。
    2.  结合用户指令更新计划。
    3.  若用户决定开始任务，运行 `python steward.py lock`。

#### 2. `code-navigator` (代码领航员)
*   **触发词**: "查找代码", "分析结构", "实现功能"
*   **流程**:
    1.  **Pre-Check**: 自动读取 `docs/structure.md` (需先运行 `scan` 确保最新)。
    2.  **Coding**: 指导用户或生成代码。
    3.  **Post-Check (QA Loop)**: 代码生成后，**必须**运行 `python steward.py validate`。
    4.  **Auto-Fix**: 若校验失败，自动提示修复注释。

#### 3. `error-handler` (错误捕获者)
*   **触发词**: "报错", "修复 bug", "异常"
*   **流程**:
    1.  运行 `python steward.py log` 记录现场。
    2.  根据错误上下文，检索相关代码。
    3.  生成修复方案。

---

## 3. 核心工作流 (Workflows)

### 3.1 意图-工具映射 (Context Routing)
通过 Skill 的 `cmd` 指令强制路由：
*   用户问 **"项目结构"** -> 执行 `python steward.py scan` -> 读取 `structure.md`。
*   用户问 **"下一步"** -> 执行 `python steward.py roadmap --active` -> 读取融合视图。

### 3.2 开发闭环 (The Loop)
1.  **Task Start**: 用户选中任务 -> Skill 运行 `lock` 指令 -> 锁定状态激活。
2.  **Coding**: 用户/AI 编辑代码。
3.  **Validation**: 编辑完成 -> Skill 运行 `validate` 指令 -> **检查 Docstring**。
    *   *Fail*: 拒绝提交，要求补全注释。
    *   *Pass*: 继续。
4.  **Sync**: Skill 运行 `scan` 指令 -> 提取新注释 -> 更新 `structure.md`。
5.  **Commit**: Skill 运行 `commit` 指令 -> 将涉及文件写入 `roadmap.md` -> 解锁。

---

## 4. 目录结构规划

```text
project_root/
├── scripts/                 # [NEW] 核心脚本目录
│   ├── steward.py           # CLI 入口
│   ├── scanner.py           # AST 扫描引擎 (基于 Tree-sitter)
│   ├── locker.py            # 锁管理逻辑
│   ├── validator.py         # Docstring 校验器
│   └── requirements.txt     # 依赖 (tree-sitter, diskcache等)
├── .claude/
│   └── skills/              # [NEW] Skill 定义
│       ├── project-planner.md
│       ├── code-navigator.md
│       └── error-handler.md
├── docs/                    # [EXISTING] 数据存储
│   ├── structure.md         # 自动生成
│   ├── roadmap.md           # 状态管理
│   ├── errors.md            # 日志
│   └── ...
└── ...
```
## Appendix B: Insights from Repomix

递归阅读 `repomix` 源码后，我们发现其在 **打包 (Packing)** 和 **上下文优化 (Context Optimization)** 方面有极高的借鉴价值，特别是针对大型代码库的处理。

### 1. XML-First 输出格式
`repomix` 强烈偏向使用 XML 格式作为 LLM 的上下文输入 (`src/core/output/outputStyles/xmlStyle.ts`)。
*   **优势**：XML 标签（如 `<file path="...">`）能清晰地隔离文件内容，避免与代码中的 Markdown 或特殊字符混淆。
*   **借鉴**：Project Steward 的 `read_files` 和 `scan` 命令输出应默认采用 XML 格式，而非简单的 Markdown 代码块，以提高 LLM 解析的准确性。

### 2. 高并发文件处理 (Worker Pool)
为了处理成千上万个文件，`repomix` 使用了 `worker_threads` 池 (`src/core/file/workers/fileCollectWorker.ts`)。
*   **优势**：显著减少 I/O 阻塞，特别是在 Windows 环境下。
*   **借鉴**：虽然初期 `steward.py` 可以单线程运行，但在设计接口时应预留并发处理的能力，特别是对于 `scan` 全局扫描命令。

### 3. 安全性与隐私 (Security Check)
`repomix` 内置了 `validateFileSafety` (`src/core/security`)，在打包前扫描潜在的密钥 (Secrets) 和敏感信息。
*   **优势**：防止将私钥、Token 等敏感数据意外发送给 LLM。
*   **借鉴**：Project Steward 必须引入类似机制，至少应支持 `.stewardignore` 或利用 `.gitignore` 来排除敏感文件，并在读取时进行简单的关键词过滤。

### 4. Tree-sitter 语义压缩
`repomix` 利用 Tree-sitter (`src/core/treeSitter`) 提取代码的关键片段（Captures），而非全量读取。
*   **优势**：能够生成“压缩版”的代码上下文（仅保留类定义、函数签名），在有限的 Context Window 下容纳更多文件。
*   **借鉴**：`steward.py` 的 `read_structure` 命令不应只列出文件名，而应尝试读取（或缓存）文件的 AST 摘要（类/函数名），实现“高密度”的结构视图。

### 5. MCP 工具定义参考
`repomix` 暴露了 `pack_codebase` 和 `generate_skill` 等工具。
*   **借鉴**：Project Steward 的 `steward.py` 可以参考其 `generate_skill` 的思路，不仅仅是管理文件，还可以根据代码自动生成 `skills` 文档，实现自我进化的文档体系。

---

## 4. Implementation Steps

1.  **初始化 Scripts**: 搭建 Python 环境，实现核心 AST 解析与锁逻辑。
2.  **编写 Skills**: 定义 Prompt 和 Shell 命令调用链。
3.  **全量扫描**: 首次运行扫描器，填充 `docs/structure.md`。

