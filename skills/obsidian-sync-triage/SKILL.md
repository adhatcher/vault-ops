---
name: obsidian-sync-triage
description: Diagnose and repair Obsidian sync failures across Aaron's four peers — the Mac vault, the headless Obsidian container on Unraid, CouchDB, the livesync-bridge mirror, and iOS devices. Use when a note written on one device does not appear on another, when an MCP vault_write returns OK but nothing propagates, when the bridge echoes or floods, or when the user asks to check, debug, or repair Obsidian sync.
---

# Obsidian Sync Triage

## Purpose

Aaron's vault syncs through five participants. A write can stall at any hop, and
several failure modes are **silent** — the writing client reports success while
the note goes nowhere. This skill locates the stall, names the cause, and repairs it.

The single most important rule: **an OK from a write API is not evidence of sync.**
Always confirm at the far end.

## Topology

```
Mac Obsidian ─┐
iPad / iPhone ─┼─→ CouchDB (obsidian_test) ─→ livesync-bridge ─→ mirror
headless Obsidian ─┘         ▲                                  /mnt/user/obsidian
      ▲                      │
      │                 authority for all peers
 REST API / MCP
 (Cline, Codex, Claude Code)
```

| Participant | Address | Notes |
|---|---|---|
| Mac vault | `/Users/aaron/Obsidian` | canonical copy; Tailscale `100.78.154.116` |
| headless Obsidian | container `obsidian-headless`, `172.18.0.4` | own vault at `/mnt/user/appdata/obsidian/obsidian-headless/vault` — **never** the mirror |
| CouchDB | container `obsidian-couchdb`, `172.18.0.2` | database is **`obsidian_test`**, not the `obsidian` value in the project `.env` |
| livesync-bridge | container `obsidian-livesync-bridge`, `172.18.0.3` | mounts `/mnt/user/obsidian` → `/app/data`, peer `baseDir: data/` |
| mirror | `/mnt/user/obsidian` | filesystem view; bridge-written, not a LiveSync peer |
| iOS devices | e.g. `100.104.67.20` | easy to forget during passphrase or credential changes |

Tailscale Serve (tainet only, Funnel off):

| URL | Proxies to | Purpose |
|---|---|---|
| `https://gringotts.tail441593.ts.net:8444` | `127.0.0.1:5984` | CouchDB |
| `https://gringotts.tail441593.ts.net:8445` | `127.0.0.1:27123` | Local REST API + MCP endpoint |
| `https://gringotts.tail441593.ts.net:8446` | `127.0.0.1:3003` | headless KasmVNC GUI (user `obsidian-crane`) |

The GUI needs no SSH tunnel. If someone reaches for `ssh -L 3003:...`, that is the
old workaround — use `:8446`.

## First move: locate the stall

Run the sweep script with the path of a note that is misbehaving:

```
scripts/obsidian-sync-check.sh "01 Projects/Some Note.md"
```

It reports presence at all four locations, peer traffic, bridge activity and
container health. Read the presence table first — where the file stops names the
broken hop:

| Present in | Missing from | Broken hop |
|---|---|---|
| headless only | CouchDB, mirror, Mac | headless peer is not replicating → §1 |
| headless + CouchDB | mirror, Mac | bridge is down or misconfigured → §3 |
| Mac only | everything else | Mac's LiveSync is off or Obsidian is closed |
| everywhere but one device | that device | that peer's config or passphrase → §4 |

## Who is talking to CouchDB

CouchDB is the authority, so "which peers are actually connected" answers most
questions faster than any config file. Either of:

```
scripts/obsidian-sync-check.sh --peers          # just this report
ssh UNRAID 'python3 -' < scripts/couchdb-peers.py
```

It parses CouchDB's request log, resolves each address to a real name (docker
containers and tailnet hosts), and reports per peer: request count, `_changes`
polls, writes, errors, last-seen time, and a verdict.

```
peer                                  address          reqs  chg  writes  errs  last      state
obsidian-headless (last known)        172.18.0.4       1077   25     655     3  01:16:10  replicating
ipad-air-5th-gen-wifi (tailnet)       100.104.67.20     239    5     147     0  23:49:12  replicating
aaron-23-air (tailnet)                100.78.154.116    228   34      57    12  01:31:11  replicating
obsidian-livesync-bridge (last known) 172.18.0.3         58   38      20     0  01:16:09  replicating
```

Reading it:

- **`replicating`** — has `_changes` polls. A real peer.
- **`HANDSHAKE ONLY`** — connected and authenticated but never polled `_changes`.
  This is the profile-tested-but-not-applied state, and it looks healthy in the UI.
- **absent entirely** — not syncing, whatever that device claims.

Expect five: Mac, iPad, iPhone, headless, bridge. A missing row is the finding —
**but only from a window that is not saturated.** A single busy peer (a phone doing
its initial sync) can fill the entire log window and crowd the quiet ones out, which
turns "absent" into a false alarm. The report prints the window it used and warns
when it sees fewer than five peers; widen it before concluding anything:

```
ssh UNRAID 'python3 - 40000' < scripts/couchdb-peers.py
```

Names marked *(last known)* come from a fallback table: a stopped container releases
its IP, so live lookup returns nothing for precisely the container you are most
likely debugging. Cross-check against the container list rather than assuming the
name is current.

Errors in the `errs` column are normal in bursts during a rebuild or a first sync,
and suspicious when they persist at idle.

## §1 Headless peer not replicating

**The signature failure.** REST/MCP writes land on the headless container's disk
and never leave. Every client reports success. This is the one to suspect first
whenever Cline, Codex or Claude Code "wrote" a note nobody can find.

Confirm with peer traffic, not with config files:

```
docker logs --tail 400 obsidian-couchdb 2>&1 | grep 172.18.0.4 | grep -v _up | tail
```

- **No lines at all** → the peer is not even trying. Not replicating.
- **Only `OPTIONS` / `GET /obsidian_test/`** → a connection *test* succeeded but the
  profile was never applied. Not replicating.
- **`POST /obsidian_test/_changes?...feed=longpoll`** plus `_local/...` checkpoint
  reads → genuinely replicating.

**Do not diagnose from `data.json` plaintext fields.** The plugin stores the
connection in `encryptedCouchDBConnection`, which leaves `couchDB_URI`,
`couchDB_USER` and `couchDB_PASSWORD` blank even when fully configured. Blank
fields prove nothing. The trustworthy keys are the toggles:

```
liveSync / periodicReplication / syncOnSave / syncOnStart
```

If `liveSync` is `false` and there is no `_changes` traffic, sync is off.

**Repair** — in the GUI at `:8446`, Self-hosted LiveSync → Remote Database:

| Field | Value |
|---|---|
| Remote Type | CouchDB |
| URI | `http://obsidian-couchdb:5984` |
| Username | `obsidian` |
| Database name | `obsidian_test` |

Password lives in the bridge config; retrieve it without displaying it:

```
ssh UNRAID "python3 -c \"import json;print(json.load(open('/mnt/user/appdata/obsidian/obsidian-livesync-bridge/config/config.json'))['peers'][0]['password'])\"" | tr -d '\n' | pbcopy
```

Prefer `http://obsidian-couchdb:5984` over the Tailscale URL. Both work — the
container can route to the tailnet — but the container-network hop has no TLS and
no dependency on tailscaled being healthy.

Then: Test Database Connection → Check Database Configuration → apply fixes →
**Fetch from Remote** (never "send to remote"; the remote is authoritative and
headless's local copy may hold `.trash` content) → enable LiveSync under Sync Settings.

Testing the connection and applying the profile are separate steps. Stopping after
the green test leaves `remoteType` empty and sync off.

**Keep hidden-file and customization sync OFF.** headless has its own `.obsidian`
with its own plugins. Syncing it pushes workspace caches to CouchDB and out to
every device. The separate-vault design exists precisely to prevent this.

Watch for duplicate saved profiles under `remoteConfigurations` — a portless
`CouchDB gringotts.tail441593.ts.net` entry has been observed alongside the correct
`:8444` one. Delete the portless one so it cannot be selected by accident.

## §2 The MCP is not the model

An error naming `litellm`, `Ollama_chatException`, a model group, or token limits is
a **client LLM** failure, not a sync failure. The Obsidian MCP performs no inference.

One real instance: `{"error":"no user query found in messages"}` from
`ollama_chat/qwen3.8:latest`. Ollama's built-in renderer for that model rejects any
request without a `role: "user"` message, which is exactly the shape of a tool-result
follow-up. Reproduce directly, bypassing every intermediary:

```
curl -s http://localhost:11434/api/chat -d '{"model":"MODEL","stream":false,
  "messages":[{"role":"system","content":"s"},{"role":"assistant","content":"a"},{"role":"tool","content":"t"}]}'
```

An error means that model cannot do MCP tool calls. `qwen3-coder:30b`,
`devstral-small-2` and `gemma4:26b-a4b-it-q4_K_M` accept it; `qwen3.8:latest` does not.

Prefer a model without a `thinking` capability for agentic work — thinking tokens are
spent from the output budget and cause mid-turn truncation. Context size is `num_ctx`,
unrelated to model size; the LiteLLM config sets none, so Ollama's default applies
regardless of the model's advertised context length.

## §3 Bridge problems

Bridge log grammar:

```
[obsidian-couchdb] --> <path> change detected      couch → bridge  (normal)
[unraid-filesystem-mirror] <-- data/<path> saved   bridge → mirror (normal)
[mirror] --> <path>                                mirror → couch  (ECHO — investigate)
```

A `mirror] -->` line for a file that originated remotely means the Phase 0 echo fix
has regressed. `Peer.isRepeating()` keyed the two directions differently — `put()`
and `delete()` used `toLocalPath(path)` while `dispatch()` used the storage-relative
path, so the cache always missed and every write echoed back. `01 Roadmap.md` once
cycled 248 times.

Patch and regression tests: `~/Documents/Development/apps/obsidian-workflow-mcp/bridge-patch/`.
**Re-apply the patch before any bridge rebuild** — a plain rebuild silently reverts it.

Verify the fix still holds after any change involving a new writer:

```
docker logs --tail 50 obsidian-livesync-bridge | grep "mirror] -->"
```

Empty is correct.

## §4 Credentials, passphrases and fan-out

Every credential or passphrase change is a **fan-out** across Mac, iPad, iPhone,
headless and the bridge. A peer left behind fails to decrypt or pushes conflicts.

- The bridge holds the CouchDB password and passphrase in **plaintext** in
  `config/config.json`. Enumerate peers from that file, not from memory.
- A rotation on 2026-09-02 (`/mnt/user/appdata/obsidian/.rotation-backups/`) coincided
  with the headless peer falling out of sync. After any rotation, verify §1 explicitly.
- The mirror at `/mnt/user/obsidian` is always plaintext on disk. E2EE protects
  CouchDB and the wire, not the mirror.
- **Never enter or handle Aaron's passphrases.** Give him a command that reads the
  secret locally and pipes it, so it stays out of shell history and out of context.

## Enabling or changing E2EE

Done once on 2026-09-03. Every trap below was hit live.

**The button choice is the whole risk.** LiveSync's E2EE panel offers `Configure` and
`Configure And Change Remote`, and the correct one *inverts* by device:

| Device | Button | Why |
|---|---|---|
| Mac (canonical vault) | **Configure And Change Remote** | it is the source; the server must be rewritten from it |
| headless, iPad, iPhone | **Configure**, then Fetch from Remote | the server is already correct; these are stale |

Pressing "Change Remote" on a non-Mac peer rebuilds the good database from that
peer's stale copy. There is no undo but the backup.

**Order:** stop the bridge and headless → Mac enables E2EE and changes remote →
set the bridge passphrase and start it → start headless, configure, fetch →
iOS devices → round trip. Peers left running during the Mac rebuild will fight it.

**Setting E2EE to true is a separate act from entering the passphrase.** A filled
passphrase box with `End-to-End Encryption: false` produces a complete, successful,
*unencrypted* rebuild. This happened on the first attempt and the UI reported success.

**Never trust the UI that encryption is on.** Verify by sampling content chunks —
note text lives in `type: leaf` documents, and encrypted ones begin `%=`:

```
curl -s -u obsidian:PW "http://localhost:5984/obsidian_test/_all_docs?include_docs=true&limit=500" \
 | python3 -c 'import sys,json
d=json.load(sys.stdin)
lv=[r["doc"] for r in d["rows"] if r.get("doc",{}).get("type")=="leaf"]
pl=[L for L in lv if any(w in L.get("data","") for w in (" the "," and ","# ","---","[["))]
print(len(lv),"leaves",len(pl),"plaintext")'
```

Any non-zero plaintext count means encryption is not active.

**The bridge needs only `passphrase`** in its peer config — no boolean. It reads
`encrypt` from the remote (`useRemoteTweaks: true`) and fails loudly:
`Remote database is encrypted but no passphrase provided.` (`PeerCouchDB.ts:228`).
It must be restarted after the edit; it will not pick up config while retrying.

**Writing the passphrase without leaking it.** `read -rs -p` silently yields an empty
string when run without a TTY, and an empty passphrase then gets written as if it
worked. Use the clipboard and assert non-empty:

```
pbpaste | tr -d '\r\n' | ssh UNRAID 'python3 -c "
import json,sys
p=\"/mnt/user/appdata/obsidian/obsidian-livesync-bridge/config/config.json\"
v=sys.stdin.read(); assert v, \"clipboard empty\"
d=json.load(open(p)); d[\"peers\"][0][\"passphrase\"]=v
json.dump(d,open(p,\"w\"),indent=1); print(\"set (%d chars)\" % len(v))"'
```

Compare the reported length against the Mac's `passphrase` length. Never enter or
handle the value directly.

**A peer with `encrypt: false` against an encrypted remote is safe but stuck.**
LiveSync refuses to replicate content rather than pushing plaintext — verified: the
remote stayed at 0 plaintext chunks while such a peer was live. It still writes its
`_local/..._milestone` node registration, which adds to the dead-node accumulation
in that document.

**Blank plaintext fields again.** After a successful E2EE setup, headless shows
`passphrase = ''` — it lives in `encryptedPassphrase`. Judge by `encrypt: true` plus
a correct note count, never by that field.

**During a fetch, `_revs_diff` POSTs are reads, not writes.** A peer downloading
shows `_revs_diff` and `_local` checkpoint traffic while `update_seq` and `doc_count`
stay put. That combination means pulling; a climbing `update_seq` means pushing.

Leave **Property Encryption** and **path obfuscation** off. Hidden File Sync and
Customisation Sync must stay off permanently — LiveSync's post-setup dialog suggests
re-enabling them; ignore it.

## Rotating the CouchDB password

Done 2026-09-03. Three approaches failed first; use the last one.

**What does not work:**

1. **Editing the project `.env` alone.** A running container's environment is fixed
   at creation. `.env` only matters at create time.
2. **The config API on its own.** `PUT /_node/_local/_config/admins/obsidian` works
   against the live node, but the image's entrypoint re-asserts
   `[admins] obsidian = $COUCHDB_PASSWORD` from the *container's* env on every start,
   silently reverting it at the next restart.
3. **`.env` + `--force-recreate`.** The entrypoint writes the admin only when none is
   configured. A stale hashed entry in `local.d/docker.ini` survives the recreate and
   stays authoritative, so the new env value is ignored.

**What works** — write it offline, where no authentication is involved:

```
docker stop obsidian-couchdb
# in /mnt/user/appdata/obsidian/obsidian-livesync-couchdb/local.d/docker.ini
# replace the single `obsidian = ...` line with the plaintext new password
docker start obsidian-couchdb        # CouchDB hashes it during startup
```

Update the project `.env` **and** recreate the container as well, so container env,
`.env` and `docker.ini` all agree. If they diverge, the next restart silently reverts
the password and the failure looks like a peer problem.

Verify old → 401, new → 200, and confirm `docker.ini` shows `-pbkdf2:` rather than a
readable string.

**Account lockout will ambush you.** CouchDB 3.4+ locks an account after repeated
auth failures:

```
{"error":"forbidden","reason":"Account is temporarily locked due to multiple
 authentication failures"}
```

A **403 instead of 401 means lockout, not a wrong password**, and every request in
that window fails including correct ones. Peers still holding the old password
generate these continuously, so a rotation left half-finished re-locks the account
and blocks the peers you already fixed. Restarting CouchDB clears the in-memory
lock. Update every peer promptly, or pause sync on the ones you cannot reach.

**Check for extra admins before rotating.** `docker.ini` accumulated a second full
admin (`ols_...`) from an earlier rotation, plus three duplicate `[admins]` sections.
Rotating one of two admin credentials is not a rotation. Enumerate first:

```
grep -A5 "^\[admins\]" .../local.d/docker.ini
```

**Fan-out:** bridge config (`peers[0].password`, then restart), then the Mac, iPad,
iPhone and headless UIs. Only the password changes — URI, database, username and the
E2EE passphrase stay as they are.

## Before anything destructive

An E2EE enable, a "Rebuild everything", or a database recreate **wipes the remote**.
There is no automatic vault backup — `/mnt/user/appdata/obsidian/obsidian-git` is dead
(one commit, two files), and neither the Mac vault nor the mirror is a git repo.

Take all three first:

```
D=/mnt/user/Aaron_NAS/obsidian-backups; TS=$(date +%Y%m%d-%H%M)
tar -czf $D/obsidian-mirror-$TS.tar.gz -C /mnt/user/obsidian .
curl -s -u obsidian:PW 'http://localhost:5984/obsidian_test/_all_docs?include_docs=true' | gzip > $D/couchdb-obsidian_test-$TS.json.gz
# and off-server, on the Mac:
tar -czf ~/Obsidian-backups/obsidian-mac-vault-$TS.tar.gz -C /Users/aaron/Obsidian .
```

Rebuild order when enabling E2EE: stop the bridge → Mac enables E2EE and rebuilds →
set the bridge passphrase and start it → every other peer fetches from remote →
verify with a round trip. Leave path obfuscation off; it changes document IDs and
makes failures unreadable.

## Always finish with a round trip

Repairs are not done until a write **and** a delete propagate. Write through the MCP,
then confirm at all four locations and check the bridge stayed quiet:

```
scripts/obsidian-sync-check.sh "mcp-roundtrip-test.md"
```

A healthy round trip lands everywhere within about a second and produces no
`mirror] -->` line. Delete the test file afterwards and confirm the deletion
propagates too — delete is a separate code path and has failed independently.

## Guardrails

- Aaron's containers are not to be changed without per-task authorization. Read-only
  diagnosis is always fine; `docker restart`, compose edits and `tailscale serve`
  changes are not. Record any exception.
- Never point the bridge or any peer at `/mnt/user/obsidian` as an Obsidian vault. The
  bridge does no hidden-file filtering, so `.obsidian` would replicate to every device.
- `ls /mnt/user/obsidian/.obsidian` must report *No such file or directory*.
