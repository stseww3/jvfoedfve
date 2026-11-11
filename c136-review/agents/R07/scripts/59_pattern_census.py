#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""59_pattern_census.py — R07：把 42_patterns.py --all 的结果（out/common/patterns_all.json，全部对局包）按模式汇成一张表。

每个模式取一个「主计数」（窗口数 / 笔数 / 号数），列：命中的局数、主计数合计、每局中位（只算命中的局）、
按结果分（赢 / 输 / 散队里有号赢）命中的局数，以及主计数最大的 3 局。模式的定义见 42_patterns.py 的文件头。

用法：python3 42_patterns.py --all && python3 59_pattern_census.py
输出：out/_cross/pattern_census.txt、out/_cross/pattern_census.tsv
"""
import json
import os
import statistics
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "out", "common", "patterns_all.json")
CROSS = os.path.join(HERE, "..", "out", "_cross")

# 模式 -> (主计数字段, 单位, 附带求和的字段和它的名字)
MAIN = [
    ("R07-SP-CLUSTER", "closeLt140", "号（最近队友 <140 像素）", None),
    ("R07-SP-SCATTER", "farGe300", "号（最近队友 ≥300 像素）", ("earlyGone", "其中 t<2400 就没了的号")),
    ("R07-OP-BOXED-EARLY", "bots", "号（t≤1620 已被队友围死）", None),
    ("R07-MT-PRE2400-HOLD", "idleNbWindows", "窗口（接敌、零进攻；到 t=2400）", ("nbWindows", "接敌窗口")),
    ("R07-EC-IDLE-RICH", "windows", "窗口（接敌、密度 ≥60、零进攻）", None),
    ("R07-EC-BOXED-RICH", "snaps", "快照（围死、密度 ≥60）", ("sumBal", "余额合计")),
    ("R07-EC-SOFTCAP", "snaps", "快照（密度 ≥100）", None),
    ("R07-EC-HARDCAP", "snaps", "快照（密度 ≥145）", None),
    ("R07-EC-NO-OUTLET", "spans", "段（围死、一条指令都发不出）", ("snaps", "快照")),
    ("R07-EC-NEUT-LOCK", "spans", "段（贴着 1~5 格无主地、不动）", ("snaps", "快照")),
    ("R07-DF-PASSIVE-BLEED", "windows", "窗口（丢地、有兵、零进攻）", ("px", "丢地格数")),
    ("R07-DF-RICH-BLEED", "windows", "窗口（丢地、密度 ≥60、零进攻）", ("px", "丢地格数")),
    ("R07-EG-FRONT-STARVE", "snaps", "快照（前线在丢地、后排握着过半的兵）", ("px", "丢地格数")),
    ("R07-AT-BIG-BURN", "windows", "窗口（余额跌 ≥30%、每格 ≥100 兵或没涨地）", ("sumDrop", "跌掉的兵")),
    ("R07-DN-TAX51", "n", "笔（到账 ≤ 手续费）", ("fee", "手续费")),
    ("R07-DN-CHAIN18", "pairs", "对（两笔捐款隔 ≤24 拍）", None),
    ("R07-DN-IDLE-RECV", "denseN", "笔（收方密度 ≥60）", ("denseFee", "手续费")),
    ("R07-DN-DEAD-RECV", "n", "笔（收方之后 90 拍没发指令且在丢地）", ("fee", "手续费")),
    ("R07-DN-PINGPONG", "n", "笔（400 拍内回捐）", ("fee", "手续费")),
    ("R07-IO-DUP-ASSIST", "bursts", "串（≤12 拍连发 ≥3 条协防）", ("cmds", "条")),
    ("R07-IO-CRASH", "errors", "条报错", None),
    ("R07-GOOD-SAVED-PUSH", "n", "次（正例：攒兵换地）", ("px", "涨地格数")),
    ("R07-GOOD-BOXED-BOAT", "bots", "号（正例：围死后靠船解套）", ("px", "涨地格数")),
]


def main():
    games = json.load(open(SRC, encoding="utf-8"))
    res_all = Counter(g["result"] for g in games)
    coh_all = Counter(g["cohort"] for g in games)
    L = []
    P = L.append
    P(f"# 机械模式普查（42_patterns.py --all → 59_pattern_census.py）：{len(games)} 个对局包"
      f"（{'、'.join(f'{k} {v}' for k, v in coh_all.most_common())}；结果：{'、'.join(f'{k} {v}' for k, v in res_all.most_common())}）")
    P("# 只用日志和 CSV，不重演录像。「命中」= 主计数 ≥1。并排放着看，不是因果。")
    P("")
    P("模式 | 主计数的单位 | 命中的局数（占全部）| 主计数合计 | 命中局的中位 | 赢的局里命中 / 输的局里命中 / 散队有号赢的局里命中 | 主计数最大的 3 局 | 附带")
    rows = []
    for name, field, unit, extra in MAIN:
        vals = []
        for g in games:
            p = g["patterns"].get(name) or {}
            v = p.get(field) or 0
            vals.append((v, g, p))
        hit = [(v, g, p) for v, g, p in vals if v]
        tot = sum(v for v, _, _ in hit)
        med = statistics.median([v for v, _, _ in hit]) if hit else 0
        by = Counter(g["result"] for _, g, _ in hit)
        top = sorted(hit, key=lambda x: -x[0])[:3]
        ex = ""
        if extra:
            ex = f"{extra[1]} {sum((p.get(extra[0]) or 0) for _, _, p in hit):,}"
        P(f"{name} | {unit} | {len(hit)}（{len(hit) / len(games):.0%}）| {tot:,} | {med:g} | "
          f"{by.get('won', 0)}/{res_all.get('won', 0)} / {by.get('lost', 0)}/{res_all.get('lost', 0)} / {by.get('split_straggler_won', 0)}/{res_all.get('split_straggler_won', 0)} | "
          + "、".join(f"{g['matchId']} {v:,}" for v, g, _ in top) + f" | {ex}")
        rows.append((name, field, len(hit), tot, med, by.get("won", 0), by.get("lost", 0), by.get("split_straggler_won", 0)))
    P("")
    P("## 赢的局和输的局，每局的中位数（全部局都算，没命中记 0）：模式 | 赢 | 输 | 散队有号赢")
    for name, field, unit, extra in MAIN:
        cells = []
        for res in ("won", "lost", "split_straggler_won"):
            v = [(g["patterns"].get(name) or {}).get(field) or 0 for g in games if g["result"] == res]
            cells.append(f"{statistics.median(v):g}" if v else "-")
        P(f"{name}（{field}）| " + " | ".join(cells))
    os.makedirs(CROSS, exist_ok=True)
    open(os.path.join(CROSS, "pattern_census.txt"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    with open(os.path.join(CROSS, "pattern_census.tsv"), "w", encoding="utf-8") as f:
        f.write("pattern\tfield\tgamesHit\ttotal\tmedianWhenHit\twonHit\tlostHit\tsplitHit\n")
        for r in rows:
            f.write("\t".join(str(x) for x in r) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
