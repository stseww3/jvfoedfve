#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""48_neutral_floor.py — R07：边界上贴着无主地、却一条指令都没发的决策拍，按「余额 − 留底 够不够一条最小指令」分开数。

背景：核心逻辑里捡无主地的那一行是 `if (this.neutral > 0) this.expandNeutral(g, g.bal[me] - this.safeAt(g, -1));`，
     expandNeutral 第一句 `if (spend < min) return;`，min = minCmd = feeK × ⌊12×余额 / 1024⌋（feeK = 4）。
     所以「余额 − safe(-1) < 最小指令」时，身边的无主地（多半是邻居清场后放出来的）不会有人去捡。

用法（在 scripts/ 目录下）：
    python3 48_neutral_floor.py <matchId> [--from 1500]

输入：out/<matchId>/shadow_trace_<号>_<t0>_<t1>.txt（65_shadow.mjs --trace 的逐拍明细；表头行带 B / L / neut / safe(-1)）
输出：out/<matchId>/neutral_floor.txt
    A. 各号：neut > 0 的决策拍数 | 发了打无主地的指令 | 发了别的指令 | 没有指令且 余额 − safe(-1) < 最小指令（留底挡住）|
       没有指令且余额够（已有兵压在无主地上、或别的闸）
    B. 「留底挡住」的连续段（同一个号相邻决策拍间隔 ≤ 10 拍算一段）：起止拍、拍数、贴无主地的边界格数范围、余额范围、safe(-1) 范围、
       差多少（safe(-1) − 余额 的范围）
    口径：全部是影子按源码公式在重演局面上重算的值；相邻明细共用的边界拍只算一次；最小指令按 4 × ⌊12×B / 1024⌋ 复算。
"""
import glob
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
HEAD = re.compile(r'^t=(\d+) (\S+) B=(-?\d+) L=(\d+) d=([\d.]+) nb=(\d+) neut=(\d+).*?safe\(-1\)=(-?\d+)')
CMD = re.compile(r'⇒ 影子指令 (\w+) pct=(\d+) → (.+?)（约 (\d+) 兵）')
FEE_K = 4


def fmt(x):
    return f"{int(round(x)):,}"


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    mid = sys.argv[1]
    t_from = 1500
    if "--from" in sys.argv:
        t_from = int(sys.argv[sys.argv.index("--from") + 1])
    outdir = os.path.join(HERE, "..", "out", mid)
    seen = {}
    for path in sorted(glob.glob(os.path.join(outdir, "shadow_trace_*.txt"))):
        cur = None
        for ln in open(path, encoding="utf-8"):
            ln = ln.rstrip("\n")
            if ln.startswith("t="):
                m = HEAD.match(ln)
                cur = None
                if not m:
                    continue
                t, bot = int(m.group(1)), m.group(2)
                if t < t_from or (bot, t) in seen:
                    continue
                cur = {"t": t, "bot": bot, "B": int(m.group(3)), "L": int(m.group(4)), "nb": int(m.group(6)),
                       "neut": int(m.group(7)), "safe": int(m.group(8)), "cmd": None}
                seen[(bot, t)] = cur
            elif cur is not None and "⇒ 影子指令" in ln:
                cm = CMD.search(ln)
                if cm:
                    cur["cmd"] = (cm.group(1), cm.group(3))
    rows = [r for r in seen.values() if r["neut"] > 0]
    per = defaultdict(lambda: {"n": 0, "neutCmd": 0, "otherCmd": 0, "floor": [], "enough": 0})
    for r in sorted(rows, key=lambda r: (r["bot"], r["t"])):
        p = per[r["bot"]]
        p["n"] += 1
        if r["cmd"]:
            if r["cmd"][0] == "attack" and "无主地" in r["cmd"][1]:
                p["neutCmd"] += 1
            else:
                p["otherCmd"] += 1
            continue
        min_cmd = FEE_K * (12 * r["B"] // 1024)
        if r["B"] - r["safe"] < min_cmd:
            p["floor"].append(r)
        else:
            p["enough"] += 1
    out = [f"# {mid} 贴着无主地却没发指令的决策拍（48_neutral_floor.py；t >= {t_from}；影子明细 {len(seen)} 个决策拍里 neut > 0 的 {len(rows)} 个）",
           "# 留底挡住 = 没有指令，且 余额 − safe(-1) < 最小指令（4 × ⌊12×余额 / 1024⌋）；safe(-1) = min(oppFloorCap×领土, max(safeFinite, dpKeep))",
           "",
           "A. 各号：neut > 0 的决策拍 | 发了打无主地的指令 | 发了别的指令 | 没有指令：留底挡住 | 没有指令：余额够（已有兵压在无主地上或别的闸）"]
    tot = [0, 0, 0, 0, 0]
    for bot in sorted(per):
        p = per[bot]
        vals = [p["n"], p["neutCmd"], p["otherCmd"], len(p["floor"]), p["enough"]]
        tot = [a + b for a, b in zip(tot, vals)]
        out.append(f"  {bot}\t" + "\t".join(str(v) for v in vals))
    out.append("  合计\t" + "\t".join(str(v) for v in tot))
    out.append("")
    out.append("B. 「留底挡住」的连续段（相邻决策拍间隔 ≤ 10 拍算一段）：号 | 起止拍 | 拍数 | 贴无主地的边界格 | 余额 | safe(-1) | 差（safe(-1) − 余额）| 领土")
    nseg = 0
    for bot in sorted(per):
        fl = per[bot]["floor"]
        seg = []
        for r in fl + [None]:
            if r is not None and (not seg or r["t"] - seg[-1]["t"] <= 10):
                seg.append(r)
                continue
            if seg:
                nseg += 1
                bs = [x["B"] for x in seg]
                ss = [x["safe"] for x in seg]
                ds = [x["safe"] - x["B"] for x in seg]
                ns = [x["neut"] for x in seg]
                ls = [x["L"] for x in seg]
                out.append(f"  {bot}\tt={seg[0]['t']}~{seg[-1]['t']}\t{len(seg)} 拍\t{min(ns)}~{max(ns)} 格\t{fmt(min(bs))}~{fmt(max(bs))}\t"
                           f"{fmt(min(ss))}~{fmt(max(ss))}\t{fmt(min(ds))}~{fmt(max(ds))}\t{fmt(min(ls))}~{fmt(max(ls))}")
            seg = [r] if r is not None else []
    out.append(f"  共 {nseg} 段 / {tot[3]} 个决策拍")
    path = os.path.join(outdir, "neutral_floor.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print("\n".join(out[:3 + 2 + len(per) + 2]))
    print(f"-> {os.path.relpath(path, os.path.join(HERE, '..', '..', '..', '..'))}")


if __name__ == "__main__":
    main()
