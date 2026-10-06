# Skills

Agent skills for keeping Aaron's Obsidian vault consistent and in sync. Each subdirectory is one skill with a `SKILL.md`. They ship as part of the `vault-keeper` plugin, which loads them as `vault-keeper:<name>`.

The vault's conventions live in the vault note `01 Projects/Obsidian Knowledge System/Operations/Vault Schema.md`. If a skill and the schema disagree, the schema wins.

## Skills

| Skill | Purpose |
|---|---|
| [`vault-ops`](vault-ops/) | Shared core: hard rules, procedures, templates and the lint script. Every `/vault-*` command loads it. |
| [`vault-project-init`](vault-project-init/) | Create the folder structure and starter notes for a new project, or upgrade an existing one to the schema. |
| [`vault-note-new`](vault-note-new/) | Create one note (adr, task, plan, runbook, handoff, requirements, feature, roadmap) from its template. |
| [`vault-lint`](vault-lint/) | Read-only sweep of the vault against the schema, with proposed fixes. |
| [`vault-index`](vault-index/) | Verify and repair the `00 Index` notes and `Home.md` coverage. |
| [`vault-stats`](vault-stats/) | Note counts by project, type and status, plus notes large enough to condense. |
| [`vault-task-close`](vault-task-close/) | Archive and condense a finished task or milestone, then update the roadmap and indexes. |
| [`obsidian-archive-condense`](obsidian-archive-condense/) | Batch-condense completed tasks and milestone notes after archiving the originals. |

## How they fit together

`vault-project-init`, `vault-note-new`, `vault-lint`, `vault-index`, `vault-stats` and `vault-task-close` are short wrappers. Each tells the agent to read `vault-ops/SKILL.md`, then follow one file in `vault-ops/references/`. Change a procedure in the reference, not the wrapper.

```
vault-ops/
  SKILL.md        hard rules, write flow, MCP gotchas, command-to-reference table
  references/     one procedure per command, plus mcp-write-flow.md
  templates/      one template per note type (placeholders are {{like-this}})
  scripts/        vault_lint.py
```

## Scripts

```bash
# Lint (read-only; exit 1 when any error is found)
uv run --script vault-ops/scripts/vault_lint.py check <draft.md> --path "<vault-relative path>"
uv run --script vault-ops/scripts/vault_lint.py sweep [--project "<name>"] [--min-severity warn]
uv run --script vault-ops/scripts/vault_lint.py stats [--project "<name>"]
uv run --script vault-ops/scripts/vault_lint.py next-adr "<project>"
```

The vault is read from `/Users/aaron/Obsidian`; set `VAULT_ROOT` or pass `--vault` to override.

## Rules every skill keeps

- Write to the vault only through the Obsidian MCP, never the filesystem. The vault syncs through CouchDB, and a filesystem write can strand a note.
- Archive a note into `_Archive/` before overwriting or condensing it.
- New notes must pass `check` with no errors before they are written.
- Read a note back after writing it. An OK from a write does not prove it synced.
