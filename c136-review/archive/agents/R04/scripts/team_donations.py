#!/usr/bin/env python3
# 全场各队落地的捐款：逐笔的捐款人余额、比例、到账、税，以及「税 ÷ 到账」。
# 引擎规则：税 = 捐款人余额的 6.25%，与捐多少无关；所以捐的比例越小，税占到账的比例越高
# （a=1023/1024 把余额全捐掉时税是到账的 6.7%，a=225/1024 时约 30%）。
# 用法：python3 scripts/team_donations.py <局号> [--team N] [--list]
# 数据：tmp/truth/<局号>/cmd.tsv（id=2 的行）、meta.json（先跑 engine_truth_all.sh）。
import csv
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def k(v):
    v = int(v)
    if abs(v) >= 10_000_000:
        return '%.1fM' % (v / 1e6)
    if abs(v) >= 10_000:
        return '%dk' % round(v / 1000)
    return str(v)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args:
        print(__doc__ or '用法：team_donations.py <局号> [--team N] [--list]')
        sys.exit(1)
    mid = args[0]
    only = None
    if '--team' in sys.argv:
        only = int(sys.argv[sys.argv.index('--team') + 1])
    show = '--list' in sys.argv or only is not None
    d = os.path.join(ROOT, 'tmp', 'truth', mid)
    meta = json.load(open(os.path.join(d, 'meta.json'), encoding='utf8'))
    team = {p['p']: p['team'] for p in meta['players']}
    name = {p['p']: p['name'] for p in meta['players']}
    ours = {int(i) for i in meta.get('ours', {})}
    tot = defaultdict(lambda: [0, 0, 0, 0, 0, 0])  # 笔数 到账 税 全捐笔数 全捐到账 全捐税
    rows = []
    for r in csv.DictReader(open(os.path.join(d, 'cmd.tsv'), encoding='utf8'), delimiter='\t'):
        if r['id'] != '2' or not r['q'] or not r['balQ0']:
            continue
        p, q = int(r['p']), int(r['q'])
        bal0, bal1 = int(r['bal0']), int(r['bal1'])
        got = int(r['balQ1']) - int(r['balQ0'])
        if got <= 0:
            continue
        tax = bal0 - bal1 - got
        T = team.get(p, 0)
        a = int(r['a'])
        x = tot[T]
        x[0] += 1
        x[1] += got
        x[2] += tax
        if a >= 1000:
            x[3] += 1
            x[4] += got
            x[5] += tax
        rows.append((int(r['t']), T, p, q, a, bal0, got, tax))
    print('# %s 全场落地的捐款（到账 > 0 的）：按捐款人所在的队' % mid)
    for T in sorted(tot):
        n, got, tax, n2, got2, tax2 = tot[T]
        print('  队%d：%d 笔，到账 %s，税 %s（税 ÷ 到账 = %.1f%%）；其中比例 ≥1000/1024（把余额全捐掉）的 %d 笔，到账 %s，税 %s（%.1f%%）'
              % (T, n, k(got), k(tax), 100 * tax / max(1, got), n2, k(got2), k(tax2), 100 * tax2 / max(1, got2)))
    mine = [r for r in rows if r[2] in ours]
    if mine:
        got = sum(r[6] for r in mine)
        tax = sum(r[7] for r in mine)
        pcts = sorted(r[4] for r in mine)
        print('  其中我方号 %d 笔：到账 %s，税 %s（%.1f%%）；比例（/1024）最小 %d、中位 %d、最大 %d；给编队外的 %d 笔'
              % (len(mine), k(got), k(tax), 100 * tax / max(1, got), pcts[0], pcts[len(pcts) // 2], pcts[-1],
                 sum(1 for r in mine if r[3] not in ours)))
    other = [r for r in rows if r[2] not in ours and team.get(r[2]) == team.get(next(iter(ours), -1))]
    if ours:
        print('  同队的非编队真人捐出 %d 笔，到账 %s；其中给我方号的 %d 笔'
              % (len(other), k(sum(r[6] for r in other)), sum(1 for r in other if r[3] in ours)))
    if show:
        for t, T, p, q, a, bal0, got, tax in rows:
            if only is not None and T != only:
                continue
            if only is None and p in ours:
                continue
            print('  拍 %5d 队%d %s → %s：比例 %d/1024，捐款人余额 %s，到账 %s，税 %s（税 ÷ 到账 %.1f%%）'
                  % (t, T, name.get(p, p), name.get(q, q), a, k(bal0), k(got), k(tax), 100 * tax / max(1, got)))


if __name__ == '__main__':
    main()
