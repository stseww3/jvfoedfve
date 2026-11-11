#!/usr/bin/env python3
"""target_price.py — 一个对手在不同拍的“每格价”（引擎 game.js L1007–1010：进攻方每格付 2 + 2×def，def≈1.6×守方密度）
和本队实际在它身上花的兵、拿到的格子对照，用来回答“早打和晚打差多少”。
用法：python3 target_price.py <matchId> --targets 1,24,35 [--ticks 1530,1800,2070,2250]
输出：每个目标在各拍的领土/余额/密度/公式每格价；本队对它的进攻（首末落地拍、条数、实扣合计）、夺到的格子、每格实扣；
      以及“按各拍公式价买同样多格子”的合计。
依赖 out/<matchId>/resim_players.csv、resim_pairs.csv、shadow_match.csv、resim_meta.json。
"""
import csv, json, os, sys
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
a = sys.argv[1:]
mid = a[0]
opt = lambda k, d=None: a[a.index('--' + k) + 1] if '--' + k in a else d
D = os.path.join(HERE, '..', 'out', mid)
meta = json.load(open(os.path.join(D, 'resim_meta.json')))
names, teams, H = meta['names'], meta['teams'], meta['humans']
seat = {v: k for k, v in meta['squad'].items()}
targets = [int(x) for x in opt('targets').split(',')]
ticks = [int(x) for x in opt('ticks', '1530,1800,2070,2250,2520,2970').split(',')]
P = defaultdict(dict)
for r in csv.DictReader(open(os.path.join(D, 'resim_players.csv'))):
    P[int(r['p'])][int(r['t'])] = (int(r['terr']), int(r['bal']), r['alive'])
pairs = list(csv.DictReader(open(os.path.join(D, 'resim_pairs.csv'))))
mt = [x for x in csv.DictReader(open(os.path.join(D, 'shadow_match.csv'))) if x['kind'] == 'attack' and x['applied'] == '1']
for q in targets:
    nm = f"{names[q]}/T{teams[str(q)]}"
    print(f"== {nm}（席位 {q}）")
    price = {}
    for t in ticks:
        if t in P[q] and P[q][t][2] == '1' and P[q][t][0] > 0:
            terr, bal, _ = P[q][t]
            d = bal / terr
            price[t] = 2 + 3.2 * d
            print(f"   t={t} 领土 {terr} 余额 {bal} 密度 {d:.1f} 公式每格价 {price[t]:.0f}（整块 {terr * price[t]:.0f}）")
    got = defaultdict(int)
    for r in pairs:
        if int(r['victim']) == q and int(r['attacker']) in seat: got[seat[int(r['attacker'])]] += int(r['px'])
    sp = defaultdict(lambda: [0, 0, 10**9, 0])
    for x in mt:
        if x['targetName'] == names[q]:
            s = sp[x['bot']]; s[0] += 1; s[1] += int(float(x['spent'] or 0)); s[2] = min(s[2], int(x['tick'])); s[3] = max(s[3], int(x['tick']))
    tot_c, tot_s = sum(got.values()), sum(s[1] for s in sp.values())
    for b in sorted(set(got) | set(sp)):
        s = sp.get(b, [0, 0, 0, 0])
        print(f"   {b}: 进攻落地 {s[0]} 条（{s[2]}–{s[3]} 拍）实扣 {s[1]}，夺 {got.get(b, 0)} 格")
    if tot_c:
        print(f"   本队合计：实扣 {tot_s}，夺 {tot_c} 格，每格实扣 {tot_s / tot_c:.0f}；同样 {tot_c} 格按各拍公式价：" + '，'.join(f"{t} 拍 {tot_c * p:.0f}" for t, p in price.items()))
