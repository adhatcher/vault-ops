# vault-keeper

A Claude Code plugin for keeping Aaron's Obsidian vault consistent: one agent, nine skills and a guard hook. There is no app, build, or test suite. The repo root is the plugin root (`~/.agents/agents/vault-keeper/`); `claude plugin validate .` checks the manifest.

The vault itself is not in this repo (filesystem copy at `/Users/aaron/Obsidian`, override with `VAULT_ROOT`). Its conventions live in the vault note `01 Projects/Obsidian Knowledge System/Operations/Vault Schema.md`, which wins over anything written here.

## Architecture

- **`agents/vault-keeper.md`** is the single agent that fronts everything else. It loads `vault-ops`, then routes each request to the right skill (update its routing table when a skill is added or renamed). Its `tools:` list is an allowlist: `Read`, `Bash`, `Skill` and specific `mcp__obsidian__*` tools. Plugin agents ignore `hooks`, `mcpServers` and `permissionMode` in frontmatter, so do not put them there.
- **`hooks/hooks.json` + `hooks/vault-guard.py`**: plugin-level PreToolUse hook that blocks `Read` of anything under the vault and `Bash` commands that name the vault path (heredoc bodies ignored). It acts only when the hook input's `agent_type` ends in `vault-keeper`, so other sessions are unaffected. A tripwire, not a sandbox.
- **`skills/vault-ops`** is the shared core: hard rules, `references/` (one procedure per command), `templates/` (one per note type) and `scripts/vault_lint.py`.
- **Thin command skills** (`vault-project-init`, `vault-note-new`, `vault-lint`, `vault-index`, `vault-stats`, `vault-task-close`) are ~17-line wrappers that load `vault-ops/SKILL.md` and then one file in `vault-ops/references/`. Put procedure changes in the reference, not the wrapper.
- **Standalone skill**: `obsidian-archive-condense`. Sync diagnosis (`obsidian-sync-triage`) is a personal skill kept outside this plugin in `~/.agents/skills/`; the agent refers to it only if it is installed.
- Skills refer to bundled files as `${CLAUDE_PLUGIN_ROOT}/skills/...`, which only resolves when loaded as a plugin. Plugin components are namespaced (`vault-keeper:vault-lint`). The plugin loader does not follow symlinks in component paths.

See also [`skills/README.md`](skills/README.md).

## Commands

```bash
S=skills/vault-ops/scripts/vault_lint.py
uv run --script $S check <draft.md> --path "<vault-relative path>"   # lint one draft; exit 1 on errors
uv run --script $S sweep [--project "<name>"] [--min-severity warn]  # whole vault, read-only
uv run --script $S stats [--project "<name>"]
uv run --script $S next-adr "<project>"
```

`vault_lint.py` is a PEP 723 script (pyyaml pinned in its header), so use `uv run --script`; no venv to manage. It is strictly read-only. It loads the schema from the fenced `# vault-schema` yaml block in the vault's schema note, layered over `DEFAULT_SCHEMA` in the script, so a rule change usually belongs in the vault note rather than the script.

## Rules that shape any edit here

- Skills must keep telling agents to **write to the vault only through the Obsidian MCP** (`vault_write`/`vault_patch`/...), never the filesystem, because the vault syncs via CouchDB and a filesystem write can strand a note. Reading the filesystem copy is fine.
- Archive-first (`vault_copy` into `_Archive/` before overwriting or condensing), lint-before-write (new notes must have zero `error` findings), and read-back-after-write are the load-bearing workflow; preserve them in any new or changed procedure.
- `vault_patch` heading targets are a JSON array (`["Heading"]`); Obsidian resolves `[[links]]` by file name, not alias.
- Templates use `{{placeholder}}` and `check` rejects any leftover `{{...}}`.
- Bourbon Book repo ADRs are owned by the `adr-authoring` skill (not in this repo); vault ADRs follow the schema.
