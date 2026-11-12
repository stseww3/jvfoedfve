#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""56_cross_match.py — R07：15 局的跨局对照表（M6）。只读已有的逐局产物，不重演。

读：
  reviews/<id>.json                 分型、结果、时间线（份额）、阵亡、关键决策、模式实例
  out/<id>/spawn_truth.tsv          66_spawn_truth.mjs：真实落点、最近队友
  out/<id>/voronoi.json             46_voronoi.mjs：天然地盘、630 / 1500 拍实际拿到、身边内置 AI 的地归了谁
  out/<id>/delay_periods.json       47_delay_periods.py：四时段的延迟分位数、漏斗、落空 / 改记、成批 / 连发
  out/<id>/same_tick_batches.json   81_same_tick_batches.py：同一号同一拍落地 ≥3 条的批
  out/<id>/result_clock.txt         52_result_clock.py：出局上报时钟
  out/_spawn_seq_all.txt            54_spawn_seq.py 的多局汇总
  out/_issue_vs_land_all.txt        53_issue_vs_land.py 的多局汇总

用法：python3 56_cross_match.py
输出：out/_cross/cross_match.txt（全部表）、out/_cross/cross_match.json
"""
import csv
import json
import os
import re
import statistics
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
R07 = os.path.join(HERE, "..")
OUT = os.path.join(R07, "out")
GAMES = ["G01", "G04", "G07", "G00", "A062", "A033", "A039", "A079", "A061", "A053", "A091", "A089", "A082", "A007", "A070"]
PERIODS = ["0~600", "600~1500", "1500~3000", "3000+"]


def jload(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def pct(x, nd=1):
    return "-" if x is None else f"{100 * x:.{nd}f}%"


def num(x):
    return "-" if x is None else f"{x:,}"


def share_at(tl, t):
    """时间线里拍号最接近 t（差 ≤45 拍）的一行的我方领土份额"""
    best = None
    for r in tl:
        if abs(r["t"] - t) <= 45 and (best is None or abs(r["t"] - t) < abs(best["t"] - t)):
            best = r
    return best


def main():
    os.makedirs(os.path.join(OUT, "_cross"), exist_ok=True)
    L = []
    P = L.append
    J = {}
    rv = {g: jload(os.path.join(R07, "reviews", f"{g}.json")) for g in GAMES}

    # ---------- 表 1：总表 ----------
    P("# R07 15 局跨局对照（56_cross_match.py）")
    P("")
    P("## 表 1 总表：局 | 策略 | 号数 | 真人位 / 队数 | 我方队名次 | 分型 | 我方最后一个号出局或终局（拍）| 我方领土份额 540 / 990 / 1530 拍 | 峰值（拍）| 第一个号出局 / 最后一个号出局（拍）")
    for g in GAMES:
        d = rv[g]
        if not d:
            P(f"{g}\t（没有 reviews/{g}.json）")
            continue
        c, o, tl = d["context"], d["outcome"], d["timeline"]
        sv = c["strategyVersion"].lower()[:60]
        ver = "Vb" if "c116-vb" in sv else ("Va" if "c116-va" in sv else ("g09" if "g09" in sv else c["strategyVersion"][:18]))
        s = []
        for t in (540, 990, 1530):
            r = share_at(tl, t)
            s.append(pct(r["squadLandShare"]) if r and r.get("squadLandShare") is not None else "-")
        pk = max((r for r in tl if r.get("squadLandShare") is not None), key=lambda r: r["squadLandShare"], default=None)
        dts = sorted(x["t"] for x in d["deaths"] if isinstance(x.get("t"), int))
        J[g] = {"archetype": d["lossArchetype"], "bots": c["bots"], "humans": c["humans"], "teams": c["teams"], "rank": o.get("ourTeamRank"),
                "endTick": o.get("endTick"), "peak": o.get("peakSquadLandShare"), "peakT": pk["t"] if pk else None,
                "deaths": dts, "ver": ver}
        P(f"{g}\t{ver}\t{c['bots']}\t{c['humans']} / {c['teams']}\t{o.get('ourTeamRank') or '-'}\t{d['lossArchetype']}\t{o.get('endTick')}\t{' / '.join(s)}\t"
          f"{pct(o.get('peakSquadLandShare'), 2)}（{pk['t'] if pk else '-'}）\t{dts[0] if dts else '-'} / {dts[-1] if dts else '-'}")
    arche = Counter(rv[g]["lossArchetype"] for g in GAMES if rv[g])
    P("分型合计：" + "、".join(f"{k} {v}" for k, v in arche.most_common()))

    # ---------- 表 2：出生 ----------
    P("")
    P("## 表 2 出生（11 局录像）：局 | 我方包围盒（像素）| 最近队友 最小 / 中位 / 最大（像素）| 天然地盘：我方占全图 / 人头占比 / 人均是全场的几倍 | 单号天然地盘中位：我方 / 其他真人")
    for g in GAMES:
        tsv = os.path.join(OUT, g, "spawn_truth.tsv")
        v = jload(os.path.join(OUT, g, "voronoi.json"))
        if not os.path.exists(tsv):
            continue
        rows = list(csv.DictReader(open(tsv, encoding="utf-8"), delimiter="\t"))
        xs = [float(r["x"]) for r in rows]
        ys = [float(r["y"]) for r in rows]
        nr = sorted(float(r["near"]) for r in rows)
        box = f"{max(xs) - min(xs):.0f}×{max(ys) - min(ys):.0f}"
        vt = "-"
        md = "-"
        if v:
            gq = v["groups"]["我方号"]
            vt = f"{pct(gq['vorShare'])} / {pct(gq['headShare'])} / {gq['perHeadRel']:.2f}"
            md = f"{v['squadVorMedian']:,.0f} / {v['otherVorMedian']:,.0f}"
            J[g].update({"vorShare": gq["vorShare"], "headShare": gq["headShare"], "perHeadRel": gq["perHeadRel"]})
        J[g].update({"box": box, "nearMin": nr[0], "nearMed": statistics.median(nr), "nearMax": nr[-1]})
        P(f"{g}\t{box}\t{nr[0]:.0f} / {statistics.median(nr):.0f} / {nr[-1]:.0f}\t{vt}\t{md}")

    # ---------- 表 3：好地实际拿到 ----------
    P("")
    P("## 表 3 好地实际拿到（46_voronoi.mjs）：局 | 630 拍 实际领土 ÷ 天然地盘：我方 / 其他各组的范围 | 1500 拍：我方 / 其他各组的范围 | 1500 拍我方天然地盘里的格子：自己 / 别的真人 / 内置 AI / 无主地 | 我方在自己天然地盘之外拿到的格数（1500）")
    for g in GAMES:
        v = jload(os.path.join(OUT, g, "voronoi.json"))
        if not v:
            continue
        cells = []
        for t in ("630", "1500"):
            a = v["at"].get(t, {})
            me = a.get("我方号")
            oth = [x["ratio"] for k, x in a.items() if k != "我方号" and "其他真人" not in k and x.get("vor", 0) > 0 and v["groups"].get(k, {}).get("n", 0) >= 2]
            cells.append(f"{me['ratio']:.2f} / {min(oth):.2f}~{max(oth):.2f}" if me and oth else (f"{me['ratio']:.2f} / -" if me else "-"))
            J[g][f"cap{t}"] = me["ratio"] if me else None
            J[g][f"capOth{t}"] = [round(min(oth), 3), round(max(oth), 3)] if oth else None
        me = v["at"].get("1500", {}).get("我方号")
        P(f"{g}\t{cells[0]}\t{cells[1]}\t" + (f"{me['ownIn']:,} / {me['humanIn']:,} / {me['aiIn']:,} / {me['neutralIn']:,}\t{me['outside']:,}" if me else "-\t-"))

    P("")
    P("## 表 4 身边内置 AI 的地归了谁（630 拍和各组接壤的内置 AI 当时的领土 = 脚印）：局 | 我方：AI 个数 / 脚印格数 | 到 1500 拍：我方吃到 / 别的真人吃到 / 还在 AI 手里 | 到 1800 拍：我方 / 别的真人 / AI | 其他各组到 1800 拍吃到自己脚印的比例范围")
    for g in GAMES:
        v = jload(os.path.join(OUT, g, "voronoi.json"))
        if not v or "我方号" not in v.get("ai", {}):
            continue
        a = v["ai"]["我方号"]
        c = max(1, a["cells"])
        f = lambda t: f"{a['to'][t]['own'] / c:.0%} / {a['to'][t]['human'] / c:.0%} / {a['to'][t]['ai'] / c:.0%}" if t in a["to"] else "-"
        oth = [x["to"]["1800"]["own"] / x["cells"] for k, x in v["ai"].items() if k != "我方号" and "其他真人" not in k and x.get("cells", 0) >= 3000 and "1800" in x["to"]]
        J[g].update({"aiCells": a["cells"], "aiOwn1500": a["to"].get("1500", {}).get("own"), "aiOwn1800": a["to"].get("1800", {}).get("own"),
                     "aiHuman1800": a["to"].get("1800", {}).get("human")})
        P(f"{g}\t{a['n']} / {a['cells']:,}\t{f('1500')}\t{f('1800')}\t" + (f"{min(oth):.0%}~{max(oth):.0%}" if oth else "-"))

    # ---------- 表 5：延迟 ----------
    P("")
    P("## 表 5 意图 → 落地的延迟（47_delay_periods.py；影子发令拍 → 录像落地拍，按影子发令拍归时段）：局 | 各时段 P50 / P90 / 最大（拍；配上的条数）")
    for g in GAMES:
        dp = jload(os.path.join(OUT, g, "delay_periods.json"))
        if not dp:
            continue
        cells = []
        for p in PERIODS:
            e = dp["delay"].get(p)
            cells.append(f"{e['p50']} / {e['p90']} / {e['max']}（{e['matched']}）" if e and e.get("matched") else "-")
        J[g]["delay"] = {p: {k: dp["delay"][p].get(k) for k in ("p50", "p90", "max", "matched", "ge35", "ge90")} for p in PERIODS if p in dp["delay"]}
        P(f"{g}\t" + "\t".join(cells))
    P("")
    P("## 表 6 晚到的条数（同上）：局 | ≥35 拍：各时段 | ≥90 拍：各时段 | 合计 ≥35 / ≥90")
    for g in GAMES:
        dp = jload(os.path.join(OUT, g, "delay_periods.json"))
        if not dp:
            continue
        a = [dp["delay"].get(p, {}).get("ge35", 0) or 0 for p in PERIODS]
        b = [dp["delay"].get(p, {}).get("ge90", 0) or 0 for p in PERIODS]
        J[g]["ge35"] = sum(a)
        J[g]["ge90"] = sum(b)
        P(f"{g}\t{' / '.join(map(str, a))}\t{' / '.join(map(str, b))}\t{sum(a)} / {sum(b)}")

    P("")
    P("## 表 7 漏斗（47_delay_periods.py）：局 | 各段「影子想发 / 真号日志 cmds 增量 / 录像落地」")
    for g in GAMES:
        dp = jload(os.path.join(OUT, g, "delay_periods.json"))
        if not dp or "funnel" not in dp:
            continue
        P(f"{g}\t" + "\t".join(f"{k}：{e['shadow']} / {e['real']} / {e['landed']}" for k, e in dp["funnel"].items()))

    P("")
    P("## 表 8 迟到落空（47_delay_periods.py）：局 | 时段 | 落地的进攻条数 / 发兵 | 落空（一兵不扣）条数 | 目标已死被记成打无主地：条数 / 兵 | 影子想打 AI 的条数 / 兵 → 实际落在 AI 身上的条数 / 兵 | 原样退回的兵（占发兵）")
    for g in GAMES:
        dp = jload(os.path.join(OUT, g, "delay_periods.json"))
        if not dp or "whiff" not in dp:
            continue
        for p in ("600~1500", "1500~3000"):
            w = dp["whiff"].get(p)
            if not w:
                continue
            rf = w.get("refund")
            rf = f"{rf:,}（{rf / w['troops']:.0%}）" if isinstance(rf, (int, float)) and w.get("troops") else str(rf)
            P(f"{g}\t{p}\t{w['atkN']} / {w['troops']:,}\t{w['noop']}\t{w['retargetN']} / {w['retargetTroops']:,}\t"
              f"{w['wantAiN']} / {w.get('wantAiTroops', 0):,} → {w.get('onAiN', 0)} / {w.get('onAiTroops', 0):,}\t{rf}")
            J[g].setdefault("whiff", {})[p] = {k: w.get(k) for k in ("atkN", "troops", "noop", "retargetN", "retargetTroops", "wantAiN", "onAiN", "refund")}

    P("")
    P("## 表 9 成批落地和连发（47_delay_periods.py / 81_same_tick_batches.py）：局 | 全场「同一号同一拍 ≥3 条」的批 / 条数 | 其中一拍打掉一半以上余额的批：600~1500；1500~3000（括号里是这些批的发兵合计）| 同一目标连发的组：600~1500；1500~3000（组 / 条 / 第 2 条起的兵）| 其他真人的批")
    for g in GAMES:
        dp = jload(os.path.join(OUT, g, "delay_periods.json"))
        sb = jload(os.path.join(OUT, g, "same_tick_batches.json"))
        if not dp or "repeat" not in dp:
            continue
        r = dp["repeat"]
        nb = sum(r[p]["batches"] for p in PERIODS if p in r)
        nc = sum(r[p]["batchCmds"] for p in PERIODS if p in r)
        big = "；".join(f"{r[p]['bigBatches']}（{r[p]['bigTroops']:,}）" for p in ("600~1500", "1500~3000") if p in r)
        grp = "；".join(f"{r[p]['groups']} / {r[p]['groupCmds']} / {r[p]['repeatTroops']:,}" for p in ("600~1500", "1500~3000") if p in r)
        oth = "-"
        if sb and isinstance(sb.get("humans"), dict):
            b = sb["humans"].get("buckets", {})
            oth = str(sum(x[0] for x in b.values() if isinstance(x, list) and x))
        J[g].update({"batches": nb, "batchCmds": nc})
        P(f"{g}\t{nb} / {nc}\t{big}\t{grp}\t{oth}")

    # ---------- 表 10：t<1500 决策拍归类 ----------
    P("")
    P("## 表 10 t<1500 的决策拍卡在哪（影子；47_delay_periods.py 的 early 节，只有 A082 / A007 / A070 有）：局 | 段 | 决策拍 | 出手 | 卡在留底 | 各类")
    for g in GAMES:
        dp = jload(os.path.join(OUT, g, "delay_periods.json"))
        if not dp or "early" not in dp:
            continue
        for k, e in dp["early"].items():
            P(f"{g}\t{k}\t{e['dec']}\t{e['fired']}\t{e['floor']}\t" + "；".join(f"{a} {b}" for a, b in sorted(e["cls"].items(), key=lambda x: -x[1])))

    # ---------- 表 11：出局上报时钟 ----------
    P("")
    P("## 表 11 出局上报时钟（52_result_clock.py）：局 | 摘要")
    for g in GAMES:
        p = os.path.join(OUT, g, "result_clock.txt")
        if not os.path.exists(p):
            continue
        for ln in open(p, encoding="utf-8"):
            if ln.startswith("阵亡 / 终局"):
                P(f"{g}\t{ln.strip()}")

    # ---------- 表 12：多局汇总原样附上 ----------
    for title, fn in (("表 12 出生指派 vs 录像（54_spawn_seq.py）", "_spawn_seq_all.txt"), ("表 13 真号计数 vs 录像落地（53_issue_vs_land.py）", "_issue_vs_land_all.txt")):
        p = os.path.join(OUT, fn)
        if os.path.exists(p):
            P("")
            P(f"## {title}")
            L.extend(x.rstrip("\n") for x in open(p, encoding="utf-8"))

    # ---------- 表 14：阵亡 ----------
    P("")
    P("## 表 14 阵亡（reviews 的 deaths）：局 | 出局号数 / 号数 | 出局拍：最早 / 中位 / 最晚 | 出局时手里的兵合计 | 出局前 500 拍收到捐款的号数 | 出局原因里挂得最多的标签")
    tagc_all = Counter()
    for g in GAMES:
        d = rv[g]
        if not d:
            continue
        ds = d["deaths"]
        ts = sorted(x["t"] for x in ds if isinstance(x.get("t"), int))
        bal = sum(x.get("balanceAtDeath") or 0 for x in ds)
        don = sum(1 for x in ds if (x.get("donIn500") or {}).get("n", 0) > 0)
        tc = Counter(p.replace("NEW:", "") for x in ds for p in x.get("patternIds", []))
        tagc_all.update(tc)
        J[g].update({"deathN": len(ds), "balAtDeath": bal})
        P(f"{g}\t{len(ds)} / {d['context']['bots']}\t" + (f"{ts[0]} / {int(statistics.median(ts))} / {ts[-1]}" if ts else "-") + f"\t{bal:,}\t{don}\t" + "、".join(f"{k.replace('R07-', '')} {v}" for k, v in tc.most_common(4)))
    P("全部阵亡挂的标签合计：" + "、".join(f"{k.replace('R07-', '')} {v}" for k, v in tagc_all.most_common(14)))

    # ---------- 表 15：关键决策 ----------
    P("")
    P("## 表 15 关键决策（reviews 的 decisions）：局 | 条数 | good / error / unclear | error 挂的标签")
    errc_all = Counter()
    goodc_all = Counter()
    tot = Counter()
    for g in GAMES:
        d = rv[g]
        if not d:
            continue
        vc = Counter(x.get("verdict") for x in d["decisions"])
        ec = Counter((x.get("patternId") or "").replace("NEW:", "") for x in d["decisions"] if x.get("verdict") == "error")
        gc = Counter((x.get("patternId") or "").replace("NEW:", "") for x in d["decisions"] if x.get("verdict") == "good")
        errc_all.update(ec)
        goodc_all.update(gc)
        tot.update(vc)
        P(f"{g}\t{len(d['decisions'])}\t{vc.get('good', 0)} / {vc.get('error', 0)} / {vc.get('unclear', 0)}\t" + "、".join(f"{k.replace('R07-', '')} {v}" for k, v in ec.most_common(6)))
    P(f"合计：{sum(tot.values())} 条，good {tot.get('good', 0)} / error {tot.get('error', 0)} / unclear {tot.get('unclear', 0)}")
    P("error 标签合计：" + "、".join(f"{k.replace('R07-', '')} {v}" for k, v in errc_all.most_common(20)))
    P("good 标签合计：" + "、".join(f"{k.replace('R07-', '')} {v}" for k, v in goodc_all.most_common(10)))

    # ---------- 表 16：模式标签出现在哪几局 ----------
    P("")
    P("## 表 16 模式标签（reviews 的 newPatterns）：标签 | 出现的局数 | 实例数合计 | 哪几局（实例数）")
    pg = defaultdict(dict)
    for g in GAMES:
        d = rv[g]
        if not d:
            continue
        for x in d.get("newPatterns", []):
            pid = (x.get("name") or x.get("id") or x.get("patternId") or "").replace("NEW:", "")
            inst = x.get("instances", [])
            if isinstance(inst, str):
                inst = re.findall(r"\{[^{}]*\}", inst)
            if pid:
                pg[pid][g] = len(inst)
    cat = defaultdict(lambda: [0, 0, set()])
    for pid, m in sorted(pg.items(), key=lambda kv: (-len(kv[1]), -sum(kv[1].values()), kv[0])):
        P(f"{pid.replace('R07-', '')}\t{len(m)}\t{sum(m.values())}\t" + "、".join(f"{g}（{n}）" for g, n in m.items()))
        k = pid.replace("R07-", "").split("-")[0]
        cat[k][0] += 1
        cat[k][1] += sum(m.values())
        cat[k][2].update(m)
    P("按前缀合计（标签个数 / 实例数 / 涉及局数）：" + "、".join(f"{k} {v[0]} / {v[1]} / {len(v[2])}" for k, v in sorted(cat.items(), key=lambda kv: -kv[1][1])))
    J["_patterns"] = {k: v for k, v in pg.items()}

    # ---------- 表 17：转折点 ----------
    P("")
    P("## 表 17 转折点（reviews 的 turningPoints）：局 | 拍段 | 份额前 → 后 | 观测 / 推断")
    for g in GAMES:
        d = rv[g]
        if not d:
            continue
        for tp in d["turningPoints"]:
            sb, sa = tp.get("shareBefore"), tp.get("shareAfter")
            P(f"{g}\t{tp.get('t0')}~{tp.get('t1')}\t{pct(sb, 2) if isinstance(sb, (int, float)) else sb} → {pct(sa, 2) if isinstance(sa, (int, float)) else sa}\t{tp.get('statementType')}")

    with open(os.path.join(OUT, "_cross", "cross_match.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    with open(os.path.join(OUT, "_cross", "cross_match.json"), "w", encoding="utf-8") as f:
        json.dump(J, f, ensure_ascii=False, indent=1)
    print("\n".join(L))


if __name__ == "__main__":
    main()
