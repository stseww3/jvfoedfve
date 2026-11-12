#!/usr/bin/env python3
"""crossnums.py — 核对跨局报告、假设卡、会审报告里的数字能不能在脚本输出里找到（字面比对）。

默认出处：out/cross/*.txt（crosstab.py 的表）、out/dossier/ledger-table.md、out/batch-compare.txt。
--src <路径或通配> 可以再加出处（可重复）：比如模式定义 scripts/notes/_patterns.py、机制规格书 reports/MECHANICS-A.md、
策略与引擎源码（核对源码常数用）。
找法：1) 字面相同（去掉千分位）；2) 后面跟着 % 时再试「去掉 % 的小数」（0.2372 ↔ 23.72%）；
      3) 后面跟着「万」「千」时再试 k / M 写法（16.7 万 → 167k，190 万 → 1.90M）。
不核的：源码行号（L1234、L1234-1250）、带字母的编号（A041、R03、AT08、X10、E2、G0、H01、P50、t0…）、一位整数。
只做字面比对：列出来不等于错（可能是换了写法），没列出来也不等于对。

用法：python3 scripts/crossnums.py <文件> [<文件> …] [--src <路径或通配> …]
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOK = re.compile(r"\d[\d,]*(?:\.\d+)?")
SKIP = re.compile(r"L\d+(?:\s*[-~]\s*\d+)?|[A-Za-z_]+[-]?\d+[A-Za-z_]*\d*|\d+[a-z]{2,}\b")
DEFAULT = ["out/cross/*.txt", "out/dossier/ledger-table.md", "out/batch-compare.txt"]


def norm(tok):
    return tok.replace(",", "").rstrip(".")


def wan_forms(n):
    try:
        v = float(n) * 10000
    except ValueError:
        return []
    return sorted({"%.0fk" % (v / 1000), "%.1fk" % (v / 1000), "%.2fM" % (v / 1e6), "%.1fM" % (v / 1e6)})


def main():
    args = sys.argv[1:]
    files, srcs = [], list(DEFAULT)
    i = 0
    while i < len(args):
        if args[i] == "--src":
            srcs.append(args[i + 1])
            i += 2
        else:
            files.append(args[i])
            i += 1
    if not files:
        print(__doc__)
        sys.exit(2)
    raw = ""
    used = []
    for pat in srcs:
        pat_abs = pat if os.path.isabs(pat) else os.path.join(ROOT, pat)
        for p in sorted(glob.glob(pat_abs)):
            raw += open(p, encoding="utf-8", errors="replace").read() + "\n"
            used.append(p)
    lit = {norm(t) for t in TOK.findall(raw)}
    km = set(re.findall(r"\d[\d,]*(?:\.\d+)?[kM]", raw))
    total = 0
    for path in files:
        p_abs = path if os.path.isabs(path) else os.path.join(ROOT, path)
        miss = 0
        for ln, line in enumerate(open(p_abs, encoding="utf-8").read().split("\n"), 1):
            body = SKIP.sub(" ", line)
            bad = []
            for m in TOK.finditer(body):
                n = norm(m.group(0))
                if len(n) < 2 and "." not in n:
                    continue
                if n in lit:
                    continue
                tail = body[m.end():m.end() + 2].lstrip()
                if tail.startswith("%"):
                    try:
                        f = float(n) / 100
                        if any(("%.*f" % (d, f)) in lit for d in (2, 3, 4)):
                            continue
                    except ValueError:
                        pass
                if tail.startswith("万") and any(f in km for f in wan_forms(n)):
                    continue
                if tail.startswith("千") and (n + "k") in km:
                    continue
                bad.append(m.group(0))
            if bad:
                miss += len(bad)
                print(f"{os.path.relpath(p_abs, ROOT)} L{ln}: {bad}")
                print("    " + line.strip()[:160])
        print(f"# {os.path.relpath(p_abs, ROOT)}：{miss} 个数字记号在 {len(used)} 份出处里找不到对应写法")
        total += miss
    return 0


if __name__ == "__main__":
    sys.exit(main())
