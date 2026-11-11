#!/usr/bin/env python3
"""noeffect.py — 只看日志的「指令没生效」指标（客户端卡顿的日志侧影子）。

    python3 noeffect.py <matchId> [--room N] [--bucket 270] [--bot 名字]

口径：相邻两条 HL-TICK 快照（间隔正好 90 拍）之间，策略自己记的指令数 cmds 涨了，
但余额没有比『只吃利息』的预期少（少的部分 < 期初余额的 2%），领土也没涨（≤ +0.5%）——
这些指令在这个窗里没有生效（没发出去、还在路上，或者被引擎丢了）。
[NA] 按时间桶：窗数、指令数、没生效的指令数（窗数）、花掉的兵 / 期初余额、领土净变化。
[NB] 逐号：第一个 / 最后一个没生效窗、没生效指令总数；随后第一次『单窗花掉 ≥40% 余额』的拍和花掉的比例。
[ND] 整段零花费：连续 ≥3 个窗每窗都有新指令、余额与只滚利息的公式逐兵相等（<0.1%）、领土不涨的段。
--bot：打印这个号逐窗的明细。
有录像的房间可以拿 truth / shadowcmp 的实测时延对照这个指标（B049 房间 1）。
"""
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import facts  # noqa: E402


def windows(b, land):
    tk = b["ticks"]
    for a, c in zip(tk, tk[1:]):
        if c["t"] - a["t"] != 90:
            continue
        exp = facts.interest_gain(a["terr"], land, a["bal"], a["t"], c["t"])
        spend = max(0, exp - c["bal"])
        dc = c["cmds"] - a["cmds"]
        noeff = dc > 0 and spend < 0.02 * a["bal"] and c["terr"] <= a["terr"] * 1.005
        yield dict(t0=a["t"], t1=c["t"], dc=dc, spend=spend, bal0=a["bal"], bal1=c["bal"], terr0=a["terr"], terr1=c["terr"], noeff=noeff,
                   frac=spend / max(1, a["bal"]), nb=a["nb"], neut=a["neut"])


def main():
    args = sys.argv[1:]
    mid = args[0]
    room = int(args[args.index("--room") + 1]) if "--room" in args else None
    bucket = int(args[args.index("--bucket") + 1]) if "--bucket" in args else 270
    only = args[args.index("--bot") + 1] if "--bot" in args else None
    F = facts.full(mid, room=room)
    land = F["land"]
    P = []
    B = defaultdict(lambda: dict(cmds=0, spend=0, dterr=0, bal=0, nwin=0, ncmd=0, nw=0))
    per = []
    for me, b in F["bots"].items():
        ws = list(windows(b, land))
        for w in ws:
            x = B[(w["t0"] // bucket) * bucket]
            x["cmds"] += w["dc"]; x["spend"] += w["spend"]; x["dterr"] += w["terr1"] - w["terr0"]; x["bal"] += w["bal0"]; x["nwin"] += 1
            if w["noeff"]:
                x["ncmd"] += w["dc"]; x["nw"] += 1
        ne = [w for w in ws if w["noeff"] and w["t0"] >= 600]
        if ne:
            # 末段：最后一个没生效窗之后（含同窗后续）第一次单窗花掉 ≥40%
            first_big = next((w for w in ws if w["t0"] >= ne[0]["t0"] and w["frac"] >= 0.40), None)
            before = [w for w in ne if first_big is None or w["t1"] <= first_big["t1"]]
            per.append(dict(name=b["name"], me=me, team=b["team"], first=ne[0]["t0"], last=ne[-1]["t1"], n=sum(w["dc"] for w in ne),
                            nBefore=sum(w["dc"] for w in before), big=first_big))
        if only and b["name"] == only:
            P.append(f"[NC] {only} 逐窗：t0~t1 | 指令+ | 余额 前→后 | 花掉(占期初%) | 领土 前→后 | 敌邻/中立 | 没生效?")
            for w in ws:
                P.append(f"     {w['t0']}~{w['t1']} | {w['dc']} | {w['bal0']}→{w['bal1']} | {int(w['spend'])}({100 * w['frac']:.1f}%) | {w['terr0']}→{w['terr1']} | {w['nb']}/{w['neut']} | {'是' if w['noeff'] else ''}")
    P.insert(0, f"[NA] {mid}{'' if room is None else ' 房间' + str(room)} 桶起点 | 窗数 | 指令数 | 没生效的指令数(窗数) | 花掉的兵/期初余额合计 | 领土净变化")
    k = 1
    for t in sorted(B):
        x = B[t]
        P.insert(k, f"     {t:>5} | {x['nwin']:>3} | {x['cmds']:>3} | {x['ncmd']:>3} ({x['nw']}) | {100 * x['spend'] / max(1, x['bal']):5.1f}% | {x['dterr']:>7}")
        k += 1
    P.insert(k, "[NB] 号 队 | 第一个没生效窗起点 | 最后一个没生效窗终点 | 没生效指令总数 | 其后第一次单窗花掉≥40%：窗、花掉比例、之前累计没生效指令数")
    k += 1
    for x in sorted(per, key=lambda x: x["first"]):
        g = x["big"]
        P.insert(k, f"     {x['name']}({x['me']}) T{x['team']} | {x['first']} | {x['last']} | {x['n']} | "
                 + (f"{g['t0']}~{g['t1']} 花掉 {100 * g['frac']:.0f}%（{g['bal0']}→{g['bal1']}，地 {g['terr0']}→{g['terr1']}），之前没生效 {x['nBefore']} 条" if g else "没有"))
        k += 1
    # [ND] 整段零花费：连续 ≥3 个窗（≥270 拍）每窗都有新指令，余额与「只滚利息」的公式相差 <0.1%（逐兵对上），领土不涨
    runs = []
    for me, b in F["bots"].items():
        cur = []
        for w in list(windows(b, land)) + [None]:
            ok = w is not None and w["dc"] > 0 and w["spend"] < 0.001 * max(1, w["bal0"]) and w["terr1"] <= w["terr0"]
            if ok:
                cur.append(w)
                continue
            if len(cur) >= 3:
                dons = sum(1 for d in b["donations"] if cur[0]["t0"] <= d["t"] < cur[-1]["t1"])
                runs.append(dict(name=b["name"], team=b["team"], t0=cur[0]["t0"], t1=cur[-1]["t1"], n=sum(x["dc"] for x in cur), dons=dons,
                                 bal0=cur[0]["bal0"], bal1=cur[-1]["bal1"], terr0=cur[0]["terr0"], terr1=cur[-1]["terr1"], nb0=cur[0]["nb"], nb1=cur[-1]["nb"]))
            cur = []
    P.append(f"[ND] 整段零花费（连续 ≥3 个窗每窗都有新指令，余额与只滚利息的公式相差 <0.1%，领土不涨）{len(runs)} 段，指令合计 {sum(r['n'] for r in runs)} 条（其中日志里的捐款 {sum(r['dons'] for r in runs)} 条）")
    P.append("     号 队 | 起止拍 | 指令数（其中捐款日志条数）| 余额 前→后 | 领土 前→后 | 敌邻 前→后")
    for r in sorted(runs, key=lambda r: (r["t0"], r["name"])):
        P.append(f"     {r['name']} T{r['team']} | {r['t0']}~{r['t1']} | {r['n']}（{r['dons']}）| {r['bal0']}→{r['bal1']} | {r['terr0']}→{r['terr1']} | {r['nb0']}→{r['nb1']}")
    early = [r for r in runs if r["t0"] < 2100]
    P.append(f"     其中起点在 t<2100 的 {len(early)} 段：指令 {sum(r['n'] for r in early)} 条（捐款日志 {sum(r['dons'] for r in early)} 条），涉及 {len({r['name'] for r in early})} 个号")
    txt = "\n".join(P)
    od = os.path.join(HERE, "..", "out", mid)
    os.makedirs(od, exist_ok=True)
    suffix = "" if room is None else f"_room{room}"
    open(os.path.join(od, f"noeffect{suffix}.txt"), "w", encoding="utf-8").write(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
