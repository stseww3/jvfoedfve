#!/usr/bin/env python3
# 敌方头号的账本：它的地是从谁手里拿的、它对我方各号出了多少兵、我方对它出了多少兵。
# 用法：python3 scripts/enemy_ledger.py <局号> [--p 引擎编号] [--win t0,t1,t2,…] [--strikes t0 t1] [--ours id,id,…]
#   不给 --p 时取「终局领土最大的非我方队真人」；--win 给出窗口边界（默认每 600 拍一段）。
# 「兵」= 实际出征的兵，不含每条指令另扣的手续费（余额的 12/1024）。
# 数据：tmp/truth/<局号>/（engine_truth.cjs 的真引擎重放）。flow.tsv 只记与我方队有关的地块流动，
#       所以「来自我方队」是精确的，它从别的队拿的地只能用「领土变化 − 我方队净流入」反推。
import sys, collections
sys.dont_write_bytecode = True
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from match_digest import Match, fmt


def main():
    a = sys.argv[1:]
    mid = a[0]
    ours = None
    if '--ours' in a:
        ours = [int(x) for x in a[a.index('--ours') + 1].split(',')]
    M = Match(mid, ours)
    last = M.samples[-1]
    if '--p' in a:
        E = int(a[a.index('--p') + 1])
    else:
        best = (-1, -1)
        for p in range(M.ku):
            if M.team.get(p) == M.our_team:
                continue
            terr = max((M.state[t][p][0] for t in M.samples[-3:] if p in M.state[t]), default=0)
            if terr > best[0]:
                best = (terr, p)
        E = best[1]
    if '--win' in a:
        edges = [int(x) for x in a[a.index('--win') + 1].split(',')]
    else:
        edges = list(range(0, last, 600)) + [last]
    print('敌方头号：%s（引擎编号 %d，队 %s）' % (M.nm(E), E, M.team.get(E)))

    def nm(p):
        return '无主地' if p >= 512 or p < 0 else M.nm(p)

    sent = collections.defaultdict(lambda: [0, 0])   # 窗口 -> [条数, 兵]  它打我方号
    recv = collections.defaultdict(lambda: [0, 0])   # 我方号打它
    other = collections.defaultdict(lambda: [0, 0])  # 它打别人
    def widx(t):
        for i in range(len(edges) - 1):
            if edges[i] < t <= edges[i + 1]:
                return i
        return None
    def troops(c):
        # 实际出征的兵（引擎里进攻槽登记的数）；余额另外还要扣一笔手续费 = 余额的 12/1024
        return sum(int(x[2]) for x in c['sub'] if x and x[0] == 'atk')
    for c in M.cmd:
        if c['id'] != 1:
            continue
        s = troops(c)
        if s <= 0:
            continue
        i = widx(c['t'])
        if i is None:
            continue
        if c['p'] == E and c['b'] in M.ours:
            sent[i][0] += 1; sent[i][1] += s
        elif c['p'] == E:
            other[i][0] += 1; other[i][1] += s
        elif c['p'] in M.ours and c['b'] == E:
            recv[i][0] += 1; recv[i][1] += s
    tot_in = 0
    for i in range(len(edges) - 1):
        t0, t1 = edges[i], edges[i + 1]
        s0 = M.state[M.at(t0)].get(E); s1 = M.state[M.at(t1)].get(E)
        if not s0 or not s1:
            continue
        g = collections.Counter()
        for (t, frm, to, n) in M.flow:
            if t0 < t <= t1:
                if to == E:
                    g[nm(frm)] += n
                if frm == E:
                    g[nm(to)] -= n
        net = sum(g.values()); tot_in += net
        print('(%d,%d] 领土 %d→%d（%+d），余额 %s→%s；与我方队的地块净流入 %+d %s；它打我方号 %d 条 %s 兵，打别人 %d 条 %s 兵；我方号打它 %d 条 %s 兵' % (
            t0, t1, s0[0], s1[0], s1[0] - s0[0], fmt(s0[1]), fmt(s1[1]), net,
            {k: v for k, v in g.most_common() if abs(v) >= 300},
            sent[i][0], fmt(sent[i][1]), other[i][0], fmt(other[i][1]), recv[i][0], fmt(recv[i][1])))
    print('合计：从我方队净拿 %d 格；对我方号出兵 %s（%d 条），我方号对它出兵 %s（%d 条）' % (
        tot_in, fmt(sum(v[1] for v in sent.values())), sum(v[0] for v in sent.values()),
        fmt(sum(v[1] for v in recv.values())), sum(v[0] for v in recv.values())))
    if '--strikes' in a:
        i = a.index('--strikes'); t0, t1 = int(a[i + 1]), int(a[i + 2])
        print('它在 [%d,%d] 的每一发陆攻（拍 / 目标 / 兵 / 它当时 地·兵 / 目标当时 地·兵·密度）：' % (t0, t1))
        for c in M.cmd:
            if c['id'] == 1 and c['p'] == E and t0 <= c['t'] <= t1:
                s = troops(c)
                if s <= 0:
                    continue
                S = M.state[M.at(c['t'])]
                me = S.get(E, (0, 0)); q = S.get(c['b'], (0, 0))
                print('  %d → %s %s 兵 | 它 %d·%s | 目标 %d·%s·%.0f' % (c['t'], nm(c['b']), fmt(s), me[0], fmt(me[1]), q[0], fmt(q[1]), q[1] / max(1, q[0])))


if __name__ == '__main__':
    main()
