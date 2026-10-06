---
name: obsidian-archive-condense
description: Condense completed project tasks, records and milestone notes in Aaron's Obsidian vault into short summaries, after archiving the originals in the vault. Use when the user asks to summarize, condense, compact or clean up finished tasks or milestones in Obsidian while keeping what was done, or invokes $obsidian-archive-condense.
---

# Obsidian Archive and Condense

## Purpose

Finished tasks pile up detail nobody needs again: full specs, "Brief" blocks, validator transcripts, command output, repeated fresh-check logs. This skill shrinks them to a short record of what was done, and keeps the originals in an archive folder so nothing is lost.

Use only the Obsidian MCP tools (`vault_list`, `vault_read`, `vault_get_document_map`, `vault_copy`, `vault_write`, `vault_patch`, `vault_delete`). Do not edit the vault through the filesystem; the vault syncs, and the MCP is the supported path.

## Hard rule: archive first, one file at a time

**Copy the original to the archive before overwriting it, for every file, with no exceptions.** The vault has no git history, so the archive copy is the only undo. Batch the copies for a whole milestone first, and confirm each returned `OK`, then start rewriting. Never run `vault_write` on a note whose archive copy you have not seen succeed. (A past run overwrote two task notes before archiving them and had to rebuild them from the conversation.)

## Procedure

1. **Scope.** Confirm which items are complete (checkbox `[x]`, `status: closed/done`, a recorded PASS or merge). Only condense completed work. Ask if completion is unclear.
2. **Inventory.** `vault_list` the project folders, then `vault_get_document_map` on each records and milestone note to see structure and size before reading. `vault_read` returns huge files in full or spills them to disk; prefer targeted reads with `targetType: heading` and `target: [...]` for large notes.
3. **Archive.** `vault_copy` each file into `<project>/_Archive/<milestone>/`. Pass a destination ending in `/` to keep the filename. Use a distinct name for `_Milestone.md` (for example `_Milestone (original).md`) so milestones do not collide. Use `allowOverwrite` only on purpose.
4. **Read** each archived original fully enough to summarize accurately. The end of a long record usually holds the final verdict, commit and limitations.
5. **Decide per file:**
   - Already short (about 3 KB or less, mostly facts) → leave it. Do not condense for its own sake.
   - Otherwise rewrite using the templates below.
6. **Write** with `vault_write`. For a milestone note, use `vault_patch` on the `Gate record` heading so the frontmatter and exit criteria stay untouched.
7. **Prune the archive.** Delete archive copies of any file you left unchanged, since the live note already equals it. Use `vault_delete` without `permanent`, so it goes to the trash.
8. **Report** what was condensed, what was left alone, what was archived, and anything you could not verify.

## What to keep and what to cut

**Keep:** outcome and status; the final commit, PR or merge commit; what was delivered (files, tables, routes, behaviors); contracts that still bind live code; the decisions and rulings cited; defects found and how each was fixed, one line each; spec errors found during validation; limitations and anything not run (such as browser steps).

**Cut:** step-by-step build instructions and "read first" lists; per-test enumerations; command transcripts and full pytest output; validator and tester reports; repeated "fresh check" and "Completed" boilerplate; helper script and log paths; mutation-check output; implementer self-reports.

Never invent a commit, test count or date. If the source does not state it, leave it out. Do not copy real names, contact details or secrets into the summary, even if the original had them.

## Templates

**Task note** (keep the frontmatter and the `- [x] Complete GL-xx.` checkbox exactly):

```markdown
Condensed YYYY-MM-DD. Full original spec: `<archive path>`. Outcome and history: [[<records note>]].

### Objective
### What was built / What was done
### Must not   (only the boundaries that still matter)
### Acceptance (the commands, result, and the validated commit)
```

**Records note:**

```markdown
# GL-xx records

Condensed record for [[<task note>|GL-xx]]. Original: `<archive path>`.

**Status:** done. Commit `…`, validator PASS on attempt N (date).
## Delivered
## History   (a small table when there were several attempts)
## Evidence
## Limitations / Notes
**Decisions:** …
```

**Milestone note:** replace only the `Gate record` section. Give the result (closed, gate attempt and commit), the milestone tests added, the key evidence, the defects the gate found, and carried-forward observations. Link the archived original.

Every condensed note starts with a line saying it was condensed, the date, and where the original lives. Make that path true: verify the archive copy exists before writing the line.

## Pitfalls

- A condensed note that points at an archive file that does not exist. Check with `vault_list` at the end.
- Re-condensing an already condensed note and losing the archive pointer.
- Overwriting frontmatter. Notes use `id`, `milestone`, `depends_on`, `rulings`, `status`; carry them over verbatim.
- Broken links. Records and task notes link each other with `[[...]]`; keep the link targets valid.
- Condensing work that is not finished. Skip anything open, blocked or reopened.
