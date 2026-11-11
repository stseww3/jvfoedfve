#!/usr/bin/env python3
# flows_win.py — 我方号在任意拍窗内的兵力收支（录像重放真值 F30 的差分）和地的进出（HS / pairAll 不够细，这里只给兵）。
#   F30 每 30 拍一个累计点，窗口边界取 ≤ 该拍的最近一个点。列：利息+地租 / 打中立 / 打机器人 / 打真人 / 出船 / 捐出 / 收到捐兵 / 进攻退兵 / 被打掉 / 开火补兵 / 船靠岸 / 其它。
# 用法：python3 scripts/flows_win.py <matchId> --wins 0:1500,1500:3000,3822:4879,4879:6600,6600:7500 [--bots ryan_m]
import json, sys, bisect
a = sys.argv[1:]
mid = a[0]
val = lambda k, d: (a[a.index(k) + 1] if k in a else d)
J = json.load(open(f'/tmp/c136-r05/truth/{mid}.json'))
CAT = ['利息+地租', '打中立', '打机器人', '打真人', '出船', '捐出', '收到捐兵', '进攻退兵', '被打掉', '开火补兵', '船靠岸', '其它']
sq = {s['p']: s['bot'] for s in J['squad']}
only = val('--bots', '')
wins = [tuple(int(x) for x in w.split(':')) for w in val('--wins', '0:99999').split(',')]
k = lambda v: ('+' if v > 0 else '') + (f'{v / 1e6:.2f}M' if abs(v) >= 1e6 else f'{v / 1e3:.0f}k')
for pid, bot in sq.items():
    if only and bot not in only.split(','):
        continue
    F = J['F30'][str(pid)]; T = F['t']; fl = F['flows']
    S = J['S10'][str(pid)] if isinstance(J['S10'], dict) else None

    def at(t):
        i = bisect.bisect_right(T, t) - 1
        return fl[i] if i >= 0 else [0] * len(CAT)
    for t0, t1 in wins:
        x, y = at(t0), at(t1)
        d = [y[i] - x[i] for i in range(len(CAT))]
        print(f'[窗内收支] {mid} {bot} {t0}–{min(t1, T[-1])}：' + ' '.join(f'{CAT[i]} {k(d[i])}' for i in range(len(CAT)) if abs(d[i]) >= 1000) + f'｜净 {k(sum(d))}')
