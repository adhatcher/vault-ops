---
name: vault-lint
description: Lint Aaron's Obsidian vault against the Vault Schema: frontmatter, types and statuses, broken links, archive pointers, ADR numbering, missing indexes, Home coverage. Read-only report with proposed fixes. Use to check vault health or a project before and after changes.
argument-hint: "[project] [--min-severity error|warn|info]"
---

# /vault-lint

Run the read-only vault sweep and report real defects separately from noise.

Arguments: $ARGUMENTS

1. Read `~/.agents/skills/vault-ops/SKILL.md` (hard rules, write flow, MCP gotchas).
2. Read the Vault Schema note in the vault: `01 Projects/Obsidian Knowledge System/Operations/Vault Schema.md`.
3. Follow `~/.agents/skills/vault-ops/references/lint-and-stats.md` exactly.

All vault writes go through the Obsidian MCP. Archive before overwriting. Lint before writing. Read back after writing.
