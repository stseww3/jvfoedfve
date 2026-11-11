#!/usr/bin/env python3
"""05_grep_min.py — 在压缩成长行的 JS 里按关键字取上下文片段（不整段读入上下文）。

用法：
  python3 05_grep_min.py <file> <regex> [before=300] [after=600] [max=10]

输出：每个命中一段：#<序号> @<字符偏移>（行号:列号），前后各取若干字符。
注意：只用来读策略层 / 评估层的片段；连接握手、验证、代理相关的代码不看（LIAISON §9）。
"""
import re
import sys

path, pat = sys.argv[1], sys.argv[2]
before = int(sys.argv[3]) if len(sys.argv) > 3 else 300
after = int(sys.argv[4]) if len(sys.argv) > 4 else 600
mx = int(sys.argv[5]) if len(sys.argv) > 5 else 10

text = open(path, encoding="utf-8", errors="replace").read()
line_starts = [0]
for m in re.finditer("\n", text):
    line_starts.append(m.end())


def linecol(off):
    import bisect
    i = bisect.bisect_right(line_starts, off) - 1
    return i + 1, off - line_starts[i] + 1


n = 0
for m in re.finditer(pat, text):
    n += 1
    if n > mx:
        continue
    s, e = max(0, m.start() - before), min(len(text), m.end() + after)
    ln, col = linecol(m.start())
    print(f"#{n} @{m.start()} (line {ln}, col {col})")
    print(text[s:e].replace("\n", "\n    "))
    print("-" * 60)
print(f"# total matches: {n}")
