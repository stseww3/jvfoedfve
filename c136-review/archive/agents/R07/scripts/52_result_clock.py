#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""52_result_clock.py — R07：出局 / 终局那一刻，客户端的局内时钟比服务器晚多少。

results.csv 每行有局内拍号 tick（该号出局 / 离开 / 终局时客户端自己的拍号）和墙上时间 at（结果上报的时刻）。
引擎每拍 56 毫秒（--ms 可改）。对每一行算  偏移 = (at − 对局卡 timestampMs) − tick × 56ms：
  同一局里各行的偏移应当是同一个常数（进场到第 0 拍的时间）；取本局阵亡 / 终局各行里最小的偏移当基线，
  某一行高出基线多少秒，就是那个客户端在上报那一刻比服务器晚了多少（上限：还含上报本身的耗时）。
只读 bundles/<id>/results.csv、card.json。

用法：python3 52_result_clock.py <matchId> [<matchId> ...] [--ms 56]
输出：每局写 out/<matchId>/result_clock.txt；多局时另在屏幕上打一张汇总。
"""
import csv
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = "/agent/repos/c136-data"


def one(mid, ms):
    card = json.load(open(os.path.join(DATA, "bundles", mid, "card.json"), encoding="utf-8"))
    t0 = datetime.datetime.fromtimestamp(card["timestampMs"] / 1000, datetime.timezone.utc)
    rows = []
    with open(os.path.join(DATA, "bundles", mid, "results.csv"), newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                at = datetime.datetime.fromisoformat(r["at"].replace("Z", "+00:00"))
                tick = int(r["tick"])
            except (ValueError, KeyError):
                continue
            rows.append({"bot": r["bot"], "event": r["event"], "tick": tick, "wall": (at - t0).total_seconds(),
                         "sent": r.get("sent", ""), "accepted": r.get("accepted", "")})
    rows.sort(key=lambda x: x["tick"])
    for r in rows:
        r["off"] = r["wall"] - r["tick"] * ms / 1000
    ref = [r for r in rows if r["event"] in ("died", "end")] or rows
    base = min(r["off"] for r in ref) if ref else 0.0
    for r in rows:
        r["late_s"] = r["off"] - base
        r["late_ticks"] = r["late_s"] * 1000 / ms
    lines = [f"# {mid} 结果上报时刻的客户端时钟（52_result_clock.py；每拍 {ms:g} 毫秒；基线 = 本局阵亡 / 终局各行里最小的偏移 {base:.2f} 秒）",
             "# 偏移 = (上报时刻 − 对局卡时间戳) − 拍号×每拍毫秒；晚 = 偏移 − 基线（上限，含上报耗时）",
             "", "号\t事件\t拍号\t上报时刻（距对局卡，秒）\t偏移（秒）\t晚（秒）\t晚（拍）\tsent / accepted"]
    for r in rows:
        lines.append(f"{r['bot']}\t{r['event']}\t{r['tick']}\t{r['wall']:.3f}\t{r['off']:.2f}\t{r['late_s']:.2f}\t{r['late_ticks']:.0f}\t{r['sent']} / {r['accepted']}")
    died = [r for r in rows if r["event"] in ("died", "end")]
    left = [r for r in rows if r["event"] == "left"]
    if died:
        mx = max(died, key=lambda r: r["late_s"])
        lines.append("")
        lines.append(f"阵亡 / 终局 {len(died)} 行：晚 ≤1 秒的 {sum(1 for r in died if r['late_s'] <= 1.0)} 行，最大 {mx['late_s']:.2f} 秒（{mx['late_ticks']:.0f} 拍；{mx['bot']} @{mx['tick']}）")
    if left:
        lines.append("离开 " + "；".join(f"{r['bot']} @{r['tick']} 晚 {r['late_s']:.1f} 秒（{r['late_ticks']:.0f} 拍）" for r in left))
    if len(rows) >= 2:
        a, b = rows[0], rows[-1]
        if b["tick"] > a["tick"]:
            lines.append(f"首尾两行之间：{b['tick'] - a['tick']} 拍用了 {b['wall'] - a['wall']:.3f} 秒 = 每拍 {1000 * (b['wall'] - a['wall']) / (b['tick'] - a['tick']):.1f} 毫秒")
    out_dir = os.path.join(HERE, "..", "out", mid)
    os.makedirs(out_dir, exist_ok=True)
    open(os.path.join(out_dir, "result_clock.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    return base, rows, lines


def main():
    argv = sys.argv[1:]
    ms = 56.0
    if "--ms" in argv:
        k = argv.index("--ms")
        ms = float(argv[k + 1])
        argv = argv[:k] + argv[k + 2:]
    if len(argv) == 1:
        print("\n".join(one(argv[0], ms)[2]))
        return
    print("局\t基线（秒）\t阵亡 / 终局行数\t晚 ≤1 秒\t最大（秒 / 拍 / 号@拍）\t离开的席位（晚 秒）")
    for mid in argv:
        base, rows, _ = one(mid, ms)
        died = [r for r in rows if r["event"] in ("died", "end")]
        left = [r for r in rows if r["event"] == "left"]
        mx = max(died, key=lambda r: r["late_s"]) if died else None
        print(f"{mid}\t{base:.2f}\t{len(died)}\t{sum(1 for r in died if r['late_s'] <= 1.0)}\t"
              + (f"{mx['late_s']:.2f} / {mx['late_ticks']:.0f} / {mx['bot']}@{mx['tick']}" if mx else "-") + "\t"
              + ("、".join(f"{r['bot']}@{r['tick']} {r['late_s']:.1f}" for r in left) or "-"))


if __name__ == "__main__":
    main()
