#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""73_front_width.py — 一个号的边界有多少格贴着敌人（前线宽度）。R07

用法（在 scripts/ 目录下）：
    python3 73_front_width.py <matchId> [--bots a,b|all] [--t0 T] [--t1 T]

输入：out/<matchId>/truth_border.tsv（60_truth.cjs 每 90 拍采样：边界格数、贴水格数、贴无主地格数、各邻居的接壤格数）、
      truth_players.tsv（各玩家的队伍、是否我方号）。
输出：out/<matchId>/front_width.txt（追加式：每次运行重写）——每个号在 [t0, t1] 内各采样拍的
      边界格数 / 贴敌方真人 / 贴内置 AI / 贴同队非我方真人 / 贴我方号，以及贴敌格数的最小、中位、最大和各敌方邻居的出现情况。
"""
import csv
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))


def med(a):
    a = sorted(a)
    return a[len(a) // 2] if a else 0


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    mid = args[0]

    def opt(k, d):
        return args[args.index(k) + 1] if k in args else d
    t0, t1 = int(opt("--t0", 0)), int(opt("--t1", 10 ** 9))
    out = os.path.join(HERE, "..", "out", mid)
    players = {int(r["p"]): r for r in csv.DictReader(open(os.path.join(out, "truth_players.tsv"), encoding="utf-8"), delimiter="\t")}
    rows = list(csv.DictReader(open(os.path.join(out, "truth_border.tsv"), encoding="utf-8"), delimiter="\t"))
    sel = opt("--bots", "all")
    bots = sorted({r["bot"] for r in rows}) if sel == "all" else sel.split(",")
    L = [f"# {mid} 前线宽度（truth_border.tsv，每 90 拍一采样；t={t0}~{t1 if t1 < 10 ** 9 else '终局'}）",
         "# 贴敌 = 与敌队真人接壤的边界格数；AI = 与内置 AI（无队）接壤；同队 = 与同队但不是我方号的真人接壤；我方 = 与我方其他号接壤"]
    for b in bots:
        rs = [r for r in rows if r["bot"] == b and t0 <= int(r["t"]) <= t1]
        if not rs:
            continue
        me = int(rs[0]["p"])
        my_team = players[me]["team"]
        series = []
        enemy_seen = defaultdict(list)
        for r in rs:
            e = ai = mate = sq = 0
            for tok in (r["nbs"] or "").split():
                if ":" not in tok:
                    continue
                q, n = tok.split(":")
                q, n = int(q), int(n)
                pl = players.get(q)
                if pl is None or pl.get("human") != "1":
                    ai += n
                elif pl["team"] != my_team:
                    e += n
                    enemy_seen[q].append((int(r["t"]), n))
                elif pl.get("squad"):
                    sq += n
                else:
                    mate += n
            series.append((int(r["t"]), int(r["borderPx"]), e, ai, mate, sq, int(r["borderTouchWater"]), int(r["neutralAdj"])))
        es = [s[2] for s in series]
        bs = [s[1] for s in series]
        zero = sum(1 for x in es if x == 0)
        L.append("")
        L.append(f"{b}：{len(series)} 个采样；边界 {min(bs)}~{max(bs)} 格；贴敌 最小 {min(es)} / 中位 {med(es)} / 最大 {max(es)} 格（贴敌为 0 的采样 {zero} 个）；"
                 f"贴同队非我方 中位 {med([s[4] for s in series])}、贴我方号 中位 {med([s[5] for s in series])}、贴水 中位 {med([s[6] for s in series])}、贴无主地 中位 {med([s[7] for s in series])}")
        for q, lst in sorted(enemy_seen.items(), key=lambda kv: -len(kv[1])):
            ns = [n for _, n in lst]
            L.append(f"    敌邻 {players[q]['name']}#{q}[T{players[q]['team']}]：出现在 {len(lst)} 个采样（t={lst[0][0]}~{lst[-1][0]}），接壤 {min(ns)}~{max(ns)} 格（中位 {med(ns)}）")
        step = max(1, len(series) // 12)
        L.append("    抽样（拍:边界/贴敌/AI/同队/我方）：" + " ".join(f"{s[0]}:{s[1]}/{s[2]}/{s[3]}/{s[4]}/{s[5]}" for s in series[::step]))
    txt = "\n".join(L) + "\n"
    open(os.path.join(out, "front_width.txt"), "w", encoding="utf-8").write(txt)
    print(txt)


if __name__ == "__main__":
    main()
