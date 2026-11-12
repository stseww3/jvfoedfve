#!/usr/bin/env python3
"""hold_list.py — 生成 tools/hold_list.txt：实录阶梯「最后一个已知点之后」那条假定的对照运行清单。

C2 在一个席位最后一个已知点之后假定页面追平。已有的 C2 断面结果（sim-v2/calib/g0/*-C2.json）里，凡是
  · 窗口里有「看不见还在卡」的一段（某席位最后一个已知点上页面还落后 28 拍以上，而这之后席位和页面都还在）
    占到窗口内 席位·拍 的 5% 以上，或者
  · 窗口末编队领土偏出真局 ±10%
的运行，各加两条同样设置、只换通道的对照：
  · C2:after=hold（已知点之后一直保持那时的落后）；
  · C2:after=cut （已知点之后发出的指令一律算没落地）。
缺省的 C2 是第三种（已知点之后页面追平）。「看不见的一段」的算法与 tools/g0_report.mjs 里 ckpt-out 表的相同。

用法（在 c136-review/agents/R06 下）：python3 sim-v2/tools/hold_list.py
"""
import glob
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SIMV2 = os.path.dirname(HERE)
idx = json.load(open(os.path.join(SIMV2, 'packs', 'index.json')))
lines = []
for f in sorted(glob.glob(os.path.join(SIMV2, 'calib', 'g0', '*-C2.json'))):
    r = json.load(open(f))
    mid, t0, t1 = r['match'], r['t0'], r['t1']
    tf = os.path.join(SIMV2, 'traces', mid + '.json')
    if not os.path.exists(tf) or not r['history'].get('terr1'):
        continue
    T = json.load(open(tf))
    pk = idx[mid]
    blind = tot = 0
    for p, rs in T['seats'].items():
        if not rs:
            continue
        d = (pk.get('deathT') or {}).get(p, -1)
        ll = (T.get('lastLog') or {}).get(p)
        # lastLog 已经是「最后一条快照 + 89」（tools/export_traces.py），这里不再加
        end = min(t1, d if d >= 0 else 10 ** 9, ll if ll is not None and ll >= 0 else 10 ** 9)
        if end <= t0:
            continue
        tot += end - t0
        last = max(rs, key=lambda x: x[1])
        if last[1] - last[0] - 12 > 28 and last[1] < end:
            blind += end - max(t0, last[1])
    share = blind / tot if tot else 0
    ratio = r['arms']['baseline']['terr1'] / r['history']['terr1']
    if share >= 0.05 or ratio < 0.9 or ratio > 1.1:
        tag = os.path.basename(f)[:-5]
        strat = tag.split('-')[2]
        lines.append((mid, t0, r['lenAsked'], strat))
out = os.path.join(HERE, 'hold_list.txt')
rows = [f"{mid}-{t0:04d}-{how} {mid} {t0} {ln} {strat} C2:after={how}" for how in ('hold', 'cut') for (mid, t0, ln, strat) in lines]
tmp = out + '.tmp'
with open(tmp, 'w') as fh:
    fh.write('# 标签 局 t0 窗口长 当年版本 通道（tools/hold_list.py 生成）\n' + '\n'.join(rows) + '\n')
os.replace(tmp, out)
print(f'hold_list.txt {len(rows)} 行（{len(lines)} 个运行 × 2 种对照）')
