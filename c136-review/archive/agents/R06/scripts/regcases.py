#!/usr/bin/env python3
"""regcases.py — 回归用例清单：把 15 局复盘里逐条审过的决策（reviews/*.json 的 decisions）按「会审提案的改动项」分组列出来

给阶段 C 用：新版策略挂到这些局、这些拍上跑影子，逐条看
  · 判「错」的那些拍，新版还会不会做同样的事；
  · 判「对」的那些拍，新版有没有把做对的事改没了。

分组按决策挂的模式名前缀（模式定义见 reviews/*.json 的 newPatterns 和 cards/）：
  P2 在途账本        IO-* / CMD-* / AT-dump-then-dead
  P3 选点            SP-*
  P4 抢内置 AI 的底线 OP-* / AT-ai-order-too-small / EG-mincmd-skips-small-ai / AT-bot-farm
  P5 核心期的闸      AT-* / EG-* / DF-* / EC-*（上面点名的除外）
  P6 捐款            DN-* / AS-*
  P7 船              BT-*
  P8 保护名单与空壳  PL-* / TS-* / HK-*
  其它               PV-* / FE-* 等

用法：python3 scripts/regcases.py            产物：out/_cross/regcases.txt
"""
import json
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from r06lib import OUT  # noqa: E402

ROOT = os.path.dirname(HERE)
IDS = ['B001', 'B002', 'B003', 'B010', 'B014', 'B017', 'B018', 'B021', 'B022', 'B023', 'B025', 'B038', 'B039', 'B041', 'B045']
GROUPS = ['P2 在途账本', 'P3 选点', 'P4 抢内置 AI 的底线', 'P5 核心期的闸', 'P6 捐款', 'P7 船', 'P8 保护名单与空壳', '其它']
VERD = dict(error='错', good='对', unclear='不确定')


def group_of(pid):
    p = (pid or '').replace('NEW:', '')
    if p.startswith(('IO-', 'CMD-')) or p == 'AT-dump-then-dead':
        return GROUPS[0]
    if p.startswith('SP-'):
        return GROUPS[1]
    if p.startswith('OP-') or p in ('AT-ai-order-too-small', 'EG-mincmd-skips-small-ai', 'AT-bot-farm'):
        return GROUPS[2]
    if p.startswith(('AT-', 'EG-', 'DF-', 'EC-')):
        return GROUPS[3]
    if p.startswith(('DN-', 'AS-')):
        return GROUPS[4]
    if p.startswith('BT-'):
        return GROUPS[5]
    if p.startswith(('PL-', 'TS-', 'HK-')):
        return GROUPS[6]
    return GROUPS[7]


def cut(s, n):
    s = str(s or '').replace('|', '／').replace('\n', ' ')
    return s if len(s) <= n else s[:n - 1] + '…'


def main():
    rows = defaultdict(list)
    tally = defaultdict(Counter)
    for mid in IDS:
        p = os.path.join(ROOT, 'reviews', f'{mid}.json')
        if not os.path.exists(p):
            continue
        for d in json.load(open(p)).get('decisions') or []:
            g = group_of(d.get('patternId'))
            v = VERD.get(d.get('verdict'), d.get('verdict'))
            rows[g].append((mid, d.get('t'), d.get('bot'), v, (d.get('patternId') or '').replace('NEW:', ''), d.get('codePath'), d.get('state')))
            tally[g][v] += 1
    out = []
    out.append('| 改动项 | 判错 | 判对 | 不确定 | 合计 |')
    out.append('|---|---|---|---|---|')
    for g in GROUPS:
        c = tally[g]
        out.append(f"| {g} | {c['错']} | {c['对']} | {c['不确定']} | {sum(c.values())} |")
    out.append(f"| 合计 | {sum(c['错'] for c in tally.values())} | {sum(c['对'] for c in tally.values())} | {sum(c['不确定'] for c in tally.values())} | {sum(sum(c.values()) for c in tally.values())} |")
    for g in GROUPS:
        out.append('')
        out.append(f'### {g}（{len(rows[g])} 条）')
        out.append('')
        out.append('| 局 | 拍 | 号 | 判定 | 模式 | 代码位置 | 当时的局面 |')
        out.append('|---|---|---|---|---|---|---|')
        order = dict(错=0, 对=1, 不确定=2)
        for r in sorted(rows[g], key=lambda r: (order.get(r[3], 3), r[4], r[0], r[1] if isinstance(r[1], (int, float)) else 0)):
            out.append(f"| {r[0]} | {r[1]} | {cut(r[2], 28)} | {r[3]} | {r[4]} | {cut(r[5], 150)} | {cut(r[6], 220)} |")
    txt = '\n'.join(out) + '\n'
    os.makedirs(os.path.join(OUT, '_cross'), exist_ok=True)
    open(os.path.join(OUT, '_cross', 'regcases.txt'), 'w').write(txt)
    print('\n'.join(out[:12]))
    print(f'…… 全文 {len(out)} 行 → out/_cross/regcases.txt')


if __name__ == '__main__':
    main()
