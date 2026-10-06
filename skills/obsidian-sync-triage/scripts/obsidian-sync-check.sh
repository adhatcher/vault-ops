#!/usr/bin/env bash
# Read-only sweep of Aaron's Obsidian sync chain.
# Usage: obsidian-sync-check.sh ["vault/relative/Note.md"]
# Makes no changes. Prints no secrets.

set -uo pipefail

MODE="all"
if [ "${1:-}" = "--peers" ]; then MODE="peers"; shift; fi
TAILN="${TAILN:-12000}"
NOTE="${1:-}"
MAC_VAULT="/Users/aaron/Obsidian"
MIRROR="/mnt/user/obsidian"
HEADLESS="/mnt/user/appdata/obsidian/obsidian-headless/vault"
SSH="ssh -o ConnectTimeout=12 UNRAID"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

hr() { printf '\n\033[1m== %s\033[0m\n' "$1"; }

if ! $SSH true 2>/dev/null; then
  echo "FATAL: cannot reach UNRAID over ssh." >&2
  exit 1
fi

if [ -n "$NOTE" ]; then
  hr "Presence of: $NOTE"
  printf '  %-10s %s\n' "Mac" "$([ -f "$MAC_VAULT/$NOTE" ] && echo PRESENT || echo absent)"
  $SSH "
    printf '  %-10s %s\n' 'headless' \"\$([ -f '$HEADLESS/$NOTE' ] && echo PRESENT || echo absent)\"
    printf '  %-10s %s\n' 'mirror'   \"\$([ -f '$MIRROR/$NOTE'   ] && echo PRESENT || echo absent)\"
  "
  echo "  (headless-only = peer not replicating, see SKILL.md §1)"
fi

hr "Containers (stopped containers are a finding, not a footnote)"
$SSH 'docker ps -a --format "{{.Names}}\t{{.State}}\t{{.Status}}" | grep -i obsidian | \
  while IFS=$'"'"'\t'"'"' read -r n st rest; do
    if [ "$st" = "running" ]; then printf "  OK   %-28s %s\n" "$n" "$rest"
    else printf "  FAIL %-28s %s  <-- not running\n" "$n" "$rest"; fi
  done'
echo "  (obsidian-livesync-bridge down = mirror stops tracking CouchDB;"
echo "   docker logs still works on a stopped container, so logs alone can mislead)"

hr "Who is talking to CouchDB"
$SSH "python3 - $TAILN" < "$HERE/couchdb-peers.py" 2>&1 || echo "  (peer report failed)"

if [ "$MODE" = "peers" ]; then echo; echo "Done (--peers mode). Nothing was modified."; exit 0; fi

hr "headless LiveSync toggles (plaintext URI fields are meaningless - see SKILL.md §1)"
$SSH 'python3 -c "
import json
p=\"/mnt/user/appdata/obsidian/obsidian-headless/vault/.obsidian/plugins/obsidian-livesync/data.json\"
try: d=json.load(open(p))
except Exception as e: print(\"  cannot read data.json:\",e); raise SystemExit
for k in (\"liveSync\",\"periodicReplication\",\"syncOnSave\",\"syncOnStart\",\"encrypt\",\"syncInternalFiles\",\"usePluginSync\"):
    print(\"  %-22s %s\" % (k, d.get(k)))
print(\"  %-22s %s\" % (\"connection stored\", bool(d.get(\"encryptedCouchDBConnection\"))))
rc=d.get(\"remoteConfigurations\",{})
print(\"  saved remote profiles: %d\" % len(rc))
for v in rc.values(): print(\"    -\", v.get(\"name\"))
"'

hr "Bridge activity (last 15 lines)"
$SSH 'docker logs --tail 15 obsidian-livesync-bridge 2>&1 | sed "s/^/  /"'

hr "Bridge echo check (any output here is a REGRESSION of the Phase 0 fix)"
$SSH 'docker logs --tail 200 obsidian-livesync-bridge 2>&1 | grep "mirror\] -->" | tail -5 | sed "s/^/  /" || true'
echo "  (empty above = correct)"

hr "Hidden-file guardrail"
$SSH 'if [ -e "/mnt/user/obsidian/.obsidian" ]; then echo "  FAIL - .obsidian present in mirror"; else echo "  OK - no .obsidian in mirror"; fi'

hr "Tailscale Serve"
$SSH 'tailscale serve status 2>/dev/null | sed "s/^/  /" || echo "  (unavailable)"'

hr "MCP endpoint"
U="https://gringotts.tail441593.ts.net:8445/mcp"
BODY='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"triage","version":"1"}}}'
printf '  unauthenticated: %s (expect 401)\n' \
  "$(curl -sS -o /dev/null -w '%{http_code}' --max-time 12 -X POST "$U" \
     -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' -d "$BODY" 2>/dev/null)"
if [ -n "${OBSIDIAN_MCP_TOKEN:-}" ]; then
  printf '  authenticated:   %s (expect 200)\n' \
    "$(curl -sS -o /dev/null -w '%{http_code}' --max-time 15 -X POST "$U" \
       -H "Authorization: Bearer $OBSIDIAN_MCP_TOKEN" \
       -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' -d "$BODY" 2>/dev/null)"
else
  echo "  authenticated:   skipped (OBSIDIAN_MCP_TOKEN not in env)"
fi

hr "Connected MCP clients"
lsof -nP -i TCP:8445 2>/dev/null | awk '/ESTABLISHED/{print "  " $1 "  pid " $2}' | sort -u || echo "  (none)"

hr "Vault counts"
echo "  Mac:    $(find "$MAC_VAULT" -name '*.md' -not -path '*/.obsidian/*' -not -path '*/.trash/*' 2>/dev/null | wc -l | tr -d ' ') notes"
$SSH "
  echo \"  mirror: \$(find $MIRROR -name '*.md' -not -path '*/.trash/*' 2>/dev/null | wc -l) notes\"
  echo \"  headless: \$(find $HEADLESS -name '*.md' -not -path '*/.obsidian/*' -not -path '*/.trash/*' 2>/dev/null | wc -l) notes\"
"

hr "Backups"
$SSH 'ls -1t /mnt/user/Aaron_NAS/obsidian-backups 2>/dev/null | head -4 | sed "s/^/  server: /" || echo "  server: (none)"'
ls -1t ~/Obsidian-backups 2>/dev/null | head -2 | sed 's/^/  mac:    /' || echo "  mac:    (none)"

echo
echo "Done. Nothing was modified."
