#!/usr/bin/env python3
"""m6_donations.py — 15 局的捐兵账（跨局对比用），只读已有产物，不重算：
  out/<局>/resim_donations.csv   整局重演里每一条落地的捐兵指令（全场真人）：t, from, to, pct, fromBal, donorPaid, received, ok
  out/<局>/voronoi_seats.csv     席位 → 队、是不是本队号
  out/<局>/dispatch_audit.csv    （c116 的 11 局有）日志里每一条捐兵调度行：引擎在决策那一拍接不接受（would）、录像里有没有落地（executed）

引擎的收费（game.js transfer / donate L404–416，dispatch_audit.mjs 的公式和重演逐条对过）：
  名义额 v = min(floor(B×(pct+1)/1024), B − fee)，手续费 fee = floor(64×B/1024) —— 按捐出方的“全部余额”收 1/16，和捐多少无关。
  捐出方付 v + fee，受赠方到手 v（再受 receiverRoom 截断）。所以捐余额的 f 成，税率 = 0.0625 / (f + 0.0625)：
  pct=1023（全捐）6.3%；pct=320（31%）16.7%；pct=163（16%）28%；pct=51（5%）55.6%。
每局输出：
  本队：落地条数、付出、到账、税率（1 − 到账/付出）；按拍分三段（<3213 配额紧 / 3213–4284 / ≥4284 不设配额）；到账最多的那个号占本队到账的几成；
        单笔 pct 的中位数；ok=0（落地时被引擎拒收，整笔作废）的条数。
  其他真人：同样几项（看别人怎么用捐兵）。
  有 dispatch_audit 的局：日志调度行数；决策那一拍引擎就会拒收的（配额/上限）；引擎会收但录像里没落地的（指令通道丢的）；落地的。
用法：python3 scripts/m6_donations.py [局号 ...] [--md]
"""
import csv, os, statistics, sys

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, '..')
MIDS = 'A075 A057 A059 A094 A055 A054 A031 A019 A009 A023 A050 A003 A005 B039 B043'.split()
PH = (('<3213', 0, 3213), ('3213–4284', 3213, 4284), ('≥4284', 4284, 10 ** 9))


def rd(mid, name):
    p = os.path.join(R, 'out', mid, name)
    return list(csv.DictReader(open(p, encoding='utf8'))) if os.path.exists(p) else None


def acct(L):
    ok = [r for r in L if r['ok'] == '1']
    paid = sum(float(r['donorPaid']) for r in ok)
    got = sum(float(r['received']) for r in ok)
    by = {}
    for r in ok:
        by[r['to']] = by.get(r['to'], 0) + float(r['received'])
    top = max(by.values()) / got if got else None
    return {'n': len(L), 'bad': len(L) - len(ok), 'paid': paid, 'got': got, 'tax': 1 - got / paid if paid else None, 'top': top,
            'pct': statistics.median(int(r['pct']) for r in L) if L else None}


def main():
    argv = sys.argv[1:]
    mids = [x for x in argv if not x.startswith('--')] or MIDS
    md = '--md' in argv
    f = lambda x, d=0: '-' if x is None else f'{100 * x:.{d}f}%'
    w = lambda x: f'{x / 1e4:.0f} 万' if x else '0'
    rows = []
    for m in mids:
        don, seats = rd(m, 'resim_donations.csv'), rd(m, 'voronoi_seats.csv')
        if don is None or seats is None:
            rows.append((m, None))
            continue
        sq = {r['p'] for r in seats if r['squad'] == '1'}
        S = [r for r in don if r['from'] in sq]
        O = [r for r in don if r['from'] not in sq]
        a, o = acct(S), acct(O)
        ph = [acct([r for r in S if lo <= int(r['t']) < hi]) for _, lo, hi in PH]
        aud = rd(m, 'dispatch_audit.csv')
        au = None
        if aud:
            au = {'lines': len(aud), 'refuse': sum(1 for r in aud if r['would'] != 'accept'), 'refuseLanded': sum(1 for r in aud if r['would'] != 'accept' and r['executed'] == '1'),
                  'lost': sum(1 for r in aud if r['would'] == 'accept' and r['executed'] != '1'), 'landed': sum(1 for r in aud if r['executed'] == '1')}
        rows.append((m, a, o, ph, au))
    sep = ' | '
    print(('| ' if md else '') + sep.join(['局', '本队落地的捐兵：条数 / 付出 / 到账 / 税率', '按拍 <3213 / 3213–4284 / ≥4284：条数（税率）', '到账最多的号占比 · 单笔 pct 中位', '落地时被拒收',
                                        '其他真人：条数 / 到账 / 税率 / 到账最多的号占比 / pct 中位', '日志调度行：共 / 决策拍引擎就拒收 / 引擎会收但没落地 / 落地']) + (' |' if md else ''))
    if md:
        print('|---' * 7 + '|')
    T = {'n': 0, 'paid': 0.0, 'got': 0.0, 'on': 0, 'opaid': 0.0, 'ogot': 0.0, 'lines': 0, 'refuse': 0, 'lost': 0, 'landed': 0}
    for row in rows:
        m = row[0]
        if row[1] is None:
            print(('| ' if md else '') + sep.join([m, '没有落地的捐兵（或没有重演产物）', '', '', '', '', '']) + (' |' if md else ''))
            continue
        _, a, o, ph, au = row
        cells = [m, f"{a['n']} / {w(a['paid'])} / {w(a['got'])} / {f(a['tax'], 1)}", ' / '.join(f"{p['n']}（{f(p['tax'])}）" for p in ph),
                 f"{f(a['top'])} · {a['pct'] if a['pct'] is not None else '-'}", str(a['bad']),
                 f"{o['n']} / {w(o['got'])} / {f(o['tax'], 1)} / {f(o['top'])} / {o['pct'] if o['pct'] is not None else '-'}",
                 f"{au['lines']} / {au['refuse']} / {au['lost']} / {au['landed']}" if au else '—']
        print(('| ' if md else '') + sep.join(cells) + (' |' if md else ''))
        T['n'] += a['n']; T['paid'] += a['paid']; T['got'] += a['got']; T['on'] += o['n']; T['opaid'] += o['paid']; T['ogot'] += o['got']
        if au:
            for k in ('lines', 'refuse', 'lost', 'landed'):
                T[k] += au[k]
    tot = ['合计', f"{T['n']} / {w(T['paid'])} / {w(T['got'])} / {f(1 - T['got'] / T['paid'], 1) if T['paid'] else '-'}", '', '', '',
           f"{T['on']} / {w(T['ogot'])} / {f(1 - T['ogot'] / T['opaid'], 1) if T['opaid'] else '-'}", f"{T['lines']} / {T['refuse']} / {T['lost']} / {T['landed']}"]
    print(('| ' if md else '') + sep.join(tot) + (' |' if md else ''))


if __name__ == '__main__':
    main()
