#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""58b_bot_trace.py — R07：一个号逐窗口的「日志快照 vs 录像落地」对照（给报告里的例子用）。

每条 [HL-TICK]（隔 90 拍）一行：领土、余额、邻居数、无主地、cmds 和它比上一条多了几条、
这一窗的 [HL-DISPATCH] 条数、录像里这个号落在 (上一条, 这一条] 的指令（拍号×条数）。

先跑 57_exec_census.mjs（写 out/_cache/census/<局>/humans_cmd.tsv）。
用法：python3 58b_bot_trace.py <局> <号> [起拍 止拍]
输出：out/_cross/trace_<局>_<号>_<起>_<止>.txt（也打印到终端）
"""
import csv
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = "/agent/repos/c136-data"
ROOT = os.path.join(HERE, "..", "out", "_cache", "census")
CROSS = os.path.join(HERE, "..", "out", "_cross")
TICK_RE = re.compile(r"^\d+\t\[([^\]\[]+)\] \[HL-TICK\] t=(\d+) terr=(\d+)\S* bal=(-?\d+) dens=([\d.]+) nb=(\d+) neut=(\d+) cmds=(\d+)")
DISP_RE = re.compile(r"^\d+\t\[([^\]\[]+)\] \[HL-DISPATCH\] t=(\d+) ")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    mid, bot = sys.argv[1], sys.argv[2]
    t0 = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    t1 = int(sys.argv[4]) if len(sys.argv) > 4 else 10 ** 9
    snaps, disp = [], []
    with open(os.path.join(DATA, "bundles", mid, "in_game.log"), encoding="utf-8", errors="replace") as f:
        for ln in f:
            m = TICK_RE.match(ln)
            if m and m.group(1) == bot:
                snaps.append(tuple(int(x) if i != 3 else float(x) for i, x in enumerate(m.groups()[1:])))
                continue
            m = DISP_RE.match(ln)
            if m and m.group(1) == bot:
                disp.append(int(m.group(2)))
    pid = None
    for ln in open(os.path.join(ROOT, mid, "squad_players.tsv"), encoding="utf-8"):
        c = ln.rstrip("\n").split("\t")
        if len(c) == 2 and c[0].isdigit() and c[1] == bot:
            pid = c[0]
    land = []
    with open(os.path.join(ROOT, mid, "humans_cmd.tsv"), newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if r["squad"] == "1" and r["p"] == pid:
                land.append((int(r["t"]), r["kind"]))
    L = []
    P = L.append
    P(f"# {mid} {bot}：逐窗口的日志快照 vs 录像落地（58b_bot_trace.py）")
    P("拍\t领土\t余额\t密度\t邻居\t无主地\tcmds\t这一窗发出\t这一窗调度日志\t这一窗录像落地\t落地明细（拍×条）")
    prev = None
    tot_i = tot_l = 0
    for t, terr, bal, dens, nb, neut, cmds in snaps:
        if prev is not None and t0 <= t <= t1 and prev[0] >= t0:
            issued = cmds - prev[6]
            c = Counter(x for x, k in land if prev[0] < x <= t)
            nd = sum(1 for x in disp if prev[0] < x <= t)
            n = sum(c.values())
            tot_i += issued
            tot_l += n
            P(f"{t}\t{terr:,}\t{bal:,}\t{dens}\t{nb}\t{neut}\t{cmds}\t{issued}\t{nd}\t{n}\t" + "、".join(f"{x}×{k}" for x, k in sorted(c.items())))
        elif t0 <= t <= t1:
            P(f"{t}\t{terr:,}\t{bal:,}\t{dens}\t{nb}\t{neut}\t{cmds}\t-\t-\t-\t（起点）")
        prev = (t, terr, bal, dens, nb, neut, cmds)
    P(f"合计：发出 {tot_i}、录像落地 {tot_l}")
    out = "\n".join(L) + "\n"
    name = f"trace_{mid}_{bot}_{t0}_{t1 if t1 < 10 ** 9 else 'end'}.txt"
    with open(os.path.join(CROSS, name), "w", encoding="utf-8") as f:
        f.write(out)
    sys.stdout.write(out)


if __name__ == "__main__":
    main()
