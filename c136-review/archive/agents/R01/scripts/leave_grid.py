#!/usr/bin/env python3
"""leave_grid.py — 录像里的 leave 指令落在哪些拍：本队号的 leave 是不是都落在同一个“16 个回合”（112 拍）的网格上。

背景：A005 里本队 4 条 leave 在 1428、1540、1652、1652 拍，相隔正好 112 拍；同一局别的真人的 leave 不在这个网格上。
本脚本对每一局列出：本队（名字带 [APEX]）的 leave 拍、它们对 112 取余的值、是否全部同余；其他真人的 leave 里和本队同余的有几条
（随机的话约 1/16）。只读 out/<局号>/replay_cmds.csv（replay_cmds.mjs 或 resim.mjs 写的，不模拟）。

用法：python3 scripts/leave_grid.py [局号 ...] [--period 112]     不给局号 = out/ 下所有有 replay_cmds.csv 的局
"""
import csv
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'out')


def main():
    a = sys.argv[1:]
    period = int(a[a.index('--period') + 1]) if '--period' in a else 112
    ids = [x for i, x in enumerate(a) if not x.startswith('--') and (i == 0 or a[i - 1] != '--period')]
    if not ids:
        ids = sorted(os.path.basename(os.path.dirname(p)) for p in glob.glob(os.path.join(OUT, '*', 'replay_cmds.csv')))
    print(f'== leave 指令的拍号对 {period} 取余（{period // 7} 个回合）；只看出生阶段之后（tick > 0）的 leave')
    tot = {'m': 0, 'multi': 0, 'same': 0, 'pairs': 0, 'pairs_same': 0, 'oth': 0, 'oth_same': 0}
    for mid in ids:
        f = os.path.join(OUT, mid, 'replay_cmds.csv')
        if not os.path.exists(f):
            print(f'  {mid}: 没有 replay_cmds.csv'); continue
        sq, oth = [], []
        for r in csv.DictReader(open(f, encoding='utf8')):
            if r['kind'] != 'leave' or int(r['tick']) <= 0:
                continue
            (sq if r['pname'].startswith('[APEX]') else oth).append((int(r['tick']), r['pname'].replace('[APEX] ', '')))
        if not sq:
            continue
        tot['m'] += 1
        ticks = sorted(t for t, _ in sq)
        distinct = sorted(set(ticks))
        res = sorted({t % period for t in ticks})
        line = f"  {mid}: 本队 leave {len(ticks)} 条，拍号 {' '.join(str(t) for t in ticks)}；余数 {res}"
        if len(distinct) >= 2:
            tot['multi'] += 1
            pairs = [(x, y) for i, x in enumerate(distinct) for y in distinct[i + 1:]]
            same = sum(1 for x, y in pairs if (y - x) % period == 0)
            tot['pairs'] += len(pairs); tot['pairs_same'] += same
            if len(res) == 1:
                tot['same'] += 1
                line += '  <<< 不同拍的 leave 全部同余'
            else:
                line += f'；不同拍两两同余 {same}/{len(pairs)} 对'
        if oth and len(res) == 1:
            hit = sum(1 for t, _ in oth if t % period == res[0])
            tot['oth'] += len(oth); tot['oth_same'] += hit
            line += f'；其他真人的 leave {len(oth)} 条里同余的 {hit} 条'
        print(line)
    print(f"# 有本队 leave 的局 {tot['m']}；其中 leave 落在 ≥2 个不同拍的 {tot['multi']} 局，全部同余的 {tot['same']} 局；"
          f"不同拍两两同余 {tot['pairs_same']}/{tot['pairs']} 对（随机约 1/{period // 7}）；"
          f"在本队全部同余的局里，其他真人的 leave {tot['oth']} 条里同余的 {tot['oth_same']} 条")


if __name__ == '__main__':
    main()
