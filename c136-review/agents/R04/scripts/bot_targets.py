#!/usr/bin/env python3
# 每个我方号在各时段把兵打到了谁身上、换回多少地。
# 用法：python3 scripts/bot_targets.py <局号> [--win t0,t1,…] [--bot 名字[,名字…]] [--ours id,id,…] [--min 兵数]
# 口径：陆攻 = cmd.tsv 里落地并在进攻槽登记了兵的陆攻指令（兵数取进攻槽登记数，不含 12/1024 手续费）；
#   船 = 落地的发船指令（装船兵）；地块净流 = flow.tsv 里该号与各方之间的像素净流入（正 = 我得地）。
#   同一拍 ≥3 条打同一目标的记为「同拍连发」（追帧后的批量落地）。
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
    only = a[a.index('--bot') + 1].split(',') if '--bot' in a else None
    mn = int(a[a.index('--min') + 1]) if '--min' in a else 0

    def nm(p):
        return '无主地' if p >= 512 or p < 0 else M.nm(p)

    def tr(c, k):
        return sum(int(x[2]) for x in c['sub'] if x and x[0] == k)
    for p in M.our_ids:
        if only and M.nm(p) not in only:
            continue
        print('== %s' % M.nm(p))
        for i in range(len(edges) - 1):
            t0, t1 = edges[i], edges[i + 1]
            tg, n, batch = collections.Counter(), collections.Counter(), collections.Counter()
            per_tick = collections.Counter()
            boats = bt = 0
            for c in M.cmd:
                if c['p'] != p or not (t0 < c['t'] <= t1):
                    continue
                if c['id'] == 1 and tr(c, 'atk') > 0:
                    k = nm(c['b'])
                    tg[k] += tr(c, 'atk'); n[k] += 1
                    per_tick[(c['t'], k)] += 1
                elif c['id'] == 3 and tr(c, 'boat') > 0:
                    boats += 1; bt += tr(c, 'boat')
            for (t, k), v in per_tick.items():
                if v >= 3:
                    batch[k] += 1
            g = collections.Counter()
            for (t, frm, to, px) in M.flow:
                if t0 < t <= t1:
                    if to == p:
                        g[nm(frm)] += px
                    if frm == p:
                        g[nm(to)] -= px
            s0 = M.state[M.at(t0)].get(p, (0, 0)); s1 = M.state[M.at(t1)].get(p, (0, 0))
            parts = []
            for k, v in tg.most_common():
                if v < mn:
                    continue
                parts.append('%s %d 条 %s 兵%s，净得地 %+d' % (k, n[k], fmt(v), ('（同拍连发 %d 次）' % batch[k]) if batch[k] else '', g.get(k, 0)))
            lost = ['%s %+d' % (k, v) for k, v in sorted(g.items(), key=lambda kv: kv[1]) if v <= -500 and k not in tg]
            print('  (%d,%d] 地 %d→%d 兵 %s→%s | 陆攻：%s | 船 %d 条 %s 兵%s' % (
                t0, t1, s0[0], s1[0], fmt(s0[1]), fmt(s1[1]), '；'.join(parts) if parts else '无', boats, fmt(bt),
                (' | 被拿走：' + '，'.join(lost)) if lost else ''))


if __name__ == '__main__':
    main()
