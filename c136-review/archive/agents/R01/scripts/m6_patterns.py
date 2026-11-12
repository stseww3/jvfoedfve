#!/usr/bin/env python3
"""m6_patterns.py — 15 局逐局复盘里的“关键决策”按模式编号汇总（只读 analysis/*.json，不重算）。

每条关键决策（decisions[]）带一个模式编号（NEW-R01-XXnn）和判定（error 错 / good 对 / unclear 不清）。
模式的名字和定义取自第一次提出它的那一局的 newPatterns[]。
输出：
  1. 模式表：编号 | 名字 | 出现的局数 | 判定 错/对/不清 | 各局（局号后缀 e/g/u = 那一局该模式的判定）
  2. 家族小计（SP 出生 / OP 开局 / IO 指令通道 / AT 进攻 / DF 防守 / DN 捐兵 / EC 经济与被围 / SE 海 / EG 收场与离场）
  3. 各局的归类和判定条数
用法：python3 scripts/m6_patterns.py [--md] [--min N]      --min N：模式表只列出现在 ≥N 局的
"""
import glob, json, os, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
FAM = {'SP': '出生', 'OP': '开局', 'IO': '指令通道', 'AT': '进攻', 'DF': '防守', 'DN': '捐兵', 'EC': '经济与被围', 'SE': '海', 'EG': '收场与离场'}
ORDER = 'A075 A057 A059 A094 A055 A054 A031 A019 A009 A023 A050 A003 A005 B039 B043'.split()


def main():
    argv = sys.argv[1:]
    md = '--md' in argv
    mn = int(argv[argv.index('--min') + 1]) if '--min' in argv else 1
    A = {}
    for f in glob.glob(os.path.join(HERE, '..', 'analysis', '*.json')):
        d = json.load(open(f, encoding='utf8'))
        A[d['matchId']] = d
    mids = [m for m in ORDER if m in A] + sorted(m for m in A if m not in ORDER)
    names, first = {}, {}
    for m in mids:
        for n in A[m].get('newPatterns', []):
            if n['proposedId'] not in names:
                names[n['proposedId']] = n['name']
                first[n['proposedId']] = m
    # 用过但没有在 newPatterns 里立项的编号
    names.setdefault('NEW-R01-DF01', '挨打后按 12% 脉冲反击（未单独立项）')
    first.setdefault('NEW-R01-DF01', 'A057')
    per = defaultdict(lambda: defaultdict(Counter))   # pattern -> match -> verdict counter
    for m in mids:
        for x in A[m]['decisions']:
            per[x['patternId']][m][x['verdict']] += 1
    short = lambda p: p.replace('NEW-R01-', '')
    L = lambda c: ''.join(k[0] for k in ('error', 'good', 'unclear') if c[k])
    rows = []
    for p, bym in per.items():
        tot = Counter()
        for c in bym.values():
            tot.update(c)
        rows.append((p, len(bym), tot, bym))
    rows.sort(key=lambda r: (-r[1], -sum(r[2].values()), r[0]))
    bar = '| ' if md else ''
    end = ' |' if md else ''
    print(f'# {len(mids)} 局，关键决策 {sum(len(A[m]["decisions"]) for m in mids)} 条，模式 {len(per)} 个')
    print(bar + ' | '.join(['模式', '名字（首次提出的局）', '局数', '条数 错/对/不清', '各局（e 错 g 对 u 不清）']) + end)
    if md:
        print('|---|---|---|---|---|')
    for p, n, tot, bym in rows:
        if n < mn:
            continue
        print(bar + ' | '.join([short(p), f"{names.get(p, '?')}（{first.get(p, '?')}）", str(n), f"{tot['error']}/{tot['good']}/{tot['unclear']}",
                                ' '.join(f'{m}{L(bym[m])}' for m in mids if m in bym)]) + end)
    print()
    print(bar + ' | '.join(['家族', '模式数', '条数', '错/对/不清', '有“错”判定的局数']) + end)
    if md:
        print('|---|---|---|---|---|')
    for k, nm in FAM.items():
        ps = [r for r in rows if short(r[0]).startswith(k)]
        tot = Counter()
        games = set()
        for p, n, t, bym in ps:
            tot.update(t)
            games |= {m for m, c in bym.items() if c['error']}
        print(bar + ' | '.join([f'{k} {nm}', str(len(ps)), str(sum(tot.values())), f"{tot['error']}/{tot['good']}/{tot['unclear']}", str(len(games))]) + end)
    print()
    arch = Counter(A[m]['lossArchetype'] for m in mids)
    print('# 归类：' + '，'.join(f'{k} {v} 局（{" ".join(m for m in mids if A[m]["lossArchetype"] == k)}）' for k, v in arch.most_common()))
    v = Counter(x['verdict'] for m in mids for x in A[m]['decisions'])
    print(f"# 判定合计：错 {v['error']}，对 {v['good']}，不清 {v['unclear']}")


if __name__ == '__main__':
    main()
