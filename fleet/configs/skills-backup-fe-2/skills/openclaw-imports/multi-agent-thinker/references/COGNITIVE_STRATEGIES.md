# Cognitive Strategies Design

This document outlines the "Cognitive Strategies" layer for Expert Agents. Each agent is equipped with these strategies to handle different interaction scenarios effectively.

## 1. Basic Scenario: Prompt Enhancement (Input Layer)
**Trigger:** All user instructions.
**Mechanism:** "Prompt Repetition" (CV Method) to improve non-reasoning model performance.
**Logic:**
- Length < 100 chars: Repeat 3 times (Total 4 segments).
- Length 100-500 chars: Repeat 2 times (Total 3 segments).
- Length > 500 chars: Repeat 1 time (Total 2 segments).
**Format:** Segments separated by two newlines (`\n\n`).

## 2. Extended Scenarios (Strategy Layer)
Expert Agents select one of these strategies based on context.

### A. Socratic Questioning (追问场景)
**Trigger:** Vague requirements, uncertainty, or need for deep clarification.
**Behavior:**
- Ask one question at a time.
- Iterate until 95% confidence in understanding is reached.
- Do not provide solution until requirements are clear.

### B. Dialectical Discussion (辩证场景)
**Trigger:** Critical decision making, need for robust solutions, or user request for critique.
**Behavior:**
- Play "Devil's Advocate" or "Opposer".
- Challenge assumptions, logic, and evidence.
- Attack the user's idea from multiple angles to find loopholes.

### C. Pre-mortem Analysis (失败预想)
**Trigger:** Project planning, risk assessment, or high-stakes execution.
**Behavior:**
- Assume the plan has already failed.
- Analyze: "What decision was wrong?", "Fatal error?", "Ignored risk?", "First thing to fix?".
- Based on real-world failure cases.

### D. Reverse Engineering (反向提示)
**Trigger:** Product design, feature brainstorming (e.g., "I want a shopping app").
**Behavior:**
- Analyze mature products (e.g., Amazon, Taobao) in the domain.
- Deduce necessary features and requirements from these finished products.
- Output the inferred spec.

### E. Multi-dimensional Explanation (多维解释)
**Trigger:** Educational requests, complex concept explanation, or mixed-audience reporting.
**Behavior:**
- **Beginner Version:** Analogies, simple language (e.g., "Grandpa at the spa").
- **Expert Version:** Technical precision, no factual errors, professional terminology.
