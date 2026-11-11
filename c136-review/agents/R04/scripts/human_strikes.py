#!/usr/bin/env python3
# human_strikes.py — 我方每次对真人出手（一个出兵串算一次）时，双方的密度比是多少、是不是「余额超过软上限才打」、打完换回多少地。
# 用法：python3 scripts/human_strikes.py <局号> [--ours id,id,…] [--min 兵] [--list N] [--from 拍]
# 口径（只用 tmp/truth/<局号>/ 的 cmd.tsv / state.tsv / flow.tsv / meta.json）：
#   出手 = 同一个号对同一个真人目标的陆攻串（相邻两条落地拍相隔 ≤7 拍，和 blind_reorders.py 的出兵串同一个定义）；
#   密度 = 余额 / 领土：我方取串首那条指令执行前的值（cmd.tsv 的 bal0/terr0），目标取 state.tsv 里执行拍之前最近一行（每 10 拍一行）；
#   密度比 = 我方密度 / 目标密度；超软上限 = 串首执行前余额 > 100×领土（策略 buyLand 里的 over）；
#   净得地 = 串首落地起 300 拍内，从这个目标净流入的像素（flow.tsv；同期别的出手拿的地也在内，所以相邻的出手会重复计）。
# 输出：按「不超软上限 / 超软上限」分两组，各组的出手次数、密度比的分位数、出兵合计、净得地为正的次数；--list 列出兵最多的 N 次。
import sys, os, csv, json, collections, bisect
sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def k(v):
    return '%.1f万' % (v / 1e4) if abs(v) >= 1e4 else str(int(v))


def q(v, f):
    v = sorted(v)
    return v[min(len(v) - 1, int(f * len(v)))] if v else float('nan')


def main():
    a = sys.argv[1:]
    mid = a[0]
    nlist = int(a[a.index('--list') + 1]) if '--list' in a else 0
    vmin = int(a[a.index('--min') + 1]) if '--min' in a else 0
    t_from = int(a[a.index('--from') + 1]) if '--from' in a else 0
    tdir = os.path.join(ROOT, 'tmp', 'truth', mid)
    meta = json.load(open(os.path.join(tdir, 'meta.json'), encoding='utf8'))
    ku = meta['info']['ku']
    names = {p['p']: p['name'].replace('[APEX] ', '') for p in meta['players']}
    ours = {int(p): n.replace('[APEX] ', '') for p, n in meta['ours'].items()}
    if '--ours' in a:
        ours = {int(x): names.get(int(x), '#' + x) for x in a[a.index('--ours') + 1].split(',')}
    # 目标的领土/余额：state.tsv 每 10 拍一行，取指令执行拍之前最近的一行
    hist = collections.defaultdict(list)
    with open(os.path.join(tdir, 'state.tsv'), encoding='utf8') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            hist[int(r['p'])].append((int(r['t']), int(r['terr']), int(r['bal'])))

    def state_at(p, t):
        h = hist.get(p)
        if not h:
            return None
        i = bisect.bisect_right(h, (t, 1 << 60, 1 << 60)) - 1
        if i < 0:
            return None
        return h[i][1], h[i][2]
    rows = []
    with open(os.path.join(tdir, 'cmd.tsv'), encoding='utf8') as f:
        for i, r in enumerate(csv.DictReader(f, delimiter='\t')):
            if int(r['spawnStep']) >= 0 or int(r['id']) != 1 or int(r['p']) not in ours:
                continue
            b = int(r['b'])
            if b >= ku:
                continue
            s = r['sub'] or ''
            if not s.startswith('atk:'):
                continue
            st = state_at(b, int(r['t']))
            if st is None:
                continue
            rows.append(dict(i=i, t=int(r['t']), p=int(r['p']), q=b, bal0=int(r['bal0']), terr0=int(r['terr0']),
                             balQ=st[1], terrQ=st[0], v=int(s.split(':')[2])))
    by = collections.defaultdict(list)
    for r in rows:
        by[(r['p'], r['q'])].append(r)
    chains = []
    for key, v in by.items():
        v.sort(key=lambda r: (r['t'], r['i']))
        cur = None
        for r in v:
            if cur is not None and r['t'] - cur['last'] <= 7:
                cur['rows'].append(r); cur['last'] = r['t']
            else:
                cur = dict(p=key[0], q=key[1], rows=[r], last=r['t']); chains.append(cur)
    flow = collections.defaultdict(list)
    with open(os.path.join(tdir, 'flow.tsv'), encoding='utf8') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            fr, to = int(r['from']), int(r['to'])
            if fr in ours or to in ours:
                flow[(fr, to)].append((int(r['t']), int(r['px'])))
    out = []
    for c in chains:
        h = c['rows'][0]
        v = sum(r['v'] for r in c['rows'])
        if v < vmin or h['t'] < t_from:
            continue
        dme = h['bal0'] / max(1, h['terr0']); dq = h['balQ'] / max(1, h['terrQ'])
        gain = sum(px for (t, px) in flow.get((c['q'], c['p']), []) if h['t'] <= t <= h['t'] + 300) - \
            sum(px for (t, px) in flow.get((c['p'], c['q']), []) if h['t'] <= t <= h['t'] + 300)
        out.append(dict(t=h['t'], p=c['p'], q=c['q'], n=len(c['rows']), v=v, share=v / max(1, h['bal0']), dme=dme, dq=dq,
                        ratio=dme / max(0.01, dq), over=h['bal0'] > 100 * h['terr0'], gain=gain, bq=h['balQ'], tq=h['terrQ'], b0=h['bal0'], t0=h['terr0']))
    print('%s：我方对真人的出手 %d 次（出兵合计 %s）%s' % (mid, len(out), k(sum(o['v'] for o in out)),
                                              ('；只算出兵 ≥ %s 的' % k(vmin)) if vmin else ''))
    for lab, grp in (('余额不超过 100×领土', [o for o in out if not o['over']]), ('余额超过 100×领土（over）', [o for o in out if o['over']])):
        if not grp:
            print('  %s：0 次' % lab)
            continue
        rs = [o['ratio'] for o in grp]
        print('  %s：%d 次，出兵 %s；密度比（我/它）25%% 位 %.2f、中位 %.2f、75%% 位 %.2f；密度比 <1.5 的 %d 次、<1 的 %d 次；净得地 >0 的 %d 次，净得地合计 %+d' % (
            lab, len(grp), k(sum(o['v'] for o in grp)), q(rs, 0.25), q(rs, 0.5), q(rs, 0.75),
            sum(1 for r in rs if r < 1.5), sum(1 for r in rs if r < 1.0), sum(1 for o in grp if o['gain'] > 0), sum(o['gain'] for o in grp)))
    per = collections.defaultdict(list)
    for o in out:
        per[o['p']].append(o)
    for p, grp in sorted(per.items(), key=lambda kv: -sum(o['v'] for o in kv[1])):
        a0 = [o for o in grp if not o['over']]; a1 = [o for o in grp if o['over']]
        print('    %-7s %d 次 %s 兵；密度比中位 %.2f；不超软上限 %d 次 %s 兵 净得地 %+d；over %d 次 %s 兵 净得地 %+d' % (
            ours[p], len(grp), k(sum(o['v'] for o in grp)), q([o['ratio'] for o in grp], 0.5),
            len(a0), k(sum(o['v'] for o in a0)), sum(o['gain'] for o in a0), len(a1), k(sum(o['v'] for o in a1)), sum(o['gain'] for o in a1)))
    for o in sorted(out, key=lambda o: -o['v'])[:nlist]:
        print('    拍 %5d %-7s → %s：%d 条 %s 兵（余额的 %.0f%%）；我 %d 格 / 密度 %.1f%s，它 %d 格 / 密度 %.1f，密度比 %.2f；300 拍净得地 %+d' % (
            o['t'], ours[o['p']], names.get(o['q'], '#%d' % o['q']), o['n'], k(o['v']), 100 * o['share'], o['t0'], o['dme'], '（over）' if o['over'] else '',
            o['tq'], o['dq'], o['ratio'], o['gain']))


if __name__ == '__main__':
    main()
