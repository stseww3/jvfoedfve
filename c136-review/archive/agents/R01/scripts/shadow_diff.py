#!/usr/bin/env python3
"""shadow_diff.py — 比较同一局两次影子运行（同一真值局面、不同策略内部开关）的决策差异。
用法：python3 shadow_diff.py <matchId> <tagB> [--tagA ''] [--show 12]
典型：先 node shadow.mjs <mid>（基线），再 node shadow.mjs <mid> --pin-no-full --tag nf0，然后本脚本 <mid> nf0。
按 (号, 拍, 类型, pct, 目标) 比较受理的指令：只在基线、只在对照、两边都有；并按代码位置汇总。
"""
import argparse, csv, os, re, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shadow_report import outline, nice_path, strategy_key, OUT

ap = argparse.ArgumentParser()
ap.add_argument('mid'); ap.add_argument('tagB'); ap.add_argument('--tagA', default=''); ap.add_argument('--show', type=int, default=12)
a = ap.parse_args()
def load(tag):
    p = os.path.join(OUT, a.mid, f'shadow_cmds{"_" + tag if tag else ""}.csv')
    return [r for r in csv.DictReader(open(p, encoding='utf8')) if r['ok'] == '1']
A, B = load(a.tagA), load(a.tagB)
key = lambda r: (r['bot'], int(r['t']), r['kind'], r['pct'], r['target'])
ka, kb = Counter(map(key, A)), Counter(map(key, B))
onlyA = [r for r in A if key(r) not in kb]
onlyB = [r for r in B if key(r) not in ka]
name_of = outline(strategy_key(a.mid))
print(f'== {a.mid} 决策差异：基线 {len(A)} 条，对照[{a.tagB}] {len(B)} 条；相同 {sum((ka & kb).values())}；只在基线 {len(onlyA)}；只在对照 {len(onlyB)}')
for nm, rows in (('只在基线', onlyA), ('只在对照', onlyB)):
    c = Counter((r['bot'], nice_path(r['path'], name_of, 1)) for r in rows)
    for (b, site), n in c.most_common(a.show):
        ts = [int(r['t']) for r in rows if r['bot'] == b and nice_path(r['path'], name_of, 1) == site]
        print(f'   {nm} {b:10s} {n:4d} 条 t={min(ts)}–{max(ts)}  {site}')
