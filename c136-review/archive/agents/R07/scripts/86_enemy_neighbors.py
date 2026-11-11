#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""86_enemy_neighbors.py — R07：指定采样拍上，贴着我方号的敌方真人席位都是谁、哪一队、多大。

用法（在 scripts/ 目录下）：
    python3 86_enemy_neighbors.py <matchId> --at 540,990,1080,1440,1530 [--tag 名字]

输入（都在 out/<matchId>/，由 60_truth.cjs 生成）：
    truth_border.tsv   每 90 拍每个我方号的邻居（玩家号:接壤格数）
    truth_all.tsv      每 90 拍每个席位的领土 / 余额 / 是否在场 / state（2 = 离开）
    truth_players.tsv  席位名、队伍、是否真人席位、是否我方号
输出：out/<matchId>/enemy_neighbors[_<tag>].txt
    A. 每个采样拍：贴着我方号的敌方在位真人按队伍数人头（括号里是该队当拍在场的真人数）
    B. 每个采样拍：逐个敌方真人邻居——领土 / 余额 / 密度、贴着哪几个我方号（接壤格数）
    C. 每个采样拍：我方各号的领土 / 余额 / 密度、敌方真人邻居数、最弱的那个敌方真人邻居（按密度）
"""
import csv
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))


def fmt(x):
    return f"{int(round(x)):,}"


def main():
    args = sys.argv[1:]
    if not args or "--at" not in args:
        print(__doc__)
        sys.exit(2)
    mid = args[0]
    ats = [int(x) for x in args[args.index("--at") + 1].split(",")]
    tag = args[args.index("--tag") + 1] if "--tag" in args else ""
    out = os.path.join(HERE, "..", "out", mid)

    def rd(name):
        return list(csv.DictReader(open(os.path.join(out, name), encoding="utf-8"), delimiter="\t"))

    players = {int(r["p"]): r for r in rd("truth_players.tsv")}
    squad = {p for p, r in players.items() if r.get("squad") not in ("", None, "0")}
    my_team = players[next(iter(squad))]["team"]
    human = {p for p, r in players.items() if r.get("human") == "1"}

    snap = defaultdict(dict)
    for r in rd("truth_all.tsv"):
        snap[int(r["t"])][int(r["p"])] = (int(r["terr"]), int(float(r["bal"])), int(r["alive"]), int(r["state"]))
    border = defaultdict(list)
    for r in rd("truth_border.tsv"):
        border[int(r["t"])].append(r)

    def nm(p):
        r = players.get(p)
        if not r:
            return f"AI#{p}"
        return f"{r['name']}#{p}[T{r['team']}]"

    L = [f"# {mid} 贴着我方号的敌方真人席位（真引擎重放的接壤真值；只算在位、没离开的真人）", ""]
    secA, secB, secC = ["A. 按队伍数人头：贴着我方号的敌方真人 / 该队当拍在场真人"], ["B. 逐个敌方真人邻居"], ["C. 我方各号"]
    for t in ats:
        if t not in border:
            secA.append(f"  t={t}: 没有这个采样拍")
            continue
        st = snap.get(t, {})
        present = defaultdict(int)
        for p in human:
            terr, bal, alive, state = st.get(p, (0, 0, 0, 0))
            if alive and terr > 0 and state != 2 and p not in squad:
                present[players[p]["team"]] += 1
        touch = defaultdict(list)  # enemy p -> [(bot, px)]
        per_bot = {}
        for r in border[t]:
            bp = int(r["p"])
            bterr, bbal, balive, bstate = st.get(bp, (0, 0, 0, 0))
            if not balive or bterr <= 0:
                continue
            ens = []
            for tok in (r["nbs"] or "").split():
                q, px = tok.split(":")
                q, px = int(q), int(px)
                if q not in human or q in squad:
                    continue
                if players[q]["team"] == my_team:
                    continue
                qterr, qbal, qalive, qstate = st.get(q, (0, 0, 0, 0))
                if not qalive or qterr <= 0 or qstate == 2:
                    continue
                touch[q].append((r["bot"], px))
                ens.append((qbal / max(1, qterr), q, qterr, qbal))
            per_bot[r["bot"]] = (bterr, bbal, bstate, sorted(ens))
        byteam = defaultdict(int)
        for q in touch:
            byteam[players[q]["team"]] += 1
        secA.append(f"  t={t}: 共 {len(touch)} 个 | " + "，".join(
            f"T{tm} {byteam.get(tm, 0)}/{present[tm]}" for tm in sorted(present)))
        secB.append(f"  t={t}:")
        for q in sorted(touch, key=lambda q: -sum(px for _, px in touch[q])):
            qterr, qbal, _, _ = st[q]
            secB.append(f"    {nm(q)} {fmt(qterr)} 格 / {fmt(qbal)} 兵（密度 {qbal / max(1, qterr):.1f}）| 贴着 " + "、".join(
                f"{b}:{px}" for b, px in sorted(touch[q], key=lambda x: -x[1])))
        secC.append(f"  t={t}:")
        for b in sorted(per_bot, key=lambda b: -per_bot[b][0]):
            bterr, bbal, bstate, ens = per_bot[b]
            left = "（已离开）" if bstate == 2 else ""
            if ens:
                d, q, qterr, qbal = ens[0]
                weakest = f"最弱的 {nm(q)} {fmt(qterr)} 格 / {fmt(qbal)} 兵（密度 {d:.1f}）"
            else:
                weakest = "没有敌方真人邻居"
            secC.append(f"    {b}{left} {fmt(bterr)} 格 / {fmt(bbal)} 兵（密度 {bbal / max(1, bterr):.1f}）| 敌方真人邻居 {len(ens)} 个 | {weakest}")
    L += secA + [""] + secB + [""] + secC
    fn = os.path.join(out, f"enemy_neighbors{'_' + tag if tag else ''}.txt")
    with open(fn, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("\n".join(L[:40]))
    print(f"... 写入 {fn}")


if __name__ == "__main__":
    main()
