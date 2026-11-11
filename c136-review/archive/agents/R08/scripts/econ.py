#!/usr/bin/env python3
"""econ.py — 兵的总账（真值）：产兵、花在哪、漏在哪。本编队 对 同房其他真人，按时段、按人头。

    python3 econ.py <matchId> [--quiet] [时段边界，默认 0,600,1500,3000,4284,6300,99999]
    写 out/<matchId>/econ.txt 和 econ_sum.json

依据 out/<局>/resim.json：snapInc（利息 + 地租的累计入账，引擎 economyTick 前后余额之差）、snapRet（进攻结束退回余额的兵）、
cmdLog（已执行的陆攻 / 船 / 捐款）、pairLog（逐对战损）、snapTerr / snapBal（每 10 拍）。

引擎规则（src/sim/sim/game.js）：
  · economyTick L778-791：每 10 拍 余额 += ⌊利率 × 余额 / 10000⌋；每 100 拍再 += 领土。
  · interestRate L739-746：利率 = 100 + √(25600×占地序号/508)（占地越大越高，100~260）；t<1920 时不低于 100×(13440−6t)/1920；
    余额 > 100×领土 时 利率 −= 2×利率×(余额−上限)/上限（密度 150 时为 0）；addBalance L752-757 余额封顶 150×领土。
节：
  [NA] 时段 × 组：人头、产兵（利息+地租）、人均、每 1000 兵·拍 的产兵、超软上限少拿的利息（估）、顶硬上限的号·拍
  [NB] 时段 × 组：陆攻派出 / 退回 / 实际烧掉、船上兵 / 船费、捐款到账 / 税、挨打被打掉的余额；税费 ÷ 产兵
  [NC] 编队逐号整局：产兵、少拿的利息（估）、船费、捐款税、捐出到账、收到、挨打被打掉、烧在进攻里、末拍余额
  [ND] 时段末的存量：编队 / 其他真人的地、兵、密度；编队兵占全房真人兵的比例 对 地的比例
"""
import json
import math
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from truth import Truth, NEUTRAL, OUT  # noqa: E402

MAXP = 512


def isqrt_tbl():
    def iV(a, b):
        return math.floor((a + 0.5) / b)

    def mn(h, cs):
        a = iV(h + 1, 2)
        for _ in range(cs):
            a = iV(a + iV(h, a), 2)
        return a
    return [100 + (0 if iV(25600 * i, MAXP - 4) < 1 else mn(iV(25600 * i, MAXP - 4), 9)) for i in range(MAXP)]


TBL = isqrt_tbl()


def base_rate(terr, land, t):
    n1 = TBL[min(MAXP - 1, math.floor(((MAXP - 1) * terr + 0.5) / land))]
    if t < 1920:
        n1 = max(math.floor((100 * (13440 - 6 * t) + 0.5) / 1920), n1)
    return n1


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    quiet = "--quiet" in sys.argv
    mid = args[0]
    T = Truth(mid)
    R = T.R
    edges = [int(x) for x in (args[1].split(",") if len(args) > 1 else "0,600,1500,3000,4284,6300,99999".split(","))]
    edges = [min(e, T.end) for e in edges]
    edges = sorted(set(edges))
    snapT, terr, bal, inc, ret = R["snapT"], R["snapTerr"], R["snapBal"], R["snapInc"], R["snapRet"]
    H = T.H
    spawned = [p for p in range(H) if any(row[p] > 0 for row in terr[::30])]
    groups = {"编队": [p for p in spawned if p in T.sqIds], "其他真人": [p for p in spawned if p not in T.sqIds and p not in T.peerIds]}
    if T.peerIds:
        groups["另一支"] = [p for p in spawned if p in T.peerIds]
    gid = {}
    for g, ps in groups.items():
        for p in ps:
            gid[p] = g

    def period(t):
        for i in range(len(edges) - 1):
            if edges[i] <= t < edges[i + 1]:
                return i
        return len(edges) - 2

    nP = len(edges) - 1
    Z = lambda: [defaultdict(float) for _ in range(nP)]  # noqa: E731
    acc = {g: Z() for g in groups}
    per = defaultdict(lambda: defaultdict(float))   # 逐号整局

    # 产兵、退回、少拿的利息、兵·拍
    for i in range(1, len(snapT)):
        t = snapT[i]
        k = period(snapT[i - 1])
        dt = t - snapT[i - 1]
        for p in spawned:
            g = gid.get(p)
            if g is None:
                continue
            a = acc[g][k]
            d = inc[i][p] - inc[i - 1][p]
            a["inc"] += d
            a["ret"] += ret[i][p] - ret[i - 1][p]
            b0, l0 = bal[i - 1][p], terr[i - 1][p]
            if l0 > 0:
                a["balTicks"] += b0 * dt
                a["cellTicks"] += l0 * dt
                a["botTicks"] += dt
                cap = 100 * l0
                if b0 > cap:
                    n1 = base_rate(l0, T.land, snapT[i - 1])
                    cut = min(n1, math.floor((2 * n1 * (b0 - cap) + 0.5) / cap))
                    lost = cut * b0 / 1e4 * (dt / 10.0)
                    a["forgone"] += lost
                    a["overTicks"] += dt
                    if b0 >= 150 * l0 - 1:
                        a["hardTicks"] += dt
                    if p in T.sqIds:
                        per[p]["forgone"] += lost
                        per[p]["overTicks"] += dt
                        if b0 >= 150 * l0 - 1:
                            per[p]["hardTicks"] += dt
            if p in T.sqIds:
                per[p]["inc"] += d

    for r in R["cmdLog"]:
        p = r[1]
        g = gid.get(p)
        if g is None or r[2] not in (1, 2, 3):
            continue
        a = acc[g][period(r[0])]
        if r[2] == 1:
            a["atkN"] += 1
            if r[5]:
                a["atkOk"] += 1
                a["atkTroops"] += r[6]
                a["atkFee"] += r[7]
        elif r[2] == 3:
            a["boatN"] += 1
            a["boatTroops"] += r[6]
            a["boatFee"] += r[7]
            if r[7] > r[6]:
                a["boatHiN"] += 1
                a["boatHiFee"] += r[7]
            if p in T.sqIds:
                per[p]["boatFee"] += r[7]
                per[p]["boatTroops"] += r[6]
        elif r[2] == 2 and r[5]:
            a["donN"] += 1
            a["donGot"] += r[6]
            a["donTax"] += r[7]
            q = r[4]
            gq = gid.get(q)
            if gq is not None:
                acc[gq][period(r[0])]["donIn"] += r[6]
            if p in T.sqIds:
                per[p]["donTax"] += r[7]
                per[p]["donOut"] += r[6]
            if q in T.sqIds:
                per[q]["donIn"] += r[6]

    for r in R["pairLog"]:
        t, a_, q, tiles, burnt, dB, dC = r[0], r[1], r[2], r[3], r[4], r[5], r[6]
        k = period(max(0, t - 1))
        ga = gid.get(a_)
        if ga is not None:
            acc[ga][k]["burnt"] += burnt
            acc[ga][k]["tilesGot"] += tiles
            if a_ in T.sqIds:
                per[a_]["burnt"] += burnt
        gq = gid.get(q) if q < H else None
        if gq is not None:
            acc[gq][k]["hitBal"] += dB + dC
            acc[gq][k]["tilesLost"] += tiles
            if q in T.sqIds:
                per[q]["hitBal"] += dB + dC

    out = []
    summ = dict(matchId=mid, edges=edges, groups={g: len(ps) for g, ps in groups.items()}, periods=[], perBot={})
    out.append(f"[NA] {mid} 产兵（真值；利息 + 地租的入账）。出生的真人：" + "、".join(f"{g} {len(ps)}" for g, ps in groups.items())
               + "｜时段 | 组 | 产兵合计 | 人均（按出生人头）| 每 1000 兵·拍 产兵 | 每 1000 格·拍 产兵 | 超软上限少拿的利息（估；占 产兵+少拿 的）| 密度 ≥100 的号·拍（占有地号·拍 %）| 顶 150 硬上限的号·拍")
    for k in range(nP):
        rec = dict(t0=edges[k], t1=edges[k + 1])
        for g, ps in groups.items():
            a = acc[g][k]
            n = len(ps)
            out.append(f"    {edges[k]}~{edges[k + 1]} | {g} | {a['inc']:.0f} | {a['inc'] / max(n, 1):.0f} | {1000 * a['inc'] / max(a['balTicks'], 1):.2f} | {1000 * a['inc'] / max(a['cellTicks'], 1):.1f} | "
                       f"{a['forgone']:.0f}（{100 * a['forgone'] / max(a['inc'] + a['forgone'], 1):.1f}%）| {a['overTicks']:.0f}（{100 * a['overTicks'] / max(a['botTicks'], 1):.1f}%）| {a['hardTicks']:.0f}")
            rec[g] = {kk: round(v) for kk, v in a.items()}
            rec[g]["heads"] = n
        sq, ot = acc["编队"][k], acc["其他真人"][k]
        ns, no = len(groups["编队"]), len(groups["其他真人"])
        ratio = (sq["inc"] / max(ns, 1)) / max(ot["inc"] / max(no, 1), 1e-9)
        out.append(f"      → 编队人均产兵 ÷ 其他真人人均产兵 = {ratio:.2f}；编队产兵占全房真人的 {100 * sq['inc'] / max(sq['inc'] + ot['inc'], 1):.1f}%（人头 {100 * ns / max(ns + no, 1):.1f}%）")
        rec["incPerCapRatio"] = round(ratio, 3)
        summ["periods"].append(rec)

    out.append("")
    out.append("[NB] 兵花在哪（真值）：时段 | 组 | 陆攻 条数 / 生效 / 派出的兵 | 进攻结束退回余额 | 实际烧在进攻里（拿到的格）| 发船 条数 / 船上兵 / 船费（其中船费 > 船上兵的 条数 / 船费）| 捐款 笔数 / 到账 / 税 | 收到捐款 | 挨打被打掉的余额（丢的格）|（船费 + 捐款税）÷ 产兵")
    for k in range(nP):
        for g in groups:
            a = acc[g][k]
            leak = a["boatFee"] + a["donTax"]
            out.append(f"    {edges[k]}~{edges[k + 1]} | {g} | {a['atkN']:.0f} / {a['atkOk']:.0f} / {a['atkTroops']:.0f} | {a['ret']:.0f} | {a['burnt']:.0f}（{a['tilesGot']:.0f}）| "
                       f"{a['boatN']:.0f} / {a['boatTroops']:.0f} / {a['boatFee']:.0f}（{a['boatHiN']:.0f} / {a['boatHiFee']:.0f}）| {a['donN']:.0f} / {a['donGot']:.0f} / {a['donTax']:.0f} | {a['donIn']:.0f} | "
                       f"{a['hitBal']:.0f}（{a['tilesLost']:.0f}）| {100 * leak / max(a['inc'], 1):.1f}%")
    tot = {g: defaultdict(float) for g in groups}
    for g in groups:
        for k in range(nP):
            for kk, v in acc[g][k].items():
                tot[g][kk] += v
    for g in groups:
        a = tot[g]
        leak = a["boatFee"] + a["donTax"]
        out.append(f"    整局 | {g} | 产兵 {a['inc']:.0f}｜船费 {a['boatFee']:.0f}（{100 * a['boatFee'] / max(a['inc'], 1):.1f}%）｜捐款税 {a['donTax']:.0f}（{100 * a['donTax'] / max(a['inc'], 1):.1f}%）｜"
                   f"少拿的利息（估）{a['forgone']:.0f}（{100 * a['forgone'] / max(a['inc'], 1):.1f}%）｜烧在进攻里 {a['burnt']:.0f}（{100 * a['burnt'] / max(a['inc'], 1):.1f}%）｜"
                   f"挨打被打掉 {a['hitBal']:.0f}（{100 * a['hitBal'] / max(a['inc'], 1):.1f}%）｜（船费 + 捐款税）÷ 产兵 = {100 * leak / max(a['inc'], 1):.1f}%")
        summ.setdefault("total", {})[g] = {kk: round(v) for kk, v in a.items()}

    out.append("")
    out.append("[NC] 编队逐号整局（真值）：号 | 队 | 产兵 | 少拿的利息（估）| 密度 ≥100 的拍数 / 顶硬上限的拍数 | 船上兵 / 船费 | 捐出 到账 / 税 | 收到 | 烧在进攻里 | 挨打被打掉 |（船费 + 税）÷ 产兵")
    for name, p in sorted(T.squad.items(), key=lambda kv: -per[kv[1]]["inc"]):
        a = per[p]
        leak = a["boatFee"] + a["donTax"]
        out.append(f"    {name:<16} | T{T.team(p)} | {a['inc']:.0f} | {a['forgone']:.0f} | {a['overTicks']:.0f} / {a['hardTicks']:.0f} | {a['boatTroops']:.0f} / {a['boatFee']:.0f} | {a['donOut']:.0f} / {a['donTax']:.0f} | "
                   f"{a['donIn']:.0f} | {a['burnt']:.0f} | {a['hitBal']:.0f} | {100 * leak / max(a['inc'], 1):.0f}%")
        summ["perBot"][name] = {kk: round(v) for kk, v in a.items()}

    out.append("")
    out.append("[ND] 时段末的存量（真值）：拍 | 编队：还有地的号数 / 地 / 兵 / 密度 | 其他真人：同口径 | 编队占全房真人的 地 % / 兵 %")
    for e in edges[1:]:
        i = T.at(min(e, T.end))
        rowT, rowB = terr[i], bal[i]
        v = {}
        for g, ps in groups.items():
            alive = [p for p in ps if rowT[p] > 0]
            v[g] = (len(alive), sum(rowT[p] for p in alive), sum(rowB[p] for p in alive))
        s, o = v["编队"], v["其他真人"]
        out.append(f"    {snapT[i]:>5} | {s[0]} / {s[1]} / {s[2]} / {s[2] / max(s[1], 1):.1f} | {o[0]} / {o[1]} / {o[2]} / {o[2] / max(o[1], 1):.1f} | "
                   f"{100 * s[1] / max(s[1] + o[1], 1):.1f}% / {100 * s[2] / max(s[2] + o[2], 1):.1f}%")
        summ.setdefault("stock", []).append(dict(t=snapT[i], squad=s, others=o))

    txt = "\n".join(out) + "\n"
    with open(os.path.join(OUT, mid, "econ.txt"), "w", encoding="utf-8") as f:
        f.write(txt)
    with open(os.path.join(OUT, mid, "econ_sum.json"), "w", encoding="utf-8") as f:
        json.dump(summ, f, ensure_ascii=False, indent=1)
    if quiet:
        print(f"{mid}: econ.txt {len(out)} 行")
    else:
        print(txt)


if __name__ == "__main__":
    main()
