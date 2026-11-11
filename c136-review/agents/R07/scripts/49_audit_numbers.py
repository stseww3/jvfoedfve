#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""49_audit_numbers.py — R07：成稿前自查「没有脚本的数字不收」。

把 review_src/<matchId>.py 里所有 ≥4 位的数字（带逗号或不带逗号）拿出来，看它是否在
  out/<matchId>/ 的某个输出文件、bundles/<matchId>/ 的某个文件、或者策略 / 引擎源码的行号范围里出现过。
找不到的逐个列出来（数值 + 源文件行号）。剩下的应该只有两类：
  (a) 用打印出来的数做的加减乘除（文中要把算式写出来）；(b) 源码行号。
其余的都要回到输出里核对，或者补脚本。

用法：python3 49_audit_numbers.py <matchId> [--max-line 6000]
  --max-line：不超过这个值、且紧跟在 L / ：L / : 后面的数按源码行号处理，不列（默认 6000）
输出：只打印到终端（不写文件）。
"""
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = '/agent/repos/c136-data'
NUM = re.compile(r'(?<![\d,.])(\d{1,3}(?:,\d{3})+|\d{4,})(?![\d,])')


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    mid = sys.argv[1]
    a = sys.argv[2:]
    max_line = int(a[a.index('--max-line') + 1]) if '--max-line' in a else 6000
    src_path = os.path.join(HERE, 'review_src', f'{mid}.py')
    nums = {}
    for ln, line in enumerate(open(src_path, encoding='utf-8').read().split('\n'), 1):
        # 复现命令里的参数（时间点、切分）不算正文里的数字
        if 'run-heavy.sh' in line or line.strip().startswith(('"python3 ', 'f"python3 ', '"--trace ', '"bash ', 'f"bash ')):
            continue
        for m in NUM.finditer(line):
            v = int(m.group(1).replace(',', ''))
            if v < 1000:
                continue
            pre = line[max(0, m.start() - 2):m.start()]
            if v <= max_line and (pre.endswith('L') or pre.endswith('-') and re.search(r'L\d+-$', line[max(0, m.start() - 8):m.start()])):
                continue
            nums.setdefault(v, []).append(ln)
    seen = set()
    n_files = 0
    paths = sorted(glob.glob(os.path.join(HERE, '..', 'out', mid, '*'))) + sorted(glob.glob(os.path.join(DATA, 'bundles', mid, '*')))
    for p in paths:
        if not os.path.isfile(p) or os.path.getsize(p) > 80_000_000:
            continue
        try:
            txt = open(p, encoding='utf-8', errors='ignore').read()
        except OSError:
            continue
        n_files += 1
        for x in NUM.findall(txt):
            seen.add(int(x.replace(',', '')))
    miss = sorted((v, l) for v, l in nums.items() if v not in seen)
    print(f'{mid}：正文里 {len(nums)} 个不同的 ≥4 位数；对照 {n_files} 个文件；{len(miss)} 个找不到：')
    for v, l in miss:
        print(f'  {v:,}\t行 {",".join(str(x) for x in sorted(set(l))[:8])}')


if __name__ == '__main__':
    main()
