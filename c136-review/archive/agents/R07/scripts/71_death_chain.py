#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""71_death_chain.py — R07：每个出局 / 离开的号的最后 500 拍（真账）。

依赖同一局已经跑过的：60_truth.cjs（truth_bots.tsv / truth_atk.tsv / truth_players.tsv）、
67_troop_flow.mjs（cmd_effect.tsv / tick_net.tsv）、results.csv。

对每个结算表里 event ∈ {died, left} 的号给出：
  · 出局拍（引擎里 alive 变 0 或 state 变 2 的第一个 10 拍采样）与结算表拍；
  · 最后 500 拍的领土 / 余额 / 密度（−500、−300、−200、−100、−50、最后一个采样）；
  · 这 500 拍里谁在打它（进攻槽峰值、起止拍）、它挨打掉了多少兵；
  · 它自己发了什么指令（进攻：目标、兵、费；捐出：给谁、到账、费；发船）；
  · 收到的捐款（别的号的捐款指令、内置 AI 送兵）。

用法：python3 71_death_chain.py <matchId> [--win 500]
输出：out/<matchId>/death_chain.txt / .json
"""
import csv
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = "/agent/repos/c136-data"


def tsv(path):
    if not os.path.exists(path):
        return []
    return list(csv.DictReader(open(path, encoding="utf-8"), delimiter="\t"))


def fmt(n):
    return f"{int(round(n)):,}"


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    mid = sys.argv[1]
    win = int(sys.argv[sys.argv.index("--win") + 1]) if "--win" in sys.argv else 500
    out = os.path.join(HERE, "..", "out", mid)
    bots = tsv(os.path.join(out, "truth_bots.tsv"))
    atk = tsv(os.path.join(out, "truth_atk.tsv"))
    players = {int(r["p"]): r for r in tsv(os.path.join(out, "truth_players.tsv"))}
    eff = tsv(os.path.join(out, "cmd_effect.tsv"))
    net = tsv(os.path.join(out, "tick_net.tsv"))
    res = list(csv.DictReader(open(os.path.join(DATA, "bundles", mid, "results.csv"), encoding="utf-8")))
    pid = {}
    series = defaultdict(list)
    for r in bots:
        pid[r["bot"]] = int(r["p"])
        series[r["bot"]].append((int(r["t"]), int(r["terr"]), int(float(r["bal"])), int(r["alive"]), int(r["state"])))

    def pname(q):
        if q >= 512:
            return "无主地"
        r = players.get(q)
        if not r:
            return f"AI#{q}"
        if r.get("human") in ("1", "true"):
            return f"{r['name'].strip()[:18]}#{q}（T{r['team']}）"
        return f"AI#{q}"

    L = [f"# {mid} 出局 / 离开的号的最后 {win} 拍（真账）"]
    J = {}
    for r in res:
        ev = r.get("event") or r.get("result")
        b = r.get("bot") or r.get("name")
        if ev not in ("died", "left") or b not in series:
            continue
        s = sorted(series[b])
        t_res = int(float(r.get("tick") or r.get("t") or 0))
        t_dead = next((t for t, terr, bal, al, st in s if not al), None)
        t_left = next((t for t, terr, bal, al, st in s if st == 2), None)
        t_end = t_dead if ev == "died" and t_dead is not None else (t_res if ev == "left" else s[-1][0])
        if ev == "died" and t_dead is None:
            t_end = t_res
        t0 = t_end - win

        def at(t):
            c = [x for x in s if x[0] <= t and x[3]]
            return c[-1] if c else s[0]

        pts = []
        for dt in (win, 300, 200, 100, 50, 0):
            x = at(t_end - dt)
            pts.append({"t": x[0], "terr": x[1], "bal": x[2], "dens": round(x[2] / max(1, x[1]), 1)})
        p = pid[b]
        # 谁在打它
        who = defaultdict(lambda: {"peak": 0, "t0": None, "t1": None, "tPeak": None})
        for a in atk:
            t = int(a["t"])
            if a["dir"] != "in" or int(a["to"]) != p or t < t0 or t > t_end + 10:
                continue
            o = who[int(a["from"])]
            tr = int(float(a["troops"]))
            if tr > o["peak"]:
                o["peak"], o["tPeak"] = tr, t
            o["t0"] = t if o["t0"] is None else o["t0"]
            o["t1"] = t
        killers = sorted(who.items(), key=lambda kv: -kv[1]["peak"])
        # 自己的指令
        mine = [e for e in eff if e["bot"] == b and t0 <= int(e["t"]) <= t_end + 10 and int(e["spent"]) > 0]
        a_by = defaultdict(lambda: [0, 0, 0, None, None])
        for e in mine:
            if e["kind"] != "attack":
                continue
            k = e["tname"] if e["tHuman"] == "1" else ("无主地" if int(e["target"]) >= 512 else "内置 AI")
            o = a_by[k]
            o[0] += 1
            o[1] += int(e["troops"])
            o[2] += int(e["fee"])
            o[3] = int(e["t"]) if o[3] is None else o[3]
            o[4] = int(e["t"])
        d_by = defaultdict(lambda: [0, 0, 0, None, None])
        for e in mine:
            if e["kind"] != "donate":
                continue
            o = d_by[e["tname"]]
            o[0] += 1
            o[1] += int(e["troops"])
            o[2] += int(e["fee"])
            o[3] = int(e["t"]) if o[3] is None else o[3]
            o[4] = int(e["t"])
        boats = [e for e in mine if e["kind"] in ("boat", "boatTo")]
        # 收到的捐款
        recv = [e for e in eff if e["kind"] == "donate" and int(e["target"]) == p and t0 <= int(e["t"]) <= t_end + 10 and int(e["spent"]) > 0]
        r_by = defaultdict(lambda: [0, 0])
        for e in recv:
            r_by[e["bot"]][0] += 1
            r_by[e["bot"]][1] += int(e["troops"])
        nn = [x for x in net if x["bot"] == b and t0 <= int(x["t0"]) <= t_end + 10]
        hit = sum(int(x["hit"]) for x in nn)
        eco = sum(int(x["eco"]) for x in nn)
        gift_in = sum(int(x["giftIn"]) for x in nn)
        gift_out = sum(int(x["giftOut"]) for x in nn)
        refund = sum(int(x["refund"]) for x in nn)
        don_out_n = sum(o[0] for o in d_by.values())
        don_out_amt = sum(o[1] for o in d_by.values())
        don_out_fee = sum(o[2] for o in d_by.values())
        don_in_n = sum(o[0] for o in r_by.values())
        don_in_amt = sum(o[1] for o in r_by.values())
        atk_tr = sum(o[1] for o in a_by.values())
        atk_fee = sum(o[2] for o in a_by.values())
        L.append("")
        L.append(f"## {b}（{ev}，结算表 t={t_res}，名次 {r.get('place')}" + (f"；引擎里出局采样 t={t_dead}" if t_dead is not None else "") + (f"；state=2（离开）采样 t={t_left}" if t_left is not None else "") + "）")
        L.append("  最后 %d 拍：" % win + " → ".join(f"t={x['t']} {fmt(x['terr'])} 格 / {fmt(x['bal'])} 兵 / 密度 {x['dens']:.0f}" for x in pts))
        L.append("  谁在打它：" + ("；".join(f"{pname(q)} {o['t0']}~{o['t1']} 进攻槽峰值 {fmt(o['peak'])}（t={o['tPeak']}）" for q, o in killers[:4]) or "没有记录到进攻槽"))
        L.append(f"  挨打掉的兵 {fmt(hit)}；利息地租 +{fmt(eco)}；退回 +{fmt(refund)}；内置 AI 送来 +{fmt(gift_in)}" + (f"；离开座位送走 {fmt(gift_out)}" if gift_out else ""))
        L.append("  自己的进攻：" + ("；".join(f"{k} {o[0]} 条 {fmt(o[1])} 兵 + 费 {fmt(o[2])}（{o[3]}~{o[4]}）" for k, o in sorted(a_by.items(), key=lambda kv: -kv[1][1])) or "0 条") + (f"；发船 {len(boats)} 条" if boats else ""))
        L.append("  捐出：" + ("；".join(f"→{k} {o[0]} 笔到账 {fmt(o[1])} + 费 {fmt(o[2])}（{o[3]}~{o[4]}）" for k, o in sorted(d_by.items(), key=lambda kv: -kv[1][1])) or "0 笔"))
        L.append("  收捐（捐款指令）：" + ("；".join(f"{k} {o[0]} 笔 {fmt(o[1])}" for k, o in sorted(r_by.items(), key=lambda kv: -kv[1][1])) or "0 笔") + f"；合计 {don_in_n} 笔 {fmt(don_in_amt)}")
        J[b] = {"event": ev, "tResult": t_res, "tDead": t_dead, "tLeft": t_left, "points": pts,
                "killers": [{"p": q, "name": pname(q), **o} for q, o in killers[:4]],
                "hit": hit, "eco": eco, "refund": refund, "giftIn": gift_in, "giftOut": gift_out,
                "atkN": sum(o[0] for o in a_by.values()), "atkTroops": atk_tr, "atkFee": atk_fee,
                "donOut500": {"n": don_out_n, "amt": don_out_amt, "fee": don_out_fee},
                "donIn500": {"n": don_in_n, "amt": don_in_amt, "rejFlag": 0}}
    txt = "\n".join(L) + "\n"
    open(os.path.join(out, "death_chain.txt"), "w", encoding="utf-8").write(txt)
    json.dump(J, open(os.path.join(out, "death_chain.json"), "w", encoding="utf-8"), ensure_ascii=False)
    sys.stdout.write(txt)


if __name__ == "__main__":
    main()
