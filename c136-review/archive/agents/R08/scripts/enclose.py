#!/usr/bin/env python3
"""enclose.py — 编队号互相围死的硬账（真值：out/<局>/resim.json 的 sq[号].nb，每 30 拍一个边界采样）。

    python3 enclose.py <matchId> [--quiet]      # 写 out/<matchId>/enclose.txt 和 enclose_sum.json

为什么要它：c110 的 analyze L420-448 把 isProtectedSquadMate 为真的邻居从 nb 里去掉（L440）；isProtectedSquadMate L3993-3996 =
同队 或（场上还有野人 且 名字在名字池里）。编队被拆进几个队、落点又挨着时，一个号的边界可以全是「不能打的人」。
本脚本只数事实：每个采样点上这个号的边界朝着谁、有没有可打的出口。

口径：
  · 边界格分类：无主地｜内置 AI（内置 AI 分队的局里，同队 AI 另算，不可打）｜敌队野人（含空壳）｜异队编队友（受保护）｜
    同队真人（编队友 / 野人，引擎就不让打）｜同房另一支编队的号（单列，不算出口也不算受保护）。
  · 围死（sealed）= 这个号还有地，边界上 无主地 + 可打的内置 AI + 敌队野人 = 0。
      A 类：边界上有异队编队友（要是能打它，就有出口）；B 类：边界上只有同队的人；C 类：四周只有水（没有任何邻居）。
  · 保护开关：场上还有『不在编队名单里、领土 ≥80』的真人（含空壳）时为开（hasWildOutsidersAlive L3978-3990）。
节：
  [EA] 逐号：采样数、围死的采样数（A / B / C）、最长的一段 A 类围死（起止拍、地、兵、密度）、围死期间已执行的指令（陆攻 / 船 / 捐款）
  [EB] 时间线（每 270 拍）：在场号数、A / B / C 类围死的号数、围死号的地 / 兵占编队的比例、其中密度 ≥100 的号数、保护开关
  [EC] 异队编队友接壤对：接壤的采样数、首末拍、最大接壤格数、这期间两边各自 A 类围死的采样数
  [ED] 编队整条边界朝着谁（每 540 拍，按接壤格数）：无主地 / 内置 AI / 敌队野人 / 异队编队友 / 同队真人
  [EE] A 类围死的号·拍里的兵：利息照滚的本金、围死期间船带走的兵和手续费、捐出去的兵和税
"""
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from truth import Truth, NEUTRAL, OUT  # noqa: E402


def classify(T, me, lst, t):
    """返回 dict(neutral, ai, teamAi, foe, mateX, own, peer) 的接壤格数，外加异队编队友的明细。"""
    c = dict(neutral=0, ai=0, teamAi=0, foe=0, mateX=0, own=0, peer=0)
    mates = []
    tm = T.team(me)
    for q, n in lst:
        if q >= NEUTRAL:
            c["neutral"] += n
        elif q >= T.H:
            if T.botsTeamed and T.team(q) == tm:
                c["teamAi"] += n
            else:
                c["ai"] += n
        elif T.same(q, me):
            c["own"] += n
        elif q in T.sqIds:
            c["mateX"] += n
            mates.append((q, n))
        elif q in T.peerIds:
            c["peer"] += n
        else:
            c["foe"] += n
    return c, mates


def seal_kind(c):
    if c["neutral"] + c["ai"] + c["foe"] > 0:
        return ""
    if c["mateX"] > 0:
        return "A"
    if c["own"] + c["teamAi"] + c["peer"] > 0:
        return "B"
    return "C"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    quiet = "--quiet" in sys.argv
    mid = args[0]
    T = Truth(mid)
    R = T.R
    id2name = {p: n for n, p in T.squad.items()}
    wild = [p for p in range(T.H) if p not in T.sqIds and p not in T.peerIds]

    def wild_alive(t):
        i = T.at(t)
        row = R["snapTerr"][i]
        return any(row[p] >= 80 and T.alive(p, t) for p in wild)

    # 每个号的采样
    samp = {}   # name -> list of (t, terr, bal, cls, kind, mates)
    for name, me in T.squad.items():
        o = T.sq_of(name)
        rows = []
        for t, lst in o["nb"]:
            if not T.alive(me, t):
                continue
            terr = T.terr(me, t)
            if terr <= 0:
                continue
            c, mates = classify(T, me, lst, t)
            rows.append((t, terr, T.bal(me, t), c, seal_kind(c), mates))
        samp[name] = rows

    cmds = defaultdict(list)   # player -> [(t, kind, row)]
    for r in R["cmdLog"]:
        if r[1] in T.sqIds and r[2] in (1, 2, 3):
            cmds[r[1]].append(r)

    out = []
    summ = dict(matchId=mid, step=30, perBot={}, timeline=[], pairs=[], border=[])
    protAll = all(wild_alive(t) for t in range(270, T.end, 270))
    out.append(f"[EA] {mid} 编队号互相围死（真值边界采样，每 30 拍一个点；本编队 {len(T.squad)} 个号，分在 {len(set(T.team(p) for p in T.sqIds))} 个队；"
               f"保护开关{'从 t=270 起全程开着（一直有领土 ≥80 的野人）' if protAll else '中途关过，见 [EB]'}）")
    out.append("  号 | 队 | 有地的采样数 | 围死的采样数 A（有异队编队友）/ B（只有同队）/ C（只有水）| A 类占比 | 最长一段 A 类：起止拍（拍数）| 地 起→止 | 兵 起→止 | 密度 起→止（最高）| 这一段已执行的 陆攻 / 船 / 捐款 条数 | 这一段贴着的异队编队友")
    totA = totN = 0
    for name, rows in sorted(samp.items(), key=lambda kv: -sum(1 for r in kv[1] if r[4] == "A")):
        me = T.squad[name]
        n = len(rows)
        nA = sum(1 for r in rows if r[4] == "A")
        nB = sum(1 for r in rows if r[4] == "B")
        nC = sum(1 for r in rows if r[4] == "C")
        totA += nA
        totN += n
        # 最长连续 A 段（允许中间断 1 个采样点）
        best = None
        cur = None
        gap = 0
        for r in rows:
            if r[4] == "A":
                if cur is None:
                    cur = [r, r, 1]
                else:
                    cur[1] = r
                    cur[2] += 1
                gap = 0
            elif cur is not None:
                gap += 1
                if gap > 1:
                    if best is None or cur[2] > best[2]:
                        best = cur
                    cur = None
                    gap = 0
        if cur is not None and (best is None or cur[2] > best[2]):
            best = cur
        rec = dict(team=T.team(me), samples=n, sealedA=nA, sealedB=nB, sealedC=nC)
        if best:
            a, b, k = best
            seg = [r for r in rows if a[0] <= r[0] <= b[0]]
            dmax = max(r[2] / max(r[1], 1) for r in seg)
            cl = [r for r in cmds[me] if a[0] <= r[0] <= b[0] + 30]
            nat = sum(1 for r in cl if r[2] == 1)
            nbo = sum(1 for r in cl if r[2] == 3)
            ndo = sum(1 for r in cl if r[2] == 2)
            mm = defaultdict(int)
            for r in seg:
                for q, c in r[5]:
                    mm[q] = max(mm[q], c)
            mates = " ".join(f"{id2name[q]}(T{T.team(q)}):{c}" for q, c in sorted(mm.items(), key=lambda kv: -kv[1]))
            out.append(f"    {name:<16} | T{T.team(me)} | {n} | {nA} / {nB} / {nC} | {100 * nA / max(n, 1):.0f}% | {a[0]}~{b[0]}（{b[0] - a[0] + 30}）| {a[1]}→{b[1]} | {a[2]}→{b[2]} | "
                       f"{a[2] / max(a[1], 1):.1f}→{b[2] / max(b[1], 1):.1f}（{dmax:.1f}）| {nat} / {nbo} / {ndo} | {mates}")
            rec.update(longestA=dict(t0=a[0], t1=b[0], ticks=b[0] - a[0] + 30, terr0=a[1], terr1=b[1], bal0=a[2], bal1=b[2], densMax=round(dmax, 1),
                                     landAtk=nat, boats=nbo, donations=ndo, mates=[id2name[q] for q in mm]))
        else:
            out.append(f"    {name:<16} | T{T.team(me)} | {n} | {nA} / {nB} / {nC} | {100 * nA / max(n, 1):.0f}% | –")
        summ["perBot"][name] = rec
    out.append(f"  合计：{totN} 个号·采样里 A 类围死 {totA} 个（{100 * totA / max(totN, 1):.1f}%）= {totA * 30} 号·拍；A 类围死过（≥10 个采样）的号 "
               f"{sum(1 for v in summ['perBot'].values() if v['sealedA'] >= 10)}/{len(samp)} 个")
    summ["total"] = dict(samples=totN, sealedA=totA, botTicksA=totA * 30, botsEverA=sum(1 for v in summ["perBot"].values() if v["sealedA"] >= 10))

    out.append("")
    out.append("[EB] 时间线（每 270 拍）：拍 | 有地的号数 | 围死的号数 A / B / C | A 类围死号的地合计（占编队地 %）| 兵合计（占编队兵 %）| A 类里密度 ≥100 的号数 | 保护开关 | A 类围死的号")
    bySamp = defaultdict(dict)
    for name, rows in samp.items():
        for r in rows:
            bySamp[r[0]][name] = r
    for t in sorted(bySamp):
        if t % 270:
            continue
        d = bySamp[t]
        A = [n for n, r in d.items() if r[4] == "A"]
        B = [n for n, r in d.items() if r[4] == "B"]
        C = [n for n, r in d.items() if r[4] == "C"]
        terrAll = sum(r[1] for r in d.values())
        balAll = sum(r[2] for r in d.values())
        tA = sum(d[n][1] for n in A)
        bA = sum(d[n][2] for n in A)
        hi = sum(1 for n in A if d[n][2] >= 100 * d[n][1])
        w = wild_alive(t)
        out.append(f"    {t:>5} | {len(d)} | {len(A)} / {len(B)} / {len(C)} | {tA}（{100 * tA / max(terrAll, 1):.0f}%）| {bA}（{100 * bA / max(balAll, 1):.0f}%）| {hi} | {'开' if w else '关'} | "
                   + " ".join(sorted(A, key=lambda n: -d[n][1])))
        summ["timeline"].append(dict(t=t, bots=len(d), A=len(A), B=len(B), C=len(C), terrA=tA, terrAll=terrAll, balA=bA, balAll=balAll, over100=hi, protect=w))

    out.append("")
    out.append("[EC] 异队编队友接壤对（接壤采样数最多的 20 对）：号 A(队) – 号 B(队) | 接壤的采样数（×30 拍）| 首末拍 | 最大接壤格数 | 这期间 A 被围死的采样数（A 类）| B 被围死的采样数 | 互打：A→B 格数 / 耗兵、B→A 格数 / 耗兵")
    pair = defaultdict(lambda: dict(n=0, t0=None, t1=None, mx=0, sa=0, sb=0))
    for name, rows in samp.items():
        me = T.squad[name]
        for r in rows:
            for q, c in r[5]:
                a, b = (me, q) if me < q else (q, me)
                e = pair[(a, b)]
                if me == a:
                    e["n"] += 1
                    e["t0"] = r[0] if e["t0"] is None else min(e["t0"], r[0])
                    e["t1"] = r[0] if e["t1"] is None else max(e["t1"], r[0])
                    e["mx"] = max(e["mx"], c)
                    if r[4] == "A":
                        e["sa"] += 1
                else:
                    if e["t0"] is None:
                        e["t0"] = e["t1"] = r[0]
                    e["t0"] = min(e["t0"], r[0])
                    e["t1"] = max(e["t1"], r[0])
                    e["mx"] = max(e["mx"], c)
                    if e["n"] == 0:
                        e["nb_only"] = e.get("nb_only", 0) + 1
                    if r[4] == "A":
                        e["sb"] += 1
    fight = defaultdict(lambda: [0, 0])
    for r in R["pairLog"]:
        a, q = r[1], r[2]
        if a in T.sqIds and q in T.sqIds and not T.same(a, q):
            fight[(a, q)][0] += r[3]
            fight[(a, q)][1] += r[4]
    npairs = 0
    for (a, b), e in sorted(pair.items(), key=lambda kv: -max(kv[1]["n"], kv[1].get("nb_only", 0))):
        n = max(e["n"], e.get("nb_only", 0))
        if n < 3:
            continue
        npairs += 1
        fa, fb = fight[(a, b)], fight[(b, a)]
        summ["pairs"].append(dict(a=id2name[a], b=id2name[b], samples=n, t0=e["t0"], t1=e["t1"], maxCells=e["mx"], sealedA=e["sa"], sealedB=e["sb"],
                                  aToB=fa, bToA=fb))
        if npairs <= 20:
            out.append(f"    {id2name[a]}(T{T.team(a)}) – {id2name[b]}(T{T.team(b)}) | {n}（{n * 30} 拍）| {e['t0']}~{e['t1']} | {e['mx']} | {e['sa']} | {e['sb']} | "
                       f"{fa[0]} / {fa[1]}、{fb[0]} / {fb[1]}")
    out.append(f"  接壤过 ≥3 个采样的异队编队友对：{npairs} 对（编队共 {len(samp)} 个号）")
    summ["pairCount"] = npairs

    out.append("")
    out.append("[ED] 编队整条边界朝着谁（每 540 拍，按接壤格数；括号里是占比）：拍 | 号数 | 无主地 | 内置 AI | 敌队野人 | 异队编队友 | 同队真人 | 同队 AI / 另一支编队")
    for t in sorted(bySamp):
        if t % 540:
            continue
        d = bySamp[t]
        tot = defaultdict(int)
        for r in d.values():
            for k, v in r[3].items():
                tot[k] += v
        s = sum(tot.values()) or 1
        out.append(f"    {t:>5} | {len(d)} | {tot['neutral']}（{100 * tot['neutral'] / s:.0f}%）| {tot['ai']}（{100 * tot['ai'] / s:.0f}%）| {tot['foe']}（{100 * tot['foe'] / s:.0f}%）| "
                   f"{tot['mateX']}（{100 * tot['mateX'] / s:.0f}%）| {tot['own']}（{100 * tot['own'] / s:.0f}%）| {tot['teamAi'] + tot['peer']}")
        summ["border"].append(dict(t=t, bots=len(d), **{k: tot[k] for k in ("neutral", "ai", "foe", "mateX", "own", "teamAi", "peer")}))

    out.append("")
    out.append("[EE] A 类围死期间的兵（逐号；只算围死采样点前后 30 拍内已执行的指令）：号 | 围死号·拍 | 发船 条数 / 船上兵 / 手续费（其中手续费 > 船上兵的条数）| 捐款 笔数 / 到账 / 税 | 陆攻 条数 / 生效 / 派出的兵 | 围死期间地 最小~最大 | 密度 ≥100 的采样数 / 顶 150 硬上限的采样数")
    tb = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    for name, rows in sorted(samp.items(), key=lambda kv: -sum(1 for r in kv[1] if r[4] == "A")):
        me = T.squad[name]
        At = set(r[0] for r in rows if r[4] == "A")
        if len(At) < 10:
            continue
        seg = [r for r in rows if r[0] in At]

        def insealed(t):
            base = (t // 30) * 30
            return base in At or base + 30 in At
        cl = [r for r in cmds[me] if insealed(r[0])]
        bo = [r for r in cl if r[2] == 3]
        do = [r for r in cl if r[2] == 2 and r[5]]
        at = [r for r in cl if r[2] == 1]
        bt = sum(r[6] for r in bo)
        bf = sum(r[7] for r in bo)
        bhi = sum(1 for r in bo if r[7] > r[6])
        dg = sum(r[6] for r in do)
        dt = sum(r[7] for r in do)
        aok = sum(1 for r in at if r[5])
        atr = sum(r[6] for r in at if r[5])
        over = sum(1 for r in seg if r[2] >= 100 * r[1])
        hard = sum(1 for r in seg if r[2] >= 150 * r[1] - 1)
        out.append(f"    {name:<16} | {len(At) * 30} | {len(bo)} / {bt} / {bf}（{bhi}）| {len(do)} / {dg} / {dt} | {len(at)} / {aok} / {atr} | {min(r[1] for r in seg)}~{max(r[1] for r in seg)} | {over} / {hard}")
        for i, v in enumerate((len(At) * 30, len(bo), bt, bf, bhi, len(do), dg, dt, over, hard)):
            tb[i] += v
        summ["perBot"][name]["inSealA"] = dict(botTicks=len(At) * 30, boats=len(bo), boatTroops=bt, boatFees=bf, boatsFeeOverTroops=bhi, donations=len(do), donArrived=dg, donTax=dt,
                                               landAtk=len(at), landAtkOk=aok, landAtkTroops=atr, over100=over, hardCap=hard)
    out.append(f"  合计：{tb[0]} 号·拍｜船 {tb[1]} 条、船上兵 {tb[2]}、手续费 {tb[3]}（手续费 > 船上兵的 {tb[4]} 条）｜捐款 {tb[5]} 笔、到账 {tb[6]}、税 {tb[7]}｜密度 ≥100 的采样 {tb[8]} 个、顶硬上限 {tb[9]} 个")
    summ["inSealA"] = dict(botTicks=tb[0], boats=tb[1], boatTroops=tb[2], boatFees=tb[3], boatsFeeOverTroops=tb[4], donations=tb[5], donArrived=tb[6], donTax=tb[7], over100=tb[8], hardCap=tb[9])

    txt = "\n".join(out) + "\n"
    with open(os.path.join(OUT, mid, "enclose.txt"), "w", encoding="utf-8") as f:
        f.write(txt)
    with open(os.path.join(OUT, mid, "enclose_sum.json"), "w", encoding="utf-8") as f:
        json.dump(summ, f, ensure_ascii=False, indent=1)
    if quiet:
        print(f"{mid}: enclose.txt {len(out)} 行")
    else:
        print(txt)


if __name__ == "__main__":
    main()
