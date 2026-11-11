#!/usr/bin/env python3
"""dispatch_signature.py — 用 [HL-DISPATCH] 日志给每一局的「实际运行策略版本」打指纹。

背景：/agent/repos/c136-data/src/strategy/ 下三份源码里 tryDonateToTeammate 的常量各不相同
（理想捐出比例 idealPct、捐出方密度门槛 reqD、最小 pct、冷却拍数）。日志里每条 [HL-DISPATCH]
都打印了 kind / pct / boxedIn / dMe / dAlly，所以可以反推该局实际跑的是哪一组常量。

用法：
    python3 dispatch_signature.py [bundles 目录] > out/dispatch-signature.tsv
输出（每局一行，TSV）：
    matchId  cohort  timeUtc  nDispatch
    modes    —— 每个 (kind 首字母, boxedIn) 组合里出现次数最多的 pct（"理想 pct"），形如 O1=320 Y1=320 D1=380 O0=225 …
    minPct   —— 全局最小 pct
    minDme   —— 每个 (kind, boxedIn) 组合里 dMe 的最小值
    minGap   —— 同一个号相邻两次 DISPATCH 的最小间隔（拍）
    maxDally —— 每个 (kind, boxedIn) 组合里 dAlly 的最大值
"""
import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict

ROOT = sys.argv[1] if len(sys.argv) > 1 else "/agent/repos/c136-data/bundles"
PAT = re.compile(
    r"\[(?P<bot>[^\]]+)\] \[HL-DISPATCH\] t=(?P<t>\d+) (?P<kind>\w+) pct=(?P<pct>\d+)/1024 -> ally=(?P<ally>\d+)\((?P<name>[^)]*)\) "
    r"boxedIn=(?P<boxed>true|false) myBal=(?P<bal>\d+) dMe=(?P<dme>-?\d+) dAlly=(?P<dally>-?\d+)")
KEY = {"offense_dispatch": "O", "yield_opt_dispatch": "Y", "defense_dispatch": "D", "prod_opt": "P"}


def scan(mid):
    path = os.path.join(ROOT, mid, "in_game.log")
    rows = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if "HL-DISPATCH" not in line:
                continue
            m = PAT.search(line)
            if not m:
                continue
            d = m.groupdict()
            rows.append((d["bot"], int(d["t"]), KEY.get(d["kind"], d["kind"][:1].upper()), int(d["pct"]),
                         1 if d["boxed"] == "true" else 0, int(d["bal"]), int(d["dme"]), int(d["dally"])))
    return rows


def main():
    out = csv.writer(sys.stdout, delimiter="\t", lineterminator="\n")
    out.writerow(["matchId", "cohort", "timeUtc", "nDispatch", "modes", "minPct", "minDme", "minGap", "maxDally"])
    for mid in sorted(os.listdir(ROOT)):
        card_p = os.path.join(ROOT, mid, "card.json")
        if not os.path.isfile(card_p):
            continue
        card = json.load(open(card_p))
        rows = scan(mid)
        pcts = defaultdict(Counter)
        min_dme = {}
        max_dally = {}
        last = {}
        min_gap = None
        for bot, t, k, pct, boxed, bal, dme, dally in rows:
            key = f"{k}{boxed}"
            pcts[key][pct] += 1
            min_dme[key] = min(min_dme.get(key, 10 ** 9), dme)
            max_dally[key] = max(max_dally.get(key, -10 ** 9), dally)
            if bot in last:
                gap = t - last[bot]
                if min_gap is None or gap < min_gap:
                    min_gap = gap
            last[bot] = t
        modes = " ".join(f"{k}={c.most_common(1)[0][0]}({c.most_common(1)[0][1]}/{sum(c.values())})" for k, c in sorted(pcts.items()))
        out.writerow([mid, card.get("cohort"), card.get("timeUtc"), len(rows), modes,
                      min((r[3] for r in rows), default=""),
                      " ".join(f"{k}={v}" for k, v in sorted(min_dme.items())),
                      "" if min_gap is None else min_gap,
                      " ".join(f"{k}={v}" for k, v in sorted(max_dally.items()))])


if __name__ == "__main__":
    main()
