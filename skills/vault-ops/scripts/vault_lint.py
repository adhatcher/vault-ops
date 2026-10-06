#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml==6.0.3"]
# ///
"""Lint Aaron's Obsidian vault against the Vault Schema.

READ-ONLY. This script never writes to the vault. All vault writes go through
the Obsidian MCP (vault_write / vault_patch / ...), never the filesystem.

Modes:
  sweep    (default) lint every note, plus cross-note rules (indexes, ADRs, Home)
  check    lint ONE note's content (stdin or file) as if it lived at --path;
           use this on a draft BEFORE calling vault_write
  stats    note counts by type/status/project and condense candidates
  next-adr print the next ADR number for a project

Exit status: 1 when any `error` finding is reported, otherwise 0.

The schema is read from the fenced ```yaml block that starts with
`# vault-schema` in the vault's schema note, layered over DEFAULT_SCHEMA.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path

import yaml

DEFAULT_VAULT = os.environ.get("VAULT_ROOT", "/Users/aaron/Obsidian")
SCHEMA_NOTE = "01 Projects/Obsidian Knowledge System/Operations/Vault Schema.md"

DEFAULT_SCHEMA = {
    "types": [
        "index", "project", "area", "adr", "architecture", "design", "plan",
        "roadmap", "requirements", "runbook", "handoff", "task", "record",
        "milestone", "feature", "report", "research", "reference", "history",
        "finding", "note",
    ],
    "type_aliases": {
        "implementation-plan": "plan",
        "architecture-reference": "architecture",
    },
    "statuses": [
        "draft", "proposed", "open", "active", "in-progress", "blocked",
        "accepted", "done", "superseded", "deprecated", "rejected", "archived",
    ],
    "status_aliases": {
        "closed": "done", "complete": "done", "completed": "done",
        "shipped": "done", "in_progress": "in-progress",
    },
    "done_statuses": ["done", "accepted", "superseded", "archived"],
    "status_required_for": ["adr", "task", "plan", "roadmap"],
    "adr_digits": 3,
    "adr_digits_overrides": {},
    "exclude_top": [".obsidian", ".trash", ".git", "Excalidraw", "05 Memories"],
    "frozen_dirs": ["_Archive", "Archive"],
    "index_like_types": ["index", "milestone"],
    "index_like_names": ["_Milestone.md"],
    "hop_dirs": ["records"],
    "oversized_kb": 40,
    "condense_kb": 8,
    "condense_types": ["task", "record", "milestone", "plan", "handoff"],
    "severity": {
        "no-frontmatter": "error", "bad-frontmatter": "error",
        "missing-type": "error", "unknown-type": "warn", "legacy-type": "warn",
        "missing-title": "warn", "missing-owner": "warn", "owner-mismatch": "warn",
        "missing-status": "warn", "unknown-status": "warn", "legacy-status": "warn",
        "bad-date": "warn", "broken-link": "error", "ambiguous-link": "warn",
        "md-link": "info", "broken-md-link": "error", "archive-pointer": "error",
        "adr-name": "error", "adr-type": "warn", "adr-duplicate": "error",
        "adr-gap": "info", "unfilled-placeholder": "error", "oversized": "warn", "condense-candidate": "info",
        "missing-index": "warn", "missing-collection-index": "info",
        "not-in-index": "warn", "not-in-home": "warn", "duplicate-name": "info",
    },
}

SEV_ORDER = {"error": 0, "warn": 1, "info": 2}
FENCE_RE = re.compile(r"(```|~~~).*?\1", re.S)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
WIKILINK_RE = re.compile(r"(!?)\[\[([^\[\]\n]+?)\]\]")
MDLINK_RE = re.compile(r"(!?)\[[^\]\n]*\]\(([^)\n]+)\)")
SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
ARCHIVE_PTR_RE = re.compile(
    r"(?:[Oo]riginal(?: spec)?|Full original spec)[^`\n]{0,40}`([^`\n]+\.md)`"
)
ADR_NAME_RE = re.compile(r"^ADR[ -](\d+)[ -]\S")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PLACEHOLDER_RE = re.compile(r"\{\{[^}\n]+\}\}")


@dataclass
class Finding:
    sev: str
    rule: str
    path: str
    msg: str


@dataclass
class Note:
    rel: str
    text: str
    fm: dict | None
    body: str
    fm_error: str | None

    @property
    def name(self) -> str:
        return Path(self.rel).stem


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def split_frontmatter(text: str):
    text = text.lstrip("﻿")
    if not text.startswith("---"):
        return None, text, None
    lines = text.split("\n")
    if lines[0].strip() != "---":
        return None, text, None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            block = "\n".join(lines[1:i])
            body = "\n".join(lines[i + 1:])
            try:
                data = yaml.safe_load(block) if block.strip() else {}
            except yaml.YAMLError as e:
                return None, body, str(e).splitlines()[0]
            if not isinstance(data, dict):
                return None, body, "frontmatter is not a mapping"
            return data, body, None
    return None, text, "frontmatter block is not closed"


def load_schema(vault: Path) -> dict:
    schema = json.loads(json.dumps(DEFAULT_SCHEMA))
    note = vault / SCHEMA_NOTE
    if note.exists():
        for m in re.finditer(r"```yaml\n(.*?)```", note.read_text(encoding="utf-8"), re.S):
            if m.group(1).lstrip().startswith("# vault-schema"):
                override = yaml.safe_load(m.group(1)) or {}
                for k, v in override.items():
                    if isinstance(v, dict) and isinstance(schema.get(k), dict):
                        schema[k].update(v)
                    else:
                        schema[k] = v
                break
    return schema


class Vault:
    def __init__(self, root: Path, schema: dict):
        self.root = root
        self.schema = schema
        self.notes: dict[str, Note] = {}
        self.files: dict[str, list[str]] = defaultdict(list)
        self._scan()
        self._index()

    def _scan(self):
        for p in sorted(self.root.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(self.root).as_posix()
            if rel.split("/")[0] == ".obsidian" or "/.obsidian/" in rel:
                continue
            if p.suffix.lower() == ".md":
                self.add_note(rel, p.read_text(encoding="utf-8", errors="replace"))
            else:
                self.files[p.name.lower()].append(rel)

    def add_note(self, rel: str, text: str):
        fm, body, err = split_frontmatter(text)
        self.notes[rel] = Note(rel, text, fm, body, err)

    def _index(self):
        self.by_path: dict[str, str] = {}
        self.by_base: dict[str, list[str]] = defaultdict(list)
        self.by_alias: dict[str, list[str]] = defaultdict(list)
        for rel, n in self.notes.items():
            noext = rel[:-3].lower()
            self.by_path[noext] = rel
            self.by_base[Path(rel).stem.lower()].append(rel)
            aliases = (n.fm or {}).get("aliases")
            if isinstance(aliases, str):
                aliases = [aliases]
            for a in aliases or []:
                self.by_alias[str(a).lower()].append(rel)

    def resolve_wiki(self, target: str, from_rel: str) -> list[str]:
        t = target.strip().replace("\\", "/")
        if not t:
            return [from_rel]
        if t.startswith("./") or t.startswith("../"):
            t = os.path.normpath((Path(from_rel).parent / t).as_posix()).replace("\\", "/")
        tl = t.lower()
        if tl.endswith(".md"):
            tl = tl[:-3]
        if "/" in tl:
            if tl in self.by_path:
                return [self.by_path[tl]]
            return [r for k, r in self.by_path.items() if k.endswith("/" + tl)]
        # Obsidian resolves links by file name only; frontmatter aliases are not targets.
        hits = list(self.by_base.get(tl, []))
        if not hits:
            hits = list(self.files.get(t.lower(), []))
        return hits

    def exists_rel(self, from_rel: str, target: str) -> str | None:
        from urllib.parse import unquote
        t = unquote(target.strip())
        if t.startswith("<") and t.endswith(">"):
            t = t[1:-1]
        t = re.split(r"\s+\"", t)[0]
        t = t.split("#")[0].split("?")[0]
        if not t:
            return from_rel
        base = (Path(from_rel).parent / t).as_posix()
        for cand in (os.path.normpath(base), os.path.normpath(t)):
            if (self.root / cand).exists():
                return cand
        return None

    # ---- path helpers -------------------------------------------------
    def top(self, rel: str) -> str:
        return rel.split("/")[0]

    def is_excluded(self, rel: str) -> bool:
        return self.top(rel) in self.schema["exclude_top"]

    def is_frozen(self, rel: str) -> bool:
        parts = rel.split("/")[:-1]
        return any(p in self.schema["frozen_dirs"] for p in parts)

    def owner_of(self, rel: str):
        """(kind, folder-name) for 01 Projects/<P>/... or 02 Areas/<A>/..., else None."""
        parts = rel.split("/")
        if len(parts) >= 3 and parts[0] == "01 Projects":
            return "project", parts[1]
        if len(parts) >= 3 and parts[0] == "02 Areas":
            return "area", parts[1]
        return None

    def lintable(self, rel: str) -> bool:
        return not self.is_excluded(rel) and not self.is_frozen(rel)


def strip_code(body: str, inline: bool = True) -> str:
    body = COMMENT_RE.sub("", FENCE_RE.sub("", body))
    return INLINE_CODE_RE.sub("", body) if inline else body


def sev(schema: dict, rule: str) -> str:
    return schema["severity"].get(rule, "warn")


def lint_note(v: Vault, rel: str, note: Note) -> list[Finding]:
    s = v.schema
    out: list[Finding] = []

    def add(rule: str, msg: str):
        out.append(Finding(sev(s, rule), rule, rel, msg))

    fm = note.fm
    if note.fm_error:
        add("bad-frontmatter", f"cannot parse frontmatter: {note.fm_error}")
    elif fm is None:
        add("no-frontmatter", "note has no YAML frontmatter")
    if fm is not None:
        ntype = fm.get("type")
        if not ntype:
            add("missing-type", "frontmatter has no `type`")
        else:
            ntype = str(ntype)
            if ntype in s["type_aliases"]:
                add("legacy-type", f"type `{ntype}` -> use `{s['type_aliases'][ntype]}`")
                ntype = s["type_aliases"][ntype]
            elif ntype not in s["types"]:
                add("unknown-type", f"type `{ntype}` is not in the schema vocabulary")
        if not fm.get("title"):
            add("missing-title", "frontmatter has no `title`")
        owner = v.owner_of(rel)
        if owner:
            kind, folder = owner
            val = fm.get(kind)
            if not val:
                add("missing-owner", f"no `{kind}` field (expected `{slug(folder)}`)")
            elif slug(str(val)) != slug(folder):
                add("owner-mismatch", f"`{kind}: {val}` does not match folder `{folder}`")
        status = fm.get("status")
        if status is not None:
            st = str(status)
            if st in s["status_aliases"]:
                add("legacy-status", f"status `{st}` -> use `{s['status_aliases'][st]}`")
            elif st not in s["statuses"]:
                add("unknown-status", f"status `{st}` is not in the schema vocabulary")
        elif ntype in s["status_required_for"]:
            add("missing-status", f"type `{ntype}` should carry a `status`")
        for key in ("created", "updated"):
            if key in fm and not ISO_DATE_RE.match(str(fm[key])):
                add("bad-date", f"`{key}: {fm[key]}` is not YYYY-MM-DD")
    # ADR filename rules
    fname = Path(rel).name
    m = ADR_NAME_RE.match(fname)
    in_decisions = "Decisions" in rel.split("/")[:-1]
    if m:
        owner = v.owner_of(rel)
        digits = s["adr_digits"]
        if owner:
            digits = s["adr_digits_overrides"].get(slug(owner[1]), digits)
        if len(m.group(1)) != digits:
            add("adr-name", f"ADR number `{m.group(1)}` should be {digits} digits")
        if fm is not None and str(fm.get("type", "")) not in ("adr",):
            add("adr-type", "ADR note should have `type: adr`")
    elif in_decisions and not fname.startswith("00 ") and fm is not None \
            and str(fm.get("type", "")) == "adr":
        add("adr-name", "ADR file name should be `ADR NNN Title.md`")

    # leftover template placeholders (frontmatter or prose, not code samples)
    unfilled = PLACEHOLDER_RE.findall(strip_code(note.text))
    if unfilled:
        add("unfilled-placeholder", f"{len(unfilled)} unreplaced placeholder(s), e.g. {unfilled[0]}")

    # links
    body = strip_code(note.body)
    for m in WIKILINK_RE.finditer(body):
        raw = m.group(2).replace("\\|", "|")
        target = raw.split("|")[0].split("#")[0].split("^")[0]
        hits = v.resolve_wiki(target, rel)
        if not hits:
            add("broken-link", f"[[{raw}]] does not resolve")
        elif (len(hits) > 1 and "/" not in target and rel not in hits
              and not any(Path(h).parent == Path(rel).parent for h in hits)):
            # Obsidian prefers a same-folder match, so only cross-folder clashes are ambiguous
            add("ambiguous-link", f"[[{raw}]] matches {len(hits)} notes; qualify with a path")
    for m in MDLINK_RE.finditer(body):
        tgt = m.group(2).strip()
        if SCHEME_RE.match(tgt) or tgt.startswith("#") or tgt.startswith("mailto:"):
            continue
        hit = v.exists_rel(rel, tgt)
        if hit is None:
            add("broken-md-link", f"({tgt}) does not exist")
        elif hit.endswith(".md") and not m.group(1):
            add("md-link", f"markdown link to note `{hit}`; use a [[wikilink]]")

    # archive pointers (inline code is where they live, so strip fences only)
    for m in ARCHIVE_PTR_RE.finditer(strip_code(note.body, inline=False)):
        ptr = m.group(1)
        owner = v.owner_of(rel)
        roots = [v.root, (v.root / Path(rel).parent)]
        if owner:
            roots.append(v.root / (("01 Projects" if owner[0] == "project" else "02 Areas") + "/" + owner[1]))
        if not any((r / ptr).is_file() for r in roots):
            add("archive-pointer", f"archive path `{ptr}` does not exist")

    # size
    size_kb = len(note.text.encode("utf-8")) / 1024
    if size_kb > s["oversized_kb"]:
        add("oversized", f"{size_kb:.0f} KB exceeds {s['oversized_kb']} KB; split or condense")
    if fm is not None:
        nt = s["type_aliases"].get(str(fm.get("type", "")), str(fm.get("type", "")))
        st = s["status_aliases"].get(str(fm.get("status", "")), str(fm.get("status", "")))
        if nt in s["condense_types"] and st in ("done", "archived") and size_kb > s["condense_kb"]:
            add("condense-candidate", f"finished {nt} of {size_kb:.0f} KB; run /vault-task-close")
    return out


def sweep_rules(v: Vault, only: str | None) -> list[Finding]:
    s = v.schema
    out: list[Finding] = []

    def add(rule: str, path: str, msg: str):
        out.append(Finding(sev(s, rule), rule, path, msg))

    linted = [r for r in v.notes if v.lintable(r)]

    def is_index(rel: str) -> bool:
        n = v.notes[rel]
        return Path(rel).name.startswith("00 ") or str((n.fm or {}).get("type")) == "index"

    def is_index_like(rel: str) -> bool:
        """Notes that act as an index for their scope: `00 …` / type index, plus milestone notes."""
        n = v.notes[rel]
        return (is_index(rel) or Path(rel).name in s["index_like_names"]
                or str((n.fm or {}).get("type")) in s["index_like_types"])

    def outlinks(rel: str) -> set[str]:
        body = strip_code(v.notes[rel].body)
        out: set[str] = set()
        for m in WIKILINK_RE.finditer(body):
            t = m.group(2).replace("\\|", "|").split("|")[0].split("#")[0].split("^")[0]
            out.update(h for h in v.resolve_wiki(t, rel) if h in v.notes)
        for m in MDLINK_RE.finditer(body):
            tgt = m.group(2).strip()
            if not SCHEME_RE.match(tgt):
                hit = v.exists_rel(rel, tgt)
                if hit and hit.endswith(".md"):
                    out.add(hit)
        out.discard(rel)
        return out

    links_out = {rel: outlinks(rel) for rel in v.notes}
    indexed: set[str] = set()
    for rel, targets in links_out.items():
        if is_index_like(rel):
            indexed.update(targets)
    # a note under a hop dir (e.g. records/) counts when an already-indexed note links to it
    for rel in v.notes:
        if rel not in indexed and any(p in s["hop_dirs"] for p in rel.split("/")[:-1]):
            if any(rel in links_out[src] for src in indexed if src in links_out):
                indexed.add(rel)

    # project / area roots
    roots: dict[str, list[str]] = defaultdict(list)
    for rel in linted:
        o = v.owner_of(rel)
        if o:
            roots[f"{'01 Projects' if o[0] == 'project' else '02 Areas'}/{o[1]}"].append(rel)
    for top in ("01 Projects", "02 Areas"):
        for p in sorted((v.root / top).glob("*")):
            if p.is_dir():
                roots.setdefault(f"{top}/{p.name}", [])

    home = v.notes.get("00 Home.md")
    home_targets: set[str] = set()
    if home:
        for m in WIKILINK_RE.finditer(strip_code(home.body)):
            t = m.group(2).replace("\\|", "|").split("|")[0].split("#")[0]
            home_targets.update(v.resolve_wiki(t, "00 Home.md"))

    for root, members in sorted(roots.items()):
        name = root.split("/")[1]
        if only and only.lower() not in name.lower():
            continue
        has_index = any(
            Path(r).parent.as_posix() == root and is_index(r) for r in v.notes
        )
        if not has_index:
            add("missing-index", root, f"no `00 {name} Index.md` at the {root.split('/')[0][3:-1].lower()} root")
        if home and not any(t.startswith(root + "/") for t in home_targets):
            add("not-in-home", "00 Home.md", f"`{name}` is not linked from 00 Home.md")
        # collection indexes
        by_dir: dict[str, list[str]] = defaultdict(list)
        for r in members:
            by_dir[Path(r).parent.as_posix()].append(r)
        for d, rs in sorted(by_dir.items()):
            if d == root or v.is_frozen(rs[0]):
                continue
            if len(rs) >= 3 and not any(is_index(r) for r in rs):
                add("missing-collection-index", d, f"{len(rs)} notes and no `00 … Index.md`")
        # ADR numbering
        nums: dict[int, list[str]] = defaultdict(list)
        for r in members:
            m = ADR_NAME_RE.match(Path(r).name)
            if m:
                nums[int(m.group(1))].append(r)
        for n, rs in sorted(nums.items()):
            if len(rs) > 1:
                add("adr-duplicate", rs[0], f"ADR {n} used by {len(rs)} notes: {', '.join(Path(x).name for x in rs)}")
        if nums:
            missing = [n for n in range(min(nums), max(nums) + 1) if n not in nums]
            if missing:
                add("adr-gap", root, f"ADR numbers missing: {missing}")

    for rel in linted:
        if only and only.lower() not in rel.lower():
            continue
        if is_index(rel) or rel == "00 Home.md":
            continue
        if v.owner_of(rel) and rel not in indexed:
            add("not-in-index", rel, "not linked from an index (00 … Index or milestone) note")

    dup = {b: rs for b, rs in v.by_base.items() if len([r for r in rs if v.lintable(r)]) > 1}
    for b, rs in sorted(dup.items()):
        if only and not any(only.lower() in r.lower() for r in rs):
            continue
        add("duplicate-name", rs[0], f"basename `{b}` used by {len(rs)} notes; qualify links with a path")
    return out


def run_sweep(v: Vault, only: str | None) -> list[Finding]:
    findings: list[Finding] = []
    for rel, note in v.notes.items():
        if not v.lintable(rel):
            continue
        if only and only.lower() not in rel.lower():
            continue
        findings += lint_note(v, rel, note)
    findings += sweep_rules(v, only)
    return findings


def render(findings: list[Finding], min_sev: str, as_json: bool) -> str:
    cut = SEV_ORDER[min_sev]
    shown = [f for f in findings if SEV_ORDER[f.sev] <= cut]
    shown.sort(key=lambda f: (SEV_ORDER[f.sev], f.rule, f.path))
    if as_json:
        return json.dumps([asdict(f) for f in shown], indent=2)
    if not shown:
        return "clean: no findings"
    lines = []
    counts = Counter((f.sev, f.rule) for f in shown)
    totals = Counter(f.sev for f in shown)
    lines.append(f"{totals['error']} error, {totals['warn']} warn, {totals['info']} info\n")
    lines.append("rule                       sev    count")
    for (sv, rule), c in sorted(counts.items(), key=lambda kv: (SEV_ORDER[kv[0][0]], kv[0][1])):
        lines.append(f"{rule:<26} {sv:<6} {c}")
    lines.append("")
    for f in shown:
        lines.append(f"[{f.sev}] {f.rule}: {f.path}: {f.msg}")
    return "\n".join(lines)


def cmd_stats(v: Vault, only: str | None) -> str:
    s = v.schema
    types, statuses, projects = Counter(), Counter(), Counter()
    nofm = frozen = excluded = 0
    cands = []
    for rel, n in v.notes.items():
        if v.is_excluded(rel):
            excluded += 1
            continue
        if v.is_frozen(rel):
            frozen += 1
            continue
        if only and only.lower() not in rel.lower():
            continue
        o = v.owner_of(rel)
        projects[o[1] if o else "(vault)"] += 1
        if n.fm is None:
            nofm += 1
            continue
        t = s["type_aliases"].get(str(n.fm.get("type", "-")), str(n.fm.get("type", "-")))
        types[t] += 1
        st = s["status_aliases"].get(str(n.fm.get("status", "-")), str(n.fm.get("status", "-")))
        statuses[st] += 1
        kb = len(n.text.encode()) / 1024
        if t in s["condense_types"] and st in ("done", "archived") and kb > s["condense_kb"]:
            cands.append((kb, rel))
    out = [f"notes: {len(v.notes)} total, {frozen} archived/frozen, {excluded} excluded",
           f"without frontmatter: {nofm}", "", "by project/area:"]
    out += [f"  {k}: {c}" for k, c in projects.most_common()]
    out += ["", "by type:"] + [f"  {k}: {c}" for k, c in types.most_common()]
    out += ["", "by status:"] + [f"  {k}: {c}" for k, c in statuses.most_common()]
    out += ["", "condense candidates (finished, over size):"]
    out += [f"  {kb:.0f} KB  {rel}" for kb, rel in sorted(cands, reverse=True)] or ["  none"]
    return "\n".join(out)


def cmd_next_adr(v: Vault, project: str) -> str:
    folder = next((p for p in v.notes if v.owner_of(p) and project.lower() in v.owner_of(p)[1].lower()), None)
    if not folder:
        sys.exit(f"no project matching {project!r}")
    kind, name = v.owner_of(folder)
    top = "01 Projects" if kind == "project" else "02 Areas"
    nums = [int(m.group(1)) for r in v.notes
            if r.startswith(f"{top}/{name}/") and (m := ADR_NAME_RE.match(Path(r).name))]
    digits = v.schema["adr_digits_overrides"].get(slug(name), v.schema["adr_digits"])
    return str((max(nums) if nums else 0) + 1).zfill(digits)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", nargs="?", default="sweep", choices=["sweep", "check", "stats", "next-adr"])
    ap.add_argument("target", nargs="?", help="check: file to read (default stdin); next-adr: project name")
    ap.add_argument("--vault", default=DEFAULT_VAULT)
    ap.add_argument("--path", help="check: vault-relative path the note will be written to")
    ap.add_argument("--project", help="limit to paths containing this text")
    ap.add_argument("--min-severity", choices=["error", "warn", "info"], default="info")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    root = Path(a.vault).expanduser()
    if not root.is_dir():
        sys.exit(f"vault not found: {root}")
    v = Vault(root, load_schema(root))

    if a.mode == "stats":
        print(cmd_stats(v, a.project))
        return 0
    if a.mode == "next-adr":
        print(cmd_next_adr(v, a.target or a.project or ""))
        return 0
    if a.mode == "check":
        if not a.path:
            sys.exit("check requires --path <vault-relative path of the note>")
        text = Path(a.target).read_text(encoding="utf-8") if a.target else sys.stdin.read()
        v.add_note(a.path, text)
        v._index()
        findings = lint_note(v, a.path, v.notes[a.path])
        findings += [f for f in sweep_rules(v, None) if f.path == a.path and f.rule in ("adr-duplicate",)]
    else:
        findings = run_sweep(v, a.project)
    print(render(findings, a.min_severity, a.json))
    return 1 if any(f.sev == "error" for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
