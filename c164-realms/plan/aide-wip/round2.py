#!/usr/bin/env python3
"""Round two (the director's announcement of 11-16 12:12): who has moved since, who has something in the assembly.

    round2.py [--since HH:MM] [-v]

Reads git only (fetch first). Per person: commits with the subject prefix `c164-<code>:` on the person's
own branches since the given time (default 12:12 CST), node jobs on them, and whether a merge into the
assembly since then carries a commit of theirs. Prints the short lists the director asked for
(nobody's names but those without a push, and those without work), then the whole table with -v.
"""
import re
import subprocess
import sys
import time

TREE = "/agent/repos/c164-aide-f3-b9ab"
ASM = "origin/cursor/c164-assembly-fable-a9f5"

# who does what, from plan/round2.md section 4 (ae08058d, df3f4072 for 丙二, b9f4fd46 for 丙三) and the changes told to the aide
WORK = {
    "a2": "motion/travel（载人，12:35 前和 s1 试）；丙三 sky/alive 星星闪烁、流星",
    "s1": "和 a2 试载人；每版存档图",
    "cable": "machines/train 牵头；卷扬机一整套",
    "m1": "machines/train 的机车；丙三 site/engine-shed 机车库",
    "a4": "site/railway 定线（_rail.py，12:30 前）；site/fountain；下平台、山体分人；走查",
    "cloud": "site/railway 的桥墩入云；sky/birds；丙三 sky/far-lights 远处的灯",
    "snow": "site/railway 的石拱；山体",
    "mast": "motion/arrival 牵头；桅杆顶灯和火花；丙三 motion/levers 能动手的底件",
    "outb": "motion/arrival 的导出和验证；每版导出；丙三 核猫",
    "smoke": "motion/train-smoke-sound；motion/small-life",
    "sound": "motion/train-smoke-sound；每版量暗格；丙三 值班室留声机的旋律",
    "lamps": "props/station；带火苗的灯",
    "m3": "props/steam-mains 的管；丙二 props/pipe-bridge 管桥",
    "power": "发电房；丙三 interiors/workshop 仪器工坊（表和阀 12:27 归 a6 做成套件）",
    "rec": "props/pneumatic；授时室的电报机；丙三 machines/recorders-2 自记仪器",
    "dome": "穹顶慢转、天窗开合；丙三 main/semaphore 臂板信号塔",
    "m5": "穹顶传动跟着转；丙二 site/gasometer 煤气柜",
    "scope": "大折射镜跟彗星；丙二 site/goods-lift 货梯和吊杆",
    "tower": "塔钟的针、风向标；丙二 main/tower-works 露出机芯",
    "clocks": "报时球、塔钟、打钟；丙二 main/tower-works",
    "ashlar": "浑天仪的环；丙二 site/yard 下平台的场子",
    "m2": "授时室（V10 的三处先完）",
    "chart": "星图室刻图机",
    "vault": "V4 门洞；底片库滴水",
    "astro": "蓄电池室冒泡、电流表",
    "sdome": "端部女儿墙；天文室照相仪、摆钟；屋顶",
    "a3": "穹顶室观测椅、表",
    "clkrm": "钟室打点锤、风翼；丙三 machines/difference-engine 差分机（12:27 起现在就开）",
    "orrery": "行星仪的月亮、轴、蜗杆；丙二 machines/wind-engine 风力抽水机、风向标、自记气压计",
    "a1": "贴图动画的做法（12:30 前）；火苗",
    "a6": "旗；前庭的家具；丙三 props/gauges 表和阀套件、interiors/duty-room 值班室；props 审批",
    "shell": "丙二 main/roof-works 屋顶机器和背面、两翼的管线；窗里的灯",
    "facade": "主楼外面；室外走查；main 审批",
    "lights": "星厅代主人（hall 掉线，aide 12:17 派）；丙三 motion/doors 正门铁门",
    "review": "12:40 前在 A8 的图上圈空处；打分",
    "cr2": "圈空处；sky、motion 审批",
    "cr3": "圈空处；machines 审批，代 interiors",
    "s2": "守头、checkall、STATUS",
    "aide": "名单、机器、报告",
}
GONE = {"stair": "掉线（cr4）", "hall": "掉线", "comet": "掉线"}


def git(*args):
    return subprocess.run(("git", "-C", TREE) + args, capture_output=True, text=True).stdout


def main():
    args = sys.argv[1:]
    since = "12:12"
    if "--since" in args:
        since = args[args.index("--since") + 1]
    verbose = "-v" in args
    day = time.strftime("%Y-%m-%d", time.gmtime(time.time() + 8 * 3600))
    since_iso = "%sT%s:00+08:00" % (day, since)

    refs = [r for r in git("for-each-ref", "--format=%(refname:short)", "refs/remotes/origin/cursor/").split("\n") if r]
    rows = {}
    for code in list(WORK) + list(GONE):
        mine = [r for r in refs if r.startswith("origin/cursor/c164-%s-" % code)]
        n, jobs, last, subj = 0, 0, 0, ""
        if mine:
            out = git("log", "--since=" + since_iso, "--format=%ct\t%s", *mine, "--not", ASM + "@{0}~0") if False else \
                git("log", "--since=" + since_iso, "--format=%H\t%ct\t%s", *mine)
            seen = set()
            for line in out.split("\n"):
                if not line:
                    continue
                h, ct, s = line.split("\t", 2)
                if h in seen:
                    continue
                seen.add(h)
                if s.startswith("c164-%s:" % code) or s.startswith("c164-%s " % code):
                    n += 1
                    if int(ct) > last:
                        last, subj = int(ct), s
                elif s.startswith("c164-node:"):
                    jobs += 1
        rows[code] = dict(n=n, jobs=jobs, last=last, subj=subj, merged=[])

    # merges into the assembly since then: whose commits do they carry
    out = git("log", "--first-parent", "--merges", "--since=" + since_iso, "--format=%H\t%ct\t%s", ASM)
    for line in out.split("\n"):
        if not line:
            continue
        h, ct, s = line.split("\t", 2)
        inner = git("log", "--since=%sT11:30:00+08:00" % day, "--format=%s", "%s^1..%s^2" % (h, h))
        codes = set(re.findall(r"^c164-([a-z0-9]+)[: ]", inner, re.M))
        m = re.search(r"merge ([a-z]+/[a-z0-9_-]+)", s)
        what = m.group(1) if m else s[:40]
        for code in codes:
            if code in rows:
                rows[code]["merged"].append("%s %s" % (time.strftime("%H:%M", time.gmtime(int(ct) + 8 * 3600)), what))

    def hm(t):
        return time.strftime("%H:%M", time.gmtime(t + 8 * 3600)) if t else "—"

    quiet = [c for c in WORK if rows[c]["n"] == 0 and c != "aide"]
    moved = [c for c in WORK if rows[c]["merged"]]
    print("since %s: %d people on the page; %d with a push, %d without; %d with something merged"
          % (since, len(WORK) - 1, len(WORK) - 1 - len(quiet), len(quiet), len(moved)))
    print("没推送的：" + ("、".join(quiet) if quiet else "无"))
    print("已进总装的：" + ("、".join("%s（%s）" % (c, rows[c]["merged"][-1]) for c in moved) if moved else "无"))
    print("掉线的：" + "、".join(GONE))
    if verbose:
        print()
        for code in list(WORK) + list(GONE):
            r = rows[code]
            print("%-7s push %2d job %2d last %s  merged %-28s | %s | %s" % (
                code, r["n"], r["jobs"], hm(r["last"]), ";".join(r["merged"])[:28] or "-",
                (WORK.get(code) or GONE.get(code))[:34], r["subj"][:70]))


main()
