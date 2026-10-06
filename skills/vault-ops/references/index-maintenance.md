# /vault-index

Verify the indexes for a project or the whole vault and repair gaps. An index is the cheap-to-read entry point: one line per note, no bodies.

Arguments: `[project] [--fix]`. Without `--fix`, report only.

## What a good index is

- Every project and area has `00 <Name> Index.md` at its root, linked from `00 Home.md`.
- Every collection with three or more notes has its own `00 <Collection> Index.md`, linked from the project index.
- Every note is linked from exactly the index of its collection, with a one-line description (use the note's `description` field).
- Index notes carry `type: index`, the owner slug, and `updated`.

## Procedure

1. `sweep --project "<name>"` and keep only `missing-index`, `missing-collection-index`, `not-in-index`, `not-in-home` and `broken-link` findings that sit in an index note.
2. For each gap, work out the fix:
   - Missing index: draft from `../templates/index-project.md` or `index-collection.md`, listing the notes that exist, each with its `description` (or the first sentence of the note if there is none).
   - Unlisted note: one line to append under the right heading of its collection index.
   - Dead entry: ask whether the note was renamed (search by title), retired (remove the line) or still to be written (leave it and say so).
3. Present the proposed edits as a list. Report-only mode stops here.
4. With `--fix` or approval: follow `mcp-write-flow.md`. New index notes via `vault_write`; additions to existing indexes via `vault_patch` append on the list heading, with `rejectIfContentPreexists` so a retry cannot duplicate a line. Bump the index's `updated`.
5. Re-run the sweep for the project and report before and after counts for the index rules.

## Order of entries

Keep the existing order of an index you did not create. Do not alphabetize or regroup unless asked. New entries go at the end of their list.

## Do not

- Rebuild an index from scratch when it has hand-written prose, status lines or "Start here" sections. Patch it.
- Index notes under `_Archive` or `Archive`; those are linked from the note that was condensed.
