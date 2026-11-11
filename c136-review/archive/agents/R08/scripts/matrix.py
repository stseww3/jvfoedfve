#!/usr/bin/env python3
"""matrix.py — 一局的「拍 × bot」矩阵：每格 terr/bal(千)/dens/nb/neut，方便横向看同一拍全队的状态。

    python3 matrix.py <matchId> [t0 t1] [--team N] [--me a,b,c]

列按玩家号排；B 组可用 --team 只看某一队（按 RESULT 的 team.mine；未知队号的也一并列出并标 ?）。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import facts  # noqa: E402


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    mid = args[0]
    t0 = int(args[1]) if len(args) > 1 else 0
    t1 = int(args[2]) if len(args) > 2 else 10 ** 9
    team = None
    mes = None
    for i, a in enumerate(sys.argv):
        if a == "--team":
            team = int(sys.argv[i + 1])
        if a == "--me":
            mes = {int(x) for x in sys.argv[i + 1].split(",")}
    F = facts.build(mid)
    bots = F["bots"]
    cols = [me for me, b in bots.items() if b["ticks"] and (team is None or b["team"] in (team, None)) and (mes is None or me in mes)]
    print("t     | " + " | ".join(f"{bots[me]['name'][:9]}({me})T{bots[me]['team'] if bots[me]['team'] is not None else '?'}" for me in cols))
    ts = sorted({s["t"] for me in cols for s in bots[me]["ticks"] if t0 <= s["t"] <= t1})
    for t in ts:
        row = []
        for me in cols:
            s = facts.snap_at(bots[me], t, 0)
            row.append(f"{s['terr']}/{s['bal'] // 1000}k/{s['dens']:.0f}/{s['nb']}/{s['neut']}" if s else "-")
        print(f"{t:<5} | " + " | ".join(row))


if __name__ == "__main__":
    main()
