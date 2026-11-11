#!/usr/bin/env python3
"""top.py — 全场真值里各时刻的头部玩家与各队合计（地、兵、人数）。

    python3 top.py <matchId> [t1,t2,...] [--n 8]
名字后缀同 truth.py（*本编队 +同房另一支 ~空壳）。
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from truth import Truth, checkpoints  # noqa: E402


def main():
    mid = sys.argv[1]
    T = Truth(mid)
    R = T.R
    n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 8
    ts = [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else [t for t in checkpoints(T.end) if t % 900 == 0]
    for t in ts:
        i = T.at(t)
        terr, bal = R["snapTerr"][i], R["snapBal"][i]
        tl = [0] * (T.nTeams + 1)
        tb = [0] * (T.nTeams + 1)
        tn = [0] * (T.nTeams + 1)
        hl = [0] * (T.nTeams + 1)
        for p in range(T.H):
            if terr[p] <= 0:
                continue
            tm = T.team(p)
            tl[tm] += terr[p]
            tb[tm] += bal[p]
            if T.is_husk(p, t):
                hl[tm] += terr[p]
            else:
                tn[tm] += 1
        print(f"t={T.snapT[i]}：各队 地%/兵(千)/活跃人数/其中空壳地% → " + "  ".join(
            f"T{k}:{100 * tl[k] / T.land:.1f}%/{tb[k] // 1000}k/{tn[k]}/{100 * hl[k] / T.land:.1f}%" for k in range(1, T.nTeams + 1))
            + f"  内置AI:{100 * R['botLand'][i] / T.land:.1f}%")
        order = sorted(range(T.H), key=lambda p: -terr[p])[:n]
        print("    头部：" + "  ".join(f"{T.nm(p, t)} {terr[p]}格/{bal[p] // 1000}k({bal[p] / max(terr[p], 1):.0f})" for p in order if terr[p] > 0))


if __name__ == "__main__":
    main()
