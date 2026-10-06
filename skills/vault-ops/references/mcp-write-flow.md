# MCP write flow

Use for every note you create or materially edit. The goal: nothing reaches the vault with lint errors, and every write is verified at the far end.

## 1. Draft

Write the full note to a file in the session scratchpad (never in the vault, never in `/tmp`). Start from a template in `../templates/`. Replace every `{{placeholder}}`.

## 2. Check

```bash
uv run --script ~/.agents/skills/vault-ops/scripts/vault_lint.py check "<draft>" --path "<vault-relative target path>"
```

- Exit 0: no errors. Warnings are advisory; fix the cheap ones.
- Exit 1: errors. Fix and re-check. Typical causes: missing `type`, broken `[[link]]`, an ADR number with the wrong padding, an archive pointer to a file that does not exist.
- The check resolves links against the real vault, so a link to a note you are creating in the same batch will show as broken. Create the target first, or accept that finding and confirm after the batch.
- Check also fails on any leftover `{{...}}` placeholder in the draft; search the draft for `{{` yourself if unsure.

For an edit with `vault_patch`, apply the same edit to a scratchpad copy of the whole note, check that, then send the patch.

## 3. Write

- New note: `vault_write`. Confirm the path does not exist first (`vault_list` the folder).
- Existing note: archive first (`vault_copy` into `_Archive/`), then `vault_patch` for a section, or `vault_write` only when replacing the whole note.
- Prefer `vault_patch` on a heading over rewriting a note.

## 4. Verify

1. `vault_read` the note. Confirm `frontmatter` parsed as expected and `unresolvedLinks` is empty.
2. For a batch, also confirm the file reached the Mac copy: `ls`/`diff` the path under `/Users/aaron/Obsidian` after a few seconds. A missing or different file is the signature of a stranded write; stop and run `obsidian-sync-triage`.

## 5. Index

Add the note to the right `00 … Index` with one line (`vault_patch` append on its list heading). Update `updated:` on the index. See `index-maintenance.md`.

## 6. Report

State what was written, the lint result, and anything left unresolved. Do not claim a clean vault; claim only what was checked.
