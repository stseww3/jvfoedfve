#!/usr/bin/env python3
# refund_strikes.py — 对真人的大笔出手里，有多少是「打完一小块就没地可打、兵退回」的空打（典型：对方坐船登在我岸上的滩头）。
# 用法：python3 scripts/refund_strikes.py <局号> [--ours id,id,…] [--frac 0.10] [--px 100] [--min 10000] [--list]
# 口径（只用 tmp/truth/<局号>/ 的 cmd.tsv / state.tsv / atk.tsv / meta.json）：
#   出手 = 同一个号对同一个真人目标的陆攻串（只算产生了进攻的指令；相邻两条落地拍相隔 ≤7 拍，和 human_strikes.py 同一个定义）；
#   大笔 = 整串出兵 ≥ 串首执行前余额的 frac（默认 10%）且 ≥ min（默认 1 万兵）；
#   空打 = 大笔出手，并且同时满足：
#     (1) 串尾之后 20~40 拍内 atk.tsv 里已经没有这个号打这个目标的在途兵（进攻已经结束）；
#     (2) 目标的领土（state.tsv，串尾之后 ≥30 拍的第一行）比串首之前最近一行少了不到 px 格（默认 100）；
#     (3) 不是对打：串首前 20 拍到串尾后 20 拍之间，目标打这个号的在途兵最多不到整串出兵的 25%
#         （对打时两边的兵互相抵消，兵是打光的，不是退回的）；
#     (4) 兵回来了：这个号在串尾之后 ≥30 拍的第一行余额，加上串尾到那一行之间它别的指令花掉的兵和手续费，
#         ≥ 串首执行前余额 − 整串出兵的 25%（这几十拍的利息也算在里面，所以 (4) 略偏宽）。
#   手续费 = 每条指令 bal0 − bal1 − 出兵。
# 输出：大笔出手的次数与兵、其中空打的次数 / 兵 / 手续费；--list 逐次列出空打。
import sys, os, csv, json, collections, bisect
sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def k(v):
    return '%.1f万' % (v / 1e4) if abs(v) >= 1e4 else str(int(v))


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__ or '用法：python3 scripts/refund_strikes.py <局号> [--ours id,…] [--frac 0.10] [--px 100] [--list]')
        sys.exit(2)
    mid = a[0]
    frac = float(a[a.index('--frac') + 1]) if '--frac' in a else 0.10
    pxmax = int(a[a.index('--px') + 1]) if '--px' in a else 100
    vmin = int(a[a.index('--min') + 1]) if '--min' in a else 10000
    tdir = os.path.join(ROOT, 'tmp', 'truth', mid)
    meta = json.load(open(os.path.join(tdir, 'meta.json'), encoding='utf8'))
    ku = meta['info']['ku']
    names = {p['p']: p['name'].replace('[APEX] ', '') for p in meta['players']}
    ours = {int(p): n.replace('[APEX] ', '') for p, n in meta['ours'].items()}
    if '--ours' in a:
        ours = {int(x): names.get(int(x), '#' + x) for x in a[a.index('--ours') + 1].split(',')}
    hist = collections.defaultdict(list)
    bals = collections.defaultdict(list)
    spend = collections.defaultdict(list)   # 号 -> (拍, 这条指令让余额少了多少)
    with open(os.path.join(tdir, 'state.tsv'), encoding='utf8') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            hist[int(r['p'])].append((int(r['t']), int(r['terr'])))
            bals[int(r['p'])].append((int(r['t']), int(r['bal'])))
    alive = collections.defaultdict(list)   # (attacker, target) -> 有在途兵的拍
    onway = collections.defaultdict(list)   # (attacker, target) -> (拍, 在途兵)
    with open(os.path.join(tdir, 'atk.tsv'), encoding='utf8') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            if int(r['troops']) > 0:
                alive[(int(r['attacker']), int(r['target']))].append(int(r['t']))
                onway[(int(r['attacker']), int(r['target']))].append((int(r['t']), int(r['troops'])))

    def terr_before(p, t):
        h = hist.get(p) or []
        i = bisect.bisect_left(h, (t, -1)) - 1
        return h[i][1] if i >= 0 else None

    def terr_after(p, t):
        h = hist.get(p) or []
        i = bisect.bisect_left(h, (t, -1))
        return h[i][1] if i < len(h) else None

    cmds = collections.defaultdict(list)
    with open(os.path.join(tdir, 'cmd.tsv'), encoding='utf8') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            if int(r['spawnStep']) >= 0 or int(r['p']) not in ours:
                continue
            if r['bal0'] and r['bal1']:
                spend[int(r['p'])].append((int(r['t']), int(r['bal0']) - int(r['bal1'])))
            if int(r['id']) != 1:
                continue
            sub = r['sub'] or ''
            if not sub.startswith('atk:'):
                continue
            tgt, troops = int(sub.split(':')[1]), int(sub.split(':')[2])
            if tgt >= ku or tgt == int(r['p']):
                continue
            bal0, bal1 = int(r['bal0']), int(r['bal1'])
            cmds[(int(r['p']), tgt)].append((int(r['t']), troops, bal0 - bal1 - troops, bal0))
    strikes = []
    for (p, tgt), lst in cmds.items():
        lst.sort(key=lambda x: x[0])
        cur = None
        for t, troops, fee, bal0 in lst:
            if cur and t - cur['t1'] <= 7:
                cur['t1'] = t; cur['troops'] += troops; cur['fee'] += fee; cur['n'] += 1
            else:
                cur = dict(p=p, tgt=tgt, t0=t, t1=t, troops=troops, fee=fee, n=1, bal0=bal0)
                strikes.append(cur)
    big = [s for s in strikes if s['troops'] >= max(vmin, frac * max(1, s['bal0']))]
    empty = []
    for s in big:
        ticks = alive.get((s['p'], s['tgt']), [])
        i = bisect.bisect_right(ticks, s['t1'] + 20)
        still = i < len(ticks) and ticks[i] <= s['t1'] + 40
        tb, ta = terr_before(s['tgt'], s['t0']), terr_after(s['tgt'], s['t1'] + 30)
        back = max([v for t, v in onway.get((s['tgt'], s['p']), []) if s['t0'] - 20 <= t <= s['t1'] + 20] or [0])
        if still or tb is None or ta is None:
            continue
        h = bals.get(s['p']) or []
        i = bisect.bisect_left(h, (s['t1'] + 30, -1))
        if i >= len(h):
            continue
        t_row, bal_row = h[i]
        other = sum(v for t, v in spend.get(s['p'], []) if s['t1'] < t <= t_row)
        if tb - ta < pxmax and back < 0.25 * s['troops'] and bal_row + other >= s['bal0'] - 0.25 * s['troops']:
            s['back'] = back
            s['tb'], s['ta'] = tb, ta
            empty.append(s)
    print('# %s 对真人的大笔出手（整串出兵 ≥ 余额的 %d%%）里的空打（进攻 40 拍内结束、目标领土少了不到 %d 格、不是对打、兵回到余额）' % (mid, round(100 * frac), pxmax))
    print('  对真人的出手 %d 次；大笔 %d 次 %s 兵；其中空打 %d 次 %s 兵，手续费 %s' % (
        len(strikes), len(big), k(sum(s['troops'] for s in big)), len(empty), k(sum(s['troops'] for s in empty)), k(sum(s['fee'] for s in empty))))
    by = collections.Counter()
    for s in empty:
        by[ours[s['p']]] += 1
    if by:
        print('  按号：' + '，'.join('%s %d 次' % (n, c) for n, c in by.most_common()))
    if '--list' in a:
        for s in sorted(empty, key=lambda s: s['t0']):
            print('    拍 %5d %s → %s：%d 条 %s 兵（余额的 %d%%），手续费 %s；目标领土 %d→%d；同期目标打过来的在途兵最多 %s' % (
                s['t0'], ours[s['p']], names.get(s['tgt'], '#%d' % s['tgt']), s['n'], k(s['troops']), round(100 * s['troops'] / max(1, s['bal0'])), k(s['fee']), s['tb'], s['ta'], k(s['back'])))


if __name__ == '__main__':
    main()
