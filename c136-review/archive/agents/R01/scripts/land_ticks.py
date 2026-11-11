#!/usr/bin/env python3
"""land_ticks.py — 每个号的指令是“细水长流”地落地，还是隔很久才成组落地一次。
对每个号列出它在录像里的落地拍（一个落地拍 = 该号至少一条进攻/捐兵指令在这一拍被引擎执行）：
  * 相邻两个落地拍的间隔（中位、最大），每个落地拍落地几条；
  * 每组落地指令对应的决策拍范围（shadow_match 的 tDecide），以及“最新一条的延迟”= 落地拍 − 组内最大的决策拍
    （这一拍发出的令最快也要这么久才到 → 客户端本地拍落后服务器拍的上界估计）；
  * 相邻两组之间，策略受理了但录像里找不到的指令条数（shadow_cmds 里 ok=1、不含船、决策拍在两组的决策拍之间）。
用法：python3 land_ticks.py <matchId> [--t0 a --t1 b] [--bot name] [--list] [--win 300]
  默认只打每个号的汇总和按 --win 拍分窗的全队表；--list 把每个落地拍逐行列出（配 --bot 用）。
依赖 out/<id>/shadow_match.csv、shadow_cmds.csv、resim_meta.json。
"""
import csv, json, os, statistics as st, sys
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
a = sys.argv[1:]
mid = a[0]
opt = lambda k, d=None: a[a.index('--' + k) + 1] if '--' + k in a else d
T0 = int(opt('t0', 0)); T1 = int(opt('t1', 10 ** 9)); WIN = int(opt('win', 300)); ONLY = opt('bot')
OUT = os.path.join(HERE, '..', 'out', mid)
mt = [r for r in csv.DictReader(open(os.path.join(OUT, 'shadow_match.csv'))) if r['kind'] in ('attack', 'donate')]
cm = [r for r in csv.DictReader(open(os.path.join(OUT, 'shadow_cmds.csv'))) if r['ok'] == '1' and r['kind'] != 'boatTo']
bots = sorted({r['bot'] for r in mt})
groups = defaultdict(lambda: defaultdict(list))   # bot -> landing tick -> rows
for r in mt:
    groups[r['bot']][int(r['tick'])].append(r)
issued = defaultdict(list)
for r in cm:
    issued[r['bot']].append(int(r['t']))
print(f'== {mid} 各号的落地拍 [{T0},{min(T1, 99999)}]（一个落地拍 = 这一拍至少有一条该号的进攻/捐兵指令被执行）')
print('   号 | 落地拍个数 落地条数 | 相邻落地拍间隔 中位/最大 | 一拍落地 >=8 条的次数 | 受理条数（不含船）| 落地/受理 | “最新一条的延迟”中位/最大（只算配上决策拍的组）')
allrows = []
for b in bots:
    if ONLY and b != ONLY: continue
    ticks = sorted(t for t in groups[b] if T0 <= t <= T1)
    if not ticks: continue
    gaps = [y - x for x, y in zip(ticks, ticks[1:])]
    n = sum(len(groups[b][t]) for t in ticks)
    big = sum(1 for t in ticks if len(groups[b][t]) >= 8)
    acc = sum(1 for t in issued[b] if T0 <= t <= T1)
    fresh = []
    for t in ticks:
        d = [int(r['tDecide']) for r in groups[b][t] if r['tDecide'] != '']
        if d:
            fresh.append(t - max(d)); allrows.append((t, b, len(groups[b][t]), min(d), max(d), t - max(d)))
        else:
            allrows.append((t, b, len(groups[b][t]), None, None, None))
    g = f'{st.median(gaps):.0f}/{max(gaps)}' if gaps else '-'
    f = f'{st.median(fresh):.0f}/{max(fresh)}' if fresh else '-'
    print(f'   {b:8s} | {len(ticks):3d} {n:4d} | {g:>9s} | {big:2d} | {acc:4d} | {n / acc * 100 if acc else 0:5.1f}% | {f}')
allrows.sort()
print(f'== 全队按落地拍每 {WIN} 拍一窗：落地拍个数（各号合计）/ 落地条数 / 其中一拍 >=8 条的组数 | 相邻落地拍间隔（同一号内）中位 | “最新一条的延迟”最小/中位/最大')
lo = (min(r[0] for r in allrows) // WIN) * WIN if allrows else 0
hi = max(r[0] for r in allrows) if allrows else 0
prev = {}
gapw = defaultdict(list)
for t, b, n, d0, d1, fr in allrows:
    if b in prev: gapw[(t // WIN) * WIN].append(t - prev[b])
    prev[b] = t
for w in range(lo, hi + 1, WIN):
    rows = [r for r in allrows if w <= r[0] < w + WIN]
    if not rows: continue
    fr = [r[5] for r in rows if r[5] is not None]
    gp = gapw.get(w, [])
    print(f'   [{w:5d},{w + WIN:5d}) 落地拍 {len(rows):3d} 条数 {sum(r[2] for r in rows):3d} 大组 {sum(1 for r in rows if r[2] >= 8):2d} | 间隔中位 {st.median(gp) if gp else 0:5.0f} | '
          + (f'延迟 {min(fr)}/{st.median(fr):.0f}/{max(fr)}' if fr else '延迟 -'))
if '--list' in a:
    print('== 逐个落地拍：落地拍 号 条数 | 决策拍范围 | 最新一条的延迟 | 上一组到这一组之间受理但没落地的条数')
    last = {}
    for t, b, n, d0, d1, fr in allrows:
        lost = ''
        if d0 is not None and b in last:
            lost = sum(1 for x in issued[b] if last[b] < x < d0)
        if d1 is not None: last[b] = d1
        print(f'   {t:5d} {b:8s} {n:2d} | ' + (f'{d0}–{d1} | {fr:4d} | {lost}' if d0 is not None else '未配上决策拍'))
