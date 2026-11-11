#!/usr/bin/env python3
# yield_payback.py — 每笔已执行的我方捐兵：按引擎利息公式算「捐前两号的每 10 拍利息之和」与「捐后之和」，
#   得到这笔捐兵让两号合计利息每 10 拍多拿（或少拿）多少，以及 6.25% 的税要多少拍才能靠多出来的利息赚回。
# 引擎公式（c136-data/src/sim/sim/game.js）：
#   INTEREST_TABLE[i] = 100 + isqrt(25600*i/508)（L40-41）；interestRate（L739-746）：n1 = TABLE[511*地/全图陆地]；
#     t<1920 时 n1 = max(100*(13440-6t)/1920, n1)；存兵 > 100×地 时 n1 -= 2*n1*(存兵-100×地)/(100×地)；夹到 [0,700]。
#   economyTick（L778-784）：每 10 拍 存兵 += max(n1*存兵/10000, 1)，受 150×地 硬上限截断（addBalance L752-756）。
#   transfer（L388-399）：税 = 捐出方全部存兵的 64/1024，到账受 receiverRoom 截断。
# 这是「捐完那一刻」的静态比较（策略源码注释里的收益论证也是这个口径），不含之后局面的变化。
# 用法：python3 scripts/yield_payback.py <matchId> [--t0 4284 --t1 5400] [--kind yield_opt_dispatch] [--list]
import json, sys, statistics as st
from collections import defaultdict

a = sys.argv[1:]
mid = a[0]
val = lambda k, d: (a[a.index(k) + 1] if k in a else d)
T0, T1 = int(val('--t0', 0)), int(val('--t1', 99999))
KIND = val('--kind', '')
J = json.load(open(f'/tmp/c136-r05/truth/{mid}.json'))
LAND = None
for line in open(f'/tmp/c136-r05/work/{mid}-digest.txt', encoding='utf-8') if False else []:
    pass
iV = lambda x, y: int((x + 0.5) // y)


def isqrt9(h):
    if h < 1:
        return 0
    x = iV(h + 1, 2)
    for _ in range(9):
        x = iV(x + iV(h, x), 2)
    return x


TABLE = [100 + isqrt9(iV(25600 * i, 508)) for i in range(512)]


def interest(t, terr, bal, land):
    if terr <= 0:
        return 0
    n1 = TABLE[min(511, iV(511 * terr, land))]
    if t < 1920:
        n1 = max(iV(100 * (13440 - 6 * t), 1920), n1)
    cap = min(100 * terr, 1e9)
    if bal > cap:
        n1 -= iV(2 * n1 * (bal - cap), cap)
    n1 = min(max(n1, 0), 700)
    v = max(iV(n1 * bal, 1e4), 1)
    return max(min(v, terr * 150 - bal), 0)


land = J.get('mapLand') or J.get('land')
if not land:
    S = json.load(open(f'/tmp/c136-r05/skel/{mid}.json'))
    land = S['context']['mapLand']
sq = {s['p']: s['bot'] for s in J['squad']}
rows = []
for e in J['events']:
    if e['type'] != 'donate' or e['p'] not in sq or not e.get('ok', True) or not (T0 <= e['t'] < T1):
        continue
    if KIND and e.get('logKind') != KIND:
        continue
    t, B, L, qB, qL, got, fee = e['t'], e['B0'], e['L0'], e['qB0'], e['qL0'], e['got'], e['fee']
    before = interest(t, L, B, land) + interest(t, qL, qB, land)
    after = interest(t, L, B - got - fee, land) + interest(t, qL, qB + got, land)
    d = after - before
    rows.append(dict(t=t, p=sq[e['p']], q=sq.get(e['q'], e['q']), kind=e.get('logKind'), got=got, fee=fee, dMe=B / max(1, L), dAlly=qB / max(1, qL), dAllyAfter=(qB + got) / max(1, qL), delta=d, payback=(10 * fee / d if d > 0 else None)))

k = lambda x: f'{x/1e6:.2f}M' if abs(x) >= 1e6 else f'{x/1000:.0f}k'
n = len(rows)
if not n:
    print('无匹配的捐兵'); sys.exit(0)
pos = [r for r in rows if r['delta'] > 0]
neg = [r for r in rows if r['delta'] <= 0]
pb = sorted(r['payback'] for r in pos)
print(f'[捐兵利息回本] {mid} t∈[{T0},{T1}){"｜类别 " + KIND if KIND else ""}：{n} 笔，到账 {k(sum(r["got"] for r in rows))}，税 {k(sum(r["fee"] for r in rows))}')
print(f'   捐后两号合计利息变多的 {len(pos)} 笔（每 10 拍合计多拿 {k(sum(r["delta"] for r in pos))}）；变少或不变的 {len(neg)} 笔（每 10 拍合计少拿 {k(-sum(r["delta"] for r in neg))}，这些笔的税 {k(sum(r["fee"] for r in neg))}）')
if pb:
    print(f'   变多的那些：税靠多出来的利息赚回要的拍数 中位 {st.median(pb):.0f}、四分位 {pb[len(pb)//4]:.0f}–{pb[3*len(pb)//4]:.0f}、最短 {pb[0]:.0f}；≤300 拍回本的 {sum(1 for x in pb if x <= 300)} 笔，>1000 拍的 {sum(1 for x in pb if x > 1000)} 笔')
print(f'   受赠方捐前密度 ≥100 的 {sum(1 for r in rows if r["dAlly"] >= 100)} 笔；捐后密度 ≥100 的 {sum(1 for r in rows if r["dAllyAfter"] >= 100)} 笔；捐出方捐前密度中位 {st.median(r["dMe"] for r in rows):.0f}，受赠方 捐前 {st.median(r["dAlly"] for r in rows):.0f} → 捐后 {st.median(r["dAllyAfter"] for r in rows):.0f}')
by = defaultdict(lambda: [0, 0, 0, 0])
for r in rows:
    x = by[r['kind']]; x[0] += 1; x[1] += r['got']; x[2] += r['fee']; x[3] += r['delta']
print('   按类别：' + '；'.join(f'{kk} {v[0]} 笔 到账 {k(v[1])} 税 {k(v[2])} 利息变化合计 {k(v[3])}/10拍' for kk, v in by.items()))
if '--list' in a:
    for r in rows:
        print(f"   t={r['t']} {r['p']}→{r['q']} {r['kind']} 到账 {k(r['got'])} 税 {k(r['fee'])}｜密度 {r['dMe']:.0f}→对方 {r['dAlly']:.0f}→{r['dAllyAfter']:.0f}｜两号利息 {r['delta']:+d}/10拍｜回本 {('%.0f 拍' % r['payback']) if r['payback'] else '不回本'}")
