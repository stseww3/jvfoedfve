#!/usr/bin/env python3
# volleys.py — 「连续下单」统计：把我方号对同一个真人目标、相邻两条间隔 ≤ GAP 拍的已执行陆攻归成一轮（volley），
#   看一轮里有几条、合计打出批前存兵的多少（含手续费）。用来对账「指令在途时重复下单」：
#   分批进攻分支的本意是一条 pulse（约 10–12% 存兵），如果一轮里有 3–5 条，实际打出的就是 30–50%。
# 用法：python3 scripts/volleys.py <matchId> [--gap 21] [--t0 0 --t1 99999] [--min 3] [--list]
#   先跑 match_truth.mjs <matchId>（读 /tmp/c136-r05/truth/<id>.json）
import json, sys, statistics as st
from collections import defaultdict
a = sys.argv[1:]
mid = a[0]
val = lambda k, d: (a[a.index(k) + 1] if k in a else d)
GAP, T0, T1, MIN = int(val('--gap', 21)), int(val('--t0', 0)), int(val('--t1', 99999)), int(val('--min', 3))
J = json.load(open(f'/tmp/c136-r05/truth/{mid}.json'))
H = J['humans']
P = {p['id']: p for p in J['players']}
sq = {s['p']: s['bot'] for s in J['squad']}
ev = [e for e in J['events'] if e['type'] == 'attack' and e['p'] in sq and e.get('q') is not None and 0 <= e['q'] < H and e.get('ok', True) and T0 <= e['t'] < T1]
seq = defaultdict(list)
for e in ev:
    seq[(e['p'], e['q'])].append(e)
S10 = J.get('S10', {})


def land_at(p, t):
    """该号在 t 拍前最近一个 10 拍采样点的地（S10）；没有采样返回 0。"""
    s = S10.get(str(p))
    if not s:
        return 0
    i = min(len(s['t']) - 1, max(0, t // 10 - 1))
    return s['terr'][i]


vol = []
for (p, q), es in seq.items():
    es.sort(key=lambda e: e['t'])
    cur = [es[0]]
    for e in es[1:]:
        if e['t'] - cur[-1]['t'] <= GAP:
            cur.append(e)
        else:
            vol.append((p, q, cur)); cur = [e]
    vol.append((p, q, cur))
rows = []
for p, q, es in vol:
    B0 = es[0].get('B0') or 0
    spent = sum((e.get('troops') or 0) + (e.get('fee') or 0) for e in es)
    first = (es[0].get('troops') or 0) + (es[0].get('fee') or 0)
    rows.append({'bot': sq[p], 'q': P[q]['name'], 't0': es[0]['t'], 't1': es[-1]['t'], 'n': len(es), 'ticks': len({e['t'] for e in es}), 'B0': B0, 'spent': spent,
                 'share': spent / B0 if B0 else 0, 'firstShare': first / B0 if B0 else 0, 'pct': sorted({e['pct'] for e in es}), 'first': first,
                 'span': es[-1]['t'] - es[0]['t'], 'L0': land_at(p, es[0]['t'])})
n = len(rows)
if not n:
    print(f'[连续下单] {mid}: 无'); sys.exit(0)
big = [r for r in rows if r['n'] >= MIN]
tot = sum(r['spent'] for r in rows)
print(f"[连续下单] {mid} t={T0}–{T1} 间隔≤{GAP} 拍：我方号打真人 {sum(r['n'] for r in rows)} 条，归成 {n} 轮；每轮条数 中位 {st.median(r['n'] for r in rows)} 最大 {max(r['n'] for r in rows)}；"
      f"≥{MIN} 条的轮 {len(big)} 个（含 {sum(r['n'] for r in big)} 条，打出 {sum(r['spent'] for r in big)/1e6:.2f}M＝全部打真人支出 {tot/1e6:.2f}M 的 {100*sum(r['spent'] for r in big)/max(1,tot):.0f}%）")
print(f"    每轮打出批前存兵的比例：全部轮 中位 {100*st.median(r['share'] for r in rows):.0f}%；首条 中位 {100*st.median(r['firstShare'] for r in rows):.0f}%；≥{MIN} 条的轮 中位 {100*st.median([r['share'] for r in big] or [0]):.0f}% 最大 {100*max([r['share'] for r in big] or [0]):.0f}%")
firsts = sum(r['first'] for r in rows)
print(f"    各轮首条合计 {firsts/1e6:.2f}M；同一轮里跟在首条后面的那些条合计 {(tot-firsts)/1e6:.2f}M（占全部打真人支出的 {100*(tot-firsts)/max(1,tot):.0f}%）；一轮从首条到末条的拍数 中位 {st.median(r['span'] for r in rows)} 最大 {max(r['span'] for r in rows)}")
dist = defaultdict(int)
for r in rows:
    dist[min(r['n'], 9)] += 1
over = [r for r in rows if r['L0'] and r['B0'] > 100 * r['L0']]
print(f"    批前存兵 > 100×地（over 放行）的轮 {len(over)} 个，打出 {sum(r['spent'] for r in over)/1e6:.2f}M（占 {100*sum(r['spent'] for r in over)/max(1,tot):.0f}%）")
print('    轮的条数分布：' + ' '.join(f"{k}{'+' if k == 9 else ''}条×{v}" for k, v in sorted(dist.items())))
if '--list' in a:
    for r in sorted(big, key=lambda r: r['t0']):
        print(f"    {r['bot']} → {r['q'][:16]} t={r['t0']}–{r['t1']} {r['n']} 条/{r['ticks']} 拍 pct {r['pct']} 批前 {r['B0']/1000:.0f}k（地 {r['L0']}，密度 {r['B0']/max(1,r['L0']):.1f}）打出 {r['spent']/1000:.0f}k（{100*r['share']:.0f}%；首条 {100*r['firstShare']:.0f}%）")
