---
description: End-of-chunk automation: run quality gates + refresh context pack.
---

1) Run quality gates:
!`powershell -ExecutionPolicy Bypass -File scripts/quality_gate.ps1`

2) Refresh context pack (force):
!`powershell -ExecutionPolicy Bypass -File scripts/gemini_context_pack.ps1 -Force`

3) Write a short entry to context/local/runbook_updates.md describing what changed.