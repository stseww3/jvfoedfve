#!/usr/bin/env python3
"""md_join.py — 把叙述版 .md 里手工折行的段落并回一行（collect-reviews 按换行数卡 150 行上限，折行不该占名额）。

    python3 c136-review/agents/R08/scripts/md_join.py reviews/G02.md

规则：当前行与下一行都不是空行/表格行/标题行，且下一行不是新的列表项或编号项时，把下一行并到当前行尾。
"""
import re
import sys


def is_block_start(line):
    s = line.lstrip()
    return (not s) or s.startswith(("#", "|", "- ", "* ", "```", ">")) or re.match(r"\d+\.\s", s) is not None


def join(text):
    out = []
    for line in text.split("\n"):
        if out and out[-1].strip() and not out[-1].lstrip().startswith(("#", "|", "```")) and not is_block_start(line):
            out[-1] = out[-1].rstrip() + line.strip()
        else:
            out.append(line)
    return "\n".join(out)


if __name__ == "__main__":
    for p in sys.argv[1:]:
        s = open(p, encoding="utf-8").read()
        t = join(s)
        open(p, "w", encoding="utf-8").write(t)
        print(f"{p}: {s.count(chr(10))} -> {t.count(chr(10))} 行")
