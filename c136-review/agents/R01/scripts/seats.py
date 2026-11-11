#!/usr/bin/env python3
"""席位表：python3 scripts/seats.py <mid> [--t 拍]

读 out/<mid>/resim_meta.json（names、teams、squad），按队列出人类席位的 席位号 名字；
给 --t 时再从 out/<mid>/resim_players.csv 取那一拍的 领土/余额/状态（state 2 = 离场壳，alive 0 = 已死）。
只为了把证据里的 “#席位” 和名字对上，不做任何统计。
"""
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    mid = sys.argv[1]
    t = None
    if '--t' in sys.argv:
        t = int(sys.argv[sys.argv.index('--t') + 1])
    out = os.path.join(HERE, '..', 'out', mid)
    meta = json.load(open(os.path.join(out, 'resim_meta.json'), encoding='utf-8'))
    names = meta['names']
    teams = {int(k): v for k, v in meta['teams'].items()}
    squad = {v: k for k, v in meta['squad'].items()}
    rows = {}
    if t is not None:
        with open(os.path.join(out, 'resim_players.csv'), encoding='utf-8') as f:
            for r in csv.DictReader(f):
                if int(r['t']) == t:
                    rows[int(r['p'])] = r
    by_team = {}
    for p, tm in sorted(teams.items()):
        by_team.setdefault(tm, []).append(p)
    print('== %s 席位表（人类席位 %d 个）%s' % (mid, len(teams), '' if t is None else '；t=%d 的 领土/余额' % t))
    for tm in sorted(by_team):
        ps = by_team[tm]
        print('  T%d（%d 个席位，其中本队号 %d 个）' % (tm, len(ps), sum(1 for p in ps if p in squad)))
        for p in ps:
            nm = names[p] if p < len(names) else '?'
            tag = ' [本队 %s]' % squad[p] if p in squad else ''
            extra = ''
            if t is not None:
                r = rows.get(p)
                if r is None:
                    extra = ' | 无记录'
                else:
                    st = '已死' if r['alive'] == '0' else ('离场壳' if r['state'] == '2' else '在场')
                    extra = ' | %s 领土 %s 余额 %s' % (st, r['terr'], r['bal'])
            print('    #%-2d %s%s%s' % (p, nm, tag, extra))
    return 0


if __name__ == '__main__':
    sys.exit(main())
