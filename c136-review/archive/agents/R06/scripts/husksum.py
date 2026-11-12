#!/usr/bin/env python3
"""R06 空壳账（录像真值）：我方号在活着的时候被登记离开（空壳，内置 AI 托管、利息为 0、仍在原队）之后发生了什么。

用法：python3 husksum.py [<matchId> ...]      不带局号 = 有对局录像的 9 局

每局一行：
  空壳个数、登记离开的服务器拍、离开那一拍的地和兵（真引擎重放）；
  空壳的地最后给了谁（账本 lost，按对方类别：敌方真人 / 内置 AI / 我方在场号 / 队友…）；
  空壳与我方在场号之间的交换（simdigest.husk_rows：空壳拿走在场号多少格、在场号拿回多少）；
  我方在场号捐给空壳的笔数 / 到账 / 手续费（simdigest.don_rows 的 toLeft）；
  空壳期间少拿的利息（账本 huskLoss，没有这一项的局记 —）。
没开局的席位（离开拍 < 600 且整局没有出兵指令）单列，不算空壳。
"""
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import simdigest as SD  # noqa: E402

DEFAULT = ['B010', 'B017', 'B021', 'B022', 'B023', 'B025', 'B038', 'B039', 'B041']


def wan(n):
    n = float(n)
    if abs(n) >= 1e8:
        return f'{n / 1e8:.2f} 亿'
    if abs(n) >= 1e6:
        return f'{n / 1e4:,.0f} 万'
    if abs(n) >= 1e4:
        return f'{n / 1e4:.1f} 万'
    return f'{n:,.0f}'


def one(mid):
    X = SD.Sim(mid)
    S = X.S
    played = {c['p'] for c in S['squadCmds'] if c['k'] in ('atk', 'boat', 'boatAdd') and c.get('ok')}
    husks, never = [], []
    for p in X.squad:
        if p not in X.leave:
            continue
        t0 = X.leave[p]['t']
        if t0 < 600 and p not in played:
            never.append(p)
            continue
        if X.deathT[p] >= 0 and X.deathT[p] <= t0:
            continue
        husks.append(p)
    o = dict(id=mid, n=len(husks), never=len(never), ticks=sorted(X.leave[p]['t'] for p in husks), terr=0, bal=0, lost=defaultdict(int), fromLive=0, toLive=0, liveDmg=0,
             don=0, donDelivered=0, donFee=0, diedAsHusk=0, endAlive=0)
    for p in husks:
        t0 = X.leave[p]['t']
        o['terr'] += X.terr(p, t0) or 0
        o['bal'] += X.bal(p, t0) or 0
        for k, v in X.led_sum(p, 'lost', t0, X.end_of(p) + 1, by='cls').items():
            o['lost'][k] += v
        if X.deathT[p] >= 0:
            o['diedAsHusk'] += 1
        else:
            o['endAlive'] += 1
    for r in SD.husk_rows(X):
        if r['aHusk'] or r['h'] not in husks:
            continue
        o['fromLive'] += r['hGain']
        o['toLive'] += r['aGain']
        o['liveDmg'] += r['aDmg']
    for r in SD.don_rows(X):
        if r['ok'] and r['from'] in X.squad and r['toLeft'] and r['to'] in X.squad:
            o['don'] += 1
            o['donDelivered'] += r['delivered']
            o['donFee'] += r['fee']
    return o


def main():
    ids = [a for a in sys.argv[1:] if not a.startswith('-')] or DEFAULT
    out = [one(m) for m in ids]
    print('| 局 | 空壳（活着时被登记离开） | 登记离开的服务器拍 | 离开时的地 / 兵 | 之后阵亡 / 活到录像末 | 空壳的地给了谁（格） | 空壳从我方在场号手里拿走 / 在场号从空壳拿回（格） | 我方在场号捐给空壳：笔 / 到账 / 手续费 | 没开局的席位 |')
    print('|---|---|---|---|---|---|---|---|---|')
    tl = defaultdict(int)
    for o in out:
        for k, v in o['lost'].items():
            tl[k] += v
        lost = '；'.join(f"{k} {v:,}" for k, v in sorted(o['lost'].items(), key=lambda kv: -kv[1])[:4]) or '—'
        tk = f"{o['ticks'][0]}~{o['ticks'][-1]}" if o['ticks'] else '—'
        print(f"| {o['id']} | {o['n']} | {tk} | {o['terr']:,} / {wan(o['bal'])} | {o['diedAsHusk']} / {o['endAlive']} | {lost} | {o['fromLive']:,} / {o['toLive']:,} | "
              f"{o['don']} / {wan(o['donDelivered'])} / {wan(o['donFee'])} | {o['never']} |")
    s = lambda k: sum(o[k] for o in out)
    allt = sorted(t for o in out for t in o['ticks'])
    lost = '；'.join(f"{k} {v:,}（{100 * v / max(1, sum(tl.values())):.0f}%）" for k, v in sorted(tl.items(), key=lambda kv: -kv[1])[:5])
    print(f"| 合计 | {s('n')} | 600~2100 拍 {sum(1 for t in allt if 600 <= t < 2100)} 个、其余 {sum(1 for t in allt if not 600 <= t < 2100)} 个 | {s('terr'):,} / {wan(s('bal'))} | {s('diedAsHusk')} / {s('endAlive')} | {lost} | "
          f"{s('fromLive'):,} / {s('toLive'):,} | {s('don')} / {wan(s('donDelivered'))} / {wan(s('donFee'))} | {s('never')} |")


if __name__ == '__main__':
    main()
