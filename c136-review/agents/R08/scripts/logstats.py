#!/usr/bin/env python3
"""logstats.py — 只有日志（没有录像）的房间里，从 HL-TICK 快照里数几样东西。

    python3 logstats.py <matchId> [--room N]

节：
  [QA] 清仓事件：相邻快照窗内余额跌 ≥80%（连续的窗合并），清仓前后的地、兵、密度；之后 600 拍内的最低领土与结局。
       同一时间窗（±180 拍）里清仓的号数 → 是不是「全队同窗清仓」。
  [QB] 顶上限空转：每个号余额 ≥ 149.5×领土（引擎硬上限 150×领土，利息被截掉）的快照数、
       余额 > 100×领土（软上限）的快照数、「有敌邻（nb≥1）且密度 ≥95 且指令数没变」的最长连续段。
       硬上限段里被截掉的利息 = 按公式不封顶应得的利息（r08lib.interest_rate），逐窗累加。
  [QC] 协防戳刺：谁、为谁、打谁、几次；戳刺那一拍前后的快照余额 ×(102+1)/1024 估出每次的兵。
  [QF] 单邻门槛：只有 1 个敌邻、没有中立地的窗按起点密度分档（<100 / 100~128 / ≥128），数没有任何非捐款指令的窗；128 = overHumanCap×100。
  [QD] 挨打不还手：领土从局部峰值掉 ≥30% 的过程（到谷底或阵亡），期间的指令数、发船数、余额前后。
  [QE] 发船：boats 计数涨了的快照窗；「纯船窗」（这一窗新增指令全是船）里少掉的兵和领土变化。没有录像时看不到船靠没靠岸，只能看地涨没涨。
       注意 cmds 计数包含陆攻、发船、捐款、戳刺（c110 L537 / L1049 / L4440 / L4451 / L4492）。
"""
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import facts  # noqa: E402
import r08lib as L  # noqa: E402


def uncapped_interest(terr, land, bal, t0, t1):
    """t0..t1 之间按公式应得的利息（不做 150×领土 封顶），领土不变。"""
    b = bal
    for t in range(t0, t1):
        if t % 10 == 9:
            r = L.interest_rate(terr, land, b, t)
            b = b + max(L.g0(r * b, 10000), 1)
        if t % 100 == 99:
            b = b + terr
    return b - bal


def analyse(mid, room=None):
    F = facts.full(mid, room=room)
    land = F["land"]
    bots = F["bots"]
    out = dict(allin=[], cap=[], pokes=[], nofight=[])
    # [QA]
    for me, b in bots.items():
        tk = b["ticks"]
        i = 1
        while i < len(tk):
            a, c = tk[i - 1], tk[i]
            if a["bal"] > 20000 and c["bal"] <= 0.2 * a["bal"] and c["t"] - a["t"] <= 270:
                j = i
                # 往前并：前一窗也在大跌（≥30%）就并进来
                k = i - 1
                while k >= 1 and tk[k]["bal"] <= 0.7 * tk[k - 1]["bal"]:
                    k -= 1
                start = tk[k]
                # 往后并：余额继续走低
                while j + 1 < len(tk) and tk[j + 1]["bal"] < tk[j]["bal"]:
                    j += 1
                low = tk[j]
                after = [s for s in tk if low["t"] < s["t"] <= low["t"] + 600]
                peak_after = max([low["terr"]] + [s["terr"] for s in after])
                min_after = min([s["terr"] for s in after]) if after else None
                died = b.get("deathTick")
                out["allin"].append(dict(me=me, name=b["name"], team=b["team"], t0=start["t"], t1=low["t"], bal0=start["bal"], bal1=low["bal"],
                                         terr0=start["terr"], terr1=low["terr"], dens0=round(start["bal"] / max(1, start["terr"]), 1),
                                         dens1=round(low["bal"] / max(1, low["terr"]), 1), boats=low["boats"] - start["boats"], cmds=low["cmds"] - start["cmds"],
                                         nb1=low["nb"], peakAfter=peak_after, minAfter=min_after, lastAfter=after[-1]["terr"] if after else None,
                                         diedWithin=bool(died and died <= low["t"] + 600), died=died))
                i = j + 1
            else:
                i += 1
    out["allin"].sort(key=lambda x: x["t0"])
    # [QB]
    for me, b in bots.items():
        tk = b["ticks"]
        if not tk:
            continue
        hard = [s for s in tk if s["terr"] > 0 and s["bal"] >= 149.5 * s["terr"]]
        soft = [s for s in tk if s["terr"] > 0 and s["bal"] > 100 * s["terr"]]
        forgone = 0
        for a, c in zip(tk, tk[1:]):
            if a["terr"] > 0 and a["terr"] == c["terr"] and c["bal"] >= 149.5 * c["terr"] and c["t"] - a["t"] <= 180:
                should = uncapped_interest(a["terr"], land, a["bal"], a["t"], c["t"])
                forgone += max(0, should - (c["bal"] - a["bal"]))
        # 最长「有敌邻、密度≥95、指令数不变」段
        best = None
        cur = None
        for a, c in zip(tk, tk[1:]):
            ok = c["nb"] >= 1 and a["nb"] >= 1 and c["cmds"] == a["cmds"] and c["boats"] == a["boats"] and a["bal"] >= 95 * max(1, a["terr"])
            if ok:
                if cur is None:
                    cur = [a["t"], c["t"], a, c]
                else:
                    cur[1], cur[3] = c["t"], c
            else:
                if cur and (best is None or cur[1] - cur[0] > best[1] - best[0]):
                    best = cur
                cur = None
        if cur and (best is None or cur[1] - cur[0] > best[1] - best[0]):
            best = cur
        # 最长「指令数不变」段（不论密度），有敌邻
        best2 = None
        cur = None
        for a, c in zip(tk, tk[1:]):
            ok = c["cmds"] == a["cmds"] and c["boats"] == a["boats"] and a["nb"] >= 1 and c["nb"] >= 1
            if ok:
                if cur is None:
                    cur = [a["t"], c["t"], a, c]
                else:
                    cur[1], cur[3] = c["t"], c
            else:
                if cur and (best2 is None or cur[1] - cur[0] > best2[1] - best2[0]):
                    best2 = cur
                cur = None
        if cur and (best2 is None or cur[1] - cur[0] > best2[1] - best2[0]):
            best2 = cur
        out["cap"].append(dict(me=me, name=b["name"], team=b["team"], n=len(tk), nHard=len(hard), nSoft=len(soft), forgone=int(forgone),
                               hardSpan=(hard[0]["t"], hard[-1]["t"]) if hard else None,
                               idleDense=dict(t0=best[0], t1=best[1], terr0=best[2]["terr"], terr1=best[3]["terr"], bal0=best[2]["bal"], bal1=best[3]["bal"]) if best else None,
                               idleAny=dict(t0=best2[0], t1=best2[1], terr0=best2[2]["terr"], terr1=best2[3]["terr"], bal0=best2[2]["bal"], bal1=best2[3]["bal"]) if best2 else None))
    # [QC]
    for me, b in bots.items():
        for ev in b.get("assists", []):
            t = ev["t"]
            prev = [s for s in b["ticks"] if s["t"] <= t]
            bal = prev[-1]["bal"] if prev else None
            ally = bots.get(ev["ally"])
            out["pokes"].append(dict(t=t, me=me, name=b["name"], team=b["team"], enemy=ev["enemy"], enemyName=ev["enemyName"], ally=ev["ally"], allyName=ev["allyName"],
                                     allyTeam=ally["team"] if ally else None, balBefore=bal, est=L.g0((bal or 0) * 103, 1024), line=ev["line"]))
    out["pokes"].sort(key=lambda x: x["t"])
    # [QD]
    for me, b in bots.items():
        tk = b["ticks"]
        i = 0
        while i < len(tk):
            # 局部峰值：之后一路不再超过它
            pk = tk[i]
            j = i + 1
            low = None
            while j < len(tk) and tk[j]["terr"] <= pk["terr"] * 1.01:
                if low is None or tk[j]["terr"] < low["terr"]:
                    low = tk[j]
                    jl = j
                j += 1
            end_t = b.get("deathTick") if j >= len(tk) and b.get("deathTick") else (low["t"] if low else None)
            end_terr = 0 if j >= len(tk) and b.get("deathTick") else (low["terr"] if low else pk["terr"])
            if low is not None and pk["terr"] >= 3000 and end_terr <= 0.7 * pk["terr"]:
                last = tk[-1] if j >= len(tk) else low
                out["nofight"].append(dict(me=me, name=b["name"], team=b["team"], t0=pk["t"], t1=end_t, terr0=pk["terr"], terr1=end_terr, bal0=pk["bal"], balLast=last["bal"],
                                           dens0=round(pk["bal"] / max(1, pk["terr"]), 1), densLast=round(last["bal"] / max(1, last["terr"]), 1),
                                           cmds=last["cmds"] - pk["cmds"], boats=last["boats"] - pk["boats"], lastSnapT=last["t"], died=j >= len(tk) and bool(b.get("deathTick"))))
                i = (jl + 1) if j < len(tk) else len(tk)
            else:
                i += 1
    out["nofight"].sort(key=lambda x: x["t0"])
    # [QE] 发船：boats 计数涨了的快照窗。纯船窗 = 这一窗新增的指令全是船（Δcmds == Δboats）。
    out["boats"] = []
    for me, b in bots.items():
        tk = b["ticks"]
        if not tk or tk[-1]["boats"] == 0:
            continue
        rows = []
        for i in range(1, len(tk)):
            a, c = tk[i - 1], tk[i]
            db = c["boats"] - a["boats"]
            if db <= 0:
                continue
            should = facts.interest_gain(a["terr"], land, a["bal"], a["t"], c["t"])
            nxt = [s for s in tk if c["t"] < s["t"] <= c["t"] + 180]
            rows.append(dict(t0=a["t"], t1=c["t"], boats=db, cmds=c["cmds"] - a["cmds"], pure=(c["cmds"] - a["cmds"]) == db, bal0=a["bal"], bal1=c["bal"],
                             spent=should - c["bal"], terr0=a["terr"], terr1=c["terr"], terrLater=max([c["terr"]] + [s["terr"] for s in nxt]),
                             boxed=a["nb"] == 0 and a["neut"] == 0, nb0=a["nb"], neut0=a["neut"], dens0=round(a["bal"] / max(1, a["terr"]), 1)))
        out["boats"].append(dict(me=me, name=b["name"], team=b["team"], total=tk[-1]["boats"], rows=rows))
    # [QF] 单邻门槛：窗口起点只有 1 个敌邻、没有中立地。按起点密度分档（<100 / 100~128 / ≥128），
    # 数「这一窗没有任何非捐款指令」的窗数（非捐款指令 = Δcmds − 窗内 HL-DONATE 条数 − HL-ASSIST 条数）。
    # 128 = c110 的 overHumanCap×100：只剩一个健康真人邻居时，余额不到 128×领土就不打他（buyLand L5269-5273）。
    gates = []
    for me, b in F["bots"].items():
        tk = b["ticks"]
        row = dict(name=b["name"], me=me, team=b["team"], lo=[0, 0], mid=[0, 0], hi=[0, 0], hiLost=0, hiFirst=None, hiLast=None, run=None)
        cur = None
        for a, c in zip(tk, tk[1:]):
            if c["t"] - a["t"] > 100 or a["nb"] != 1 or a["neut"] != 0 or a["terr"] <= 0:
                cur = None
                continue
            dons = sum(1 for d in b["donations"] if a["t"] <= d["t"] < c["t"])
            pokes = sum(1 for d in b["assists"] if a["t"] <= d["t"] < c["t"])
            acts = (c["cmds"] - a["cmds"]) - dons - pokes
            dens = a["bal"] / max(1, a["terr"])
            k = "hi" if dens >= 128 else ("mid" if dens >= 100 else "lo")
            row[k][0] += 1
            if acts <= 0:
                row[k][1] += 1
            if k == "hi" and acts <= 0:
                row["hiLost"] += max(0, a["terr"] - c["terr"])
                row["hiFirst"] = a["t"] if row["hiFirst"] is None else row["hiFirst"]
                row["hiLast"] = c["t"]
            if acts <= 0 and dens >= 100:
                if cur is None:
                    cur = dict(t0=a["t"], t1=c["t"], terr0=a["terr"], terr1=c["terr"], bal0=a["bal"], bal1=c["bal"])
                else:
                    cur.update(t1=c["t"], terr1=c["terr"], bal1=c["bal"])
                if row["run"] is None or cur["t1"] - cur["t0"] > row["run"]["t1"] - row["run"]["t0"]:
                    row["run"] = dict(cur)
            else:
                cur = None
        if row["lo"][0] + row["mid"][0] + row["hi"][0]:
            gates.append(row)
    out["gates"] = gates
    return F, out


def main():
    args = sys.argv[1:]
    mid = args[0]
    room = int(args[args.index("--room") + 1]) if "--room" in args else None
    F, o = analyse(mid, room)
    P = []
    P.append(f"[QA] {mid}{'' if room is None else ' 房间' + str(room)} 清仓事件（余额单窗跌到 ≤20%，前后大跌的窗并在一起）{len(o['allin'])} 起：")
    P.append("     号 队 | 起止拍 | 余额 前→后（密度 前→后）| 领土 前→后 | 指令/船 | 清仓后敌邻数 | 之后 600 拍：最高地 / 最低地 / 末条地 | 600 拍内阵亡?")
    for x in o["allin"]:
        P.append(f"     {x['name']}({x['me']}) T{x['team']} | {x['t0']}~{x['t1']} | {x['bal0']}→{x['bal1']}（{x['dens0']}→{x['dens1']}）| {x['terr0']}→{x['terr1']} | {x['cmds']}/{x['boats']} | {x['nb1']} | "
                 f"{x['peakAfter']} / {x['minAfter']} / {x['lastAfter']} | {'是 @' + str(x['died']) if x['diedWithin'] else '否'}")
    # 同窗聚类
    ts = sorted(x["t1"] for x in o["allin"])
    best = (0, None)
    for t in ts:
        n = len({x["me"] for x in o["allin"] if t <= x["t1"] <= t + 360})
        if n > best[0]:
            best = (n, t)
    if best[1] is not None:
        names = sorted({x["name"] for x in o["allin"] if best[1] <= x["t1"] <= best[1] + 360})
        P.append(f"     最密的 360 拍窗：t={best[1]}~{best[1] + 360} 里 {best[0]} 个号清仓（{' '.join(names)}）")
    P.append("[QB] 顶上限空转：号 | 快照数 | 硬上限(≥149.5×领土)快照数 首末拍 | 被截掉的利息 | 软上限(>100×)快照数 | 有敌邻且密度≥95 且不发指令的最长段（地、兵 前→后）| 有敌邻不发指令的最长段")
    for x in sorted(o["cap"], key=lambda x: -x["nSoft"]):
        d = x["idleDense"]
        a = x["idleAny"]
        P.append(f"     {x['name']}({x['me']}) T{x['team']} | {x['n']} | {x['nHard']} {x['hardSpan'] or '-'} | {x['forgone']} | {x['nSoft']} | "
                 + (f"{d['t0']}~{d['t1']}（{d['t1'] - d['t0']} 拍，地 {d['terr0']}→{d['terr1']}，兵 {d['bal0']}→{d['bal1']}）" if d else "-") + " | "
                 + (f"{a['t0']}~{a['t1']}（{a['t1'] - a['t0']} 拍，地 {a['terr0']}→{a['terr1']}，兵 {a['bal0']}→{a['bal1']}）" if a else "-"))
    P.append(f"[QC] 协防戳刺 {len(o['pokes'])} 次：拍 | 出手的号(队) → 打谁 | 为谁(队) | 跨队? | 戳刺前快照余额 | 估计出兵(10.06%)")
    tot = defaultdict(lambda: [0, 0])
    for x in o["pokes"]:
        cross = x["allyTeam"] is not None and x["allyTeam"] != x["team"]
        P.append(f"     {x['t']} | {x['name']}(T{x['team']}) → {x['enemyName']}({x['enemy']}) | {x['allyName']}(T{x['allyTeam']}) | {'跨队' if cross else '同队'} | {x['balBefore']} | {x['est']} L{x['line']}")
        k = (x["name"], x["enemyName"], x["allyName"], cross)
        tot[k][0] += 1
        tot[k][1] += x["est"]
    for k, v in sorted(tot.items(), key=lambda kv: -kv[1][1]):
        P.append(f"     合计：{k[0]} → {k[1]} 为 {k[2]}（{'跨队' if k[3] else '同队'}）{v[0]} 次，估计出兵 {v[1]}")
    P.append("[QD] 挨打不还手（领土从局部峰值掉 ≥30%）：号 队 | 峰值拍→谷底/阵亡拍 | 领土 前→后 | 余额 峰值时→末条快照（密度）| 期间指令数/发船数 | 末条快照拍 | 以阵亡收场?")
    for x in o["nofight"]:
        P.append(f"     {x['name']}({x['me']}) T{x['team']} | {x['t0']}→{x['t1']} | {x['terr0']}→{x['terr1']} | {x['bal0']}→{x['balLast']}（{x['dens0']}→{x['densLast']}）| {x['cmds']}/{x['boats']} | {x['lastSnapT']} | {'是' if x['died'] else '否'}")
    P.append("[QE] 发船（HL-TICK 的 boats 计数）：号 队 | 总船数 | 发船的快照窗数（纯船窗 = 这一窗新增指令全是船）| 纯船窗里：船数 / 少掉的兵（按利息公式应有 − 实际）/ 窗内领土变化合计 / 之后 180 拍内最高领土比窗前多出的合计 | 被围时发的船数")
    for x in sorted(o["boats"], key=lambda x: -x["total"]):
        pure = [r for r in x["rows"] if r["pure"]]
        P.append(f"     {x['name']}({x['me']}) T{x['team']} | {x['total']} | {len(x['rows'])}（纯 {len(pure)}）| {sum(r['boats'] for r in pure)} / {sum(r['spent'] for r in pure)} / "
                 f"{sum(r['terr1'] - r['terr0'] for r in pure):+d} / {sum(r['terrLater'] - r['terr0'] for r in pure):+d} | {sum(r['boats'] for r in x['rows'] if r['boxed'])}")
    P.append("     明细（船数 ≥3 的窗，或单窗少掉 ≥20% 余额的纯船窗）：号 | 窗 | 船/指令 | 余额 前→后（少掉的兵，占窗前余额 %）| 领土 前→后（之后 180 拍最高）| 窗前 敌邻/中立/密度")
    for x in sorted(o["boats"], key=lambda x: -x["total"]):
        for r in x["rows"]:
            if r["boats"] >= 3 or (r["pure"] and r["spent"] >= 0.2 * max(1, r["bal0"])):
                P.append(f"     {x['name']} | {r['t0']}~{r['t1']} | {r['boats']}/{r['cmds']} | {r['bal0']}→{r['bal1']}（{r['spent']}，{100 * r['spent'] / max(1, r['bal0']):.0f}%）| "
                         f"{r['terr0']}→{r['terr1']}（{r['terrLater']}）| {r['nb0']}/{r['neut0']}/{r['dens0']}")
    P.append("[QF] 单邻门槛（窗口起点只有 1 个敌邻、没有中立地）：号 队 | 起点密度 <100：窗数 / 其中没有非捐款指令 | 100~128：窗数 / 没指令 | ≥128：窗数 / 没指令（首末拍，这些窗里丢的地）| 密度≥100 连续没指令的最长段")
    tot = [0, 0, 0, 0, 0, 0, 0]
    for x in sorted(o["gates"], key=lambda x: -(x["hi"][1] * 1000 + x["mid"][1])):
        r = x["run"]
        P.append(f"     {x['name']}({x['me']}) T{x['team']} | {x['lo'][0]} / {x['lo'][1]} | {x['mid'][0]} / {x['mid'][1]} | {x['hi'][0]} / {x['hi'][1]}"
                 + (f"（{x['hiFirst']}~{x['hiLast']}，丢 {x['hiLost']} 格）" if x["hi"][1] else "") + " | "
                 + (f"{r['t0']}~{r['t1']}（{r['t1'] - r['t0']} 拍，地 {r['terr0']}→{r['terr1']}，兵 {r['bal0']}→{r['bal1']}）" if r else "-"))
        for i, k in enumerate(("lo", "mid", "hi")):
            tot[2 * i] += x[k][0]
            tot[2 * i + 1] += x[k][1]
        tot[6] += x["hiLost"]
    P.append(f"     合计：<100 {tot[0]} 窗 / 没指令 {tot[1]}；100~128 {tot[2]} / {tot[3]}；≥128 {tot[4]} / {tot[5]}（这些窗里共丢 {tot[6]} 格）")
    txt = "\n".join(P)
    suffix = "" if room is None else f"_room{room}"
    od = os.path.join(HERE, "..", "out", mid)
    os.makedirs(od, exist_ok=True)
    open(os.path.join(od, f"logstats{suffix}.txt"), "w", encoding="utf-8").write(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
