#!/usr/bin/env python3
"""notesnums.py — 核对手写笔记（或任意一份文字）里的数字能不能在本局的脚本输出里找到。

mdnums.py 只核 reviews/<mid>.md，而且把笔记本身当出处；这个脚本反过来核笔记：
笔记里的每个数字记号必须能在 out/dossier/<mid>*、out/trace/<mid>-* 里找到，找法依次是
  1) 字面相同（去掉千分位）；
  2) 后面跟着「万」：换成卷宗的 k / M 写法再找（16.7 万 → 167k，190 万 → 1.90M，1,912 万 → 19.12M，0.9 万 → 9.0k）；
  3) 后面跟着「千」：换成 k（3.7 千 → 3.7k）；
  4) 后面跟着 %：再试「去掉 % 的小数」（0.2372 ↔ 23.72%）。
不核的：源码行号（L1234、L1234-1250）、模式/对局编号（A041、R03、AT08…）、一位整数。
用法：python3 scripts/notesnums.py <mid> [文件路径]      默认核 scripts/notes/<mid>.py
只做字面比对：列出来不等于错（可能是手算的合计或换了写法），没列出来也不等于对。
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOK = re.compile(r"\d[\d,]*(?:\.\d+)?")
SKIP = re.compile(r"L\d+(?:\s*[-~]\s*\d+)?|[A-Za-z_]+\d+[A-Za-z_]*\d*|\d+[a-z]{2,}\b")


def norm(tok):
    return tok.replace(",", "").rstrip(".")


def wan_forms(n):
    """n 是「万」前面的记号（字符串）。返回卷宗里可能的 k / M 写法。"""
    try:
        v = float(n) * 10000
    except ValueError:
        return []
    dec = len(n.split(".")[1]) if "." in n else 0
    out = set()
    kv = v / 1000
    out.add("%.0fk" % kv)
    out.add("%.1fk" % kv)
    mv = v / 1e6
    out.add("%.2fM" % mv)
    out.add("%.1fM" % mv)
    if dec == 0 and v >= 1e6:
        out.add("%.2fM" % mv)
    return sorted(out)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    mid = sys.argv[1]
    path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "scripts", "notes", f"{mid}.py")
    srcs = sorted(glob.glob(os.path.join(ROOT, "out", "dossier", f"{mid}*")))
    srcs += sorted(glob.glob(os.path.join(ROOT, "out", "trace", f"{mid}-*")))
    raw = ""
    for p in srcs:
        raw += open(p, encoding="utf-8", errors="replace").read() + "\n"
    lit = {norm(t) for t in TOK.findall(raw)}
    km = set(re.findall(r"\d[\d,]*(?:\.\d+)?[kM]", raw))
    miss = 0
    for ln, line in enumerate(open(path, encoding="utf-8").read().split("\n"), 1):
        body = SKIP.sub(" ", line)
        bad = []
        for m in TOK.finditer(body):
            n = norm(m.group(0))
            if len(n) < 2 and "." not in n:
                continue
            if n in lit:
                continue
            tail = body[m.end():m.end() + 2].lstrip()
            if tail.startswith("万") and any(f in km for f in wan_forms(n)):
                continue
            if tail.startswith("千") and (n + "k") in km:
                continue
            if tail.startswith("%"):
                try:
                    f = float(n) / 100
                    if any(("%.*f" % (d, f)) in lit for d in (2, 3, 4)):
                        continue
                except ValueError:
                    pass
            bad.append(m.group(0) + ("万" if tail.startswith("万") else "千" if tail.startswith("千") else ""))
        if bad:
            miss += len(bad)
            print(f"L{ln}: {bad}")
            print("    " + line.strip()[:170])
    print(f"# {mid}: {os.path.relpath(path, ROOT)} 里 {miss} 个记号在卷宗、追踪里找不到对应写法")


if __name__ == "__main__":
    main()
