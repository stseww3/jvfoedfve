#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""89_squad_perimeter.py — 我方号合起来的「外圈」由什么组成、有多少号碰不到敌人。R07

用法（在 scripts/ 目录下）：
    python3 89_squad_perimeter.py <matchId> [--at t1,t2,...]

输入：out/<matchId>/truth_border.tsv（60_truth.cjs 每 90 拍采样：每个我方号的边界格数、贴水格数、贴无主地格数、各邻居的接壤格数）、
      truth_bots.tsv（每 10 拍我方号的领土 / 余额）、truth_players.tsv（队伍、是否真人、是否我方号）。
口径：
  · 「接壤格数」= 该号的边界格里与某个邻居相邻的格数（一个边界格可以同时贴两个邻居，所以各项相加可以大于边界格数）。
  · 敌 = 敌队真人席位（含已离开、由内置 AI 接管的真人席位）；AI = 无队的内置 AI；同队 = 同队但不是我方号的真人；我方 = 我方其他号。
  · 「碰不到敌人的号」= 贴敌、贴 AI、贴无主地都为 0 的号（只贴我方 / 同队 / 水）。
输出：out/<matchId>/squad_perimeter.txt
  A. 每个时刻：全队各类接壤格数合计；碰不到敌人的号有几个、名字、它们的领土和余额占全队的比例。
  B. 每个号「碰不到敌人」的采样段（起止拍、段内领土）。
  C. 每个时刻两类号各自离软上限（100×领土）还差多少兵。
"""
import csv
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    mid = args[0]
    out = os.path.join(HERE, "..", "out", mid)
    at = [int(x) for x in args[args.index("--at") + 1].split(",")] if "--at" in args else None
    players = {int(r["p"]): r for r in csv.DictReader(open(os.path.join(out, "truth_players.tsv"), encoding="utf-8"), delimiter="\t")}
    rows = list(csv.DictReader(open(os.path.join(out, "truth_border.tsv"), encoding="utf-8"), delimiter="\t"))
    bots_state = {}
    for r in csv.DictReader(open(os.path.join(out, "truth_bots.tsv"), encoding="utf-8"), delimiter="\t"):
        bots_state[(int(r["t"]), r["bot"])] = (int(r["terr"]), int(r["bal"]))
    by_t = defaultdict(list)
    for r in rows:
        by_t[int(r["t"])].append(r)
    ts = sorted(by_t)
    if at is None:
        at = [t for t in ts if t % 450 == 0 or t in (990, 1530)]

    def classify(r):
        me = int(r["p"])
        my_team = players[me]["team"]
        e = ai = mate = sq = 0
        enemies = {}
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
                enemies[q] = n
            elif pl.get("squad"):
                sq += n
            else:
                mate += n
        return e, ai, mate, sq, int(r["borderTouchWater"]), int(r["neutralAdj"]), enemies

    def fmt(n):
        return f"{n:,}"

    L = [f"# {mid} 我方号合起来的外圈（truth_border.tsv，每 90 拍采样；接壤格数口径见脚本抬头）", "",
         "A. 各时刻全队合计", "t\t在场号\t边界格\t贴敌\t贴AI\t贴无主地\t贴同队非我方\t贴我方号\t贴水\t敌方邻居（接壤格数）\t碰不到敌人的号（领土 / 余额）\t这些号占全队 领土% / 余额%"]
    for t in at:
        tt = max([x for x in ts if x <= t], default=None)
        if tt is None:
            continue
        rs = by_t[tt]
        tot = [0] * 6
        border = 0
        enemy_tot = defaultdict(int)
        idle = []
        terr_all = bal_all = 0
        for r in rs:
            e, ai, mate, sq, water, neut, enemies = classify(r)
            border += int(r["borderPx"])
            for i, v in enumerate((e, ai, neut, mate, sq, water)):
                tot[i] += v
            for q, n in enemies.items():
                enemy_tot[q] += n
            terr, bal = bots_state.get((tt, r["bot"]), (0, 0))
            terr_all += terr
            bal_all += bal
            if e == 0 and ai == 0 and neut == 0:
                idle.append((r["bot"], terr, bal))
        en = "、".join(f"{players[q]['name']}#{q}[T{players[q]['team']}] {n}" for q, n in sorted(enemy_tot.items(), key=lambda kv: -kv[1])) or "-"
        idle_s = "、".join(f"{b} {fmt(te)} / {fmt(ba)}" for b, te, ba in idle) or "-"
        it = sum(x[1] for x in idle)
        ib = sum(x[2] for x in idle)
        share = f"{100 * it / terr_all:.1f}% / {100 * ib / bal_all:.1f}%" if terr_all and bal_all else "-"
        L.append(f"{tt}\t{len(rs)}\t{border}\t{tot[0]}\t{tot[1]}\t{tot[2]}\t{tot[3]}\t{tot[4]}\t{tot[5]}\t{en}\t{len(idle)} 个：{idle_s}\t{share}")

    L += ["", "B. 每个号「碰不到敌人」（贴敌 = 贴 AI = 贴无主地 = 0）的采样段"]
    by_bot = defaultdict(list)
    for r in rows:
        by_bot[r["bot"]].append(r)
    for b in sorted(by_bot):
        segs = []
        cur = None
        for r in sorted(by_bot[b], key=lambda r: int(r["t"])):
            e, ai, mate, sq, water, neut, _ = classify(r)
            t = int(r["t"])
            if e == 0 and ai == 0 and neut == 0:
                if cur is None:
                    cur = [t, t]
                else:
                    cur[1] = t
            else:
                if cur is not None:
                    segs.append(cur)
                    cur = None
        if cur is not None:
            segs.append(cur)
        n = sum((s[1] - s[0]) // 90 + 1 for s in segs)
        total = len(by_bot[b])

        def terr_at(t):
            return bots_state.get((t, b), (0, 0))[0]
        seg_s = "；".join(f"{s[0]}~{s[1]}（{(s[1] - s[0]) // 90 + 1} 个采样，领土 {fmt(terr_at(s[0]))}→{fmt(terr_at(s[1]))}）" for s in segs) or "无"
        L.append(f"  {b}：{n}/{total} 个采样碰不到敌人；{seg_s}")
    L += ["", "C. 软上限（100×领土）以下还能装多少兵：碰不到敌人的号 vs 贴着敌人 / AI / 无主地的号",
          "t\t碰不到敌人的号：个数 / 领土 / 余额 / 密度 / 软上限以下空位\t贴敌的号：个数 / 领土 / 余额 / 密度 / 软上限以下空位（已过软上限的号按 0 计）/ 过软上限的号（超出多少）"]
    for t in at:
        tt = max([x for x in ts if x <= t], default=None)
        if tt is None:
            continue
        idle, front = [], []
        for r in by_t[tt]:
            e, ai, mate, sq, water, neut, _ = classify(r)
            terr, bal = bots_state.get((tt, r["bot"]), (0, 0))
            (idle if (e == 0 and ai == 0 and neut == 0) else front).append((r["bot"], terr, bal))

        def summ(lst):
            te = sum(x[1] for x in lst)
            ba = sum(x[2] for x in lst)
            room = sum(max(0, 100 * x[1] - x[2]) for x in lst)
            return f"{len(lst)} / {fmt(te)} / {fmt(ba)} / {ba / max(1, te):.0f} / {fmt(room)}"
        over = "、".join(f"{b} +{fmt(ba - 100 * te)}" for b, te, ba in front if ba > 100 * te) or "无"
        L.append(f"{tt}\t{summ(idle)}\t{summ(front)} / {over}")
    txt = "\n".join(L) + "\n"
    open(os.path.join(out, "squad_perimeter.txt"), "w", encoding="utf-8").write(txt)
    print(txt)


if __name__ == "__main__":
    main()
