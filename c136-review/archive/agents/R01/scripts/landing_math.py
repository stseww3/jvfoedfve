#!/usr/bin/env python3
"""landing_math.py — 每条登陆到本队号上的敌船，按引擎每格成本（game.js L1007–1010：2 + 2×def，def≈1.6×守方密度）换算：
  登陆时守方密度 → 每格价 → 这船兵够吃多少格；同一个号 --back 拍之前的密度下，同一船兵够吃多少格；
  以及该号从登陆到阵亡实际丢给这个对手多少格、多久阵亡。
用法：python3 landing_math.py <matchId> [--back 900] [--min 100000]
依赖 out/<matchId>/sea_landings.csv、resim_squad.csv、resim_pairs.csv、resim_events.csv、resim_meta.json。
"""
import csv, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
a = sys.argv[1:]
mid = a[0]
opt = lambda k, d=None: a[a.index('--' + k) + 1] if '--' + k in a else d
BACK, MIN = int(opt('back', 900)), int(opt('min', 100000))
D = os.path.join(HERE, '..', 'out', mid)
meta = json.load(open(os.path.join(D, 'resim_meta.json')))
names = meta['names']; seat = meta['squad']
sq = {}
for r in csv.DictReader(open(os.path.join(D, 'resim_squad.csv'))): sq[(r['bot'], int(r['t']))] = r
pairs = list(csv.DictReader(open(os.path.join(D, 'resim_pairs.csv'))))
ev = {int(r['p']): int(r['t']) for r in csv.DictReader(open(os.path.join(D, 'resim_events.csv'))) if r['ev'] == 'died'}
for r in csv.DictReader(open(os.path.join(D, 'sea_landings.csv'))):
    troops = int(r['troops'])
    if troops < MIN: continue
    t = int(r['t']); bot = r['bot']; d0 = float(r['botDens'])
    price0 = 2 + 3.2 * d0
    tb = max(k[1] for k in sq if k[0] == bot and k[1] <= t - BACK)
    rb = sq[(bot, tb)]
    d1 = float(rb['dens']); price1 = 2 + 3.2 * d1
    owner = names.index(r['owner'])
    lost = sum(int(p['px']) for p in pairs if int(p['victim']) == seat[bot] and int(p['attacker']) == owner and int(p['t1']) > t)
    died = ev.get(seat[bot])
    print(f"t={t} {r['owner']} → {bot}：船上 {troops} 兵 = 该号余额 {r['botBal']} 的 {100 * troops / max(1, int(r['botBal'])):.0f}%；"
          f"登陆时密度 {d0:.1f}（每格 {price0:.0f}，够吃 {troops / price0:.0f} 格）；{tb} 拍密度 {d1:.1f}（每格 {price1:.0f}，够吃 {troops / price1:.0f} 格）；"
          f"此后被它夺走 {lost} 格" + (f"，{died} 拍阵亡（登陆后 {died - t} 拍）" if died and died > t else ''))
