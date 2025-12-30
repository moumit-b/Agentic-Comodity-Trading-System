---
description: Refresh local Context Pack (Gemini 3 Pro) with cooldown.
# Keep this auto-invocable (Claude can call it) because cooldown prevents waste.
---

Run:

!`powershell -ExecutionPolicy Bypass -File scripts/gemini_context_pack.ps1`

Then:
- read context/local/context_pack.md
- continue work using only that summary (avoid rereading huge files)