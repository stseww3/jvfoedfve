#!/usr/bin/env python3
# 用法：python3 scripts/mdnums.py <mid> [--all]
# 把 reviews/<mid>.md 里的每个数字记号（含千分位、小数）拿去和本局的笔记、卷宗、追踪输出逐字比对，
# 列出「哪儿都找不到」的记号及所在行——这些要么是手算的，要么是写错的，逐个人工核对。
# 只做字面比对：246.3 万 与 2,463,000 不会互相匹配，所以没列出来不等于对，列出来也不等于错。
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOK = re.compile(r"\d[\d,]*(?:\.\d+)?")


def norm(tok):
    return tok.replace(",", "").rstrip(".")


def main():
    mid = sys.argv[1]
    show_all = "--all" in sys.argv
    md = open(os.path.join(ROOT, "reviews", f"{mid}.md"), encoding="utf-8").read().split("\n")
    srcs = [os.path.join(ROOT, "scripts", "notes", f"{mid}.py")]
    srcs += sorted(glob.glob(os.path.join(ROOT, "out", "dossier", f"{mid}*")))
    srcs += sorted(glob.glob(os.path.join(ROOT, "out", "trace", f"{mid}-*")))
    notes_set, other_set = set(), set()
    for i, p in enumerate(srcs):
        if not os.path.exists(p):
            continue
        txt = open(p, encoding="utf-8", errors="replace").read()
        toks = {norm(t) for t in TOK.findall(txt)}
        (notes_set if i == 0 else other_set).update(toks)
    miss = 0
    for ln, line in enumerate(md, 1):
        if line.startswith("```") or line.startswith("node ") or line.startswith("python3 "):
            continue
        bad, weak = [], []
        for t in TOK.findall(line):
            n = norm(t)
            if len(n) < 2 and "." not in n:
                continue
            if n in notes_set:
                continue
            if n in other_set:
                weak.append(t)
            else:
                bad.append(t)
        if bad or (show_all and weak):
            miss += len(bad)
            print(f"L{ln}: 找不到 {bad}" + (f"；只在卷宗/追踪里 {weak}" if show_all and weak else ""))
            print("    " + line[:150])
    print(f"# {mid}: {miss} 个记号在笔记、卷宗、追踪里都找不到")


if __name__ == "__main__":
    main()
