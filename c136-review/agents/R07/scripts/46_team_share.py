#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""46_team_share.py — 结算拍上的队伍份额，以及我方号的地占本队多少。

口径：
  - 队伍份额：results.json 每个号结算那一拍的 teamTotals（各队领土格数）÷ 地图陆地格数；同一拍多行只取一行。
  - 我方号领土：traj.csv 里每个号在该结算拍之前（含）最近一个 HL-TICK 快照的 terr 求和；
    快照比结算拍早 >90 拍的号不计（已经没有快照 = 已阵亡/掉线/停摆）。
  - 占本队比例 = 我方号领土 ÷ 我方主队（card.ourPrimaryTeam）在该拍的领土。
  - 相邻两个结算拍之间：本队净增格数、我方号净增格数。
  - 沿用口径（最后一列）：尚未结算（results 里的结算拍 > 该拍）但快照已经断了 >90 拍的号（策略停摆），
    按它最后一个快照的 terr 计入；这是「假设停摆期间领土没变」的估计，不是观测值。

用法：python3 46_team_share.py <matchId> [--at t1,t2,...]
  --at：另外在这些拍号上只打印我方号的两种口径（有快照 / 沿用），没有队伍份额。
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
    end_of = {r.get("bot"): int(r["tick"]) for r in rows if isinstance(r.get("tick"), (int, float))}
    print("tick\t各队份额%\t本队格数\t我方号格数(快照拍,号数)\t我方号占本队%\t| 较上一结算拍：本队净增\t我方号净增\t| 沿用口径：停摆号(最后快照拍:格数) 合计格数 占本队% 占全图%")
    prev = None
    for t in sorted(seen):
        tt = seen[t]
        shares = " ".join(f"T{k}={100 * v / land:.1f}" for k, v in sorted(tt.items(), key=lambda kv: -kv[1]))
        team_px = tt.get(mine, 0)
        sq = 0
        n = 0
        snap_ts = []
        carry = []
        for b, rs in traj.items():
            before = [x for x in rs if x["t"] <= t]
            if not before:
                continue
            if t - before[-1]["t"] > 90:
                if end_of.get(b, -1) > t:
                    carry.append((b, before[-1]["t"], before[-1]["terr"]))
                continue
            sq += before[-1]["terr"]
            n += 1
            snap_ts.append(before[-1]["t"])
        ratio = f"{100 * sq / team_px:.1f}" if team_px else "—"
        st = f"{min(snap_ts)}" if snap_ts and min(snap_ts) == max(snap_ts) else (f"{min(snap_ts)}~{max(snap_ts)}" if snap_ts else "—")
        delta = ""
        if prev:
            delta = f"| {team_px - prev[0]:+d}\t{sq - prev[1]:+d}"
        csum = sq + sum(c[2] for c in carry)
        ctxt = " ".join(f"{b}({tt_}:{px})" for b, tt_, px in carry) or "—"
        cr = f"{100 * csum / team_px:.1f}" if team_px else "—"
        if not prev:
            delta = "| \t"
        print(f"{t}\t{shares}\t{team_px}\t{sq}({st},{n})\t{ratio}\t{delta}\t| {ctxt} {csum} {cr} {100 * csum / land:.2f}")
        prev = (team_px, sq)
    if "--at" in sys.argv:
        ats = [int(x) for x in sys.argv[sys.argv.index("--at") + 1].split(",") if x]
        print("\n--at：t\t有快照的号(号数) 格数 份额%\t| 沿用口径：停摆号(最后快照拍:格数)\t合计格数 份额%")
        for t in ats:
            sq = 0
            n = 0
            carry = []
            for b, rs in traj.items():
                before = [x for x in rs if x["t"] <= t]
                if not before:
                    continue
                if t - before[-1]["t"] > 90:
                    if end_of.get(b, -1) > t:
                        carry.append((b, before[-1]["t"], before[-1]["terr"]))
                    continue
                if end_of.get(b, 10 ** 9) <= t:
                    continue
                sq += before[-1]["terr"]
                n += 1
            csum = sq + sum(c[2] for c in carry)
            ctxt = " ".join(f"{b}({tt_}:{px})" for b, tt_, px in carry) or "—"
            print(f"{t}\t({n}) {sq} {100 * sq / land:.2f}\t| {ctxt}\t{csum} {100 * csum / land:.2f}")


if __name__ == "__main__":
    main()
