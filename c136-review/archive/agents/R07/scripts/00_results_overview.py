#!/usr/bin/env python3
"""00_results_overview.py — 把 G01-G09-results.jsonl 的每条结算记录列成一张表，并按结算时间看分组。

用法：
  python3 00_results_overview.py <raw_dir> > out/common/results_overview.txt

输入：<raw_dir>/G01-G09-results.jsonl（数据 A：jvfoedfve cursor/c116-winrate-liaison-b3bc:c116-winrate/data/）
输出：每条记录一行（按 at 排序），以及所有出现过的字段名清单。
只做读取与排版，不做任何推断。
"""
import json
import sys
from collections import Counter, OrderedDict

raw = sys.argv[1] if len(sys.argv) > 1 else "/tmp/c136-r07/raw"
path = f"{raw}/G01-G09-results.jsonl"

recs = []
with open(path, encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        r["_line"] = i
        recs.append(r)

keys = Counter()
for r in recs:
    keys.update(r.keys())
print(f"# records={len(recs)} file={path}")
print("# field presence (field: count):")
for k, c in sorted(keys.items()):
    print(f"#   {k}: {c}")

print()
hdr = ["line", "at", "bot", "port", "event", "result", "game", "tick", "time", "secs", "place", "players",
       "alivePl", "terr", "lastTerr", "lastRank", "peak", "land", "bal", "sent", "acc", "meId", "nHumans",
       "team.mine", "team.best", "team.totals"]
print("\t".join(hdr))
for r in sorted(recs, key=lambda r: r.get("at", "")):
    team = r.get("team") or {}
    row = [r["_line"], r.get("at"), r.get("bot"), r.get("port"), r.get("event"), r.get("result"), r.get("game"),
           r.get("tick"), r.get("time"), r.get("seconds"), r.get("place"), r.get("players"), r.get("alivePlayers"),
           r.get("territory"), r.get("lastTerritory"), r.get("lastRank"), r.get("peak"), r.get("land"),
           r.get("balance"), r.get("sent"), r.get("accepted"), (r.get("me") or {}).get("id"),
           len(r.get("humans") or []), team.get("mine"), team.get("best"),
           json.dumps(team.get("totals"), separators=(",", ":"))]
    print("\t".join("" if v is None else str(v) for v in row))

print()
print("# distinct values")
for k in ["mode", "strategy", "armed", "loop", "next", "stay", "allowed", "ext", "type"]:
    print(f"#   {k}: {dict(Counter(json.dumps(r.get(k)) for r in recs))}")
