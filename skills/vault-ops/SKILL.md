---
name: vault-ops
description: Create, lint, index and close out notes in Aaron's Obsidian vault using the Vault Schema. Shared core for the vault-project-init, vault-note-new, vault-lint, vault-index, vault-stats and vault-task-close commands. Use whenever creating or restructuring vault notes or projects, checking vault conventions, or summarizing finished work in Obsidian.
---

# Vault Ops

Shared rules, scripts and templates for keeping Aaron's vault consistent. The slash commands (`/vault-project-init`, `/vault-note-new`, `/vault-lint`, `/vault-index`, `/vault-stats`, `/vault-task-close`) each load this file, then one reference from `references/`.

## Source of truth

The conventions live in the vault, not here:

`01 Projects/Obsidian Knowledge System/Operations/Vault Schema.md`

Read it before creating or restructuring anything. It defines note types, frontmatter, statuses, naming, linking and the machine-readable lint rules. If this skill and the schema disagree, the schema wins.

## Hard rules

1. **Write only through the Obsidian MCP** (`vault_write`, `vault_patch`, `vault_append`, `vault_copy`, `vault_move`, `vault_delete`). The vault syncs through CouchDB; a filesystem write can strand a note. Reading the filesystem copy at `/Users/aaron/Obsidian` is fine, and the lint script does exactly that.
2. **Archive first.** Before overwriting or condensing a note, `vault_copy` it into `_Archive/` and confirm the copy. The vault has no git history, so the copy is the only undo.
3. **An OK from a write is not proof of sync.** After a batch, read one note back (`vault_read`) and confirm it matches. If it does not, stop and report the mismatch.
4. **Lint is advisory for existing notes, blocking for new ones.** New or edited notes must have no `error` findings before they are written. Report existing-note findings as proposals; do not rewrite them unasked.
5. **Never invent facts** (commits, dates, test counts, verdicts). If the source does not state it, leave it out.
6. **Do not touch** `_Archive`, `Archive`, `.obsidian`, `Excalidraw` or `05 Memories` unless the user names them.

## The write flow

Every create or edit follows `references/mcp-write-flow.md`: draft in the scratchpad, `check` it with the lint script, fix errors, write through the MCP, read back, update the index. Summary:

```bash
S=${CLAUDE_PLUGIN_ROOT}/skills/vault-ops/scripts/vault_lint.py
uv run --script $S check <draft.md> --path "<vault-relative target path>"   # exit 1 = errors
uv run --script $S sweep [--project "<name>"] [--min-severity warn]          # whole vault, read-only
uv run --script $S stats [--project "<name>"]                                # counts, condense candidates
uv run --script $S next-adr "<project>"                                      # next ADR number, correct padding
```

`uv run --script` installs the pinned PyYAML on first use. Set `VAULT_ROOT` or pass `--vault` if the vault is not at `/Users/aaron/Obsidian`.

## MCP gotchas

- `vault_patch` heading targets must be a JSON **array** (`["Heading"]`), never a bare string.
- `vault_patch` `prepend` into a heading's content leaves a blank line after the inserted text; harmless.
- `vault_write` overwrites without warning. Read first, or archive first.
- `vault_read` returns `links`, `backlinks` and `unresolvedLinks`. After writing a note, `unresolvedLinks` must be empty (or only contain links you intend to create next). This is the same resolver Obsidian uses.
- Obsidian resolves `[[links]]` by **file name**, not frontmatter alias. `[[Roadmap]]` does not reach `01 Roadmap.md`.
- Large notes: use `vault_get_document_map`, then read by heading.

## Templates

`templates/` holds one template per note type (`adr`, `task`, `plan`, `roadmap`, `runbook`, `handoff`, `requirements`, `feature`, `index-project`, `index-collection`, plus `task-condensed` and `record-condensed` for close-out). Copy the template, replace every `{{placeholder}}`, and never leave one behind: the check rejects unresolved `{{...}}`.

## Related skills

- `obsidian-archive-condense`: batch condensing of a finished milestone. `/vault-task-close` reuses its archive-first mechanics for a single task and adds lessons and index upkeep.
- `adr-authoring`: Bourbon Book repository ADRs. Vault ADRs follow the schema; Bourbon Book vault ADRs mirror the repo and keep 4-digit numbers.

## Procedures

| Command | Reference |
|---|---|
| `/vault-project-init` | `references/project-init.md` |
| `/vault-note-new` | `references/note-new.md` |
| `/vault-lint` and `/vault-stats` | `references/lint-and-stats.md` |
| `/vault-index` | `references/index-maintenance.md` |
| `/vault-task-close` | `references/task-close.md` |
| any write | `references/mcp-write-flow.md` |
