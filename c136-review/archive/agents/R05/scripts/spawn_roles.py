#!/usr/bin/env python3
"""spawn_roles.py — 每局每个号「最后一次」选点分配的角色/坐标/最近队友距离（读 bundles/*/spawn.csv）。
spawn.csv 每行 = 一条 [HL-SPAWN-BACKEND]（协调器分配）或 [HL-SPAWN]（号内自主兜底）日志；同一个号在选点倒计时里会被重复分配，
取 line 最大（最后一条）的那行当作最终落点。
输出 TSV：matchId cohort timeUtc nBots roles(角色:个数) minAllyDist中位 最小 最大 重解次数中位 自主兜底号数
用法：python3 spawn_roles.py [matchId ...]   （不带参数 = 全部 bundles）
"""
import csv, json, os, sys, collections, statistics
DATA = os.environ.get("C136_DATA", "/agent/repos/c136-data")
ids = sys.argv[1:] or sorted(os.listdir(f"{DATA}/bundles"))
print("matchId\tcohort\ttimeUtc\tnBots\troles\tminAllyDist_med\tmin\tmax\tresolves_med\tautonomousBots")
for mid in ids:
    p = f"{DATA}/bundles/{mid}/spawn.csv"
    if not os.path.exists(p):
        continue
    card = json.load(open(f"{DATA}/bundles/{mid}/card.json"))
    last, n, auto = {}, collections.Counter(), set()
    for r in csv.DictReader(open(p)):
        b = r["bot"]
        n[b] += 1
        if r.get("role", "") in ("", "None", "AUTONOMOUS", "HL-SPAWN"):
            auto.add(b)
        if b not in last or int(r["line"]) > int(last[b]["line"]):
            last[b] = r
    roles = collections.Counter(v["role"] or "(none)" for v in last.values())
    ds = [int(float(v["minAllyDist"])) for v in last.values() if v["minAllyDist"] not in ("", "None", "-1")]
    print("\t".join(map(str, [
        mid, card.get("cohort"), card.get("timeUtc"), len(last),
        " ".join(f"{k}:{v}" for k, v in sorted(roles.items())),
        int(statistics.median(ds)) if ds else "", min(ds) if ds else "", max(ds) if ds else "",
        int(statistics.median(n.values())) if n else "", len(auto)])))
