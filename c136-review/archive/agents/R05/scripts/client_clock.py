#!/usr/bin/env python3
"""client_clock.py — 用对局包 results.csv 的墙上时间，量每个号的客户端在上报结果那一刻落后服务器多少拍。

口径：
  results.csv 每个号一行：event（died/left/won…）、tick（客户端上报时自己的本地拍）、at（上报的墙上时间，毫秒）。
  「阵亡」的行：本地拍应当紧挨着录像里的阵亡拍（真值 died 事件）。用这些行（本地拍 − 录像阵亡拍 ≤ --tol 拍的）
      对（at, tick）做最小二乘直线，得到服务器每拍多少毫秒、以及任一墙上时间对应的服务器拍。
  其他行（left 等）：服务器拍（由直线推出）− 本地拍 = 客户端落后的拍数。
  另外并排列出：该号最后一条 [HL-TICK] 日志的拍（traj.csv）、最后一条落地指令的拍（录像真值）、录像里的阵亡拍与离场拍，
      以及 sent / accepted 两列（sent − accepted 与影子的「同拍第二条被拒」条数对照）。
用法：python3 scripts/client_clock.py <matchId> [--tol 8]
"""
import csv
import json
import sys
from datetime import datetime

a = sys.argv[1:]
mid = a[0]
TOL = int(a[a.index('--tol') + 1]) if '--tol' in a else 8
B = f'/agent/repos/c136-data/bundles/{mid}'
J = json.load(open(f'/tmp/c136-r05/truth/{mid}.json'))
sq = {s['bot']: s['p'] for s in J['squad']}
P = {p['id']: p for p in J['players']}
rows = list(csv.DictReader(open(f'{B}/results.csv', encoding='utf-8')))
last_log = {}
for r in csv.DictReader(open(f'{B}/traj.csv', encoding='utf-8')):
    last_log[r['bot']] = max(last_log.get(r['bot'], 0), int(r['t']))
last_cmd = {}
leave_t = {}
for e in J['events']:
    if e['type'] in ('attack', 'boat', 'donate') and e.get('p') in P:
        last_cmd[e['p']] = max(last_cmd.get(e['p'], 0), e['t'])
    if e['type'] == 'leave':
        leave_t[e['p']] = e['t']


def ms(s):
    return datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp() * 1000


pts = []
for r in rows:
    p = sq.get(r['bot'])
    if p is None:
        continue
    r['_ms'] = ms(r['at'])
    r['_tick'] = int(r['tick'])
    r['_death'] = P[p]['deathT']
    if r['event'] == 'died' and r['_death'] >= 0 and 0 <= r['_tick'] - r['_death'] <= TOL:
        pts.append((r['_ms'], r['_tick']))
n = len(pts)
if n < 2:
    print(f'{mid}: 阵亡行不足 2 条，拟合不了服务器时钟')
    sys.exit(0)
mx = sum(x for x, _ in pts) / n
my = sum(y for _, y in pts) / n
sxx = sum((x - mx) ** 2 for x, _ in pts)
sxy = sum((x - mx) * (y - my) for x, y in pts)
slope = sxy / sxx          # 拍 / 毫秒
resid = [y - (my + slope * (x - mx)) for x, y in pts]
print(f'{mid}: 用 {n} 条阵亡行拟合服务器时钟：每拍 {1 / slope:.2f} 毫秒；拟合残差 最大 {max(abs(x) for x in resid):.1f} 拍')
tot_sent = tot_acc = 0
for r in sorted((r for r in rows if '_ms' in r), key=lambda r: r['_ms']):
    p = sq[r['bot']]
    srv = my + slope * (r['_ms'] - mx)
    lag = srv - r['_tick']
    sent, acc = int(r['sent'] or 0), int(r['accepted'] or 0)
    tot_sent += sent
    tot_acc += acc
    print(f'   {r["bot"]}: {r["event"]}｜上报时本地拍 {r["_tick"]}（地 {r["lastTerritory"]}、兵 {r["balance"]}）｜当时服务器约在 {srv:.0f} 拍 → 客户端落后 {lag:.0f} 拍（{lag / slope / 1000:.1f} 秒）'
          f'｜录像：阵亡 {r["_death"]}、离场 {leave_t.get(p, -1)}｜最后一条日志 t={last_log.get(r["bot"], -1)}、最后一条落地指令 t={last_cmd.get(p, -1)}'
          f'｜sent {sent} accepted {acc}（差 {sent - acc}）')
print(f'   合计 sent {tot_sent}、accepted {tot_acc}（差 {tot_sent - tot_acc}）')
