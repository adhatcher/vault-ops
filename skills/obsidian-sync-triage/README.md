# Obsidian Sync Triage

Diagnoses and repairs sync failures across Aaron's Obsidian setup: the Mac vault,
the headless Obsidian container on Unraid, CouchDB, the livesync-bridge mirror,
and iOS devices.

## Why this exists

Several failure modes in this chain are silent — a client's `vault_write` returns
`OK` while the note never leaves the container it was written in. On 2026-09-03 two
notes written through the MCP sat stranded in the headless vault for an hour while
every client reported success. This skill exists so that hop is checked first
instead of rediscovered.

## Use it when

- A note written on one device does not appear on another
- An MCP `vault_write` returns OK but nothing propagates
- The bridge floods, echoes, or goes quiet
- After any credential rotation, passphrase change, or container rebuild

## Quick start

```bash
scripts/obsidian-sync-check.sh "01 Projects/Some Note.md"
```

Read-only. Changes nothing, prints no secrets. The presence table at the top names
the broken hop; `SKILL.md` has the repair for each.

Set `OBSIDIAN_MCP_TOKEN` in the environment to include the authenticated
endpoint check.

## Contents

- `SKILL.md` — topology, failure modes, repairs, guardrails
- `scripts/obsidian-sync-check.sh` — read-only diagnostic sweep
