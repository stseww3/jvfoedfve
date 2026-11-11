#!/usr/bin/env python3
"""tick_cost.py — 从日志 [HL-TICK] 行读策略自身的每次决策耗时（avgMs 累计均值、maxMs 最大值、skip 跳过次数）。
用法：python3 tick_cost.py <matchId> [--log id1,id2]
用来回答“客户端落后是不是策略算得慢”：avgMs 是每次 act 的毫秒数，游戏一拍 56 毫秒、每 5 拍 act 一次。
另外按日志行的先后顺序检查各号的本地拍是否齐步走（同一个 90 拍快照，各号写日志的行号跨度）。
"""
import re, sys
from collections import defaultdict

a = sys.argv[1:]
mid = a[0]
logs = a[a.index('--log') + 1].split(',') if '--log' in a else [mid]
pat = re.compile(r'^(\d+)\t\[([^\]]+)\] \[HL-TICK\] t=(\d+) .*avgMs=([\d.]+) maxMs=([\d.]+) skip=(\d+)')
for lid in logs:
    by = defaultdict(list)
    order = []
    for line in open(f'/agent/repos/c136-data/bundles/{lid}/in_game.log', errors='replace'):
        m = pat.match(line)
        if m:
            by[m.group(2)].append((int(m.group(3)), float(m.group(4)), float(m.group(5)), int(m.group(6))))
            order.append((int(m.group(1)), m.group(2), int(m.group(3))))
    if not by:
        print(f'{lid}: 日志里的 HL-TICK 行没有 avgMs 字段')
        continue
    print(f'== {lid} 策略决策耗时（HL-TICK）：号 | 快照数 | avgMs 最大 | maxMs 最大 | skip 最大')
    for b, xs in by.items():
        print(f'   {b:10s} {len(xs):4d} | {max(x[1] for x in xs):5.2f} | {max(x[2] for x in xs):5.1f} | {max(x[3] for x in xs)}')
    print(f'   全队 avgMs 最大 {max(x[1] for xs in by.values() for x in xs):.2f} 毫秒，maxMs 最大 {max(x[2] for xs in by.values() for x in xs):.1f} 毫秒')
    # 齐步走：按写入顺序，任一时刻各号最新本地拍的极差
    last = {}
    worst = (0, 0)
    for seq, b, t in order:
        last[b] = t
        live = [v for k, v in last.items()]
        if len(live) >= 2:
            # 只看还在写日志的号：最近一次写入不早于全队最新拍 - 180
            mx = max(live)
            act = [v for v in live if v >= mx - 180]
            sp = mx - min(act)
            if sp > worst[0]:
                worst = (sp, t)
    print(f'   按日志写入顺序，仍在推进的各号本地拍极差最大 {worst[0]} 拍（出现在本地拍 {worst[1]} 附近）：各客户端是一起变慢的')

    # [HL-SLOW-TICK] 行：单次决策超过阈值时策略自己打的日志。按号、按 1000 拍分窗计数；
    # 再和影子策略里“走到出海搜索”的决策拍（shadow_cmds.csv 里 kind=boatTo 的行）对一下，看慢拍是不是出在找船上。
    slow = defaultdict(list)
    sp = re.compile(r'\[([^\]]+)\] \[HL-SLOW-TICK\] t=(\d+) took ([\d.]+)ms')
    for line in open(f'/agent/repos/c136-data/bundles/{lid}/in_game.log', errors='replace'):
        m = sp.search(line)
        if m:
            slow[m.group(1)].append((int(m.group(2)), float(m.group(3))))
    if slow:
        import csv, os
        n = sum(len(v) for v in slow.values())
        print(f'== {lid} HL-SLOW-TICK {n} 条：号 | 条数 | 最慢毫秒 | 按 1000 拍分窗的条数 | 相邻两条的间隔（拍）中位')
        boats = defaultdict(set)
        cp = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out', lid, 'shadow_cmds.csv')
        if os.path.exists(cp):
            for r in csv.DictReader(open(cp, encoding='utf8')):
                if r['kind'] == 'boatTo':
                    boats[r['bot']].add(int(r['t']))
        for b, xs in sorted(slow.items()):
            win = defaultdict(int)
            for t, ms in xs:
                win[t // 1000 * 1000] += 1
            gaps = sorted(y[0] - x[0] for x, y in zip(xs, xs[1:]))
            hit = sum(1 for t, ms in xs if t in boats.get(b, ()))
            print(f"   {b:10s} {len(xs):3d} | {max(ms for t, ms in xs):6.1f} | " + ' '.join(f'{k}:{v}' for k, v in sorted(win.items()))
                  + f" | {gaps[len(gaps) // 2] if gaps else '-'}" + (f" | 其中 {hit} 条的拍正好是影子策略发出船令的决策拍（共 {len(boats.get(b, ()))} 条船令）" if boats else ''))
