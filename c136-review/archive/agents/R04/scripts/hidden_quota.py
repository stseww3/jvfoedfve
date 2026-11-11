#!/usr/bin/env python3
"""hidden_quota.py — 从捐款对账表反推“收款人配额里有多少点不是捐款指令用掉的”。

背景：引擎里只有两处会消耗收款人的配额点：真人捐款指令、船靠岸到队友地上时的移交（规格书 B 第 8.5 节）。
对账表（donation_ledger.py --tsv）按录像里的捐款指令累加了每个收款人的已用点数 used。
若某收款人还有一部分看不见的占用 H（船移交），那么：
   每一笔被接受的捐款要求  used + H + cost <= cap  →  H <= cap - used - cost
   每一次被拒的发起要求    used + H + cost >  cap  →  H >= cap - used - cost + 1
本脚本对每个收款人、按时间顺序给出 H 的下界（来自被拒）和上界（来自被接受），并报告两者是否相容。
只用 t<4284（之后不查配额）且金额不受“收款方到顶”影响的行。

用法：cd c136-review/agents/R04 && timeout 120 python3 scripts/hidden_quota.py out/ledger/A047.donations.tsv [...]
"""
import csv
import sys
from collections import defaultdict

for path in sys.argv[1:]:
    rows = list(csv.DictReader(open(path, encoding='utf8'), delimiter='\t'))
    by = defaultdict(list)
    for r in rows:
        te = int(r['execTick'])
        if te >= 4284 or r['v'] in ('None', '') or r['why'] == '收款方到顶':
            continue
        slack = int(r['cap']) - int(r['usedBefore']) - int(r['cost'])
        by[r['qname']].append((te, r['accepted'] == 'True', slack, r['bot'], int(r['cost']), int(r['cap']), int(r['usedBefore'])))
    print(f'== {path}')
    for q, arr in sorted(by.items()):
        arr.sort()
        unexplained = sum(1 for te, acc, slack, *_ in arr if not acc and slack >= 0)
        if unexplained < 3:
            continue
        # 逐段：在第 k 笔被接受之前的所有被拒，给出下界；该笔被接受给出上界
        print(f'  收款人 {q}：公式（只算捐款指令）解释不了的拒单 {unexplained} 次')
        lo, lo_row = 0, None
        for te, acc, slack, bot, cost, cap, used in arr:
            if not acc:
                if slack + 1 > lo:
                    lo, lo_row = slack + 1, (te, bot, cost, cap, used)
            else:
                hi = slack
                state = '相容' if lo <= hi else '不相容'
                if lo > 0:
                    print(f'    到 t={te} 这笔被接受（{bot}，需 {cost} 点，上限 {cap}，捐款已用 {used}）为止：看不见的占用 H ∈ [{lo}, {hi}] → {state}'
                          + (f'；下界来自 t={lo_row[0]} {lo_row[1]} 被拒（需 {lo_row[2]} 点，上限 {lo_row[3]}，捐款已用 {lo_row[4]}）' if lo_row else ''))
        if lo > 0:
            print(f'    全程下界：H >= {lo}')
