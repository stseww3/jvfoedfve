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


# -- the first line since 11-16 10:32 (the director: the cards are all in, report these three) --------

BOARD = "/tmp/c164_aide/board.json"   # kept by hand from the reviewers' lines


def newest(patterns, suffix):
    """The newest file ending in suffix on the branches matching the patterns: (time, ref, path)."""
    best = None
    refs = git("for-each-ref", "--format=%(refname:short)", *["refs/remotes/origin/cursor/" + p for p in patterns])
    for ref in refs.stdout.split() + [ASM]:
        for top in ("c164-realms/plan/reviews/walk", "c164-realms/renders/_wip/light"):
            for path in git("ls-tree", "-r", "--name-only", ref, "--", top).stdout.split("\n"):
                if not path.endswith(suffix):
                    continue
                ct = git("log", "-1", "--format=%ct", ref, "--", path).stdout.strip()
                if ct and (best is None or int(ct) > best[0]):
                    best = (int(ct), ref, path)
    return best


def walk_count(kind):
    """(the places that still stop a visitor, the head walked, when written) of the newest findings."""
    got = newest(["c164-a4-*", "c164-facade-*"], "/%s-findings.md" % kind)
    if not got:
        return None
    ct, ref, path = got
    text = git("show", "%s:%s" % (ref, path)).stdout
    m = re.search(r"挡人的[：:]\s*(\d+)", text) or re.search(r"挡人的\s*(\d+)\s*处", text)
    if not m and re.search(r"没有.{0,6}挡人|nobody is stopped", text):
        n = 0
    else:
        n = int(m.group(1)) if m else None
    return n, path.split("/")[-2], ct


def dark_count():
    """(dark cells, of them ruled 'not to be lit', the head measured, when) of sound's newest list."""
    got = newest(["c164-sound-*", "c164-lights-*"], "/dark.md")
    if not got:
        return None
    ct, ref, path = got
    text = git("show", "%s:%s" % (ref, path)).stdout
    m = re.search(r"\*\*暗：(\d+) 格", text)
    head = re.search(r"总装 ([0-9a-f]{7,8})", text)
    # since 10:46 the cells ruled "not to be lit" are listed apart and are not in the total
    apart = re.search(r"定了不补的 (\d+) 格", text)
    skip = int(apart.group(1)) if apart else None
    return (int(m.group(1)) if m else None), skip, head.group(1) if head else "?", ct


def board():
    import json
    try:
        return json.load(open(BOARD, encoding="utf-8"))
    except (OSError, ValueError):
        return None


def first_line():
    parts = []
    wi, wo = walk_count("in"), walk_count("out")
    def w(x):
        return "?" if not x or x[0] is None else str(x[0])
    parts.append("走查还挡人：室内 %s（%s）、室外 %s（%s）"
                 % (w(wi), wi[1] if wi else "?", w(wo), wo[1] if wo else "?"))
    d = dark_count()
    if d:
        parts.append("路上还暗 %s 格（总装 %s，%s 量；定了不补的%s另算）"
                     % (d[0], d[2], hm(d[3]), " %d 格" % d[1] if d[1] is not None else ""))
    else:
        parts.append("路上还暗 ? 格")
    b = board()
    if b:
        parts.append("12 张图过 %d 张（%s；没过 %s%s）" % (
            len(b["pass"]), b["version"], "、".join("%s %s" % kv for kv in b["fail"].items()) or "无",
            "；等着 " + "、".join(b["wait"]) if b.get("wait") else ""))
    else:
        parts.append("12 张图过 ? 张")
    return "1. " + "；".join(parts) + "。"


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
    have = {c["key"] for c in out}
    for cat, name, who in EXTRA:
        if "%s/%s" % (cat, name) not in have:
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
    # the ones that went into the assembly count too: a merged first version is still his
    log = git("log", "--format=%H %s", "--since=%d" % SHIFT3, ASM, *refs).stdout
    n = sum(1 for s in log.split("\n") if s[41:].startswith("c164-%s:" % code))
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
    print(first_line())
    print("   卡 %d 张：进总装 %d，在做 %d%s，没人领或不做 %d。"
          % (len(cs), len(inside), len(work), "（其中退回 %d）" % back if back else "", len(unclaimed)))
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
