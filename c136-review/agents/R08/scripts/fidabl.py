#!/usr/bin/env python3
"""fidabl.py — 离线模拟器（src/sim + 重放器）对历史录像的保真度：对账与消融的汇总。

数据从三个 node 脚本来（都只读 /agent/repos/c136-data 的发现集，不跑策略、不改指令）：
    fidabl.mjs  --until 1800 <局…>                          → out/_run/fidabl/<局>.json        （臂：full / nocolor / aiteam / diff6；对我方日志快照）
    fidabl.mjs  --arms full,nocache,noteamend --tag late <局…> → out/_run/fidabl/<局>.late.json   （整局长度；对我方日志快照）
    engdiff.mjs <局…>                                        → out/_run/engdiff/<局>.json        （整局长度；模拟器对线上引擎原文，全部 512 个玩家每 10 拍）
    engdiff.mjs --until 1800 --fid aiteam <局…>              → out/_run/engdiff/<局>.aiteam.u1800.json
    engdiff.mjs --fid nocache|noteamend <局…>                → out/_run/engdiff/<局>.<臂>.json
    xtruth.mjs（早先跑过）                                    → out/_run/xtruth/<局>.json         （这里只用录像头：队数、AI 入不入队）
再汇总：
    python3 fidabl.py [--quiet]     → out/_cross/fidabl.txt、fidabl.json

「引擎」= src/engine/live_game_js.js（线上客户端原文）在 Node 里按录像原样重放（src/tools/engine_replay.cjs）；
「模拟器」= src/sim/sim/*.js + 本目录 resim_r08.mjs 里的重放器子类（组队配色随机数、引擎分队、32 拍缓存、组队版猎杀 / 提速）。
「开环」= 把录像里的指令原样喂进去，世界走偏以后指令不会跟着变；所以消融臂的宏观量只说明「世界偏了多少」，不是那一臂闭环会打成什么样。

节：
  [FA-A] 样本与录像头：有对局段且重演对得上的 89 局；其中是同一个物理房间的几对；录像头队数 → 实际队数；内置 AI 入不入队。
  [FA-B] 消融（到 1800 拍，对我方日志快照）：每一臂还剩几局 / 几行逐位一致、第一处不一致在哪一拍。
  [FA-C] 消融（开环）的宏观偏移：内置 AI 占全图陆地的份额、还有地的 AI 个数、真人席位的地、我方占真人总地的份额。
  [FA-D] 只在后期才起作用的引擎项（猎杀、终局提速、32 拍缓存）：多少局触发、第一次在哪一拍；关掉以后对引擎第一处不一致在哪一拍。
  [FA-E] 模拟器对引擎，全场逐位：几局整局一致、不一致的那几局第一处在哪、是什么事件；各断面（0 / 630 / 1500 / 3000 / 4284 / 6000）上还一致的局数。
"""
import glob
import json
import os
import statistics
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")
RUN = os.path.join(OUT, "_run")
CPS = [300, 600, 900, 1500, 1800]
SECTIONS = [0, 630, 1500, 3000, 4284, 6000]


def q(xs, p):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    k = (len(xs) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def f(x, nd=0):
    return "–" if x is None else f"{x:.{nd}f}"


def pct(a, b, nd=0):
    return "–" if not b else f"{100 * a / b:.{nd}f}%"


def qs(xs, ps=(0.1, 0.25, 0.5, 0.75, 0.9), nd=0):
    return " / ".join(f(q(xs, p), nd) for p in ps)


def load(pattern):
    out = {}
    for p in sorted(glob.glob(os.path.join(RUN, pattern))):
        try:
            R = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        out[os.path.basename(p).split(".")[0]] = R
    return out


def main():
    quiet = "--quiet" in sys.argv
    lines = []
    J = {}

    def P(s=""):
        lines.append(s)

    lst = json.load(open(os.path.join(RUN, "fidabl_list.json"), encoding="utf-8"))
    mids = [m for m, _, _ in lst]
    cohort = {m: c for m, _, c in lst}
    A = {}
    for m in mids:
        p = os.path.join(RUN, "fidabl", f"{m}.json")
        if os.path.exists(p):
            A[m] = json.load(open(p, encoding="utf-8"))
    L = {}
    for m in mids:
        p = os.path.join(RUN, "fidabl", f"{m}.late.json")
        if os.path.exists(p):
            L[m] = json.load(open(p, encoding="utf-8"))
    E, EA, EC, ET = {}, {}, {}, {}
    for m in mids:
        for d, suf in ((E, ""), (EA, ".aiteam.u1800"), (EC, ".nocache"), (ET, ".noteamend")):
            p = os.path.join(RUN, "engdiff", f"{m}{suf}.json")
            if os.path.exists(p):
                R = json.load(open(p, encoding="utf-8"))
                if "error" not in R:
                    d[m] = R

    # ---------------------------------------------------------------- [FA-A]
    P("[FA-A] 样本与录像头")
    XT = {}
    for p in sorted(glob.glob(os.path.join(RUN, "xtruth", "*.json"))):
        R = json.load(open(p, encoding="utf-8"))
        if "error" in R or "H" not in R:
            continue
        XT[R["matchId"]] = R
    P(f"  有地图、能重演的录像 {len(XT)} 份；其中有对局段且重演和我方日志逐行对得上的 {len(mids)} 局（squad10 {sum(1 for m in mids if cohort[m] == 'squad10')} / squad20 {sum(1 for m in mids if cohort[m] == 'squad20')}）")
    rooms = defaultdict(list)
    for m in mids:
        R = XT.get(m)
        if R:
            rooms[(R["H"], R["land"], tuple(R["names"]))].append(m)
    dup = [v for v in rooms.values() if len(v) > 1]
    P(f"  这 {len(mids)} 局是 {len(rooms)} 个物理房间（同一个房间出了两份包的 {len(dup)} 对：{'；'.join('+'.join(v) for v in dup) or '无'}）")
    J["valid"] = len(mids)
    J["rooms"] = len(rooms)

    def head_table(sel, label):
        ffa = [m for m in sel if XT[m]["gameMode"] == 0]
        team = [m for m in sel if XT[m]["gameMode"] != 0]
        bt = [m for m in team if XT[m]["botsTeamed"]]
        red = [m for m in team if XT[m]["nTeams"] < XT[m]["nTeamsHeader"]]
        P(f"  {label}：{len(sel)} 份；自由混战 {len(ffa)}，组队 {len(team)}；组队局里内置 AI 入队的 {len(bt)}（都是实际 8 队：{all(XT[m]['nTeams'] == 8 for m in bt)}），不入队的 {len(team) - len(bt)}（{pct(len(team) - len(bt), len(team))}）")
        P(f"    录像头队数比实际队数多（引擎按最大战队人数减队）的 {len(red)} / {len(team)}（{pct(len(red), len(team))}）；实际队数分布：" + "；".join(f"{k} 队 {v}" for k, v in sorted(Counter(XT[m]['nTeams'] for m in team).items())))
        cnt = Counter((XT[m]["nTeamsHeader"], XT[m]["nTeams"]) for m in team)
        P("    录像头队数→实际队数：" + "；".join(f"{a}→{b} {n}" for (a, b), n in sorted(cnt.items())))
        return dict(n=len(sel), ffa=len(ffa), team=len(team), botsTeamed=len(bt), reduced=len(red))

    J["head_all"] = head_table(sorted(XT), "全部能重演的录像")
    J["head_valid"] = head_table([m for m in mids if m in XT], "其中对得上的 89 局")
    Hs = [XT[m]["H"] for m in mids if m in XT]
    P(f"  开局真人数（89 局）P10 / P25 / P50 / P75 / P90 = {qs(Hs)}；最少 {min(Hs)}，最多 {max(Hs)}")
    P()

    # ---------------------------------------------------------------- [FA-B]
    P("[FA-B] 消融（到 1800 拍；对我方日志快照 traj.csv，每个号每 90 拍一行）")
    P("  臂 | 适用的局 | 整段逐位一致的局 | 逐位一致的行 / 总行 | 第一处不一致的拍 P10 / P50 / P90（不一致的局里）")
    arms = [("full", "原样（参照）"), ("nocolor", "不做组队配色随机数"), ("aiteam", "内置 AI 一律入队（基类默认；teamgate 的建局方式）"), ("diff6", "内置 AI 难度 6")]
    J["ablate"] = {}
    for arm, cn in arms:
        app = []
        for m, R in A.items():
            if arm == "nocolor" and R.get("gameMode") == 0:
                continue          # 自由混战不走组队配色
            if arm == "aiteam" and (R.get("gameMode") == 0 or R.get("botsTeamed")):
                continue          # 自由混战没有队；实际 8 队的局线上本来就入队
            if arm not in R["arms"] or "error" in R["arms"][arm]:
                continue
            app.append(m)
        ok = [m for m in app if A[m]["arms"][arm]["exact"] == A[m]["arms"][arm]["rows"]]
        rows = sum(A[m]["arms"][arm]["rows"] for m in app)
        ex = sum(A[m]["arms"][arm]["exact"] for m in app)
        fm = [A[m]["arms"][arm]["firstMism"] for m in app if A[m]["arms"][arm]["firstMism"] is not None]
        P(f"  {arm}（{cn}）| {len(app)} | {len(ok)} | {ex} / {rows}（{pct(ex, rows)}）| {qs(fm, (0.1, 0.5, 0.9)) if fm else '–'}")
        J["ablate"][arm] = dict(matches=len(app), exactMatches=len(ok), rows=rows, exact=ex, firstQ=[q(fm, p) for p in (0.1, 0.5, 0.9)] if fm else None)
    P("  （nocolor 不适用的是 4 局自由混战；aiteam 不适用的是自由混战和线上本来就让 AI 入队的实际 8 队局——这两类局里这一臂和原样逐位相同）")
    if EA:
        app = [m for m in EA if not (A.get(m, {}).get("gameMode") == 0 or A.get(m, {}).get("botsTeamed"))]
        ft = [EA[m]["exactT"] for m in app if EA[m].get("exactT") is not None]
        kinds = Counter(EA[m]["who"][0]["kind"] for m in app if EA[m].get("who"))
        P(f"  aiteam 臂对引擎（全部 512 个玩家，到 1800 拍）：{len(app)} 局里 {len(ft)} 局走偏，第一处不一致的拍 P10 / P25 / P50 / P75 / P90 = {qs(ft)}；第一个对不上的玩家：" + "；".join(f"{k} {v}" for k, v in kinds.most_common()))
        J["ablate"]["aiteam_engine"] = dict(matches=len(app), diverged=len(ft), firstQ=[q(ft, p) for p in (0.1, 0.25, 0.5, 0.75, 0.9)])
    P()

    # ---------------------------------------------------------------- [FA-C]
    P("[FA-C] 消融（开环）的宏观偏移：同一份录像，各臂在同一拍上的量对原样（= 线上真相）")
    P("  「AI 份额」= 内置 AI 的地 ÷ 全图陆地；「席位偏差」= 原样里还有地的真人席位，|这一臂的地 − 原样的地| ÷ 原样的地；「我方份额」= 我方号的地 ÷ 全部真人席位的地")
    J["drift"] = {}
    for arm, cn in arms[1:]:
        P(f"  {arm}（{cn}）")
        P("    拍 | 局 | AI 份额 原样 → 这一臂（各局中位）| 差的 P10 / P50 / P90（百分点）| 还有地的 AI 个数 原样 → 这一臂（中位）| 席位偏差：各局中位的中位 / 偏差 >20% 的席位占比（合并）| 我方份额 原样 → 这一臂（中位）| 我方份额之比 P10 / P50 / P90")
        J["drift"][arm] = {}
        for t in CPS:
            sh0, sh1, dsh, n0, n1, med_dev, big, tot, own0, own1, ratio = [], [], [], [], [], [], 0, 0, [], [], []
            nm = 0
            for m, R in A.items():
                if arm == "nocolor" and R.get("gameMode") == 0:
                    continue
                if arm == "aiteam" and (R.get("gameMode") == 0 or R.get("botsTeamed")):
                    continue
                a0, a1 = R["arms"].get("full"), R["arms"].get(arm)
                if not a0 or not a1 or "error" in a0 or "error" in a1:
                    continue
                c0, c1 = a0["cp"].get(str(t)), a1["cp"].get(str(t))
                if not c0 or not c1:
                    continue
                nm += 1
                land = R["land"]
                s0, s1 = c0["botLand"] / land, c1["botLand"] / land
                sh0.append(s0)
                sh1.append(s1)
                dsh.append(100 * (s1 - s0))
                if c0["aiN"] is not None and c1["aiN"] is not None:
                    n0.append(c0["aiN"])
                    n1.append(c1["aiN"])
                devs = []
                for p, (x0, x1) in enumerate(zip(c0["terr"], c1["terr"])):
                    if x0 > 0:
                        d = abs(x1 - x0) / x0
                        devs.append(d)
                        tot += 1
                        big += d > 0.2
                if devs:
                    med_dev.append(statistics.median(devs))
                own = [i for i in R["squad"].values() if i >= 0]
                h0, h1 = sum(c0["terr"]), sum(c1["terr"])
                if own and h0 and h1:
                    o0, o1 = sum(c0["terr"][i] for i in own) / h0, sum(c1["terr"][i] for i in own) / h1
                    own0.append(o0)
                    own1.append(o1)
                    if o0 > 0:
                        ratio.append(o1 / o0)
            P(f"    {t} | {nm} | {f(q(sh0, 0.5), 3)} → {f(q(sh1, 0.5), 3)} | {qs(dsh, (0.1, 0.5, 0.9), 1)} | {f(q(n0, 0.5))} → {f(q(n1, 0.5))} | {f(q(med_dev, 0.5), 2)} / {pct(big, tot)} | {f(q(own0, 0.5), 3)} → {f(q(own1, 0.5), 3)} | {qs(ratio, (0.1, 0.5, 0.9), 2)}")
            J["drift"][arm][t] = dict(matches=nm, ai0=q(sh0, 0.5), ai1=q(sh1, 0.5), dAI=[q(dsh, p) for p in (0.1, 0.5, 0.9)], seatDev=q(med_dev, 0.5), seatBig=big / tot if tot else None,
                                      own0=q(own0, 0.5), own1=q(own1, 0.5), ownRatio=[q(ratio, p) for p in (0.1, 0.5, 0.9)])
    P()

    # ---------------------------------------------------------------- [FA-D]
    P("[FA-D] 只在后期才起作用的引擎项（整局长度）")
    hunts = [(m, R["arms"]["full"]) for m, R in L.items() if "full" in R["arms"] and "error" not in R["arms"]["full"]]
    hm = [(m, a) for m, a in hunts if a["hunts"]]
    fm = [(m, a) for m, a in hunts if a["firstFast"] is not None]
    either = [(m, a) for m, a in hunts if a["hunts"] or a["firstFast"] is not None]
    first_any = [min(x for x in (a["firstHunt"], a["firstFast"]) if x is not None) for m, a in either]
    P(f"  {len(hunts)} 局里：触发过猎杀（领先队 ≥80% 地、活人 ≥20、每 109 拍派目标）的 {len(hm)} 局，第一次的拍 最早 / P25 / P50 / P75 = {f(min(a['firstHunt'] for _, a in hm))} / {qs([a['firstHunt'] for _, a in hm], (0.25, 0.5, 0.75))}")
    P(f"    触发过终局提速（领先队 ≥90% 地）的 {len(fm)} 局，第一次的拍 最早 / P25 / P50 / P75 = {f(min(a['firstFast'] for _, a in fm))} / {qs([a['firstFast'] for _, a in fm], (0.25, 0.5, 0.75))}")
    P(f"    两者任一触发过的 {len(either)} 局（{pct(len(either), len(hunts))}）；最早的一次事件在 {min(first_any)} 拍；在 1500 拍以前触发的 {sum(1 for x in first_any if x < 1500)} 局，在 4284 拍以前触发的 {sum(1 for x in first_any if x < 4284)} 局")
    J["late"] = dict(matches=len(hunts), hunt=len(hm), fast=len(fm), either=len(either), earliest=min(first_any), before4284=sum(1 for x in first_any if x < 4284))
    for arm, cn, D in (("nocache", "各队总地不按 32 拍缓存（当拍现算）", EC), ("noteamend", "猎杀 / 提速退回基类写法（提速看榜首个人 ≥90%）", ET)):
        own_bad = [m for m, R in L.items() if arm in R["arms"] and "error" not in R["arms"][arm] and R["arms"][arm]["firstMism"] is not None
                   and (R["arms"]["full"]["firstMism"] is None or R["arms"][arm]["firstMism"] < R["arms"]["full"]["firstMism"])]
        s = f"  {arm}（{cn}）：对我方日志快照，比原样多出不一致的 {len(own_bad)} 局"
        if D:
            ev = [m for m in D if m in dict(either)]
            base_first = {m: E[m].get("exactT") for m in E}
            worse = [m for m in ev if D[m].get("exactT") is not None and (base_first.get(m) is None or D[m]["exactT"] < base_first[m])]
            ft = [D[m]["exactT"] for m in worse]
            s += f"；对引擎（全场），在触发过事件的 {len(ev)} 局里走偏 {len(worse)} 局，第一处不一致的拍 最早 / P50 / 最晚 = {f(min(ft)) if ft else '–'} / {f(q(ft, 0.5))} / {f(max(ft)) if ft else '–'}"
            J["late"][arm] = dict(ownRowsWorse=len(own_bad), engMatches=len(ev), engWorse=len(worse), first=[min(ft) if ft else None, q(ft, 0.5), max(ft) if ft else None])
        P(s)
    P()

    # ---------------------------------------------------------------- [FA-E]
    P("[FA-E] 模拟器对引擎，全场逐位（整局长度；每 10 拍比全部 512 个玩家的地和兵）")
    ok = [m for m in E if E[m]["firstT"] is None]
    bad = [m for m in E if E[m]["firstT"] is not None]
    ticks = sum(E[m]["engLast"] for m in E)
    ncmp = sum(E[m]["nCmp"] for m in E)
    nbad = sum(E[m]["nBad"] for m in E)
    P(f"  {len(E)} 局，合计 {ticks} 拍、{ncmp} 个断面：全场一致的断面 {ncmp - nbad}（{pct(ncmp - nbad, ncmp, 1)}）")
    P(f"  引擎 对 我方日志快照：{sum(E[m]['engLogExact'] for m in E)} / {sum(E[m]['engLogRows'] for m in E)} 行逐位一致（有不一致的局：{sum(1 for m in E if E[m]['engLogFirst'] is not None)}）")
    P(f"  模拟器 对 我方日志快照：{sum(E[m]['simLogExact'] for m in E)} / {sum(E[m]['logRows'] for m in E)} 行逐位一致（有不一致的局：{sum(1 for m in E if E[m]['simLogFirst'] is not None)}）")
    P(f"  模拟器 对 引擎：整局每个断面全场一致的 {len(ok)} 局；走偏的 {len(bad)} 局：")
    for m in sorted(bad, key=lambda m: E[m]["exactT"]):
        R = E[m]
        w = R["who"][0]
        P(f"    {m}（真人 {R['H']}，录像 {R['engLast']} 拍）：第一处 t={R['exactT']}，{w['kind']}#{w['p']}（{w['name']}）地 引擎 {w['terrE']} / 模拟器 {w['terrS']}，兵 引擎 {w['balE']} / 模拟器 {w['balS']}；同一拍对不上的玩家 {R['nWho']} 个；"
          f"之后一致的断面 {R['nCmp'] - R['nBad']} / {R['nCmp']}；在我方日志快照上第一次显出来是 t={R['simLogFirst']}（晚 {R['simLogFirst'] - R['exactT'] if R['simLogFirst'] is not None else '–'} 拍）；"
          f"末尾对不上的真人席位 {R['series'][-1][1] if R['series'] else '–'} 个")
    P("    （逐拍的摊开见 out/_cross/fidmism.txt）")
    P("  各断面上「录像到这一拍」的局数 / 其中到这一拍为止模拟器和引擎全场一致的局数：")
    J["sections"] = {}
    for t in SECTIONS:
        reach = [m for m in E if E[m]["engLast"] >= t]
        good = [m for m in reach if E[m].get("exactT") is None or E[m]["exactT"] > t]
        P(f"    t={t} | {len(reach)} | {len(good)}" + (f"（走偏的：{' '.join(sorted(set(reach) - set(good)))}）" if len(good) < len(reach) else ""))
        J["sections"][t] = dict(reach=len(reach), exact=len(good))
    J["engine"] = dict(matches=len(E), ticks=ticks, sections=ncmp, exactSections=ncmp - nbad, exactMatches=len(ok), diverged=sorted(bad),
                       engLog=[sum(E[m]["engLogExact"] for m in E), sum(E[m]["engLogRows"] for m in E)],
                       simLog=[sum(E[m]["simLogExact"] for m in E), sum(E[m]["logRows"] for m in E)])

    os.makedirs(os.path.join(OUT, "_cross"), exist_ok=True)
    open(os.path.join(OUT, "_cross", "fidabl.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    json.dump(J, open(os.path.join(OUT, "_cross", "fidabl.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if not quiet:
        print("\n".join(lines))


if __name__ == "__main__":
    main()
