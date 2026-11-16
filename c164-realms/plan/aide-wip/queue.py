#!/usr/bin/env python3
"""Approvers' queues, from git only (run after a fetch).

A package "waits" when a person's branch (not -wip, not the assembly) has commits of today's second round that the
assembly does not have, and the newest of them that is the person's own (not a node's) is older than --quiet minutes
(default 10: a branch still being pushed to every couple of minutes is work in progress, not a queue).
The approver is the one of the category the changed files fall in.

usage: queue.py [--quiet N] [-v]
"""
import re, subprocess, sys, time

REPO = "/agent/repos/c164-aide-f3-b9ab"
ASM = "origin/cursor/c164-assembly-fable-a9f5"
APPROVER = {"common": "s2", "materials": "a1", "main": "facade", "sky": "cr2", "motion": "cr2", "site": "a4",
            "machines": "cr3", "props": "a6", "interiors": "cr3"}
SINCE = "2026-11-16T12:12:00+08:00"   # round two


def git(*a):
    return subprocess.run(("git", "-C", REPO) + a, capture_output=True, text=True, errors="replace").stdout.strip()


def category(files):
    n = {}
    for f in files:
        m = re.search(r"scenes/obs/(main|sky|motion|site|machines|props|interiors|materials)/", f) or \
            re.search(r"plan/packages/(common|main|sky|motion|site|machines|props|interiors|materials)/", f) or \
            re.search(r"scenes/obs_(mat|mach|int|site|sky|prop|main|motion)_", f)
        if m:
            c = {"mat": "materials", "mach": "machines", "int": "interiors", "prop": "props"}.get(m.group(1), m.group(1))
            n[c] = n.get(c, 0) + (3 if "scenes/obs/" in f else 1)
        elif "/tools/" in f or "artkit/" in f or "scenes/obs/__" in f or "scenes/obs/scene.py" in f:
            n["common"] = n.get("common", 0) + 1
    return max(n, key=n.get) if n else "?"


def main():
    quiet = 10
    if "--quiet" in sys.argv:
        quiet = int(sys.argv[sys.argv.index("--quiet") + 1])
    verbose = "-v" in sys.argv
    now = time.time()
    refs = [r for r in git("for-each-ref", "--format=%(refname:short)", "refs/remotes/origin/cursor/c164-*").split("\n")
            if r and not r.endswith("-wip") and "assembly" not in r and "-wip-" not in r
            and not re.search(r"c164-(s2|aide|s1|dist)-", r)
            # reviewers' note branches and scratch branches are not deliveries
            and not re.search(r"c164-(review|cr2|cr3)-f3-[0-9a-f]{4}$", r)
            and not re.search(r"trial|probe|scratch|gltest|-look-", r)]
    rows = []
    for r in refs:
        # --cherry-pick: a commit whose patch the assembly already has (picked or squashed) does not wait
        out = git("log", "--since=" + SINCE, "--cherry-pick", "--right-only", "--no-merges",
                  "--format=%H\t%ct\t%s", ASM + "..." + r)
        mine = [l.split("\t", 2) for l in out.split("\n") if l and not l.split("\t", 2)[2].startswith("c164-node:")
                and not l.split("\t", 2)[2].startswith("Merge")]
        mine = [m for m in mine if not re.match(r"c164-[a-z0-9]+: merge (the )?(assembly|head)", m[2])]
        if not mine:
            continue
        h, ct, s = mine[0]
        age = (now - int(ct)) / 60.0
        code = re.match(r"origin/cursor/c164-([a-z0-9]+)-", r).group(1)
        base = git("merge-base", ASM, r)
        files = git("diff", "--name-only", base, r).split("\n")
        files = [f for f in files if f and "/renders/" not in f]
        if not files:
            continue
        cat = category(files)
        if re.match(r"(trial|TRIAL)", s) or "TRIAL" in s:
            continue
        rows.append((APPROVER.get(cat, "?"), age, code, r.replace("origin/", ""), len(mine), cat, s))
    by = {}
    for ap, age, code, r, n, cat, s in rows:
        if age < quiet:
            continue
        by.setdefault(ap, []).append((age, code, r, n, cat, s))
    for ap in sorted(by, key=lambda a: -len(by[a])):
        q = sorted(by[ap], reverse=True)
        print("%s: %d 个，最老 %d 分（%s）" % (ap, len(q), q[0][0], "、".join("%s %d" % (c, a) for a, c, *_ in q[:8])))
        if verbose:
            for age, code, r, n, cat, s in q:
                print("    %4d 分 %-8s %-10s %-52s %s" % (age, code, cat, r[:52], s[:70]))
    fresh = [(age, code) for ap, age, code, *_ in rows if age < quiet]
    print("刚推的（%d 分以内，不算排队）: %s" % (quiet, "、".join(sorted({c for _, c in fresh})) or "没有"))


if __name__ == "__main__":
    main()
