#!/usr/bin/env python3
"""spawn_exec_sum.py — 把 spawn_exec.py --tsv 的全量输出按 组别 × 结局 汇总：最终坐标落地 / 停在旧坐标 / 日志外坐标 / 0 条落地 的号数与占比。

输入：out/spawn-exec-all.tsv（python3 scripts/spawn_exec.py --tsv <全部有录像的局> > out/spawn-exec-all.tsv）+ 各局 card.json 的结局。
口径见 spawn_exec.py 头注：只数「在录像这一盘里」的号；B 组（c110）没有协调器求解行，「最终坐标」= 该号自己日志里最后一次算出的出生点。
用法：python3 scripts/spawn_exec_sum.py [--tsv out/spawn-exec-all.tsv] [--list]      --list：列出有号 0 条落地、或一半以上的号停在旧坐标的局
"""
import collections
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
a = sys.argv[1:]
tsv = a[a.index('--tsv') + 1] if '--tsv' in a else os.path.join(HERE, '..', 'out', 'spawn-exec-all.tsv')
SRC = os.environ.get('C136_DATA', '/agent/repos/c136-data')
agg = collections.defaultdict(collections.Counter)
zero, half = [], []
for r in csv.DictReader(open(tsv, encoding='utf-8'), delimiter='\t'):
    m = r['matchId']
    try:
        n = int(r['inReplay'])
        card = json.load(open(f"{SRC}/{os.environ.get('C136_BUNDLES', 'bundles')}/{m}/card.json"))
    except (ValueError, TypeError, OSError):
        continue
    res = card['outcome']['resultLabel']
    v = {k: int(r[k] or 0) for k in ('finalLanded', 'stuckOld', 'offLog', 'zeroLanded')}
    for key in ((m[0], res), (m[0], '合计')):
        c = agg[key]
        c['games'] += 1
        c['bots'] += n
        c.update(v)
        c['gamesZero'] += 1 if v['zeroLanded'] else 0
        c['gamesAllFinal'] += 1 if n and v['finalLanded'] == n else 0
        c['gamesHalfOld'] += 1 if n and 2 * v['stuckOld'] >= n else 0
        c['rounds'] += int(r['solveRounds'] or 0)
    if v['zeroLanded']:
        zero.append(f"{m}（{v['zeroLanded']}/{n}）")
    if n and 2 * v['stuckOld'] >= n:
        half.append(f"{m}（{v['stuckOld']}/{n}）")
p = lambda x, y: f'{100 * x / y:.0f}%' if y else '–'
print('组别\t结局\t局数\t录像盘里的号\t最终坐标落地\t停在旧坐标\t日志外坐标\t0 条落地\t全部号都落在最终坐标的局\t一半以上的号停在旧坐标的局\t有号 0 条落地的局\t每局求解轮数（平均）')
for key in sorted(agg):
    c = agg[key]
    print('\t'.join([key[0], key[1], str(c['games']), str(c['bots']), f"{c['finalLanded']}（{p(c['finalLanded'], c['bots'])}）", f"{c['stuckOld']}（{p(c['stuckOld'], c['bots'])}）",
                     f"{c['offLog']}（{p(c['offLog'], c['bots'])}）", f"{c['zeroLanded']}（{p(c['zeroLanded'], c['bots'])}）", str(c['gamesAllFinal']), str(c['gamesHalfOld']), str(c['gamesZero']),
                     f"{c['rounds'] / max(1, c['games']):.0f}"]))
if '--list' in a:
    print('有号 0 条落地的局：' + '、'.join(zero))
    print('一半以上的号停在旧坐标的局：' + '、'.join(half))
