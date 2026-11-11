#!/usr/bin/env python3
"""roster.py — 从重放缓存里打出全部真人的名册：按队分组，每人 席位、名字、出生点、离线拍、出局拍、峰值地盘，
以及若干采样拍的 地%/余额（不重跑重放）。编队号前面带 *。

用法：
  python3 scripts/roster.py <mid> [t1,t2,…]        默认采样拍 630,1500,3000,4500,6000
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def k(v):
    if v >= 1e6:
        return f"{v / 1e6:.2f}M"
    if v >= 1e4:
        return f"{v / 1e3:.0f}k"
    if v >= 1e3:
        return f"{v / 1e3:.1f}k"
    return str(int(v))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        sys.exit(2)
    mid = args[0]
    d = json.load(open(os.path.join(ROOT, "out", "cache", f"{mid}-resim.json")))
    H, names, teams, land = d["H"], d["names"], d["teams"], d["land"]
    snapT = d["snapT"]
    ts = [int(x) for x in args[1].split(",")] if len(args) > 1 else [630, 1500, 3000, 4500, 6000]
    ts = [t for t in ts if t <= snapT[-1]]
    idx = {t: i for i, t in enumerate(snapT)}

    def at(t):
        if t in idx:
            return idx[t]
        return max(i for i, x in enumerate(snapT) if x <= t)

    sq = {v["id"]: n for n, v in d["squad"].items() if v["id"] >= 0 and not v.get("mismatch")}
    print(f"# {mid} 真人名册（{H} 人；全图陆地 {land} 格；录像到 {d['endTick']} 拍）；每个采样拍：地% / 余额")
    print("# 列：席位 名字 | 出生点 | 离线拍 出局拍 | 峰值（拍 格 %）| " + " | ".join(str(t) for t in ts))
    by_team = {}
    for p in range(H):
        by_team.setdefault(teams[p], []).append(p)
    for tm in sorted(by_team):
        ps = by_team[tm]
        tot = [sum(d["snapTerr"][at(t)][p] for p in ps) for t in ts]
        print(f"队{tm}（{len(ps)} 人）合计地%：" + " | ".join(f"{t}:{v / land * 100:.1f}" for t, v in zip(ts, tot)))
        for p in sorted(ps, key=lambda p: -max(d["snapTerr"][i][p] for i in range(len(snapT)))):
            best = max(range(len(snapT)), key=lambda i: d["snapTerr"][i][p])
            pk = d["snapTerr"][best][p]
            lt, dt = d["leftT"][p], d["deathT"][p]
            xy = d["spawnXY"][p] if d.get("spawnXY") else None
            cells = " | ".join(f"{d['snapTerr'][at(t)][p] / land * 100:.2f}/{k(d['snapBal'][at(t)][p])}" for t in ts)
            nm = ("*" + sq[p]) if p in sq else names[p][:18]
            print(f"  #{p:<3} {nm:<19} | {('(%d,%d)' % tuple(xy)) if xy else '—':<11} | 离线 {lt if lt is not None and lt >= 0 else '—':>5} 出局 {dt if dt is not None and dt >= 0 else '—':>5} | "
                  f"峰值 {snapT[best]:>5} 拍 {pk:>6} 格 {pk / land * 100:5.2f}% | {cells}")


if __name__ == "__main__":
    main()
