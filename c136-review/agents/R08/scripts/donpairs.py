#!/usr/bin/env python3
"""donpairs.py — 捐款的对子账（真值：out/<局>/resim.json 的 cmdLog 捐款行）：谁给谁、净流向、来回倒手、税。

    python3 donpairs.py <matchId> [--quiet]     # 写 out/<matchId>/donpairs.txt 和 donpairs_sum.json

捐款行：[拍, 捐出方, 2, pct, 收款方, 成交, 到账, 税, 捐出方余额, 捐出方领土, 额度已用, 额度上限, 点数, 收款方领土, 收款方余额]
引擎：transfer L388-401 税 = 捐出方余额的 64/1024（按全额余额收，和实际到账多少无关）；receiverRoom L340-345 到账 ≤ 150×收款方领土 − 收款方余额。
节：
  [YA] 合计与分段：笔数、到账、税、税 ÷ 到账；到账被收款方上限夹小的笔数（到账 < 捐出方余额×(pct+1)/1024 的 90%）
  [YB] 各队分支：成交笔数、到账、税、净转移（各对子净额的绝对值之和）、来回倒掉的（到账 − 净转移）、倒手占比
  [YC] 对子（按到账合计排序）：A→B 笔数 / 到账 / 税、B→A 笔数 / 到账 / 税、净额、600 拍内来回的次数
  [YD] 收款方当拍的状态：密度分档（<50 / 50~80 / 80~100 / 100~132 / ≥132）的笔数、到账、税；收款后 600 拍内阵亡的笔数、到账
  [YE] 捐出方当拍的状态：密度分档；捐完后捐出方密度（中位）；捐出方当拍是不是被异队编队友围死（要 enclose_sum.json）
  [YF] 逐号：捐出 笔数 / 到账 / 税、收到 笔数 / 到账、净额、净额 ÷ 自己的产兵（要 econ_sum.json）
"""
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from truth import Truth, OUT  # noqa: E402


def med(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2] if xs else 0


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    quiet = "--quiet" in sys.argv
    mid = args[0]
    T = Truth(mid)
    R = T.R
    id2name = {p: n for n, p in T.squad.items()}
    rows = [r for r in R["cmdLog"] if r[2] == 2 and r[1] in T.sqIds]
    ok = [r for r in rows if r[5]]
    out = []
    summ = dict(matchId=mid)

    def nm(p):
        return id2name.get(p, T.nm(p))

    def intended(r):
        return r[8] * (r[3] + 1) / 1024.0

    tot_got = sum(r[6] for r in ok)
    tot_tax = sum(r[7] for r in ok)
    clamp = [r for r in ok if r[6] < 0.9 * intended(r)]
    taxge = [r for r in ok if r[7] >= r[6]]
    out.append(f"[YA] {mid} 本编队捐款（真值）：录像里 {len(rows)} 笔，成交 {len(ok)} 笔，到账 {tot_got}，税 {tot_tax}（税 ÷ 到账 = {100 * tot_tax / max(tot_got, 1):.1f}%；捐出方合计付出 {tot_got + tot_tax}）")
    out.append(f"  到账被收款方的 150 倍上限夹小的（到账 < 本意的 90%）：{len(clamp)} 笔，本意 {sum(intended(r) for r in clamp):.0f}，到账 {sum(r[6] for r in clamp)}，税 {sum(r[7] for r in clamp)}｜"
               f"税 ≥ 到账的 {len(taxge)} 笔，到账 {sum(r[6] for r in taxge)}，税 {sum(r[7] for r in taxge)}")
    summ["total"] = dict(logged=len(rows), executed=len(ok), arrived=tot_got, tax=tot_tax, clamped=len(clamp), clampedArrived=sum(r[6] for r in clamp), clampedTax=sum(r[7] for r in clamp),
                         taxGeArrived=len(taxge))
    out.append("  时段（执行拍）| 成交笔数 | 到账 | 税 | 税 ÷ 到账 | 捐出方数 / 收款方数")
    edges = [0, 2142, 3213, 4284, 6300, 9000, T.end + 1]
    summ["periods"] = []
    for a, b in zip(edges, edges[1:]):
        rr = [r for r in ok if a <= r[0] < b]
        if not rr:
            continue
        g, x = sum(r[6] for r in rr), sum(r[7] for r in rr)
        out.append(f"    {a}~{min(b, T.end)} | {len(rr)} | {g} | {x} | {100 * x / max(g, 1):.0f}% | {len(set(r[1] for r in rr))} / {len(set(r[4] for r in rr))}")
        summ["periods"].append(dict(t0=a, t1=min(b, T.end), n=len(rr), arrived=g, tax=x))

    # 对子
    flow = defaultdict(lambda: dict(n=0, got=0, tax=0, ts=[]))
    for r in ok:
        e = flow[(r[1], r[4])]
        e["n"] += 1
        e["got"] += r[6]
        e["tax"] += r[7]
        e["ts"].append((r[0], r[6], r[7]))
    pairs = {}
    for (a, b), e in flow.items():
        k = (a, b) if a < b else (b, a)
        pairs.setdefault(k, {})[(a, b)] = e

    out.append("")
    out.append("[YB] 各队分支（捐款只能给同队）：队 | 编队号数 | 成交笔数 | 到账 | 税 | 净转移（各对子净额绝对值之和）| 来回倒掉的到账（到账 − 净转移）| 倒手占到账 % | 逐号净额之和为正的（净收款方）")
    summ["teams"] = {}
    byTeam = defaultdict(list)
    for r in ok:
        byTeam[T.team(r[1])].append(r)
    for tm in sorted(byTeam):
        rr = byTeam[tm]
        g, x = sum(r[6] for r in rr), sum(r[7] for r in rr)
        net = 0
        for k, d in pairs.items():
            if T.team(k[0]) != tm:
                continue
            ab = d.get((k[0], k[1]), dict(got=0))["got"]
            ba = d.get((k[1], k[0]), dict(got=0))["got"]
            net += abs(ab - ba)
        nb = defaultdict(int)
        for r in rr:
            nb[r[1]] -= r[6]
            nb[r[4]] += r[6]
        recv = " ".join(f"{nm(p)} +{v}" for p, v in sorted(nb.items(), key=lambda kv: -kv[1]) if v > 0)
        nBots = sum(1 for p in T.sqIds if T.team(p) == tm)
        out.append(f"    T{tm} | {nBots} | {len(rr)} | {g} | {x} | {net} | {g - net} | {100 * (g - net) / max(g, 1):.0f}% | {recv}")
        summ["teams"][f"T{tm}"] = dict(bots=nBots, n=len(rr), arrived=g, tax=x, netMoved=net, churned=g - net)
    allnet = sum(v["netMoved"] for v in summ["teams"].values())
    out.append(f"    合计：到账 {tot_got}，净转移 {allnet}（{100 * allnet / max(tot_got, 1):.0f}%），来回倒掉 {tot_got - allnet}（{100 * (tot_got - allnet) / max(tot_got, 1):.0f}%）；税 {tot_tax} = 净转移的 {100 * tot_tax / max(allnet, 1):.0f}%")
    summ["total"].update(netMoved=allnet, churned=tot_got - allnet)

    out.append("")
    out.append("[YC] 对子（到账合计最多的 24 对）：A – B（队）| A→B 笔数 / 到账 / 税 | B→A 笔数 / 到账 / 税 | 净额（+ = A 净给 B）| 600 拍内来回的次数（A→B 之后 600 拍内 B→A，或反过来）| 这些来回里较小一笔的到账合计 / 两笔的税合计")
    summ["pairs"] = []
    plist = []
    for k, d in pairs.items():
        ab = d.get((k[0], k[1]), dict(n=0, got=0, tax=0, ts=[]))
        ba = d.get((k[1], k[0]), dict(n=0, got=0, tax=0, ts=[]))
        # 来回：把两边的成交按时间合并，相邻方向相反且间隔 ≤600 记一次
        ev = sorted([(t, 0, g, x) for t, g, x in ab["ts"]] + [(t, 1, g, x) for t, g, x in ba["ts"]])
        pp = 0
        ppMin = 0
        ppTax = 0
        last = None
        for e in ev:
            if last is not None and e[1] != last[1] and e[0] - last[0] <= 600:
                pp += 1
                ppMin += min(e[2], last[2])
                ppTax += e[3] + last[3]
                last = None
            else:
                last = e
        plist.append((ab["got"] + ba["got"], k, ab, ba, pp, ppMin, ppTax))
    plist.sort(key=lambda x: -x[0])
    totPP = sum(x[4] for x in plist)
    totPPmin = sum(x[5] for x in plist)
    totPPtax = sum(x[6] for x in plist)
    for tot, k, ab, ba, pp, ppMin, ppTax in plist[:24]:
        out.append(f"    {nm(k[0])} – {nm(k[1])}（T{T.team(k[0])}）| {ab['n']} / {ab['got']} / {ab['tax']} | {ba['n']} / {ba['got']} / {ba['tax']} | {ab['got'] - ba['got']:+d} | {pp} | {ppMin} / {ppTax}")
    for tot, k, ab, ba, pp, ppMin, ppTax in plist:
        summ["pairs"].append(dict(a=nm(k[0]), b=nm(k[1]), team=T.team(k[0]), ab=[ab["n"], ab["got"], ab["tax"]], ba=[ba["n"], ba["got"], ba["tax"]], pingPong=pp, ppMin=ppMin, ppTax=ppTax))
    out.append(f"  合计 {len(plist)} 对；双向都有成交的 {sum(1 for x in plist if x[2]['n'] and x[3]['n'])} 对；600 拍内来回 {totPP} 次，来回里较小一笔的到账合计 {totPPmin}，这些来回两笔的税合计 {totPPtax}")
    summ["total"].update(pairCount=len(plist), twoWayPairs=sum(1 for x in plist if x[2]["n"] and x[3]["n"]), pingPong=totPP, ppMin=totPPmin, ppTax=totPPtax)

    out.append("")
    out.append("[YD] 收款方当拍的状态（成交的）：收款方密度档 | 笔数 | 到账 | 税 | 其中收款方在 600 拍内阵亡的 笔数 / 到账")
    bands = [(0, 50, "<50"), (50, 80, "50~80"), (80, 100, "80~100"), (100, 132, "100~132"), (132, 1e9, "≥132")]
    summ["recvDensity"] = []
    for lo, hi, lab in bands:
        rr = [r for r in ok if lo <= r[14] / max(r[13], 1) < hi]
        dead = [r for r in rr if 0 <= T.deathT[r[4]] <= r[0] + 600]
        out.append(f"    {lab} | {len(rr)} | {sum(r[6] for r in rr)} | {sum(r[7] for r in rr)} | {len(dead)} / {sum(r[6] for r in dead)}")
        summ["recvDensity"].append(dict(band=lab, n=len(rr), arrived=sum(r[6] for r in rr), tax=sum(r[7] for r in rr), recvDiedIn600=len(dead), diedArrived=sum(r[6] for r in dead)))

    # 捐出方
    encl = None
    p_en = os.path.join(OUT, mid, "enclose_sum.json")
    sealedAt = defaultdict(set)
    if os.path.exists(p_en):
        encl = True
        # 重新从 resim 的 nb 采样算一次 A 类围死（和 enclose.py 同口径）
        from enclose import classify, seal_kind
        for name, me in T.squad.items():
            for t, lst in T.sq_of(name)["nb"]:
                if not T.alive(me, t) or T.terr(me, t) <= 0:
                    continue
                c, _ = classify(T, me, lst, t)
                if seal_kind(c) == "A":
                    sealedAt[me].add(t)
    out.append("")
    out.append("[YE] 捐出方当拍的状态（成交的）：捐出方密度档 | 笔数 | 到账 | 税 | 捐完后捐出方密度（中位）| 其中捐出方当拍被异队编队友围死的 笔数 / 到账 / 税")
    summ["donorDensity"] = []
    for lo, hi, lab in [(0, 60, "<60"), (60, 80, "60~80"), (80, 100, "80~100"), (100, 132, "100~132"), (132, 1e9, "≥132")]:
        rr = [r for r in ok if lo <= r[8] / max(r[9], 1) < hi]
        after = med([(r[8] - r[6] - r[7]) / max(r[9], 1) for r in rr])
        sl = [r for r in rr if ((r[0] // 30) * 30 in sealedAt[r[1]] or (r[0] // 30) * 30 + 30 in sealedAt[r[1]])]
        out.append(f"    {lab} | {len(rr)} | {sum(r[6] for r in rr)} | {sum(r[7] for r in rr)} | {after:.1f} | {len(sl)} / {sum(r[6] for r in sl)} / {sum(r[7] for r in sl)}")
        summ["donorDensity"].append(dict(band=lab, n=len(rr), arrived=sum(r[6] for r in rr), tax=sum(r[7] for r in rr), sealedN=len(sl), sealedArrived=sum(r[6] for r in sl), sealedTax=sum(r[7] for r in sl)))
    slAll = [r for r in ok if ((r[0] // 30) * 30 in sealedAt[r[1]] or (r[0] // 30) * 30 + 30 in sealedAt[r[1]])]
    rvAll = [r for r in ok if ((r[0] // 30) * 30 in sealedAt[r[4]] or (r[0] // 30) * 30 + 30 in sealedAt[r[4]])]
    both = [r for r in slAll if r in rvAll]
    if encl:
        out.append(f"  捐出方当拍被围死（A 类）的 {len(slAll)} 笔，到账 {sum(r[6] for r in slAll)}，税 {sum(r[7] for r in slAll)}｜收款方当拍被围死的 {len(rvAll)} 笔，到账 {sum(r[6] for r in rvAll)}｜两头都被围死的 {len(both)} 笔，到账 {sum(r[6] for r in both)}，税 {sum(r[7] for r in both)}")
        summ["total"].update(donorSealedN=len(slAll), donorSealedArrived=sum(r[6] for r in slAll), donorSealedTax=sum(r[7] for r in slAll),
                             recvSealedN=len(rvAll), recvSealedArrived=sum(r[6] for r in rvAll), bothSealedN=len(both), bothSealedArrived=sum(r[6] for r in both), bothSealedTax=sum(r[7] for r in both))
    kinds = defaultdict(lambda: [0, 0, 0])
    for r in ok:
        e = kinds[r[3]]
        e[0] += 1
        e[1] += r[6]
        e[2] += r[7]
    out.append("  按 pct：" + "；".join(f"pct={k} ×{v[0]} 到账 {v[1]} 税 {v[2]}" for k, v in sorted(kinds.items(), key=lambda kv: -kv[1][0])[:8]))

    out.append("")
    out.append("[YF] 逐号（真值）：号 | 队 | 捐出 笔数 / 到账 / 税 | 收到 笔数 / 到账 | 净额（收 − 捐出到账）| 净额 − 税 | 自己的产兵（要 econ_sum.json）| 税 ÷ 产兵")
    econ = None
    p_ec = os.path.join(OUT, mid, "econ_sum.json")
    if os.path.exists(p_ec):
        econ = json.load(open(p_ec, encoding="utf-8"))["perBot"]
    summ["perBot"] = {}
    stat = defaultdict(lambda: [0, 0, 0, 0, 0])
    for r in ok:
        s = stat[r[1]]
        s[0] += 1
        s[1] += r[6]
        s[2] += r[7]
        s2 = stat[r[4]]
        s2[3] += 1
        s2[4] += r[6]
    for name, p in sorted(T.squad.items(), key=lambda kv: -(stat[kv[1]][1] + stat[kv[1]][4])):
        s = stat[p]
        inc = econ[name].get("inc", 0) if econ and name in econ else 0
        out.append(f"    {name:<16} | T{T.team(p)} | {s[0]} / {s[1]} / {s[2]} | {s[3]} / {s[4]} | {s[4] - s[1]:+d} | {s[4] - s[1] - s[2]:+d} | {inc} | {100 * s[2] / max(inc, 1):.0f}%")
        summ["perBot"][name] = dict(team=T.team(p), outN=s[0], outArrived=s[1], tax=s[2], inN=s[3], inArrived=s[4])

    txt = "\n".join(out) + "\n"
    with open(os.path.join(OUT, mid, "donpairs.txt"), "w", encoding="utf-8") as f:
        f.write(txt)
    with open(os.path.join(OUT, mid, "donpairs_sum.json"), "w", encoding="utf-8") as f:
        json.dump(summ, f, ensure_ascii=False, indent=1)
    if quiet:
        print(f"{mid}: donpairs.txt {len(out)} 行")
    else:
        print(txt)


if __name__ == "__main__":
    main()
