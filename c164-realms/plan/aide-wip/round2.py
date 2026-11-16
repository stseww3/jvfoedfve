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
    "a2": "motion/travel（载人；13:25 前节点上跑通，B3 要见车）；预算的账（sky/alive 13:00 交 comet）",
    "s1": "和 a2 试载人；每版存档图",
    "cable": "machines/train 牵头（客车 5×3、12 座；13:30 前能跑的第一版）；卷扬机一整套",
    "m1": "machines/train 的机车（13:30 前第一版）；机车库 12:47 砍了",
    "a4": "site/railway 定线（13:04 改直，不再动）；站内平轨；两块大铺地管总；V1 挡墙和 site 的审批；喷泉 12:47 砍了",
    "cloud": "桥墩入云那一圈；云涌；sky/birds",
    "snow": "石拱桥 17 孔 18 墩（13:30 前体块）；山体",
    "mast": "motion/arrival 牵头；桅杆顶灯和火花；丙三 motion/levers 能动手的底件",
    "outb": "motion/arrival 的导出和验证；每版导出；丙三 核猫",
    "smoke": "motion/train-smoke-sound；motion/small-life",
    "sound": "motion/train-smoke-sound；每版量暗格；丙三 值班室留声机的旋律",
    "lamps": "props/station；带火苗的灯",
    "m3": "props/steam-mains 的管；丙二 props/pipe-bridge 管桥；前庭的冒汽格栅",
    "power": "发电房；风力抽水机；气象站三样和测风杆（12:55）；丙三 仪器工坊",
    "rec": "props/pneumatic；授时室的电报机；丙三 machines/recorders-2 自记仪器",
    "dome": "穹顶慢转、天窗开合（臂板信号塔 12:47 砍了）",
    "m5": "穹顶传动跟着转、天窗帘；水压蓄能器（12:47 由煤气柜改）",
    "scope": "大折射镜跟彗星；丙四 目镜里真能看、小望远镜；前庭的小赤道仪（货梯 12:30 挪给 astro）",
    "tower": "塔钟的针、风向标；丙二 main/tower-works 露出机芯",
    "clocks": "报时球、塔钟、打钟；丙二 main/tower-works",
    "ashlar": "下平台的场子排最前（总监 13:02）；浑天仪收尾往后",
    "m2": "授时室（V10 的三处先完）",
    "chart": "星图室刻图机；interiors 第二审批人（13:16）",
    "vault": "V4 门洞；底片库滴水",
    "astro": "蓄电池室冒泡、电流表；丙二 site/goods-lift 货梯和吊杆（12:30 从 scope 挪来）",
    "sdome": "V1 正中那面挡墙（总监 13:02，stair 帮）；天文室收尾；暖房 12:47 砍了",
    "a3": "客车里的散件（帮 cable，12:56）；穹顶室；风暴信号杆排后",
    "clkrm": "钟室打点锤、风翼；丙三 machines/difference-engine 差分机（12:27 起现在就开）",
    "orrery": "新聊天 c363（13:00）：行星仪做到近层",
    "hall": "新聊天 c364（13:00）：星厅的墙地回廊门",
    "stair": "新聊天 c365（13:04 报到）：先帮 sdome 做 V1 挡墙，再大台阶",
    "comet": "新聊天 c366（13:05 报到）：sky/alive 彗尾、闪烁、流星",
    "a1": "贴图动画的做法（12:30 前）；火苗",
    "a6": "旗；前庭的家具；丙三 props/gauges 表和阀套件、interiors/duty-room 值班室；props 审批",
    "shell": "丙二 main/roof-works 屋顶机器和背面、两翼的管线；窗里的灯；下观景台",
    "facade": "主楼外面；室外走查；main 审批",
    "lights": "室外灯具留远档（13:35 前）；星厅天花星座、弧光灯、正门铁门",
    "review": "12:40 前在 A8 的图上圈空处；打分",
    "cr2": "圈空处；sky、motion 审批",
    "cr3": "machines、interiors 审批；每版六处近景",
    "s2": "守头、checkall、STATUS",
    "aide": "名单、机器、报告",
}
GONE = {}


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
        rows[code] = dict(n=0, jobs=0, last=0, subj="", merged=[])
    # a person's commits wherever they are pushed (a stand-in works on another package's branch): by subject prefix
    out = git("log", "--since=" + since_iso, "--format=%H\t%ct\t%s", "--remotes=origin/cursor/c164-*")
    for line in out.split("\n"):
        if not line:
            continue
        h, ct, s = line.split("\t", 2)
        m = re.match(r"c164-([a-z0-9]+)[: ]", s)
        if m and m.group(1) in rows:
            r = rows[m.group(1)]
            r["n"] += 1
            if int(ct) > r["last"]:
                r["last"], r["subj"] = int(ct), s
    # node jobs: by the branch they were pushed back to
    for code in rows:
        mine = [r for r in refs if r.startswith("origin/cursor/c164-%s-" % code)]
        if mine:
            out = git("log", "--since=" + since_iso, "--format=%s", *mine)
            rows[code]["jobs"] = sum(1 for s in out.split("\n") if s.startswith("c164-node:"))

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
