#!/usr/bin/env python3
"""62_rank.py — R07：全场真人的领土/余额排位表（真引擎重放真值），看我方号在全场排第几、和各队中位数/头部差多少。

用法：python3 62_rank.py <matchId> [--at t1,t2,...] [--top 8]
输入：out/<matchId>/truth_all.tsv、truth_players.tsv（先跑 60_truth.cjs；truth_all 每 90 拍一行/玩家）
输出：stdout + out/<matchId>/rank.txt
  每个时刻：在场真人数（不含已离开的）、各队真人领土中位数、我方每个号的领土名次与余额名次、
  领土前 top 名真人（队伍、领土、余额、密度）。「真人」= 录像头里的人类席位且当时没离开（state!=2）。
"""
import csv
import os
import statistics
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))


def load(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def main():
    argv = sys.argv[1:]
    mid = argv[0]
    at = [180, 630, 1080, 1530, 1980, 2520, 3060, 3960, 4500, 5400]
    top = 8
    if "--at" in argv:
        at = [int(x) for x in argv[argv.index("--at") + 1].split(",")]
    if "--top" in argv:
        top = int(argv[argv.index("--top") + 1])
    out = os.path.join(HERE, "..", "out", mid)
    players = load(os.path.join(out, "truth_players.tsv"))
    name = {int(r["p"]): r["name"] for r in players}
    team = {int(r["p"]): int(r["team"]) for r in players}
    human = {int(r["p"]): r["human"] == "1" for r in players}
    squad = {int(r["p"]): r["squad"] for r in players if r["squad"]}
    rows = defaultdict(list)
    for r in load(os.path.join(out, "truth_all.tsv")):
        rows[int(r["t"])].append(r)
    ticks = sorted(rows)
    lines = []
    P = lines.append
    P(f"# {mid} 全场真人排位（真引擎重放真值；truth_all 每 90 拍采样，取不晚于所给时刻的最近一拍）")
    for t in at:
        ts = [x for x in ticks if x <= t]
        if not ts:
            continue
        tt = ts[-1]
        hum = []
        for r in rows[tt]:
            p = int(r["p"])
            if not human.get(p) or r["alive"] != "1" or r["state"] == "2":
                continue
            hum.append((p, int(r["terr"]), int(r["bal"])))
        if not hum:
            continue
        by_terr = sorted(hum, key=lambda x: -x[1])
        by_bal = sorted(hum, key=lambda x: -x[2])
        rk_t = {p: i + 1 for i, (p, _, _) in enumerate(by_terr)}
        rk_b = {p: i + 1 for i, (p, _, _) in enumerate(by_bal)}
        P(f"\n== t={tt}：在场真人 {len(hum)} 人；全体领土中位数 {int(statistics.median([x[1] for x in hum]))}，余额中位数 {int(statistics.median([x[2] for x in hum]))}")
        per_team = defaultdict(list)
        for p, te, ba in hum:
            per_team[team[p]].append((te, ba))
        P("   各队真人：" + "；".join(
            f"T{k} {len(v)} 人 领土中位 {int(statistics.median([x[0] for x in v]))} 合计 {sum(x[0] for x in v)} 余额合计 {sum(x[1] for x in v)}"
            for k, v in sorted(per_team.items())))
        ours = [(p, te, ba) for p, te, ba in hum if p in squad]
        if ours:
            P("   我方在场号（领土名次/余额名次）：" + "  ".join(
                f"{squad[p]} {te}格#{rk_t[p]} {ba}兵#{rk_b[p]}" for p, te, ba in sorted(ours, key=lambda x: rk_t[x[0]])))
            P(f"   我方在场号领土中位数 {int(statistics.median([x[1] for x in ours]))}，名次中位数 {int(statistics.median([rk_t[x[0]] for x in ours]))}/{len(hum)}")
        P(f"   领土前 {top}：" + "  ".join(
            f"{name[p]}#{p}[T{team[p]}{'我' if p in squad else ''}] {te}格/{ba}兵(密度{ba / max(1, te):.0f})" for p, te, ba in by_terr[:top]))
    txt = "\n".join(lines) + "\n"
    with open(os.path.join(out, "rank.txt"), "w") as f:
        f.write(txt)
    sys.stdout.write(txt)


if __name__ == "__main__":
    main()
