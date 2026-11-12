#!/usr/bin/env python3
"""v28_equiv.py — R07：比对两份影子指令流（v28_shadow.mjs 写的 out/_cache/v28/<matchId>_<label>_cmds.tsv）是否逐拍逐条相同。

用法：python3 c136-review/agents/R07/scripts/v28_equiv.py <matchId> <labelA> <labelB> [--show N]
退出码：0 = 完全相同；1 = 有差异（打印前 N 处，默认 12）。

用途：v28 把模块开关全部关掉时，决策必须和 Vc（v27-team-c116.js）逐拍逐条相同；每加一个模块都重跑一遍。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load(mid, label):
    path = os.path.join(HERE, '..', 'out', '_cache', 'v28', f'{mid}_{label}_cmds.tsv')
    rows = []
    with open(path, encoding='utf-8') as f:
        next(f)
        for ln in f:
            ln = ln.rstrip('\n')
            if ln:
                rows.append(tuple(ln.split('\t')))
    return rows


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(2)
    mid, a, b = sys.argv[1:4]
    show = int(sys.argv[sys.argv.index('--show') + 1]) if '--show' in sys.argv else 12
    ra, rb = load(mid, a), load(mid, b)
    if ra == rb:
        print(f'{mid}: {a} 与 {b} 的影子指令流完全相同（{len(ra)} 条）')
        sys.exit(0)
    sa, sb = set(ra), set(rb)
    only_a = sorted(sa - sb, key=lambda r: (int(r[0]), r[1]))
    only_b = sorted(sb - sa, key=lambda r: (int(r[0]), r[1]))
    first = None
    for i, (x, y) in enumerate(zip(ra, rb)):
        if x != y:
            first = (i, x, y)
            break
    print(f'{mid}: {a}（{len(ra)} 条）与 {b}（{len(rb)} 条）不同；只在 {a} 里 {len(only_a)} 条，只在 {b} 里 {len(only_b)} 条')
    if first:
        print(f'  第一处不同：第 {first[0]} 条  {a}={first[1]}  {b}={first[2]}')
    for r in only_a[:show]:
        print(f'  只在 {a}: {r}')
    for r in only_b[:show]:
        print(f'  只在 {b}: {r}')
    sys.exit(1)


if __name__ == '__main__':
    main()
