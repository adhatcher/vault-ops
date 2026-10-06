# MCP write flow

Use for every note you create or materially edit. The goal: nothing reaches the vault with lint errors, and every write is verified at the far end.

## 1. Draft

Compose the full note in context, starting from a template in `../templates/`. Replace every `{{placeholder}}`. Do not write the draft into the vault. Agents without a file-write tool pass it to `check` on stdin (below); otherwise a scratchpad file (never `/tmp`) works too.

## 2. Check

```bash
uv run --script ${CLAUDE_PLUGIN_ROOT}/skills/vault-ops/scripts/vault_lint.py check --path "<vault-relative target path>" <<'NOTE'
<full note text>
NOTE
```

(`check` reads stdin when no file is given; pass `"<draft>"` instead to lint a scratchpad file.) Send exactly the text that passed to `vault_write`.

- Exit 0: no errors. Warnings are advisory; fix the cheap ones.
- Exit 1: errors. Fix and re-check. Typical causes: missing `type`, broken `[[link]]`, an ADR number with the wrong padding, an archive pointer to a file that does not exist.
- The check resolves links against the real vault, so a link to a note you are creating in the same batch will show as broken. Create the target first, or accept that finding and confirm after the batch.
- Check also fails on any leftover `{{...}}` placeholder in the draft; search the draft for `{{` yourself if unsure.

For an edit with `vault_patch`, `vault_read` the note, apply the same edit to that text in context, check the whole result on stdin, then send the patch.

## 3. Write

- New note: `vault_write`. Confirm the path does not exist first (`vault_list` the folder).
- Existing note: archive first (`vault_copy` into `_Archive/`), then `vault_patch` for a section, or `vault_write` only when replacing the whole note.
- Exception: a single-line append to an `00 … Index` list heading (step 5) removes nothing, so it needs no archive. Any other edit to an index, including rewording or removing entries, archives first.
- Prefer `vault_patch` on a heading over rewriting a note.
- A dated handoff or history note that a later note supersedes is corrected in place, archive-first, with a `[[link]]` to the superseding note. Fix only the statements that are now false.

## 4. Verify

1. `vault_read` the note. Confirm `frontmatter` parsed as expected and `unresolvedLinks` is empty.
2. For a batch, also confirm the file reached the Mac copy: `ls`/`diff` the path under `/Users/aaron/Obsidian` after a few seconds. A missing or different file is the signature of a stranded write; stop and run `obsidian-sync-triage`.

## 5. Index

Add the note to the right `00 … Index` with one line (`vault_patch` append on its list heading). Update `updated:` on the index when it has that field; do not add frontmatter to an index that lacks it, report it as a finding instead. Then `vault_read` the patched index, apply the same read-back as step 4, and run `check` on its full text (step 2): an index patch is lint-checked like any other write. Pre-existing errors on the index (for example a missing `type`) are reported, not blocked on. See `index-maintenance.md`.

## 6. Report

State what was written, the lint result, and anything left unresolved. Do not claim a clean vault; claim only what was checked.

## YAML gotcha

Quote any frontmatter value that contains `: ` or starts with a special character (`description: "Entry point: plan and tasks"`). An unquoted colon makes the whole block unparseable and `check` reports `bad-frontmatter`. The templates already quote their `description` and `title` values.
