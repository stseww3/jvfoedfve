#!/usr/bin/env python3
"""61_truth_view.py — R07：把 60_truth.cjs 的真引擎重放结果整理成可读的全场真值表。

用法：python3 61_truth_view.py <matchId> [--step 90] [--at t1,t2,...] [--bot name] [--atk t0 t1]
输入：c136-review/agents/R07/out/<matchId>/truth_{players,teams,bots,atk,all}.tsv（先跑 60_truth.cjs）
输出（stdout，并写 out/<matchId>/truth_view.txt 当没有 --bot/--atk 时）：
  A. 各队领土份额/余额/在场人数（每 step 拍；份额 = 领土 / 全图陆地）
  B. 我方每个号的 领土/余额/密度/状态（state=2 表示已离开、由内置 AI 接管）
  C. 离开拍（state 第一次变 2）、阵亡拍（alive 第一次变 0）
  D. 我方号被谁打（进攻槽里的兵，按 进攻方×被打方 汇总：首末拍、采样次数、峰值兵力）
  E. 我方号打谁（同上）
"""
import csv
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = "/agent/repos/c136-data/bundles"


def load(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def main():
    argv = sys.argv[1:]
    mid = argv[0]
    step = 90
    at = None
    bot = None
    atkwin = None
    if "--step" in argv:
        step = int(argv[argv.index("--step") + 1])
    if "--at" in argv:
        at = [int(x) for x in argv[argv.index("--at") + 1].split(",")]
    if "--bot" in argv:
        bot = argv[argv.index("--bot") + 1]
    if "--atk" in argv:
        k = argv.index("--atk")
        atkwin = (int(argv[k + 1]), int(argv[k + 2]))
    out = os.path.join(HERE, "..", "out", mid)
    players = load(os.path.join(out, "truth_players.tsv"))
    teams = load(os.path.join(out, "truth_teams.tsv"))
    bots = load(os.path.join(out, "truth_bots.tsv"))
    atk = load(os.path.join(out, "truth_atk.tsv"))
    card = json.load(open(os.path.join(DATA, mid, "card.json")))
    land = card["mapLand"]
    name = {int(r["p"]): r["name"] for r in players}
    team = {int(r["p"]): int(r["team"]) for r in players}
    human = {int(r["p"]): r["human"] == "1" for r in players}
    squad = {int(r["p"]): r["squad"] for r in players if r["squad"]}
    my_team = sorted(set(team[p] for p in squad))
    lines = []
    P = lines.append

    def who(p):
        if p == 512:
            return "无主地"
        tag = "我" if p in squad else ("人" if human.get(p) else "机")
        return f"{name.get(p, p)}#{p}[T{team.get(p, '?')}{tag}]"

    if bot:
        pid = [p for p, b in squad.items() if b == bot][0]
        rows = [r for r in bots if int(r["p"]) == pid]
        ts = at or sorted(set(int(r["t"]) for r in rows if int(r["t"]) % step == 0))
        bt = {int(r["t"]): r for r in rows}
        a_by_t = defaultdict(list)
        for r in atk:
            a_by_t[int(r["t"])].append(r)
        print(f"# {mid} {bot}#{pid}：t terr bal dens alive state boats | 被打(进攻方:兵) | 在打(目标:兵)")
        for t in ts:
            r = bt.get(t)
            if not r:
                continue
            terr, bal = int(r["terr"]), int(r["bal"])
            ins = [f"{who(int(a['from']))}:{a['troops']}" for a in a_by_t.get(t, []) if a["dir"] == "in" and int(a["to"]) == pid]
            outs = [f"{who(int(a['to']))}:{a['troops']}" for a in a_by_t.get(t, []) if a["dir"] == "out" and int(a["from"]) == pid]
            dens = bal / terr if terr else 0
            print(f"{t}\t{terr}\t{bal}\t{dens:.1f}\t{r['alive']}\t{r['state']}\t{r['boats']}\t| {' '.join(ins) or '-'} | {' '.join(outs) or '-'}")
        return

    if atkwin:
        t0, t1 = atkwin
        print(f"# {mid} 进攻槽明细 {t0}~{t1}：t dir 进攻方 → 目标 兵")
        for r in atk:
            t = int(r["t"])
            if t0 <= t <= t1:
                print(f"{t}\t{r['dir']}\t{who(int(r['from']))} → {who(int(r['to']))}\t{r['troops']}")
        return

    P(f"=== {mid} 真引擎重放全场真值（60_truth.cjs；与 traj.csv 对账见 truth_check.txt）===")
    P(open(os.path.join(out, "truth_check.txt")).read().strip())
    P(f"我方所在队：{my_team}；全图陆地 {land}")
    P("")
    P("A. 各队领土份额%（括号内：余额合计(万)/在场人数）；队号 0 = 无队伍的内置 AI")
    tt = defaultdict(dict)
    for r in teams:
        tt[int(r["t"])][int(r["team"])] = (int(r["terr"]), int(r["bal"]), int(r["alive"]))
    tlist = at or [t for t in sorted(tt) if t % step == 0]
    tks = sorted(set(k for t in tt for k in tt[t]))
    P("t\t" + "\t".join(f"T{k}" for k in tks) + "\t我方号合计%(格/余额万/密度)")
    bots_by_t = defaultdict(dict)
    for r in bots:
        bots_by_t[int(r["t"])][int(r["p"])] = r
    for t in tlist:
        if t not in tt:
            continue
        cells = []
        for k in tks:
            v = tt[t].get(k)
            cells.append(f"{100 * v[0] / land:.1f}({v[1] / 1e4:.0f}/{v[2]})" if v else "-")
        sq = bots_by_t.get(t, {})
        sterr = sum(int(r["terr"]) for r in sq.values() if r["alive"] == "1" and r["state"] != "2")
        sbal = sum(int(r["bal"]) for r in sq.values() if r["alive"] == "1" and r["state"] != "2")
        lterr = sum(int(r["terr"]) for r in sq.values() if r["alive"] == "1" and r["state"] == "2")
        P(f"{t}\t" + "\t".join(cells) + f"\t{100 * sterr / land:.2f}({sterr}/{sbal / 1e4:.0f}/{(sbal / sterr if sterr else 0):.0f}) 另:已离开号 {lterr} 格")
    P("")
    P("B. 我方每个号：领土/余额(千)/密度；L=已离开(内置 AI 接管)；x=已出局")
    order = sorted(squad, key=lambda p: squad[p])
    P("t\t" + "\t".join(squad[p] for p in order))
    for t in tlist:
        sq = bots_by_t.get(t)
        if not sq:
            continue
        cells = []
        for p in order:
            r = sq.get(p)
            if not r or r["alive"] != "1":
                cells.append("x")
                continue
            terr, bal = int(r["terr"]), int(r["bal"])
            cells.append(f"{terr}/{bal // 1000}k/{(bal / terr if terr else 0):.0f}{'L' if r['state'] == '2' else ''}{'B' + r['boats'] if r['boats'] != '0' else ''}")
        P(f"{t}\t" + "\t".join(cells))
    P("")
    P("C. 离开拍 / 出局拍（10 拍粒度；离开 = state 变 2；出局 = alive 变 0）")
    for p in order:
        rows = [r for r in bots if int(r["p"]) == p]
        left = next((int(r["t"]) for r in rows if r["state"] == "2"), None)
        dead = next((int(r["t"]) for r in rows if r["alive"] != "1"), None)
        peak = max(rows, key=lambda r: int(r["terr"]))
        last_alive = [r for r in rows if r["alive"] == "1"]
        la = last_alive[-1] if last_alive else None
        P(f"  {squad[p]}#{p}: 离开≈{left} 出局≈{dead} 峰值领土 {peak['terr']}@{peak['t']}" + (f" 最后在场 t={la['t']} terr={la['terr']} bal={la['bal']}" if la else ""))
    P("")

    def agg(direction, key_from):
        d = defaultdict(lambda: {"n": 0, "t0": None, "t1": None, "peak": 0, "tpeak": None})
        for r in atk:
            if r["dir"] != direction:
                continue
            k = (int(r["from"]), int(r["to"]))
            a = d[k]
            t = int(r["t"])
            a["n"] += 1
            a["t0"] = t if a["t0"] is None else a["t0"]
            a["t1"] = t
            x = int(r["troops"])
            if x > a["peak"]:
                a["peak"], a["tpeak"] = x, t
        return d

    P("D. 我方号被谁打（进攻槽采样：每 10 拍一次；n=采样到的次数）")
    din = agg("in", True)
    for (f, to), a in sorted(din.items(), key=lambda kv: (squad.get(kv[0][1], ""), kv[1]["t0"])):
        P(f"  {squad.get(to, to)} ← {who(f)}: t={a['t0']}~{a['t1']} n={a['n']} 峰值兵 {a['peak']}@{a['tpeak']}")
    P("")
    P("E. 我方号打谁（同上；无主地不逐条列，只给合计）")
    dout = agg("out", False)
    neu = defaultdict(lambda: [0, None, None, 0])
    for (f, to), a in sorted(dout.items(), key=lambda kv: (squad.get(kv[0][0], ""), kv[1]["t0"])):
        if to == 512:
            x = neu[f]
            x[0] += a["n"]
            x[1] = a["t0"] if x[1] is None else x[1]
            x[2] = a["t1"]
            x[3] = max(x[3], a["peak"])
            continue
        P(f"  {squad.get(f, f)} → {who(to)}: t={a['t0']}~{a['t1']} n={a['n']} 峰值兵 {a['peak']}@{a['tpeak']}")
    for f, x in sorted(neu.items(), key=lambda kv: squad.get(kv[0], "")):
        P(f"  {squad.get(f, f)} → 无主地: t={x[1]}~{x[2]} n={x[0]} 峰值兵 {x[3]}")
    txt = "\n".join(lines) + "\n"
    if not at:
        with open(os.path.join(out, "truth_view.txt"), "w") as f:
            f.write(txt)
    sys.stdout.write(txt)


if __name__ == "__main__":
    main()
