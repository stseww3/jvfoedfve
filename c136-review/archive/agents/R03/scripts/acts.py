#!/usr/bin/env python3
"""acts.py — 从影子缓存里把某个号的逐决策拍记录打出来（不重跑重放）。

out/cache/<mid>-shadow.json 的 bots[号].acts 每个决策拍一行：
  [t, 余额, 地, nb 数, 中立邻格, 累计指令数, isNoFullSend, 影子额度, 报价条数,
   前 4 条报价 [[目标, c, need, person, nearCollapse, bleeding, onMe, pulseMode, isCrowdedHard, inAtk, tD]...],
   本拍发令数, worth, over, safeAt(-1)]

用法：python3 scripts/acts.py <mid> <号> <t0> <t1> [--every N] [--sent]
  --every N  每 N 个决策拍打一行（默认 1）
  --sent     只打有发令的拍
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def k(v):
    v = float(v)
    a = abs(v)
    if a >= 1e6:
        return "%.2fM" % (v / 1e6)
    if a >= 1e4:
        return "%.0fk" % (v / 1e3)
    if a >= 1e3:
        return "%.1fk" % (v / 1e3)
    return "%d" % v


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 4:
        print(__doc__)
        sys.exit(2)
    mid, bot, t0, t1 = args[0], args[1], int(args[2]), int(args[3])
    every = 1
    if "--every" in sys.argv:
        every = int(sys.argv[sys.argv.index("--every") + 1])
    only_sent = "--sent" in sys.argv
    sh = json.load(open(os.path.join(ROOT, "out", "cache", f"{mid}-shadow.json"), encoding="utf-8"))
    rs = json.load(open(os.path.join(ROOT, "out", "cache", f"{mid}-resim.json"), encoding="utf-8"))
    names = rs["names"]

    def nm(q):
        if q is None or q < 0:
            return "-"
        if q < len(names):
            return "%s#%d" % (names[q].replace("[APEX] ", "")[:10], q)
        return "中立" if q == 512 else "AI%d" % q

    b = sh["bots"][bot]
    print(f"# {mid} {bot}（me={b['me']}）决策拍 {t0}~{t1}：t 余额 地 密 | nb 中立 | 发令 | worth over safe | 报价（目标 c need 标记 inAtk tD）")
    n = 0
    for row in b["acts"]:
        t = row[0]
        if t < t0 or t > t1:
            continue
        sent = row[10] if len(row) > 10 else 0
        if only_sent and not sent:
            continue
        n += 1
        if (n - 1) % every:
            continue
        B, L = row[1], row[2]
        offs = []
        for o in (row[9] or []):
            flags = "".join(f for f, on in zip(["人", "塌", "血", "压我", "脉", "挤"], o[3:9]) if on)
            offs.append(f"{nm(o[0])} c={o[1]} need={k(o[2])} {flags} in={k(o[9])} tD={o[10]}")
        worth, over, safe = (row[11], row[12], row[13]) if len(row) > 13 else (-1, 0, -1)
        print(f"{t} B={k(B)} L={L} d={B / max(1, L):.1f} | nb={row[3]} neut={row[4]} | 发{sent} nfs={row[6]} | worth={worth} over={over} safe={k(safe) if safe >= 0 else '-'} | "
              + ("；".join(offs) if offs else f"报价 {row[8]}"))


if __name__ == "__main__":
    main()
