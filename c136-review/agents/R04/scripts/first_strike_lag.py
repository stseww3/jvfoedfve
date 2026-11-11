#!/usr/bin/env python3
# first_strike_lag.py — 我方每个号对每个真人目标：影子策略第一次想打它是哪一拍、录像里第一条真的出了兵的陆攻是哪一拍，中间隔了多少拍、
# 这段时间影子重复下了多少条、想出的兵（第一条）和真出的兵（第一串）各是多少、这段时间目标的领土 / 余额怎么变了。
# 用法：python3 scripts/first_strike_lag.py <局号> [<局号> …] [--min 兵]     只列第一条想出 ≥ --min（默认 20000）兵的（号, 目标）对
# 数据：tmp/shadow/<局号>/intents.tsv、tmp/truth/<局号>/{cmd.tsv,state.tsv,meta.json}
# 口径：
#   想打 = intents.tsv 里 kind=attack、target 是真人（编号 < ku）的第一条；想出 = 那一条的 troops（按决策拍余额算）。
#   真打 = cmd.tsv 里这个号 id=1、sub 以 atk:<这个真人> 开头的第一条（落地并产生进攻）；第一串 = 之后相邻落地拍 ≤7 拍的同目标陆攻合计。
#   没有真打的对子记「没落地」。目标状态取 state.tsv（每 10 拍一行）里不晚于该拍的最近一行。
import sys, csv, json, os, bisect, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def k(v):
    return f'{v / 10000:.1f}万' if abs(v) >= 10000 else str(int(v))


def one(mid, vmin):
    tdir = os.path.join(ROOT, 'tmp', 'truth', mid)
    meta = json.load(open(os.path.join(tdir, 'meta.json'), encoding='utf8'))
    ku = meta['info']['ku']
    names = {p['p']: p['name'].replace('[APEX] ', '') for p in meta['players']}
    ours = {int(p): n for p, n in meta['ours'].items()}
    hist = collections.defaultdict(list)
    for r in csv.DictReader(open(os.path.join(tdir, 'state.tsv'), encoding='utf8'), delimiter='\t'):
        hist[int(r['p'])].append((int(r['t']), int(r['terr']), int(r['bal'])))

    def state_at(p, t):
        h = hist.get(p)
        if not h:
            return (0, 0)
        i = bisect.bisect_right(h, (t, 1 << 60, 1 << 60)) - 1
        return (h[i][1], h[i][2]) if i >= 0 else (0, 0)
    want = collections.defaultdict(list)
    for r in csv.DictReader(open(os.path.join(ROOT, 'tmp', 'shadow', mid, 'intents.tsv'), encoding='utf8'), delimiter='\t'):
        if r['kind'] != 'attack':
            continue
        tg = int(r['target'])
        if tg >= ku:
            continue
        want[(int(r['p']), tg)].append((int(r['t']), int(float(r['troops'] or 0)), int(r['pct'] or 0)))
    real = collections.defaultdict(list)
    for r in csv.DictReader(open(os.path.join(tdir, 'cmd.tsv'), encoding='utf8'), delimiter='\t'):
        if int(r['spawnStep']) >= 0 or int(r['id']) != 1 or int(r['p']) not in ours:
            continue
        s = r['sub'] or ''
        if not s.startswith('atk:'):
            continue
        tg = int(s.split(':')[1])
        if tg >= ku:
            continue
        real[(int(r['p']), tg)].append((int(r['t']), int(s.split(':')[2]), int(r['bal0'])))
    out = []
    lags = []
    for key, w in sorted(want.items(), key=lambda kv: kv[1][0][0]):
        p, tg = key
        t0, v0, pct0 = w[0]
        if v0 < vmin:
            continue
        rl = real.get(key)
        me0 = state_at(p, t0)
        q0 = state_at(tg, t0)
        if not rl:
            n = len(w)
            out.append(f'  {ours[p]:8s}→ {names.get(tg, tg)}：拍 {t0} 想打（比例 {pct0}/1024，想出 {k(v0)}；本号 {me0[0]} 格 / {k(me0[1])} 兵，它 {q0[0]} 格 / {k(q0[1])} 兵）→ 没落地（影子共下了 {n} 条，最后一条在拍 {w[-1][0]}）')
            continue
        t1 = rl[0][0]
        chain = [rl[0]]
        for x in rl[1:]:
            if x[0] - chain[-1][0] <= 7:
                chain.append(x)
            else:
                break
        tot = sum(x[1] for x in chain)
        n = sum(1 for x in w if x[0] < t1)
        q1 = state_at(tg, t1)
        me1 = state_at(p, t1)
        lags.append(t1 - t0)
        out.append(f'  {ours[p]:8s}→ {names.get(tg, tg)}：拍 {t0} 想打（比例 {pct0}/1024，想出 {k(v0)}；本号 {me0[0]} 格 / {k(me0[1])} 兵，它 {q0[0]} 格 / {k(q0[1])} 兵）'
                   f'→ 拍 {t1} 第一串落地（晚 {t1 - t0} 拍；{len(chain)} 条 真出 {k(tot)} = 落地前余额 {k(chain[0][2])} 的 {tot * 100 // max(1, chain[0][2])}%；'
                   f'这段时间影子下了 {n} 条；落地时本号 {me1[0]} 格 / {k(me1[1])} 兵，它 {q1[0]} 格 / {k(q1[1])} 兵）')
    print(f'# {mid} 对真人的第一次出手：影子想打的拍 → 录像里第一串落地的拍（只列第一条想出 ≥ {k(vmin)} 兵的对子）')
    for line in out:
        print(line)
    if lags:
        lags.sort()
        print(f'合计：{len(out)} 对，其中落地 {len(lags)} 对；晚的拍数 最小 {lags[0]}、中位 {lags[len(lags) // 2]}、最大 {lags[-1]}')
    else:
        print(f'合计：{len(out)} 对，落地 0 对')


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        sys.exit(1)
    vmin = 20000
    mids = []
    i = 0
    while i < len(a):
        if a[i] == '--min':
            vmin = int(a[i + 1])
            i += 2
        else:
            mids.append(a[i])
            i += 1
    for mid in mids:
        one(mid, vmin)


main()
