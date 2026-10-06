# /vault-lint and /vault-stats

Report on vault health. Read-only: nothing is changed without separate approval.

## /vault-lint [project] [--min-severity error|warn|info]

```bash
uv run --script ~/.agents/skills/vault-ops/scripts/vault_lint.py sweep [--project "<name>"] [--min-severity warn]
```

Exit status 1 means at least one `error`. Use `--json` when you need to process findings.

### Report

1. Give the totals (errors, warnings, info) and the rule table.
2. Group findings by project, then by rule. Lead with errors.
3. Separate **real defects** from **noise** before presenting. Verify before asserting:
   - `archive-pointer`: confirm with `vault_list` that the archive folder really is missing. A missing archive means the original is gone; this is serious and must be reported, not repaired by guessing.
   - `broken-link`: check for a rename or a retired note (search with `search_simple`). If Obsidian itself reports the link as unresolved (`vault_read` → `unresolvedLinks`) it is real.
   - `not-in-index` on a project with no indexes at all is one finding (`missing-index`) in disguise; report it once.
4. Propose fixes grouped by effort, and ask which to apply. Do not apply anything in the same turn as the report unless the user said to.
5. When applying approved fixes, use `mcp-write-flow.md` and archive-first.

### Rules at a glance

| rule | severity | meaning |
|---|---|---|
| `no-frontmatter`, `bad-frontmatter`, `missing-type` | error | note is invisible to typed retrieval |
| `broken-link`, `broken-md-link` | error | target does not exist |
| `archive-pointer` | error | condensed note cites an archive file that does not exist |
| `adr-name`, `adr-duplicate` | error | ADR number padding wrong or reused |
| `unfilled-placeholder` | error | template placeholder left in the note |
| `missing-owner`, `owner-mismatch`, `missing-title`, `missing-status` | warn | metadata incomplete |
| `legacy-type`, `legacy-status`, `unknown-type`, `unknown-status` | warn | outside the schema vocabulary |
| `not-in-index`, `missing-index`, `not-in-home` | warn | navigation gap |
| `ambiguous-link`, `oversized` | warn | link may hit the wrong note; note too large |
| `md-link`, `duplicate-name`, `adr-gap`, `missing-collection-index`, `condense-candidate` | info | style and housekeeping |

## Semantic pass (optional, on request)

After the script, read the recently changed notes and look for what a script cannot see; present as proposals with evidence:

- A roadmap or index status that contradicts the note it points to (for example a roadmap item "in progress" whose action note says COMPLETED).
- A superseded ADR still cited as current.
- Two notes that duplicate the same decision.

## /vault-stats [project]

```bash
uv run --script ~/.agents/skills/vault-ops/scripts/vault_lint.py stats [--project "<name>"]
```

Report note counts by project, type and status, the number without frontmatter, and the condense candidates. Point the user at `/vault-task-close` for finished tasks that are large.
