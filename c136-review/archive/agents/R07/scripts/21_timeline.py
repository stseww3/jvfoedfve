#!/usr/bin/env python3
"""21_timeline.py — 一局的全局时间线（我方 8 个号合计 + 结算时刻的全队 / 各队领土）。

用法：
  python3 21_timeline.py <out_dir>          （读 <out_dir>/traj.csv opening.csv results.csv squad.slice.log）

输出：
  <out_dir>/timeline.csv   每个快照拍一行：t, alive(有 HL-TICK 且 terr>0 的号数), squadTerr, squadShare(=squadTerr/land),
                           squadBal, squadDens, 以及每个号的 terr / bal / dens / nb / neut
  <out_dir>/timeline.txt   便于阅读的版本 + 结算时刻各队领土表（team.totals）+ t<630 的开局数据（HL-OPENING、OPENING-CHECK）

口径说明：
  - 「我方 8 个号合计」只是小队自己的号；整支队伍（同队的其他玩家）只在每个号结算的那一拍有数（team.totals）。
  - t<630 没有 HL-TICK；用 HL-OPENING 里的 terr（发指令那一拍、指令生效前）和 OPENING-CHECK。
  - 某个号在某一拍没有 HL-TICK（已阵亡或中断）时，该拍它的 terr / bal 记为空；alive 只数有快照且 terr>0 的号。
    阵亡拍取 results.csv 的 tick。阵亡之后不再计入。
  - land 取 results.csv 的 land 字段。
"""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from c136lib import BOTS, load_slice  # noqa: E402

out = sys.argv[1]
traj = list(csv.DictReader(open(f"{out}/traj.csv", encoding="utf-8")))
opening = list(csv.DictReader(open(f"{out}/opening.csv", encoding="utf-8")))
results = list(csv.DictReader(open(f"{out}/results.csv", encoding="utf-8")))
land = int(results[0]["land"])
death = {r["bot"]: int(r["tick"]) for r in results}
res_event = {r["bot"]: r["event"] for r in results}

by_t = {}
for r in traj:
    by_t.setdefault(int(r["t"]), {})[r["bot"]] = r

rows = []
for t in sorted(by_t):
    snap = by_t[t]
    terr = bal = 0
    alive = 0
    cells = []
    for b in BOTS:
        r = snap.get(b)
        if r:
            tr, bl = int(r["terr"]), int(r["bal"])
            terr += tr
            bal += bl
            if tr > 0:
                alive += 1
            cells += [tr, bl, r["dens"], r["nb"], r["neut"]]
        else:
            cells += ["", "", "", "", ""]
    rows.append([t, alive, terr, round(terr / land, 5), bal, round(bal / max(1, terr), 2)] + cells)

hdr = ["t", "alive", "squadTerr", "squadShare", "squadBal", "squadDens"] + [f"{b}_{c}" for b in BOTS for c in ("terr", "bal", "dens", "nb", "neut")]
with open(f"{out}/timeline.csv", "w", newline="", encoding="utf-8") as f:
    cw = csv.writer(f)
    cw.writerow(hdr)
    cw.writerows(rows)

L = []
L.append(f"land={land}  deaths/exit ticks: " + ", ".join(f"{b}@{death[b]}({res_event[b]})" for b in sorted(death, key=death.get)))
L.append("")
L.append("== t<630: HL-OPENING terr (before the command lands) per cycle ==")
cyc = {}
for r in opening:
    cyc.setdefault(int(r["cyc"]), {})[r["bot"]] = r
L.append("cyc\t" + "\t".join(BOTS) + "\t(sum of listed)")
for c in sorted(cyc):
    cells = []
    s = 0
    for b in BOTS:
        r = cyc[c].get(b)
        if r:
            cells.append(f"t{r['t']}:{r['terr']}")
            s += int(r["terr"])
        else:
            cells.append("-")
    L.append(f"{c}\t" + "\t".join(cells) + f"\t{s}")
evs = load_slice(f"{out}/squad.slice.log")
for e in evs:
    if e["type"] == "OPENCHECK":
        tot = sum(it["terr"] for it in e["items"])
        L.append("")
        L.append(f"OPENING-CHECK @ tick {e['t']} (line {e['line']}): " + " | ".join(f"{it['bot']}:t{it['tick']},terr={it['terr']},sent={it['sent']}({it['status']})" for it in e["items"]) + f"  => squadTerr={tot} share={tot / land:.5f}")
L.append("")
L.append("== snapshots (HL-TICK every 90 ticks) ==")
L.append("t\talive\tsqTerr\tsqShare%\tsqBal\tsqDens\t| " + "\t".join(f"{b}(terr/bal/dens/nb/neut)" for b in BOTS))
for row in rows:
    t, alive, terr, share, bal, dens = row[:6]
    cells = []
    for i, b in enumerate(BOTS):
        c = row[6 + 5 * i: 11 + 5 * i]
        cells.append("-" if c[0] == "" else f"{c[0]}/{c[1]}/{c[2]}/{c[3]}/{c[4]}")
    L.append(f"{t}\t{alive}\t{terr}\t{100 * share:.2f}\t{bal}\t{dens}\t| " + "\t".join(cells))
L.append("")
L.append("== whole-team land at each result tick (team.totals; key 0 = players with team id 0) ==")
L.append("tick\tbot\tevent\tmine\tbest\ttotals(share% of land)\tsumAll%\tourTeamRank")
for r in sorted(results, key=lambda r: int(r["tick"])):
    if not r["teamTotals"]:
        L.append(f"{r['tick']}\t{r['bot']}\t{r['event']}\t-\t-\t(team=null)")
        continue
    tot = json.loads(r["teamTotals"])
    mine = r["teamMine"]
    real = {k: v for k, v in tot.items() if k != "0"}
    rank = 1 + sum(1 for k, v in real.items() if v > real.get(mine, 0))
    s = " ".join(f"T{k}={v}({100 * v / land:.1f}%)" for k, v in sorted(tot.items(), key=lambda kv: int(kv[0])))
    L.append(f"{r['tick']}\t{r['bot']}\t{r['event']}\t{mine}\t{r['teamBest']}\t{s}\t{100 * sum(tot.values()) / land:.1f}\t{rank}/{len(real)}")
open(f"{out}/timeline.txt", "w", encoding="utf-8").write("\n".join(L) + "\n")
print(f"timeline rows={len(rows)} land={land}")
