#!/usr/bin/env python3
"""exchange_price.py — 换地的“单价”对比：本队夺来的格子和丢掉的格子，按引擎每格成本公式（game.js L1007–1010：
进攻方每格付 2 + 2×def，def = 守方余额/(1+10×守方领土/16) ≈ 1.6×守方密度，即每格约 2+3.2×守方密度；守方每格掉 def）
用 90 拍采样窗口起点的守方密度估算：
  · 本队夺地：Σ格 ×(2+3.2×对手密度) = 本队按公式该付的兵；
  · 本队丢地：Σ格 ×(2+3.2×本队那个号的密度) = 对手按公式该付的兵；本队同时掉 Σ格×1.6×密度。
用法：python3 exchange_price.py <matchId> [--windows 1530-3960,3960-5130,...] [--by-bot]
依赖 out/<matchId>/resim_pairs.csv、resim_players.csv、resim_meta.json。
"""
import csv, json, os, sys
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
a = sys.argv[1:]
mid = a[0]
opt = lambda k, d=None: a[a.index('--' + k) + 1] if '--' + k in a else d
D = os.path.join(HERE, '..', 'out', mid)
meta = json.load(open(os.path.join(D, 'resim_meta.json')))
H = meta['humans']; seat = {v: k for k, v in meta['squad'].items()}
dens = {}
for r in csv.DictReader(open(os.path.join(D, 'resim_players.csv'))):
    dens[(int(r['t']), int(r['p']))] = (int(r['bal']), int(r['terr']))
pairs = list(csv.DictReader(open(os.path.join(D, 'resim_pairs.csv'))))
wins = [tuple(map(int, w.split('-'))) for w in opt('windows', '1530-3960,3960-5130,5130-7200,7200-9000').split(',')]
def cost(n, bal, terr):
    d = bal / max(1, terr)
    return n * (2 + 3.2 * d), n * 1.6 * d, d
for t0, t1 in wins:
    g = defaultdict(lambda: [0, 0.0, 0.0, 0.0])   # cells, attackerCost, defenderLoss, dens*cells
    per = defaultdict(lambda: [0, 0.0, 0.0])
    for r in pairs:
        a0, b0 = int(r['t0']), int(r['t1'])
        if not (t0 <= a0 and b0 <= t1): continue
        v, at, n = int(r['victim']), int(r['attacker']), int(r['px'])
        if v < 0 or v >= H or at >= H: continue
        bt = dens.get((a0, v))
        if not bt or bt[1] <= 0: continue
        c, l, d = cost(n, *bt)
        if at in seat and v not in seat:
            k = '夺'; g[k][0] += n; g[k][1] += c; g[k][2] += l; g[k][3] += d * n
        elif v in seat and at not in seat:
            k = '丢'; g[k][0] += n; g[k][1] += c; g[k][2] += l; g[k][3] += d * n
            per[seat[v]][0] += n; per[seat[v]][1] += c; per[seat[v]][2] += d * n
    out = []
    for k in ('夺', '丢'):
        n, c, l, dn = g[k]
        if n: out.append(f"{k} {n} 格：守方密度（按格加权）{dn / n:.1f}，进攻方按公式每格 {c / n:.0f}（合计 {c:.0f}），守方每格掉 {l / n:.0f}")
    print(f"== [{t0},{t1}] " + ' | '.join(out))
    if '--by-bot' in a:
        for b, (n, c, dn) in sorted(per.items(), key=lambda kv: -kv[1][0]):
            print(f"     丢地 {b}: {n} 格，丢地时密度（按格加权）{dn / n:.1f}，对手每格 {c / n:.0f}")
