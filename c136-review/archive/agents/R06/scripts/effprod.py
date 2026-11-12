#!/usr/bin/env python3
"""effprod.py — 有效产兵账（录像真值，按时间段；只读已有的 sim_state.json，不重放）

有效产兵 = 实得利息（含地租） − 出兵/发船手续费 − 捐款手续费 − 回兵溢出（兵回来时撞硬上限被削掉的部分）
应得利息 = 实得利息 + 顶格少拿（兵超过 100×领土后利率被降档、以及撞 150×领土硬上限而少拿的利息）
有效产兵率 = 有效产兵 ÷ 应得利息

口径：我方号（含离开以后的空壳席位：空壳不生利息，另列「空壳少拿」）。账按 100 拍一格记，分段边界取 100 的整数倍
（RFC 的 t=1500~4284 这里是 1500~4300）。

用法：python3 scripts/effprod.py            产物：out/_cross/effprod.txt
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import simdigest as SD  # noqa: E402
from r06lib import OUT  # noqa: E402

IDS = ['B010', 'B017', 'B021', 'B022', 'B023', 'B025', 'B038', 'B039', 'B041']
BANDS = [(0, 600, '<600'), (600, 1500, '600~1500'), (1500, 4300, '1500~4300'), (4300, 10 ** 9, '>=4300')]
KS = ['inc', 'capLoss', 'huskLoss', 'fee', 'donFee', 'capRet']


def wan(v):
    v = float(v)
    if abs(v) >= 1e8:
        return f'{v / 1e8:.2f} 亿'
    if abs(v) >= 1e4:
        return f'{v / 1e4:,.0f} 万' if abs(v) >= 1e6 else f'{v / 1e4:.1f} 万'
    return f'{v:,.0f}'


def pc(a, b):
    return f'{100 * a / b:.0f}%' if b else '—'


def main():
    lines = []
    tot = {b[2]: dict.fromkeys(KS, 0) for b in BANDS}
    nm = dict.fromkeys((b[2] for b in BANDS), 0)
    per = {}
    for mid in IDS:
        X = SD.Sim(mid)
        row = {}
        for a, b, name in BANDS:
            if a >= X.endT:
                row[name] = None
                continue
            s = {k: sum(X.led_sum(p, k, a, min(b, X.endT + 1)) for p in X.squad) for k in KS}
            row[name] = s
            nm[name] += 1
            for k in KS:
                tot[name][k] += s[k]
        per[mid] = (X.endT, row)

    def cell(s):
        if not s:
            return '—'
        eff = s['inc'] - s['fee'] - s['donFee'] - s['capRet']
        due = s['inc'] + s['capLoss']
        return f"{wan(eff)} / {wan(due)}（{pc(eff, due)}）"

    def cell2(s):
        if not s:
            return '—'
        return f"顶格少拿 {pc(s['capLoss'], s['inc'] + s['capLoss'])}、捐款费 {pc(s['donFee'], s['inc'])}、出兵/发船费 {pc(s['fee'], s['inc'])}"

    lines.append('**有效产兵 / 应得利息（有效产兵率）**，我方号合计，按时间段')
    lines.append('')
    lines.append('| 局 | 录像末拍 | ' + ' | '.join(b[2] for b in BANDS) + ' |')
    lines.append('|---|---|' + '---|' * len(BANDS))
    for mid in IDS:
        end, row = per[mid]
        lines.append(f"| {mid} | {end} | " + ' | '.join(cell(row[b[2]]) for b in BANDS) + ' |')
    lines.append('| 合计 | — | ' + ' | '.join(f"{cell(tot[b[2]])}，{nm[b[2]]} 局" for b in BANDS) + ' |')
    lines.append('')
    lines.append('**损耗拆开看**（顶格少拿 ÷ 应得；捐款手续费、出兵/发船手续费 ÷ 实得利息）')
    lines.append('')
    lines.append('| 局 | ' + ' | '.join(b[2] for b in BANDS) + ' |')
    lines.append('|---|' + '---|' * len(BANDS))
    for mid in IDS:
        end, row = per[mid]
        lines.append(f"| {mid} | " + ' | '.join(cell2(row[b[2]]) for b in BANDS) + ' |')
    lines.append('| 合计 | ' + ' | '.join(cell2(tot[b[2]]) for b in BANDS) + ' |')
    lines.append('')
    for a, b, name in BANDS:
        s = tot[name]
        eff = s['inc'] - s['fee'] - s['donFee'] - s['capRet']
        lines.append(f"   {name}（{nm[name]} 局）：实得利息 {wan(s['inc'])}、顶格少拿 {wan(s['capLoss'])}、空壳少拿 {wan(s['huskLoss'])}、出兵/发船手续费 {wan(s['fee'])}、捐款手续费 {wan(s['donFee'])}、"
                     f"回兵溢出 {wan(s['capRet'])} → 有效产兵 {wan(eff)}，有效产兵率 {pc(eff, s['inc'] + s['capLoss'])}")
    rates = []
    for mid in IDS:
        s = per[mid][1]['1500~4300']
        if s and per[mid][0] >= 4300:
            rates.append((mid, (s['inc'] - s['fee'] - s['donFee'] - s['capRet']) / max(1, s['inc'] + s['capLoss'])))
    rates.sort(key=lambda x: x[1])
    lines.append('   1500~4300 各局有效产兵率（录像到 4300 拍的局，从低到高）：' + '、'.join(f'{m} {100 * r:.0f}%' for m, r in rates))
    txt = '\n'.join(lines) + '\n'
    os.makedirs(os.path.join(OUT, '_cross'), exist_ok=True)
    open(os.path.join(OUT, '_cross', 'effprod.txt'), 'w').write(txt)
    print(txt)


if __name__ == '__main__':
    main()
