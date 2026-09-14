# Project Task Verification Document Structure

Some projects (e.g., RagFlow/Aidean) use a `.docs/` directory with a specific structure for tracking planned tasks against requirements:

## Directory Structure

```
.docs/
  readme.md          # Requirements document — lists all problems to solve, organized by section (一、二、三...)
  temp.md            # Master task list — maps requirements to numbered tasks across Phases/Milestones
  .memory.md         # Session memory — records what was completed each session
  Parses/            # One file per Phase — detailed execution plan for each task group
    01.1-*.md        # Phase documents with task tables, file paths, implementation steps
    02.0-*.md
    ...
  UndefineParses/    # Unassigned/planning-phase documents
    M1-*.md          # Milestone-level planning
    P1.1-*.md        # Phase-level planning
    plans.md         # Master plan
    todolists.md     # Task lists
  原项目分析/         # Original project analysis
    目录结构/         # Directory structure analysis
    技术架构/         # Technical architecture
    ...
```

## Key Relationships

- **readme.md** → **temp.md**: Each readme requirement maps to one or more tasks in temp.md
- **temp.md** → **Parses/*.md**: Each task in temp.md has a corresponding Phase document
- **Parses/*.md** → **Code files**: Each Phase document specifies which source files to modify

## temp.md Format

- Organized by Milestone (M1-M13) and Phase
- Each Phase has a task table with: task ID, description, requirement mapping, status
- Status markers: ✅ completed, ⬜ incomplete, ⚠️ partial
- Includes cross-references to readme sections (e.g., "一.2", "二.3(1)")
- Notes technical debt and incomplete items

## Verification Approach

When verifying:
1. Read temp.md to get the master task list and expected status
2. Read readme.md to understand original requirements
3. For each Phase, check Parse document for planned file changes
4. Verify actual code matches planned changes using keyword/function search
5. Report gaps with connection to both temp.md task IDs and readme requirement numbers
