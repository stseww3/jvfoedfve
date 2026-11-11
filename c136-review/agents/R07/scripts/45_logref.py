#!/usr/bin/env python3
"""45_logref.py — 按号 / 拍号区间 / 标签列出 in_game.log 的行（带对局包行号，供复盘里的 logRef 引用）。

用法：python3 45_logref.py <matchId> <bot|ALL> <t0> <t1> [TAG ...] [--no-tick] [--max N]
  行号 = 对局包 in_game.log 的行号（grep -n 的那个），复盘里写作「in_game.log L<n>」。
  TAG 例如 HL-DONATE HL-ASSIST HL-INTERCEPT HL-TICK HL-DISPATCH；不给则全部（--no-tick 去掉 HL-TICK）。
"""
import os
import re
import sys

from r07lib import DATA

RE_T = re.compile(r"\bt=(\d+)")
RE_TICK = re.compile(r"@ tick (\d+)")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    mid, bot, t0, t1 = args[0], args[1], int(args[2]), int(args[3])
    tags = args[4:]
    no_tick = "--no-tick" in sys.argv
    mx = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 400
    p = os.path.join(DATA, "bundles", mid, "in_game.log")
    n = 0
    with open(p, encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f, 1):
            line = line.rstrip("\n")
            body = line.split("\t", 1)[1] if "\t" in line else line
            if bot != "ALL" and f"[{bot}]" not in body.split("] ", 1)[0] + "]":
                continue
            m = RE_T.search(body) or RE_TICK.search(body)
            if not m:
                continue
            t = int(m.group(1))
            if t < t0 or t > t1:
                continue
            if tags and not any(tg in body for tg in tags):
                continue
            if no_tick and "[HL-TICK]" in body:
                continue
            print(f"L{i}\t{body[:330]}")
            n += 1
            if n >= mx:
                print(f"... 截断于 {mx} 行")
                break


if __name__ == "__main__":
    main()
