#!/usr/bin/env python3
# reissue_runs.py — 「同一条打内置 AI 的单子每个决策拍重下一遍」的连下串，以及串里身边有没有真人。
# 用法：python3 scripts/reissue_runs.py <局号> [--t0 1500] [--t1 3000] [--min 6] [--list N]
# 数据：tmp/shadow/<局号>/{intents.tsv,rows.tsv}（影子策略逐拍复现的意图和状态）、tmp/truth/<局号>/{cmd.tsv,meta.json}（真引擎重放）
# 定义：
#   连下串 = 同一个号对同一个内置 AI 的陆攻意图，相邻两条相隔 ≤10 拍（策略每 5 拍决策一次），条数 ≥ --min。
#   每串记：起止拍、条数、每条想出的兵的范围、串开始和结束时这个号的 领土 / 余额、
#           串里这个号身边有真人邻居（rows.tsv 的 nHum ≥ 1）的决策拍数、串里对真人的意图条数、
#           [串开始, 串结束+60] 里录像中真的落在这个 AI 身上的陆攻条数和兵（cmd.tsv 的 sub = atk:<这个 AI>:<兵>）。
#   「空转串」= 串里一条都没落在这个 AI 身上。
# 口径：只数影子策略的意图；一个决策拍里同一个号有多条意图时，按「这一拍有没有对这个 AI 的意图」算。
# 输出：按号小结（串数、合计拍数、空转串数、身边有真人的拍数），以及全部号合计；--list 列最长的 N 串。
import sys, os, csv, json, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def k(v):
    return f'{v / 10000:.1f}万' if abs(v) >= 10000 else str(int(v))


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        sys.exit(1)
    mid = a[0]
    t0 = int(a[a.index('--t0') + 1]) if '--t0' in a else 1500
    t1 = int(a[a.index('--t1') + 1]) if '--t1' in a else 3000
    nmin = int(a[a.index('--min') + 1]) if '--min' in a else 6
    nlist = int(a[a.index('--list') + 1]) if '--list' in a else 0
    tdir = os.path.join(ROOT, 'tmp', 'truth', mid)
    sdir = os.path.join(ROOT, 'tmp', 'shadow', mid)
    meta = json.load(open(os.path.join(tdir, 'meta.json'), encoding='utf8'))
    ours = {int(p): n.replace('[APEX] ', '') for p, n in meta['ours'].items()}
    ku = meta['info']['ku']
    rows = {}
    for r in csv.DictReader(open(os.path.join(sdir, 'rows.tsv'), encoding='utf8'), delimiter='\t'):
        rows[(r['bot'], int(r['t']))] = (int(r['terr']), int(r['bal']), int(r['nHum'] or 0))
    byb = collections.defaultdict(lambda: collections.defaultdict(list))
    hum = collections.defaultdict(set)
    for r in csv.DictReader(open(os.path.join(sdir, 'intents.tsv'), encoding='utf8'), delimiter='\t'):
        if r['kind'] != 'attack':
            continue
        t = int(r['t'])
        q = int(r['target'])
        if q < ku:
            hum[r['bot']].add(t)
        if ku <= q < 512 and t0 <= t < t1:
            byb[r['bot']][q].append((t, int(float(r['troops']))))
    land = collections.defaultdict(list)
    for r in csv.DictReader(open(os.path.join(tdir, 'cmd.tsv'), encoding='utf8'), delimiter='\t'):
        if int(r['spawnStep']) >= 0 or int(r['id']) != 1 or int(r['p']) not in ours:
            continue
        s = r['sub'] or ''
        if s.startswith('atk:'):
            _, q, v = s.split(':')[:3]
            land[(ours[int(r['p'])], int(q))].append((int(r['t']), int(v)))
    runs = []
    for bot, d in byb.items():
        for q, lst in d.items():
            lst.sort()
            cur = [lst[0]]
            for x in lst[1:]:
                if x[0] - cur[-1][0] <= 10:
                    cur.append(x)
                else:
                    runs.append((bot, q, cur))
                    cur = [x]
            runs.append((bot, q, cur))
    out = []
    for bot, q, cur in runs:
        ts = sorted(set(t for t, _ in cur))
        if len(ts) < nmin:
            continue
        a0, a1 = ts[0], ts[-1]
        ld = [(t, v) for t, v in land.get((bot, q), []) if a0 <= t <= a1 + 60]
        nh = sum(1 for t in ts if rows.get((bot, t), (0, 0, 0))[2] >= 1)
        hi = sum(1 for t in hum[bot] if a0 <= t <= a1)
        r0 = rows.get((bot, a0), (0, 0, 0))
        r1 = rows.get((bot, a1), (0, 0, 0))
        tr = [v for _, v in cur]
        out.append(dict(bot=bot, q=q, a0=a0, a1=a1, n=len(ts), lo=min(tr), hi=max(tr), terr0=r0[0], bal0=r0[1], terr1=r1[0], bal1=r1[1], nh=nh, humInt=hi, landed=len(ld), landedTroops=sum(v for _, v in ld)))
    print(f'# {mid} 拍 [{t0},{t1}) 对同一个内置 AI 连下 ≥{nmin} 个决策拍的串（影子意图；相邻 ≤10 拍）')
    tot = collections.Counter()
    for bot in sorted(set(o['bot'] for o in out)):
        oo = [o for o in out if o['bot'] == bot]
        dry = [o for o in oo if o['landed'] == 0]
        span = sum(o['a1'] - o['a0'] + 5 for o in oo)
        nh = sum(o['nh'] for o in oo)
        n = sum(o['n'] for o in oo)
        print(f'  {bot:7s} {len(oo)} 串 {n} 个决策拍（合计 {span} 拍）；空转串 {len(dry)} 个 {sum(o["n"] for o in dry)} 个决策拍；身边有真人邻居的决策拍 {nh} 个；这些串里对真人的意图 {sum(o["humInt"] for o in oo)} 条；落在这些 AI 身上的陆攻 {sum(o["landed"] for o in oo)} 条 {k(sum(o["landedTroops"] for o in oo))} 兵')
        tot['runs'] += len(oo)
        tot['n'] += n
        tot['span'] += span
        tot['dry'] += len(dry)
        tot['dryn'] += sum(o['n'] for o in dry)
        tot['nh'] += nh
        tot['landed'] += sum(o['landed'] for o in oo)
        tot['lt'] += sum(o['landedTroops'] for o in oo)
    print(f'合计：{tot["runs"]} 串 {tot["n"]} 个决策拍（{tot["span"]} 号·拍）；空转串 {tot["dry"]} 个 {tot["dryn"]} 个决策拍；身边有真人邻居的决策拍 {tot["nh"]} 个（{tot["nh"] * 100 // max(1, tot["n"])}%）；落在这些 AI 身上的陆攻 {tot["landed"]} 条 {k(tot["lt"])} 兵')
    if nlist:
        for o in sorted(out, key=lambda o: -(o['a1'] - o['a0']))[:nlist]:
            print(f'    {o["bot"]:7s} → AI#{o["q"]} 拍 {o["a0"]}~{o["a1"]}：{o["n"]} 个决策拍，每条想出 {k(o["lo"])}~{k(o["hi"])} 兵；领土 {o["terr0"]} → {o["terr1"]}，余额 {k(o["bal0"])} → {k(o["bal1"])}；身边有真人的决策拍 {o["nh"]} 个，串里对真人的意图 {o["humInt"]} 条；落在它身上的陆攻 {o["landed"]} 条 {k(o["landedTroops"])} 兵')


main()
