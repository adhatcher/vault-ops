---
name: vault-index
description: Verify and repair the 00 Index notes of a project or the vault: missing indexes, unlisted notes, dead entries, and Home.md coverage. Report-only unless --fix or approved.
argument-hint: "[project] [--fix]"
---

# /vault-index

Check that every note is reachable from an index and every project is linked from Home.

Arguments: $ARGUMENTS

1. Read `${CLAUDE_PLUGIN_ROOT}/skills/vault-ops/SKILL.md` (hard rules, write flow, MCP gotchas).
2. Read the Vault Schema note in the vault: `01 Projects/Obsidian Knowledge System/Operations/Vault Schema.md`.
3. Follow `${CLAUDE_PLUGIN_ROOT}/skills/vault-ops/references/index-maintenance.md` exactly.

All vault writes go through the Obsidian MCP. Archive before overwriting. Lint before writing. Read back after writing.
