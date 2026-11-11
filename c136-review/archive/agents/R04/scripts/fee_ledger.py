#!/usr/bin/env python3
# 陆攻手续费账：每条陆攻指令除了出征的兵，还要从余额里扣 12/1024（约 1.17%）的手续费，
# 不管这条指令出多少兵。这里统计我方各号全场付了多少手续费，以及「出的兵比手续费还少」的指令。
# 用法：python3 scripts/fee_ledger.py <局号> [--ours id,id,…] [--list]
# 数据：tmp/truth/<局号>/cmd.tsv（真引擎重放时逐条记下的 指令前余额 / 指令后余额 / 进攻槽登记的兵）。
import sys, collections
sys.dont_write_bytecode = True
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from match_digest import Match, fmt


def main():
    a = sys.argv[1:]
    mid = a[0]
    ours = [int(x) for x in a[a.index('--ours') + 1].split(',')] if '--ours' in a else None
    M = Match(mid, ours)
    n = collections.Counter(); troops = collections.Counter(); fee = collections.Counter()
    small_n = collections.Counter(); small_fee = collections.Counter(); small_tr = collections.Counter()
    small_tg = collections.defaultdict(collections.Counter)
    rows = []
    for c in M.cmd:
        if c['id'] != 1 or c['p'] not in M.ours:
            continue
        tr = sum(int(x[2]) for x in c['sub'] if x and x[0] == 'atk')
        if tr <= 0:
            continue
        f = c['bal0'] - c['bal1'] - tr
        b = M.nm(c['p'])
        n[b] += 1; troops[b] += tr; fee[b] += f
        if tr < f:
            small_n[b] += 1; small_fee[b] += f; small_tr[b] += tr
            tg = '无主地' if c['b'] >= 512 else M.nm(c['b'])
            small_tg[b][tg] += 1
            rows.append((c['t'], b, tg, c['a'], tr, f))
    print('%-8s %6s %10s %10s %7s | 出兵<手续费的指令：条数 / 出的兵 / 付的手续费 / 目标' % ('号', '条数', '出征兵', '手续费', '费/兵'))
    for b in sorted(n, key=lambda x: -fee[x]):
        print('%-8s %6d %10s %10s %6.1f%% | %d / %s / %s / %s' % (b, n[b], fmt(troops[b]), fmt(fee[b]), 100.0 * fee[b] / max(1, troops[b]),
              small_n[b], fmt(small_tr[b]), fmt(small_fee[b]), dict(small_tg[b].most_common(4))))
    print('合计：%d 条，出征 %s 兵，手续费 %s（%.1f%%）；出兵<手续费的指令 %d 条，白付手续费 %s' % (
        sum(n.values()), fmt(sum(troops.values())), fmt(sum(fee.values())), 100.0 * sum(fee.values()) / max(1, sum(troops.values())),
        sum(small_n.values()), fmt(sum(small_fee.values()))))
    if '--list' in a:
        for r in rows:
            print('  拍 %d %s → %s 比例 %d/1024 出兵 %s 手续费 %s' % (r[0], r[1], r[2], r[3], fmt(r[4]), fmt(r[5])))


if __name__ == '__main__':
    main()
