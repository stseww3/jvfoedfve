#!/usr/bin/env python3
"""cadence.py — 每局「本地发指令的节奏」：相邻两条 HL-TICK（间隔 90 拍）之间 cmds 涨了多少条（扣掉船）。

    python3 cadence.py [B|A|G]            # 默认 B 组；写 out/_cross/cadence_<组>.txt 并打印

用途：核对线上实际跑的版本是否带存档源码里的两条节流——
     · v27-team-c110.js 文件头第 19~31 行：发过指令后 450 毫秒 / 8 拍内不再调用策略（period=5 → 每 90 拍最多 9 条）；
     · Strategy.send 第 529~533 行：联机时同一个目标 15 拍内不重发（单目标每 90 拍最多 6 条）。
     某局出现「每 90 拍 16~18 条（不含船）」的窗，就说明那一局这两条节流至少有一条不在。
只读每局的 card.json 和 traj.csv。
"""
import collections
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out", "_cross")
DATA = os.environ.get("C136_DATA", "/agent/repos/c136-data")


def one(mid):
    d = os.path.join(DATA, "bundles", mid)
    card = json.load(open(os.path.join(d, "card.json"), encoding="utf-8"))
    by = collections.defaultdict(list)
    for r in csv.DictReader(open(os.path.join(d, "traj.csv"), encoding="utf-8")):
        try:
            by[r["bot"]].append((int(r["t"]), int(r["cmds"]), int(r["boats"])))
        except (ValueError, KeyError):
            pass
    mx = n16 = n10 = nwin = tot = 0
    for l in by.values():
        l.sort()
        for (t0, c0, b0), (t1, c1, b1) in zip(l, l[1:]):
            if t1 - t0 != 90 or not (700 <= t0 < 2100):
                continue
            d_ = (c1 - c0) - (b1 - b0)
            if d_ < 0:
                continue
            nwin += 1
            tot += d_
            mx = max(mx, d_)
            n16 += d_ >= 16
            n10 += d_ >= 10
    return dict(mid=mid, time=card.get("timeUtc", ""), bots=card.get("squadBots"), replay=bool((card.get("dataCompleteness") or {}).get("replay")),
                windows=nwin, cmds=tot, max=mx, ge16=n16, ge10=n10)


def main():
    grp = sys.argv[1] if len(sys.argv) > 1 else "B"
    mids = sorted(m for m in os.listdir(os.path.join(DATA, "bundles")) if m.startswith(grp))
    rows = []
    for m in mids:
        try:
            rows.append(one(m))
        except (OSError, ValueError):
            continue
    rows.sort(key=lambda r: r["time"])
    P = [f"[CA] {grp} 组各局 t=700~2100 的发指令节奏（相邻 HL-TICK 之间 cmds 增量，不含船）：局 | 开局时间 UTC | 号数 | 有录像 | 窗数 | 指令数 | 单窗最大 | ≥16 条的窗数 | ≥10 条的窗数"]
    for r in rows:
        P.append(f"     {r['mid']} | {r['time']} | {r['bots']} | {'是' if r['replay'] else '否'} | {r['windows']} | {r['cmds']} | {r['max']} | {r['ge16']} | {r['ge10']}")
    fast = [r for r in rows if r["ge16"] > 0]
    slow = [r for r in rows if r["ge16"] == 0]
    P.append(f"     有 ≥16 条窗的局 {len(fast)} 个：{' '.join(r['mid'] for r in fast)}（开局时间 {fast[0]['time'] if fast else '-'} ~ {fast[-1]['time'] if fast else '-'}）")
    P.append(f"     没有的局 {len(slow)} 个（开局时间 {slow[0]['time'] if slow else '-'} ~ {slow[-1]['time'] if slow else '-'}），单窗最大 {max([r['max'] for r in slow] or [0])} 条")
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, f"cadence_{grp}.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(P) + "\n")
    print("\n".join(P))


if __name__ == "__main__":
    main()
