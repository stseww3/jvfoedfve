#!/usr/bin/env python3
"""The reviewers' queues, told from git alone (the aide's helper).

    queue.py        fetch the assembly and the three reviewers' branches, print per reviewer the
                    packages whose newest merge into the assembly is newer than the newest review
                    commit that names them

A package waits when the merge keeper has merged a delivery of it (subject "c164-s2: merge
<category>/<package> ...") after the last commit of its reviewer that names it. Merges of pictures or
of a card only are listed apart: they seldom need a new review. This is a count to start a question
with, not a ruling: before telling the director that a queue is longer than three (his word of
11-16 05:25), ask the reviewer.
review c332: materials, main, props; cr2 c333: site, sky, motion; cr3 c347: machines, interiors.
"""
import re
import subprocess
import time

TREE = "/agent/repos/c164-aide-f3-b9ab"
ASM = "cursor/c164-assembly-fable-a9f5"
SHIFT3 = 1794765540
REVIEWER = {"materials": "review", "main": "review", "props": "review",
            "site": "cr2", "sky": "cr2", "motion": "cr2",
            "machines": "cr3", "interiors": "cr3"}
PKG = re.compile(r"\b(materials|main|props|site|sky|motion|machines|interiors)/([a-z0-9-]+)")


def git(*args):
    return subprocess.run(["git", "-C", TREE, *args], capture_output=True, text=True)


def hhmm(ts):
    return time.strftime("%H:%M", time.gmtime(ts + 8 * 3600))


def main():
    refs = [ASM]
    out = git("ls-remote", "--heads", "origin", "refs/heads/cursor/c164-review-f3-*", "refs/heads/cursor/c164-cr2-f3-*",
              "refs/heads/cursor/c164-cr3-f3-*").stdout
    for line in out.splitlines():
        name = line.split()[1][len("refs/heads/"):]
        if not re.search(r"-wip(-|$)", name):
            refs.append(name)
    for attempt in range(4):
        if git("fetch", "-q", "origin", *["+refs/heads/%s:refs/remotes/origin/%s" % (r, r) for r in refs]).returncode == 0:
            break
        time.sleep(2 + 3 * attempt)

    merged, light = {}, {}
    log = git("log", "--since=%d" % SHIFT3, "--format=%ct\t%h\t%s", "origin/" + ASM).stdout
    for line in log.splitlines():
        ct, sha, subj = line.split("\t", 2)
        if not subj.startswith("c164-s2: merge "):
            continue
        head = subj.split("(", 1)[0]
        minor = bool(re.search(r"picture|card", head)) or "the card only" in subj
        for cat, name in PKG.findall(head):
            d = light if minor else merged
            key = "%s/%s" % (cat, name)
            if int(ct) > d.get(key, (0, ""))[0]:
                d[key] = (int(ct), sha)

    reviewed = {}
    for r in refs[1:]:
        code = re.match(r"cursor/c164-([^-]+)-", r).group(1)
        log = git("log", "--since=%d" % SHIFT3, "--format=%ct\t%s", "origin/" + r).stdout
        for line in log.splitlines():
            ct, subj = line.split("\t", 1)
            if not subj.startswith("c164-%s:" % code) or not re.search(r"review|re-look", subj):
                continue
            for cat, name in PKG.findall(subj):
                key = "%s/%s" % (cat, name)
                reviewed[key] = max(reviewed.get(key, 0), int(ct))

    now = int(time.time())
    for r in ("review", "cr2", "cr3"):
        wait = sorted((t, key, sha) for key, (t, sha) in merged.items()
                      if REVIEWER[key.split("/")[0]] == r and t > reviewed.get(key, 0))
        minor = sorted((t, key, sha) for key, (t, sha) in light.items()
                       if REVIEWER[key.split("/")[0]] == r and t > max(reviewed.get(key, 0), merged.get(key, (0, ""))[0]))
        print("%-6s %d waiting%s" % (r, len(wait), "  <-- more than three" if len(wait) > 3 else ""))
        for t, key, sha in wait:
            last = reviewed.get(key)
            print("         %-34s merged %s (%s, %d min ago)%s" % (
                key, hhmm(t), sha, (now - t) // 60, "; last reviewed %s" % hhmm(last) if last else "; never reviewed this shift"))
        for t, key, sha in minor:
            print("         %-34s pictures or card only, merged %s (%s)" % (key, hhmm(t), sha))


if __name__ == "__main__":
    main()
