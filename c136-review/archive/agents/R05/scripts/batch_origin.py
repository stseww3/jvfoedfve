#!/usr/bin/env python3
"""batch_origin.py — 同拍连发批里的每条指令，是这个号在哪几拍决定的？

做法：影子策略在重放状态上逐决策拍重算出「这个号当拍想发什么」（shadow.mjs --json 的产物；A 系列各局影子指令数与号自报指令数相等）。
      一批 = 同一个号同一拍落地 ≥ --min 条陆攻（录像真值 events[]，含落空的）。
      把这一批按落地顺序的 pct 序列，与这个号在落地拍之前的影子陆攻决策序列（按决策拍先后）做「连续子序列」匹配，
      顺序、倒序都试，取离落地拍最近的一处匹配（倒序 = 一批里先落地的那条是后决定的）。目标不参与匹配：目标已死的指令会被引擎改写成打中立（engine-evidence [A5]）。
输出（每批一行）：落地拍、条数、匹配到的决策拍 首–末、落地时已过去多少拍（首/末）、这批决策的第一拍距上一批落地多少拍、
      决策时的目标 → 落地时的目标（改写成中立的条数）、落空条数。
汇总：匹配上的批数；陈旧度（落地拍 − 决策拍）中位/最大；「决策第一拍 − 上一批落地拍」的分布；
      两批之间这个号想发而没有出现在任何一批里的陆攻条数。
用法：python3 scripts/batch_origin.py <matchId> [--min 5] [--t0 0 --t1 99999] [--bots a,b]
"""
import json
import sys
import statistics as st
from collections import defaultdict

a = sys.argv[1:]
mid = a[0]
val = lambda k, d: (a[a.index(k) + 1] if k in a else d)
MIN = int(val('--min', 5))
T0, T1 = int(val('--t0', 0)), int(val('--t1', 99999))
only = set(val('--bots', '').split(',')) - {''}
J = json.load(open(f'/tmp/c136-r05/truth/{mid}.json'))
S = json.load(open(f'/tmp/c136-r05/work/{mid}-shadow.json'))
sq = {s['p']: s['bot'] for s in J['squad']}
H = J['humans']
names = {p['id']: p['name'] for p in J['players']}


def cls(q):
    return '中立' if q == 512 else ('真人' if q < H else '机器人')


dec = defaultdict(list)  # bot -> [(t, pct, q)]
for r in S['ticks']:
    for c in r['cmds']:
        if c['k'] == 'attack':
            dec[r['bot']].append((r['t'], c['pct'], c['q']))

exe = defaultdict(lambda: defaultdict(list))  # bot -> t -> [event]
for e in J['events']:
    if e['type'] == 'attack' and e.get('p') in sq:
        exe[sq[e['p']]][e['t']].append(e)

tot_b = tot_m = 0
orders = defaultdict(int)
stale_all, gap_all, lost_all = [], [], []
rewr = void = ncmd = 0
uniq_n = 0
uniq_stale = []
for bot in sorted(exe):
    if only and bot not in only:
        continue
    D = dec[bot]
    bts = sorted(t for t, es in exe[bot].items() if len(es) >= MIN and T0 <= t < T1)
    prev_t = None
    prev_last_idx = None
    for T in bts:
        es = exe[bot][T]
        pcts = [e['pct'] for e in es]
        n = len(pcts)
        tot_b += 1
        cand = [i for i in range(len(D) - n + 1) if D[i + n - 1][0] < T and [d[1] for d in D[i:i + n]] == pcts]
        order = '顺序'
        rc = [i for i in range(len(D) - n + 1) if D[i + n - 1][0] < T and [d[1] for d in D[i:i + n]] == pcts[::-1]]
        if rc and (not cand or rc[-1] >= cand[-1]):
            cand, order = rc, '倒序'
            es = es[::-1]
        orders[order if cand else '无'] += 1
        nvoid = sum(1 for e in es if not e['ok'] or not e.get('troops'))
        if not cand:
            print(f'{bot} t={T} ×{n}: 没有找到 pct 序列一致的连续决策（pct {pcts}）｜落空 {nvoid}')
            prev_t = T
            prev_last_idx = None
            continue
        i = cand[-1]
        tot_m += 1
        d0, d1 = D[i][0], D[i + n - 1][0]
        stale_all += [T - d[0] for d in D[i:i + n]]
        if len(cand) == 1:
            uniq_n += 1
            uniq_stale += [T - d[0] for d in D[i:i + n]]
        was = [cls(d[2]) for d in D[i:i + n]]
        now = [cls(e['q']) for e in es]
        rw = sum(1 for x, y in zip(was, now) if x != y)
        rewr += rw
        void += nvoid
        ncmd += n
        gap = d0 - prev_t if prev_t is not None else None
        if gap is not None:
            gap_all.append(gap)
        lost = None
        if prev_last_idx is not None:
            lost = i - prev_last_idx - 1
            lost_all.append(lost)
        wsum = defaultdict(int)
        for x in was:
            wsum[x] += 1
        nsum = defaultdict(int)
        for x in now:
            nsum[x] += 1
        print(f'{bot} t={T} ×{n}: 决策拍 {d0}–{d1}（{order}落地；落地时已过 {T - d0}–{T - d1} 拍）'
              + (f'｜决策第一拍在上一批落地（{prev_t}）之后 {gap} 拍' if gap is not None else '')
              + (f'｜两批之间想发而没进任何一批的陆攻 {lost} 条' if lost is not None else '')
              + '｜决策时目标 ' + '、'.join(f'{k}×{v}' for k, v in wsum.items()) + ' → 落地时 ' + '、'.join(f'{k}×{v}' for k, v in nsum.items())
              + f'（目标类别变了 {rw} 条）｜落空 {nvoid}' + (f'｜候选匹配 {len(cand)} 处，取最近' if len(cand) > 1 else ''))
        prev_t = T
        prev_last_idx = i + n - 1
print(f'== 落地顺序：' + '、'.join(f'{k} {v} 批' for k, v in orders.items()) + '（倒序 = 一批里先落地的是后决定的）')
print(f'== 汇总：{tot_b} 批，匹配上 {tot_m} 批（{ncmd} 条）｜陈旧度 中位 {st.median(stale_all):.0f}、最小 {min(stale_all)}、最大 {max(stale_all)} 拍'
      f'｜目标类别被改写 {rewr} 条，落空 {void} 条')
if uniq_stale:
    print(f'   只算唯一匹配的批（pct 序列在决策流里只出现一处）：{uniq_n} 批 {len(uniq_stale)} 条｜陈旧度 中位 {st.median(uniq_stale):.0f}、最小 {min(uniq_stale)}、最大 {max(uniq_stale)} 拍；≥90 拍的 {sum(1 for x in uniq_stale if x >= 90)} 条')
if gap_all:
    print(f'   决策第一拍 − 上一批落地拍：中位 {st.median(gap_all):.0f}（{min(gap_all)}–{max(gap_all)}，n={len(gap_all)}）；≤10 拍的 {sum(1 for g in gap_all if g <= 10)} 批')
if lost_all:
    print(f'   相邻两批之间想发而没进任何一批的陆攻：合计 {sum(lost_all)} 条，中位 {st.median(lost_all):.0f}（{min(lost_all)}–{max(lost_all)}，n={len(lost_all)}）')
