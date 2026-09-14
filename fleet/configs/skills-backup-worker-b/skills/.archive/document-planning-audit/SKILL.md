---
name: document-planning-audit
description: Audit planning documents for software refactoring projects — verify requirement coverage, cross-document consistency, and global effectiveness chains.
category: software-development
---

# Document Planning Audit

Audit planning documents for software refactoring projects. Verify completeness against requirements, validate each plan can solve its target need, and confirm end-to-end effectiveness chains.

## When to Use

- Reviewing `.docs/Parses/` or similar planning document directories
- Auditing refactoring plans against a requirements file (readme.md, AGENTS.md, spec documents)
- Verifying that configuration changes propagate globally through multi-layer architectures
- Checking document consistency across versions (v1→v2→v3)

## Audit Checklist

### 1. One-to-One Requirement Coverage

For each requirement in the source document (readme.md, AGENTS.md):
- [ ] A dedicated plan file exists that targets this specific requirement
- [ ] The plan file cites the exact requirement source (e.g., `readme.md 二.2.(1)`)
- [ ] The plan's tasks are atomic and executable (not descriptive)

**Pitfall**: A plan that describes "what to build" but not "how to build it" is incomplete. Every task needs: steps, involved modules, priority, side effects, confidence level.

### 2. Full Requirement Coverage

Map every requirement to a plan file:

| Requirement | Plan File | Can Solve? | Notes |
|------------|-----------|-----------|-------|

**Coverage must be 100%**. Any gap is a P0 finding.

### 3. Global Effectiveness Chain (CRITICAL)

For configuration-driven features (model providers, system settings, etc.), verify the COMPLETE data propagation chain:

```
Source of Truth → Storage Layer → User Layer → Frontend Perception
```

**The chain must be complete at EVERY layer:**

| Layer | Question | If Missing |
|-------|----------|-----------|
| **Code-level registration** | Is the entity registered in code enums, constants, and config files? | Admin UI cannot manage what doesn't exist in code |
| **Configuration storage** | Is there a config file (JSON/YAML) with the entity's data? | Service startup fails to load |
| **Database persistence** | Are DB tables updated at runtime (not just startup)? | Changes require service restart |
| **User-level propagation** | Do existing users automatically get new entities? | Only new users see changes |
| **Cache invalidation** | Is in-process cache cleared after updates? | Multi-instance deployments stale |
| **Frontend real-time perception** | Does the UI refresh without manual page reload? | Users don't see changes |

**Pitfall (discovered in Aidean project)**: The most common missing link is **code-level registration**. Admin management UIs can only manage entities that already exist in code enums and configuration files. A "new entity registration" plan MUST precede any "admin management UI" plan.

### 4. Cross-Document Consistency

- [ ] No contradictory strategies between plan files (e.g., one says "hardcode 20480", another says "configurable")
- [ ] Shared constants are consistent (model type counts, default values, enum definitions)
- [ ] Protocol boundaries are explicit (e.g., "this modal only supports OpenAI protocol, not Anthropic")
- [ ] Dependency ordering is correct (prerequisites execute before dependents)

### 5. Master Index (todolists.md)

- [ ] A master index file exists and is populated (not empty)
- [ ] Total task count matches sum of individual plan files
- [ ] Dependency graph is accurate
- [ ] Version history tracks what changed between versions

## Execution Method

1. Read the requirements source document (readme.md, AGENTS.md)
2. List all plan files in the Parses directory
3. For each requirement, find the matching plan file
4. Read each plan file and verify:
   - Steps are atomic and actionable
   - Involved modules are specific (file paths, not vague descriptions)
   - Confidence level is justified
   - Side effects are identified
5. Verify the global effectiveness chain for configuration features
6. Check cross-document consistency
7. Report findings by severity: P0 (blocks execution), P1 (important), P2 (suggested)

**Read-only constraint**: The audit itself must NOT edit or create files. It only reads planning documents and reports findings. File modifications belong in a subsequent execution phase, not the audit phase.

## Version Evolution Tracking

When planning documents have multiple versions (v1.0 → v2.0 → v3.x), check the version history to understand what issues were found and fixed in prior rounds. This avoids re-reporting already-resolved issues and focuses on remaining gaps.

## Severity Classification

| Severity | Meaning | Action |
|----------|---------|--------|
| P0 | Blocks execution — missing prerequisite or broken chain | Must fix before proceeding |
| P1 | Important — inconsistency or incomplete coverage | Fix before execution |
| P2 | Suggested — improvement opportunity | Fix when convenient |
