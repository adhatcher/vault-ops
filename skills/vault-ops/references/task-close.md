# /vault-task-close

Review a finished task, then summarize it: what was done, what was learned, and which decisions were made. Cut the detail that was only needed to write the code, because the code now exists. Keep the originals in an archive so nothing is lost.

Arguments: `<task note or ID> [more IDs...]`, or `--milestone <name>` to close a whole milestone. If none given, ask which work is finished.

This is the single-task version of `obsidian-archive-condense`, with completion review, a lessons section and index upkeep added. For a large batch of already-closed work, `obsidian-archive-condense` is still the right tool.

## Hard rule: archive first, one file at a time

Copy every original into `_Archive/` and confirm each copy returned `OK` **before** any `vault_write`/`vault_patch` on the live note. The vault has no git history; the archive is the only undo. As of 2026-10-05, 38 condensed Golf League notes cite `_Archive` originals that do not exist anywhere in the vault; the lint flags that as `archive-pointer` errors. Do not add to that.

## Phase 1: Review (is it really finished?)

Read the task note and its records. Confirm, and record the evidence for, each of:

1. The checkbox is ticked (`- [x] Complete <ID>.`) or `status` is `done`/`closed`.
2. A final commit, PR or merge commit is named, and a validator or review verdict (PASS) is recorded.
3. The acceptance commands and results are recorded.
4. Nothing is open, blocked or reopened.

If any item is missing, stop and tell the user exactly what is missing. Do not condense unfinished work, and do not invent a commit, verdict or test count.

Already short (about 3 KB or less, mostly facts)? Leave it alone and say so.

## Phase 2: Archive

1. `vault_copy` the task note and each records note to `<project>/_Archive/<milestone>/`, destination ending in `/` to keep the file name. A milestone note gets a distinct name (`_Milestone (original).md`).
2. Confirm every copy with `vault_list` of the archive folder.

## Phase 3: Summarize

Read each archived original fully enough to be accurate; the end of a long record usually holds the verdict, commit and limitations. Then write using the templates in `../templates/task-condensed.md` and `record-condensed.md`.

**Keep:**
- Outcome and status; the final commit, PR or merge commit.
- What was delivered: files, tables, routes, behaviors.
- **Decisions:** rulings and design choices that still bind live code, one line each, with a link to the ADR if one exists.
- **Lessons:** what was learned that changes how similar work should be done: defects found and how each was fixed, spec errors found during validation, surprises, and what you would do differently. One line each.
- Limitations, and anything not run (such as browser steps).

**Cut:**
- Step-by-step build instructions and "read first" lists.
- Per-test enumerations; command transcripts and full pytest output.
- Validator and tester reports; repeated "fresh check" and "Completed" boilerplate.
- Helper script and log paths; implementer self-reports.

Never copy real names, contact details or secrets into a summary.

## Phase 4: Write and verify

1. Keep the frontmatter and the `- [x] Complete <ID>.` checkbox exactly; carry `id`, `milestone`, `depends_on`, `rulings`, `status` over verbatim. Set `updated`.
2. The first line of the condensed note says it was condensed, the date and the archive path. The path must exist; confirm before writing the line.
3. Draft in the scratchpad and `check` it (`mcp-write-flow.md`). `archive-pointer` must be clean.
4. Write: `vault_write` for a task or records note; for a milestone note use `vault_patch` on the `Gate record` heading so frontmatter and exit criteria stay untouched.
5. Read each note back and confirm `unresolvedLinks` is empty.

## Phase 5: Promote and update

1. **Decisions worth keeping beyond this task:** if a decision affects the architecture beyond this task and has no ADR, propose one (`/vault-note-new adr`); do not create it unasked.
2. **Roadmap and indexes:** if the project has a roadmap, update the item's status and evidence line (`vault_patch`, archive-first). Update the collection index line if the note's one-line description changed.
3. **Prune the archive:** delete archive copies of any file you left unchanged (the live note already equals it) with `vault_delete` without `permanent`, so it goes to the trash.

## Report

State, per note: condensed, left alone (and why), or blocked at review (and what is missing). Give the archive paths, the size before and after, the decisions and lessons captured, any ADR proposed, and the lint result. Say what you could not verify.
