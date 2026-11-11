#!/usr/bin/env python3
"""floor_tally.py — 汇总 shadow.mjs --floor 的逐样本行（不带 --quiet 时每个 号×采样拍 一行 `[留底] …`）。

口径：
  「有机器人邻居」= 该号当拍至少贴着 1 个机器人；「锁死」= 有机器人邻居、但没有任何机器人目标过得了留底。
  定留底的是谁：行里「由 机器人#x 决定：它的其它邻居里最弱的是 <名字>(<类别>)」的类别（我方号 / 机器人 / 其他真人）；
  没写「由…决定」的锁死样本归为「别的门槛」（safeFinite=0 却仍无目标）。
  「留底占存兵」= safeFinite ÷ 存兵。
用法：python3 scripts/floor_tally.py <floor 输出文件> [--wins 500:900,900:1200,1200:1500,1500:1700] [--by-bot] [--who]
"""
import re
import sys
import statistics as st
from collections import Counter, defaultdict

a = sys.argv[1:]
f = a[0]
val = lambda k, d: (a[a.index(k) + 1] if k in a else d)
wins = [tuple(int(x) for x in w.split(':')) for w in val('--wins', '500:900,900:1200,1200:1500,1500:1700').split(',')]
rx = re.compile(r'^\[留底\] t=(\d+) (\S+) 兵 (\d+) 地 (\d+)｜相邻机器人 (\d+) 个（共 (\d+) 格，其中几乎没兵的 (\d+) 个）｜safeFinite=(\d+)（([^）]*)）(.*?)｜此刻过得了留底的机器人目标 (\d+) 个')
rw = re.compile(r'由 机器人#(\d+)（地 (\d+) 兵 (\d+)）决定：它的其它邻居里最弱的是 (.+?)\((我方号|机器人|其他真人|路人队友|队友)\) 兵 (\d+)')
rows = []
for line in open(f, encoding='utf-8', errors='replace'):
    m = rx.match(line.strip())
    if not m:
        continue
    t, bot, B, L, nb, cells, empty, sf, _, rest, ok = m.groups()
    w = rw.search(rest)
    rows.append(dict(t=int(t), bot=bot, B=int(B), L=int(L), nb=int(nb), cells=int(cells), sf=int(sf), ok=int(ok),
                     who=(w.group(5) if w else None), whoName=(w.group(4) if w else None), via=(int(w.group(1)) if w else None)))
if not rows:
    sys.exit('没有 [留底] 行（别带 --quiet）')
bots = sorted({r['bot'] for r in rows}, key=lambda b: [r['bot'] for r in rows].index(b))
print(f'[留底分窗] {f.split("/")[-1]}：样本 {len(rows)} 个（号×采样拍），采样拍 {min(r["t"] for r in rows)}–{max(r["t"] for r in rows)}')
for lo, hi in wins:
    R = [r for r in rows if lo <= r['t'] < hi]
    if not R:
        continue
    have = [r for r in R if r['nb'] > 0]
    lock = [r for r in have if r['ok'] == 0]
    who = Counter((r['who'] or '别的门槛') for r in lock)
    half = [r for r in lock if r['sf'] * 2 >= r['B']]
    full = [r for r in lock if r['sf'] >= r['B']]
    print(f'== {lo}–{hi}：样本 {len(R)}｜有机器人邻居 {len(have)}（贴着的机器人地 中位 {int(st.median([r["cells"] for r in have])) if have else 0} 格）'
          f'｜锁死 {len(lock)}（{100 * len(lock) // max(1, len(have))}%）｜留底 ≥ 一半存兵 {len(half)}、≥ 全部存兵 {len(full)}'
          f'｜定留底的：' + '、'.join(f'{k} {v}' for k, v in who.most_common()))
    if '--by-bot' in a:
        for b in bots:
            Rb = [r for r in R if r['bot'] == b]
            hb = [r for r in Rb if r['nb'] > 0]
            lb = [r for r in hb if r['ok'] == 0]
            wb = Counter((r['who'] or '别的门槛') for r in lb)
            nm = Counter(r['whoName'] for r in lb if r['whoName'])
            print(f'   {b:>7}: 样本 {len(Rb)} 有机器人邻居 {len(hb)} 锁死 {len(lb)}｜贴着的机器人地 中位 {int(st.median([r["cells"] for r in hb])) if hb else 0} 格'
                  f'｜存兵 中位 {int(st.median([r["B"] for r in Rb])) if Rb else 0}｜' + '、'.join(f'{k} {v}' for k, v in wb.most_common())
                  + ('｜经谁：' + '、'.join(f'{k}×{v}' for k, v in nm.most_common(3)) if nm and '--who' in a else ''))
