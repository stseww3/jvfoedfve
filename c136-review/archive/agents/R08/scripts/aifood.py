#!/usr/bin/env python3
"""aifood.py — 内置 AI「口粮」账：每个号的每个内置 AI 邻居在各时刻的地/兵/每格价（2+1.78×兵/地），
对照策略的买入门槛 winWorth = winR×t×自己密度（c110/g09 的 botOk，t<dpEnd 时生效），以及这个 AI 最后被谁、几拍、多少兵一格吃掉。

    python3 aifood.py <matchId> [--bot <名字>] [--winR 0.002] [--dpEnd 1500]
不带 --bot 时输出全队汇总：各时刻「接壤的内置 AI 里，门槛允许买的占几成」。
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from truth import Truth, NEUTRAL  # noqa: E402


def main():
    args = sys.argv[1:]
    mid = args[0]
    T = Truth(mid)
    R = T.R
    opt = lambda k, d=None: args[args.index(k) + 1] if k in args else d  # noqa: E731
    winR = float(opt("--winR", 0.002))
    dpEnd = int(opt("--dpEnd", 1500))
    ai = {}
    for t, lst in R.get("snapAi", []):
        ai[t] = {p: (terr, bal) for p, terr, bal in lst}
    eat = defaultdict(lambda: defaultdict(lambda: [0, 0, 99999, 0]))
    for t, a, d, tiles, burnt, dB, dS, n in R["pairLog"]:
        if T.H <= d < NEUTRAL and tiles > 0:
            e = eat[d][a]
            e[0] += tiles
            e[1] += burnt
            e[2] = min(e[2], t)
            e[3] = max(e[3], t)
    only = opt("--bot")
    tot = defaultdict(lambda: [0, 0, 0, 0])   # t -> [有AI邻居的号数, AI邻居个数, 门槛允许的个数, 接壤格数]
    for name, info in sorted(R["squad"].items(), key=lambda kv: kv[1]["id"]):
        p = info["id"]
        if p < 0 or info.get("peer") or (only and name != only):
            continue
        s = R["sq"][name]
        seen = {}
        for rec in s["nb"]:
            t = rec[0]
            if t % 90 or t < 540 or t > dpEnd + 300:
                continue
            if T.terr(p, t) <= 0 or T.is_husk(p, t):
                continue
            dens = T.bal(p, t) / max(T.terr(p, t), 1)
            worth = winR * t * dens if t < dpEnd else float("inf")
            row = []
            for q, c in rec[1]:
                if not (T.H <= q < NEUTRAL):
                    continue
                st = ai.get(t, {}).get(q)
                if not st:
                    continue
                px = 2 + 1.78 * st[1] / max(st[0], 1)
                ok = px <= worth
                row.append((q, c, st[0], st[1], px, ok))
                seen[q] = 1
                tot[t][1] += 1
                tot[t][2] += 1 if ok else 0
                tot[t][3] += c
            if row:
                tot[t][0] += 1
            if only:
                print(f"t={t} {name} 地{T.terr(p, t)} 兵{T.bal(p, t)} 密度{dens:.1f} 门槛winWorth={worth:.1f}：" + "  ".join(
                    f"AI{q}[接壤{c} 地{te} 兵{ba} 每格价{px:.1f}{'✓' if ok else '✗'}]" for q, c, te, ba, px, ok in row))
        if only:
            for q in seen:
                es = sorted(eat[q].items(), key=lambda kv: -kv[1][0])[:3]
                print(f"   AI{q} 被吃：" + "；".join(f"{T.nm(a, v[2])} {v[0]}格 {v[1] / max(v[0], 1):.1f}兵/格 t={v[2]}~{v[3]}" for a, v in es))
    if not only:
        print("拍 | 有内置AI邻居的号数 | 内置AI邻居个数 | 其中门槛(winWorth)允许买 | 接壤格数合计")
        for t in sorted(tot):
            a, b, c, d = tot[t]
            print(f"  {t:5d} | {a:2d} | {b:3d} | {c:3d}（{100 * c / max(b, 1):.0f}%）| {d}")


if __name__ == "__main__":
    main()
