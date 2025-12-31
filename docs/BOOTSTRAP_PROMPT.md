# Initial Bootstrap Prompt for Claude Code

## Context

You are starting work on **oil-gas-trading-dashboard** — a personal multi-agent commodity trading system focused on crude oil and natural gas (intraday + swing trading). This is a Python-first codebase.

**Before proceeding, read these two reference documents:**
1. `docs/TRADING_SYSTEM_PLAN.md` — defines the multi-agent architecture, instrument choices, modeling techniques, risk management, and development phases
2. `docs/DEV_WORKFLOW.md` — defines how you (Claude Code) operate as the central developer, with Gemini CLI as the big-context reader/compressor

**Read both documents now.**

---

## Important: These Documents Are Living — Improve Them

The two reference documents above are **starting points, not rigid specs**. Moumit has given you full creative freedom to:

- **Restructure** sections that don't flow well or are redundant
- **Add** details, clarifications, or missing pieces you think are important
- **Remove or consolidate** content that's over-engineered for a personal project
- **Challenge** assumptions if you see better approaches (explain your reasoning)
- **Fix** any technical inaccuracies or outdated recommendations
- **Improve** the development workflow based on your knowledge of Claude Code's actual capabilities and limitations

Think of yourself as a senior engineer who's been handed a rough design doc. Your job is to make it actually buildable and maintainable. If something in the plan seems overcomplicated, simplify it. If something is missing, add it. If you'd architect it differently, say so and update the doc.

**After reviewing, make any edits you think improve the documents.** Then proceed with the audit.

---

## Your First Task: Project Audit & Foundation

### Step 1: Review Directory Structure

Run `tree` or `ls -R` to see the current repo layout. Compare against the expected structure from the workflow doc.

**Expected structure:**
```
oil-gas-trading-dashboard/
├── .claude/
│   ├── commands/       # Slash commands (ctx-refresh.md, ctx-ask.md, checkpoint.md)
│   ├── skills/         # Progressive disclosure skill packs
│   ├── hooks/          # Automation hooks (session_start, pre_tool_use, pre_compact)
│   └── .state/         # Runtime state (gitignored)
├── .gemini/            # Gemini project config if needed
├── scripts/            # PowerShell automation scripts
├── context/
│   ├── local/          # Gitignored context packs from Gemini
│   └── shared/         # Publishable context (later)
├── src/                # Main Python source
├── tests/              # pytest tests
├── docs/               # Documentation
├── CLAUDE.md           # Your project constitution
├── GEMINI.md           # Gemini's job description
└── .gitignore
```

**Report:** What exists? What's missing? What should be changed?

If you think a different structure would work better, propose it and explain why.

---

### Step 2: Audit & Improve Configuration Files

Review these files. Create if missing, fix if broken, **improve if you see a better approach**:

#### CLAUDE.md (Project Constitution)

Should contain:
- Golden rules (Moumit controls git, no secrets, advisory-first mode)
- Token discipline guidelines
- Model policy (Opus for planning, Sonnet for coding)
- When to call Gemini
- "Chunk complete" definition

**Feel free to add rules you think are missing or remove ones that seem unnecessary.**

#### GEMINI.md (Gemini's Job Description)

Should contain:
- Output targets (context_pack.md, repo_map.md, decision_notes.md, runbook_updates.md)
- Style guidelines
- Safety rules

**If you think different output artifacts would be more useful, change them.**

#### .gitignore

Ensure it excludes what it should. Add anything else you think should be ignored.

---

### Step 3: Set Up Scripts

Create or verify these PowerShell scripts in `scripts/`:

1. **gemini_context_pack.ps1** — Refreshes local context pack with cooldown logic
2. **gemini_ask.ps1** — Focused Q&A that updates decision_notes.md
3. **quality_gate.ps1** — Runs `ruff check`, `ruff format`, `pytest -q`

**If you think additional scripts would be useful, create them. If any scripts seem overcomplicated, simplify them.**

---

### Step 4: Set Up Claude Commands

Create or verify in `.claude/commands/`:

1. **ctx-refresh.md** — Runs gemini_context_pack.ps1, reads context_pack.md
2. **ctx-ask.md** — Runs gemini_ask.ps1 with argument, reads decision_notes.md  
3. **checkpoint.md** — End-of-chunk: quality gates → force context refresh → update runbook

**Add any other commands you think would be useful for this workflow.**

---

### Step 5: Set Up Claude Skills

Create or verify in `.claude/skills/`:

1. **context-pack/SKILL.md** — When/how to use context packs for token efficiency
2. **quality-gates/SKILL.md** — When/how to run quality gates and fix issues

**Consider whether other skills would be valuable. If so, create them.**

---

### Step 6: Set Up Hooks

Create in `.claude/hooks/`:

1. **session_start.ps1** — Prints reminder about git control and checkpoint workflow
2. **pre_tool_use.ps1** — Blocks dangerous git commands
3. **pre_compact.ps1** — Forces context pack refresh before compaction

Create `.claude/settings.local.json` to wire the hooks.

**Note:** Hook payload/env var names may differ by Claude Code version. Verify what's actually available and adapt accordingly. If hooks aren't working as expected, document the issue and propose alternatives.

---

### Step 7: Create Project Requirements Document

Create `docs/PROJECT_REQUIREMENTS.md` — this is a **separate document** that consolidates and synthesizes both reference docs into a single, actionable spec.

This should be **your interpretation** of what needs to be built, not just a copy-paste. Include:

#### 7.1 System Overview
- What this system is and isn't
- Core goals and constraints
- What "done" looks like for MVP

#### 7.2 Agent Architecture
Document each agent — but feel free to restructure the agent boundaries if you think a different decomposition makes more sense. For each agent:
- Responsibility
- Inputs/outputs
- Key interfaces
- Implementation notes

#### 7.3 Technology Stack
Concrete choices (not just options). If you disagree with choices in the reference docs, state your recommendation and why.

#### 7.4 Development Phases
Rewrite the phases if needed. Make them concrete and actionable. Each phase should have clear deliverables.

#### 7.5 Safety & Risk Rules
Non-negotiables for trading real money.

#### 7.6 Key Interfaces
Define the actual interfaces/abstractions needed:
- Data provider interface
- Agent signal interface  
- Broker interface
- Notification interface

---

### Step 8: Create Initial Runbook

Create `context/shared/runbook.md` with:

- Current phase and status
- Completed items
- Next actions (specific, actionable)
- Open questions
- Decisions log

---

### Step 9: Environment Setup

1. Create/verify `.env.example`
2. Create `pyproject.toml` or `requirements.txt` with initial deps
3. Verify Python 3.11+ is available
4. Test that `ruff` and `pytest` work

---

## Output Expected

After completing this audit and setup:

1. **Summary report** of what existed vs what you created/fixed/improved
2. **List of changes made to reference docs** (TRADING_SYSTEM_PLAN.md and DEV_WORKFLOW.md) with brief rationale for each
3. **docs/PROJECT_REQUIREMENTS.md** — your synthesized project spec
4. **context/shared/runbook.md** — initial runbook with checklist
5. All scripts, commands, skills, hooks in place and verified
6. **Recommendations** for anything you couldn't fix but think should be addressed

---

## Operating Rules (Reminder)

- **You do NOT commit or push** — Moumit controls all git actions
- Use `/checkpoint` when a meaningful chunk is complete
- Use `/ctx-refresh` when context grows large or before `/compact`
- Follow the model policy: Opus for planning, Sonnet for coding
- When uncertain, write to `context/local/decision_notes.md` and flag for human review

---

## Begin

1. Read `docs/TRADING_SYSTEM_PLAN.md` and `docs/DEV_WORKFLOW.md`
2. Make any improvements you see to those documents
3. Run a directory audit
4. Proceed through each step systematically
5. Report findings and take action as you go