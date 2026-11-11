#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""46_team_share.py — 结算拍上的队伍份额，以及我方号的地占本队多少。

口径：
  - 队伍份额：results.json 每个号结算那一拍的 teamTotals（各队领土格数）÷ 地图陆地格数；同一拍多行只取一行。
  - 我方号领土：traj.csv 里每个号在该结算拍之前（含）最近一个 HL-TICK 快照的 terr 求和；
    快照比结算拍早 >90 拍的号不计（已经没有快照 = 已阵亡/掉线/停摆）。
  - 占本队比例 = 我方号领土 ÷ 我方主队（card.ourPrimaryTeam）在该拍的领土。
  - 相邻两个结算拍之间：本队净增格数、我方号净增格数。

用法：python3 46_team_share.py <matchId>
"""
import json
import os
import sys

from r07lib import DATA, load_card, load_traj


def main():
    mid = sys.argv[1]
    card = load_card(mid)
    land = card["mapLand"]
    mine = str(card.get("ourPrimaryTeam"))
    traj = load_traj(mid)
    res = json.load(open(os.path.join(DATA, "bundles", mid, "results.json"), encoding="utf-8"))
    rows = res if isinstance(res, list) else res.get("rows", [])
    seen = {}
    for r in rows:
        tt = r.get("teamTotals")
        if not tt or not isinstance(r.get("tick"), (int, float)):
            continue
        seen.setdefault(int(r["tick"]), tt)
    print(f"{mid} land={land} ourPrimaryTeam=T{mine} resultLabel={card['outcome']['resultLabel']} endTick={card['outcome']['endTick']}")
    print("tick\t各队份额%\t本队格数\t我方号格数(快照拍,号数)\t我方号占本队%\t| 较上一结算拍：本队净增\t我方号净增")
    prev = None
    for t in sorted(seen):
        tt = seen[t]
        shares = " ".join(f"T{k}={100 * v / land:.1f}" for k, v in sorted(tt.items(), key=lambda kv: -kv[1]))
        team_px = tt.get(mine, 0)
        sq = 0
        n = 0
        snap_ts = []
        for b, rs in traj.items():
            before = [x for x in rs if x["t"] <= t]
            if not before or t - before[-1]["t"] > 90:
                continue
            sq += before[-1]["terr"]
            n += 1
            snap_ts.append(before[-1]["t"])
        ratio = f"{100 * sq / team_px:.1f}" if team_px else "—"
        st = f"{min(snap_ts)}" if snap_ts and min(snap_ts) == max(snap_ts) else (f"{min(snap_ts)}~{max(snap_ts)}" if snap_ts else "—")
        delta = ""
        if prev:
            delta = f"| {team_px - prev[0]:+d}\t{sq - prev[1]:+d}"
        print(f"{t}\t{shares}\t{team_px}\t{sq}({st},{n})\t{ratio}\t{delta}")
        prev = (team_px, sq)


if __name__ == "__main__":
    main()
