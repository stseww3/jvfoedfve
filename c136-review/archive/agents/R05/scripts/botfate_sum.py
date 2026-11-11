#!/usr/bin/env python3
"""botfate_sum.py — 汇总 bot_fate.mjs 的输出：被跟踪的机器人的地最后归了谁（按类别合计）。

类别：我方号（行里带「我方 」前缀）/ 其他真人（名字后面带 #编号、不以「机器人#」开头）/ 别的机器人 / 变中立（机器人被除名时剩下的地）。
另给出每个真人拿走的合计（前 8）和每个我方号拿走的合计。
用法：python3 scripts/botfate_sum.py <bot_fate 输出文件> [--at 1200]   （--at：顺带合计这些机器人在该采样拍的地）
"""
import re
import sys
from collections import Counter

a = sys.argv[1:]
f = a[0]
at = a[a.index('--at') + 1] if '--at' in a else None
cat = Counter()
who = Counter()
ours = Counter()
land_at = 0
n = 0
for line in open(f, encoding='utf-8'):
    line = line.strip()
    m = re.match(r'#(\d+)（机器人）', line)
    if m:
        n += 1
        if at:
            mm = re.search(rf'{at}: (\d+) 格', line)
            if mm:
                land_at += int(mm.group(1))
        continue
    if not line.startswith('被拿走'):
        continue
    body = line.split('：', 1)[1]
    for part in body.split('、'):
        mm = re.match(r'(.+?) (\d+)（', part)
        if not mm:
            continue
        name, v = mm.group(1).strip(), int(mm.group(2))
        if name == '变中立':
            cat['变中立'] += v
        elif name.startswith('我方 '):
            cat['我方号'] += v
            ours[name[3:]] += v
        elif name.startswith('机器人#'):
            cat['别的机器人'] += v
        else:
            cat['其他真人'] += v
            who[name] += v
tot = sum(cat.values())
print(f'[机器人去向汇总] {f.split("/")[-1]}：跟踪 {n} 个机器人' + (f'，t={at} 时合计 {land_at} 格' if at else '') + f'｜被拿走合计 {tot} 格')
for k in ('我方号', '其他真人', '别的机器人', '变中立'):
    print(f'   {k} {cat[k]} 格（{100 * cat[k] / max(1, tot):.0f}%）')
print('   其他真人前 8：' + '、'.join(f'{k} {v}' for k, v in who.most_common(8)))
print('   我方号：' + '、'.join(f'{k} {v}' for k, v in ours.most_common()))
