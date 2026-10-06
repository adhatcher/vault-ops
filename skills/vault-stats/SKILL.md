---
name: vault-stats
description: Show Obsidian vault size and shape: note counts by project, type and status, notes without frontmatter, and finished notes that are large enough to condense.
argument-hint: "[project]"
---

# /vault-stats

Report vault statistics and condense candidates (see the /vault-stats section of the reference).

Arguments: $ARGUMENTS

1. Read `~/.agents/skills/vault-ops/SKILL.md` (hard rules, write flow, MCP gotchas).
2. Read the Vault Schema note in the vault: `01 Projects/Obsidian Knowledge System/Operations/Vault Schema.md`.
3. Follow `~/.agents/skills/vault-ops/references/lint-and-stats.md` exactly.

All vault writes go through the Obsidian MCP. Archive before overwriting. Lint before writing. Read back after writing.
