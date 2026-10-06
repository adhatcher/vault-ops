# /vault-project-init

Create the folder structure and starter notes for a new project or area, or bring an existing one up to the schema (`--upgrade`).

Arguments: `<Name> [--type software|ops|area] [--upgrade]`. Ask for the name and type if missing; default type is `software`.

## Layouts

| type | Root | Collections | Starter notes |
|---|---|---|---|
| `software` | `01 Projects/<Name>/` | `Architecture`, `Decisions`, `Operations`, `Planning`, `History`, `Features` | project index, one index per collection, `Planning/01 Roadmap.md` |
| `ops` | `01 Projects/<Name>/` | `Architecture`, `Decisions`, `Operations`, `Planning`, `History` | project index, one index per collection, `Planning/01 Roadmap.md` |
| `area` | `02 Areas/<Name>/` | `Operations`, `Decisions`, `History` | area index, one index per collection |

`Tasks/` and `Findings/` are added later by the work that needs them (for example milestone-based delivery), not at init.

The owner slug is the name lowercased with hyphens (`Golf League` becomes `golf-league`). Area notes use `area:` instead of `project:`.

## Procedure (new)

1. Read the Vault Schema. Confirm `<root>/<Name>` does not exist (`vault_list` the parent) and the slug is not in use.
2. Show the user the exact list of folders and notes you will create, and wait for a yes.
3. Build every note from `../templates/`:
   - `index-project.md` for `00 <Name> Index.md`, with `{{collection-links}}` filled as `- [[<Collection>/00 <Collection> Index|<Collection>]] — <one line>`.
   - `index-collection.md` for each `<Collection>/00 <Collection> Index.md`.
   - `roadmap.md` for `Planning/01 Roadmap.md` (software and ops).
4. Draft each note in the scratchpad and `check` it (see `mcp-write-flow.md`). Index links resolve once their targets exist, so create collection indexes and the roadmap first, the project index last.
5. Write with `vault_write`, one note at a time.
6. Add the project to `00 Home.md` under `## Projects` (or `## Areas`) with `vault_patch` append: `- [[<root>/<Name>/00 <Name> Index|<Name>]] — <one line>`. Read `00 Home.md` first and patch only that one heading; an append does not need an archive copy.
7. Verify: `vault_read` the project index (empty `unresolvedLinks`), `vault_list` the tree, and `diff` one note against the Mac copy.
8. Run `sweep --project "<Name>"` and report the result. The new project should have no errors.

## Procedure (`--upgrade`, existing project)

Never overwrite. Add only what is missing.

1. Run `sweep --project "<Name>"` and `stats --project "<Name>"`. Summarize findings by rule.
2. Propose a plan, in this order, and wait for approval of each group:
   1. Missing indexes: create `00 <Name> Index.md` and collection indexes, populated from the notes that exist.
   2. Missing frontmatter on notes that have none: add the minimum block (`title` from the first heading or file name, `type` inferred from folder, owner slug). Show the proposed block for each note; apply only approved ones.
   3. `not-in-index` and `not-in-home` entries: add the links.
   4. Legacy `type` and `status` values: rewrite to canonical.
3. For every existing note you change: `vault_copy` it to `<root>/<Name>/_Archive/upgrade-<date>/` first, confirm the copy, then `vault_patch` the frontmatter (or `vault_write` only for a note with no frontmatter at all). Do not bulk-rewrite; unknown frontmatter keys stay.
4. Re-run the sweep and report before and after counts.

Do not renumber ADRs, rename notes or move folders as part of an upgrade. Those need their own decision.
