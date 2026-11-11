#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""72_repeat_sends.py — 同一目标的连发进攻（上一条还没生效就又发一条）统计。R07

用法（在 scripts/ 目录下）：
    python3 72_repeat_sends.py <matchId> [--gap 12] [--top 14]

输入：out/<matchId>/cmd_effect.tsv（67_troop_flow.mjs 按引擎重演记下的每条指令的真实扣款：t、号、种类、pct、目标、
      扣款前后余额、手续费、发出的兵，以及落地那一拍目标的领土 / 余额）。
口径：
  - 「一组连发」= 同一个号对同一个目标的进攻指令，相邻两条的落地拍相差 ≤ gap（默认 12 拍；策略每 5 拍一个决策拍，
    指令从发出到生效要 6~19 拍，所以相邻决策拍发出的指令落地间隔不超过 12 拍左右）。只统计 ≥2 条的组。
  - 「重复部分」= 组里第 2 条起发出的兵和手续费（发这些指令时，前面的指令还没生效，策略看到的局面和发第 1 条时一样）。
  - 「吃掉整块所需」= 1.5×目标领土 + 1.78×目标余额（取组里第 1 条落地时目标的领土 / 余额；统筹广播 0003 事实 1 的口径）。
    「超出部分」= max(0, 组内发兵合计 − 吃掉整块所需)。按 12% 小额脉冲逐条加码的组不会超出，这一栏是 0。
输出：out/<matchId>/repeat_sends.txt、repeat_sends.json
"""
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def fmt(x):
    return f"{int(round(x)):,}"


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    mid = args[0]
    gap = int(args[args.index("--gap") + 1]) if "--gap" in args else 12
    top = int(args[args.index("--top") + 1]) if "--top" in args else 14
    out = os.path.join(HERE, "..", "out", mid)
    src = os.path.join(out, "cmd_effect.tsv")
    if not os.path.exists(src):
        print(f"缺 {src}：先跑 67_troop_flow.mjs {mid}")
        sys.exit(2)
    rows = []
    for r in csv.DictReader(open(src, encoding="utf-8"), delimiter="\t"):
        if r["kind"] != "attack" or int(r["spent"]) <= 0:
            continue
        rows.append({"t": int(r["t"]), "bot": r["bot"], "pct": int(r["pct"]), "target": r["target"], "tname": r["tname"] or "?",
                     "b0": int(r["b0"]), "troops": int(r["troops"]), "fee": int(r["fee"]), "terr": int(r["terr"]),
                     "tTerr": int(r["tTerr"] or 0), "tBal": int(r["tBal"] or 0), "tHuman": r.get("tHuman", "0") == "1"})
    rows.sort(key=lambda r: (r["bot"], r["target"], r["t"]))
    groups = []
    cur = []
    for r in rows:
        if cur and (r["bot"] != cur[-1]["bot"] or r["target"] != cur[-1]["target"] or r["t"] - cur[-1]["t"] > gap):
            if len(cur) >= 2:
                groups.append(cur)
            cur = []
        cur.append(r)
    if len(cur) >= 2:
        groups.append(cur)

    def kind_of(g):
        if g[0]["tname"].startswith("无主地"):
            return "无主地"
        return "真人" if g[0]["tHuman"] else "内置 AI"

    recs = []
    for g in groups:
        tot = sum(r["troops"] for r in g)
        fee = sum(r["fee"] for r in g)
        rep = sum(r["troops"] for r in g[1:])
        repfee = sum(r["fee"] for r in g[1:])
        k = kind_of(g)
        need = None if k == "无主地" else 1.5 * g[0]["tTerr"] + 1.78 * g[0]["tBal"]
        over = 0 if need is None else max(0, tot - need)
        recs.append({"bot": g[0]["bot"], "t0": g[0]["t"], "t1": g[-1]["t"], "n": len(g), "kind": k, "target": g[0]["tname"],
                     "pcts": [r["pct"] for r in g], "troops": tot, "fee": fee, "repeatTroops": rep, "repeatFee": repfee,
                     "b0": g[0]["b0"], "terr": g[0]["terr"], "tTerr": g[0]["tTerr"], "tBal": g[0]["tBal"],
                     "need": None if need is None else int(round(need)), "over": int(round(over)), "share": tot / max(1, g[0]["b0"])})
    L = [f"# {mid} 同一目标的连发进攻（相邻两条落地拍相差 ≤{gap}；只算 ≥2 条的组；数字全部是引擎重演出的真实扣款）"]
    all_atk = len(rows)
    in_grp = sum(r["n"] for r in recs)
    L.append(f"# 全部生效的进攻指令 {all_atk} 条，其中 {in_grp} 条在连发组里（{len(recs)} 组）")
    L.append("")
    L.append("A. 按目标类别")
    L.append("类别\t组数\t指令条数\t发兵合计\t手续费合计\t重复部分（第 2 条起）兵 / 费\t超出「吃掉整块所需」的兵")
    summ = {}
    for k in ("真人", "内置 AI", "无主地"):
        gs = [r for r in recs if r["kind"] == k]
        summ[k] = {"groups": len(gs), "cmds": sum(r["n"] for r in gs), "troops": sum(r["troops"] for r in gs), "fee": sum(r["fee"] for r in gs),
                   "repeatTroops": sum(r["repeatTroops"] for r in gs), "repeatFee": sum(r["repeatFee"] for r in gs), "over": sum(r["over"] for r in gs),
                   "overGroups": sum(1 for r in gs if r["over"] > 0)}
        s = summ[k]
        L.append(f"{k}\t{s['groups']}\t{s['cmds']}\t{fmt(s['troops'])}\t{fmt(s['fee'])}\t{fmt(s['repeatTroops'])} / {fmt(s['repeatFee'])}\t{fmt(s['over'])}（{s['overGroups']} 组）")
    L.append("")
    L.append("B. 每个号（只算对真人的组）")
    L.append("号\t组数\t指令条数\t发兵合计\t重复部分兵 / 费\t超出的兵（组数）\t一组里花掉余额最多的一次")
    per = {}
    for b in sorted({r["bot"] for r in recs}):
        gs = [r for r in recs if r["bot"] == b and r["kind"] == "真人"]
        if not gs:
            continue
        mx = max(gs, key=lambda r: r["share"])
        per[b] = {"groups": len(gs), "cmds": sum(r["n"] for r in gs), "troops": sum(r["troops"] for r in gs), "repeatTroops": sum(r["repeatTroops"] for r in gs),
                  "repeatFee": sum(r["repeatFee"] for r in gs), "over": sum(r["over"] for r in gs), "overGroups": sum(1 for r in gs if r["over"] > 0)}
        s = per[b]
        L.append(f"{b}\t{s['groups']}\t{s['cmds']}\t{fmt(s['troops'])}\t{fmt(s['repeatTroops'])} / {fmt(s['repeatFee'])}\t{fmt(s['over'])}（{s['overGroups']}）\t"
                 f"t={mx['t0']}~{mx['t1']} {mx['n']} 条 → {mx['target']}，发兵 {fmt(mx['troops'])} = 第 1 条落地前余额的 {100 * mx['share']:.0f}%")
    L.append("")
    L.append(f"C. 对真人 / 内置 AI 的连发组，按「超出的兵」再按发兵合计排，前 {top} 组")
    L.append("号\t落地拍\t条数\tpct\t目标（第 1 条落地时 领土 / 余额）\t发兵合计（手续费）\t吃掉整块所需\t超出\t第 1 条落地前自己的 余额 / 领土")
    for r in sorted([r for r in recs if r["kind"] != "无主地"], key=lambda r: (-r["over"], -r["troops"]))[:top]:
        L.append(f"{r['bot']}\t{r['t0']}~{r['t1']}\t{r['n']}\t{'/'.join(str(p) for p in r['pcts'])}\t{r['target']}（{fmt(r['tTerr'])} 格 / {fmt(r['tBal'])} 兵）\t"
                 f"{fmt(r['troops'])}（{fmt(r['fee'])}）\t{fmt(r['need'])}\t{fmt(r['over'])}\t{fmt(r['b0'])} / {fmt(r['terr'])}")
    txt = "\n".join(L) + "\n"
    open(os.path.join(out, "repeat_sends.txt"), "w", encoding="utf-8").write(txt)
    json.dump({"matchId": mid, "gap": gap, "attackCmds": all_atk, "inGroups": in_grp, "byKind": summ, "perBot": per, "groups": recs},
              open(os.path.join(out, "repeat_sends.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print(txt)


if __name__ == "__main__":
    main()
