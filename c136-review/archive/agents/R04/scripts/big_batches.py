#!/usr/bin/env python3
# big_batches.py — 同一个号同一拍落地 ≥N 条陆攻的批，逐批列出：条数、比例范围、批前批后余额、实际出兵、手续费、没产生进攻的条数、落地时的实际目标。
# 用法：python3 scripts/big_batches.py <局号> [--t0 1500] [--t1 2400] [--min 5]
# 数据：tmp/truth/<局号>/{cmd.tsv,meta.json}（真引擎重放；sub = atk:<实际目标>:<出征兵>，空 = 这条指令没有产生进攻、不扣兵也不收手续费）
# 口径：手续费 = bal0 − bal1 − 出征兵（引擎按执行那一刻余额的 12/1024 收）；目标按落地时引擎规整之后的记（目标已出局 → 无主地）。
# 末尾三行小结：一兵没出的批、落在无主地 / 内置 AI 上的批、落在真人身上的批，各自的批数、条数、出兵、手续费。
import sys, csv, json, os, collections

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
    t1 = int(a[a.index('--t1') + 1]) if '--t1' in a else 2400
    nmin = int(a[a.index('--min') + 1]) if '--min' in a else 5
    tdir = os.path.join(ROOT, 'tmp', 'truth', mid)
    meta = json.load(open(os.path.join(tdir, 'meta.json'), encoding='utf8'))
    ours = {int(p): n.replace('[APEX] ', '') for p, n in meta['ours'].items()}
    ku = meta['info']['ku']
    names = {p['p']: p['name'].replace('[APEX] ', '') for p in meta['players']}
    g = collections.OrderedDict()
    for r in csv.DictReader(open(os.path.join(tdir, 'cmd.tsv'), encoding='utf8'), delimiter='\t'):
        if int(r['spawnStep']) >= 0 or int(r['id']) != 1 or int(r['p']) not in ours:
            continue
        t = int(r['t'])
        if t0 <= t <= t1:
            g.setdefault((t, int(r['p'])), []).append(r)
    summ = {'一兵没出': [0, 0, 0, 0], '落在无主地 / 内置 AI 上': [0, 0, 0, 0], '落在真人身上': [0, 0, 0, 0]}
    print(f'# {mid} 拍 {t0}~{t1} 同号同拍落地 ≥{nmin} 条陆攻的批')
    for (t, p), rs in g.items():
        if len(rs) < nmin:
            continue
        sent = fee = noatk = 0
        tg = collections.Counter()
        human = False
        for r in rs:
            s = r['sub'] or ''
            if s.startswith('atk:'):
                _, q, v = s.split(':')[:3]
                q = int(q)
                v = int(v)
                sent += v
                fee += int(r['bal0']) - int(r['bal1']) - v
                if q >= 512:
                    tg['无主地'] += 1
                elif q < ku:
                    tg[names.get(q, f'#{q}')] += 1
                    human = True
                else:
                    tg[f'AI#{q}'] += 1
            else:
                noatk += 1
        b0 = int(rs[0]['bal0'])
        b1 = int(rs[-1]['bal1'])
        pcts = sorted(int(r['a']) for r in rs)
        key = '一兵没出' if sent == 0 else ('落在真人身上' if human else '落在无主地 / 内置 AI 上')
        x = summ[key]
        x[0] += 1
        x[1] += len(rs)
        x[2] += sent
        x[3] += fee
        tgs = '、'.join(f'{n}×{c}' for n, c in tg.items()) or '—'
        print(f'  拍 {t} {ours[p]:7s} {len(rs)} 条，比例 {pcts[0]}~{pcts[-1]}/1024；余额 {k(b0)} → {k(b1)}（剩 {b1 * 100 // max(1, b0)}%）；出兵 {k(sent)}、手续费 {k(fee)}；没产生进攻 {noatk} 条；目标 {tgs}')
    for key, x in summ.items():
        print(f'{key}：{x[0]} 批 {x[1]} 条，出兵 {k(x[2])}，手续费 {k(x[3])}')


main()
