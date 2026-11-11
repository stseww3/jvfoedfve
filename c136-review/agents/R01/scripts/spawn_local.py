#!/usr/bin/env python3
"""spawn_local.py — B 组（c110）本地分槽出生（Policy.chooseSpawn 的 “Autonomous 20-brother” 分支，[HL-SPAWN] 行）的账。
读 bundles/<局号>/in_game.log 的 [HL-GAME-INIT]/[HL-SPAWN] 行、out/<局号>/spawn_actual.csv（先跑 spawn_actual.mjs）、
out/<局号>/voronoi_seats.csv（先跑 voronoi_share.mjs：全体真人第 1 拍的出生点、天然份额、630/1500 拍领土）。
用法：python3 scripts/spawn_local.py <局号> [--near 60]
  表 1 每个号：席位/队、slot、日志里换了几版位置（[HL-SPAWN] 行数）、第一版→最后一版坐标、相邻两版之间跳的距离（中位/最大）、
        最后一版的 chosenSlots=a/b（贪心表长度/候选数）、实际出生点、实际点离最后一版多远、最近的本队号（同队/别队）和距离、最近的任何真人和距离、
        天然份额（泰森多边形格数）、630 拍领土。
  表 2 slot 号有没有重号；同一毫秒窗口里不同号拿到的候选数 b 是否一致（各号算出来的候选表是不是同一张）。
  表 3 实际出生点两两距离 < --near 像素的本队号对（同队 / 别队），以及离任何真人 < --near 的号。
说明：[HL-SPAWN] 行只在位置变动 > 6 像素时才打（L4147），所以“版数”是位置变动次数的下界。
"""
import csv, os, re, statistics, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
a = sys.argv[1:]
mid = a[0]
near = float(a[a.index('--near') + 1]) if '--near' in a else 60.0
B = '/agent/repos/c136-data/bundles'
D = os.path.join(HERE, '..', 'out', mid)
log = open(os.path.join(B, mid, 'in_game.log'), encoding='utf8', errors='replace').read().split('\n')
pat = re.compile(r'^(\d+)\t\[([^\]]+)\] \[HL-SPAWN\] me=(\d+) slot=(\d+) \(squad=(\d+),rankIdx=(\d+)\) -> \((\d+),(\d+)\) chosenSlots=(\d+)/(\d+) minSep=(\d+)')
ver = defaultdict(list)   # seat -> [(ms, x, y, a, b, slot, squadN, rankIdx, label)]
for ln in log:
    m = pat.match(ln)
    if m:
        ms, lb, me, slot, sqn, rk, x, y, ca, cb, sep = m.groups()
        ver[int(me)].append((int(ms), int(x), int(y), int(ca), int(cb), int(slot), int(sqn), int(rk), lb))
act = {int(r['p']): r for r in csv.DictReader(open(os.path.join(D, 'spawn_actual.csv'), encoding='utf8'))}
seats = {int(r['p']): r for r in csv.DictReader(open(os.path.join(D, 'voronoi_seats.csv'), encoding='utf8'))} if os.path.exists(os.path.join(D, 'voronoi_seats.csv')) else {}
terr_cols = [c for c in (next(iter(seats.values())).keys() if seats else []) if c.startswith('terr')]
hyp = lambda x0, y0, x1, y1: ((x0 - x1) ** 2 + (y0 - y1) ** 2) ** 0.5
sq = sorted(act)
print(f'== {mid} 表 1 本地分槽出生：号 | 席位/队 | slot | 版数 | 第一版 → 最后一版 | 相邻两版跳的距离 中位/最大 | 贪心表/候选 | 实际出生点 | 离最后一版 | 最近本队号(队) 距离 | 最近真人(队) 距离 | 天然份额 | {" ".join(terr_cols)}')
slots = defaultdict(list)
for p in sq:
    r = act[p]
    x, y = int(r['x']), int(r['y'])
    V = ver.get(p, [])
    tm = seats[p]['team'] if p in seats else '?'
    jumps = [hyp(V[i][1], V[i][2], V[i + 1][1], V[i + 1][2]) for i in range(len(V) - 1)]
    last = V[-1] if V else None
    if last:
        slots[last[5]].append(r['bot'])
    # 最近的本队号 / 最近的任何真人
    bm = min(((hyp(x, y, int(act[o]['x']), int(act[o]['y'])), o) for o in sq if o != p), default=(0, -1))
    bh = min(((hyp(x, y, int(s['x']), int(s['y'])), o) for o, s in seats.items() if o != p), default=(0, -1))
    tmo = lambda o: seats[o]['team'] if o in seats else '?'
    print(f"   {r['bot']:14s} #{p:<3d}T{tm} slot {last[5] if last else '-':>2} 版 {len(V):2d} | "
          + (f"({V[0][1]},{V[0][2]}) → ({last[1]},{last[2]})" if V else '无 [HL-SPAWN] 行').ljust(28)
          + f" | 跳 {statistics.median(jumps) if jumps else 0:6.0f}/{max(jumps) if jumps else 0:6.0f} | {str(last[3]) + '/' + str(last[4]) if last else '-':>6} | ({x},{y}) | {hyp(x, y, last[1], last[2]) if last else 0:5.0f} | "
          + f"{act[bm[1]]['bot'] if bm[1] >= 0 else '-'}(T{tmo(bm[1])}) {bm[0]:4.0f} | {(seats[bh[1]]['name'] if bh[1] >= 0 else '-')[:18]}(T{tmo(bh[1])}) {bh[0]:4.0f} | {seats[p]['nat'] if p in seats else '-':>6} | {' '.join(seats[p][c] for c in terr_cols) if p in seats else ''}")
print(f'== {mid} 表 2 slot 与候选表')
dup = {s: L for s, L in slots.items() if len(L) > 1}
print(f"   slot 号：{len(slots)} 个不同的值 / {sum(len(L) for L in slots.values())} 个号；重号：{dup if dup else '无'}")
allv = sorted((v[0], p, v[4], v[3]) for p, V in ver.items() for v in V)
if allv:
    # 日志第一列是行序号（不是时间），所以只能按先后看：同一个号前后两版之间，别的号打了几行
    cbs = defaultdict(int)
    for v in allv:
        cbs[v[2]] += 1
    print(f'   [HL-SPAWN] 行 {len(allv)} 条（日志行序号 {allv[0][0]}–{allv[-1][0]}）；候选数 b 的取值与行数：{dict(sorted(cbs.items()))}；贪心表长度 a 的取值：{sorted({v[3] for v in allv})[:20]}')
    same_xy = defaultdict(set)
    for p, V in ver.items():
        for v in V:
            same_xy[(v[1], v[2])].add(p)
    shared = {k: sorted(act[p]['bot'] for p in s) for k, s in same_xy.items() if len(s) > 1}
    print(f'   同一个坐标先后被不同的号选中过的：{len(shared)} 个坐标 / 共 {len(same_xy)} 个不同坐标；例：' + '；'.join(f'({k[0]},{k[1]}) {"/".join(v)}' for k, v in list(sorted(shared.items(), key=lambda kv: -len(kv[1])))[:6]))
    lastxy = defaultdict(list)
    for p, V in ver.items():
        lastxy[(V[-1][1], V[-1][2])].append(act[p]['bot'])
    print(f'   最后一版坐标相同（或 <= 6 像素）的号：' + ('；'.join(f'({k[0]},{k[1]}) {"/".join(v)}' for k, v in lastxy.items() if len(v) > 1) or '无'))
    short = [(act[p]['bot'], ca, s) for p, V in ver.items() for (ms, x, y, ca, cb, s, *_r) in V[-1:] if ca <= s]
    print(f'   最后一版里贪心表长度 a <= 自己 slot 的号（走了放宽间距或最远点兜底）：{short if short else "无"}')
print(f'== {mid} 表 3 实际出生点挨得近（< {near:.0f} 像素）')
pairs = []
for i, p in enumerate(sq):
    for o in sq[i + 1:]:
        d = hyp(int(act[p]['x']), int(act[p]['y']), int(act[o]['x']), int(act[o]['y']))
        if d < near:
            same = seats and seats[p]['team'] == seats[o]['team']
            pairs.append((d, act[p]['bot'], act[o]['bot'], '同队' if same else '别队'))
for d, x, y, k in sorted(pairs):
    print(f'   {x} – {y}：{d:.0f} 像素（{k}）')
if not pairs:
    print('   无')
if seats:
    cl = []
    for p in sq:
        x, y = int(act[p]['x']), int(act[p]['y'])
        d, o = min((hyp(x, y, int(s['x']), int(s['y'])), o) for o, s in seats.items() if o != p)
        if d < near:
            cl.append(f"{act[p]['bot']} – {seats[o]['name']}#{o}/T{seats[o]['team']}{'(本队)' if o in act else ''} {d:.0f}")
    print(f'   离任何真人 < {near:.0f} 像素的号 {len(cl)} 个：' + '；'.join(cl))
    dsq = [min(hyp(int(act[p]['x']), int(act[p]['y']), int(s['x']), int(s['y'])) for o, s in seats.items() if o != p) for p in sq]
    oth = [o for o in seats if o not in act]
    dot = [min(hyp(int(seats[p]['x']), int(seats[p]['y']), int(s['x']), int(s['y'])) for o, s in seats.items() if o != p) for p in oth]
    print(f'   最近真人距离 中位：本队 {statistics.median(dsq):.0f}，其他真人 {statistics.median(dot):.0f}；天然份额 中位：本队 {statistics.median(int(seats[p]["nat"]) for p in sq)}，其他 {statistics.median(int(seats[p]["nat"]) for p in oth)}')
