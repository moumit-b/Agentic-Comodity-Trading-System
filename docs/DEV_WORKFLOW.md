# Claude Code + Gemini 3 Pro Development Workflow

> **Status:** Living document — adapt and improve as you discover what works best. This workflow is a starting point.

## Goal

Claude Code is the central engine of development. Gemini CLI (Gemini 3 Pro) is the big-context reader/compressor that Claude calls automatically via scripts, commands, and hooks.

This guide covers **development workflow only** (not the trading tool's internal agent architecture).

---

## Key Decisions (Locked In)

- **Codebase:** Python-first
- **Notifications MVP:** Discord webhook (easiest); add email later
- **Testing automation:** Not on every file write; run automatically on "sense-making chunks" using a checkpoint workflow + cooldown logic
- **Context outputs:** Local-only now (gitignored); later you can "publish" selected context to git
- **Claude model strategy:** Opus 4.5 for planning (`opusplan`), Sonnet 4.5 for coding (switching policy defined below)

---

## The Workflow in One Picture (Mental Model)

1. Claude Code plans + implements + runs local tools
2. When repo/context is "big," Claude triggers Gemini CLI (Gemini 3 Pro) headlessly via scripts
3. Gemini writes Context Packs to `context/local/…`
4. Claude reads those small packs and continues coding with lower token use
5. At the end of a meaningful chunk, Claude runs checkpoint: tests + context pack refresh + runbook update

---

## Repo Skeleton

```
oil-gas-trading-dashboard/
├── .claude/
│   ├── commands/           # Slash commands
│   │   ├── ctx-refresh.md
│   │   ├── ctx-ask.md
│   │   └── checkpoint.md
│   ├── skills/             # Progressive disclosure skill packs
│   │   ├── context-pack/
│   │   │   └── SKILL.md
│   │   └── quality-gates/
│   │       └── SKILL.md
│   ├── hooks/              # Automation hooks
│   │   ├── session_start.ps1
│   │   ├── pre_tool_use.ps1
│   │   └── pre_compact.ps1
│   ├── .state/             # Runtime state (gitignored)
│   └── settings.local.json # Hook wiring (gitignored)
├── .gemini/                # Gemini project config if needed
├── scripts/
│   ├── gemini_context_pack.ps1
│   ├── gemini_ask.ps1
│   └── quality_gate.ps1
├── context/
│   ├── local/              # Gitignored context packs from Gemini
│   └── shared/             # Publishable context (later)
├── src/                    # Main Python source
├── tests/                  # pytest tests
├── docs/                   # Documentation
│   ├── TRADING_SYSTEM_PLAN.md
│   ├── DEV_WORKFLOW.md
│   └── PROJECT_REQUIREMENTS.md
├── CLAUDE.md               # Project constitution
├── GEMINI.md               # Gemini's job description
├── .env.example
└── .gitignore
```

### Setup Commands (PowerShell)

```powershell
mkdir oil-gas-trading-dashboard
cd oil-gas-trading-dashboard
git init
git checkout -b moumitDevBranch

# Create folders
mkdir -Force .claude\commands, .claude\skills, .claude\hooks, .claude\.state
mkdir -Force .gemini
mkdir -Force scripts
mkdir -Force context\local, context\shared
mkdir -Force src, tests, docs
```

### .gitignore

```gitignore
# Secrets
.env
.env.*

# Local context packs (not committed for now)
context/local/

# Claude local settings
.claude/settings.local.json

# State
.claude/.state/

# Python
.venv/
__pycache__/
*.pyc
.pytest_cache/
.ruff_cache/
```

---

## Prerequisites (Windows)

### Python Tooling

Python 3.11+ recommended. Use `uv` (fast, modern) or venv+pip.

**Option A (recommended): uv**
```powershell
pip install uv
uv venv
.\.venv\Scripts\activate
```

### Claude Code

You already have Claude Code working.

### Gemini CLI

Install and verify:
```powershell
npm install -g @google/gemini-cli
gemini --version
```

Open Gemini interactive once to authenticate:
```powershell
gemini
```

---

## Project Memory Files

These keep stable rules out of the chat (token savings) and keep behavior consistent.

### CLAUDE.md (Claude Code Project Constitution)

```markdown
# Development Constitution (Moumit)

## Golden Rules
- Moumit controls all git actions (no commit/push/rebase)
- No secrets in repo. Use .env (gitignored) or OS secrets
- Build advisory-first (paper/shadow mode). Real-money execution requires explicit human confirmation

## Token Discipline
- Prefer reading small curated files in context/ over re-explaining
- Use checkpoint workflow for bigger context + tests

## Model Policy
- Planning / architecture / risky refactors: Opus (opusplan)
- Implementation / coding / tests: Sonnet

## When to Call Gemini
Use Gemini only when:
- You need to read many files / long logs / large specs
- You need a compressed context pack before compaction

## "Chunk Complete" Definition
A chunk is complete when:
- A feature is runnable end-to-end or a major TODO is resolved
- Tests pass (checkpoint)
- Context pack updated
```

### GEMINI.md (Gemini's Job Description)

```markdown
# Gemini Project Instructions

You are the big-context reader and compressor.

## Your Output Targets
Write artifacts to:
- context/local/context_pack.md
- context/local/repo_map.md
- context/local/decision_notes.md
- context/local/runbook_updates.md

## Style
- Concise headings
- Bullet points
- Separate FACTS vs ASSUMPTIONS
- End with NEXT STEPS

## Safety
- Never output secrets
- Never invent APIs; mark UNKNOWN when unsure
```

---

## Gemini Bridge (Claude-Managed Automation)

Claude will call Gemini through scripts.

### .env.example

```
GEMINI_MODEL=gemini-3-pro-preview
CTX_REFRESH_COOLDOWN_MINUTES=45
```

### scripts/gemini_context_pack.ps1

Creates/refreshes local context pack (cooldown to avoid waste):

```powershell
param(
    [string]$Question = "",
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

# Load .env if present
if (Test-Path .env) {
    Get-Content .env | ForEach-Object {
        if ($_ -match '^(.*?)=(.*)$') {
            $name=$matches[1].Trim(); $value=$matches[2].Trim()
            if ($name -and $value) { Set-Item -Path Env:$name -Value $value }
        }
    }
}

$model = $env:GEMINI_MODEL
if (-not $model) { $model = 'gemini-3-pro-preview' }

$cooldown = $env:CTX_REFRESH_COOLDOWN_MINUTES
if (-not $cooldown) { $cooldown = 45 }
$cooldown = [int]$cooldown

$statePath = ".claude/.state/ctx_last_run.json"
$now = Get-Date

function ShouldRun {
    if ($Force) { return $true }
    if (-not (Test-Path $statePath)) { return $true }
    $s = Get-Content $statePath -Raw | ConvertFrom-Json
    $last = Get-Date $s.lastRun
    return ((New-TimeSpan -Start $last -End $now).TotalMinutes -ge $cooldown)
}

if (-not (ShouldRun)) {
    Write-Output "[Gemini] Skipping context pack (cooldown active)."
    exit 0
}

New-Item -Force -ItemType Directory context/local | Out-Null

$prompt = @"
You are updating project context for a Python codebase.
Read repository structure and key entrypoints. Produce:
1) context/local/repo_map.md: repo tree + important files
2) context/local/context_pack.md: current system snapshot (goals, modules, APIs, TODOs, risks)
3) context/local/decision_notes.md: open decisions and recommended next actions

If a question is provided, answer it in decision_notes.md under a section called ANSWER.

QUESTION:
$Question
"@

# Headless Gemini run
gemini -p "$prompt" --model "$model"

@{ lastRun = $now.ToString('o'); model = $model } | ConvertTo-Json | Set-Content $statePath

Write-Output "[Gemini] Context pack refreshed using $model"
```

### scripts/gemini_ask.ps1

Focused Q&A:

```powershell
param([Parameter(Mandatory=$true)][string]$Question)

New-Item -Force -ItemType Directory context/local | Out-Null
.\scripts\gemini_context_pack.ps1 -Question $Question -Force
```

### scripts/quality_gate.ps1

```powershell
$ErrorActionPreference = 'Stop'

Write-Output "[QA] ruff check"
ruff check .

Write-Output "[QA] ruff format"
ruff format .

Write-Output "[QA] pytest"
pytest -q

Write-Output "[QA] OK"
```

---

## Claude Code Commands

### .claude/commands/ctx-refresh.md

```markdown
---
description: Refresh local Context Pack (Gemini 3 Pro) with cooldown.
---

Run:
!`powershell -ExecutionPolicy Bypass -File scripts/gemini_context_pack.ps1`

Then:
- Read context/local/context_pack.md
- Continue work using only that summary (avoid rereading huge files)
```

### .claude/commands/ctx-ask.md

```markdown
---
description: Ask Gemini a big-context question and update local context artifacts.
argument-hint: <question>
---

!`powershell -ExecutionPolicy Bypass -File scripts/gemini_ask.ps1 "$ARGUMENTS"`

Then read:
- context/local/decision_notes.md
```

### .claude/commands/checkpoint.md

```markdown
---
description: End-of-chunk automation: run quality gates + refresh context pack.
---

1) Run quality gates:
!`powershell -ExecutionPolicy Bypass -File scripts/quality_gate.ps1`

2) Refresh context pack (force):
!`powershell -ExecutionPolicy Bypass -File scripts/gemini_context_pack.ps1 -Force`

3) Write a short entry to context/local/runbook_updates.md describing what changed.
```

---

## Claude Code Skills

### .claude/skills/context-pack/SKILL.md

```markdown
---
name: context-pack
description: Keep development token use low by refreshing and relying on local context packs.
allowed-tools: Bash, Read, Grep, Glob, Write
---

# Context Pack Skill

## When to Use
- Before large refactors
- After finishing a feature chunk
- Before /compact

## What to Do
1) Run /ctx-refresh (Gemini with cooldown)
2) Read context/local/context_pack.md
3) Base next steps only on that file + files you touch
4) If uncertain, write an OPEN QUESTION into context/local/decision_notes.md
```

### .claude/skills/quality-gates/SKILL.md

```markdown
---
name: quality-gates
description: Run ruff + pytest and fix issues minimally.
allowed-tools: Bash, Read, Grep, Glob, Write
---

# Quality Gates Skill

## When to Use
- After implementing a meaningful chunk
- Before creating a PR or switching tasks

## Procedure
1) Run scripts/quality_gate.ps1
2) If failures:
   - Fix smallest diff
   - Re-run
3) Stop if the fix is risky and propose options.
```

---

## Claude Code Hooks

### Strategy

Use hooks for guardrails and gentle automation, not heavy work every edit.

### .claude/hooks/session_start.ps1

```powershell
Write-Output "[SessionStart] Remember: Moumit controls git. Use /checkpoint after meaningful chunks."
```

### .claude/hooks/pre_tool_use.ps1

```powershell
param([string]$cmd)

$blocked = @(
    "git commit",
    "git push",
    "git rebase",
    "git reset",
    "git cherry-pick"
)

foreach ($b in $blocked) {
    if ($cmd -like "$b*") {
        Write-Output "BLOCKED: Moumit controls git actions. Attempted: $cmd"
        exit 2
    }
}

exit 0
```

### .claude/hooks/pre_compact.ps1

```powershell
Write-Output "[PreCompact] Refreshing local context pack before compaction..."
powershell -ExecutionPolicy Bypass -File scripts/gemini_context_pack.ps1 -Force
```

### .claude/settings.local.json

```json
{
  "hooks": {
    "SessionStart": [
      { "command": "powershell -ExecutionPolicy Bypass -File .claude/hooks/session_start.ps1" }
    ],
    "PreToolUse": [
      { "command": "powershell -ExecutionPolicy Bypass -File .claude/hooks/pre_tool_use.ps1 $CLAUDE_TOOL_INPUT" }
    ],
    "PreCompact": [
      { "command": "powershell -ExecutionPolicy Bypass -File .claude/hooks/pre_compact.ps1" }
    ]
  }
}
```

> **Note:** Hook payload/env var names can differ by version. If `$CLAUDE_TOOL_INPUT` isn't available, adapt to actual hook payload.

---

## Daily Development Loop

### Loop A — Plan (Opus)
1. Start Claude Code
2. Switch to planning model (Opus plan)
3. Ask Claude to outline the chunk and update TODOs

### Loop B — Build (Sonnet)
4. Switch to coding model (Sonnet)
5. Implement the chunk in small diffs
6. If context gets large: `/ctx-refresh` (cooldown prevents spam)

### Loop C — Verify (Automated Chunk Checkpoint)
7. Run `/checkpoint` when the chunk is "done":
   - ruff + pytest
   - Gemini context pack forced refresh
   - Runbook update

### Loop D — Compact (Token Reset)
8. When the session gets long:
   - `/checkpoint`
   - `/compact`

---

## Context Outputs: Local Now, Publish Later

**Today:** `context/local/` is gitignored.

**Later:** Create a `/publish-context` command that copies selected artifacts into `context/shared/` and commits them.

**Recommended publish candidates:**
- context/shared/architecture.md
- context/shared/decisions.md
- context/shared/runbook.md

---

## Development Roadmap

### A) Foundation (Workflow + Scaffolding)
1. Create repo skeleton (this guide)
2. Add Python env + lint/test tools
3. Validate: /ctx-refresh and /checkpoint work end-to-end

### B) Product Skeleton (No Live Trading)
4. Build minimal CLI + config system
5. Add data layer abstraction (pluggable providers)
6. Add dashboard skeleton (local UI) OR start CLI-first, then UI

### C) Operational Data + Logging
7. Implement market data ingestion (MVP provider)
8. Add persistence (SQLite) for candles/signals/logs
9. Add observability: structured logs + runbook

### D) Advisory Engine (No Auto-Exec)
10. Implement "analysis pipeline" interfaces (inputs/outputs)
11. Add alerting (Discord webhook) + dedupe/cooldowns
12. Add paper/shadow mode runner

### E) Broker Integration (Schwab, Read-Only First)
13. Implement Schwab account read (positions/cash)
14. Add trade-intent objects (proposed orders only)
15. Add explicit manual confirmation UI/CLI step

### F) Paper Trading & Evaluation
16. Paper execution + journaling
17. Backtesting harness + replay mode
18. Regression tests for data correctness and invariants

### G) Go-Live Hardening (Still Guarded)
19. Circuit breakers (max loss/day, stale data halt, volatility halt)
20. Kill switch
21. Start real-money operation with manual confirmation only

### H) Optional Automation (Only If Chosen)
22. Feature flag for auto-exec
23. Extra safety: two-step confirmations, restricted order types, whitelists

---

## Notification MVP

**Discord webhook:**
- Easiest setup
- Pushes to phone immediately via Discord app

(We'll implement a `notify_discord(webhook_url, message)` function and later add email.)

---

## Next Actions (What We Do First)

1. Create the repo + folders exactly as above
2. Install `ruff`, `pytest`
3. Install Gemini CLI and confirm `gemini -p` works
4. Run:
   - `/ctx-refresh`
   - `/checkpoint`
5. If any command/hook payload differs in your Claude Code version, adjust scripts/settings to match