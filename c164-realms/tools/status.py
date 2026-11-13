#!/usr/bin/env python3
"""Count the cards of plan/STATUS.md by status and keep its summary line right.

    status.py            print the counts; exit 1 when the summary line says something else
    status.py --fix      rewrite the numbers of the summary line

A card is a row of a table whose header has the columns 包 and 状态. The summary line is the one
that starts with "**汇总"; what stands before "：共" (up to which message the table is current)
is left alone.
"""
import os
import re
import sys

PATH = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "plan", "STATUS.md"))
ORDER = ["待领", "制作中", "已交付", "已合并", "已出图", "暂过", "已过审", "退回"]


def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def main():
    with open(PATH, encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    counts, col, unknown = {s: 0 for s in ORDER}, None, []
    for line in lines:
        if not line.startswith("|"):
            col = None
            continue
        row = cells(line)
        if "包" in row and "状态" in row:
            col = row.index("状态")
        elif col is not None and not set("".join(row)) <= set("-: "):
            if row[col] in counts:
                counts[row[col]] += 1
            else:
                unknown.append(line)
    total = sum(counts.values())
    summary = f"共 {total} 张卡 —— " + "，".join(f"{s} {counts[s]}" for s in ORDER) + "。**"
    print(summary.rstrip("*"))
    for line in unknown:
        print("unknown status:", line)
    at = next((i for i, line in enumerate(lines) if line.startswith("**汇总")), None)
    if at is None:
        sys.exit("no summary line (**汇总 ...) in " + PATH)
    want = re.sub(r"共 .*$", summary, lines[at]) if "共 " in lines[at] else lines[at]
    if want != lines[at]:
        if "--fix" not in sys.argv:
            sys.exit("the summary line is out of date; run with --fix")
        lines[at] = want
        with open(PATH, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
        print("summary line rewritten")
    sys.exit(1 if unknown else 0)


if __name__ == "__main__":
    main()
