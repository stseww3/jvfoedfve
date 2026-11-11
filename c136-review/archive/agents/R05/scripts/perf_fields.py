#!/usr/bin/env python3
# perf_fields.py — 策略自己每拍花多少时间：[HL-TICK] 行尾的 avgMs / maxMs / skip（window.__hlPerf，策略 act() 的累计耗时）。
#   用途：给「指令延迟」排除一个原因——如果策略每拍只花 1 毫秒左右、skip=0，那么几百拍的延迟不是策略算得慢造成的。
#   口径：每条 [HL-TICK] 一行（每号每 90 拍一条）；avgMs = 累计耗时 ÷ 累计拍数；maxMs = 开局以来单拍最大耗时；skip = 被跳过的拍数。
#         按本地拍分段（0–600 / 600–1500 / 1500–3000 / 3000+）列：行数、avgMs 中位与最大、maxMs 的最大、skip 的最大。
#   B 组对局先跑 scripts/alias_overlay.py <局> 并加 C136_DATA=/tmp/c136-r05/overlay。
# 用法：python3 scripts/perf_fields.py <局…> [--by-bot] [--tsv]
import os, re, sys, statistics as st, collections
DATA = os.environ.get('C136_DATA', '/agent/repos/c136-data')
ids = [a for a in sys.argv[1:] if not a.startswith('--')]
BYBOT = '--by-bot' in sys.argv; TSV = '--tsv' in sys.argv
PER = [(0, 600, '0–600'), (600, 1500, '600–1500'), (1500, 3000, '1500–3000'), (3000, 10 ** 9, '3000+')]
rx = re.compile(r'\[([^\]]+)\] \[HL-TICK\] t=(\d+) .*?avgMs=([\d.]+) maxMs=([\d.]+) skip=(\d+)')
if TSV: print('\t'.join(['match', 'period', 'lines', 'avgMsP50', 'avgMsMax', 'maxMsMax', 'skipMax', 'bots']))
for mid in ids:
    d = DATA if os.path.exists(f'{DATA}/bundles/{mid}/in_game.log') else '/agent/repos/c136-data'
    rows = []; ticks = 0
    for ln in open(f'{d}/bundles/{mid}/in_game.log', encoding='utf-8', errors='replace'):
        if '[HL-TICK]' in ln: ticks += 1
        m = rx.search(ln)
        if m: rows.append((m.group(1), int(m.group(2)), float(m.group(3)), float(m.group(4)), int(m.group(5))))
    if not TSV: print(f'== {mid}: [HL-TICK] {ticks} 行，其中带 avgMs/maxMs/skip 的 {len(rows)} 行，{len({r[0] for r in rows})} 个号 ==')
    for a, b, lab in PER:
        rr = [r for r in rows if a <= r[1] < b]
        if not rr: continue
        if TSV:
            print('\t'.join(map(str, [mid, lab, len(rr), round(st.median(r[2] for r in rr), 2), max(r[2] for r in rr), max(r[3] for r in rr), max(r[4] for r in rr), len({r[0] for r in rr})])))
        else:
            print(f'   {lab}: {len(rr)} 行｜avgMs 中位 {st.median(r[2] for r in rr):.2f}、最大 {max(r[2] for r in rr):.2f}｜maxMs 最大 {max(r[3] for r in rr):.1f}｜skip 最大 {max(r[4] for r in rr)}')
    if BYBOT and not TSV:
        by = collections.defaultdict(list)
        for r in rows: by[r[0]].append(r)
        for bot, rr in by.items():
            last = max(rr, key=lambda r: r[1])
            print(f'      {bot}: {len(rr)} 行，最后一条 t={last[1]} avgMs={last[2]} maxMs={last[3]} skip={last[4]}｜avgMs 最大 {max(r[2] for r in rr)}')
