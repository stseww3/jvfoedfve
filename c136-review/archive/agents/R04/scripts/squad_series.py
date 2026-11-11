#!/usr/bin/env python3
# squad_series.py — 我方每个号在一串拍上的 领土 / 余额 / 密度（真引擎重放 tmp/truth/<局号>/our.tsv），
# 一行一个拍，方便看「谁在哪一段长了、谁在哪一段塌了」。
# 用法：python3 scripts/squad_series.py <局号> <t0> <t1> [步长=300] [--terr|--bal|--dens] [--ours id,id,…]
#   默认每格印 领土/余额(千)/密度；--terr、--bal、--dens 只印其中一项（列更窄）。
#   最右边一列是我方号合计领土、合计余额，以及同队其他真人（不是我方号）的合计领土。
import sys, os, collections
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from match_digest import Match, fmt


def main():
    a = sys.argv[1:]
    mid = a[0]
    ov = [int(x) for x in a[a.index('--ours') + 1].split(',')] if '--ours' in a else None
    pos = [x for x in a[1:] if not x.startswith('--') and (ov is None or x != a[a.index('--ours') + 1])]
    t0, t1 = int(pos[0]), int(pos[1])
    step = int(pos[2]) if len(pos) > 2 else 300
    mode = 'terr' if '--terr' in a else 'bal' if '--bal' in a else 'dens' if '--dens' in a else 'all'
    M = Match(mid, ov)
    our = sorted(M.our_ids)
    names = [M.ours[p].replace('[APEX] ', '') for p in our]
    # M.our: 号 -> 拍 -> (领土, 余额, …)；M.teamts: 拍 -> 队 -> (领土, 余额, …)
    rows = collections.defaultdict(dict)
    for p in our:
        for t, v in M.our[p].items():
            rows[t][p] = (v[0], v[1])
    team = M.teamts
    my_team = M.team[our[0]]
    w = 20 if mode == 'all' else 8
    print(f'# {mid} 我方各号逐拍（{"领土/余额(千)/密度" if mode == "all" else {"terr": "领土", "bal": "余额(千)", "dens": "密度"}[mode]}）；右边：我方号合计领土 / 合计余额 / 同队其他真人领土')
    print('拍     ' + ' '.join(f'{n:>{w}s}' for n in names) + ' | 合计')
    ticks = sorted(rows)
    for t in range(t0, t1 + 1, step):
        tt = min(ticks, key=lambda x: abs(x - t))
        cells = []
        st = sb = 0
        for p in our:
            terr, bal = rows[tt].get(p, (0, 0))
            st += terr; sb += bal
            if terr <= 0:
                cells.append(f'{"-":>{w}s}')
            elif mode == 'terr':
                cells.append(f'{terr:>{w}d}')
            elif mode == 'bal':
                cells.append(f'{bal / 1000:>{w}.0f}')
            elif mode == 'dens':
                cells.append(f'{bal / terr:>{w}.1f}')
            else:
                cells.append(f'{terr:>6d}/{bal / 1000:>6.0f}/{bal / terr:>5.1f} ')
        tm = team.get(tt, {}).get(my_team, (0, 0))
        print(f'{tt:<6d} ' + ' '.join(cells) + f' | {st} / {fmt(sb)} / {tm[0] - st}')


if __name__ == '__main__':
    main()
