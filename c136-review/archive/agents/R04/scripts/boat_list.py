#!/usr/bin/env python3
# 我方每条船的清单：发船拍、载兵、发船手续费、结果（登陆打谁 / 移交队友 / 回自己地作废 / 沉没）、登陆后 300 拍从目标净得地。
# 用法：python3 scripts/boat_list.py <局号> [t0 t1] [--bot 名字[,名字…]] [--ours id,id,…] [--all]
# 口径：
#   载兵 = cmd.tsv 发船指令在引擎里登记的兵（sub 字段 boat:<船号>:<兵>:<终点>）；
#   手续费 = 发船那一拍余额减少量 − 载兵（引擎按余额的 32/1024 收，见规格书 B 海战一节）；
#   结果取 ev.tsv 里同一船号的 land / sunk / boatend 事件；到岸兵 = 登陆时船上剩的兵（船在海上按航程掉兵）；
#   「登陆后净得地」= 登陆拍起 300 拍内 flow.tsv 里该号从登陆目标净流入的像素（目标是无主地时不算）。
# 默认只逐条列载兵 ≥ 发船时余额 5% 或手续费 > 载兵的船；加 --all 全列。
import sys, os, collections
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from match_digest import Match, fmt


def main():
    a = sys.argv[1:]
    mid = a[0]
    ours = [int(x) for x in a[a.index('--ours') + 1].split(',')] if '--ours' in a else None
    M = Match(mid, ours)
    nums = [int(x) for x in a[1:3] if x.lstrip('-').isdigit()]
    t0, t1 = (nums + [0, 10 ** 9])[:2] if len(nums) >= 2 else (0, 10 ** 9)
    only = a[a.index('--bot') + 1].split(',') if '--bot' in a else None
    show_all = '--all' in a

    def nm(p):
        return '无主地' if p >= 512 or p < 0 else M.nm(p)
    ends = {}
    for (t, kind, pl, x, y, det) in M.ev:
        if kind in ('land', 'sunk', 'boatend') and pl in M.ours:
            ends.setdefault((pl, int(x)), (t, kind, y, det))
    rows = []
    for c in M.cmd:
        if c['id'] != 3 or c['p'] not in M.ours or not (t0 <= c['t'] <= t1):
            continue
        if only and M.nm(c['p']) not in only:
            continue
        for s in c['sub']:
            if not s or s[0] != 'boat':
                continue
            bid, troops = int(s[1]), int(s[2])
            fee = max(0, c['bal0'] - c['bal1'] - troops)
            e = ends.get((c['p'], bid))
            res, tgt, gain, te, arrived = '还在海上/无记录', None, None, None, None
            if e:
                te, kind, y, det = e
                tail = det.split('|', 1)[1] if '|' in det else ''
                if kind == 'sunk':
                    res = '沉没'; arrived = 0
                elif kind == 'boatend':
                    res = '船消失'
                elif tail.startswith('atk:'):
                    f = tail.split(':')
                    tgt = int(f[1]); arrived = int(f[2]); res = '登陆打 %s %s 兵' % (nm(tgt), fmt(int(f[2])))
                    if tgt < 512:
                        gain = 0
                        for (t, frm, to, px) in M.flow:
                            if te <= t <= te + 300:
                                if to == c['p'] and frm == tgt:
                                    gain += px
                                if frm == c['p'] and to == tgt:
                                    gain -= px
                elif tail.startswith('give:'):
                    f = tail.split(':')
                    arrived = int(f[2]); res = '移交队友 %s，到岸 %s 到账 %s' % (nm(int(f[1])), fmt(int(f[2])), fmt(int(f[3])))
                else:
                    try:
                        arrived = max(0, int(tail.split(':')[1]))
                    except (IndexError, ValueError):
                        arrived = None
                    res = '回到自己地上作废（%s）' % tail
            rows.append(dict(t=c['t'], p=c['p'], pct=c['a'], bal0=c['bal0'], terr=c['terr0'], troops=troops, fee=fee, te=te, res=res, tgt=tgt, gain=gain, arrived=arrived))
    tot = collections.Counter(); cnt = collections.Counter()
    feeby = collections.Counter(); arrby = collections.Counter()
    tiny_n = tiny_fee = tiny_troops = 0
    for r in rows:
        k = '登陆打敌方/AI' if r['res'].startswith('登陆打') and r['tgt'] is not None and r['tgt'] < 512 else \
            '登陆无主地' if r['res'].startswith('登陆打') else r['res'].split(' ')[0].split('（')[0]
        cnt[k] += 1; tot[k] += r['troops']
        feeby[k] += r['fee']; arrby[k] += (r['arrived'] or 0)
        tiny = r['fee'] > r['troops']
        if tiny:
            tiny_n += 1; tiny_fee += r['fee']; tiny_troops += r['troops']
        big = r['troops'] >= 0.05 * max(1, r['bal0'])
        if show_all or big or tiny:
            print('拍 %5d %-7s 比例 %4d/1024 余额 %s（密度 %.0f） 载 %s 兵，手续费 %s%s → %s%s%s' % (
                r['t'], M.nm(r['p']), r['pct'], fmt(r['bal0']), r['bal0'] / max(1, r['terr']), fmt(r['troops']), fmt(r['fee']),
                '（手续费比载兵多）' if tiny else '',
                ('拍 %d ' % r['te']) if r['te'] is not None else '', r['res'],
                ('，300 拍内从它净得地 %+d' % r['gain']) if r['gain'] is not None else ''))
    n = len(rows)
    print('合计 %d 条船，载兵 %s，手续费 %s。结果：%s' % (
        n, fmt(sum(r['troops'] for r in rows)), fmt(sum(r['fee'] for r in rows)),
        '；'.join('%s %d 条 %s 兵' % (k, v, fmt(tot[k])) for k, v in cnt.most_common())))
    print('按结果分的手续费和到岸兵：%s' % '；'.join('%s 手续费 %s、到岸 %s' % (k, fmt(feeby[k]), fmt(arrby[k])) for k, v in cnt.most_common()))
    byp = collections.defaultdict(lambda: [0, 0, 0])
    for r in rows:
        byp[M.nm(r['p'])][0] += 1; byp[M.nm(r['p'])][1] += r['troops']; byp[M.nm(r['p'])][2] += r['fee']
    print('按号（条数 / 载兵 / 手续费）：%s' % '；'.join('%s %d 条 / %s / %s' % (k, v[0], fmt(v[1]), fmt(v[2])) for k, v in sorted(byp.items(), key=lambda kv: -kv[1][1])))
    print('手续费比载兵多的船：%d 条，载兵合计 %s，手续费合计 %s' % (tiny_n, fmt(tiny_troops), fmt(tiny_fee)))
    done = [r for r in rows if r['arrived'] is not None]
    if done:
        ld = sum(r['troops'] for r in done); ar = sum(r['arrived'] for r in done)
        print('有结果的 %d 条船：载兵 %s，到岸 %s，海上损耗 %s（%.0f%%）；航行拍数中位 %d、最长 %d' % (
            len(done), fmt(ld), fmt(ar), fmt(ld - ar), 100.0 * (ld - ar) / max(1, ld),
            sorted(r['te'] - r['t'] for r in done)[len(done) // 2], max(r['te'] - r['t'] for r in done)))
    hum = [r for r in rows if r['gain'] is not None]
    if hum:
        # 同一个号对同一目标的多条船，300 拍窗口可能重叠：合计时把窗口并起来，每格地只算一次
        wins = collections.defaultdict(list)
        for r in hum:
            wins[(r['p'], r['tgt'])].append((r['te'], r['te'] + 300))
        total = 0
        for (p, tgt), ws in wins.items():
            ws.sort(); merged = []
            for w in ws:
                if merged and w[0] <= merged[-1][1]:
                    merged[-1] = (merged[-1][0], max(merged[-1][1], w[1]))
                else:
                    merged.append(w)
            for (t, frm, to, px) in M.flow:
                if any(w0 <= t <= w1 for (w0, w1) in merged):
                    if to == p and frm == tgt:
                        total += px
                    if frm == p and to == tgt:
                        total -= px
        print('登陆打敌方/AI 的 %d 条：载兵 %s，到岸 %s；登陆后 300 拍从目标净得地合计 %+d（重叠窗口只算一次；同期的陆攻得地也在内）；单条净得地 ≤100 的 %d 条 %s 兵' % (
            len(hum), fmt(sum(r['troops'] for r in hum)), fmt(sum(r['arrived'] or 0 for r in hum)), total,
            sum(1 for r in hum if r['gain'] <= 100), fmt(sum(r['troops'] for r in hum if r['gain'] <= 100))))

if __name__ == '__main__':
    main()
