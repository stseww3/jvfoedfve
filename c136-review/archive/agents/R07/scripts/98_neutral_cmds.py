#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""98_neutral_cmds.py — R07：核心逻辑阶段（默认 t≥1500）打无主地的指令：条数、发兵、手续费、pct 分布。

背景：邻居出局 / 被清场后会空出零碎的无主地。策略的 General.expandNeutral 把这种指令垫到最小指令（minCmd = feeK×手续费，
      约等于余额的 4.69%，落到引擎里恒为 pct=47），引擎再按全部余额收 12/1024 的手续费——
      吃几十格空地的一条指令要发出余额的 4.6%、付掉余额的 1.17%。这个脚本把这类指令逐条列出来并合计。
输入：out/<matchId>/humans_cmd.tsv（74_side_flow.mjs：全场真人逐条指令，tt=N 表示目标是无主地；squad=1 是我方号）
用法（在 scripts/ 目录下）：python3 98_neutral_cmds.py <matchId> [--t0 1500] [--gap 60]
输出：out/<matchId>/neutral_cmds.txt
  A. 我方号 t≥t0 打无主地的指令逐条（落地拍、号、pct、落地前余额、发兵、手续费、手续费 ÷ 发兵）
  B. 每个号合计；其中 pct=47 的条数
  C. 按「相邻两条不超过 gap 拍」分成的段：拍号范围、条数、号、发兵、手续费
  D. 对照：别的真人 t≥t0 打无主地的指令条数、发兵、手续费、pct 中位数；其中 pct=47 的条数
"""
import csv
import os
import statistics
import sys
from collections import OrderedDict, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))


def f(n):
    return f"{int(round(n)):,}"


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    mid = sys.argv[1]
    t0 = 1500
    gap = 60
    a = sys.argv[2:]
    i = 0
    while i < len(a):
        if a[i] == '--t0':
            t0 = int(a[i + 1]); i += 2
        elif a[i] == '--gap':
            gap = int(a[i + 1]); i += 2
        else:
            raise SystemExit(f'未知参数 {a[i]}')
    out = os.path.join(HERE, '..', 'out', mid)
    rows = list(csv.DictReader(open(os.path.join(out, 'humans_cmd.tsv'), encoding='utf-8'), delimiter='\t'))
    neu = [r for r in rows if r['kind'] == 'attack' and r['tt'] == 'N' and int(r['t']) >= t0]
    ours = [r for r in neu if r['squad'] in ('1', 'true', 'True')]
    oth = [r for r in neu if r['squad'] not in ('1', 'true', 'True')]
    T = []
    P = T.append
    P(f"# {mid} t≥{t0} 打无主地的指令（98_neutral_cmds.py；来源 humans_cmd.tsv，引擎里落地时的真实扣款）")
    P(f"# 我方 {len(ours)} 条：发兵 {f(sum(int(r['troops']) for r in ours))}、手续费 {f(sum(int(r['fee']) for r in ours))}；"
      f"其中 pct=47 的 {sum(1 for r in ours if r['pct'] == '47')} 条（发兵 {f(sum(int(r['troops']) for r in ours if r['pct'] == '47'))}、手续费 {f(sum(int(r['fee']) for r in ours if r['pct'] == '47'))}）")
    P('')
    P('A. 逐条（落地拍 号 pct | 落地前余额 | 发兵 | 手续费 | 手续费 ÷ 发兵 | 发兵 ÷ 余额）')
    for r in ours:
        b0 = int(r['b0']); tr = int(r['troops']); fe = int(r['fee'])
        P(f"  t={r['t']} {r['name'].replace('[APEX] ', '')} pct={r['pct']} | {f(b0)} | {f(tr)} | {f(fe)} | {100 * fe / max(1, tr):.0f}% | {100 * tr / max(1, b0):.1f}%")
    P('')
    P('B. 每个号合计（条数 / 发兵 / 手续费；其中 pct=47 的条数）')
    per = OrderedDict()
    for r in ours:
        k = r['name'].replace('[APEX] ', '')
        d = per.setdefault(k, dict(n=0, troops=0, fee=0, n47=0, t0=int(r['t']), t1=int(r['t'])))
        d['n'] += 1; d['troops'] += int(r['troops']); d['fee'] += int(r['fee']); d['n47'] += (r['pct'] == '47'); d['t1'] = int(r['t'])
    for k, d in sorted(per.items(), key=lambda kv: -kv[1]['fee']):
        P(f"  {k}: {d['n']} 条 / {f(d['troops'])} / {f(d['fee'])}；pct=47 的 {d['n47']} 条；t={d['t0']}~{d['t1']}")
    P('')
    P(f'C. 分段（相邻两条不超过 {gap} 拍算一段）')
    segs = []
    for r in sorted(ours, key=lambda r: int(r['t'])):
        t = int(r['t'])
        if segs and t - segs[-1]['t1'] <= gap:
            s = segs[-1]
        else:
            s = dict(t0=t, t1=t, n=0, troops=0, fee=0, bots=defaultdict(lambda: [0, 0, 0]))
            segs.append(s)
        s['t1'] = t; s['n'] += 1; s['troops'] += int(r['troops']); s['fee'] += int(r['fee'])
        b = s['bots'][r['name'].replace('[APEX] ', '')]
        b[0] += 1; b[1] += int(r['troops']); b[2] += int(r['fee'])
    for s in segs:
        bots = '、'.join(f"{k} {v[0]} 条 {f(v[1])} / {f(v[2])}" for k, v in sorted(s['bots'].items(), key=lambda kv: -kv[1][2]))
        P(f"  t={s['t0']}~{s['t1']}: {s['n']} 条，发兵 {f(s['troops'])}、手续费 {f(s['fee'])}（{bots}）")
    P('')
    P(f'D. 对照：别的真人 t≥{t0} 打无主地的指令')
    if oth:
        pcts = [int(r['pct']) for r in oth]
        P(f"  {len(oth)} 条（{len(set(r['p'] for r in oth))} 个人），发兵 {f(sum(int(r['troops']) for r in oth))}、手续费 {f(sum(int(r['fee']) for r in oth))}；"
          f"pct 中位数 {statistics.median(pcts):.0f}（最小 {min(pcts)}、最大 {max(pcts)}）；pct=47 的 {sum(1 for p in pcts if p == 47)} 条")
        fr = [100 * int(r['fee']) / max(1, int(r['troops'])) for r in oth if int(r['troops']) > 0]
        if fr:
            P(f"  手续费 ÷ 发兵 的中位数 {statistics.median(fr):.0f}%（我方 {statistics.median([100 * int(r['fee']) / max(1, int(r['troops'])) for r in ours if int(r['troops']) > 0]):.0f}%）" if ours else '')
    else:
        P('  0 条')
    open(os.path.join(out, 'neutral_cmds.txt'), 'w', encoding='utf-8').write('\n'.join(T) + '\n')
    print('\n'.join(T))


if __name__ == '__main__':
    main()
