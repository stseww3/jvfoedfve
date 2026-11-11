#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""95_group_sends.py — 各组把陆上进攻的兵发给了哪一组（按时间段）。R07

用法（在 scripts/ 目录下）：
    python3 95_group_sends.py <matchId> --cuts 0,990,1530,... [--top 8] [--tag 名字]

输入：out/<matchId>/humans_cmd.tsv（74_side_flow.mjs 按真引擎重放记下的全场真人逐条指令）与 truth_players.tsv（编号 → 名字 / 队）。
口径：
  只算 kind=attack 且真正扣了款的指令（troops > 0），按落地拍归段（t0 ≤ t < t1，最后一段含 t1；和 74_side_flow.mjs / 90_spend_ratio.py 同口径）。
  发令方分组：我方号 / T<n> 同队其他真人 / T<n> 真人。
  目标分组：无主地（tt=N）/ 内置 AI（tt=A）/ 某队真人（tt=H）/ 某队已离开的席位（tt=L，引擎里由 AI 接管）；
            目标是我方号时单列「我方号」。
  每格三个数：条数 / 发兵合计 / 手续费合计。发兵是引擎里扣下的兵，没用完退回的部分不在这张表里（退回看 67_troop_flow.mjs / 90_spend_ratio.py）。
  B 段只列我方号：每段里按发兵排前 --top 个目标（目标当时的领土 / 余额取该段第一条指令落地时的值）。
输出：out/<matchId>/group_sends[_<tag>].txt
"""
import csv
import os
import sys
from collections import OrderedDict, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))


def fmt(x):
    return f"{int(round(x)):,}"


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    mid = sys.argv[1]
    cuts, top, tag = None, 8, ""
    i = 2
    while i < len(sys.argv):
        a = sys.argv[i]
        if a == "--cuts":
            cuts = [int(x) for x in sys.argv[i + 1].split(",")]
            i += 2
        elif a == "--top":
            top = int(sys.argv[i + 1])
            i += 2
        elif a == "--tag":
            tag = sys.argv[i + 1]
            i += 2
        else:
            raise SystemExit(f"不认识的参数 {a}")
    if not cuts or len(cuts) < 2:
        raise SystemExit("要给 --cuts t0,t1,...")
    out_dir = os.path.join(HERE, "..", "out", mid)
    players = {}
    with open(os.path.join(out_dir, "truth_players.tsv"), encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            players[int(r["p"])] = r
    squad_ids = {p for p, r in players.items() if (r.get("squad") or "").strip() not in ("", "0")}
    my_team = None
    for p in squad_ids:
        my_team = players[p]["team"]
        break

    def sender_group(p):
        r = players.get(p)
        if r is None:
            return "?"
        if p in squad_ids:
            return "我方号"
        if r["team"] == my_team:
            return f"T{r['team']} 同队其他真人"
        return f"T{r['team']} 真人"

    def target_group(tt, target):
        if tt == "N":
            return "无主地"
        if tt == "A":
            return "内置 AI"
        r = players.get(target)
        if r is None:
            return "内置 AI"
        if target in squad_ids:
            base = "我方号"
        elif r["team"] == my_team:
            base = f"T{r['team']} 同队其他真人"
        else:
            base = f"T{r['team']} 真人"
        return base + ("（已离开的席位）" if tt == "L" else "")

    def span_of(t):
        for k in range(len(cuts) - 1):
            lo, hi = cuts[k], cuts[k + 1]
            if t >= lo and (t < hi or (k == len(cuts) - 2 and t <= hi)):
                return k
        return -1

    nspan = len(cuts) - 1
    agg = [defaultdict(lambda: [0, 0, 0]) for _ in range(nspan)]
    per_target = [OrderedDict() for _ in range(nspan)]
    n_rows = 0
    with open(os.path.join(out_dir, "humans_cmd.tsv"), encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if r["kind"] != "attack":
                continue
            troops = int(float(r["troops"] or 0))
            if troops <= 0:
                continue
            t = int(r["t"])
            s = span_of(t)
            if s < 0:
                continue
            p = int(r["p"])
            tt = r["tt"]
            target = int(r["target"]) if r["target"] not in ("", None) else -1
            sg = sender_group(p)
            tg = target_group(tt, target)
            cell = agg[s][(sg, tg)]
            cell[0] += 1
            cell[1] += troops
            cell[2] += int(float(r["fee"] or 0))
            n_rows += 1
            if p in squad_ids and tt in ("H", "L"):
                key = target
                d = per_target[s].get(key)
                if d is None:
                    d = per_target[s][key] = {"n": 0, "troops": 0, "fee": 0, "t0": t, "t1": t, "terr": int(float(r["tTerr"] or 0)),
                                              "bal": int(float(r["tBal"] or 0)), "left": tt == "L", "by": defaultdict(int)}
                d["n"] += 1
                d["troops"] += troops
                d["fee"] += int(float(r["fee"] or 0))
                d["t1"] = t
                d["by"][r["name"].replace("[APEX] ", "")] += troops

    lines = [f"# {mid} 各组把陆上进攻的兵发给了哪一组（95_group_sends.py；humans_cmd.tsv 里扣了款的进攻 {n_rows} 条；切点 {','.join(str(c) for c in cuts)}）",
             "# 每格：条数 / 发兵合计 / 手续费合计（发兵 = 引擎里扣下的兵，退回的部分不在这张表里）；括号里是这一组当段发兵的占比", ""]
    lines.append("A. 发令方分组 × 时间段 × 目标分组")
    for s in range(nspan):
        lines.append(f"## t={cuts[s]}~{cuts[s + 1]}")
        senders = sorted({k[0] for k in agg[s]}, key=lambda g: (g != "我方号", g))
        for sg in senders:
            cells = {k[1]: v for k, v in agg[s].items() if k[0] == sg}
            tot = sum(v[1] for v in cells.values())
            parts = []
            for tg, v in sorted(cells.items(), key=lambda kv: -kv[1][1]):
                parts.append(f"{tg} {v[0]} 条 / {fmt(v[1])} / 费 {fmt(v[2])}（{100 * v[1] / tot:.0f}%）" if tot else f"{tg} {v[0]} 条")
            lines.append(f"  {sg}：发兵合计 {fmt(tot)} | " + "；".join(parts))
        lines.append("")
    lines.append(f"B. 我方号 × 时间段：对真人 / 离开席位的进攻，按发兵排前 {top} 个目标（目标的领土 / 余额取该段第一条落地时）")
    for s in range(nspan):
        if not per_target[s]:
            continue
        lines.append(f"## t={cuts[s]}~{cuts[s + 1]}")
        tot = sum(d["troops"] for d in per_target[s].values())
        rows = sorted(per_target[s].items(), key=lambda kv: -kv[1]["troops"])[:top]
        for target, d in rows:
            r = players.get(target) or {}
            nm = f"{r.get('name', '?')}#{target}[T{r.get('team', '?')}]" + ("（已离开）" if d["left"] else "")
            by = "、".join(f"{k} {fmt(v)}" for k, v in sorted(d["by"].items(), key=lambda kv: -kv[1]))
            lines.append(f"  {nm}：{d['n']} 条 / {fmt(d['troops'])} 兵 / 费 {fmt(d['fee'])}（占本段对人发兵 {100 * d['troops'] / tot:.0f}%）| "
                         f"t={d['t0']}~{d['t1']} | 首条落地时它 {fmt(d['terr'])} 格 / {fmt(d['bal'])} 兵 | {by}")
        lines.append(f"  本段对真人 / 离开席位发兵合计 {fmt(tot)}，目标 {len(per_target[s])} 个")
        lines.append("")
    name = "group_sends" + (f"_{tag}" if tag else "") + ".txt"
    with open(os.path.join(out_dir, name), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"写出 out/{mid}/{name}（{len(lines)} 行）")


if __name__ == "__main__":
    main()
