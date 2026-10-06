#!/usr/bin/env python3
"""Report which peers are talking to CouchDB. Runs ON the Unraid host.

Invoked as:  ssh UNRAID 'python3 -' < couchdb-peers.py [tail_lines]
Read-only. Prints no credentials.
"""
import re
import subprocess
import sys

TAIL = int(sys.argv[1]) if len(sys.argv) > 1 else 12000
CONTAINER = "obsidian-couchdb"

# CouchDB notice line:
# [notice] <ts> nonode@nohost <pid> <reqid> <host:port> <ip> <user> <METHOD> <path> <code> ok <ms>
LINE = re.compile(
    r"^\[\w+\]\s+(\S+)\s+\S+\s+<[^>]+>\s+\S+\s+(\S+)\s+(\S+)\s+(\S+)\s+"
    r"(GET|PUT|POST|DELETE|HEAD|OPTIONS|COPY)\s+(\S+)\s+(\d{3})"
)


def sh(cmd):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True,
                              timeout=30).stdout
    except Exception:
        return ""


# Stopped containers release their IP, so a live lookup returns nothing for
# exactly the containers you are most likely to be debugging. These are the
# observed assignments on the obsidian compose network, used only as fallback.
HINTS = {
    "172.18.0.2": "obsidian-couchdb (last known)",
    "172.18.0.3": "obsidian-livesync-bridge (last known)",
    "172.18.0.4": "obsidian-headless (last known)",
    "127.0.0.1": "unraid host (diagnostics/healthcheck)",
}


def name_map():
    """ip -> friendly name, from docker and from tailscale."""
    m = dict(HINTS)
    names = sh("docker ps -a --format '{{.Names}}'").split()
    for n in names:
        ip = sh("docker inspect %s --format "
                "'{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}'" % n).strip()
        for part in ip.split():
            if part:
                m[part] = n
    for line in sh("tailscale status").splitlines():
        f = line.split()
        if len(f) >= 2 and f[0].count(".") == 3:
            m[f[0]] = f[1] + "  (tailnet)"
    return m


def main():
    logs = sh("docker logs --tail %d %s 2>&1" % (TAIL, CONTAINER))
    if not logs.strip():
        print("  cannot read logs for %s" % CONTAINER)
        return

    names = name_map()
    peers = {}
    for line in logs.splitlines():
        mt = LINE.match(line.strip())
        if not mt:
            continue
        ts, _hostport, ip, user, method, path, code = mt.groups()
        if path.startswith("/_up"):          # healthcheck noise
            continue
        p = peers.setdefault(ip, {
            "n": 0, "first": ts, "last": ts, "user": set(),
            "changes": 0, "writes": 0, "errors": 0, "paths": {},
        })
        p["n"] += 1
        p["last"] = ts
        if user not in ("undefined", "-"):
            p["user"].add(user)
        if "_changes" in path:
            p["changes"] += 1
        if method in ("PUT", "POST") and "_changes" not in path:
            p["writes"] += 1
        if code[0] in "45":
            p["errors"] += 1
        key = path.split("?")[0]
        p["paths"][key] = p["paths"].get(key, 0) + 1

    if not peers:
        print("  no non-healthcheck CouchDB traffic in the last %d log lines" % TAIL)
        print("  -> nothing is replicating at all")
        return

    print("  %-42s %-17s %6s %5s %6s %6s  %-8s %s" %
          ("peer", "address", "reqs", "chg", "writes", "errs", "last", "state"))
    print("  " + "-" * 112)
    for ip, p in sorted(peers.items(), key=lambda kv: -kv[1]["n"]):
        who = names.get(ip, "unknown")
        if p["user"]:
            who += " [" + ",".join(sorted(p["user"])) + "]"
        if p["changes"]:
            state = "replicating"
        elif p["n"] <= 4:
            state = "HANDSHAKE ONLY"
        else:
            state = "connected, no _changes"
        if p["errors"]:
            state += " (%d errors)" % p["errors"]
        last = p["last"][11:19] if len(p["last"]) > 19 else p["last"]
        print("  %-42s %-17s %6d %5d %6d %6d  %-8s %s" %
              (who[:42], ip, p["n"], p["changes"], p["writes"], p["errors"], last, state))

    stamps = sorted(p["first"] for p in peers.values())
    span = "%s .. %s" % (stamps[0][11:19], max(p["last"] for p in peers.values())[11:19])
    print("\n  window: %d log lines, covering %s" % (TAIL, span))
    if len(peers) < 5:
        print("  WARNING: only %d peers seen. A busy peer can fill the whole window and" % len(peers))
        print("           crowd quiet ones out, so absence here may be an artefact.")
        print("           Re-run with a bigger window before concluding anything:")
        print("             ssh UNRAID 'python3 - 40000' < couchdb-peers.py")
    print("\n  expected peers: Mac, iPad, iPhone, obsidian-headless, obsidian-livesync-bridge")
    print("  a peer absent from a NON-saturated window is not syncing, whatever its UI says")

    print("\n  top paths per peer:")
    for ip, p in sorted(peers.items(), key=lambda kv: -kv[1]["n"]):
        top = sorted(p["paths"].items(), key=lambda kv: -kv[1])[:3]
        print("    %-17s %s" % (ip, ", ".join("%s (%d)" % (k, v) for k, v in top)))

    print("\n  live TCP connections to CouchDB (from inside the container):")
    print("    note: tailnet peers arrive proxied via Tailscale Serve, so they show")
    print("    as the docker gateway (172.18.0.1), not their own address.")
    raw = sh("docker exec %s sh -c 'cat /proc/net/tcp /proc/net/tcp6 2>/dev/null'" % CONTAINER)
    seen = {}
    for line in raw.splitlines()[1:]:
        f = line.split()
        if len(f) < 4 or f[3] != "01":          # 01 = ESTABLISHED
            continue
        loc, rem = f[1], f[2]
        try:
            if int(loc.rsplit(":", 1)[1], 16) != 5984:
                continue
            hexip = rem.rsplit(":", 1)[0]
        except (ValueError, IndexError):
            continue
        if len(hexip) == 8:                      # IPv4, little-endian
            ip = ".".join(str(int(hexip[i:i + 2], 16)) for i in (6, 4, 2, 0))
        else:                                    # IPv4-mapped IPv6 tail
            tail = hexip[-8:]
            ip = ".".join(str(int(tail[i:i + 2], 16)) for i in (6, 4, 2, 0))
        seen[ip] = seen.get(ip, 0) + 1
    if seen:
        for ip, c in sorted(seen.items(), key=lambda kv: -kv[1]):
            print("    %-17s %-42s %d connection(s)" % (ip, names.get(ip, "unknown")[:42], c))
    else:
        print("    (none established right now)")


main()
