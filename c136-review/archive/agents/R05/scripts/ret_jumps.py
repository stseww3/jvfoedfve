#!/usr/bin/env python3
# ret_jumps.py — 「打出去又退回来的兵」：我方号每 30 拍窗里 进攻退兵（ret）≥ MIN 的窗口，配上此前 150 拍内它打出的各条陆攻（目标、兵数）。
#   用来看：一轮进攻打出去的兵有多少没换到地、原样退回（目标可达的地吃完 / 目标死了 / 目标被别人吃光）。
#   ret 来自录像重放真值的资金流水 F30（累计值，列序见 match_truth.mjs：eco, atkNeutral, atkBot, atkHuman, boat, donOut, donIn, ret, dmg, …）。
# 用法：python3 scripts/ret_jumps.py <matchId> [--min 50000] [--bots a,b]
import json, sys
a = sys.argv[1:]
mid = a[0]
val = lambda k, d: (a[a.index(k) + 1] if k in a else d)
MIN = int(val('--min', 50000))
J = json.load(open(f'/tmp/c136-r05/truth/{mid}.json'))
P = {p['id']: p for p in J['players']}
sq = {s['p']: s['bot'] for s in J['squad']}
only = val('--bots', '')
k = lambda v: f'{v / 1e6:.2f}M' if abs(v) >= 1e6 else f'{v / 1e3:.0f}k'
for pid, bot in sq.items():
    if only and bot not in only.split(','):
        continue
    F = J['F30'][str(pid)]
    T, fl = F['t'], F['flows']
    tot_ret = fl[-1][7]
    tot_h = -fl[-1][3]
    rows = []
    for i in range(1, len(T)):
        d = fl[i][7] - fl[i - 1][7]
        if d >= MIN:
            t0, t1 = T[i - 1], T[i]
            ev = [e for e in J['events'] if e['p'] == pid and e['type'] == 'attack' and e.get('ok', True) and t1 - 150 <= e['t'] < t1]
            by = {}
            for e in ev:
                q = e.get('q')
                nm = '中立' if q is None or q < 0 or q == 512 else (P[q]['name'] + f'#{q}' if q in P else f'机器人#{q}')
                by.setdefault(nm, [0, 0, e['t'], e['t']])
                by[nm][0] += 1; by[nm][1] += (e.get('troops') or 0); by[nm][3] = e['t']
            rows.append((t0, t1, d, by))
    print(f'[退兵] {mid} {bot}：全局退回 {k(tot_ret)}（打真人支出 {k(tot_h)}）；单窗 ≥{k(MIN)} 的退兵 {len(rows)} 次，合计 {k(sum(r[2] for r in rows))}')
    for t0, t1, d, by in rows:
        print(f'   拍 {t0}–{t1} 退回 {k(d)}｜此前 150 拍内打出：' + ('；'.join(f'{nm} {v[0]} 条 {k(v[1])}（{v[2]}–{v[3]}）' for nm, v in by.items()) or '无'))
