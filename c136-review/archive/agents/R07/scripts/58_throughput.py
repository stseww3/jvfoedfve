#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""58_throughput.py — R07：发令快慢和落地条数的关系（全部能对账的带录像对局包）。

窗口 = 同一个号相邻两条 [HL-TICK]（正好隔 90 拍、cmds 没有回绕）。
  发出 = 窗口里 cmds 的增量；落地 = 录像里这个号落在 (t0, t1] 的指令条数（进攻 / 捐款 / 船 / 追击）。
  有 [HL-DISPATCH]（捐款）的窗口单列：被服务器按配额拒收的捐款不进录像，会混进「没落地」。
全队窗口 = 同一个 (t0, t1] 上所有在场号的和。

先跑 57_exec_census.mjs（写 out/_cache/census/<局>/humans_cmd.tsv 和 squad_players.tsv）和 57_exec_census.py（写 out/_cross/exec_census.tsv）。
用法：python3 58_throughput.py
输出：out/_cross/throughput.txt、out/_cross/throughput_games.tsv
"""
import bisect
import csv
import os
import re
import statistics
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = "/agent/repos/c136-data"
ROOT = os.path.join(HERE, "..", "out", "_cache", "census")
CROSS = os.path.join(HERE, "..", "out", "_cross")
TICK_RE = re.compile(r"^\d+\t\[([^\]\[]+)\] \[HL-TICK\] t=(\d+) .*?cmds=(\d+)")
DISP_RE = re.compile(r"^\d+\t\[([^\]\[]+)\] \[HL-DISPATCH\] t=(\d+) ")
PERIODS = [(0, 600), (600, 1500), (1500, 3000), (3000, 10 ** 9)]
BATCH_GAPS = {}


def plabel(p):
    return f"{p[0]}~{p[1]}" if p[1] < 10 ** 9 else f"{p[0]}+"


def load_game(mid):
    allow = set()
    pmap = {}
    for ln in open(os.path.join(ROOT, mid, "squad_players.tsv"), encoding="utf-8"):
        c = ln.rstrip("\n").split("\t")
        if len(c) == 2 and c[0].isdigit():
            allow.add(c[1])
            pmap[c[0]] = c[1]
    snaps = defaultdict(dict)
    disp = defaultdict(list)
    with open(os.path.join(DATA, "bundles", mid, "in_game.log"), encoding="utf-8", errors="replace") as f:
        for ln in f:
            m = TICK_RE.match(ln)
            if m:
                if m.group(1) in allow:
                    snaps[m.group(1)][int(m.group(2))] = int(m.group(3))
                continue
            m = DISP_RE.match(ln)
            if m and m.group(1) in allow:
                disp[m.group(1)].append(int(m.group(2)))
    land = defaultdict(list)
    with open(os.path.join(ROOT, mid, "humans_cmd.tsv"), newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if r["squad"] == "1" and r["p"] in pmap:
                land[pmap[r["p"]]].append(int(r["t"]))
    for b in land:
        land[b].sort()
    for b in disp:
        disp[b].sort()
    wins = []   # (bot, t0, t1, issued, landed, dispatches)
    for b, sn in snaps.items():
        ts = sorted(sn)
        for a, z in zip(ts, ts[1:]):
            if z - a != 90 or sn[z] < sn[a]:
                continue
            lt = land.get(b, [])
            dp = disp.get(b, [])
            wins.append((b, a, z, sn[z] - sn[a], bisect.bisect_right(lt, z) - bisect.bisect_right(lt, a), bisect.bisect_right(dp, z) - bisect.bisect_right(dp, a)))
    # 同一个号相邻两个 ≥8 条的批（中间零星落地 ≤2 条）：(后一个批的落地拍, 间隔的回合数)
    BATCH_GAPS[mid] = []
    for b, lt in land.items():
        cnt = defaultdict(int)
        for t in lt:
            cnt[t] += 1
        last, between = None, 0
        for t in sorted(cnt):
            if cnt[t] >= 8:
                if last is not None and between <= 2:
                    BATCH_GAPS[mid].append((t, (t - last) // 7))
                last, between = t, 0
            else:
                between += cnt[t]
    return wins


def binned(rows, edges, key):
    out = []
    for lo, hi in edges:
        sel = [r for r in rows if lo <= key(r) <= hi]
        out.append(((lo, hi), sel))
    return out


def main():
    games = [r for r in csv.DictReader(open(os.path.join(CROSS, "exec_census.tsv"), encoding="utf-8"), delimiter="\t") if r["atkIssued"]]
    all_w = []
    per_game = []
    for g in games:
        mid = g["matchId"]
        w = load_game(mid)
        all_w += [(mid,) + x for x in w]
        team = defaultdict(lambda: [0, 0, 0, 0])
        for b, a, z, i, l, d in w:
            t = team[(a, z)]
            t[0] += i
            t[1] += l
            t[2] += d
            t[3] += 1
        per_game.append((g, w, team))

    L = []
    P = L.append
    P(f"# 发令快慢 vs 落地（58_throughput.py）：{len(games)} 局能对账的对局包，{len(all_w):,} 个「号 × 90 拍」窗口")
    P("")
    P("## A. 单个号的 90 拍窗口（窗口里没有捐款的）：窗口里发出几条 | 窗口数 | 发出合计 | 落地合计 | 落地 ÷ 发出 | 落地条数的中位 / P90 / 最大")
    nod = [r for r in all_w if r[6] == 0]
    edges = [(0, 0), (1, 2), (3, 5), (6, 9), (10, 14), (15, 24), (25, 39), (40, 10 ** 6)]
    for (lo, hi), sel in binned(nod, edges, lambda r: r[4]):
        if not sel:
            continue
        si, sl = sum(r[4] for r in sel), sum(r[5] for r in sel)
        ls = sorted(r[5] for r in sel)
        lab = f"{lo}" if lo == hi else (f"{lo}~{hi}" if hi < 10 ** 6 else f"≥{lo}")
        P(f"  {lab}\t{len(sel):,}\t{si:,}\t{sl:,}\t{(sl / si if si else 0):.2f}\t{statistics.median(ls):.0f} / {ls[int(0.9 * (len(ls) - 1))]} / {ls[-1]}")
    P(f"  （有捐款的窗口另有 {len(all_w) - len(nod):,} 个，不在上表）")
    P("")
    P("## B. 同上，按时段（窗口起点）：时段 | 发出 ≤5 条的窗口：发出 / 落地（比）| 发出 6~14 条：发出 / 落地（比）| 发出 ≥15 条：发出 / 落地（比）")
    for p in PERIODS:
        cells = []
        for lo, hi in ((0, 5), (6, 14), (15, 10 ** 6)):
            sel = [r for r in nod if p[0] <= r[2] < p[1] and lo <= r[4] <= hi]
            si, sl = sum(r[4] for r in sel), sum(r[5] for r in sel)
            cells.append(f"{si:,} / {sl:,}（{(sl / si if si else 0):.2f}，{len(sel):,} 窗）")
        P(f"  {plabel(p)}\t" + "\t".join(cells))
    P("")
    P("## C. 全队的 90 拍窗口：全队发出几条 | 窗口数 | 发出合计 | 落地合计 | 落地 ÷ 发出 | 全队落地条数的中位 / P90 / 最大")
    tw = [(g["matchId"], a, z, v[0], v[1], v[2], v[3]) for g, w, team in per_game for (a, z), v in team.items()]
    edges = [(0, 9), (10, 19), (20, 39), (40, 59), (60, 89), (90, 129), (130, 10 ** 6)]
    for (lo, hi), sel in binned(tw, edges, lambda r: r[3]):
        if not sel:
            continue
        si, sl = sum(r[3] for r in sel), sum(r[4] for r in sel)
        ls = sorted(r[4] for r in sel)
        lab = f"{lo}~{hi}" if hi < 10 ** 6 else f"≥{lo}"
        P(f"  {lab}\t{len(sel):,}\t{si:,}\t{sl:,}\t{(sl / si if si else 0):.2f}\t{statistics.median(ls):.0f} / {ls[int(0.9 * (len(ls) - 1))]} / {ls[-1]}")
    P("  （全队窗口里的发出和落地都含捐款）")
    P("")
    P("## D. 单个号一个窗口最多落地几条（全部窗口）")
    ls = sorted(r[5] for r in all_w)
    cnt = defaultdict(int)
    for x in ls:
        cnt["0" if x == 0 else "1~4" if x <= 4 else "5~9" if x <= 9 else "10~18" if x <= 18 else "19~27" if x <= 27 else "≥28"] += 1
    P("  落地条数分布（窗口数）：" + "、".join(f"{k} 条 {cnt[k]:,}" for k in ("0", "1~4", "5~9", "10~18", "19~27", "≥28")) + f"；最大 {ls[-1]}")
    top = sorted(all_w, key=lambda r: -r[5])[:8]
    P("  落地最多的窗口：" + "、".join(f"{m} {b} ({a}, {z}] 落地 {l}（发出 {i}）" for m, b, a, z, i, l, d in top))
    P("")
    P("## E. 逐局：600~3000 拍里全队每 90 拍发出的条数（中位 / 最大）和落地的条数（中位 / 最大）| 这一段发出合计 / 落地合计（比）；按落地比从低到高，只列前 25 局和后 10 局")
    rows = []
    for g, w, team in per_game:
        sel = [(a, v) for (a, z), v in team.items() if 600 <= a < 3000]
        if len(sel) < 5:
            continue
        iss = sorted(v[0] for a, v in sel)
        lan = sorted(v[1] for a, v in sel)
        si, sl = sum(iss), sum(lan)
        rows.append((sl / si if si else 1, g["matchId"], g["result"], g["humans"], g["bots"], statistics.median(iss), iss[-1], statistics.median(lan), lan[-1], si, sl, len(sel)))
    rows.sort()
    with open(os.path.join(CROSS, "throughput_games.tsv"), "w", encoding="utf-8") as f:
        f.write("matchId\tresult\thumans\tbots\twindows\tissuedMedianPer90\tissuedMaxPer90\tlandedMedianPer90\tlandedMaxPer90\tissued600_3000\tlanded600_3000\tratio\n")
        for ratio, mid, res, hum, bots, im, ix, lm, lx, si, sl, n in rows:
            f.write(f"{mid}\t{res}\t{hum}\t{bots}\t{n}\t{im:.0f}\t{ix}\t{lm:.0f}\t{lx}\t{si}\t{sl}\t{ratio:.3f}\n")
    for ratio, mid, res, hum, bots, im, ix, lm, lx, si, sl, n in rows[:25] + rows[-10:]:
        P(f"  {mid}（{res}，真人位 {hum}，在场 {bots} 个号）\t发出 {im:.0f} / {ix}\t落地 {lm:.0f} / {lx}\t{si:,} / {sl:,}（{ratio:.2f}）")
    P("")
    P("## F. 逐局的发令速度和落地比（600~3000 拍，全队每 90 拍发出条数的中位数分档）：档 | 局数 | 发出合计 | 落地合计 | 落地 ÷ 发出 | 各局落地比的最小 / 中位 / 最大")
    for lo, hi in ((0, 19), (20, 29), (30, 39), (40, 59), (60, 10 ** 6)):
        sel = [r for r in rows if lo <= r[5] <= hi]
        if not sel:
            continue
        si, sl = sum(r[9] for r in sel), sum(r[10] for r in sel)
        rs = sorted(r[0] for r in sel)
        lab = f"{lo}~{hi}" if hi < 10 ** 6 else f"≥{lo}"
        P(f"  {lab}\t{len(sel)}\t{si:,}\t{sl:,}\t{sl / si:.2f}\t{rs[0]:.2f} / {statistics.median(rs):.2f} / {rs[-1]:.2f}")
    P("")
    P("## G. 真人位多少和落地比（600~3000 拍）：真人位 | 局数 | 发出合计 | 落地合计 | 落地 ÷ 发出 | 各局落地比的最小 / 中位 / 最大 | 全队每 90 拍发出条数的中位（各局的中位）")
    for lo, hi in ((0, 25), (26, 50), (51, 80), (81, 10 ** 6)):
        sel = [r for r in rows if lo <= int(r[3]) <= hi]
        if not sel:
            continue
        si, sl = sum(r[9] for r in sel), sum(r[10] for r in sel)
        rs = sorted(r[0] for r in sel)
        lab = f"{lo}~{hi}" if hi < 10 ** 6 else f"≥{lo}"
        P(f"  {lab}\t{len(sel)}\t{si:,}\t{sl:,}\t{sl / si:.2f}\t{rs[0]:.2f} / {statistics.median(rs):.2f} / {rs[-1]:.2f}\t{statistics.median([r[5] for r in sel]):.0f}")

    P("")
    P("## H. 单个号的窗口，逐条看（这一窗和上一窗都没有捐款、两窗相连）：这一窗发出 k 条 | 上一窗发出 ≤2 条的：窗口数、平均落地、落地 ÷ 发出、一条都没落地的窗口占比 | 上一窗发出 ≥3 条的：同样四项")
    seq = defaultdict(list)
    for m, b, a, z, i, l, d in all_w:
        seq[(m, b)].append((a, z, i, l, d))
    by = defaultdict(list)
    for ws in seq.values():
        ws.sort()
        for p0, c in zip(ws, ws[1:]):
            if c[0] == p0[1] and c[4] == 0 and p0[4] == 0:
                by[("calm" if p0[2] <= 2 else "busy", min(c[2], 19))].append(c[3])
    for k in range(0, 20):
        cells = []
        for tag in ("calm", "busy"):
            v = by.get((tag, k), [])
            if len(v) < 5:
                cells.append("（不足 5 个窗口）")
                continue
            mean = sum(v) / len(v)
            cells.append(f"{len(v):,} 窗、{mean:.2f}、{(mean / k if k else 0):.2f}、{sum(1 for x in v if x == 0) / len(v):.0%}")
        P(f"  {k if k < 19 else '≥19'}\t" + "\t".join(cells))
    P("")
    P("## I. 逐个号（一局一个号算一个）：这个号发出的指令里有多少是在「一窗发出 ≥10 条」的窗口里发的 | 号次 | 发出合计 | 落地合计 | 落地 ÷ 发出")
    bg = []
    for (m, b), ws0 in seq.items():
        ws = [w for w in ws0 if w[4] == 0]
        tot_i = sum(w[2] for w in ws)
        if tot_i < 20:
            continue
        fast = sum(w[2] for w in ws if w[2] >= 10)
        bg.append((fast / tot_i, tot_i, sum(w[3] for w in ws)))
    for lo, hi, lab in ((0, 0.0001, "0"), (0.0001, 0.2, "0~20%"), (0.2, 0.4, "20%~40%"), (0.4, 0.6, "40%~60%"), (0.6, 0.8, "60%~80%"), (0.8, 1.01, "≥80%")):
        sel = [x for x in bg if lo <= x[0] < hi]
        if not sel:
            continue
        si, sl = sum(x[1] for x in sel), sum(x[2] for x in sel)
        P(f"  {lab}\t{len(sel)}\t{si:,}\t{sl:,}\t{sl / si:.2f}")
    P("  （只算有相邻 HL-TICK、且窗口里没有捐款的窗口；这样的窗口里发出不足 20 条的号次不列）")
    k18 = [r for r in all_w if r[4] >= 17 and r[6] == 0]
    P(f"  一窗发出 ≥17 条（差不多每个决策拍一条）且没有捐款的窗口：{len(k18):,} 个，发出 {sum(r[4] for r in k18):,}、落地 {sum(r[5] for r in k18):,}；分布在 {len({r[0] for r in k18})} 局、{len({(r[0], r[1]) for r in k18})} 个号次")

    P("")
    P("## I2. 逐个号（一局一个号算一个）在 600~3000 拍里：这个号发出合计分档（只算起点在 600~3000、没有捐款的窗口；这样的窗口不足 10 个的号次不列）")
    P("   发出合计 | 号次 | 发出合计 | 落地合计 | 落地 ÷ 发出 | 每个号落地条数的中位 / P90 / 最大")
    bl = []
    for (m, b), ws0 in seq.items():
        ws = [w for w in ws0 if w[4] == 0 and 600 <= w[0] < 3000]
        if len(ws) >= 10:
            bl.append((sum(w[2] for w in ws), sum(w[3] for w in ws), m, b))
    for lo, hi in ((0, 19), (20, 39), (40, 79), (80, 149), (150, 249), (250, 10 ** 6)):
        sel = [x for x in bl if lo <= x[0] <= hi]
        if not sel:
            continue
        si, sl = sum(x[0] for x in sel), sum(x[1] for x in sel)
        ls = sorted(x[1] for x in sel)
        lab = f"{lo}~{hi}" if hi < 10 ** 6 else f"≥{lo}"
        P(f"  {lab}\t{len(sel)}\t{si:,}\t{sl:,}\t{(sl / si if si else 0):.2f}\t{statistics.median(ls):.0f} / {ls[int(0.9 * (len(ls) - 1))]} / {ls[-1]}")
    topl = sorted(bl, key=lambda x: -x[1])[:5]
    P("  落地最多的 5 个号次：" + "、".join(f"{m} {b}（发出 {i}、落地 {l}）" for i, l, m, b in topl))

    P("")
    P("## J. 逐局的「连发窗口」（单个号一窗发出 ≥10 条、窗口里没有捐款）：局 | 这样的窗口数（其中 ≥17 条的）| 窗口里发出 / 落地 | 按窗口起点分 0~600 / 600~1500 / 1500~3000 / 3000+ 的窗口数 | 涉及的号数")
    fl = defaultdict(list)
    for r in all_w:
        if r[4] >= 10 and r[6] == 0:
            fl[r[0]].append(r)
    with open(os.path.join(CROSS, "throughput_flood.tsv"), "w", encoding="utf-8") as f:
        f.write("matchId\tresult\tfloodWindows\tfloodWindowsGe17\tissuedInFlood\tlandedInFlood\tw0_600\tw600_1500\tw1500_3000\tw3000\tbots\n")
        for g in games:
            ws = fl.get(g["matchId"], [])
            per = [sum(1 for r in ws if p[0] <= r[2] < p[1]) for p in PERIODS]
            f.write(f"{g['matchId']}\t{g['result']}\t{len(ws)}\t{sum(1 for r in ws if r[4] >= 17)}\t{sum(r[4] for r in ws)}\t{sum(r[5] for r in ws)}\t" + "\t".join(str(x) for x in per) + f"\t{len({r[1] for r in ws})}\n")
    mine = ["A062", "A033", "A039", "A079", "A061", "A053", "A091", "A089", "A082", "A007", "A070"]
    for mid in mine:
        ws = fl.get(mid, [])
        per = [sum(1 for r in ws if p[0] <= r[2] < p[1]) for p in PERIODS]
        P(f"  {mid}\t{len(ws)}（{sum(1 for r in ws if r[4] >= 17)}）\t{sum(r[4] for r in ws):,} / {sum(r[5] for r in ws):,}\t" + " / ".join(str(x) for x in per) + f"\t{len({r[1] for r in ws})}")
    allfl = [r for ws in fl.values() for r in ws]
    P(f"  全部 {len(games)} 局\t{len(allfl):,}（{sum(1 for r in allfl if r[4] >= 17):,}）\t{sum(r[4] for r in allfl):,} / {sum(r[5] for r in allfl):,}\t"
      + " / ".join(str(sum(1 for r in allfl if p[0] <= r[2] < p[1])) for p in PERIODS) + f"\t有这种窗口的局 {len(fl)} 局")
    nz = sorted(((len(ws), m) for m, ws in fl.items()), reverse=True)
    P("  这种窗口最多的 15 局：" + "、".join(f"{m}（{n}）" for n, m in nz[:15]))
    P("  （只列我逐局复盘过的 11 局带录像的局；全部局在 throughput_flood.tsv）")

    P("")
    P("## K. 同一个 90 拍窗口里，队友在连发时，发得慢的号怎么样（慢号 = 这一窗发出 1~5 条、没有捐款）")
    P("   同窗队友的情况 | 时段 | 慢号窗口数 | 发出 / 落地（比）| 一条都没落地的窗口占比")
    res = defaultdict(lambda: [0, 0, 0, 0])
    for g, w, team in per_game:
        tw2 = defaultdict(list)
        for b, a, z, i, l, d in w:
            tw2[(a, z)].append((b, i, l, d))
        for (a, z), ws in tw2.items():
            stalled = any(x[1] >= 15 and x[2] <= 1 and x[3] == 0 for x in ws)
            fast_ok = any(x[1] >= 15 and x[2] >= 6 and x[3] == 0 for x in ws)
            tag = "有队友发 ≥15 条、落地 ≤1 条" if stalled else ("有队友发 ≥15 条、落地 ≥6 条" if fast_ok else "没有队友发 ≥15 条")
            for b, i, l, d in ws:
                if d == 0 and 1 <= i <= 5:
                    for p in PERIODS:
                        if p[0] <= a < p[1]:
                            r = res[(tag, plabel(p))]
                            r[0] += 1
                            r[1] += i
                            r[2] += l
                            r[3] += 1 if l == 0 else 0
    for tag in ("没有队友发 ≥15 条", "有队友发 ≥15 条、落地 ≥6 条", "有队友发 ≥15 条、落地 ≤1 条"):
        for p in PERIODS:
            r = res.get((tag, plabel(p)))
            if r and r[0] >= 20:
                P(f"  {tag}\t{plabel(p)}\t{r[0]:,}\t{r[1]:,} / {r[2]:,}（{r[2] / r[1]:.2f}）\t{r[3] / r[0]:.0%}")
    P("  （不足 20 个窗口的格子不列）")

    P("")
    P("## M. 同一个号相邻两个 ≥8 条的批隔几个回合，和全队当时发得多少的关系（后一个批落在 600~3000 拍；全队发出 = 后一个批所在的 90 拍窗口里全队 cmds 的增量）")
    P("   全队这一窗发出 | 对数 | 间隔（回合）中位 / P90 | 涉及的局数")
    mg = []
    for g, w, team in per_game:
        mid = g["matchId"]
        for t, gap in BATCH_GAPS.get(mid, []):
            if not (600 <= t < 3000):
                continue
            a = (t - 1) // 90 * 90
            v = team.get((a, a + 90))
            if v:
                mg.append((v[0], gap, mid))
    for lo, hi in ((0, 19), (20, 39), (40, 79), (80, 129), (130, 10 ** 6)):
        sel = sorted(x[1] for x in mg if lo <= x[0] <= hi)
        if not sel:
            continue
        lab = f"{lo}~{hi}" if hi < 10 ** 6 else f"≥{lo}"
        P(f"  {lab}\t{len(sel)}\t{statistics.median(sel):.0f} / {sel[int(0.9 * (len(sel) - 1))]}\t{len({x[2] for x in mg if lo <= x[0] <= hi})}")
    P(f"  （合计 {len(mg)} 对；只算能对账的局）")

    os.makedirs(CROSS, exist_ok=True)
    open(os.path.join(CROSS, "throughput.txt"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
