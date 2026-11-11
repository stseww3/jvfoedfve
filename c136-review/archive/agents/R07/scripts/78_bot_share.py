#!/usr/bin/env python3
"""78_bot_share.py — R07：我方某几个号（比如被围在里面的内圈号）在各时刻占全队领土 / 余额的份额。

输入：out/<mid>/truth_bots.tsv（60_truth.cjs：真引擎重放，每 10 拍一采样：t bot p terr bal alive state boats）
用法：python3 78_bot_share.py <matchId> --bots noah88,alex_k,kaito9 --at 990,1530,1800 [--tag name]
输出：out/<mid>/bot_share[_<tag>].txt
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    if len(sys.argv) < 2 or '--bots' not in sys.argv or '--at' not in sys.argv:
        print(__doc__)
        sys.exit(2)
    mid = sys.argv[1]
    bots = sys.argv[sys.argv.index('--bots') + 1].split(',')
    at = [int(x) for x in sys.argv[sys.argv.index('--at') + 1].split(',')]
    tag = sys.argv[sys.argv.index('--tag') + 1] if '--tag' in sys.argv else ''
    out = os.path.join(HERE, '..', 'out', mid)
    rows = {}
    ticks = set()
    for r in csv.DictReader(open(os.path.join(out, 'truth_bots.tsv')), delimiter='\t'):
        t = int(r['t'])
        ticks.add(t)
        rows[(t, r['bot'])] = (int(r['terr']), int(r['bal']), int(r['alive']), int(r['state']))
    ticks = sorted(ticks)
    names = sorted({b for (_, b) in rows})
    miss = [b for b in bots if b not in names]
    if miss:
        print('没有这些号：', miss)
        sys.exit(2)
    L = [f'# {mid} 指定的 {len(bots)} 个号（{"、".join(bots)}）占我方全队的份额（真引擎重放；只算在场、未离开的号）',
         't\t全队 号数 / 领土 / 余额 / 密度\t这几个号 在场数 / 领土 / 余额 / 密度\t占全队领土\t占全队余额\t其余号 领土 / 余额 / 密度\t逐号 领土/余额/密度']
    for t in at:
        tt = max([x for x in ticks if x <= t] or [ticks[0]])
        live = [b for b in names if (tt, b) in rows and rows[(tt, b)][2] and rows[(tt, b)][3] != 2 and rows[(tt, b)][0] > 0]
        sub = [b for b in live if b in bots]
        rest = [b for b in live if b not in bots]
        T = sum(rows[(tt, b)][0] for b in live)
        B = sum(rows[(tt, b)][1] for b in live)
        st = sum(rows[(tt, b)][0] for b in sub)
        sb = sum(rows[(tt, b)][1] for b in sub)
        rt, rb = T - st, B - sb
        cells = ' '.join(f"{b} {rows[(tt, b)][0]:,}/{rows[(tt, b)][1]:,}/{rows[(tt, b)][1] / max(1, rows[(tt, b)][0]):.0f}" for b in sub)
        L.append(f"{tt}\t{len(live)} / {T:,} / {B:,} / {B / max(1, T):.0f}\t{len(sub)} / {st:,} / {sb:,} / {sb / max(1, st):.0f}\t{100 * st / max(1, T):.1f}%\t{100 * sb / max(1, B):.1f}%\t{rt:,} / {rb:,} / {rb / max(1, rt):.0f}\t{cells}")
    fn = os.path.join(out, f"bot_share{'_' + tag if tag else ''}.txt")
    open(fn, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print('\n'.join(L))


if __name__ == '__main__':
    main()
