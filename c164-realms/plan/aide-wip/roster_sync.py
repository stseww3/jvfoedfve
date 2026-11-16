#!/usr/bin/env python3
"""Hold plan/ROSTER.md against the remote's third-shift branches (the aide's helper, git only).

    roster_sync.py                    report only
    roster_sync.py --fix NAME...      write these branches into their owner's "new branch" cell, when
                                      the branch holds one of the first-shift heads the row names
    roster_sync.py --scratch NAME...  note these branches as scratch (looked at, never merged): they
                                      leave the roster and are left out from now on
    roster_sync.py --drop NAME...     take these names out of the roster's cells

Reports: branches on the remote the roster does not name (with the head's subject, to tell a card's
branch from a scratch one); branches the roster names that the remote does not have; branches that
hold none of their row's first-shift heads (cut from the wrong place); people with a chat number and
no branch. Scratch branches are left out: -wip, -trial, -study, -try, -scratch in the name, or a name
in /tmp/c164_aide/scratch.txt.
"""
import os
import re
import subprocess
import sys

TREE = "/agent/repos/c164-aide-f3-b9ab"
ROSTER = TREE + "/c164-realms/plan/ROSTER.md"
SCRATCH_LIST = "/tmp/c164_aide/scratch.txt"
SCRATCH = re.compile(r"-(wip|trial|study|try|scratch)(-|$)")


def git(*args):
    return subprocess.run(["git", "-C", TREE, *args], capture_output=True, text=True)


def scratch_names():
    try:
        with open(SCRATCH_LIST, encoding="utf-8") as fh:
            return set(x.strip() for x in fh if x.strip())
    except OSError:
        return set()


def is_scratch(name, listed):
    if SCRATCH.search(name):
        return True
    # the node's -wip of a listed scratch branch is scratch too
    return any(name == s or name.startswith(s + "-") for s in listed)


def names_after(flag):
    args = sys.argv[1:]
    if flag not in args:
        return None
    out = []
    for a in args[args.index(flag) + 1:]:
        if a.startswith("--"):
            break
        out.append(a)
    return out


def main():
    fix = names_after("--fix")
    drop = names_after("--drop") or []
    new_scratch = names_after("--scratch") or []
    listed = scratch_names()
    if new_scratch:
        listed.update(new_scratch)
        os.makedirs(os.path.dirname(SCRATCH_LIST), exist_ok=True)
        with open(SCRATCH_LIST, "w", encoding="utf-8") as fh:
            fh.write("\n".join(sorted(listed)) + "\n")
        drop = drop + new_scratch

    with open(ROSTER, encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    rows = {}
    for i, line in enumerate(lines):
        if not line.startswith("| "):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 7 or cells[0] in ("代号", "---"):
            continue
        rows[cells[0]] = {
            "i": i,
            "cells": cells,
            "chat": cells[1],
            "heads": re.findall(r"@ `([0-9a-f]{7,40})`", cells[5]),
            "new": re.findall(r"`(cursor/[^`]+)`", cells[6]),
        }

    notes, changed = [], False

    def write_cell(row):
        row["cells"][6] = "、".join("`%s`" % n for n in row["new"]) or "—"
        lines[row["i"]] = "| " + " | ".join(row["cells"]) + " |"

    for name in drop:
        for code, row in rows.items():
            if name in row["new"]:
                row["new"].remove(name)
                write_cell(row)
                changed = True
                notes.append("dropped    %s from %s" % (name, code))

    out = git("ls-remote", "--heads", "origin", "refs/heads/cursor/c164-*").stdout
    remote = {}
    for line in out.splitlines():
        sha, ref = line.split()[:2]
        name = ref[len("refs/heads/"):]
        named = any(name in row["new"] for row in rows.values())
        if (re.search(r"-f3(-|$)", name) or named) and not is_scratch(name, listed):
            remote[name] = sha
    if not remote:
        sys.exit("roster_sync: cannot list the remote branches")

    for name, sha in sorted(remote.items()):
        code = re.match(r"cursor/c164-([^-]+)-", name).group(1)
        row = rows.get(code)
        if row is None:
            notes.append("NO ROW     %s: no code %r in the roster" % (name, code))
            continue
        if git("cat-file", "-e", sha + "^{commit}").returncode != 0:
            git("fetch", "-q", "origin", "+refs/heads/%s:refs/remotes/origin/%s" % (name, name))
        held = [h for h in row["heads"] if git("merge-base", "--is-ancestor", h, sha).returncode == 0]
        if row["heads"] and not held:
            notes.append("BASE?      %s holds none of the heads of %s (%s)" % (name, code, ", ".join(row["heads"])))
        if name not in row["new"]:
            if fix is not None and name in fix and (held or not row["heads"]):
                row["new"].append(name)
                write_cell(row)
                changed = True
                notes.append("added      %s to %s (holds %s)" % (name, code, ", ".join(held) or "the assembly"))
            else:
                subj = git("log", "-1", "--format=%s", sha).stdout.strip()
                notes.append("NOT NAMED  %s is on the remote, not in the row of %s; head: %s" % (name, code, subj[:110]))
    for name in fix or []:
        if name not in remote:
            notes.append("NOT THERE  %s was to be added and is not on the remote (or is scratch)" % name)
    for code, row in rows.items():
        for name in row["new"]:
            if name not in remote:
                notes.append("GONE       %s (row %s) is not on the remote" % (name, code))
        if row["chat"] != "—" and not row["new"]:
            notes.append("no branch  %s (%s) is online and has pushed no -f3 branch" % (code, row["chat"]))
    if changed:
        with open(ROSTER, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
    online = sum(1 for r in rows.values() if r["chat"] != "—")
    print("roster: %d rows, %d with a chat; remote: %d branches with -f3 (scratch ones left out)" % (len(rows), online, len(remote)))
    for n in notes:
        print("  " + n)


if __name__ == "__main__":
    main()
