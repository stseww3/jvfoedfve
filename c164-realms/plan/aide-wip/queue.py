#!/usr/bin/env python3
"""The reviewers' queues, told from git alone (the aide's helper).

    queue.py        fetch the assembly and the reviewers' branches, print per reviewer the packages
                    whose newest merge into the assembly is newer than the newest review of them

A package waits when the merge keeper has merged a delivery of it (subject "c164-s2: merge
<category>/<package> ...") after its last review. A review is a heading "## 评审 ...：<category>/<package>"
in a reviewer's record file (plan/aesthetics/S3-reviews-v4*.md on the reviewer's branch); its time is
the time of the commit that wrote the heading. (Commit subjects are no good for this: "#21" names no
package, and the count of 11-16 07:13 was wrong by two for that reason.) Merges of pictures or of a
card only are listed apart: they seldom need a new review. This is a count to start a question with,
not a ruling: before telling the director that a queue is longer than three (his word of 11-16
05:25), ask the reviewer.

review c332: materials, main, props; cr2 c333: site, sky, motion; cr3 c347: machines, interiors;
cr4 c337 (stair, since 11-16 07:30): what OVERRIDE gives it.
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
# the director's reshuffle of 11-16 07:30 and what followed
OVERRIDE = {"sky/tones": "cr3", "site/stair": "cr3",
            "props/instruments": "cr4", "props/furniture": "cr4"}
RECORDS = {"review": ("cursor/c164-review-f3-3c69", "S3-reviews-v4.md"),
           "cr2": ("cursor/c164-cr2-f3-ccff", "S3-reviews-v4-cr2.md"),
           "cr3": ("cursor/c164-cr3-f3-998d", "S3-reviews-v4-cr3.md"),
           "cr4": ("cursor/c164-stair-cr4-f3-b330", "S3-reviews-v4-cr4.md")}
PKG = re.compile(r"\b(materials|main|props|site|sky|motion|machines|interiors)/([a-z0-9-]+)")
HEADING = re.compile(r"^##\s*评审[^：:]*[：:]\s*(.*)$")


def git(*args):
    return subprocess.run(["git", "-C", TREE, *args], capture_output=True, text=True)


def hhmm(ts):
    return time.strftime("%H:%M", time.gmtime(ts + 8 * 3600))


def reviewer_of(key):
    return OVERRIDE.get(key, REVIEWER[key.split("/")[0]])


def reviews():
    """{package: (time, who, heading)} of the newest review heading that names the package."""
    out = {}
    for who, (branch, name) in RECORDS.items():
        path = "c164-realms/plan/aesthetics/" + name
        blame = git("blame", "--line-porcelain", "origin/" + branch, "--", path)
        if blame.returncode != 0:
            continue
        ct = 0
        for line in blame.stdout.splitlines():
            if line.startswith("committer-time "):
                ct = int(line.split()[1])
            elif line.startswith("\t"):
                m = HEADING.match(line[1:])
                if not m or ct < SHIFT3:
                    continue
                # the package is the first one named in the heading
                found = PKG.search(m.group(1))
                if found:
                    key = "%s/%s" % found.groups()
                    if ct > out.get(key, (0, "", ""))[0]:
                        out[key] = (ct, who, line[1:].strip()[:60])
    return out


def main():
    refs = [ASM] + [b for b, _ in RECORDS.values()]
    for attempt in range(4):
        ok = True
        for r in refs:
            if git("fetch", "-q", "origin", "+refs/heads/%s:refs/remotes/origin/%s" % (r, r)).returncode != 0 and r == ASM:
                ok = False
        if ok:
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

    reviewed = reviews()
    now = int(time.time())
    for r in ("review", "cr2", "cr3", "cr4"):
        wait = sorted((t, key, sha) for key, (t, sha) in merged.items()
                      if reviewer_of(key) == r and t > reviewed.get(key, (0,))[0])
        minor = sorted((t, key, sha) for key, (t, sha) in light.items()
                       if reviewer_of(key) == r and t > max(reviewed.get(key, (0,))[0], merged.get(key, (0, ""))[0]))
        print("%-6s %d waiting%s" % (r, len(wait), "  <-- more than three" if len(wait) > 3 else ""))
        for t, key, sha in wait:
            last = reviewed.get(key)
            print("         %-34s merged %s (%s, %d min ago)%s" % (
                key, hhmm(t), sha, (now - t) // 60,
                "; last reviewed %s by %s" % (hhmm(last[0]), last[1]) if last else "; never reviewed this shift"))
        for t, key, sha in minor:
            print("         %-34s pictures or card only, merged %s (%s)" % (key, hhmm(t), sha))


if __name__ == "__main__":
    main()
