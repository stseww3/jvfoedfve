#!/usr/bin/env python3
# land_takers.py — 某个玩家的地是被谁拿走的：按 600 拍窗列出「从它手里拿地」的各方格数（录像重放真值 pairAll）。
#   pairAll 行 = [窗序号 w（第 w 窗 = 拍 600w…600w+599）, 拿地方 a, 丢地方 b, 格数]；a/b = 512 中立、600 机器人合计、其余真人 id。
# 用法：python3 scripts/land_takers.py <matchId> --victims 8,9,4 [--top 5] [--t0 0 --t1 99999]
#   先跑 match_truth.mjs <matchId>（读 /tmp/c136-r05/truth/<id>.json）
import json, sys
from collections import defaultdict, Counter

a = sys.argv[1:]
mid = a[0]
val = lambda k, d: (a[a.index(k) + 1] if k in a else d)
J = json.load(open(f'/tmp/c136-r05/truth/{mid}.json'))
P = {p['id']: p for p in J['players']}
sq = {s['p']: s['bot'] for s in J['squad']}
TOP, T0, T1 = int(val('--top', 5)), int(val('--t0', 0)), int(val('--t1', 99999))


def nm(i):
    if i == 512:
        return '中立'
    if i == 600:
        return '机器人'
    p = P.get(i)
    tag = '*' if i in sq else ''
    return f"{p['name'] if p else '?'}#{i}{tag}(T{p['team'] if p else '?'})"


victims = [int(x) for x in val('--victims', '').split(',') if x]
for v in victims:
    by = defaultdict(Counter)
    tot = Counter()
    for w, x, y, n in J['pairAll']:
        if y == v and T0 <= w * 600 < T1:
            by[w][x] += n
            tot[x] += n
    p = P.get(v, {})
    print(f"[谁拿走了 {nm(v)} 的地] {mid}｜它峰值地 {p.get('peakTerr')}@{p.get('peakT')}｜阵亡 {p.get('deathT')} 离线 {p.get('leftT')}｜合计被拿 {sum(tot.values())} 格："
          + '、'.join(f'{nm(x)} {n}（{100 * n / max(1, sum(tot.values())):.0f}%）' for x, n in tot.most_common(TOP)))
    for w in sorted(by):
        c = by[w]
        print(f"   {w * 600}–{w * 600 + 599}: " + '、'.join(f'{nm(x)} {n}' for x, n in c.most_common(TOP)) + f'｜窗内合计 {sum(c.values())}')
