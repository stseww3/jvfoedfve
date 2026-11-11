#!/usr/bin/env python3
"""dispatch_survey.py — 从 events.csv 机械统计各局 HL-DISPATCH 的 kind/pct/boxedIn/dMe/dAlly 分布，
用来反推“实际部署版本”的捐款阈值，并与 src/strategy/v27-team-c116.js 的常量对账。
用法: python3 dispatch_survey.py [matchId ...]   (缺省 = R01 的 15 局)
"""
import csv, sys, os, collections
DATA = '/agent/repos/c136-data/bundles'
MINE = ['A057','A059','A094','A055','A075','A054','A031','A019','A009','A023','A050','A003','A005','B039','B043']
ids = sys.argv[1:] or MINE
for mid in ids:
    p = os.path.join(DATA, mid, 'events.csv')
    if not os.path.exists(p):
        print(mid, 'NO events.csv'); continue
    rows = list(csv.DictReader(open(p)))
    types = collections.Counter(r['type'] for r in rows)
    print(f'== {mid} events={len(rows)} types={dict(types)}')
    d = [r for r in rows if r['type'] == 'DISPATCH']
    if not d:
        continue
    by = collections.defaultdict(list)
    for r in d:
        by[(r['kind'], r['boxedIn'])].append(r)
    for k, rs in sorted(by.items()):
        pcts = collections.Counter(int(r['pct']) for r in rs)
        dme = sorted(float(r['dMe']) for r in rs)
        dal = sorted(float(r['dAlly']) for r in rs if r['dAlly'] not in ('', None))
        bal = sorted(int(r['myBal']) for r in rs)
        rej = sum(1 for r in rs if r['likelyRejected'] == 'True')
        gap = sum(1 for r in rs if float(r['dMe']) < float(r['dAlly']))
        top = ', '.join(f'{p}x{c}' for p, c in pcts.most_common(6))
        print(f'  {k[0]:20s} boxedIn={k[1]:5s} n={len(rs):4d} rej={rej:4d} pct[{top}] pctMin={min(pcts)} pctMax={max(pcts)} '
              f'dMe[min={dme[0]:.0f} med={dme[len(dme)//2]:.0f} max={dme[-1]:.0f}] dAlly[min={dal[0]:.0f} med={dal[len(dal)//2]:.0f} max={dal[-1]:.0f}] '
              f'myBalMin={bal[0]} dMe<dAlly={gap}')
    # per-bot min interval
    last = {}
    mingap = {}
    for r in sorted(d, key=lambda r: int(r['t'])):
        b = r['bot']; t = int(r['t'])
        if b in last:
            g = t - last[b]
            mingap[b] = min(mingap.get(b, 10**9), g)
        last[b] = t
    if mingap:
        print('  per-bot min interval between DISPATCH:', min(mingap.values()), ' t range:', min(int(r['t']) for r in d), '-', max(int(r['t']) for r in d))
