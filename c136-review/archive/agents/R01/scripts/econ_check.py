#!/usr/bin/env python3
"""econ_check.py — 逐窗口经济对账：用引擎的利息/领土收入公式，从每个 HL-TICK 快照推到下一个快照，
残差 = 实测余额 − 纯挂机推算余额。残差≈0 说明这 90 拍里余额只受利息和领土收入影响（没有任何出兵、
捐款、收款生效）；残差为负 = 有支出（出兵/捐款/税）；残差为正 = 有流入（收款/进攻兵返还）。
领土在窗口内变化时按起点领土推算，标 terrChanged（残差只作参考）。
用法: python3 econ_check.py <matchId> <bot> [t0 t1]
输出: out/<matchId>/econ_<bot>.csv + 屏幕打印
"""
import csv, json, os, re, sys
mid, bot = sys.argv[1], sys.argv[2]
T0 = int(sys.argv[3]) if len(sys.argv) > 3 else 0
T1 = int(sys.argv[4]) if len(sys.argv) > 4 else 10 ** 9
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'out', mid)
os.makedirs(OUT, exist_ok=True)
B = f'/agent/repos/c136-data/bundles/{mid}'
card = json.load(open(os.path.join(B, 'card.json')))
LAND = card['mapLand']
def isqrt_e(h):
    if h < 1: return 0
    a = (h + 1) // 2
    for _ in range(9):
        a = (a + h // a) // 2
    return a
TABLE = [100 + isqrt_e((25600 * i) // 508) for i in range(512)]
def rate(t, terr, bal):
    r = TABLE[min(511, (511 * terr) // LAND)]
    if t < 1920:
        r = max((100 * (13440 - 6 * t)) // 1920, r)
    cap = min(100 * terr, 10 ** 9)
    if bal > cap and cap > 0:
        r -= (2 * r * (bal - cap)) // cap
    return min(max(r, 0), 700)
def gain(bal, terr, g):
    g = min(g, terr * 150 - bal, int(1.5e9) - bal)
    return bal + max(g, 0)
def idle(bal, terr, t0, t1):
    for t in range(t0, t1):
        if t % 10 == 9:
            bal = gain(bal, terr, max((rate(t, terr, bal) * bal) // 10000, 1))
        if t % 100 == 99:
            bal = gain(bal, terr, terr)
    return bal
pat = re.compile(r'\[' + re.escape(bot) + r'\] \[HL-TICK\] t=(\d+) terr=(\d+)\([^)]*\) bal=(\d+) dens=([\d.]+) nb=(\d+) neut=(\d+) cmds=(\d+)')
snaps = []
for line in open(os.path.join(B, 'in_game.log'), errors='replace'):
    m = pat.search(line)
    if m:
        snaps.append(tuple(int(x) if i != 3 else float(x) for i, x in enumerate(m.groups())))
snaps.sort()
rows = []
for a, b in zip(snaps, snaps[1:]):
    if b[0] < T0 or a[0] > T1: continue
    pred = idle(a[2], a[1], a[0], b[0])
    rows.append(dict(t0=a[0], t1=b[0], terr0=a[1], terr1=b[1], bal0=a[2], bal1=b[2], idlePred=pred, resid=b[2] - pred,
                     residPct=round(100 * (b[2] - pred) / max(1, a[2]), 2), terrChanged=int(a[1] != b[1]),
                     nb0=a[4], neut0=a[5], dCmds=b[6] - a[6], atCap0=int(a[2] >= 150 * a[1]), rate0=rate(a[0] + 9, a[1], a[2])))
with open(os.path.join(OUT, f'econ_{bot}.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)
print(f'{mid} {bot}: {len(rows)} windows; columns t0-t1 terr0->terr1 bal0->bal1 idlePred resid(resid%) dCmds nb neut rate0(per 1e4/10ticks)')
for r in rows:
    flag = '' if abs(r['resid']) <= max(2, 0.002 * r['bal0']) else ('  <-- OUTFLOW' if r['resid'] < 0 else '  <-- INFLOW')
    if r['terrChanged']: flag += ' (terrChanged)'
    print(f"  {r['t0']:5d}-{r['t1']:5d} terr {r['terr0']:6d}->{r['terr1']:6d} bal {r['bal0']:8d}->{r['bal1']:8d} idle {r['idlePred']:8d} resid {r['resid']:8d} ({r['residPct']:6.2f}%) dCmds {r['dCmds']:3d} nb {r['nb0']} neut {r['neut0']:4d} rate {r['rate0']:3d}{flag}")
