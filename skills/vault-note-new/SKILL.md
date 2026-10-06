---
name: vault-note-new
description: Create one note of a given type (adr, task, plan, runbook, handoff, requirements, feature, roadmap) in Aaron's Obsidian vault from its template, with the next ADR number, correct frontmatter, a lint check, and an index entry.
argument-hint: "<type> <title> [--project <Name>]"
---

# /vault-note-new

Create a single schema-conformant note and register it in its index.

Arguments: $ARGUMENTS

1. Read `${CLAUDE_PLUGIN_ROOT}/skills/vault-ops/SKILL.md` (hard rules, write flow, MCP gotchas).
2. Read the Vault Schema note in the vault: `01 Projects/Obsidian Knowledge System/Operations/Vault Schema.md`.
3. Follow `${CLAUDE_PLUGIN_ROOT}/skills/vault-ops/references/note-new.md` exactly.

All vault writes go through the Obsidian MCP. Archive before overwriting. Lint before writing. Read back after writing.
