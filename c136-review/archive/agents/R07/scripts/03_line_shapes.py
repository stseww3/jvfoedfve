#!/usr/bin/env python3
"""03_line_shapes.py — 列出日志（全部 10 局的策略层行）里出现过的全部句式。

用法：
  python3 03_line_shapes.py <raw_dir> > out/common/line_shapes.txt

做法：只看策略层 / 评估层的行（[HL-*]、[BACKEND-SPAWN-COORD]、[OPENING-CHECK]、[RESULT]、[HOT-IMPORT]、ERROR: Strategy）。
把数字换成 N、把 "(<name>)" 里的名字换成 (NAME)，得到句式；统计每种句式的条数和首次出现的原始行号，并给一条原文样例。
用途：写解析器之前确认没有漏掉的句式变体。
"""
import re
import sys
from collections import OrderedDict

raw = sys.argv[1] if len(sys.argv) > 1 else "/tmp/c136-r07/raw"
path = f"{raw}/G01-G09-squad.log"
BOT_PREFIX = re.compile(r"^\[\[Nope\] ([A-Za-z0-9_]+)\] ?(.*)$", re.S)
KEEP_PREFIX = ("[HL-", "[BACKEND-SPAWN-COORD]", "[OPENING-CHECK", "[RESULT", "[HOT-IMPORT]", "ERROR: Strategy")

shapes = OrderedDict()
with open(path, encoding="utf-8", errors="replace") as f:
    for ln, line in enumerate(f, 1):
        line = line.rstrip("\n")
        m = BOT_PREFIX.match(line)
        body = m.group(2) if m else line
        if not body.startswith(KEEP_PREFIX):
            continue
        s = body
        if s.startswith("[BACKEND-SPAWN-COORD]"):
            s = s.split("):")[0] + "): …"
        if s.startswith("[OPENING-CHECK"):
            s = re.sub(r"\] .*", "] …", s, count=1)
        if s.startswith("[RESULT"):
            s = re.sub(r"^\[RESULT [^\]]*\] [^\]]*\]", "[RESULT BOT]", s) if s.startswith("[RESULT [") else s
            s = re.sub(r"team=\{.*\}", "team={…}", s)
        s = re.sub(r"\((?:[^()]|\([^()]*\))*\)(?=\s|$)", lambda mm: mm.group(0) if re.fullmatch(r"\([\d.,%~xpx= A-Za-z/]*\)", mm.group(0)) and not re.search(r"[A-Za-z]{3,}", mm.group(0).replace("max", "").replace("map", "")) else "(NAME)", s)
        s = re.sub(r"-?\d+(?:\.\d+)?", "N", s)
        e = shapes.get(s)
        if e is None:
            shapes[s] = e = {"n": 0, "first": ln, "sample": line[:300]}
        e["n"] += 1

print(f"# distinct shapes={len(shapes)}")
for s, e in sorted(shapes.items(), key=lambda kv: (kv[0].split("]")[0], -kv[1]["n"])):
    print(f"{e['n']}\t{e['first']}\t{s[:230]}\n\t\t例: {e['sample']}")
