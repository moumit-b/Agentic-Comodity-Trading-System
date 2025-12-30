# Development Constitution

## Golden rules
- Human/Me(Name: Moumit) controls all git actions (no commit/push/rebase).
- No secrets in repo. Use .env (gitignored) or OS secrets.
- Build advisory-first (paper/shadow mode). Real-money execution requires explicit human confirmation.

## Token discipline
- Prefer reading small curated files in context/ over re-explaining.
- Use checkpoint workflow for bigger context + tests.

## Model policy
- Planning / architecture / risky refactors: Opus (opusplan)
- Implementation / coding / tests: Sonnet

## When to call Gemini
Use Gemini only when:
- you need to read many files / long logs / large specs
- you need a compressed context pack before compaction
- offload any of these token consuming acts of context management to gemini
The point of this is to help you conserve tokens, and take advantage of gemini CLI's very large context window.

## “Chunk complete” definition
A chunk is complete when:
- a feature is runnable end-to-end or a major TODO is resolved
- tests pass (checkpoint)
- context pack updated