#!/usr/bin/env python3
# client_lag.py — 只用我方日志的「行序号」估计每个号的客户端落后多少拍（不依赖录像配对）。
# 原理：in_game.log 每行开头是日志入库的顺序号。所有号的日志进同一个流，
#   所以「A 号打出 t=1375 的那一行」排在「B 号打出 t=990 的那一行」前后，就说明那一刻 B 的客户端才算到 990 拍前后。
#   对每个号的每条 [HL-TICK] t=X：落后量 = 此刻所有号里已经打出的最大 t − X（只能精确到 ±90 拍，因为 90 拍才打一行）。
# 用法：python3 scripts/client_lag.py <局号> [--bot 名字]
# 输出：每个号各时段落后量的中位/最大，以及落后 ≥180 拍的时段；--bot 逐行列出。
# 局限：领跑的那个号自己也可能落后于服务器，所以这是「相对最快的队友」的落后量，是下限。
import sys, os, re, collections, statistics

DATA = os.environ.get('C136_DATA', '/agent/repos/c136-data')


def load(mid):
    rows = []
    rx = re.compile(r'^(\d+)\t\[([^\]]+)\] \[HL-TICK\] t=(\d+) ')
    with open(os.path.join(DATA, 'bundles', mid, 'in_game.log'), encoding='utf8', errors='replace') as f:
        for line in f:
            m = rx.match(line)
            if m:
                rows.append((int(m.group(1)), m.group(2), int(m.group(3))))
    rows.sort()
    return rows


def lags(rows):
    front = 0
    out = collections.defaultdict(list)
    for seq, bot, t in rows:
        if t > front:
            front = t
        out[bot].append((t, front - t, seq))
    return out


def main():
    a = sys.argv[1:]
    mid = a[0]
    only = a[a.index('--bot') + 1] if '--bot' in a else None
    L = lags(load(mid))
    phases = [(0, 630, '<630'), (630, 1500, '630~1499'), (1500, 3000, '1500~2999'), (3000, 4284, '3000~4283'), (4284, 10 ** 9, '≥4284')]
    print(f'# {mid} 客户端落后量（相对最快的队友，单位拍；来自日志行序）')
    print('号        ' + ' '.join(f'{nm:>16s}' for _, _, nm in phases) + '   落后≥180 拍的快照（拍:落后）')
    for bot, v in L.items():
        if only and bot != only:
            continue
        cells = []
        for lo, hi, _ in phases:
            x = [lag for t, lag, _ in v if lo <= t < hi]
            cells.append(f'{statistics.median(x):5.0f}/{max(x):5d}（{len(x):3d}）' if x else '       -        ')
        big = [f'{t}:{lag}' for t, lag, _ in v if lag >= 180]
        print(f'{bot:8s}  ' + ' '.join(cells) + '   ' + (' '.join(big[:14]) + (' …' if len(big) > 14 else '') if big else '无'))
        if only:
            for t, lag, seq in v:
                print(f'   t={t:5d} 落后 {lag:5d}（行号 {seq}）')
    print('（每格：中位/最大（快照数））')


if __name__ == '__main__':
    main()
