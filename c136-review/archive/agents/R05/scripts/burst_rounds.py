#!/usr/bin/env python3
"""burst_rounds.py — 同拍连发批的时间结构：每个号两批之间隔多少拍、各号的批是不是一轮一轮挨着来、每轮里各号的先后次序稳不稳。

背景：指令成批迟到（同一个号同一拍落地 ≥ --min 条陆攻/出船）时，想知道这是「每个号各自的事」还是「所有号被同一个东西轮流放行」。
口径：
  批 = 同一个号在同一拍执行 ≥ --min 条（默认 5）陆攻/出船指令（录像真值 events[]）。
  轮 = 按落地拍排序后，把批依次归入当前轮；某个号在当前轮里已经出现过、或与当前轮第一批相隔 > --span 拍（默认 160）时另起一轮。
  次序稳定度 = 相邻两轮里共同出现的号，按落地先后排名的秩相关（Spearman），取各对相邻轮的中位数。
输出：
  1. 每 300 拍：落地指令数、其中在批里的条数、落空（ok=False 或打出 0 兵）的条数、目标为中立的条数；影子想发数（若有 shadow JSON）
  2. 每个号的批：落地拍×条数，相邻两批间隔
  3. 轮表：起止拍、跨度、号的先后次序；轮与轮的间隔；次序稳定度
用法：python3 scripts/burst_rounds.py <matchId> [--min 5] [--span 160] [--t0 0 --t1 99999]
"""
import json
import sys
import statistics as st
from collections import Counter, defaultdict

a = sys.argv[1:]
mid = a[0]
val = lambda k, d: (a[a.index(k) + 1] if k in a else d)
MIN, SPAN = int(val('--min', 5)), int(val('--span', 160))
T0, T1 = int(val('--t0', 0)), int(val('--t1', 99999))
J = json.load(open(f'/tmp/c136-r05/truth/{mid}.json'))
sq = {s['p']: s['bot'] for s in J['squad']}
ev = [e for e in J['events'] if e.get('p') in sq and e['type'] in ('attack', 'boat') and T0 <= e['t'] < T1]
try:
    S = json.load(open(f'/tmp/c136-r05/work/{mid}-shadow.json'))
    want = Counter()
    for r in S['ticks']:
        if T0 <= r['t'] < T1:
            want[r['t'] // 300 * 300] += sum(1 for c in r['cmds'] if c['k'] in ('attack', 'boat'))
except FileNotFoundError:
    want = None

per = defaultdict(Counter)  # bot -> tick -> n
for e in ev:
    per[sq[e['p']]][e['t']] += 1
inbatch = lambda e: per[sq[e['p']]][e['t']] >= MIN

print(f'== 1 {mid} 每 300 拍：落地的陆攻/出船（批 = 同号同拍 ≥{MIN} 条）==')
wins = sorted({e['t'] // 300 * 300 for e in ev})
for w in wins:
    es = [e for e in ev if w <= e['t'] < w + 300]
    nb = sum(1 for e in es if inbatch(e))
    void = sum(1 for e in es if not e['ok'] or not e.get('troops'))
    neut = sum(1 for e in es if e['q'] == 512)
    voidb = sum(1 for e in es if inbatch(e) and (not e['ok'] or not e.get('troops')))
    wtxt = f'｜影子想发 {want[w]}' if want is not None else ''
    print(f'   t={w}: 落地 {len(es)}，在批里 {nb}（{100 * nb / max(1, len(es)):.0f}%），落空 {void}（批里 {voidb}），目标为中立 {neut}{wtxt}')
tot = len(ev)
nb = sum(1 for e in ev if inbatch(e))
print(f'   合计：落地 {tot}，在批里 {nb}（{100 * nb / max(1, tot):.0f}%）')

print(f'== 2 每个号的批（落地拍×条数；括号里是与上一批的间隔）==')
batches = []
for bot, c in per.items():
    bs = sorted(t for t, n in c.items() if n >= MIN)
    if not bs:
        print(f'   {bot}: 无')
        continue
    parts = []
    for i, t in enumerate(bs):
        parts.append(f'{t}×{c[t]}' + (f'（+{t - bs[i - 1]}）' if i else ''))
        batches.append((t, bot, c[t]))
    gaps = [bs[i] - bs[i - 1] for i in range(1, len(bs))]
    print(f'   {bot}: ' + ' '.join(parts) + (f'｜间隔中位 {st.median(gaps):.0f}' if gaps else ''))
batches.sort()
if batches:
    allgaps = defaultdict(list)
    for bot, c in per.items():
        bs = sorted(t for t, n in c.items() if n >= MIN)
        for i in range(1, len(bs)):
            allgaps[bs[i] // 300 * 300].append(bs[i] - bs[i - 1])
    print('   间隔按后一批所在的 300 拍窗：' + '；'.join(f't={w}: 中位 {st.median(g):.0f}（{min(g)}–{max(g)}，n={len(g)}）' for w, g in sorted(allgaps.items())))
    mod7 = Counter(t % 7 for t, _, _ in batches)
    print(f'   批落地拍 mod 7 的分布：{dict(mod7)}')
    sizes = Counter(n for _, _, n in batches)
    print(f'   批的条数分布：{dict(sorted(sizes.items()))}（最大 {max(sizes)}）')

print(f'== 3 轮（同一轮里每个号至多一批；与轮首相隔 > {SPAN} 拍另起一轮）==')
rounds = []
cur = []
for t, bot, n in batches:
    if cur and (bot in {b for _, b, _ in cur} or t - cur[0][0] > SPAN):
        rounds.append(cur)
        cur = []
    cur.append((t, bot, n))
if cur:
    rounds.append(cur)


def spearman(x, y):
    n = len(x)
    if n < 3:
        return None
    rx = {v: i for i, v in enumerate(sorted(x))}
    ry = {v: i for i, v in enumerate(sorted(y))}
    d2 = sum((rx[a_] - ry[b_]) ** 2 for a_, b_ in zip(x, y))
    return 1 - 6 * d2 / (n * (n * n - 1))


rhos = []
for i, r in enumerate(rounds):
    span = r[-1][0] - r[0][0]
    gap = f'，距上一轮轮首 {r[0][0] - rounds[i - 1][0][0]}' if i else ''
    rho_txt = ''
    if i:
        prev = {b: k for k, (_, b, _) in enumerate(rounds[i - 1])}
        nowr = {b: k for k, (_, b, _) in enumerate(r)}
        common = [b for b in nowr if b in prev]
        if len(common) >= 3:
            # 用落地拍 + 序号打破并列
            x = [prev[b] for b in common]
            y = [nowr[b] for b in common]
            rho = spearman(x, y)
            if rho is not None:
                rhos.append(rho)
                rho_txt = f'｜与上一轮共同的 {len(common)} 个号次序秩相关 {rho:.2f}'
    print(f'   轮 {i + 1}: {r[0][0]}–{r[-1][0]}（跨 {span} 拍，{len(r)} 个号{gap}）：' + ' → '.join(f'{b}@{t}×{n}' for t, b, n in r) + rho_txt)
if rhos:
    print(f'   相邻两轮次序秩相关：中位 {st.median(rhos):.2f}（{min(rhos):.2f}–{max(rhos):.2f}，n={len(rhos)}）')
if len(rounds) >= 2:
    g = [rounds[i][0][0] - rounds[i - 1][0][0] for i in range(1, len(rounds))]
    print(f'   轮首间隔：{g}')
