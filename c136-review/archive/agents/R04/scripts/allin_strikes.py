#!/usr/bin/env python3
# allin_strikes.py — 我方对真人「一把全压」的出手：一个出兵串把执行前余额的 ≥60% 送出去，目标却没有出局，之后这个号怎么样了。
# 用法：python3 scripts/allin_strikes.py <局号>… [--ours id,id,…] [--share 0.6] [--list]
# 口径（只用 tmp/truth/<局号>/ 的 cmd.tsv / state.tsv / flow.tsv / meta.json）：
#   出兵串 = 同一个号对同一个真人目标的陆攻，相邻两条落地拍相隔 ≤7 拍（和 human_strikes.py 同一个定义）；
#   全压 = 整串出兵 ≥ 串首那条执行前余额的 share（默认 60%）；
#   吃不死 = 串首落地后 300 拍内目标没有出局（state.tsv 的 alive）；
#   之后：串尾执行后的密度（余额 / 领土）、此后 300 拍里每 10 拍一行的密度最小值、密度 <5 持续了多少拍、
#         串首落地后 300 / 450 拍从目标净拿的地、450 拍内被所有真人拿走的地、450 拍时本号的地比出手前多还是少、是否出局。
#   记作 NEW-AT-PARTALLIN 的条件：全压 + 吃不死 +（450 拍时本号的地 < 出手前的地，或 450 拍内出局）。
# 输出：每局的全压次数、其中吃不死的、其中记作 NEW-AT-PARTALLIN 的；--list 逐次列出。
import sys, os, csv, json, collections, bisect
sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def k(v):
    return '%.1f万' % (v / 1e4) if abs(v) >= 1e4 else str(int(v))


def one(mid, a):
    share_min = float(a[a.index('--share') + 1]) if '--share' in a else 0.6
    tdir = os.path.join(ROOT, 'tmp', 'truth', mid)
    meta = json.load(open(os.path.join(tdir, 'meta.json'), encoding='utf8'))
    ku = meta['info']['ku']
    names = {p['p']: p['name'].replace('[APEX] ', '') for p in meta['players']}
    ours = {int(p): n.replace('[APEX] ', '') for p, n in meta['ours'].items()}
    if '--ours' in a:
        ours = {int(x): names.get(int(x), '#' + x) for x in a[a.index('--ours') + 1].split(',')}
    hist = collections.defaultdict(list)
    with open(os.path.join(tdir, 'state.tsv'), encoding='utf8') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            p = int(r['p'])
            if p < ku:
                hist[p].append((int(r['t']), int(r['terr']), int(r['bal']), int(r['alive'])))

    def at(p, t):
        h = hist.get(p)
        if not h:
            return None
        i = bisect.bisect_right(h, (t, 1 << 60, 1 << 60, 9)) - 1
        return h[max(i, 0)]

    def span(p, t0, t1):
        return [x for x in hist.get(p, []) if t0 < x[0] <= t1]
    rows = []
    with open(os.path.join(tdir, 'cmd.tsv'), encoding='utf8') as f:
        for i, r in enumerate(csv.DictReader(f, delimiter='\t')):
            if int(r['spawnStep']) >= 0 or int(r['id']) != 1 or int(r['p']) not in ours:
                continue
            b = int(r['b'])
            s = r['sub'] or ''
            if b >= ku or not s.startswith('atk:'):
                continue
            rows.append(dict(i=i, t=int(r['t']), p=int(r['p']), q=b, bal0=int(r['bal0']), bal1=int(r['bal1']),
                             terr0=int(r['terr0']), v=int(s.split(':')[2])))
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

    def net(p, q, t0, t1):
        return sum(px for (t, px) in flow.get((q, p), []) if t0 <= t <= t1) - sum(px for (t, px) in flow.get((p, q), []) if t0 <= t <= t1)
    out = []
    n_all = 0
    for c in chains:
        h = c['rows'][0]; last = c['rows'][-1]
        n_all += 1
        v = sum(r['v'] for r in c['rows'])
        sh = v / max(1, h['bal0'])
        if sh < share_min:
            continue
        t0 = h['t']
        sq = at(c['q'], t0)
        q300 = at(c['q'], t0 + 300)
        killed = (q300 is None) or (q300[3] == 0) or q300[1] == 0
        me = span(c['p'], last['t'], last['t'] + 300)
        dens = [x[2] / max(1, x[1]) for x in me if x[1] > 0]
        thin = 10 * sum(1 for d in dens if d < 5)
        m450 = at(c['p'], t0 + 450)
        dead450 = m450 is None or m450[3] == 0 or m450[1] == 0
        lost_h = sum(sum(px for (t, px) in flow.get((c['p'], e), []) if t0 < t <= t0 + 450) for e in range(ku) if e not in ours)
        o = dict(mid=mid, t=t0, p=c['p'], q=c['q'], n=len(c['rows']), v=v, share=sh, b0=h['bal0'], t0terr=h['terr0'],
                 qb=sq[2] if sq else 0, qt=sq[1] if sq else 0, d_after=last['bal1'] / max(1, last['terr0']),
                 d_min=min(dens) if dens else 0.0, thin=thin, g300=net(c['p'], c['q'], t0, t0 + 300), g450=net(c['p'], c['q'], t0, t0 + 450),
                 lost=lost_h, terr450=0 if dead450 else m450[1], dead=dead450, killed=killed)
        o['hit'] = (not killed) and (dead450 or o['terr450'] < o['t0terr'])
        out.append(o)
    alive = [o for o in out if not o['killed']]
    hit = [o for o in out if o['hit']]
    print('%s：我方对真人的出兵串 %d 个；全压（≥%d%% 余额）%d 个 %s 兵；其中目标 300 拍内没出局 %d 个 %s 兵；其中 450 拍后本号的地比出手前少或已出局（NEW-AT-PARTALLIN）%d 个 %s 兵' % (
        mid, n_all, round(100 * share_min), len(out), k(sum(o['v'] for o in out)), len(alive), k(sum(o['v'] for o in alive)),
        len(hit), k(sum(o['v'] for o in hit))))
    if '--list' in a:
        for o in sorted(out, key=lambda o: o['t']):
            print('    拍 %5d %-7s → %s：%d 条 %s 兵（余额 %s 的 %.0f%%）；本号 %d 格，对方 %d 格 / %s 兵；打完密度 %.2f，此后 300 拍最低 %.2f、密度 <5 共 %d 拍；从它净拿 300 拍 %+d / 450 拍 %+d；450 拍内被真人拿走 %d 格；450 拍时 %s%s%s' % (
                o['t'], ours[o['p']], names.get(o['q'], '#%d' % o['q']), o['n'], k(o['v']), k(o['b0']), 100 * o['share'], o['t0terr'], o['qt'], k(o['qb']),
                o['d_after'], o['d_min'], o['thin'], o['g300'], o['g450'], o['lost'],
                '已出局' if o['dead'] else '%d 格（%+d）' % (o['terr450'], o['terr450'] - o['t0terr']),
                '；目标 300 拍内出局' if o['killed'] else '', '  ← PARTALLIN' if o['hit'] else ''))
    return dict(mid=mid, chains=n_all, allin=len(out), alive=len(alive), hit=len(hit), hitTroops=sum(o['v'] for o in hit), rows=out)


def main():
    a = sys.argv[1:]
    mids = [x for x in a if not x.startswith('--') and (x[0] in 'AB' and x[1:].isdigit())]
    res = [one(m, a) for m in mids]
    os.makedirs(os.path.join(ROOT, 'tmp', 'allin'), exist_ok=True)
    for r in res:
        json.dump(r, open(os.path.join(ROOT, 'tmp', 'allin', r['mid'] + '.json'), 'w', encoding='utf8'), ensure_ascii=False)
    if len(res) > 1:
        print('合计 %d 局：出兵串 %d 个，全压 %d 个，目标没出局 %d 个，NEW-AT-PARTALLIN %d 个 %s 兵' % (
            len(res), sum(r['chains'] for r in res), sum(r['allin'] for r in res), sum(r['alive'] for r in res),
            sum(r['hit'] for r in res), k(sum(r['hitTroops'] for r in res))))


if __name__ == '__main__':
    main()
