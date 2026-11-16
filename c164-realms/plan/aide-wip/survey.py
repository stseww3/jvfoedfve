#!/usr/bin/env python3
"""The aide's survey of the third shift, from git alone (no renders, no checks).

    survey.py            look only: compare with the last kept snapshot
    survey.py --keep     the hourly run: compare, then keep a new snapshot

Per person (the code in the branch name, cursor/c164-<code>-...-f3...): the branches, whether any of
them was pushed to since the last kept snapshot, the person's own commits (subject starts with
c164-<code>: or c164-node:) since then and in all of the third shift, the newest one, the newest
head (the latest push that can be told from git), and what tools/provenance.sh says of every head.
Then the people who are due a question (no head of theirs is newer than an hour), the people
without a branch, and what the assembly gained.  survey.py --asked=a,b notes who was asked.
Nothing is written to the repository; the state lives in /tmp/c164_aide/.
"""
import json
import os
import re
import subprocess
import sys
import time

TREE = "/agent/repos/c164-aide-f3-b9ab"
STATE = "/tmp/c164_aide"
ROSTER = TREE + "/c164-realms/plan/ROSTER.md"
ASM = "cursor/c164-assembly-fable-a9f5"
SHIFT3 = 1794765540  # 2026-11-15T17:59:00Z, the first minute of the third shift
SNAP = STATE + "/snap/latest.json"
# branches that are looked at and never merged: the node's -wip, and trials and studies their owners cut
SCRATCH = re.compile(r"-(wip|trial|study|try|scratch)(-|$)")
SCRATCH_LIST = STATE + "/scratch.txt"  # more scratch branches, by name (roster_sync.py --scratch writes it)
SEEN = STATE + "/first_seen.json"
ASKED = STATE + "/asked.json"  # whom the aide has asked "where are you stuck", and when


def git(*args):
    return subprocess.run(["git", "-C", TREE, *args], capture_output=True, text=True)


def hhmm(ts):
    return time.strftime("%H:%M", time.gmtime(ts + 8 * 3600))


def load(path, default):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def roster_rows():
    rows = {}
    with open(ROSTER, encoding="utf-8") as fh:
        for line in fh:
            if not line.startswith("| "):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) == 7 and cells[0] not in ("代号", "---"):
                rows[cells[0]] = cells
    return rows


def main():
    keep = "--keep" in sys.argv[1:]
    nsubj, width = 2, 140
    asked = load(ASKED, {})
    for a in sys.argv[1:]:
        if a.startswith("--asked="):
            # survey.py --asked=hall,a2 : note that these were asked just now, and stop
            for c in a.split("=", 1)[1].split(","):
                asked[c] = int(time.time())
            os.makedirs(STATE, exist_ok=True)
            with open(ASKED, "w", encoding="utf-8") as fh:
                json.dump(asked, fh, indent=0, sort_keys=True)
            print("asked: " + ", ".join("%s %s" % (c, hhmm(t)) for c, t in sorted(asked.items(), key=lambda kv: kv[1])))
            return
    for a in sys.argv[1:]:
        if a.startswith("--subjects="):
            nsubj = int(a.split("=", 1)[1])
        if a.startswith("--width="):
            width = int(a.split("=", 1)[1])
    now = int(time.time())
    os.makedirs(STATE + "/snap", exist_ok=True)

    rows = roster_rows()
    named = set()
    for cells in rows.values():
        named.update(re.findall(r"`(cursor/[^`]+)`", cells[6]))

    # Third-shift branches: named with -f3, or named in the roster's "new branch" cell (s2's is not).
    out = git("ls-remote", "--heads", "origin", "refs/heads/cursor/c164-*").stdout
    heads = {}
    for line in out.splitlines():
        sha, ref = line.split()[:2]
        name = ref[len("refs/heads/"):]
        if name == ASM or re.search(r"-f[34](-|$)", name) or name in named:
            heads[name] = sha
    if ASM not in heads:
        sys.exit("survey: cannot list the remote branches")
    specs = ["+refs/heads/%s:refs/remotes/origin/%s" % (b, b) for b in heads]
    # the clone is shared with everybody on this machine: a fetch can lose a ref lock to somebody else's
    for attempt in range(4):
        res = git("fetch", "-q", "origin", *specs)
        if res.returncode == 0:
            break
        time.sleep(2 + 3 * attempt)
    else:
        # never print a remote's address: it holds a credential
        sys.exit("survey: fetch failed: " + re.sub(r"\S+://\S+", "<address>", res.stderr.strip())[-300:])

    snap = load(SNAP, {})
    was, snap_time = snap.get("heads", {}), snap.get("time")
    seen = load(SEEN, {})
    asm = heads[ASM]
    branches = sorted(b for b in heads if b != ASM)

    # What came to a branch by merging the assembly is not its owner's: the third shift's commits the
    # assembly holds, and each branch's own first-parent line.
    in_asm = set(git("log", "--since=%d" % SHIFT3, "--format=%H", asm).stdout.split())
    first_parent = {}
    for b in branches:
        code = re.match(r"cursor/c164-([^-]+)-", b).group(1)
        fp = [line.split() for line in git("log", "--first-parent", "--since=%d" % SHIFT3, "--format=%H %ct", heads[b]).stdout.splitlines()]
        first_parent[b] = set(sha for sha, _ in fp)
        if b not in seen:
            # A branch cut from a first-shift head starts with its owner's merge of the assembly; a
            # later branch of somebody who is online already (a second card, a -wip, a trial) says
            # nothing about when the person came.
            cut_from_old = "@ `" in rows.get(code, [""] * 7)[5]
            times = [int(ct) for _, ct in fp if int(ct) >= SHIFT3]
            earlier = [t for x, t in seen.items() if x.startswith("cursor/c164-%s-" % code)]
            seen[b] = min(earlier) if earlier else (min([now] + times) if cut_from_old else now)
    seen.setdefault(ASM, now)
    with open(SEEN, "w", encoding="utf-8") as fh:
        json.dump(seen, fh, indent=0, sort_keys=True)

    # provenance of every head, one call
    prov = {}
    res = subprocess.run(["bash", TREE + "/c164-realms/tools/provenance.sh", *[heads[b] for b in branches]],
                         capture_output=True, text=True)
    for line in res.stdout.splitlines():
        m = re.match(r"(clean|NOT CLEAN)\s+([0-9a-f]{8})", line)
        if m:
            prov[m.group(2)] = m.group(1)

    # When a head was made is the earliest its push can have been: the newest head of a person's
    # branches says how long the person has been quiet (a merge of the assembly counts as a push).
    head_time = {}
    for line in git("show", "-s", "--format=%H %ct", *sorted(set(heads[b] for b in branches))).stdout.splitlines():
        sha, ct = line.split()
        head_time[sha] = int(ct)

    try:
        with open(SCRATCH_LIST, encoding="utf-8") as fh:
            listed = set(x.strip() for x in fh if x.strip())
    except OSError:
        listed = set()

    people = {}
    for b in branches:
        code = re.match(r"cursor/c164-([^-]+)-", b).group(1)
        scratch = bool(SCRATCH.search(b)) or any(b == x or b.startswith(x + "-") for x in listed)

        def is_own(sha, subj, code=code, b=b):
            if subj.startswith("c164-%s:" % code):
                return True
            # A node's commit is its sender's when the node put it on this branch, not when it came in with the assembly.
            return subj.startswith("c164-node:") and code != "aide" and (sha in first_parent[b] or sha not in in_asm)

        log = git("log", "--no-merges", "--since=%d" % SHIFT3, "--format=%ct\t%H\t%s", heads[b]).stdout
        own = []
        for line in log.splitlines():
            ct, sha, subj = line.split("\t", 2)
            if int(ct) >= SHIFT3 and is_own(sha, subj):
                own.append((int(ct), sha[:8], subj))
        p = people.setdefault(code, {"branches": [], "own": {}, "moved": False, "first": now, "bad": [], "merged": True,
                                     "pics": set(), "wip_pics": set(), "pushed": 0})
        p["branches"].append((b, scratch))
        p["pushed"] = max(p["pushed"], head_time.get(heads[b], 0))
        # pictures under renders/ that the person's own commits (or the node's) put on this branch
        plog = git("log", "--no-merges", "--since=%d" % SHIFT3, "--format=\x01%H\t%s", "--name-only", heads[b],
                   "--", "c164-realms/renders").stdout
        mine = False
        for line in plog.splitlines():
            if line.startswith("\x01"):
                sha, subj = line[1:].split("\t", 1)
                mine = is_own(sha, subj)
            elif mine and line.lower().endswith((".png", ".jpg", ".jpeg")):
                p["wip_pics" if scratch else "pics"].add(line)
        if was.get(b) != heads[b]:
            p["moved"] = True
        p["first"] = min(p["first"], seen[b])
        for ct, sha, subj in own:
            p["own"].setdefault(sha, (ct, subj, scratch))
        if prov.get(heads[b][:8]) != "clean":
            p["bad"].append(b)
        if not scratch and git("merge-base", "--is-ancestor", heads[b], asm).returncode != 0:
            p["merged"] = False

    since = snap_time or SHIFT3
    print("== %s CST; %d people with a branch, %d branches with -f3; last kept snapshot %s" % (
        hhmm(now), len(people), len(branches),
        "%s (%d min ago)" % (hhmm(snap_time), (now - snap_time) // 60) if snap_time else "none (counting from the start of the shift)"))
    due, bad_all = [], []
    for code in sorted(people, key=lambda c: (rows.get(c, ["", "c999"])[1], c)):
        p = people[code]
        chat = rows.get(code, ["", "?"])[1]
        own = sorted(p["own"].items(), key=lambda kv: -kv[1][0])
        kept = [(sha, v) for sha, v in own if not v[2]]
        new_kept = [x for x in kept if x[1][0] >= since]
        new_scratch = [x for x in own if x[1][2] and x[1][0] >= since]
        last = "last %s" % hhmm(own[0][1][0]) if own else "no own commit"
        work = [b for b, s in p["branches"] if not s]
        flags = []
        quiet = (now - max(p["pushed"], p["first"])) // 60
        if not p["moved"]:
            flags.append("NO PUSH since the snapshot")
        # a merge of the assembly is a push and is not work: the newest commit of the person's own counts too
        idle = (now - max(own[0][1][0] if own else 0, p["first"])) // 60
        if quiet >= 60 and code != "aide":
            flags.append("QUIET %d min" % quiet)
            due.append((code, chat, quiet, asked.get(code)))
        elif idle >= 60 and code != "aide":
            flags.append("NO COMMIT OF ITS OWN for %d min" % idle)
            due.append((code, chat, idle, asked.get(code)))
        if p["bad"]:
            flags.append("NOT CLEAN: " + ", ".join(p["bad"]))
            bad_all.append((code, chat, p["bad"]))
        if kept and p["merged"]:
            flags.append("all in the assembly")
        print("%-7s %-5s %d br%s | own +%d (+%d scratch) of %d | pics %d kept, %d scratch | %s | pushed %s | online %s%s" % (
            code, chat, len(work), "+wip" if len(work) != len(p["branches"]) else "",
            len(new_kept), len(new_scratch), len(kept), len(p["pics"]), len(p["wip_pics"]), last,
            hhmm(p["pushed"]) if p["pushed"] else "never", hhmm(p["first"]),
            " | " + "; ".join(flags) if flags else ""))
        for sha, (ct, subj, _) in new_kept[:nsubj]:
            print("          %s %s" % (sha, subj[:width]))

    no_branch = [(c, r[1]) for c, r in rows.items() if r[1] != "—" and c not in people]
    not_open = [c for c, r in rows.items() if r[1] == "—"]
    print("== online without any -f3 branch: %s" % (", ".join("%s(%s)" % x for x in no_branch) or "none"))
    print("== not opened yet (%d): %s" % (len(not_open), ", ".join(not_open) or "none"))
    print("== due a question (no push, or no commit of its own, for an hour): %s" % (
        ", ".join("%s(%s, quiet %d min%s)" % (c, ch, q, ", asked %s" % hhmm(t) if t else "") for c, ch, q, t in due) or "none"))
    print("== NOT CLEAN: %s" % (", ".join("%s(%s): %s" % (c, ch, " ".join(b)) for c, ch, b in bad_all) or "none"))

    asm_was = was.get(ASM)
    print("== assembly %s%s" % (asm[:8], " (was %s)" % asm_was[:8] if asm_was and asm_was != asm else ""))
    # What the assembly gained: the merge keeper's and the director's commits in the range (the roster's
    # commits are the aide's own; merges of the assembly into a branch say nothing).
    rng = "%s..%s" % (asm_was, asm) if asm_was else asm
    log = git("log", "--since=%d" % since, "--format=%h %s", "--abbrev=8", rng).stdout.splitlines()
    mine = [x for x in log if x.split(" ", 1)[1].startswith("c164-aide:")]
    shown = [x for x in log if re.match(r"c164-(s2|a0):", x.split(" ", 1)[1])
             and not re.match(r"c164-s2: (merge|take in) the assembly", x.split(" ", 1)[1])]
    for x in shown[:30]:
        print("          " + x[:width + 30])
    if len(shown) > 30:
        print("          (+%d more)" % (len(shown) - 30))
    print("          (+%d roster commits of the aide)" % len(mine))

    if keep:
        data = {"time": now, "heads": heads}
        with open(STATE + "/snap/%d.json" % now, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=0, sort_keys=True)
        with open(SNAP, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=0, sort_keys=True)
        print("== snapshot kept: %s/snap/%d.json" % (STATE, now))
    sys.exit(1 if bad_all else 0)


if __name__ == "__main__":
    main()
