#!/usr/bin/env python3
"""shadow_gap.py — 影子指令（零延迟策略想发的）对 录像里真正执行的：按号 × 窗口分类计数，找「日志在走、指令不到」的死窗和同拍连发批。

用法：python3 shadow_gap.py <matchId> [--win 300] [--t0 0 --t1 99999] [--bots a,b] [--sec win,dead,burst,self]
输入：
  /tmp/c136-r05/work/<id>-shadow.json   （shadow.mjs <id> --quiet --json 这个文件；ticks[] = 影子每个出指令的拍）
  /tmp/c136-r05/truth/<id>.json          （match_truth.mjs；events[] = 录像里我方号执行的指令；players[]；squad[]）
  /agent/repos/c136-data/bundles/<id>/in_game.log （[HL-TICK] 的 cmds= 是真实客户端自报的累计发令数）
口径：
  - 目标分类：512 = 中立；编号 < 真人数 = 真人（队友另计为「捐」）；其余 = 机器人。
  - 作废 = 录像里执行了但 ok=False（目标已不接壤）或打出 0 兵。
  - 死窗 = 同一个号相邻两条已执行指令之间 ≥ --gap 拍（默认 60），且这段里影子想发 ≥ --min 条（默认 5）陆攻/出船。
  - 连发批 = 同一个号在同一拍执行 ≥3 条陆攻/出船。
"""
import os
import json
import re
import sys
from collections import defaultdict

args = sys.argv[1:]
mid = args[0]


def val(k, d):
    return args[args.index(k) + 1] if k in args else d


WIN = int(val('--win', 300))
T0, T1 = int(val('--t0', 0)), int(val('--t1', 99999))
GAP, MIN = int(val('--gap', 60)), int(val('--min', 5))
SEC = set(val('--sec', 'win,dead,burst,self').split(','))
S = json.load(open(f'/tmp/c136-r05/work/{mid}-shadow.json'))
T = json.load(open(f'/tmp/c136-r05/truth/{mid}.json'))
HN = T['humans']
SQ = {s['p']: s['bot'] for s in T['squad']}
PID = {v: k for k, v in SQ.items()}
BOTS = val('--bots', ','.join(SQ.values())).split(',')
TEAM = {p['id']: p['team'] for p in T['players']}


def cls(q, kind='attack'):
    if kind == 'donate':
        return '捐'
    if kind == 'boat':
        return '船'
    if q == 512:
        return '中立'
    if q < HN:
        return '真人'
    return '机器人'


def k(v):
    return f'{v / 1e6:.2f}M' if abs(v) >= 1e6 else f'{v / 1e3:.0f}k'


sh = defaultdict(list)   # bot -> [(t, cls, troops, q, pct)]
for r in S['ticks']:
    for c in r['cmds']:
        if c['k'] in ('attack', 'boat', 'donate'):
            sh[r['bot']].append((r['t'], cls(c.get('q', -1), c['k']), c.get('troops', 0), c.get('q', -1), c.get('pct', -1)))
ex = defaultdict(list)   # bot -> [(t, cls, troops, ok, q, pct)]
for e in T['events']:
    if e['type'] in ('attack', 'boat', 'donate') and e['p'] in SQ:
        tr = e.get('troops', e.get('got', 0))
        ex[SQ[e['p']]].append((e['t'], cls(e['q'], e['type']), tr, bool(e.get('ok', True)) and tr > 0, e['q'], e.get('pct', -1)))

# 真实客户端自报 cmds=
selfc = defaultdict(list)
rx = re.compile(r'\[(\w+)\] \[HL-TICK\] t=(\d+) .*?cmds=(\d+)')
for line in open(os.environ.get('C136_DATA', '/agent/repos/c136-data') + f'/bundles/{mid}/in_game.log', encoding='utf8', errors='replace'):
    m = rx.search(line)
    if m:
        selfc[m.group(1)].append((int(m.group(2)), int(m.group(3))))

if 'win' in SEC:
    print(f'== win {mid} 每号每 {WIN} 拍：影子想发（中立/机器人/真人/船/捐）｜录像执行（同序；括号内作废）｜执行的兵 ==')
    tot = defaultdict(lambda: [0, 0, 0])
    for b in BOTS:
        print(f'-- {b}')
        t = T0 - T0 % WIN
        while t <= min(T1, T['endTick']):
            a = [x for x in sh[b] if t <= x[0] < t + WIN]
            e = [x for x in ex[b] if t <= x[0] < t + WIN]
            if a or e:
                ca, ce, cv = defaultdict(int), defaultdict(int), defaultdict(int)
                for x in a:
                    ca[x[1]] += 1
                for x in e:
                    ce[x[1]] += 1
                    if not x[3]:
                        cv[x[1]] += 1
                order = ['中立', '机器人', '真人', '船', '捐']
                sa = '/'.join(str(ca[o]) for o in order)
                se = '/'.join(f'{ce[o]}' + (f'({cv[o]})' if cv[o] else '') for o in order)
                land = sum(1 for x in a if x[1] in ('中立', '机器人', '真人', '船'))
                lande = sum(1 for x in e if x[1] in ('中立', '机器人', '真人', '船'))
                tot[t][0] += land
                tot[t][1] += lande
                tot[t][2] += sum(1 for x in e if x[1] != '捐' and not x[3])
                print(f'   t={t}: 影子 {len(a)}（{sa}）｜执行 {len(e)}（{se}）｜执行出兵 {k(sum(x[2] for x in e if x[1] != "捐"))}')
            t += WIN
    print('-- 合计（陆攻+出船，不含捐兵）：窗口: 影子想发 / 录像执行（其中作废）')
    print('   ' + '  '.join(f'{t}: {v[0]}/{v[1]}({v[2]})' for t, v in sorted(tot.items())))

if 'dead' in SEC:
    print(f'== dead 死窗：相邻两条已执行指令之间 ≥{GAP} 拍、其间影子想发 ≥{MIN} 条陆攻/出船 ==')
    for b in BOTS:
        ts = sorted(x[0] for x in ex[b])
        ts = [0] + ts + [T['endTick']]
        for a, c in zip(ts, ts[1:]):
            if c - a < GAP or c < T0 or a > T1:
                continue
            w = [x for x in sh[b] if a < x[0] < c and x[1] != '捐']
            if len(w) < MIN:
                continue
            cc = defaultdict(int)
            for x in w:
                cc[x[1]] += 1
            # 窗口结束那一拍落地了几条
            burst = [x for x in ex[b] if x[0] == c]
            sr = [v for v in selfc[b] if a <= v[0] <= c]
            dself = (sr[-1][1] - sr[0][1]) if len(sr) >= 2 else None
            print(f'   {b} ({a},{c}) 长 {c - a} 拍：影子想发 {len(w)} 条（{dict(cc)}，首条 t={w[0][0]}，合计约 {k(sum(x[2] for x in w))}）'
                  f'｜真实客户端自报 cmds 在这段 +{dself}｜窗口末 t={c} 落地 {len(burst)} 条（作废 {sum(1 for x in burst if not x[3])}）')

if 'burst' in SEC:
    print('== burst 同拍连发批（≥3 条陆攻/出船）==')
    nb = nv = nc = 0
    for b in BOTS:
        by = defaultdict(list)
        for x in ex[b]:
            if x[1] != '捐':
                by[x[0]].append(x)
        out = []
        for t in sorted(by):
            if len(by[t]) < 3 or not (T0 <= t <= T1):
                continue
            g = by[t]
            cc = defaultdict(int)
            for x in g:
                cc[x[1]] += 1
            void = sum(1 for x in g if not x[3])
            nb += 1
            nc += len(g)
            nv += void
            out.append(f't={t}×{len(g)}（{"/".join(f"{k_}{v}" for k_, v in cc.items())}；作废 {void}；出兵 {k(sum(x[2] for x in g))}）')
        if out:
            print(f'   {b}: ' + '；'.join(out))
    print(f'   合计 {nb} 批 {nc} 条，其中作废 {nv} 条')

if 'self' in SEC:
    print('== self 真实客户端自报 cmds=（累计）对 录像里累计执行（含捐兵）：每 90 拍一行里差额最大的几处 ==')
    for b in BOTS:
        rows = []
        for t, c in selfc[b]:
            e = sum(1 for x in ex[b] if x[0] <= t)
            d = sum(1 for x in sh[b] if x[0] <= t and x[1] == '捐')
            de = sum(1 for x in ex[b] if x[0] <= t and x[1] == '捐')
            rows.append((t, c, e, c - e, d - de))
        if not rows:
            continue
        # 差额第一次超过 5、峰值、末值
        first = next((r for r in rows if r[3] - r[4] >= 5), None)
        peak = max(rows, key=lambda r: r[3] - r[4])
        last = rows[-1]
        print(f'   {b}: 末行 t={last[0]} 自报 {last[1]} 执行 {last[2]} 差 {last[3]}（其中没落地的捐兵约 {last[4]}）'
              f'｜非捐兵差额首次 ≥5：{"t=%d 自报 %d 执行 %d" % first[:3] if first else "无"}｜非捐兵差额峰值 t={peak[0]}：{peak[3] - peak[4]}')
