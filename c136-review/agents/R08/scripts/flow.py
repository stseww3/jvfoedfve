#!/usr/bin/env python3
"""flow.py — 只看日志的『兵去哪了』流水账：把每个号每个 90 拍快照窗的余额变化拆成 利息 / 捐款 / 其余。

    python3 flow.py <matchId> [--room N] [--t0 3000] [--t1 99999] [--bots 名字,名字]

为什么要它：logstats [QE] 的『纯船窗少掉的兵』只数出去的那一窗，船上的兵靠岸、打完以后回到余额是在后面的窗。
要说一个号的船到底亏了多少，得把整段时间的进出合起来看；要说兵是不是并到了队友身上（船靠在同队的地上、
没定案的捐款其实成交了），得把同一窗里全队的『其余』加起来看守不守恒。

口径：
  · 残差 = 窗末余额 − 只滚利息的公式余额（facts.interest_gain；领土取窗首，窗内领土变化大时利息有 1~2% 的误差）。
  · 捐款取 donfit 定案（out/<局>/donfit[_room<N>].json）：EXEC 的按 到账+税 记捐出方流出、按 到账 记收款方流入，
    记在发令拍所在的窗（时延跨窗时会错开一窗）。没定案（AMB）的另列一栏：发令时按足额算的 到账+税 / 到账。
  · 其余 = 残差 + 成交捐出 − 成交收入。负数 = 陆攻 / 船 / 戳刺派出去还没回来的兵、挨打被打掉的兵；正数 = 回流、没定案的捐款到账、
    同队的船并进来的兵、空壳赠兵。
节：
  [VA] 逐号合计：窗数 | 利息（公式增量）| 成交捐出（到账+税）| 成交收入 | 没定案 捐出 / 收入（足额口径）| 其余 负的合计 / 正的合计 / 净 |
       领土 首→末 | 陆攻+戳刺 / 船 条数（cmds 增量 − 捐款日志条数 − 船，船）
  [VB] 逐窗全队：窗 | 各号『其余』（千兵；* = 这一窗有船，+ = 有陆攻或戳刺）| 全队合计 | 这一窗没定案的捐款（捐出→收款 足额到账，千兵）
  [VC] 被围（窗首 nb=0 且 neut=0）且窗内有船的窗，逐号合计：窗数 / 船数 | 这些窗的『其余』合计 | 之后一窗的『其余』合计（回流）| 两者之和 |
       这些窗 + 之后一窗的领土净变化
"""
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import facts  # noqa: E402


def main():
    args = sys.argv[1:]
    mid = args[0]
    room = int(args[args.index("--room") + 1]) if "--room" in args else None
    t0 = int(args[args.index("--t0") + 1]) if "--t0" in args else 0
    t1 = int(args[args.index("--t1") + 1]) if "--t1" in args else 10 ** 9
    only = set(args[args.index("--bots") + 1].split(",")) if "--bots" in args else None
    F = facts.build(mid, room=room) if room is not None else facts.build(mid)
    land = F["land"]
    sfx = f"_room{room}" if room is not None else ""
    dpath = os.path.join(HERE, "..", "out", mid, f"donfit{sfx}.json")
    if not os.path.exists(dpath) and room is not None:
        dpath = os.path.join(HERE, "..", "out", mid, "donfit.json")   # 主房间的产物不带后缀
    rows = json.load(open(dpath))["rows"] if os.path.exists(dpath) else []
    if rows and not all(r["donor"] in F["bots"] or str(r["donor"]) in F["bots"] for r in rows):
        rows = []   # 那份定案是别的房间的
    if not rows:
        print(f"（没有找到 donfit 定案 {os.path.basename(dpath)}：捐款栏全是 0，『其余』里混着捐款）")
    name_to_me = {}
    for me, b in F["bots"].items():
        name_to_me[b["name"]] = str(me)
    bots = {str(me): b for me, b in F["bots"].items()}

    def full_amt(r):
        return int((r["myBal"] * (r["pct"] + 1) + 0.5) // 1024)

    def full_fee(r):
        return int((64 * r["myBal"] + 0.5) // 1024)

    wins = defaultdict(dict)   # me -> t0 -> rec
    for me, b in bots.items():
        tk = b["ticks"]
        for i in range(1, len(tk)):
            a, c = tk[i - 1], tk[i]
            if c["t"] <= t0 or a["t"] >= t1 or a["terr"] < 50:
                continue
            exp = facts.interest_gain(a["terr"], land, a["bal"], a["t"], c["t"])
            rec = dict(t0=a["t"], t1=c["t"], resid=c["bal"] - exp, interest=exp - a["bal"], terr0=a["terr"], terr1=c["terr"],
                       dc=c["cmds"] - a["cmds"], db=c["boats"] - a["boats"], boxed=(a["nb"] == 0 and a["neut"] == 0),
                       outE=0, inE=0, outA=0, inA=0, nDonLog=0, amb=[])
            wins[me][a["t"]] = rec
    for r in rows:
        dn, al = str(r["donor"]), str(r["ally"])
        for me, key_out in ((dn, True), (al, False)):
            if me not in wins:
                continue
            for w in wins[me].values():
                if w["t0"] <= r["t"] < w["t1"]:
                    if key_out:
                        w["nDonLog"] += 1
                        if r["status"] == "EXEC":
                            w["outE"] += r["amt"] + r["fee"]
                        elif r["status"] == "AMB":
                            w["outA"] += full_amt(r) + full_fee(r)
                            w["amb"].append(f"{r['donorName']}→{r['allyName']} {full_amt(r) // 1000}")
                    else:
                        if r["status"] == "EXEC":
                            w["inE"] += r["amt"]
                        elif r["status"] == "AMB":
                            w["inA"] += full_amt(r)
                    break
    order = sorted(wins, key=lambda m: int(m))
    if only:
        order = [m for m in order if bots[m]["name"] in only]
    print(f"[VA] {mid} 兵的流水（只看日志；窗 = 相邻两条 HL-TICK，t={t0}~{min(t1, F['card']['outcome']['endTick'])}）：号 队 | 窗数 | 利息 | 成交捐出（到账+税）| 成交收入 | "
          f"没定案 捐出 / 收入（足额口径）| 其余：负的合计 / 正的合计 / 净 | 领土 首→末 | 陆攻+戳刺 / 船")
    for me in order:
        ws = sorted(wins[me].values(), key=lambda w: w["t0"])
        if not ws:
            continue
        oth = [w["resid"] + w["outE"] - w["inE"] for w in ws]
        b = bots[me]
        print(f"     {b['name']}({me}) T{b.get('team')} | {len(ws)} | {sum(w['interest'] for w in ws)} | {sum(w['outE'] for w in ws)} | {sum(w['inE'] for w in ws)} | "
              f"{sum(w['outA'] for w in ws)} / {sum(w['inA'] for w in ws)} | {sum(x for x in oth if x < 0)} / {sum(x for x in oth if x > 0)} / {sum(oth)} | "
              f"{ws[0]['terr0']}→{ws[-1]['terr1']} | {sum(w['dc'] - w['db'] - w['nDonLog'] for w in ws)} / {sum(w['db'] for w in ws)}")
    print("[VB] 逐窗全队『其余』（千兵；* = 这一窗有船，+ = 有陆攻或戳刺，# = 窗首被围）：窗 | " + " | ".join(bots[m]["name"] for m in order) + " | 全队合计 | 没定案的捐款（足额到账，千兵）")
    tset = sorted({t for m in order for t in wins[m]})
    for t in tset:
        cells, tot, amb = [], 0, []
        for m in order:
            w = wins[m].get(t)
            if not w:
                cells.append("-")
                continue
            o = w["resid"] + w["outE"] - w["inE"]
            tot += o
            amb += w["amb"]
            flag = ("*" if w["db"] > 0 else "") + ("+" if w["dc"] - w["db"] - w["nDonLog"] > 0 else "") + ("#" if w["boxed"] else "")
            cells.append(f"{round(o / 1000)}{flag}")
        print(f"     {t:>5} | " + " | ".join(f"{c:>8}" for c in cells) + f" | {round(tot / 1000):>7} | " + "；".join(amb))
    print("[VC] 被围（窗首 nb=0 且 neut=0）且窗内有船的窗：号 | 窗数 / 船数 | 这些窗的『其余』合计 | 紧接着一窗的『其余』合计 | 两者之和 | 领土净变化（这些窗 + 紧接着一窗）")
    for me in order:
        ws = sorted(wins[me].values(), key=lambda w: w["t0"])
        n = nb = a = bsum = dterr = 0
        used = set()
        for i, w in enumerate(ws):
            if w["boxed"] and w["db"] > 0:
                n += 1
                nb += w["db"]
                if i not in used:
                    a += w["resid"] + w["outE"] - w["inE"]
                    dterr += w["terr1"] - w["terr0"]
                    used.add(i)
                if i + 1 < len(ws) and i + 1 not in used and not (ws[i + 1]["boxed"] and ws[i + 1]["db"] > 0):
                    x = ws[i + 1]
                    bsum += x["resid"] + x["outE"] - x["inE"]
                    dterr += x["terr1"] - x["terr0"]
                    used.add(i + 1)
        if n:
            print(f"     {bots[me]['name']} | {n} / {nb} | {a} | {bsum} | {a + bsum} | {dterr:+d}")


if __name__ == "__main__":
    main()
