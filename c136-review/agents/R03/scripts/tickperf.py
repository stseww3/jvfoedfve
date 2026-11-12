#!/usr/bin/env python3
# 用法：python3 scripts/tickperf.py <mid> [t0 t1]
# 读 bundles/<mid>/in_game.log 的 HL-TICK 行尾的 avgMs / maxMs / skip（策略每拍的计算耗时与跳拍数），
# 按号、按 300 拍窗口列出来。用来回答「页面落后是不是策略算得慢」：
#   avgMs、maxMs 很小而成交延迟很大 → 慢的不是策略计算（是页面/网络/服务器那一侧）。
# 只读日志，不读重放。
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.environ.get("C136_DATA", "/agent/repos/c136-data")
LINE = re.compile(r"\[(\w+)\] \[HL-TICK\] t=(\d+) .*?avgMs=([\d.]+) maxMs=([\d.]+) skip=(\d+)")


def main():
    mid = sys.argv[1]
    t0 = int(sys.argv[2]) if len(sys.argv) > 3 else 0
    t1 = int(sys.argv[3]) if len(sys.argv) > 3 else 10 ** 9
    path = os.path.join(DATA, "bundles", mid, "in_game.log")
    per = {}
    win = {}
    n = 0
    for ln in open(path, encoding="utf-8", errors="replace"):
        m = LINE.search(ln)
        if not m:
            continue
        bot, t, avg, mx, skip = m.group(1), int(m.group(2)), float(m.group(3)), float(m.group(4)), int(m.group(5))
        if not (t0 <= t <= t1):
            continue
        n += 1
        p = per.setdefault(bot, {"rows": 0, "avg": 0.0, "max": 0.0, "skip": 0, "lastT": 0})
        p["rows"] += 1
        p["avg"] = max(p["avg"], avg)
        p["max"] = max(p["max"], mx)
        p["skip"] = max(p["skip"], skip)
        p["lastT"] = max(p["lastT"], t)
        w = win.setdefault(t // 300 * 300, {"rows": 0, "avg": 0.0, "max": 0.0, "skip": 0})
        w["rows"] += 1
        w["avg"] = max(w["avg"], avg)
        w["max"] = max(w["max"], mx)
        w["skip"] = max(w["skip"], skip)
    rng = f"{t0}~{t1} 拍" if len(sys.argv) > 3 else "整局"
    print(f"# {mid} 策略计算耗时（tickperf.py；in_game.log 的 HL-TICK 行，{rng}，共 {n} 行；avgMs/maxMs 是日志里的累计值，这里取各行里的最大值）")
    print("  号：行数 | avgMs 最大 | maxMs 最大 | skip 最大 | 最后一行的拍号")
    for bot, p in sorted(per.items()):
        print(f"  {bot:<7} {p['rows']:>3} 行 | avgMs ≤ {p['avg']:.2f} | maxMs ≤ {p['max']:.1f} | skip ≤ {p['skip']} | 最后一行 t={p['lastT']}")
    if per:
        print(f"  全队：avgMs ≤ {max(p['avg'] for p in per.values()):.2f}，maxMs ≤ {max(p['max'] for p in per.values()):.1f}，skip ≤ {max(p['skip'] for p in per.values())}")
    print("  每 300 拍窗口（全队）：行数 | avgMs 最大 | maxMs 最大 | skip 最大")
    for t in sorted(win):
        w = win[t]
        print(f"  {t:>5}~{t + 300:<5} {w['rows']:>3} 行 | avgMs ≤ {w['avg']:.2f} | maxMs ≤ {w['max']:.1f} | skip ≤ {w['skip']}")


if __name__ == "__main__":
    main()
