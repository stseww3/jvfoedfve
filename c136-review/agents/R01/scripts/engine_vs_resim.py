#!/usr/bin/env python3
"""engine_vs_resim.py — 用总部的真引擎重放（src/tools/engine_replay.cjs --dump）核对我的模拟器重演（resim_players.csv）。
用法：
  node /agent/repos/c136-data/src/tools/engine_replay.cjs <mid> --dump out/<mid>/engine_dump.tsv --every 90 --quiet
  python3 engine_vs_resim.py <mid> [--show 12]
逐（拍, 席位）比对全部真人席位的领土、余额、是否在场；报告第一处不同的拍、涉及的席位，以及此前完全一致的点数。
日志只覆盖本队的号；这一步把核对范围扩大到全场真人（含离场壳）。
"""
import csv, os, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
a = sys.argv[1:]
mid = a[0]
show = int(a[a.index('--show') + 1]) if '--show' in a else 12
out = os.path.join(HERE, '..', 'out', mid)
eng = {}
names = {}
for r in csv.DictReader(open(os.path.join(out, 'engine_dump.tsv'), encoding='utf8'), delimiter='\t'):
    eng[(int(r['t']), int(r['p']))] = (int(r['terr']), int(r['bal']), int(r['alive']), int(r['state']))
    names[int(r['p'])] = r['name']
sim = {}
for r in csv.DictReader(open(os.path.join(out, 'resim_players.csv'), encoding='utf8')):
    sim[(int(r['t']), int(r['p']))] = (int(r['terr']), int(r['bal']), int(r['alive']), int(r['state']))
ticks = sorted({t for t, _ in eng} & {t for t, _ in sim})
same = 0
bad = defaultdict(list)
for t in ticks:
    for (tt, p), e in eng.items():
        if tt != t:
            continue
        s = sim.get((t, p))
        if s is None:
            # 真引擎只导出还活着的真人；模拟器这边没有这一行 = 模拟器认为它不存在
            bad[t].append((p, e, None))
            continue
        if e[0] == s[0] and e[1] == s[1]:
            same += 1
        else:
            bad[t].append((p, e, s))
print(f'== {mid} 真引擎 对 模拟器重演：共同采样拍 {len(ticks)} 个（{ticks[0]}–{ticks[-1]}），领土和余额都相同的（拍, 席位）{same} 个，不同 {sum(len(v) for v in bad.values())} 个')
if bad:
    t0 = min(bad)
    print(f'   第一处不同在 t={t0}，涉及 {len(bad[t0])} 个席位；此前 {sum(1 for t in ticks if t < t0)} 个采样拍全场一致')
    for p, e, s in bad[t0][:show]:
        print(f'     #{p} {names.get(p, "")[:20]:20s} 真引擎 terr={e[0]} bal={e[1]} alive={e[2]} state={e[3]} | 模拟器 ' + (f'terr={s[0]} bal={s[1]} alive={s[2]} state={s[3]}' if s else '无此行'))
    nxt = sorted(bad)[1:4]
    for t in nxt:
        print(f'   t={t}: 不同 {len(bad[t])} 个席位，例 ' + ', '.join(f'#{p}' for p, _, _ in bad[t][:8]))
else:
    print('   全部一致')
