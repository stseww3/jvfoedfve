#!/usr/bin/env python3
# pair_war.py — 我方某个号与某个对手之间的「消耗战」分窗账（全部来自 match_truth.mjs 真值 JSON 的 pairsW，100 拍一格）。
#   每窗：我方投兵 / 拿到的地 / 打掉对方的存兵；对方投兵 / 拿走的地 / 打掉我方的存兵；窗末双方 地、兵、密度。
#   末尾：合计、每格地的兵价（投兵÷拿地）、净地、净兵。
# 用法：python3 scripts/pair_war.py <matchId> --a ryan_m [--b 8,5,6] [--win 300] [--t0 0 --t1 99999]
#   --b 省略 = 该号所有真人对手（按双方投兵合计排序，取前 6）
import json, sys
from collections import defaultdict

a = sys.argv[1:]
MID = a[0]
val = lambda k, d: (a[a.index(k) + 1] if k in a else d)
J = json.load(open(f'/tmp/c136-r05/truth/{MID}.json'))
H = J['humans']
P = {p['id']: p for p in J['players']}
sq = {s['bot']: s['p'] for s in J['squad']}
A = sq[val('--a', J['squad'][0]['bot'])]
WIN = int(val('--win', 300)); T0 = int(val('--t0', 0)); T1 = int(val('--t1', 99999))
HS = J['HS']; hs_t = HS['t']
k = lambda v: f'{v / 1e6:.2f}M' if abs(v) >= 1e6 else (f'{v / 1e3:.0f}k' if abs(v) >= 1e4 else str(int(v)))
name = lambda p: f"{P[p]['name'][:16]}(#{p},T{P[p]['team']})" if p < H else ('中立' if p == 512 else f'机器人#{p}')
W = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))   # (a,b) -> w -> [sent, tiles, balDmg]
for r in J['pairsW']:
    x = W[(r['a'], r['b'])][r['w']]
    x[0] += r['sent']; x[1] += r['tiles']; x[2] += r['balDmg']
if '--b' in a:
    Bs = [int(x) for x in val('--b', '').split(',')]
else:
    tot = defaultdict(int)
    for (x, y), d in W.items():
        if x == A and y < H:
            tot[y] += sum(v[0] for v in d.values())
        if y == A and x < H:
            tot[x] += sum(v[0] for v in d.values())
    Bs = [p for p, _ in sorted(tot.items(), key=lambda z: -z[1])[:6]]


def state(p, t):
    # HS 每 300 拍一采；取 ≤ t 的最近一采
    i = max([j for j, tt in enumerate(hs_t) if tt <= t] or [0])
    L = HS['terr'][i][p] if isinstance(HS['terr'][i], list) else HS['terr'][i].get(str(p), 0)
    Bv = HS['bal'][i][p] if isinstance(HS['bal'][i], list) else HS['bal'][i].get(str(p), 0)
    return hs_t[i], L, Bv


print(f'# {MID} {name(A)} 的消耗战分窗账（窗 {WIN} 拍；pairsW 100 拍一格）')
for b in Bs:
    out = W[(A, b)]; inn = W[(b, A)]
    ws = sorted(set(out) | set(inn))
    if not ws:
        continue
    print(f'== 对 {name(b)}：峰值地 {P[b]["peakTerr"]}@{P[b]["peakT"]} 离场 {P[b]["leftT"]} 阵亡 {P[b]["deathT"]} ==')
    S = [0] * 6
    lo = (min(ws) * 100 // WIN) * WIN
    while lo <= max(ws) * 100:
        hi = lo + WIN
        if hi > T0 and lo < T1:
            o = [sum(out[w][i] for w in out if lo <= w * 100 < hi) for i in range(3)]
            n = [sum(inn[w][i] for w in inn if lo <= w * 100 < hi) for i in range(3)]
            if any(o) or any(n):
                for i in range(3):
                    S[i] += o[i]; S[3 + i] += n[i]
                ta, La, Ba = state(A, hi); tb, Lb, Bb = state(b, hi)
                print(f'  {lo}–{hi}: 我方投 {k(o[0])} 拿地 {o[1]} 打掉存兵 {k(o[2])}{f"（{o[0] / o[1]:.0f} 兵/格）" if o[1] else ""}｜对方投 {k(n[0])} 拿地 {n[1]} 打掉我方存兵 {k(n[2])}{f"（{n[0] / n[1]:.0f} 兵/格）" if n[1] else ""}｜t={ta} 我方 {La}/{k(Ba)}/{Ba / max(1, La):.0f}；对方 {Lb}/{k(Bb)}/{Bb / max(1, Lb):.0f}')
        lo = hi
    print(f'  合计：我方投 {k(S[0])} 拿地 {S[1]} 打掉对方存兵 {k(S[2])}（{S[0] / max(1, S[1]):.0f} 兵/格）｜对方投 {k(S[3])} 拿地 {S[4]} 打掉我方存兵 {k(S[5])}（{S[3] / max(1, S[4]):.0f} 兵/格）｜净地 {S[1] - S[4]:+d}｜我方投兵+被打掉 {k(S[0] + S[5])}，对方投兵+被打掉 {k(S[3] + S[2])}')
