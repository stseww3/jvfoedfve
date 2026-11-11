#!/usr/bin/env python3
"""31_assist_burst_check.py — 协防连发（[HL-ASSIST] 2 拍一条）到底执行了几条？（R07 v2.0）

对每一串协防（同一个号、相邻 ≤6 拍、同一目标），从串前最近的 HL-TICK 快照余额出发，用引擎整数公式
（利息 / 地租 / 陆攻报价 pct=102：兵 = g0(B*103,1024)，费 = g0(12B,1024)）推到串后第一个快照，
枚举「串里有 k 条指令真的执行」（k=0..n，执行拍 = 发出拍 + lat，lat 取 8/12/16），看哪个 k 的预测余额最接近观测值。
领土在串内会因进攻而变化，利息按串前快照领土算，所以这里只要求近似吻合（给出相对误差）。

用法：python3 31_assist_burst_check.py <matchId>
"""
import sys
from collections import defaultdict
from r07lib import load_card, load_events, load_traj, income_tick, attack_quote, donate_quote


def main():
    mid = sys.argv[1]
    land = load_card(mid)["mapLand"]
    traj = load_traj(mid)
    ev = load_events(mid)
    by = defaultdict(list)
    for e in ev:
        if e["type"] == "ASSIST":
            by[e["bot"]].append(e)
    dons = [e for e in ev if e["type"] in ("DONATE", "DISPATCH")]
    for b, lst in sorted(by.items()):
        lst.sort(key=lambda e: e["t"])
        bursts = []
        cur = [lst[0]]
        for e in lst[1:]:
            if e["t"] - cur[-1]["t"] <= 6 and e.get("target") == cur[-1].get("target"):
                cur.append(e)
            else:
                bursts.append(cur)
                cur = [e]
        bursts.append(cur)
        rows = traj.get(b, [])
        for c in bursts:
            t0, t1 = c[0]["t"], c[-1]["t"]
            s0 = [r for r in rows if r["t"] <= t0]
            s1 = [r for r in rows if r["t"] > t1]
            if not s0 or not s1:
                print(f"{mid} {b} burst {t0}~{t1} n={len(c)}: 缺快照")
                continue
            s0, s1 = s0[-1], s1[0]
            pct = int(c[0].get("pct") or 102)
            print(f"{mid} {b} 协防串 t={t0}~{t1} n={len(c)} 目标={c[0].get('target')}({c[0].get('targetName')}) pct={pct}；"
                  f"快照 {s0['t']}: bal={s0['bal']} terr={s0['terr']} → {s1['t']}: bal={s1['bal']} terr={s1['terr']} (dCmds={s1['cmds'] - s0['cmds']})")
            mydons = [e for e in dons if e["bot"] == b and s0["t"] <= e["t"] < s1["t"]]
            for lat in (8, 12, 16):
                best = None
                for k in range(0, len(c) + 1):
                    bal = s0["bal"]
                    execs = {e["t"] + lat: "A" for e in c[:k]}
                    for e in mydons:
                        execs[e["t"] + lat] = ("D", int(e["pct"]))
                    for t in range(s0["t"], s1["t"]):
                        x = execs.get(t)
                        if x == "A":
                            tr, fee = attack_quote(bal, pct)
                            bal -= tr + fee
                        elif x:
                            amt, fee = donate_quote(bal, x[1])
                            bal -= amt + fee
                        bal = income_tick(bal, s0["terr"], land, t)
                    err = (bal - s1["bal"]) / max(1, s1["bal"])
                    if best is None or abs(err) < abs(best[2]):
                        best = (k, bal, err)
                    if lat == 12:
                        print(f"     lat=12 执行 {k} 条 → 预测 {bal}（相对观测 {err:+.1%}）")
                print(f"   lat={lat}: 最接近观测的是执行 {best[0]} 条（预测 {best[1]}，误差 {best[2]:+.2%}）")


if __name__ == "__main__":
    main()
