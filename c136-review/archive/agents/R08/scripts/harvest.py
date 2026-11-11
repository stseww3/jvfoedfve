#!/usr/bin/env python3
"""harvest.py — 「吃内置 AI / 吃空地 / 吃真人」的分账：按时间窗统计本编队、同房另一支编队、其余真人各拿了多少格、每格花多少兵。

    python3 harvest.py <matchId> [窗口边界，默认 0,270,630,900,1260,1800,2700,3600,99999]
依据 resim.json 的逐对战损账（每 30 拍一窗，窗尾拍号）。人均 = 该组在窗口起点还活跃（没离开、没死）的号数。
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from truth import Truth, NEUTRAL  # noqa: E402


def main():
    mid = sys.argv[1]
    T = Truth(mid)
    edges = [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else [0, 270, 630, 900, 1260, 1800, 2700, 3600, 99999]
    grp = lambda p: "本编队" if p in T.sqIds else "另一支" if p in T.peerIds else "其余真人" if p < T.H else "内置AI"  # noqa: E731
    for a, b in zip(edges, edges[1:]):
        acc = defaultdict(lambda: [0, 0])
        for t, atk, dfd, tiles, burnt, dB, dS, n in T.R["pairLog"]:
            if not (a < t <= b) or atk >= T.H:
                continue
            kind = "空地" if dfd >= NEUTRAL else "内置AI" if dfd >= T.H else "空壳" if T.is_husk(dfd, t) else "真人"
            r = acc[(grp(atk), kind)]
            r[0] += tiles
            r[1] += burnt
        head = {g: sum(1 for p in ids if T.active(p, a) and T.terr(p, max(a, 10)) > 0) for g, ids in
                (("本编队", T.sqIds), ("另一支", T.peerIds), ("其余真人", set(range(T.H)) - T.sqIds - T.peerIds))}
        print(f"窗口 ({a}, {min(b, T.end)}]：活跃人数 本编队 {head['本编队']}，另一支 {head['另一支']}，其余真人 {head['其余真人']}")
        for kind in ("空地", "内置AI", "空壳", "真人"):
            tot = sum(acc[(g, kind)][0] for g in ("本编队", "另一支", "其余真人"))
            if tot <= 0:
                continue
            parts = []
            for g in ("本编队", "另一支", "其余真人"):
                r = acc[(g, kind)]
                if head[g] == 0:
                    continue
                parts.append(f"{g} {r[0]}格（占{100 * r[0] / tot:.0f}%，人均{r[0] / head[g]:.0f}，{r[1] / max(r[0], 1):.1f}兵/格）")
            print(f"    吃{kind} 共{tot}格：" + "；".join(parts))


if __name__ == "__main__":
    main()
