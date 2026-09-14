# Aidean/RagFlow Project Planning Patterns

> Session: 2026-06-01 | Source: `.docs/Parses/` optimization

## Project Structure

- Base: RagFlow v0.24.0 fork, renamed to "Aidean"
- Key directories: `web/` (frontend), `rag/` (backend RAG), `api/` (API layer), `conf/` (config)
- Planning docs live in `.docs/Parses/`

## Document Optimization Patterns

### What was missing in original plans.md
1. No multi-level step guides (tasks described at 1 level only)
2. No dependency chain diagrams showing execution order
3. No rollback plans per operation
4. No "不良影响" (impact analysis) per task
5. No verification checkpoints per task

### What was missing in original todolists.md
1. No global dependency chain overview
2. No "可并行任务" (parallelizable tasks) column
3. No rollback strategy table
4. No execution order within iterations

### What was missing in P-phase files
1. Most files were 1.7-5KB (too brief)
2. Steps were not decomposed to 3 levels
3. Missing "先做什么/后做什么" (what first/what next)
4. Missing rollback plans
5. Missing verification methods

### What was missing at M-level
1. Only M1 existed (22KB, good quality)
2. M2-M13 had no milestone-level overview files
3. No cross-phase dependency analysis

## Optimization Results

| File | Before | After | Key Addition |
|------|--------|-------|-------------|
| plans.md | 20KB | 22KB | Multi-level steps, dependency chains, rollback plans |
| todolists.md | 40KB | 46KB | Dependency chain overview, rollback table |
| P2.4 | 8.7KB | 11.5KB | 6 Tasks × 10-section detail |
| P2.5 | 5.5KB | 7.3KB | 10 Tasks × multi-level steps |
| M2-M13 | 0 files | 12 files | Phase overviews with rollback |

## Key Insight: 3-Tier Document Structure

The 3-tier structure (plans.md → M{N}.md → P{N}.{X}.md) works well for 100+ task projects:
- **plans.md**: Strategic overview for all stakeholders
- **M{N}.md**: Tactical plan for team leads
- **P{N}.{X}.md**: Operational detail for implementers

Each tier answers different questions:
- plans.md: "What are we building and in what order?"
- M{N}.md: "How do we execute this milestone?"
- P{N}.{X}.md: "What exactly do I code right now?"

## Rollback Strategy Types Discovered

For this project, 7 rollback strategy types covered all operations:
1. 配置回滚 (config rollback) — restore config files
2. JSON回滚 (JSON rollback) — restore JSON config
3. 前端回滚 (frontend rollback) — git revert + rebuild
4. 功能开关 (feature toggle) — disable feature flag
5. 默认值回滚 (default value rollback) — restore defaults
6. 参数回滚 (parameter rollback) — restore performance params
7. 全量重建 (full rebuild) — rebuild index/data

## Priority Distribution Pattern

For a 110-task project:
- P0: ~30 tasks (27%) — must fix in 1-2 weeks
- P1: ~41 tasks (37%) — important enhancements in 3-6 weeks
- P2: ~39 tasks (36%) — long-term/architecture in 6-10 weeks

This 27/37/36 split is a reasonable default for optimization projects.
