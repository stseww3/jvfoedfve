#!/usr/bin/env python3
"""mids_tally.py — 汇总 shadow.mjs --mids <函数> 的「分支命中」行：按号、按时间段统计各出口行与途中 continue/break 行的命中数。

用法：
  python3 scripts/mids_tally.py <shadow --mids 的输出文件>... [--fn buyLand] [--t0 1500] [--t1 99999] [--lines 5359,5364,5447,5452] [--per-window]
输出：每个号在 [t0,t1) 内的调用数、出口行分布、指定 continue 行的命中数（「按拍去重」口径，与 shadow.mjs 一致）。
"""
import re
import sys
from collections import Counter, defaultdict

args = sys.argv[1:]


def val(k, d=None):
    return args[args.index(k) + 1] if k in args else d


files = [a for i, a in enumerate(args) if not a.startswith('--') and (i == 0 or args[i - 1] not in ('--fn', '--t0', '--t1', '--lines'))]
fn = val('--fn', 'buyLand')
t0, t1 = int(val('--t0', 0)), int(val('--t1', 10 ** 9))
want = [int(x) for x in val('--lines', '').split(',') if x]
per_window = '--per-window' in args


def num(x):
    # 出口标签除了行号还有 'end'（函数走到末尾没有显式 return）
    return int(x) if x.isdigit() else x


rx = re.compile(r'^\[分支命中 (\S+)\] (\S+) t=(\d+)[–-](\d+) 调用 (\d+) 次｜出口行 ([^｜]*)(?:｜途中 continue 行（按拍去重）(.*))?$')
calls = Counter()
exits = defaultdict(Counter)
mids = defaultdict(Counter)
rows = []
for f in files:
    for line in open(f, encoding='utf-8', errors='replace'):
        m = rx.match(line.rstrip('\n'))
        if not m:
            continue
        tag, who = m.group(1), m.group(2)
        if '@' in who:   # --mids 一次给了多个函数时，行里是「函数@号」
            f1, who = who.split('@', 1)
            if f1 != fn:
                continue
        elif tag != fn:
            continue
        bot, a, b, n = who, int(m.group(3)), int(m.group(4)), int(m.group(5))
        if a < t0 or a >= t1:
            continue
        ex = Counter({num(x.split('×')[0]): int(x.split('×')[1]) for x in m.group(6).split() if '×' in x})
        md = Counter({num(x.split('×')[0]): int(x.split('×')[1]) for x in (m.group(7) or '').split() if '×' in x})
        calls[bot] += n
        exits[bot].update(ex)
        mids[bot].update(md)
        rows.append((bot, a, b, n, ex, md))
print(f'[{fn} 分支命中汇总] t∈[{t0},{t1 if t1 < 10 ** 9 else "末"}）；continue 行按拍去重')
tot_calls, tot_ex, tot_md = 0, Counter(), Counter()
for bot in calls:
    tot_calls += calls[bot]
    tot_ex.update(exits[bot])
    tot_md.update(mids[bot])
    md = mids[bot]
    show = want or [k for k, _ in md.most_common(6)]
    print(f"  {bot:8s} 调用 {calls[bot]:5d}｜出口 " + ' '.join(f'{k}×{v}' for k, v in exits[bot].most_common(5)) + '｜途中 ' + ' '.join(f'{k}×{md.get(k, 0)}' for k in show))
show = want or [k for k, _ in tot_md.most_common(8)]
print(f"  合计     调用 {tot_calls:5d}｜出口 " + ' '.join(f'{k}×{v}' for k, v in tot_ex.most_common(6)) + '｜途中 ' + ' '.join(f'{k}×{tot_md.get(k, 0)}' for k in show))
if per_window:
    for bot, a, b, n, ex, md in rows:
        show = want or [k for k, _ in md.most_common(6)]
        print(f"    {bot:8s} {a:5d}–{b:<5d} 调用 {n:4d}｜出口 " + ' '.join(f'{k}×{v}' for k, v in ex.most_common(4)) + '｜途中 ' + ' '.join(f'{k}×{md.get(k, 0)}' for k in show))
