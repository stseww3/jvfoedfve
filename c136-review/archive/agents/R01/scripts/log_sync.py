#!/usr/bin/env python3
"""log_sync.py — 只用日志的行序估计各客户端落后了多少拍（没有录像的实例用；A094 的 6 个号）。
用法：python3 log_sync.py <matchId> [--bots a,b,..] [--win 900]
依据：
  1) in_game.log 的行是按到达采集端的先后排的；每个号每 90 个本地拍打一行 [HL-TICK]。
  2) [RESULT] 行在 results.csv 里有墙上时间（at）和事件拍（tick）。事件拍 = 服务器拍（A094 用重演核过：zexos1 results 2577 / 重演 2570，ryan_m 4157 / 4154）。
     所以每条 [RESULT] 行是一个“此刻服务器拍 = S”的锚点；锚点前后紧挨着的 [HL-TICK] 行给出各号此刻的本地拍区间 [前一行 t, 后一行 t)，
     落后量就在 (S - 后一行 t, S - 前一行 t] 里。两个实例的开局时刻不同，--origin 号 用哪个号的 RESULT 定起点（默认最后一个 RESULT）。
  3) 行序本身还给一个下界：某号打出本地拍 t 那一行时，此前所有号里出现过的最大本地拍 lead，lead - t 就是它至少比最快的号落后的拍数。
输出：每个锚点一行；以及每个号按 --win 拍分窗的 lead - t 的最大值。
"""
import argparse, csv, re
from collections import defaultdict
from datetime import datetime

BUNDLES = '/agent/repos/c136-data/bundles'
TICK = re.compile(r'\[([a-z0-9_]+)\] \[HL-TICK\] t=(\d+)')
RES = re.compile(r'\[RESULT \[APEX\] ([a-z0-9_]+)\]')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mid'); ap.add_argument('--bots'); ap.add_argument('--win', type=int, default=900); ap.add_argument('--origin')
    a = ap.parse_args()
    lines = [l.rstrip('\n') for l in open(f'{BUNDLES}/{a.mid}/in_game.log', encoding='utf8')]
    res = {r['bot']: r for r in csv.DictReader(open(f'{BUNDLES}/{a.mid}/results.csv', newline=''))}
    only = set(a.bots.split(',')) if a.bots else None
    ticks = []  # (lineIdx, bot, t)
    anchors = []
    for i, l in enumerate(lines):
        m = TICK.search(l)
        if m:
            ticks.append((i, m.group(1), int(m.group(2))))
            continue
        m = RES.search(l)
        if m and m.group(1) in res:
            r = res[m.group(1)]
            anchors.append((i, m.group(1), int(r['tick']), datetime.fromisoformat(r['at'].replace('Z', '+00:00')).timestamp()))
    if not anchors:
        print('没有 RESULT 锚点'); return
    org = next((x for x in anchors if x[1] == a.origin), anchors[-1])
    T0 = org[3] - org[2] * 0.056
    bots = sorted({b for _, b, _ in ticks if not only or b in only})
    print(f'# {a.mid} 行序同步：起点取 {org[1]} 的 RESULT（拍 {org[2]}），每拍 56 毫秒；号 {",".join(bots)}')
    print('== 锚点（RESULT 行）：估算服务器拍 S；各号此刻本地拍所在区间 → 落后量区间')
    by = defaultdict(list)
    for i, b, t in ticks:
        by[b].append((i, t))
    for i, b0, tick, w in anchors:
        S = round((w - T0) / 0.056)
        cells = []
        for b in bots:
            prev = [t for j, t in by[b] if j < i]; nxt = [t for j, t in by[b] if j > i]
            if not prev or not nxt:
                continue
            lo, hi = prev[-1], nxt[0]
            cells.append(f'{b} [{lo},{hi}) 落后 {max(0, S - hi + 1)}..{max(0, S - lo)}')
        print(f'  {b0:<8} 事件拍 {tick:>5} S≈{S:>5} | ' + '; '.join(cells))
    print(f'== 行序下界：每个号打出本地拍 t 时，比此前出现过的最大本地拍至少落后多少（按 {a.win} 拍分窗取最大）')
    lead = 0; rows = defaultdict(lambda: defaultdict(int))
    for i, b, t in ticks:
        if (not only or b in only) and lead - t > rows[b][t // a.win * a.win]:
            rows[b][t // a.win * a.win] = lead - t
        lead = max(lead, t)
    wins = sorted({w for b in rows for w in rows[b]})
    print('  窗口     ' + ' '.join(f'{b:>8}' for b in bots))
    for w in wins:
        print(f'  {w:>5}+   ' + ' '.join(f'{rows[b].get(w, 0):>8}' for b in bots))


if __name__ == '__main__':
    main()
