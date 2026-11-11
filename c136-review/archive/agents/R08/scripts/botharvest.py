#!/usr/bin/env python3
"""botharvest.py — 每个号在各时间窗「吃空地/吃内置AI/吃真人」各多少格 + 当时的密度与邻居构成。

    python3 botharvest.py <matchId> [窗口边界，默认 270,630,900,1260,1800]
用来区分「没东西可吃（被真人围住）」和「有内置 AI 邻居却没吃」。
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from truth import Truth, NEUTRAL  # noqa: E402


def nb_at(T, name, t):
    best = None
    for rec in T.R["sq"][name]["nb"]:
        if rec[0] <= t:
            best = rec
        else:
            break
    if not best:
        return "", 0, 0, 0
    ai = hum = neu = 0
    out = []
    for q, c in best[1]:
        if q >= NEUTRAL:
            neu += c
        elif q >= T.H:
            ai += c
        else:
            hum += c
    for q, c in best[1][:4]:
        out.append(("空地" if q >= NEUTRAL else f"AI{q}" if q >= T.H else T.nm(q, t)) + f":{c}")
    return " ".join(out), neu, ai, hum


def main():
    mid = sys.argv[1]
    T = Truth(mid)
    R = T.R
    edges = [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else [270, 630, 900, 1260, 1800]
    wins = list(zip(edges, edges[1:]))
    acc = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for t, a, d, tiles, burnt, dB, dS, n in R["pairLog"]:
        if a >= T.H:
            continue
        kind = "N" if d >= NEUTRAL else "AI" if d >= T.H else "H"
        for w in wins:
            if w[0] < t <= w[1]:
                acc[a][(w, kind)][0] += tiles
                acc[a][(w, kind)][1] += burnt
    print("号 | 队 | 离开拍 | 各边界时刻 地 | 各边界时刻 密度 | 各窗 吃空地/内置AI/真人（格）")
    for name, info in sorted(R["squad"].items(), key=lambda kv: kv[1]["id"]):
        p = info["id"]
        if p < 0 or info.get("peer"):
            continue
        te = [T.terr(p, t) for t in edges]
        de = [T.bal(p, t) / max(T.terr(p, t), 1) for t in edges]
        cells = ["/".join(str(acc[p][(w, k)][0]) for k in ("N", "AI", "H")) for w in wins]
        print(f"{name:12s} T{T.team(p)} 离开{T.leftT[p]:5d} | {' '.join('%5d' % x for x in te)} | {' '.join('%5.1f' % x for x in de)} | {' | '.join(cells)}")
        for t in edges[1:-1]:
            s, neu, ai, hum = nb_at(T, name, t)
            print(f"        t={t} 接壤 空地{neu} 内置AI{ai} 真人{hum}：{s[:130]}")


if __name__ == "__main__":
    main()
