#!/usr/bin/env python3
"""accounts_insert.py — 把 accounts_md.py 渲染出的「三本账」一节写进 reviews/<局>.md。

- 已有同名小节（标题以 '## 6b.' 开头）就整节替换；否则插在 --before 指定的标题行之前（默认 '## 7.'）。
- 「复现」一节末尾补上三本账的脚本名（只补一次）。
- 写完打印行数（collect-reviews.py 的硬上限是 160 个换行）。

用法：python3 scripts/accounts_insert.py <局> [--before '## 7.'] [--note '只在这一局成立的口径说明']
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from accounts_md import render  # noqa: E402

a = sys.argv[1:]
mid = a[0]
before = a[a.index('--before') + 1] if '--before' in a else '## 7.'
note = a[a.index('--note') + 1] if '--note' in a else None
TITLE = '## 6b. 延迟硬账、好地账、600–1500 拍三层归因（广播 0007；数字全部来自脚本）'
REPRO = '三本账：`replay_cmds.mjs` → `shadow.mjs {m} --quiet --tc 600:1500 --json` → `atk_fate.mjs` → `delay_account.py {m}`（明细 `delay_detail.py {m}`）、`land_account.mjs {m}`、`tick_attrib.py {m} --by-bot --exits`、`quota_guard.py {m}`；`accounts_md.py {m}` 渲染 6b 节。'

J = json.load(open(os.path.join(HERE, '..', 'reviews', f'{mid}.json')))
if note:
    J = dict(J); J['accountsNote'] = note
block = render(mid, J, TITLE)
p = os.path.join(HERE, '..', 'reviews', f'{mid}.md')
lines = open(p, encoding='utf-8').read().split('\n')
# 去掉旧的 6b 节
i0 = next((i for i, l in enumerate(lines) if l.startswith('## 6b.')), None)
if i0 is not None:
    i1 = next(i for i in range(i0 + 1, len(lines)) if lines[i].startswith('## '))
    del lines[i0:i1]
ib = next((i for i, l in enumerate(lines) if l.startswith(before)), None)
if ib is None:
    sys.exit(f'找不到标题 {before!r}')
lines[ib:ib] = block + ['']
txt = '\n'.join(lines)
r = REPRO.format(m=mid)
if '三本账：' not in txt:
    # 复现一节：最后一个非空行后面接上
    j = max(i for i, l in enumerate(lines) if l.strip())
    lines[j] = lines[j].rstrip() + (' ' if not lines[j].rstrip().endswith('。') else '') + r
    txt = '\n'.join(lines)
open(p, 'w', encoding='utf-8').write(txt)
print(f'{mid}.md: {txt.count(chr(10))} 行；6b 节 {len(block)} 行，插在 {before!r} 之前')
