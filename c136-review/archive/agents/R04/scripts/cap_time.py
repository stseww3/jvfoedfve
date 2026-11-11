#!/usr/bin/env python3
# 余额压在上限上的时间：每个我方号在各时段里密度（余额/领土）超过软上限 100、贴着硬上限 150 的拍数，
# 以及那一刻编队总余额里有多少压在「密度>100 的号」身上（这些兵的利息按超出比例打折，到 150 归零）。
# 用法：python3 scripts/cap_time.py <局号> [--win t0,t1,…] [--ours id,id,…]
# 口径：state.tsv 每 10 拍一个快照，一条快照算 10 拍；硬上限按 密度 ≥ 149.5 计；领土为 0 的快照不计。
import sys, os, collections
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from match_digest import Match, fmt


def main():
    a = sys.argv[1:]
    mid = a[0]
    ours = [int(x) for x in a[a.index('--ours') + 1].split(',')] if '--ours' in a else None
    M = Match(mid, ours)
    last = M.samples[-1]
    edges = [int(x) for x in a[a.index('--win') + 1].split(',')] if '--win' in a else [0, 1500, 3000, 4284, last]
    edges = [min(e, last) for e in edges]
    print('# %s 压在上限上的时间（拍）：每格 = 密度>100 的拍数 / 其中密度≥149.5（硬上限）的拍数' % mid)
    print('号 | ' + ' | '.join('(%d,%d]' % (edges[i], edges[i + 1]) for i in range(len(edges) - 1)) + ' | 全场')
    tot = collections.Counter()
    for p in M.our_ids:
        cells = []
        s_over = s_hard = 0
        for i in range(len(edges) - 1):
            over = hard = 0
            for t in M.samples:
                if not (edges[i] < t <= edges[i + 1]):
                    continue
                s = M.state[t].get(p)
                if not s or s[0] <= 0:
                    continue
                d = s[1] / s[0]
                if d > 100:
                    over += 10
                if d >= 149.5:
                    hard += 10
            cells.append('%d / %d' % (over, hard))
            s_over += over; s_hard += hard
            tot[(i, 'o')] += over; tot[(i, 'h')] += hard
        print('%s | %s | %d / %d' % (M.nm(p), ' | '.join(cells), s_over, s_hard))
    print('合计（号·拍） | ' + ' | '.join('%d / %d' % (tot[(i, 'o')], tot[(i, 'h')]) for i in range(len(edges) - 1)))
    print('各时段里，编队总余额压在「密度>100 的号」身上的比例（按快照平均）与这些号的个数（平均）：')
    for i in range(len(edges) - 1):
        fr, n, k = 0.0, 0.0, 0
        for t in M.samples:
            if not (edges[i] < t <= edges[i + 1]):
                continue
            S = M.state[t]
            b = [(S[p][1], S[p][1] / S[p][0]) for p in M.our_ids if p in S and S[p][0] > 0]
            if not b:
                continue
            allb = sum(x[0] for x in b)
            fr += sum(x[0] for x in b if x[1] > 100) / max(1, allb)
            n += sum(1 for x in b if x[1] > 100)
            k += 1
        if k:
            print('  (%d,%d]：%.0f%% 的余额，平均 %.1f 个号' % (edges[i], edges[i + 1], 100 * fr / k, n / k))


if __name__ == '__main__':
    main()
