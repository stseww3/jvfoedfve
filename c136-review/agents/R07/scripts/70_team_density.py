#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""70_team_density.py — R07：各队密度对照表（真账）。

读 60_truth.cjs 的 truth_teams.tsv（每队每 90 拍：领土、余额）和 truth_bots.tsv（我方每个号），
把我方所在队拆成「我方号（在场、没离开的）」和「同队其余玩家」，逐拍给出领土 / 余额 / 密度，
并给出我方号占本队领土、余额的比例。

用法：python3 70_team_density.py <matchId> [--at t1,t2,...]（默认每 450 拍一行）
输出：out/<matchId>/team_density.txt / .json
"""
import csv
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    mid = sys.argv[1]
    out = os.path.join(HERE, "..", "out", mid)
    at = None
    if "--at" in sys.argv:
        at = [int(x) for x in sys.argv[sys.argv.index("--at") + 1].split(",")]
    teams = list(csv.DictReader(open(os.path.join(out, "truth_teams.tsv")), delimiter="\t"))
    bots = list(csv.DictReader(open(os.path.join(out, "truth_bots.tsv")), delimiter="\t"))
    players = list(csv.DictReader(open(os.path.join(out, "truth_players.tsv")), delimiter="\t"))
    squad_team = None
    for r in players:
        if r.get("squad") in ("1", "true", "True") or r.get("isSquad") in ("1", "true"):
            squad_team = r.get("team")
            break
    if squad_team is None:
        # 退而求其次：truth_bots 里的 p → truth_players 的 team
        pid = {r["p"] for r in bots}
        for r in players:
            if r.get("p") in pid:
                squad_team = r.get("team")
                break
    T = defaultdict(dict)
    for r in teams:
        T[int(r["t"])][r["team"]] = (int(r["terr"]), int(float(r["bal"])))
    S = defaultdict(lambda: [0, 0, 0, 0, 0])  # terr, bal, n(在场未离开), 离开座位的领土, 离开座位的余额
    for r in bots:
        t = int(r["t"])
        if r.get("alive", "1") in ("0", ""):
            continue
        if r.get("state") == "2":
            S[t][3] += int(r["terr"])
            S[t][4] += int(float(r["bal"]))
            continue
        S[t][0] += int(r["terr"])
        S[t][1] += int(float(r["bal"]))
        S[t][2] += 1
    ticks = sorted(T)
    if at is None:
        at = [t for t in ticks if t % 450 == 0 and t > 0]
    L = [f"# {mid} 各队密度对照（真账，truth_teams.tsv + truth_bots.tsv）；我方在 T{squad_team}",
         "# 「本队其余」= 本队合计 − 我方在场未离开的号 − 我方离开后被内置 AI 接管的座位；各队合计含该队的内置 AI",
         "t\t" + "\t".join(f"T{k} 领土/余额(M)/密度" for k in sorted(T[ticks[0]]) if k != "0") + "\t我方 号数/领土/余额(M)/密度\t本队其余 领土/余额(M)/密度\t我方占本队 领土%/余额%"]
    J = []
    for t in at:
        if t not in T:
            t = max(x for x in ticks if x <= t)
        row = [str(t)]
        for k in sorted(T[t]):
            if k == "0":
                continue
            terr, bal = T[t][k]
            row.append(f"{terr}/{bal / 1e6:.2f}/{bal / max(1, terr):.0f}")
        s = S[t]
        mt, mb = T[t].get(str(squad_team), (0, 0))
        rt, rb = mt - s[0] - s[3], mb - s[1] - s[4]
        row.append(f"{s[2]}/{s[0]}/{s[1] / 1e6:.2f}/{s[1] / max(1, s[0]):.0f}")
        row.append(f"{rt}/{rb / 1e6:.2f}/{rb / max(1, rt):.0f}")
        row.append(f"{100 * s[0] / max(1, mt):.1f}/{100 * s[1] / max(1, mb):.1f}")
        L.append("\t".join(row))
        J.append({"t": t, "teams": {k: {"terr": v[0], "bal": v[1], "dens": round(v[1] / max(1, v[0]), 1)} for k, v in T[t].items() if k != "0"},
                  "squad": {"n": s[2], "terr": s[0], "bal": s[1], "dens": round(s[1] / max(1, s[0]), 1)},
                  "rest": {"terr": rt, "bal": rb, "dens": round(rb / max(1, rt), 1)},
                  "squadTerrPct": round(100 * s[0] / max(1, mt), 1), "squadBalPct": round(100 * s[1] / max(1, mb), 1)})
    txt = "\n".join(L) + "\n"
    open(os.path.join(out, "team_density.txt"), "w").write(txt)
    json.dump(J, open(os.path.join(out, "team_density.json"), "w"), ensure_ascii=False)
    sys.stdout.write(txt)


if __name__ == "__main__":
    main()
