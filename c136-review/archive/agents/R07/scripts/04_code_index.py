#!/usr/bin/env python3
"""04_code_index.py — 给一个 JS 源文件做函数索引和日志句式定位。

用法：
  python3 04_code_index.py <js_file> > out/common/code_index.<name>.txt

输出两段：
  [FUNCS] 行号\t缩进\t函数签名（class 声明、两格缩进的类方法、function 声明、const x = function / =>）
  [LOGS]  行号\t出现 HL- / console.log / emit 的行（截断）
只做文本匹配，不解析语法；用于给后面的切片阅读定位。
"""
import re
import sys

path = sys.argv[1]
FUNC = re.compile(
    r"^(\s*)(?:async\s+)?function\s*\*?\s*([A-Za-z0-9_$]+)\s*\(([^)]*)\)"
    r"|^(\s*)(?:const|let|var)\s+([A-Za-z0-9_$]+)\s*=\s*(?:async\s*)?(?:function\b|\(([^)]*)\)\s*=>|[A-Za-z0-9_$]+\s*=>)")
CLASS = re.compile(r"^(\s*)(?:export\s+)?class\s+([A-Za-z0-9_$]+)(?:\s+extends\s+([A-Za-z0-9_$.]+))?")
METHOD = re.compile(r"^(  )(?:static\s+|async\s+|get\s+|set\s+)*([A-Za-z_$][A-Za-z0-9_$]*)\s*\(([^)]*)\)\s*\{\s*$")
KEYWORDS = {"if", "for", "while", "switch", "catch", "function", "return"}
LOG = re.compile(r"\[HL-|console\.(log|warn|error)|\[BACKEND|\[OPENING|ERROR: ")

funcs = []
logs = []
with open(path, encoding="utf-8", errors="replace") as f:
    for ln, line in enumerate(f, 1):
        s = line.rstrip("\n")
        c = CLASS.match(s)
        if c:
            funcs.append((ln, len(c.group(1)), f"class {c.group(2)}" + (f" extends {c.group(3)}" if c.group(3) else "")))
        mm = METHOD.match(s)
        if mm and mm.group(2) not in KEYWORDS:
            funcs.append((ln, 2, f"  .{mm.group(2)}({mm.group(3).strip()[:80]})"))
        m = FUNC.match(s)
        if m:
            indent = len(m.group(1) if m.group(1) is not None else m.group(4))
            name = m.group(2) or m.group(5)
            args = m.group(3) if m.group(3) is not None else (m.group(6) or "")
            funcs.append((ln, indent, f"{name}({args.strip()[:80]})"))
        if LOG.search(s):
            logs.append((ln, s.strip()[:240]))

print(f"# file={path}")
print("[FUNCS]")
for ln, indent, sig in funcs:
    print(f"{ln}\t{indent}\t{sig}")
print()
print("[LOGS]")
for ln, s in logs:
    print(f"{ln}\t{s}")
