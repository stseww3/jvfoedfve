#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""51_retarget_check.py — R07：晚到的进攻落地时目标变成了谁。

问题：指令晚到几十到几百拍时，录像里的目标和策略发令时的目标是不是同一个？
  录像里每条进攻是 (pct, 目标玩家号)；影子（65_shadow.mjs，同一份策略、没有延迟）每个决策拍给出 (pct, 目标)。
做法：对录像里我方每条落地的进攻，在它之前 --win 拍内找「同号、同 pct」的影子指令：
  same   = 其中有一条目标相同（照原样落地）
  toNeut = 落地目标是无主地（512），影子里同 pct 的指令目标都是别人 → 这些目标在落地拍是否已经没有领土（truth_all.tsv 最近一次采样）
  toOther= 落地目标是另一个玩家（不是无主地），影子里同 pct 的指令没有一条指向它
  none   = 影子里没有同 pct 的指令（配不上，不下结论）
只读 out/<id>/humans_cmd.tsv、shadow_cmds.tsv、truth_all.tsv。

用法：python3 51_retarget_check.py <matchId> [--win 460]
输出：out/<matchId>/retarget_check.txt
"""
import csv
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SQUAD = ("sora_w", "ryan_m", "noah88", "zexos1", "talon5", "alex_k", "leo_tx", "zero_7", "kaito9", "riku_x")


def load(p):
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def bot_of(name):
    for b in SQUAD:
        if b in name:
            return b
    return None


def main():
    mid = sys.argv[1]
    win = 460
    if "--win" in sys.argv:
        win = int(sys.argv[sys.argv.index("--win") + 1])
    out_dir = os.path.join(HERE, "..", "out", mid)
    landed = [r for r in load(os.path.join(out_dir, "humans_cmd.tsv")) if r["squad"] == "1" and r["kind"] == "attack"]
    shadow = [r for r in load(os.path.join(out_dir, "shadow_cmds.tsv")) if r["kind"] == "attack"]
    by = defaultdict(list)
    for r in shadow:
        by[(r["bot"], int(r["pct"]))].append((int(r["t"]), int(r["target"]), r["targetName"]))
    terr = defaultdict(list)  # p -> [(t, terr)]
    for r in load(os.path.join(out_dir, "truth_all.tsv")):
        terr[int(r["p"])].append((int(r["t"]), int(r["terr"])))

    def terr_at(p, t):
        best = None
        for tt, v in terr.get(p, []):
            if tt <= t:
                best = (tt, v)
        last = terr.get(p, [])[-1][0] if terr.get(p) else None
        if best is None:
            return None
        # truth_all 只列领土 >0 的玩家：最后一次出现之后就是没有领土了
        if last is not None and t - last >= 90 and best[0] == last:
            return 0
        return best[1]

    cuts = [(0, 600), (600, 1500), (1500, 3000), (3000, 10 ** 9)]
    names = ["0~600", "600~1500", "1500~3000", "3000+"]
    stat = [defaultdict(int) for _ in cuts]
    dead_stat = [defaultdict(int) for _ in cuts]
    examples = []
    for r in landed:
        t = int(r["t"])
        bot = bot_of(r["name"])
        pct = int(r["pct"])
        tgt = int(r["target"])
        i = next(k for k, (a, b) in enumerate(cuts) if a <= t < b)
        cands = [c for c in by.get((bot, pct), []) if t - win <= c[0] <= t]
        if not cands:
            stat[i]["none"] += 1
            continue
        if any(c[1] == tgt for c in cands):
            stat[i]["same"] += 1
            continue
        if tgt == 512:
            stat[i]["toNeut"] += 1
            # 影子里同 pct 的最晚一条的目标在落地拍还有没有领土
            c = max(cands)
            v = terr_at(c[1], t)
            dead_stat[i]["dead" if v == 0 else ("alive" if v else "unknown")] += 1
            if v and len(examples) < 400:
                examples.append((t, bot, pct, c[0], c[2], v, "无主地"))
        else:
            stat[i]["toOther"] += 1
            c = max(cands)
            examples.append((t, bot, pct, c[0], c[2], terr_at(c[1], t), f"{r['tt']}:{tgt}"))
    lines = [f"# {mid} 晚到的进攻落地时目标变成了谁（51_retarget_check.py；影子窗口 {win} 拍；只算我方号落地的进攻）",
             "# same = 影子里同号同 pct 的指令有一条目标相同；toNeut = 落地目标是无主地、影子里同 pct 的目标都是别人；toOther = 落地目标是另一个玩家；none = 影子里没有同 pct 的指令",
             "", "时段\t落地进攻\tsame\ttoNeut（影子目标落地时：已无领土 / 仍有领土 / 查不到）\ttoOther\tnone"]
    for i, n in enumerate(names):
        s = stat[i]
        tot = sum(s.values())
        d = dead_stat[i]
        lines.append(f"{n}\t{tot}\t{s['same']}\t{s['toNeut']}（{d['dead']} / {d['alive']} / {d['unknown']}）\t{s['toOther']}\t{s['none']}")
    lines.append("")
    lines.append("toOther 与「toNeut 但影子目标仍有领土」的逐条（落地拍 号 pct | 影子最晚一条同 pct 的发令拍 → 目标（落地拍它的领土）| 落地目标）")
    for e in examples[:60]:
        lines.append(f"  t={e[0]} {e[1]} pct={e[2]} | 影子 t={e[3]} → {e[4]}（{e[5]} 格）| 落地 {e[6]}")
    if not examples:
        lines.append("  （无）")
    out = os.path.join(out_dir, "retarget_check.txt")
    open(out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines[:14 + min(len(examples), 40)]))


if __name__ == "__main__":
    main()
