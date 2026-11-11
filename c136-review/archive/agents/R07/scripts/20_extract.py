#!/usr/bin/env python3
"""20_extract.py — 把一局的日志切片拆成结构化表。

用法：
  python3 20_extract.py <raw_dir> <G0x> <out_dir>
  （<out_dir>/squad.slice.log 和 slice.meta.json 须已由 10_slice_game.py 生成）

输出（都在 <out_dir>/）：
  ids.json          号名 -> 本局玩家编号 me、GAME-INIT 字段
  traj.csv          逐号 HL-TICK 快照：bot,t,terr,pct,bal,dens,nb,neut,cmds,boats,avgMs,maxMs,skip,line
  opening.csv       HL-OPENING：bot,t,cyc,rings,spend,bal,terr,line
  events.csv        DONATE / ASSIST / INTERCEPT：type,t,bot,kind,pct,target,targetName,boxedIn,myBal,dMe,dAlly,ally,boatId,boatTroops,line
  slow.csv          HL-SLOW-TICK：bot,t,ms,maxMs,line
  spawn_solves.csv  每次 [BACKEND-SPAWN-COORD]：solve,line,ms,minSep 及 8 个号的坐标
  spawn_assign.csv  每条 HL-SPAWN-BACKEND：bot,me,slot,role,x,y,minAllyDist,voronoi,line
  results.csv       本局 8 条结算（来自 results.jsonl，按日志顺序核对）
  anomalies.txt     ERROR / HOT-IMPORT / 未识别的行 / HL-TICK 中断（相邻快照间隔 != 90 拍）
"""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from c136lib import BOTS, load_slice, match_results  # noqa: E402

raw, gid, out = sys.argv[1], sys.argv[2], sys.argv[3]
evs = load_slice(f"{out}/squad.slice.log")
meta = json.load(open(f"{out}/slice.meta.json", encoding="utf-8"))


def w(name, header, rows):
    with open(f"{out}/{name}", "w", newline="", encoding="utf-8") as f:
        cw = csv.writer(f)
        cw.writerow(header)
        for r in rows:
            cw.writerow(["" if v is None else v for v in r])
    return len(rows)


ids = {}
for e in evs:
    if e["type"] == "INIT":
        ids[e["bot"]] = {"me": e["me"], "mode": e["mode"], "map": e["map"], "mapSeed": e["mapSeed"], "humans": e["humans"],
                         "line": e["line"]}
json.dump(ids, open(f"{out}/ids.json", "w", encoding="utf-8"), indent=1)

n_traj = w("traj.csv", ["bot", "t", "terr", "pct", "bal", "dens", "nb", "neut", "cmds", "boats", "avgMs", "maxMs", "skip", "line"],
           [[e["bot"], e["t"], e["terr"], e["pct"], e["bal"], e["dens"], e["nb"], e["neut"], e["cmds"], e["boats"], e["avgMs"],
             e["maxMs"], e["skip"], e["line"]] for e in evs if e["type"] == "TICK"])
n_open = w("opening.csv", ["bot", "t", "cyc", "rings", "spend", "bal", "terr", "line"],
           [[e["bot"], e["t"], e["cyc"], e["rings"], e["spend"], e["bal"], e["terr"], e["line"]] for e in evs if e["type"] == "OPENING"])
rows = []
for e in evs:
    if e["type"] == "DONATE":
        rows.append(["DONATE", e["t"], e["bot"], e["kind"], e["pct"], e["to"], e["toName"], e["boxedIn"], e["myBal"], e["dMe"],
                     e["dAlly"], None, None, None, e["line"]])
    elif e["type"] == "ASSIST":
        rows.append(["ASSIST", e["t"], e["bot"], e["kind"], 102, e["enemy"], e["enemyName"], None, e.get("myBal"), e.get("dMe"),
                     None, e["ally"], None, None, e["line"]])
    elif e["type"] == "INTERCEPT":
        rows.append(["INTERCEPT", e["t"], e["bot"], "sea", e["pct"], e["owner"], e["ownerName"], None, None, None, None, None,
                     e["boatId"], e["boatTroops"], e["line"]])
n_ev = w("events.csv", ["type", "t", "bot", "kind", "pct", "target", "targetName", "boxedIn", "myBal", "dMe", "dAlly", "ally",
                        "boatId", "boatTroops", "line"], rows)
n_slow = w("slow.csv", ["bot", "t", "ms", "maxMs", "line"],
           [[e["bot"], e["t"], e["ms"], e["maxMs"], e["line"]] for e in evs if e["type"] == "SLOW"])

solves = [e for e in evs if e["type"] == "COORD"]
hdr = ["solve", "line", "ms", "minSep"] + [f"{b}_{c}" for b in BOTS for c in ("x", "y")]
rows = []
for i, e in enumerate(solves, 1):
    pos = {it["bot"]: (it["x"], it["y"]) for it in e["items"]}
    rows.append([i, e["line"], e["ms"], e["minSep"]] + [v for b in BOTS for v in pos.get(b, (None, None))])
n_solve = w("spawn_solves.csv", hdr, rows)
n_assign = w("spawn_assign.csv", ["bot", "me", "slot", "role", "x", "y", "minAllyDist", "voronoi", "line"],
             [[e["bot"], e["me"], e["slot"], e["role"], e["x"], e["y"], e["minAllyDist"], e["voronoi"], e["line"]]
              for e in evs if e["type"] == "SPAWN"])

res = match_results(raw, meta["sliceFirstLine"], meta["sliceLastLine"])
hdr = ["bot", "meId", "event", "result", "tick", "seconds", "place", "alivePlayers", "territory", "lastTerritory", "lastRank",
       "peak", "land", "balance", "sent", "accepted", "teamMine", "teamBest", "teamTotals", "nHumans", "at", "logLine"]
rows = []
for r in res:
    team = r.get("team") or {}
    rows.append([r["_bot"], (r.get("me") or {}).get("id"), r.get("event"), r.get("result"), r.get("tick"), r.get("seconds"),
                 r.get("place"), r.get("alivePlayers"), r.get("territory"), r.get("lastTerritory"), r.get("lastRank"),
                 r.get("peak"), r.get("land"), r.get("balance"), r.get("sent"), r.get("accepted"), team.get("mine"),
                 team.get("best"), json.dumps(team.get("totals"), separators=(",", ":")) if team else "", len(r.get("humans") or []),
                 r.get("at"), r["_logLine"]])
n_res = w("results.csv", hdr, rows)

# 异常清单
lines = []
errs = [e for e in evs if e["type"] == "ERROR"]
hots = [e for e in evs if e["type"] == "HOTIMPORT"]
others = [e for e in evs if e["type"] == "OTHER"]
lines.append(f"ERROR lines: {len(errs)}")
by = {}
for e in errs:
    by.setdefault(e["bot"], []).append(e["line"])
for b, ls in sorted(by.items()):
    lines.append(f"  {b}: n={len(ls)} firstLine={ls[0]} lastLine={ls[-1]}")
lines.append(f"HOT-IMPORT lines: {len(hots)}" + ("" if not hots else f" (lines {hots[0]['line']}..{hots[-1]['line']}, size={hots[0]['size']})"))
lines.append(f"unparsed in-scope lines: {len(others)}")
for e in others[:20]:
    lines.append(f"  {e['line']}: {e['raw'][:160]}")
lines.append("HL-TICK gaps (consecutive snapshots of one bot not 90 ticks apart):")
last = {}
gaps = 0
for e in evs:
    if e["type"] != "TICK":
        continue
    p = last.get(e["bot"])
    if p is not None and e["t"] - p != 90:
        lines.append(f"  {e['bot']}: {p} -> {e['t']} (gap {e['t'] - p}) at line {e['line']}")
        gaps += 1
    last[e["bot"]] = e["t"]
lines.append(f"  total gaps: {gaps}")
lines.append("first/last HL-TICK per bot:")
first = {}
for e in evs:
    if e["type"] == "TICK":
        first.setdefault(e["bot"], e["t"])
for b in BOTS:
    lines.append(f"  {b}: first={first.get(b)} last={last.get(b)}")
slow_by = {}
for e in evs:
    if e["type"] == "SLOW":
        slow_by.setdefault(e["bot"], []).append((e["t"], e["ms"]))
lines.append("HL-SLOW-TICK per bot (count, max ms, first t, last t):")
for b in BOTS:
    s = slow_by.get(b, [])
    if s:
        lines.append(f"  {b}: n={len(s)} maxMs={max(x[1] for x in s)} firstT={s[0][0]} lastT={s[-1][0]}")
    else:
        lines.append(f"  {b}: n=0")
open(f"{out}/anomalies.txt", "w", encoding="utf-8").write("\n".join(lines) + "\n")

print(json.dumps({"game": gid, "ids": {b: v["me"] for b, v in ids.items()}, "traj": n_traj, "opening": n_open, "events": n_ev,
                  "slow": n_slow, "spawnSolves": n_solve, "spawnAssign": n_assign, "results": n_res,
                  "errors": len(errs), "hotImports": len(hots), "unparsed": len(others)}))
