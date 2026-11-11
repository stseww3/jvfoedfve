#!/usr/bin/env python3
# boat_pairs.py — 我方的船按「去打谁」和「是不是一前一后去同一个落点」分类。
# 用法：python3 scripts/boat_pairs.py <局号> [--ours id,id,…] [--win t0,t1,…] [--list]
# 口径（全部来自 tmp/truth/<局号>/ 的 cmd.tsv / ev.tsv / flow.tsv / state.tsv）：
#   载兵 = 发船指令登记在船上的兵；船手续费 = 发船那一拍余额减少量 − 载兵（引擎按余额的 32/1024 收）；
#   结果 = 同一船号的登陆事件：登陆打 真人 / 内置AI / 无主地，或「回到自己地上」（落点已经是自己的地，船上的兵退回余额）；
#   同落点船对 = 同一个号在 15 拍内向同一个落点像素（发船指令的目标参数相同）先后发的两条船；
#   「登陆时目标有多大」= 登陆那一拍目标的领土和余额（真人取 state.tsv；内置 AI 没有逐拍记录，只给登陆后 300 拍从它净得的地）。
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
    edges = [int(x) for x in a[a.index('--win') + 1].split(',')] if '--win' in a else [0, 4284, last + 1]
    show = '--list' in a

    def nm(p):
        return '无主地' if p >= 512 or p < 0 else M.nm(p)
    ends = {}
    for (t, kind, pl, x, y, det) in M.ev:
        if kind in ('land', 'sunk', 'boatend') and pl in M.ours:
            ends.setdefault((pl, int(x)), (t, kind, y, det))
    rows = []
    for c in M.cmd:
        if c['id'] != 3 or c['p'] not in M.ours:
            continue
        for s in c['sub']:
            if not s or s[0] != 'boat':
                continue
            bid, troops = int(s[1]), int(s[2])
            fee = max(0, c['bal0'] - c['bal1'] - troops)
            e = ends.get((c['p'], bid))
            cls, tgt, arrived, te = '还在海上', None, None, None
            if e:
                te, kind, y, det = e
                tail = det.split('|', 1)[1] if '|' in det else ''
                if kind == 'sunk':
                    cls, arrived = '沉没', 0
                elif tail.startswith('atk:'):
                    f = tail.split(':'); tgt = int(f[1]); arrived = int(f[2])
                    cls = '无主地' if tgt >= 512 else ('真人' if tgt < M.ku else '内置AI')
                elif tail.startswith('give:'):
                    f = tail.split(':'); tgt = int(f[1]); arrived = int(f[2]); cls = '移交队友'
                elif tail.startswith('home_or_lost'):
                    cls = '回到自己地上'
                    try:
                        arrived = max(0, int(tail.split(':')[1]))
                    except (IndexError, ValueError):
                        arrived = None
                else:
                    cls = '其他'
            gain = None
            if tgt is not None and tgt < 512 and te is not None:
                gain = 0
                for (t, frm, to, px) in M.flow:
                    if te <= t <= te + 300:
                        if to == c['p'] and frm == tgt:
                            gain += px
                        if frm == c['p'] and to == tgt:
                            gain -= px
            rows.append(dict(t=c['t'], p=c['p'], pct=c['a'], spot=c['b'], bal0=c['bal0'], terr=c['terr0'], troops=troops, fee=fee,
                             te=te, cls=cls, tgt=tgt, arrived=arrived, gain=gain, pair=None))
    rows.sort(key=lambda r: (r['p'], r['t']))
    # 同落点船对
    for i, r in enumerate(rows):
        for j in range(i + 1, len(rows)):
            s = rows[j]
            if s['p'] != r['p'] or s['t'] - r['t'] > 15:
                break
            if s['spot'] == r['spot'] and r['pair'] is None and s['pair'] is None:
                r['pair'] = ('first', j); s['pair'] = ('second', i)
                break
    print('# %s 我方的船：%d 条，载兵 %s，船手续费 %s' % (mid, len(rows), fmt(sum(r['troops'] for r in rows)), fmt(sum(r['fee'] for r in rows))))
    for lo, hi in zip(edges, edges[1:]):
        seg = [r for r in rows if lo <= r['t'] < hi]
        if not seg:
            continue
        print('[%d,%d)：' % (lo, hi))
        for p in sorted(set(r['p'] for r in seg)):
            mine = [r for r in seg if r['p'] == p]
            by = collections.defaultdict(list)
            for r in mine:
                by[r['cls']].append(r)
            parts = []
            for k in ('真人', '内置AI', '无主地', '回到自己地上', '移交队友', '沉没', '还在海上', '其他'):
                v = by.get(k)
                if not v:
                    continue
                g = [x['gain'] for x in v if x['gain'] is not None]
                parts.append('%s %d 条（载兵 %s，手续费 %s%s）' % (k, len(v), fmt(sum(x['troops'] for x in v)), fmt(sum(x['fee'] for x in v)),
                                                             '，单条登陆后 300 拍净得地 中位 %+d' % sorted(g)[len(g) // 2] if g else ''))
            print('  %-7s %d 条，载兵 %s，手续费 %s：%s' % (M.nm(p), len(mine), fmt(sum(r['troops'] for r in mine)), fmt(sum(r['fee'] for r in mine)), '；'.join(parts)))
            # 目标明细
            tg = collections.defaultdict(list)
            for r in mine:
                if r['tgt'] is not None and r['tgt'] < 512:
                    tg[r['tgt']].append(r)
            for q, v in sorted(tg.items(), key=lambda kv: -sum(x['troops'] for x in kv[1])):
                w0, w1 = min(x['te'] for x in v), max(x['te'] for x in v) + 300
                net = 0
                for (t, frm, to, px) in M.flow:
                    if w0 <= t <= w1:
                        if to == p and frm == q:
                            net += px
                        if frm == p and to == q:
                            net -= px
                print('    → %s：%d 条，载兵 %s，到岸 %s，手续费 %s；拍 %d~%d 从它净得地 %+d' % (
                    nm(q), len(v), fmt(sum(x['troops'] for x in v)), fmt(sum(x['arrived'] or 0 for x in v)), fmt(sum(x['fee'] for x in v)), w0, w1, net))
            pr = [(r, rows[r['pair'][1]]) for r in mine if r['pair'] and r['pair'][0] == 'first']
            if pr:
                sec_home = [(f, s) for f, s in pr if s['cls'] == '回到自己地上']
                print('    同落点船对 %d 对：第 2 条回到自己地上的 %d 对（第 2 条载兵合计 %s、手续费合计 %s、海上损耗 %s）；第 2 条载兵 / 第 1 条载兵 的中位 %.1f 倍' % (
                    len(pr), len(sec_home), fmt(sum(s['troops'] for f, s in sec_home)), fmt(sum(s['fee'] for f, s in sec_home)),
                    fmt(sum(s['troops'] - (s['arrived'] or 0) for f, s in sec_home)),
                    sorted(s['troops'] / max(1, f['troops']) for f, s in pr)[len(pr) // 2]))
                if show:
                    for f, s in pr:
                        print('      拍 %d 比例 %d 载 %s → 拍 %s %s%s；拍 %d 比例 %d 载 %s → 拍 %s %s' % (
                            f['t'], f['pct'], fmt(f['troops']), f['te'], f['cls'] + (' ' + nm(f['tgt']) if f['tgt'] is not None else ''),
                            (' 净得地 %+d' % f['gain']) if f['gain'] is not None else '',
                            s['t'], s['pct'], fmt(s['troops']), s['te'], s['cls'] + (' ' + nm(s['tgt']) if s['tgt'] is not None else '')))
            single_home = [r for r in mine if r['cls'] == '回到自己地上' and not r['pair']]
            if single_home:
                print('    不成对却回到自己地上的 %d 条：载兵 %s，手续费 %s' % (len(single_home), fmt(sum(r['troops'] for r in single_home)), fmt(sum(r['fee'] for r in single_home))))


if __name__ == '__main__':
    main()
