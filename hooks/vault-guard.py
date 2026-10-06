#!/usr/bin/env python3
"""PreToolUse guard for the vault-keeper agent: the vault is reached through the Obsidian MCP only.

Registered at plugin level (plugin agents cannot declare hooks), so it runs for every session and
acts only when the hook input names the vault-keeper agent in `agent_type`. Calls from the main
session, or from any input without that field, pass through untouched.

Blocks Read of any file under the vault, and Bash commands that name the vault path. Heredoc bodies
are ignored, so a note that mentions the path can still be piped to `vault_lint.py check`. Exit 2
blocks the call and returns stderr to the agent. This is a tripwire, not a sandbox: it cannot catch
a path built at run time or reached by `cd`.
"""
import json
import os
import re
import sys

VAULT = os.environ.get("VAULT_ROOT", "/Users/aaron/Obsidian").rstrip("/")
HOME = os.path.expanduser("~")
NAMES = {VAULT, "~/Obsidian", "$HOME/Obsidian", "${HOME}/Obsidian", HOME + "/Obsidian", "VAULT_ROOT"}
HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1[^\n]*\n.*?\n\s*\2\s*(?:\n|$)", re.S)


def block(msg: str) -> None:
    print(f"vault-guard: {msg} Use the mcp__obsidian__vault_* tools.", file=sys.stderr)
    sys.exit(2)


def main() -> None:
    call = json.load(sys.stdin)
    if not str(call.get("agent_type", "")).endswith("vault-keeper"):
        return
    tool, args = call.get("tool_name", ""), call.get("tool_input", {})
    if tool == "Read":
        path = os.path.realpath(os.path.expanduser(args.get("file_path", "")))
        if path == VAULT or path.startswith(VAULT + "/"):
            block("reading the vault from disk is not allowed.")
    elif tool == "Bash":
        cmd = HEREDOC.sub("\n", args.get("command", ""))
        if any(n in cmd for n in NAMES):
            block("shell commands must not reference the vault path.")


main()
