# /vault-note-new

Create one note of a given type from its template, in the right place, with the next number, linked from its index.

Arguments: `<type> <title> [--project <Name>]`. Types: `adr`, `task`, `plan`, `runbook`, `handoff`, `requirements`, `feature`, `roadmap`.

## Placement

| type | Path | Name |
|---|---|---|
| `adr` | `<root>/<Project>/Decisions/` | `ADR NNN <Title>.md` (NNN from `next-adr`) |
| `task` | `<root>/<Project>/Tasks/<milestone>/` | `<ID> - <Title>.md` |
| `plan` | `<root>/<Project>/Planning/` | `<Title>.md` |
| `roadmap` | `<root>/<Project>/Planning/` | `01 Roadmap.md` (one per project; refuse if it exists) |
| `runbook` | `<root>/<Project>/Operations/` | `<Title>.md` |
| `handoff` | `<root>/<Project>/History/` | `YYYY-MM-DD <Title>.md` |
| `requirements` | `<root>/<Project>/Planning/` | `<Title>.md` |
| `feature` | `<root>/<Project>/Features/` | `<Title>.md` |

If the project is not given, infer it from the user's context; if you cannot, ask.

## Procedure

1. Read the Vault Schema. Resolve the project root (`01 Projects` or `02 Areas`) and its slug.
2. For an ADR, get the number: `uv run --script ${CLAUDE_PLUGIN_ROOT}/skills/vault-ops/scripts/vault_lint.py next-adr "<Project>"`. It applies the project's padding (3 digits by default). Never pick a number by eye.
3. `vault_list` the target folder. If a note with that name exists, stop and ask; never overwrite.
4. Copy the template and fill every placeholder from what the user told you. Ask for anything essential that is missing (an ADR needs its context and decision; a task needs an objective and acceptance). Set `created` and `updated` to today.
5. Follow `mcp-write-flow.md`: scratchpad draft, `check`, `vault_write`, read back.
6. Add one line to the collection's `00 … Index` (create the collection index first if it does not exist, using `index-collection.md`). Update the index's `updated:`.
7. For an ADR that supersedes another: set `Supersedes` here, and patch the old ADR's `status: superseded` and `superseded_by`. Archive-first for the old one. Never edit the body of an accepted ADR.
8. Report the path, the lint result and the index line added.

## Task IDs

Tasks keep the project's own ID scheme (for example `GL-24`). Read the highest existing ID in the project's `Tasks/` and ask before inventing a new prefix.
