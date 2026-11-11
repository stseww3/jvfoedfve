#!/usr/bin/env python3
"""perhead.py <matchId> [t1,t2,...] —— 真值（out/<mid>/resim.json）里本编队和房间里其他真人的人均对照。

用法：timeout 60 python3 perhead.py B019 270,630,900,1080,1240
  [PH-A] 各时刻：还有地的号数、地合计（占陆地 %）、人均地、人均兵；编队人均地 ÷ 其他真人人均地。
  [PH-B] 相邻两个时刻之间：已执行的陆攻条数、其中生效的条数、生效陆攻派出的兵；按期初还活着的人数摊人均。
  [PH-C] 录像末拍每个编队号贴着谁（按接触的边界格数排前 8 个；* = 本编队的号）。
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import r08lib as L  # noqa: E402


def main():
    mid = sys.argv[1]
    R = json.load(open(os.path.join(L.OUT, mid, "resim.json")))
    H, teams, names, land = R["H"], R["teams"], R["names"], R["land"]
    squad = {b: s["id"] for b, s in R["squad"].items() if s["id"] >= 0 and not s.get("peer")}
    ids = set(squad.values())
    inv = {v: k for k, v in squad.items()}
    snapT = R["snapT"]
    if len(sys.argv) > 2:
        ts = [int(x) for x in sys.argv[2].split(",")]
    else:
        ts = [t for t in (270, 630, 900, 1080, 1260, 1800, 2700, 3600) if t <= R["endTick"]] + [snapT[-1]]
    ts = [t for t in ts if t in snapT]

    print("[PH-A] %s 人均对照（真值）：拍 | 本编队 号数 / 地合计（占陆地 %%）/ 人均地 / 人均兵 | 其他真人 同口径 | 编队人均地 ÷ 其他真人人均地" % mid)
    for t in ts:
        i = snapT.index(t)
        st = [(R["snapTerr"][i][p], R["snapBal"][i][p]) for p in ids if R["snapTerr"][i][p] > 0]
        wt = [(R["snapTerr"][i][p], R["snapBal"][i][p]) for p in range(H) if p not in ids and R["snapTerr"][i][p] > 0]
        if not st or not wt:
            continue
        sa, sb = sum(x[0] for x in st), sum(x[1] for x in st)
        wa, wb = sum(x[0] for x in wt), sum(x[1] for x in wt)
        print("     %5d | %d / %d（%.2f%%）/ %d / %d | %d / %d（%.2f%%）/ %d / %d | %.2f" % (
            t, len(st), sa, 100 * sa / land, sa / len(st), sb / len(st), len(wt), wa, 100 * wa / land, wa / len(wt), wb / len(wt),
            (sa / len(st)) / (wa / len(wt))))

    print("[PH-B] 陆攻对照（真值）：窗 | 本编队 已执行 / 生效 / 生效的派出兵 / 人数 → 人均生效条数、人均派出兵 | 其他真人 同口径")
    edges = [0] + ts
    for a, b in zip(edges, edges[1:]):
        row = []
        for sel in (lambda p: p in ids, lambda p: p < H and p not in ids):
            rows = [c for c in R["cmdLog"] if a < c[0] <= b and sel(c[1]) and c[2] == 1]
            heads = len([p for p in range(H) if sel(p) and (R["deathT"][p] < 0 or R["deathT"][p] > a)])
            ok = [c for c in rows if c[5]]
            troops = sum(c[6] for c in ok)
            row.append("%d / %d / %d / %d → %.1f、%d" % (len(rows), len(ok), troops, heads, len(ok) / max(heads, 1), troops / max(heads, 1)))
        print("     (%d,%d] | %s | %s" % (a, b, row[0], row[1]))

    def lab(p):
        if p == 512:
            return "空地"
        if p >= H:
            return "AI%d" % p
        return "%s%s(%d,T%d)" % ("*" if p in ids else "", inv.get(p, names[p]), p, teams[p])

    print("[PH-C] 录像末拍各编队号贴着谁：号(玩家号,队) 地 / 兵 / 包围盒 x0,y0,x1,y1 | 邻居:接触的边界格数")
    i = len(snapT) - 1
    for b, s in sorted(R["sq"].items(), key=lambda kv: (teams[squad[kv[0]]], squad[kv[0]]) if kv[0] in squad else (9, 0)):
        if b not in squad or not s["nb"]:
            continue
        t, nb = s["nb"][-1]
        box = s["box"][-1]
        p = squad[b]
        items = sorted(nb, key=lambda x: -x[1])
        print("     %s(%d,T%d) %d / %d / %s | t=%d %s" % (b, p, teams[p], R["snapTerr"][i][p], R["snapBal"][i][p], ",".join(str(x) for x in box[1:]), t,
                                                     " ".join("%s:%d" % (lab(int(q)), n) for q, n in items[:8])))


if __name__ == "__main__":
    main()
