#!/usr/bin/env python3
"""snapq.py — 从重放缓存里打出若干真人席位在若干拍的 地 / 余额 / 密度（不重跑重放；快照每 10 拍一行）。

用法：
  python3 scripts/snapq.py <mid> <席位或名字片段[,…]|squad> <t1,t2,…|t0:t1:步长> [--sum] [--press]
  --sum    末尾加一列：所列席位的地、余额合计
  --press  另起一段：pairLog 里这些席位在相邻两个采样拍之间「被谁打掉多少格/多少余额」「对谁烧了多少兵/得多少格」
名字片段匹配真人名字（大小写敏感、子串）；编队号可直接写 kaito9。
pairLog 每行：[拍(每 30 拍一桶), 攻方, 守方, 得地, 攻方烧的兵, 守方掉的余额, 守方反击槽被消, 桶长]
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
NEUTRAL = 512


def k(v):
    v = float(v)
    a = abs(v)
    if a >= 1e6:
        return "%.2fM" % (v / 1e6)
    if a >= 1e4:
        return "%.0fk" % (v / 1e3)
    if a >= 1e3:
        return "%.1fk" % (v / 1e3)
    return "%d" % v


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 3:
        print(__doc__)
        sys.exit(2)
    mid, who, ts = args[0], args[1], args[2]
    d = json.load(open(os.path.join(ROOT, "out", "cache", f"{mid}-resim.json")))
    H, names, teams = d["H"], d["names"], d["teams"]
    sq = {v["id"]: n for n, v in d["squad"].items()}

    def nm(p):
        if p == NEUTRAL:
            return "无主地"
        if p in sq:
            return sq[p]
        if p < H:
            return f"{names[p][:12]}#{p}T{teams[p]}"
        return f"AI{p}"

    ids = []
    if who == "squad":
        ids = sorted(sq)
    else:
        for w in who.split(","):
            if w.isdigit():
                ids.append(int(w))
            elif w in d["squad"]:
                ids.append(d["squad"][w]["id"])
            else:
                hit = [p for p in range(H) if w in names[p]]
                if not hit:
                    print(f"找不到 {w}")
                    sys.exit(2)
                ids.extend(hit)
    if ":" in ts:
        a, b, c = (int(x) for x in ts.split(":"))
        tl = list(range(a, b + 1, c))
    else:
        tl = [int(x) for x in ts.split(",")]
    snapT = d["snapT"]
    idx = {t: i for i, t in enumerate(snapT)}
    print(f"# {mid} 快照：" + "、".join(f"{nm(p)}" for p in ids) + "（每格：地 / 余额 / 密度）")
    for t in tl:
        tt = t if t in idx else min(snapT, key=lambda x: abs(x - t))
        i = idx[tt]
        cells = []
        sl = sb = 0
        for p in ids:
            L, B = d["snapTerr"][i][p], d["snapBal"][i][p]
            sl += L
            sb += B
            cells.append(f"{nm(p)} {L}/{k(B)}/{(B / L if L else 0):.0f}")
        line = f"{tt:5d} | " + " | ".join(cells)
        if "--sum" in sys.argv:
            line += f" || 合计 地 {sl} 兵 {k(sb)}"
        print(line)
    if "--press" in sys.argv:
        print("# 相邻采样拍之间的交战（pairLog；只列涉及所列席位的）")
        S = set(ids)
        for a, b in zip(tl, tl[1:]):
            agg = {}
            for r in d["pairLog"]:
                t, atk, dfn, gain, burn, lostB, slot = r[:7]
                if a <= t < b and (atk in S or dfn in S):
                    key = (atk, dfn)
                    x = agg.setdefault(key, [0, 0, 0, 0])
                    x[0] += gain
                    x[1] += burn
                    x[2] += lostB
                    x[3] += slot
            if not agg:
                continue
            print(f"  {a}~{b}：" + "；".join(f"{nm(x)}→{nm(y)} 得地 {v[0]} 烧 {k(v[1])} 对方掉 {k(v[2])}" + (f" 槽消 {k(v[3])}" if v[3] else "")
                                         for (x, y), v in sorted(agg.items(), key=lambda kv: -kv[1][1])[:8]))


if __name__ == "__main__":
    main()
