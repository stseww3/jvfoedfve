#!/usr/bin/env python3
"""cmd_staleness.py — 每条落地的陆攻是多少拍以前决定的，和「这个号当时发指令有多密」并排看。

为什么要看：指令成批迟到时，要分清两种情况——
  (甲) 通道本身在那一段整体变慢（那么同一段里稀疏发出的单条指令也应该迟到）；
  (乙) 只有连续每个决策拍都在发指令的号才堵（那么同一段里稀疏发出的单条指令应该照常几拍就落地）。
做法：
  影子决策 = shadow.mjs --json 的逐决策拍重算（/tmp/c136-r05/work/<id>-shadow.json）；落地 = 录像真值 events[]。
  批（同号同拍 ≥ --min 条）：按 batch_origin.py 的口径，倒序与连续 9 个决策对上，取唯一匹配；不唯一的不计。
  单条（同号同拍 < --min 条）：取落地拍之前最近的、pct 相同且目标相容（相同，或落地目标是中立=原目标已死）的决策；
      找不到的记「无对应」。
  发令密度 = 该决策拍之前 60 拍内这个号的影子陆攻决策数（每 5 拍一个决策拍，满额 12）。
输出：
  1. 按 300 拍窗：单条 n、陈旧度中位/≥35 拍的条数；批内 n、陈旧度中位
  2. 按发令密度分档（0–2 / 3–7 / 8–12）：落地条数、陈旧度中位、≥35 拍占比、≥90 拍占比（单条与批合并）
  3. 每个号：密度 ≥8 的决策拍数、其中出现在落地批里的条数；密度 ≤2 时落地的条数与陈旧度中位
用法：python3 scripts/cmd_staleness.py <matchId> [--min 5] [--t0 800 --t1 2100]
"""
import json
import sys
import bisect
import statistics as st
from collections import defaultdict

a = sys.argv[1:]
mid = a[0]
val = lambda k, d: (a[a.index(k) + 1] if k in a else d)
MIN = int(val('--min', 5))
T0, T1 = int(val('--t0', 800)), int(val('--t1', 2100))
J = json.load(open(f'/tmp/c136-r05/truth/{mid}.json'))
S = json.load(open(f'/tmp/c136-r05/work/{mid}-shadow.json'))
sq = {s['p']: s['bot'] for s in J['squad']}

dec = defaultdict(list)
for r in S['ticks']:
    for c in r['cmds']:
        if c['k'] == 'attack':
            dec[r['bot']].append((r['t'], c['pct'], c['q']))
dts = {b: [d[0] for d in D] for b, D in dec.items()}


def density(bot, t):
    ts = dts[bot]
    return bisect.bisect_left(ts, t) - bisect.bisect_left(ts, t - 60)


exe = defaultdict(lambda: defaultdict(list))
for e in J['events']:
    if e['type'] == 'attack' and e.get('p') in sq:
        exe[sq[e['p']]][e['t']].append(e)

rows = []  # (bot, T, kind, stale, dens)
nomatch = defaultdict(int)
for bot, byT in exe.items():
    D = dec[bot]
    for T, es in sorted(byT.items()):
        if not (T0 <= T < T1):
            continue
        if len(es) >= MIN:
            pcts = [e['pct'] for e in es][::-1]
            n = len(pcts)
            cand = [i for i in range(len(D) - n + 1) if D[i + n - 1][0] < T and [d[1] for d in D[i:i + n]] == pcts]
            if len(cand) != 1:
                nomatch['批（匹配不唯一或没有）'] += n
                continue
            for d in D[cand[0]:cand[0] + n]:
                rows.append((bot, T, '批', T - d[0], density(bot, d[0])))
        else:
            used = set()
            for e in es:
                best = None
                for i in range(len(D) - 1, -1, -1):
                    d = D[i]
                    if d[0] >= T or i in used:
                        continue
                    if T - d[0] > 600:
                        break
                    if d[1] == e['pct'] and (d[2] == e['q'] or e['q'] == 512):
                        best = i
                        break
                if best is None:
                    nomatch['单条'] += 1
                    continue
                used.add(best)
                rows.append((bot, T, '单条', T - D[best][0], density(bot, D[best][0])))

med = lambda v: f'{st.median(v):.0f}' if v else '-'
print(f'== 1 {mid} [{T0},{T1}) 按 300 拍窗（陈旧度 = 落地拍 − 决策拍）==')
for w in range(T0 // 300 * 300, T1, 300):
    s1 = [r[3] for r in rows if r[2] == '单条' and w <= r[1] < w + 300]
    s2 = [r[3] for r in rows if r[2] == '批' and w <= r[1] < w + 300]
    print(f'   t={w}: 单条 {len(s1)} 条，陈旧度中位 {med(s1)}，≥35 拍 {sum(1 for x in s1 if x >= 35)} 条｜批内 {len(s2)} 条，陈旧度中位 {med(s2)}（{min(s2) if s2 else "-"}–{max(s2) if s2 else "-"}）')
print(f'   没对上的：' + '、'.join(f'{k} {v} 条' for k, v in nomatch.items()))
print('== 2 按决策当时的发令密度（之前 60 拍内这个号的陆攻决策数；满额 12）==')
for lo, hi in ((0, 2), (3, 7), (8, 12)):
    R = [r for r in rows if lo <= r[4] <= hi]
    v = [r[3] for r in R]
    nb = sum(1 for r in R if r[2] == '批')
    print(f'   密度 {lo}–{hi}: 落地 {len(R)} 条（其中批内 {nb}）｜陈旧度中位 {med(v)}｜≥35 拍 {sum(1 for x in v if x >= 35)}（{100 * sum(1 for x in v if x >= 35) / max(1, len(v)):.0f}%）｜≥90 拍 {sum(1 for x in v if x >= 90)}（{100 * sum(1 for x in v if x >= 90) / max(1, len(v)):.0f}%）')
print('== 3 每个号 ==')
for bot in sorted(dec):
    D = [d for d in dec[bot] if T0 <= d[0] < T1]
    dense = [d for d in D if density(bot, d[0]) >= 8]
    R = [r for r in rows if r[0] == bot]
    landed_dense = sum(1 for r in R if r[4] >= 8)
    sparse = [r[3] for r in R if r[4] <= 2]
    alls = [r[3] for r in R]
    print(f'   {bot}: 决策 {len(D)} 条，其中密度 ≥8 的 {len(dense)} 条 → 落地 {landed_dense} 条（{100 * landed_dense / max(1, len(dense)):.0f}%）｜密度 ≤2 时落地 {len(sparse)} 条，陈旧度中位 {med(sparse)}｜全部落地 {len(R)} 条，陈旧度中位 {med(alls)}')
