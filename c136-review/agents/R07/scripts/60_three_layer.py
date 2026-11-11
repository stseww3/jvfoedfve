#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""60_three_layer.py — R07：11 局带录像的局，「好地没抢到」按三层并排（只并排，不分摊）。

  ① 站位：46_voronoi.mjs 的人均天然地盘倍数（我方人均 ÷ 全场人均）、最近队友中位数。
  ② 留底 / 比价：47_delay_periods.py 的 early 节（只有 A082 / A007 / A070 有）：600~1500 贴着内置 AI 的决策拍里出手、卡在留底、价高各多少。
  ③ 执行：600~1500 影子想打内置 AI 的条数和兵 → 实际落在内置 AI 身上的条数和兵（47_delay_periods.py 的 whiff 节）；
          58_throughput.py 的连发窗口（一个号 90 拍发出 ≥10 条）在 600~1500 的个数、窗口里发出 / 落地；57_exec_census.py 的「没落地」。
  结果：身边内置 AI 的脚印到 1500 拍我方吃到的比例、别的真人吃到的比例；1500 拍实际领土 ÷ 天然地盘（我方 / 其他各组范围）。

用法：python3 60_three_layer.py      （先跑 56_cross_match.py、57_exec_census.py、58_throughput.py）
输出：out/_cross/three_layer.txt
"""
import csv
import json
import os
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out")
CROSS = os.path.join(OUT, "_cross")
GAMES = ["A062", "A033", "A039", "A079", "A061", "A053", "A091", "A089", "A082", "A007", "A070"]


def jload(p):
    try:
        return json.load(open(p, encoding="utf-8"))
    except (OSError, ValueError):
        return None


def main():
    cm = jload(os.path.join(CROSS, "cross_match.json")) or {}
    census = {r["matchId"]: r for r in csv.DictReader(open(os.path.join(CROSS, "exec_census.tsv"), encoding="utf-8"), delimiter="\t")}
    flood = {r["matchId"]: r for r in csv.DictReader(open(os.path.join(CROSS, "throughput_flood.tsv"), encoding="utf-8"), delimiter="\t")}
    L = []
    P = L.append
    P("# 好地没抢到：三层并排（60_three_layer.py；11 局带录像的局）")
    P("")
    P("## 表 A：局 | ① 人均天然地盘倍数、最近队友中位数（像素）| ③ 600~1500 影子想打内置 AI：条 / 兵 → 落在内置 AI 身上：条 / 兵（条数比、兵数比）| ③ 600~1500 连发窗口数、窗口里发出 / 落地 | ③ 全局进攻和船没落地（占发出）"
      " | 结果：身边 AI 脚印到 1500 我方吃到 / 别的真人吃到 | 1500 拍 实际 ÷ 天然：我方 / 其他各组")
    rows = []
    for g in GAMES:
        v = jload(os.path.join(OUT, g, "voronoi.json"))
        dp = jload(os.path.join(OUT, g, "delay_periods.json"))
        j = cm.get(g, {})
        per_head = v["groups"]["我方号"]["perHeadRel"] if v else None
        near = j.get("nearMed")
        w = (dp or {}).get("whiff", {}).get("600~1500") if dp else None
        if w and w.get("wantAiN"):
            c3 = (f"{w['wantAiN']} / {w.get('wantAiTroops', 0):,} → {w.get('onAiN', 0)} / {w.get('onAiTroops', 0):,}"
                  f"（{w.get('onAiN', 0) / w['wantAiN']:.0%}、{w.get('onAiTroops', 0) / max(1, w.get('wantAiTroops', 0)):.0%}）")
            r_n = w.get("onAiN", 0) / w["wantAiN"]
            r_t = w.get("onAiTroops", 0) / max(1, w.get("wantAiTroops", 0))
        else:
            c3, r_n, r_t = "（没有影子对照）", None, None
        f = flood.get(g)
        cf = f"{f['w600_1500']} 个、全局窗口里 {f['issuedInFlood']} / {f['landedInFlood']}" if f else "-"
        c = census.get(g, {})
        miss = f"{c['atkMiss']} / {c['atkIssued']}（{int(c['atkMiss']) / max(1, int(c['atkIssued'])):.0%}）" if c.get("atkIssued") else "-"
        a = (v or {}).get("ai", {}).get("我方号")
        if a and "1500" in a["to"]:
            cells = max(1, a["cells"])
            ai = f"{a['to']['1500']['own'] / cells:.0%} / {a['to']['1500']['human'] / cells:.0%}"
            ai_own = a["to"]["1500"]["own"] / cells
        else:
            ai, ai_own = "-", None
        cap = j.get("cap1500")
        co = None
        if v:
            at = v["at"].get("1500", {})
            oth = [x["ratio"] for k, x in at.items() if k != "我方号" and "其他真人" not in k and x.get("vor", 0) > 0 and v["groups"].get(k, {}).get("n", 0) >= 2]
            co = (min(oth), max(oth)) if oth else None
        cap_txt = f"{cap:.2f} / {co[0]:.2f}~{co[1]:.2f}" if cap is not None and co else "-"
        P(f"{g}\t{per_head:.2f}、{near:.0f}\t{c3}\t{cf}\t{miss}\t{ai}\t{cap_txt}")
        rows.append((g, per_head, r_n, r_t, ai_own, cap, int(f["w600_1500"]) if f else 0))

    P("")
    P("## 表 B：② 600~1500 贴着内置 AI 的决策拍（影子；只有三局有）：局 | 决策拍 | 出手 | 卡在留底 | 价高或没有动机 | 留底里参照队友的 safeFinite | 参照敌方真人的 safeFinite")
    for g in GAMES:
        dp = jload(os.path.join(OUT, g, "delay_periods.json"))
        e = (dp or {}).get("early", {})
        for k, x in e.items():
            if "600~1500" in k and "AI" in k:
                cls = x.get("cls") or {}

                def pick(sub, cls=cls):
                    return sum(n for name, n in cls.items() if sub in name)
                P(f"{g}\t{x['dec']}\t{x['fired']}\t{x['floor']}\t{pick('不让打')}\t{pick('safeFinite（参照我方队友）')}\t{pick('safeFinite（参照敌方真人）')}")

    P("")
    P("## 表 C：把 11 局按一个量分成两半，看另一个量（只是并排；局数太少，不做检验）")
    def split(key_idx, label, res_idx, res_label, fmt="{:.0%}"):
        have = [r for r in rows if r[key_idx] is not None and r[res_idx] is not None]
        have.sort(key=lambda r: r[key_idx])
        h = len(have) // 2
        lo, hi = have[:h], have[h:]
        P(f"按「{label}」从小到大：小的一半 {'、'.join(r[0] for r in lo)}：{res_label}中位 {fmt.format(statistics.median([r[res_idx] for r in lo]))}；"
          f"大的一半 {'、'.join(r[0] for r in hi)}：{res_label}中位 {fmt.format(statistics.median([r[res_idx] for r in hi]))}")
    split(1, "人均天然地盘倍数", 4, "AI 脚印到 1500 我方吃到")
    split(1, "人均天然地盘倍数", 5, "1500 拍实际 ÷ 天然", "{:.2f}")
    split(3, "想打 AI 的兵落在 AI 身上的比例", 4, "AI 脚印到 1500 我方吃到")
    split(3, "想打 AI 的兵落在 AI 身上的比例", 5, "1500 拍实际 ÷ 天然", "{:.2f}")
    split(6, "600~1500 连发窗口数", 4, "AI 脚印到 1500 我方吃到")
    split(6, "600~1500 连发窗口数", 5, "1500 拍实际 ÷ 天然", "{:.2f}")

    open(os.path.join(CROSS, "three_layer.txt"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
