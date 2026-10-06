---
name: vault-task-close
description: After a task or milestone is finished, review it, archive the originals, and condense the notes to what was done, what was learned and the key decisions, dropping the build-time instructions. Updates the roadmap and indexes. Use when a task, milestone or plan note is complete and should be shrunk.
argument-hint: "<task note or ID ...> | --milestone <name>"
---

# /vault-task-close

Review completion, archive the originals, then summarize what was done, learned and decided.

Arguments: $ARGUMENTS

1. Read `${CLAUDE_PLUGIN_ROOT}/skills/vault-ops/SKILL.md` (hard rules, write flow, MCP gotchas).
2. Read the Vault Schema note in the vault: `01 Projects/Obsidian Knowledge System/Operations/Vault Schema.md`.
3. Follow `${CLAUDE_PLUGIN_ROOT}/skills/vault-ops/references/task-close.md` exactly.

All vault writes go through the Obsidian MCP. Archive before overwriting. Lint before writing. Read back after writing.
