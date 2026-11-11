#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""91_noop_cmds.py — 我方号被引擎收下的指令里有多少条「落地时什么也没发生」，以及指令是不是成批落地。R07

用法（在 scripts/ 目录下）：
    python3 91_noop_cmds.py <matchId> [--win 300] [--t1 2100] [--ai-cuts 0,540,990,1500]

输入：out/<matchId>/humans_cmd.tsv（74_side_flow.mjs：全场真人每条被引擎收下的指令，含发令前后余额 b0 / b1、发出的兵 troops、手续费 fee、
      目标类别 tt：N 无主地 / A 内置 AI / L 已离开的真人席位 / H 真人 / B 船 / D 捐款）、
      shadow_cmds.tsv（65_shadow.mjs：影子策略在每个决策拍想发的指令；影子的 cmds 计数与真日志逐快照一致时可当作「真号当时发出的指令」）。
口径：
  空指令 = 进攻类指令落地时余额一个兵都没动（b0 == b1，troops == 0，fee == 0）：目标已经不接壤、已经不存在，或没有空的进攻槽。
  批 = 同一个号同一拍落地的指令 ≥ 3 条。「批间隔」= 相邻两批的落地拍之差。
  落地间隔 = 同一个号相邻两个「有指令落地的拍」之差（策略每 5 拍决策一次；正常情况下连续出手时间隔是 5~10 拍）。
输出：out/<matchId>/noop_cmds.txt
  A. 每号 × 每个时间窗：影子想发的进攻条数 | 引擎收下的进攻条数 | 其中空指令 | 落地拍的个数 | ≥3 条的批数（批里的条数合计）
  B. 全队按时间窗合计 + 对照组（全场其他真人）同一窗口的空指令比例与批数
  C. 每号 ≥3 条的批的明细（落地拍、条数、空指令条数、批前→批后余额）
  D. 打内置 AI 的指令（t<--t1）：每号影子想发的条数 / 约兵（按发令拍余额估，指令没落地时下一拍会按同样的余额再估一次，所以是上限）
     对 引擎真正执行在内置 AI 身上的条数 / 兵；外加同一段落成空指令的条数。对照：全场其他真人打内置 AI 的条数 / 兵 / 空指令。
"""
import csv
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    mid = args[0]

    def opt(k, d):
        return args[args.index(k) + 1] if k in args else d
    win = int(opt("--win", 300))
    t1 = int(opt("--t1", 2100))
    out = os.path.join(HERE, "..", "out", mid)
    rows = list(csv.DictReader(open(os.path.join(out, "humans_cmd.tsv"), encoding="utf-8"), delimiter="\t"))
    players = {int(r["p"]): r for r in csv.DictReader(open(os.path.join(out, "truth_players.tsv"), encoding="utf-8"), delimiter="\t")}
    squad_names = {r["name"].split("] ")[-1]: int(r["p"]) for r in players.values() if r.get("squad")}
    sh = defaultdict(lambda: defaultdict(int))
    sh_path = os.path.join(out, "shadow_cmds.tsv")
    if os.path.exists(sh_path):
        for r in csv.DictReader(open(sh_path, encoding="utf-8"), delimiter="\t"):
            if r["kind"] == "attack":
                sh[r["bot"]][int(r["t"]) // win] += 1

    def is_squad(r):
        return r["squad"] not in ("", "0")

    acc = defaultdict(lambda: defaultdict(list))       # bot -> window -> rows
    others = defaultdict(list)                          # window -> rows of non-squad humans
    for r in rows:
        if r["kind"] != "attack":
            continue
        t = int(r["t"])
        if is_squad(r):
            name = r["name"].split("] ")[-1]
            acc[name][t // win].append(r)
        else:
            others[t // win].append(r)

    def noop(r):
        return int(r["b0"]) == int(r["b1"]) and int(r["troops"]) == 0 and int(r["fee"] or 0) == 0

    L = [f"# {mid} 落地时什么也没发生的指令与成批落地（humans_cmd.tsv；只算 attack；时间窗 {win} 拍，列到 t<{t1}）",
         "# 空指令 = 落地时余额没动（b0==b1、发兵 0、手续费 0）；批 = 同一个号同一拍落地 ≥3 条", "",
         "A. 每号 × 时间窗：影子想发 / 引擎收下 / 其中空指令 / 落地拍个数 / ≥3 条的批数（批里条数）/ 落地拍间隔中位数"]
    wins = list(range(0, t1 // win))
    L.append("号\t" + "\t".join(f"{w * win}~{w * win + win - 1}" for w in wins))
    tot = defaultdict(lambda: [0, 0, 0, 0, 0, 0])
    batches = defaultdict(list)
    for b in sorted(acc):
        cells = []
        for w in wins:
            rs = acc[b].get(w, [])
            by_t = defaultdict(list)
            for r in rs:
                by_t[int(r["t"])].append(r)
            n_noop = sum(1 for r in rs if noop(r))
            bt = [(t, v) for t, v in sorted(by_t.items()) if len(v) >= 3]
            for t, v in bt:
                batches[b].append((t, v))
            ts = sorted(by_t)
            gaps = sorted(ts[i + 1] - ts[i] for i in range(len(ts) - 1))
            gap = gaps[len(gaps) // 2] if gaps else "-"
            cells.append(f"{sh[b].get(w, 0)}/{len(rs)}/{n_noop}/{len(by_t)}/{len(bt)}({sum(len(v) for _, v in bt)})/{gap}")
            x = tot[w]
            x[0] += sh[b].get(w, 0)
            x[1] += len(rs)
            x[2] += n_noop
            x[3] += len(by_t)
            x[4] += len(bt)
            x[5] += sum(len(v) for _, v in bt)
        L.append(b + "\t" + "\t".join(cells))
    L += ["", "B. 全队合计 vs 全场其他真人（同一时间窗）",
          "窗口\t我方：影子想发 / 收下 / 空指令（占收下）/ 落地拍个数 / ≥3 条的批数（批里条数，占收下）\t其他真人：收下 / 空指令（占收下）/ ≥3 条的批数（批里条数，占收下）"]
    for w in wins:
        x = tot[w]
        o = others.get(w, [])
        o_noop = sum(1 for r in o if noop(r))
        by_pt = defaultdict(int)
        for r in o:
            by_pt[(r["p"], r["t"])] += 1
        o_b = [v for v in by_pt.values() if v >= 3]

        def pc(a, b_):
            return f"{100 * a / b_:.0f}%" if b_ else "-"
        L.append(f"{w * win}~{w * win + win - 1}\t{x[0]} / {x[1]} / {x[2]}（{pc(x[2], x[1])}）/ {x[3]} / {x[4]}（{x[5]}，{pc(x[5], x[1])}）\t"
                 f"{len(o)} / {o_noop}（{pc(o_noop, len(o))}）/ {len(o_b)}（{sum(o_b)}，{pc(sum(o_b), len(o))}）")
    # 全程（不限 t1）的批：最大的一批几条、一共几批；落地拍是不是都在 7 的倍数上（服务器 7 拍一个回合）
    by_bt = defaultdict(int)
    n_all = 0
    on7 = 0
    for r in rows:
        if r["kind"] != "attack" or not is_squad(r):
            continue
        n_all += 1
        on7 += 1 if int(r["t"]) % 7 == 0 else 0
        by_bt[(r["name"], int(r["t"]))] += 1
    sizes = [v for v in by_bt.values() if v >= 3]
    mx = max(sizes) if sizes else 0
    L += ["", f"B2. 全程：我方进攻指令 {n_all} 条，落地拍是 7 的倍数的 {on7} 条；同一号同一拍 ≥3 条的批 {len(sizes)} 个（{sum(sizes)} 条），"
              f"最大的一批 {mx} 条，这么大的批有 {sum(1 for v in sizes if v == mx)} 个；批的大小分布：" +
              "、".join(f"{k} 条×{sum(1 for v in sizes if v == k)}" for k in sorted(set(sizes)))]
    L += ["", "C. 我方 ≥3 条的批（落地拍 号 条数 | 空指令条数 | 目标类别计数 | 批前 → 批后余额 | 发兵合计）"]
    allb = []
    for b, lst in batches.items():
        for t, v in lst:
            allb.append((t, b, v))
    for t, b, v in sorted(allb):
        kinds = defaultdict(int)
        for r in v:
            kinds[r["tt"]] += 1
        b0 = int(v[0]["b0"])
        b1 = int(v[-1]["b1"])
        L.append(f"  {t} {b} ×{len(v)} | 空 {sum(1 for r in v if noop(r))} | " + " ".join(f"{k}:{n}" for k, n in sorted(kinds.items())) +
                 f" | {b0:,} → {b1:,} | 发兵 {sum(int(r['troops']) for r in v):,}")
    cuts = [int(x) for x in opt("--ai-cuts", f"0,{t1}").split(",")]
    L += ["", "D. 打内置 AI 的指令，按时间窗（影子按发令拍归窗，引擎按落地拍归窗）：号 | 影子想发 条 / 约兵 | 引擎执行在 AI 身上 条 / 兵 | 同窗空指令条数"]
    sh_rows = list(csv.DictReader(open(sh_path, encoding="utf-8"), delimiter="\t")) if os.path.exists(sh_path) else []
    for a0, a1 in zip(cuts, cuts[1:]):
        sh_ai = defaultdict(lambda: [0, 0])
        for r in sh_rows:
            if r["kind"] == "attack" and r["targetName"].startswith("AI#") and a0 <= int(r["t"]) < a1:
                sh_ai[r["bot"]][0] += 1
                sh_ai[r["bot"]][1] += int(r["troops"])
        ex_ai = defaultdict(lambda: [0, 0, 0])
        oth = [0, 0, 0, 0]
        for r in rows:
            if r["kind"] != "attack" or not (a0 <= int(r["t"]) < a1):
                continue
            if is_squad(r):
                name = r["name"].split("] ")[-1]
                if r["tt"] == "A":
                    ex_ai[name][0] += 1
                    ex_ai[name][1] += int(r["troops"])
                if noop(r):
                    ex_ai[name][2] += 1
            else:
                oth[3] += 1
                if r["tt"] == "A":
                    oth[0] += 1
                    oth[1] += int(r["troops"])
                if noop(r):
                    oth[2] += 1
        L.append(f"  -- t={a0}~{a1 - 1}")
        s0 = [0, 0, 0, 0, 0]
        for b in sorted(set(sh_ai) | set(ex_ai)):
            a, e = sh_ai[b], ex_ai[b]
            L.append(f"  {b} | {a[0]} / {a[1]:,} | {e[0]} / {e[1]:,} | {e[2]}")
            for i, v in enumerate((a[0], a[1], e[0], e[1], e[2])):
                s0[i] += v
        L.append(f"  合计 | {s0[0]} / {s0[1]:,} | {s0[2]} / {s0[3]:,} | {s0[4]}")
        L.append(f"  全场其他真人：进攻 {oth[3]} 条，其中打内置 AI {oth[0]} 条 / {oth[1]:,} 兵，空指令 {oth[2]} 条")
    txt = "\n".join(L) + "\n"
    open(os.path.join(out, "noop_cmds.txt"), "w", encoding="utf-8").write(txt)
    print(txt)


if __name__ == "__main__":
    main()
