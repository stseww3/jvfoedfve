#!/usr/bin/env python3
"""log_lag.py — 用日志行的先后顺序估计每个号的客户端落后服务器多少拍。
用法: python3 log_lag.py <matchId> [--every 450] [--bot name]
日志每行开头是全局递增的行号（写入顺序）。同一局里各号的 [HL-TICK] 行按写入顺序交错：
某号写下本地拍 t 的那一刻，全队已写出的最大本地拍 tmax 是“服务器至少走到了哪一拍”的下界，
lagLB = tmax - t 就是这个号落后的下界（全队都落后时会低估）。
另外对照录像：这个号在录像里的 leave 指令所在服务器拍，与它日志最后一条 [HL-TICK] 的本地拍之差。
输出: 每个号在若干本地拍处的 lagLB，以及全程最大值；写 out/<id>/log_lag.csv。
"""
import csv, os, re, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    a = sys.argv[1:]
    mid = a[0]
    every = int(a[a.index('--every') + 1]) if '--every' in a else 450
    rows = []
    tmax = 0
    pat = re.compile(r'^(\d+)\t\[([^\]]+)\] \[HL-TICK\] t=(\d+) terr=(\d+)\([^)]*\) bal=(\d+).* cmds=(\d+)')
    with open(f'/agent/repos/c136-data/bundles/{mid}/in_game.log', errors='replace') as f:
        for line in f:
            m = pat.match(line)
            if not m:
                continue
            seq, bot, t, cmds = int(m.group(1)), m.group(2), int(m.group(3)), int(m.group(6))
            tmax = max(tmax, t)
            rows.append((seq, bot, t, tmax, tmax - t, cmds))
    out = os.path.join(HERE, '..', 'out', mid)
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, 'log_lag.csv'), 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['seq', 'bot', 'localT', 'squadMaxT', 'lagLB', 'cmds'])
        w.writerows(rows)
    by = defaultdict(list)
    for r in rows:
        by[r[1]].append(r)
    # leave ticks from replay cmds
    leave = {}
    p = os.path.join(out, 'replay_cmds.csv')
    if os.path.exists(p):
        for r in csv.DictReader(open(p, newline='')):
            if r['kind'] == 'leave':
                leave[r['pname']] = int(r['tick'])
    only = a[a.index('--bot') + 1] if '--bot' in a else None
    print(f"== {mid} 客户端落后下界 lagLB（本地拍:落后拍）")
    for bot, rs in sorted(by.items()):
        if only and bot != only:
            continue
        pick = [r for r in rs if r[2] % every == 0]
        mx = max(rs, key=lambda r: r[4])
        lv = next((t for n, t in leave.items() if bot in n), None)
        tail = f" | 录像 leave@{lv}，日志最后本地拍 {rs[-1][2]}，差 {lv - rs[-1][2]}" if lv else ''
        print(f"  {bot:10s} " + ' '.join(f"{r[2]}:{r[4]}" for r in pick) + f" | 最大 {mx[4]}@本地{mx[2]}{tail}")


if __name__ == '__main__':
    main()
