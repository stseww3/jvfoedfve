#!/usr/bin/env python3
"""The director's five lines (11-16 08:39): numbers only, on the hour and the half hour.

  1. the cards (the 66 of STATUS.md and the ones opened since): in the assembly, in work, unclaimed
  2. since the fast lane (08:20): deliveries (a gate that ended in PASS) and merges
  3. the four interiors: delivered or not
  4. the six new hands: who has a commit of his own
  5. who has no first version yet: the name and what is missing

Everything is read from git: the assembly's log, the gate jobs on the -wip branches, the branches'
own commits. A gate that ended in PASS is counted as a delivery (the message itself goes to the
approver, not to the aide), so the count can run a little ahead of the messages.

  python3 five.py [-v] [--no-fetch]
"""
import re
import subprocess
import sys
import time

TREE = "/agent/repos/c164-aide-f3-b9ab"
ASM = "origin/cursor/c164-assembly-fable-a9f5"
SHIFT3 = 1794765600          # 11-16 02:00 +0800
FAST = 1794788400            # 11-16 08:20 +0800
CATS = "common|materials|main|props|site|sky|motion|machines|interiors"
PKG = re.compile(r"\b(%s)/([a-z0-9-]+)" % CATS)
IN_STATES = {"已合并", "已出图", "暂过", "已过审"}
# who holds a card now, where STATUS.md is behind
OWNER = {"machines/recorders": "rec", "interiors/platevault": "vault", "interiors/clockroom": "clkrm",
         "interiors/astroroom": "sdome", "interiors/batteryroom": "astro",
         "motion/smoke": "smoke", "motion/sound": "sound"}
# cards opened after STATUS.md's 66 were counted
EXTRA = [("sky", "safe-look", "a2")]
ROOMS = [("starhall", "星厅"), ("domeroom", "穹顶室"), ("chartroom", "星图室"), ("timeroom", "授时室")]
NEW = ["rec", "smoke", "vault", "clkrm", "astro", "sound"]
# cards that have no gate of their own (a walk is a list of findings, the status table is a file)
NO_GATE = {"common/walk-out", "common/walk-in", "common/offline-sky"}


def git(*args):
    return subprocess.run(["git", "-C", TREE] + list(args), capture_output=True, text=True)


def hm(ts):
    return time.strftime("%H:%M", time.gmtime(ts + 8 * 3600))


def cards():
    text = git("show", ASM + ":c164-realms/plan/STATUS.md").stdout
    cat, out = None, []
    for line in text.split("\n"):
        m = re.match(r"^## (\w+)（", line)
        if m:
            cat = m.group(1) if re.fullmatch(CATS, m.group(1)) else None
            continue
        if line.startswith("## "):
            cat = None
        if cat and line.startswith("| ") and not line.startswith("| 包") and not line.startswith("| ---"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 4:
                name = re.split(r"[（(]", cells[0])[0].strip()
                who = cells[3].split()[0] if cells[3] and cells[3] != "—" else ""
                out.append({"key": "%s/%s" % (cat, name), "state": cells[2], "who": who})
    for cat, name, who in EXTRA:
        out.append({"key": "%s/%s" % (cat, name), "state": "制作中", "who": who})
    for c in out:
        c["who"] = OWNER.get(c["key"], c["who"])
    return out


def merges():
    """The merges of packages into the assembly in the third shift, and the merges taken out again.

    ({package: [(time, commit, subject)]}, {package: [(time, the delivered commit)]}); a merge that
    was reverted is not in the first."""
    found_merges, reverted = [], {}
    log = git("log", "--format=%H %ct %s", "--since=%d" % SHIFT3, ASM).stdout
    for line in log.split("\n"):
        parts = line.split(" ", 2)
        if len(parts) < 3:
            continue
        h, ct, subject = parts[0], int(parts[1]), parts[2]
        m = re.match(r"^c164-[a-z0-9]+: revert the merge of (.*)$", subject)
        if m:
            found = PKG.search(m.group(1))
            commit = re.search(r"\b([0-9a-f]{7,40})\b", m.group(1)[found.end():]) if found else None
            if found and commit:
                reverted.setdefault("%s/%s" % found.groups(), []).append((ct, commit.group(1)))
            continue
        m = re.match(r"^c164-[a-z0-9]+: merge (.*)$", subject)
        if not m or re.match(r"(the )?assembly", m.group(1)):
            continue
        found = PKG.search(m.group(1))
        if found:
            commit = re.search(r"\b([0-9a-f]{7,40})\b", m.group(1)[found.end():])
            found_merges.append(("%s/%s" % found.groups(), ct, h[:8], subject, commit.group(1) if commit else ""))
    out = {}
    for key, ct, h, subject, commit in found_merges:
        gone = any(commit and (commit.startswith(c) or c.startswith(commit)) and rt >= ct
                   for rt, c in reverted.get(key, []))
        if not gone:
            out.setdefault(key, []).append((ct, h, subject))
    return out, reverted


def gates():
    """{package: [(time, delivered commit, result)]} of the gate jobs on any branch, third shift."""
    out = {}
    log = git("log", "--remotes=origin/cursor/c164-*", "--format=%H %ct %s", "--since=%d" % SHIFT3,
              "--grep=tools/gate.sh").stdout
    seen = set()
    for line in log.split("\n"):
        parts = line.split(" ", 2)
        if len(parts) < 3 or parts[0] in seen:
            continue
        seen.add(parts[0])
        h, ct, subject = parts[0], int(parts[1]), parts[2]
        m = re.search(r"tools/gate\.sh (%s)/([a-z0-9-]+) ([0-9a-f]{7,40})" % CATS, subject)
        if not m:
            continue
        cat, name, commit = m.groups()
        summary = git("show", "%s:c164-realms/renders/_wip/gate/%s/summary.txt" % (h, name))
        result = "?"
        if summary.returncode == 0:
            lines = [l for l in summary.stdout.split("\n") if l.strip()]
            head = lines[0] if lines else ""
            if lines and lines[-1].startswith("result:") and ("%s/%s" % (cat, name)) in head:
                result = lines[-1].split(":", 1)[1].strip()
        out.setdefault("%s/%s" % (cat, name), []).append((ct, commit[:8], result))
    for v in out.values():
        v.sort()
    return out


def own_commits(code):
    refs = git("for-each-ref", "--format=%(refname)", "refs/remotes/origin/cursor/c164-%s-*" % code).stdout.split()
    n = 0
    for ref in refs:
        log = git("log", "--format=%s", "--since=%d" % SHIFT3, ref, "--not", ASM).stdout
        n += sum(1 for s in log.split("\n") if s.startswith("c164-%s:" % code))
    return n, len(refs)


def main():
    verbose = "-v" in sys.argv
    if "--no-fetch" not in sys.argv:
        for attempt in range(3):
            r = git("fetch", "-q", "origin", "+refs/heads/cursor/c164-*:refs/remotes/origin/cursor/c164-*")
            if r.returncode == 0:
                break
            time.sleep(3)
    cs, (mg, reverted), gt = cards(), merges(), gates()
    now = int(time.time())

    def returned(c):
        """Its newest merge was taken out again and nothing of it went in since."""
        last_revert = max((rt for rt, _ in reverted.get(c["key"], [])), default=0)
        last_merge = max((ct for ct, _, _ in mg.get(c["key"], [])), default=0)
        return last_revert > last_merge

    def is_in(c):
        return not returned(c) and (c["state"] in IN_STATES or c["key"] in mg)

    inside = [c for c in cs if is_in(c)]
    unclaimed = [c for c in cs if not is_in(c) and not c["who"]]
    work = [c for c in cs if not is_in(c) and c["who"]]

    passes = set()
    for key, runs in gt.items():
        for ct, commit, result in runs:
            if ct >= FAST and result == "PASS":
                passes.add((key, commit))
    merged = [(ct, h, s) for v in mg.values() for ct, h, s in v if ct >= FAST]

    rooms = []
    for name, label in ROOMS:
        key = "interiors/" + name
        ok = [r for r in gt.get(key, []) if r[2] == "PASS"]
        if key in mg:
            rooms.append("%s已合（%s）" % (label, hm(mg[key][0][0])))
        elif ok:
            rooms.append("%s已交（%s 关口过），没合" % (label, hm(ok[-1][0])))
        elif gt.get(key):
            rooms.append("%s没交（关口 %s）" % (label, gt[key][-1][2]))
        else:
            rooms.append("%s没交（没跑关口）" % label)

    new = []
    for code in NEW:
        n, refs = own_commits(code)
        new.append((code, n, refs))

    missing = {"被退回等重交": [], "没跑关口": [], "关口没过": [], "新人刚开": [], "没有关口的卡": []}
    waiting = []
    for c in work:
        runs = gt.get(c["key"], [])
        label = "%s（%s）" % (c["who"], c["key"].split("/", 1)[1])
        if returned(c):
            missing["被退回等重交"].append(label)
        elif c["key"] in NO_GATE:
            missing["没有关口的卡"].append(label)
        elif any(r[2] == "PASS" for r in runs):
            waiting.append(label)
        elif runs:
            missing["关口没过"].append(label)
        elif c["who"] in NEW:
            missing["新人刚开"].append(c["who"])
        else:
            missing["没跑关口"].append(label)

    try:
        load = open("/proc/loadavg").read().split()[0]
    except OSError:
        load = "?"
    print("【五行 %s｜合用机负载 %s（4 核）】" % (hm(now), load))
    back = sum(1 for c in work if returned(c))
    print("1. 卡 %d 张（66 加新开 %d）：进总装 %d，在做 %d%s，没人领 %d。"
          % (len(cs), len(EXTRA), len(inside), len(work), "（其中退回 %d）" % back if back else "", len(unclaimed)))
    print("2. 08:20 快车道以后：新交付 %d 件（关口 PASS），合进 %d 件。" % (len(passes), len(merged)))
    print("3. 室内：" + "；".join(rooms) + "。")
    print("4. 新人有提交的：%s；还没有：%s。"
          % ("、".join("%s %d" % (c, n) for c, n, _ in new if n) or "无",
             "、".join(c for c, n, _ in new if not n) or "无"))
    line = "5. 没交第一版："
    line += "；".join("%s：%s" % (k, "、".join(v)) for k, v in missing.items() if v) or "无"
    if waiting:
        line += "。关口过了等合：" + "、".join(waiting)
    print(line + "。")

    if verbose:
        print()
        print("-- unclaimed:", ", ".join(c["key"] for c in unclaimed))
        print("-- in work:", ", ".join("%s(%s)" % (c["key"], c["who"]) for c in work))
        print("-- deliveries since the fast lane:")
        for key, commit in sorted(passes):
            print("     ", key, commit)
        print("-- merges since the fast lane:")
        for ct, h, s in sorted(merged):
            print("     ", hm(ct), h, s[:110])
        print("-- gates of the cards in work:")
        for c in work:
            print("     ", c["key"], [(hm(ct), commit, result) for ct, commit, result in gt.get(c["key"], [])][-3:])
        print("-- new hands:", new)


if __name__ == "__main__":
    main()
