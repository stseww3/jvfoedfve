#!/usr/bin/env python3
"""lagstats.py — 卡顿波的三个汇总数（依据 shadow.json 与 resim.json，配对规则同 shadowcmp.match_bot）。

    python3 lagstats.py <matchId> [--side peer] [窗口边界，默认 0,540,1260,1800,2520,3500,99999]
[LA] 按影子决策拍分窗：影子要发的指令数 / 在录像里配上的（落地率）/ 配上的里落地时已无效的；
[LB] 按执行拍分窗：已执行指令数 / 生效=0 的 / 配上影子的时延中位、P90；
[LC] 每个服务器拍同一个号落地的指令条数分布（本编队 / 同房另一支 / 其它真人）。
"""
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r08lib as L  # noqa: E402
import shadowcmp as SC  # noqa: E402
from truth import Truth  # noqa: E402


def main():
    args = sys.argv[1:]
    mid = args[0]
    peer = "--side" in args and args[args.index("--side") + 1] == "peer"
    edges = [0, 540, 1260, 1800, 2520, 3500, 99999]
    for a in args[1:]:
        if "," in a:
            edges = [int(x) for x in a.split(",")]
    T = Truth(mid)
    S = json.load(open(os.path.join(L.OUT, mid, "shadow_peer.json" if peer else "shadow.json"), encoding="utf-8"))
    wins = list(zip(edges[:-1], edges[1:]))
    dec = defaultdict(lambda: [0, 0, 0])
    exe = defaultdict(lambda: [0, 0, []])
    for name, sb in S["bots"].items():
        real, sh, used, pairs = SC.match_bot(T, name, sb)
        okmap = {}
        for c, i, lag in pairs:
            w = next((k for k, (a, b) in enumerate(wins) if a <= c[0] < b), None)
            if w is not None:
                exe[w][0] += 1
                exe[w][1] += 0 if c[5] else 1
                if i is not None:
                    exe[w][2].append(lag)
            if i is not None:
                okmap[i] = c[5]
        for i, s in enumerate(sh):
            w = next((k for k, (a, b) in enumerate(wins) if a <= s[0] < b), None)
            if w is None:
                continue
            dec[w][0] += 1
            if used[i]:
                dec[w][1] += 1
                dec[w][2] += 0 if okmap.get(i) else 1
    print(f"[LA] {mid}{'（同房另一支）' if peer else ''} 按影子决策拍：窗口 | 影子要发 | 录像里配上（落地率）| 配上的里落地时无效")
    for k, (a, b) in enumerate(wins):
        d = dec[k]
        if d[0]:
            print(f"  {a}~{b} | {d[0]} | {d[1]}（{round(100 * d[1] / d[0])}%）| {d[2]}")
    print("[LB] 按执行拍：窗口 | 已执行 | 生效=0 | 配上影子的 | 时延 中位 / P90 / 最大")
    for k, (a, b) in enumerate(wins):
        e = exe[k]
        if e[0]:
            ls = sorted(e[2])
            md = ls[len(ls) // 2] if ls else "-"
            p90 = ls[min(len(ls) - 1, int(0.9 * len(ls)))] if ls else "-"
            print(f"  {a}~{b} | {e[0]} | {e[1]}（{round(100 * e[1] / e[0])}%）| {len(ls)} | {md} / {p90} / {ls[-1] if ls else '-'}")
    per = defaultdict(lambda: defaultdict(int))
    cnt = defaultdict(int)
    for c in T.R["cmdLog"]:
        if c[2] in (1, 2, 3):
            cnt[(c[1], c[0])] += 1
    for (p, t), n in cnt.items():
        g = "本编队" if p in T.sqIds else "同房另一支" if p in T.peerIds else "其它真人"
        per[g][min(n, 10)] += 1
    print("[LC] 同一个号在同一个服务器拍落地的指令条数分布（条数:次数）")
    for g in ("本编队", "同房另一支", "其它真人"):
        if per[g]:
            print(f"  {g}: " + " ".join(f"{n}:{v}" for n, v in sorted(per[g].items())))


if __name__ == "__main__":
    main()
