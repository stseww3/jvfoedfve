#!/usr/bin/env python3
# pattern_evidence.py — 把 reviews/*.json 里同一个模式的决策按局排在一起（跨局归纳时逐条对着看）。
# 用法：python3 scripts/pattern_evidence.py [模式编号 …] [--full]
#   不给编号 = 全部模式，按「判错的局数」从多到少排；--full 连 why / evidence 一起印（默认只印 what）。
# 只读 reviews/*.json 和 scripts/patterns_r04.json，不算新数。
import sys, os, json, glob, collections
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LET = {'error': 'E', 'good': 'G', 'unclear': 'U'}


def main():
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    full = '--full' in sys.argv
    lib = json.load(open(os.path.join(HERE, 'patterns_r04.json'), encoding='utf8'))
    revs = {}
    for fp in sorted(glob.glob(os.path.join(ROOT, 'reviews', '*.json'))):
        d = json.load(open(fp, encoding='utf8'))
        revs[d['matchId']] = d
    by = collections.defaultdict(list)
    for m, d in revs.items():
        for x in d['decisions']:
            by[x['patternId']].append((m, x))
    pids = a or sorted(by, key=lambda p: (-len({m for m, x in by[p] if x['verdict'] == 'error'}), -len({m for m, x in by[p]}), p))
    for p in pids:
        rows = by.get(p, [])
        c = collections.Counter(x['verdict'] for m, x in rows)
        print('=== %s｜%s' % (p, lib.get(p, {}).get('name', '')))
        print('    %d 局、%d 条决策（错 %d / 对 %d / 不明 %d）' % (len({m for m, x in rows}), len(rows), c['error'], c['good'], c['unclear']))
        if full and p in lib:
            print('    口径：' + lib[p]['definition'])
            print('    代码：' + lib[p]['codePath'])
        for m, x in rows:
            print('  [%s %s %s 拍 %s｜%s] %s' % (m, LET[x['verdict']], x['id'], x['t'], x['bot'], x['what']))
            if full:
                print('        为什么：' + x['why'])
                print('        证据：' + x['evidence'])
        print()


if __name__ == '__main__':
    main()
