#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""107_cp_report.py — R07：把断面对照的汇总结果排成报告里的表，并把表填进报告正文。

读：out/_cross/checkpoint_attribution.json（103_cp_table.py）、channel_exposure.json（104）、spawn_par.json（106）
    scripts/cp_report_src.md（报告正文；表的位置写成单独一行「@@表 名字@@」）
写：out/_cross/cp_report_tables.md（全部的表，带名字）
    reports/OFFLINE-CHECKPOINT-ATTRIBUTION.md（正文 + 表；正文文件不存在时只写前一个）
正文里手写的数字都应当能在 out/_cross/ 的输出里找到（49b_audit_report.py 检查）。
用法：python3 107_cp_report.py
"""
import json
import math
import os
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.normpath(os.path.join(HERE, ".."))
CROSS = os.path.join(BASE, "out", "_cross")
GAMES = ["A007", "A033", "A039", "A053", "A061", "A062", "A070", "A079", "A082", "A089", "A091"]
WINS = ["0~300", "300~630", "630~900", "900~1200", "1200~1500", "1500~2400", "2400~3300", "3300~4284", "4284~5184", "5184 以后"]
SPAN = {0: ["0~300", "300~630", "630~900", "900~1200", "1200~1500"], 630: ["630~900", "900~1200", "1200~1500"], 1500: ["1500~2400"], 4284: ["4284~5184"]}


def jload(name):
    p = os.path.join(CROSS, name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}


def r3(x, nd=3):
    return "—" if x is None else f"{x:.{nd}f}"


def sg(x, nd=2):
    return "—" if x is None else f"{x:+.{nd}f}"


def pc(x, nd=0):
    return "—" if x is None else f"{100 * x:.{nd}f}%"


def md(head, rows, align=None):
    if not rows:
        return "（这张表对应的对照还没有跑出来。）"
    out = ["| " + " | ".join(head) + " |", "|" + "|".join((":--" if (align and align[i] == "l") or (not align and i == 0) else "--:") for i in range(len(head))) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def mean(a):
    a = [x for x in a if x is not None]
    return sum(a) / len(a) if a else None


def med(a):
    a = [x for x in a if x is not None]
    return statistics.median(a) if a else None


def spearman(xs, ys):
    pts = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    n = len(pts)
    if n < 4:
        return None, n

    def rank(v):
        order = sorted(range(n), key=lambda i: v[i])
        rk = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                rk[order[k]] = (i + j) / 2 + 1
            i = j + 1
        return rk
    rx, ry = rank([p[0] for p in pts]), rank([p[1] for p in pts])
    mx, my = sum(rx) / n, sum(ry) / n
    sxx = sum((a - mx) ** 2 for a in rx)
    syy = sum((b - my) ** 2 for b in ry)
    if sxx <= 0 or syy <= 0:
        return None, n
    return sum((a - mx) * (b - my) for a, b in zip(rx, ry)) / math.sqrt(sxx * syy), n


def main():
    J = jload("checkpoint_attribution.json")
    E = jload("channel_exposure.json")
    S = jload("spawn_par.json")
    T = {}
    F0 = {}  # 正文用数（先放这里，后面并进 F）
    notes = {}

    def held(g, T0):
        n = h = 0
        for w in SPAN[T0]:
            x = (E.get(g, {}).get("win") or {}).get(w)
            if x:
                n += x["n"]
                h += x["gt35"] + x["dropped"]
        return (h / n if n else None), n

    # ---- 复现
    rows = []
    for g in GAMES:
        c = (J.get("closure") or {}).get(f"{g}@0")
        if not c:
            continue
        rows.append([g, f"{c['trajBoth']} / {c['trajRows']}", "没有" if c["firstDiff"] is None else c["firstDiff"], r3(c["LSratio"]), r3(c["LOratio"]), f"{c['posHist']} / {c['landed']}"])
    T["复现-断面0"] = md(["局", "轨迹表逐行相同的行数", "第一处领土与历史不同的记录拍", "1500 拍我方领土：C2 ÷ 历史", "1500 拍其他真人领土：C2 ÷ 历史", "落在历史原位置的指令 / 全部落地"], rows)
    rows = []
    for g in GAMES:
        row = [g]
        for T0 in (630, 1500, 4284):
            c = (J.get("closure") or {}).get(f"{g}@{T0}")
            if not c:
                row += ["—", "—"]
                continue
            a = "两边都是 0" if c["LSratio"] is None else r3(c["LSratio"])
            row += ["没有" if c["firstDiff"] is None else c["firstDiff"], f"{a} / {r3(c['LOratio'])}"]
        rows.append(row)
    if not any(c != "—" for r in rows for c in r[1:]):
        rows = []
    T["复现-其余断面"] = md(["局", "断面 630：第一处不同的记录拍", "看 900 拍后领土 C2 ÷ 历史（我方 / 其他真人）", "断面 1500：第一处不同", "C2 ÷ 历史（我方 / 其他真人）", "断面 4284：第一处不同", "C2 ÷ 历史（我方 / 其他真人）"], rows)

    # ---- 通道状况
    rows = []
    for w in WINS:
        x = (E.get("all") or {}).get(w)
        if not x:
            continue
        rows.append([w, f"{x['n']:,}", x["le14"], x["15_35"], x["gt35"], x["dropped"], pc((x["gt35"] + x["dropped"]) / x["n"]) if x["n"] else "—"])
    T["通道-合计"] = md(["发令拍所在的窗", "发令", "14 拍内落地", "15~35 拍落地", "35 拍以上才落地", "没落地", "被按住的占比（后两列 ÷ 发令）"], rows)
    rows = []
    for g in GAMES:
        e = E.get(g) or {}
        row = [g, pc(e["dropped"] / e["intents"], 1) if e.get("intents") else "—"]
        for w in WINS[:9]:
            x = (e.get("win") or {}).get(w)
            row.append(pc(x["heldShare"]) if x and x["n"] else "—")
        rows.append(row)
    T["通道-逐局"] = md(["局", "整局没落地 ÷ 发令"] + WINS[:9], rows)

    # ---- 站位基准
    rows = []
    for g in GAMES:
        x = (S.get("games") or {}).get(g)
        if not x:
            continue
        rows.append([g, x["n"], x["nS"], f"{x['vorS']:,.0f}", f"{x['vorO']:,.0f}", r3(x["v"]), r3(x.get("vg630")), r3(x.get("vg1500"))])
    T["站位基准"] = md(["局", "真人席位", "我方号", "我方人均天然地盘（格）", "其他真人人均天然地盘（格）", "天然地盘之比 v", "站位基准（630 拍）", "站位基准（1500 拍）"], rows)

    # ---- 1500 拍以后的站位基准（105_human_fill.mjs --late → 106 表 E）
    LATE = S.get("late") or {}
    rows = []
    for t in ("1500", "1800", "2100", "2400", "3300", "4284", "5184"):
        x = (LATE.get("gamma") or {}).get(t)
        if not x:
            continue
        vv = [y[f"vg{t}"] for y in (LATE.get("games") or {}).values() if y.get(f"vg{t}")]
        gm = math.exp(mean([math.log(v_) for v_ in vv])) if vv else None
        rows.append([t, f"{r3(x['g'], 2)} ± {r3(x['se'], 2)}", x["games"], pc(x["zeros"] / x["n"]) if x.get("n") else "—", r3(gm, 2), f"{r3(min(vv), 2)} ~ {r3(max(vv), 2)}" if vv else "—"])
        F0[f"gammaL{t}"], F0[f"gammaLse{t}"] = r3(x["g"], 2), r3(x["se"], 2)
        F0[f"zeroL{t}"] = pc(x["zeros"] / x["n"]) if x.get("n") else "—"
        if gm:
            F0[f"vgL{t}"] = r3(gm, 2)
    T["站位基准-后段"] = md(["拍", "弹性 γ（± 刀切标准误）", "局数", "其他真人里已经没有领土的", "站位基准 v_γ：各局几何平均", "各局最小 ~ 最大"], rows)

    # ---- 断面 0 的分层
    for TT in (630, 1500):
        rows = []
        hs, hd = [], []
        for g in GAMES:
            d = (J.get("games") or {}).get(g, {}).get(f"t0_{TT}")
            if not d:
                continue
            rows.append([g, r3(d["rhoH"]), r3(d["vg"]), r3(d["rhoC0"]), r3(d["rhoC1"]), r3(d["rhoC2p"]), sg(d["spawn"]), sg(d["rule"]), sg(d["base"]), sg(d["hold"]), sg(d["total"])])
            hs.append(held(g, 0)[0] if TT == 1500 else None)
            hd.append(d["hold"])
        sm = J.get(f"sum_t0_{TT}")
        if sm and sm.get("n"):
            n = sm["n"]
            keys = ("spawn", "rule", "base", "hold", "total")
            rows.append([f"**{n} 局平均**", "", "", "", "", ""] + [f"**{sg(sm[k] / n)}**" for k in keys])
            rows.append([f"{n} 局中位数", "", "", "", "", ""] + [sg(sm["median"][k]) for k in keys])
            if sm["total"] > 0.2 * n:
                rows.append(["占合计的比例", "", "", "", "", ""] + [pc(sm[k] / sm["total"]) for k in keys])
            notes[f"分层-{TT}"] = (f"{n} 局相加：出生站位 {sg(sm['spawn'])}，规则（余项）{sg(sm['rule'])}，基础延迟 {sg(sm['base'])}，按住与成批放行 {sg(sm['hold'])}，合计 {sg(sm['total'])}；"
                                    f"走偏带来的虚高 {sg(sm['bias'])}（平均 {sg(sm['bias'] / n, 3)}，中位数 {sg(sm['median']['bias'], 3)}）；"
                                    f"零延迟下相对基准 ln v_γ − ln ρC0：平均 {sg(sm['raw0'] / n)}，中位数 {sg(sm['median']['raw0'])}；正常延迟下 ln v_γ − ln ρC1：平均 {sg(sm['raw1'] / n)}，中位数 {sg(sm['median']['raw1'])}；"
                                    f"基准改用 v_β：出生站位 {sg(sm['spawnB'] / n)} / 规则 {sg(sm['ruleB'] / n)}（平均）；改用 v：{sg(sm['spawnV'] / n)} / {sg(sm['ruleV'] / n)}；γ = {r3(sm.get('gamma'))}，β = {r3(sm.get('beta'))}")
            if TT == 1500:
                rho, nn = spearman(hs, hd)
                notes["分层-1500-相关"] = f"按住与成批放行这一项 与 0~1500 拍被按住的指令占比：秩相关 {r3(rho, 2)}（{nn} 局）"
        T[f"分层-{TT}"] = md(["局", "ρ 历史", "站位基准", "ρ 零延迟 C0", "ρ 基础延迟 C1", "ρ 历史轨迹 C2（同样走偏）", "出生站位", "规则（余项）", "基础延迟", "按住与成批放行", "合计"], rows)

    # 倍数版（每层 = e^(−对数差)）
    rows = []
    for TT in (630, 1500):
        sm = J.get(f"sum_t0_{TT}")
        if not sm or not sm.get("n"):
            continue
        n = sm["n"]
        rows.append([f"到 {TT} 拍（{n} 局几何平均）"] + [r3(math.exp(-sm[k] / n), 2) for k in ("spawn", "rule", "base", "hold", "total")])
    if rows:
        T["分层-倍数"] = md(["", "出生站位 ×", "规则（余项）×", "基础延迟 ×", "按住与成批放行 ×", "= ρ 历史"], rows)

    rows = []
    for TT in ("300", "630", "900", "1200", "1500"):
        x = (J.get("path") or {}).get(TT)
        if not x:
            continue
        rows.append([TT, x["n"], r3(math.exp(-x["total"]), 2)] + [sg(x[k]) for k in ("spawn", "rule", "base", "hold", "total")] + [sg(x["rule"] + x["base"])])
    T["分层-逐拍"] = md(["观察拍", "局数", "ρ 历史（几何平均）", "出生站位", "规则（余项）", "基础延迟", "按住与成批放行", "合计", "规则 + 基础延迟（正常通道下原策略相对基准）"], rows)

    rows = []
    cpth = J.get("chanPath") or {}
    for t in (60, 120, 180, 240, 300, 360, 420, 480, 540, 600, 720, 840, 960, 1080, 1200, 1320, 1440, 1500):
        x = cpth.get(str(t))
        if x:
            rows.append([t, x["n"], sg(x["base"]), sg(x["baseMed"]), sg(x["hold"]), sg(x["holdMed"])])
    T["通道差-逐拍"] = md(["观察拍", "局数", "基础延迟：平均", "中位数", "按住与成批放行：平均", "中位数"], rows)

    rows = []
    sh = J.get("shares") or {}
    SK = ("spawn", "hold", "rulebase", "rule", "base")
    for key, name in (("level1500", "到 1500 拍的落后"), ("change630_1500", "630 → 1500 拍之间新增的落后")):
        x = sh.get(key)
        if not x:
            continue
        rows.append([name, x["n"], sg(x["total"] / x["n"])] + [f"{pc(x[k]['share'])}（{pc(x[k]['lo'])} ~ {pc(x[k]['hi'])}）" for k in SK])
    T["占比"] = md(["口径", "局数", "各局平均的落后（对数差）", "出生站位", "按住与成批放行", "既有规则（在基础延迟的通道下）", "其中：规则在零延迟下（余项）", "其中：基础延迟"], rows)
    rows = []
    cg = J.get("change630_1500_games") or {}
    for g in GAMES:
        x = cg.get(g)
        if x:
            rows.append([g] + [sg(x[k]) for k in ("spawn", "rule", "base", "hold", "total")])
    x = (sh.get("change630_1500") or {}).get("mean")
    if x:
        rows.append(["**平均**"] + [f"**{sg(x[k])}**" for k in ("spawn", "rule", "base", "hold", "total")])
    T["分层-630到1500"] = md(["局", "出生站位", "规则（余项）", "基础延迟", "按住与成批放行", "合计（ρ 历史从 630 到 1500 拍的落差）"], rows)

    # ---- 1500 拍陆地分布
    rows = []
    acc = {}
    for g in GAMES:
        ld = (J.get("games") or {}).get(g, {}).get("land1500")
        if not ld:
            continue
        row = [g]
        for key in ("LS", "LO", "bot"):
            for ch in ("历史", "C2p", "C1", "C0"):
                x = ld.get(ch)
                row.append(f"{100 * x[key]:.1f}" if x else "—")
                if x:
                    acc.setdefault((key, ch), []).append(100 * x[key])
        rows.append(row)
    if rows:
        rows.append(["**平均**"] + [f"**{mean(acc.get((key, ch), [])):.1f}**" if acc.get((key, ch)) else "—" for key in ("LS", "LO", "bot") for ch in ("历史", "C2p", "C1", "C0")])
    T["陆地分布-1500"] = md(["局", "我方：历史", "C2（走偏）", "C1", "C0", "其他真人：历史", "C2（走偏）", "C1", "C0", "内置 AI：历史", "C2（走偏）", "C1", "C0"], rows)

    rows = []
    for TT in (630, 1500):
        sp = J.get(f"split_{TT}")
        if not sp:
            continue
        for name in ("mean", "median"):
            rows.append([f"{TT} 拍，{'平均' if name == 'mean' else '中位数'}"] + [sg(x, 3) for x in sp[name]])
    T["我方与其他真人-拆分"] = md(["", "基础延迟：我方领土 ln(C0 ÷ C1)", "其他真人领土 ln(C0 ÷ C1)", "按住与成批放行：我方 ln(C1 ÷ C2)", "其他真人 ln(C1 ÷ C2)", "走偏：我方 ln(C2 ÷ 历史)", "其他真人 ln(C2 ÷ 历史)"], rows)

    # ---- 指令去向
    rows = []
    for g in GAMES:
        ft = (J.get("fate") or {}).get(g)
        if not ft:
            continue
        c0, c1, c2 = ft.get("C0"), ft.get("C1"), ft.get("C2")
        hshare, hn = held(g, 0)
        rows.append([g, c0["issued"] if c0 else "—", c1["issued"] if c1 else "—", c1["landed"] if c1 else "—", c2["issued"] if c2 else "—", c2["landed"] if c2 else "—",
                     c2["mapDrop"] if c2 else "—", f"{c2['delayP50']} / {c2['delayP90']}" if c2 else "—", pc(hshare)])
    T["指令去向-1500"] = md(["局", "C0 发出", "C1 发出", "C1 落地", "C2 发出", "C2 落地", "C2 按历史轨迹没落地", "C2 在途拍数 中位 / P90", "历史上 0~1500 拍被按住的占比"], rows)

    # ---- 各断面往后 900 拍的历史（不需要对照）
    HW = J.get("histWin") or {}
    for T0 in (630, 1500, 4284):
        rows = []
        hx, hy = [], []
        for g in GAMES:
            d = HW.get(g, {}).get(str(T0))
            if not d:
                continue
            hsh, hn = held(g, T0)
            if d["d"] is not None and hsh is not None:
                hx.append(hsh)
                hy.append(d["d"])
            if d["aS0"] == 0:
                rows.append([g, "我方已全灭", "", "", f"0 / {d['nSquad']}", "", ""])
                continue
            r1 = "—" if d["rho1"] is None else ("0（全灭）" if d["rho1"] == 0 else r3(d["rho1"], 2))
            rows.append([g, r3(d["rho0"], 2), r1, sg(d["d"]) if d["d"] is not None else "—", f"{d['aS0']} → {d['aS1'] if d['aS1'] is not None else '—'}", hn if hn else "—", pc(hsh) if hn else "—"])
        sm = HW.get("sum", {}).get(str(T0))
        if len(hx) >= 5:
            F0[f"hw{T0}corr"] = sg(spearman(hx, hy)[0])
        if sm:
            if T0 != 4284:      # 4284 这一窗有两局全灭、一局崩盘，平均没有意义
                rows.append([f"**平均**（{sm['n']} 局）", "", "", f"**{sg(sm['mean'])}**", "", "", ""])
            F0[f"hw{T0}mean"] = sg(sm["mean"])
            F0[f"hw{T0}n"] = str(sm["n"])
            F0[f"hw{T0}up"] = str(sm["up"])
            F0[f"hw{T0}down"] = str(sm["down"])
        span = "630~1500" if T0 == 630 else f"{T0}~{T0 + 900}"
        T[f"窗口-历史-{T0}"] = md(["局", f"{T0} 拍的 ρ", "900 拍后的 ρ", "ln ρ 的变化", "我方在场号：断面 → 900 拍后", f"{span} 拍我方发令", "其中被按住的占比"], rows)

    # ---- 各断面往后的窗口
    for T0 in (630, 1500, 4284):
        for hh in (300, 600, 900):
            rows = []
            hs, hd, gd = [], [], []
            for g in GAMES:
                d = (J.get("win") or {}).get(g, {}).get(f"t{T0}_h{hh}")
                if not d:
                    continue
                hsh, hn = held(g, T0)
                dh = "历史上已全灭" if d.get("rhoH") == 0 else sg(d["dH"])
                rows.append([g, r3(d["rho0"]), pc(hsh) if hh == 900 else "", dh, sg(d["d2p"]), sg(d["d1"]), sg(d["d0"]), sg(d["base"]), sg(d["hold"]), sg(d["bias"])])
                hs.append(hsh)
                hd.append(d["hold"])
                gd.append((g, d["hold"], hsh, d["dH"], d["d1"]))
            ws = (J.get("winSum") or {}).get(f"t{T0}_h{hh}")
            if ws:
                ks = ("dH", "d2p", "d1", "d0", "base", "hold", "bias")
                rows.append(["**平均**", "", ""] + [f"**{sg(ws[k]['mean'])}**（{ws[k]['n']} 局）" for k in ks])
                rows.append(["中位数", "", ""] + [sg(ws[k]["median"]) for k in ks])
                if hh == 900:
                    rho, nn = spearman(hs, hd)
                    notes[f"窗口-{T0}-相关"] = f"断面 {T0} 往后 900 拍：按住与成批放行这一项 与 这一窗被按住的指令占比 的秩相关 {r3(rho, 2)}（{nn} 局）"
                    hv = [(g_, h_, s_) for g_, h_, s_, _, _ in gd if h_ is not None]
                    if hv:
                        F0[f"wh{T0}n"] = str(len(hv))
                        F0[f"wh{T0}mean"] = sg(ws["hold"]["mean"])
                        F0[f"wh{T0}med"] = sg(ws["hold"]["median"])
                        F0[f"wbias{T0}mean"] = sg(ws["bias"]["mean"])
                        F0[f"wc1_{T0}mean"] = sg(ws["d1"]["mean"])
                        F0[f"wc2_{T0}mean"] = sg(ws["d2p"]["mean"])
                        F0[f"wh{T0}corr"] = r3(rho, 2) if rho is not None else "—"
                        big = sorted([x for x in hv if x[1] >= 0.15], key=lambda x: -x[1])
                        rest = [x for x in hv if x[1] < 0.15]
                        F0[f"wh{T0}bigN"] = str(len(big))
                        F0[f"wh{T0}big"] = "、".join(f"{g_}（{sg(h_)}）" for g_, h_, _ in big)
                        tot = sum(x[1] for x in hv)
                        if tot > 0:
                            F0[f"wh{T0}bigShare"] = pc(sum(x[1] for x in big) / tot)
                        if rest:
                            F0[f"wh{T0}restN"] = str(len(rest))
                            F0[f"wh{T0}restMin"], F0[f"wh{T0}restMax"] = sg(min(x[1] for x in rest)), sg(max(x[1] for x in rest))
                        low = [x for x in hv if x[2] is not None and x[2] <= 0.15]
                        if low:
                            F0[f"wh{T0}lowN"] = str(len(low))
                            F0[f"wh{T0}lowMin"], F0[f"wh{T0}lowMax"] = sg(min(x[1] for x in low)), sg(max(x[1] for x in low))
                            F0[f"wh{T0}lowList"] = "、".join(f"{g_}（{sg(h_)}）" for g_, h_, _ in sorted(low, key=lambda x: -x[1]))
                        dd = [(dH_, d1_) for _, _, _, dH_, d1_ in gd if dH_ is not None and d1_ is not None]
                        F0[f"wH{T0}neg"] = str(sum(1 for a_, _ in dd if a_ < 0))
                        F0[f"wc1_{T0}neg"] = str(sum(1 for _, b_ in dd if b_ < 0))
                        F0[f"wc1_{T0}of"] = str(len(dd))
            head = ["局", "断面时的 ρ", "这 900 拍里历史上被按住的指令占比" if hh == 900 else "", "历史", "C2（同样走偏）", "C1", "C0", "基础延迟", "按住与成批放行", "走偏带来的虚高"]
            T[f"窗口-{T0}-{hh}"] = md(head, rows)
    # ---- 4284 断面：窗口末尾的水平值（这一窗有的局我方被打光，ln ρ 没有定义）
    WL = J.get("winLevel") or {}
    rows = []
    wl_h = []
    for g in GAMES:
        x = (WL.get(g) or {}).get("4284")
        if not x:
            continue
        held = ((E.get(g, {}).get("win") or {}).get("4284~5184") or {}).get("heldShare")

        def lvl(k):
            y = x.get(k)
            return f"{r3(y['rho'], 2)}（{y['aS']:g} 个号）" if y else "—"
        c1, c2 = x.get("C1"), x.get("C2p")
        if c1 and c2 and c1["rho"] > 0 and c2["rho"] > 0:
            hd_ = math.log(c1["rho"]) - math.log(c2["rho"])
            hs = sg(hd_)
            wl_h.append((g, hd_, held))
        elif c1 and c2:
            hs = "两种通道下都全灭" if c1["rho"] == 0 and c2["rho"] == 0 else ("C2 下全灭" if c2["rho"] == 0 else "C1 下全灭")
        else:
            hs = "—"
        rows.append([g, f"{r3(x['rho0'], 2)}（{x['aS0']} 个号）", pc(held) if held is not None else "—", lvl("H"), lvl("C2p"), lvl("C1"), hs])
    T["窗口-4284-水平"] = md(["局", "4284 拍：ρ（我方在场号）", "这 900 拍里被按住的指令占比", "5184 拍 历史", "C2（同样走偏）", "C1", "按住与成批放行（ln ρ 之差）"], rows)
    if wl_h:
        hv_ = [h_ for _, h_, _ in wl_h]
        F0["wl4284n"] = str(len(wl_h))
        F0["wl4284min"], F0["wl4284max"] = sg(min(hv_)), sg(max(hv_))
        F0["wl4284mean"] = sg(mean(hv_))
        F0["wl4284absMax"] = r3(max(abs(h_) for h_ in hv_), 2)
        F0["wl4284rows"] = str(len(rows))
    # A053：630~1200 拍被按住的指令里，晚到但落地的和没落地的各多少（正文用）
    ex = [(E.get("A053", {}).get("win") or {}).get(w_) for w_ in ("630~900", "900~1200")]
    if all(ex):
        F0["a053n"] = str(sum(e_["n"] for e_ in ex))
        F0["a053late"] = str(sum(e_["gt35"] for e_ in ex))
        F0["a053drop"] = str(sum(e_["dropped"] for e_ in ex))
    # ---- 各断面窗口的三层
    W3 = J.get("win3") or {}
    w3sum = []
    for T0 in (630, 1500, 4284):
        w3 = W3.get(str(T0))
        if not w3:
            continue
        w3m, w3sh = w3["mean"], w3.get("shares")
        w3row = [f"{T0} → {T0 + 900}", w3["n"], sg(w3m["total"])]
        for k in ("spawn", "hold", "rulebase"):
            w3row.append(f"{sg(w3m[k])}（{pc(w3sh[k]['share'])}）" if w3sh else sg(w3m[k]))
            F0[f"w3_{T0}_{k}"] = sg(w3m[k])
            if w3sh:
                F0[f"w3s_{T0}_{k}"] = pc(w3sh[k]["share"])
                F0[f"w3r_{T0}_{k}"] = f"{pc(w3sh[k]['lo'])} ~ {pc(w3sh[k]['hi'])}"
        F0[f"w3_{T0}_total"] = sg(w3m["total"])
        F0[f"w3_{T0}_n"] = str(w3["n"])
        w3rb = sorted((x_["rulebase"], g_) for g_, x_ in w3["games"].items())
        F0[f"w3_{T0}_rbNeg"] = str(sum(1 for v_, _ in w3rb if v_ < 0))
        F0[f"w3_{T0}_rbPos"] = str(sum(1 for v_, _ in w3rb if v_ >= 0))
        F0[f"w3_{T0}_rbPosList"] = "、".join(f"{g_}（{sg(v_)}）" for v_, g_ in w3rb if v_ >= 0) or "没有"
        F0[f"w3_{T0}_rbMin"], F0[f"w3_{T0}_rbMax"] = sg(w3rb[0][0]), sg(w3rb[-1][0])
        w3sp = [x_["spawn"] for x_ in w3["games"].values()]
        F0[f"w3_{T0}_spMin"], F0[f"w3_{T0}_spMax"] = sg(min(w3sp)), sg(max(w3sp))
        for k in ("total", "spawn", "hold", "rulebase"):
            F0[f"w3med_{T0}_{k}"] = sg(med([x_[k] for x_ in w3["games"].values()]))
        # 合计最大的一局单列（4284 断面里是我方号大量出局的那一局），其余各局另算平均
        w3top = max(w3["games"], key=lambda g_: abs(w3["games"][g_]["total"]))
        w3oth = [x_ for g_, x_ in w3["games"].items() if g_ != w3top]
        F0[f"w3top_{T0}"] = w3top
        F0[f"w3ex_{T0}_n"] = str(len(w3oth))
        for k in ("total", "spawn", "hold", "rulebase"):
            F0[f"w3ex_{T0}_{k}"] = sg(mean([x_[k] for x_ in w3oth]))
        F0[f"w3ex_{T0}_rbNeg"] = str(sum(1 for x_ in w3oth if x_["rulebase"] < -0.1))
        F0[f"w3ex_{T0}_rbZero"] = str(sum(1 for x_ in w3oth if abs(x_["rulebase"]) <= 0.1))
        F0[f"w3ex_{T0}_holdMin"], F0[f"w3ex_{T0}_holdMax"] = sg(min(x_["hold"] for x_ in w3oth)), sg(max(x_["hold"] for x_ in w3oth))
        w3sum.append(w3row)
        w3rows = []
        for g in GAMES:
            w3x = w3["games"].get(g)
            if w3x:
                w3rows.append([g, sg(w3x["total"]), sg(w3x["spawn"]), sg(w3x["hold"]), sg(w3x["rulebase"])])
        w3rows.append([f"**平均**（{w3['n']} 局）"] + [f"**{sg(w3m[k])}**" for k in ("total", "spawn", "hold", "rulebase")])
        if w3sh:
            w3rows.append(["占合计的比例", "100%"] + [f"{pc(w3sh[k]['share'])}（{pc(w3sh[k]['lo'])} ~ {pc(w3sh[k]['hi'])}）" for k in ("spawn", "hold", "rulebase")])
        T[f"三层-窗口-{T0}"] = md(["局", "合计（这一窗里多落后多少）", "出生站位", "按住与成批放行", "既有规则（基础延迟通道下）"], w3rows)
    T["三层-窗口"] = md(["断面 → 观察拍", "局数", "合计（这一窗里我方多落后多少）", "出生站位", "按住与成批放行", "既有规则（基础延迟通道下）"], w3sum)
    for T0 in (630, 1500, 4284):
        T.setdefault(f"三层-窗口-{T0}", md(["局"], []))

    rows = []
    for T0 in (630, 1500, 4284):
        for hh in (300, 600, 900):
            ws = (J.get("winSum") or {}).get(f"t{T0}_h{hh}")
            if not ws:
                continue
            rows.append([f"{T0} → {T0 + hh}", ws["base"]["n"], sg(ws["base"]["median"]), sg(ws["base"]["mean"]), ws["hold"]["n"], sg(ws["hold"]["median"]), sg(ws["hold"]["mean"]), sg(ws["bias"]["median"])])
    T["窗口-汇总"] = md(["断面 → 观察拍", "基础延迟：局数", "中位数", "平均", "按住与成批放行：局数", "中位数", "平均", "走偏带来的虚高：中位数"], rows)

    # ---- 敏感性
    rows = []
    name = {"c0b": "零延迟但一拍只受理一条", "d0": "在途 0 拍，只等回合边界", "emp": "C1 默认（实测取法）", "d5": "d 取 5~12 均匀", "d10": "d 取 10~18 均匀"}
    lagm = {"c0b": "0", "d0": "约 3", "emp": "约 12", "d5": "约 12", "d10": "约 17"}
    for k in ("c0b", "d0", "emp", "d5", "d10"):
        row = [name[k], lagm[k]]
        for hh in (630, 1500):
            x = (J.get("sens") or {}).get(f"t0_h{hh}_{k}")
            row += [f"{sg(x['median'])}（{x['n']} 局）" if x else "—", f"{sg(x['min'])} ~ {sg(x['max'])}" if x else "—"]
        rows.append(row)
    if not any(c != "—" for r in rows for c in r[2:]):
        rows = []
    T["敏感性-延迟"] = md(["通道取法", "发令到生效平均拍数", "到 630 拍：ln ρ − ln ρ(C0) 中位数", "最小 ~ 最大", "到 1500 拍：中位数", "最小 ~ 最大"], rows, align="llrrrr")
    rows = [[x["g"], x["T0"], x["h"], x["C1"], x["C2"]] for x in (J.get("leave") or [])]
    T["敏感性-离开"] = md(["局", "断面", "看多少拍", "C1：ln ρ(不离开) − ln ρ(照录像离开)", "C2"], rows)
    # 断面 0 / 630 的版本对调没有信息（两版在 1500 拍以前逐拍相同，见「版本对调-断面0」），表里只列 1500 拍以后的
    rows = []
    for k, x in sorted((J.get("ver") or {}).items()):
        ch, t0, hh = k.split("_")
        if int(t0[1:]) < 1500:
            continue
        rows.append([ch, t0[1:], hh[1:], x["n"], sg(x["median"]), f"{sg(x['min'])} ~ {sg(x['max'])}", x["pos"]])
    T["版本对调"] = md(["通道", "断面", "看多少拍", "局数", "ln ρ(Vb) − ln ρ(Va) 中位数", "最小 ~ 最大", "Vb 更高的局数"], rows)
    rows = []
    vr = {}
    for x in (J.get("verRows") or []):
        if x["T0"] >= 1500 and x["ch"] == "C1":
            vr.setdefault(x["g"], {})[x["h"]] = x["d"]
    for g in GAMES:
        if g in vr:
            rows.append([g, "Va" if g == "A007" else "Vb", sg(vr[g].get(300)), sg(vr[g].get(900))])
    v15 = sorted((d_, g_) for g_, hh_ in vr.items() for h2_, d_ in hh_.items() if h2_ == 900)
    if v15:
        ds = [d_ for d_, _ in v15]
        F0["ver1500n"] = str(len(ds))
        F0["ver1500med"] = sg(med(ds))
        F0["ver1500mean"] = sg(mean(ds))
        F0["ver1500min"], F0["ver1500max"] = sg(min(ds)), sg(max(ds))
        F0["ver1500pos"] = str(sum(1 for d_ in ds if d_ > 0))
        F0["ver1500neg"] = str(sum(1 for d_ in ds if d_ < 0))
        big = [(d_, g_) for d_, g_ in v15 if abs(d_) >= 0.15]
        rest = [d_ for d_, g_ in v15 if abs(d_) < 0.15]
        F0["ver1500bigN"] = str(len(big))
        F0["ver1500big"] = "、".join(f"{g_}（{sg(d_)}）" for d_, g_ in big) if big else "没有"
        F0["ver1500restN"] = str(len(rest))
        if rest:
            F0["ver1500restMin"], F0["ver1500restMax"] = sg(min(rest)), sg(max(rest))
    T["版本对调-逐局"] = md(["局", "历史上用的版本", "1500 → 1800 拍：ln ρ(Vb) − ln ρ(Va)", "1500 → 2400 拍：ln ρ(Vb) − ln ρ(Va)"], rows)
    vs = J.get("verSame") or {}
    rows = [[r["g"], r["snaps"], r["diff"], f"{r['issuedA']} / {r['issuedB']}", f"{r['landedA']} / {r['landedB']}"] for r in vs.get("rows", [])]
    T["版本对调-断面0"] = md(["局", "记录拍数（每 30 拍一次）", "与本局版本不同的记录拍数", "发出的指令：本局版本 / 另一版本", "落地的指令：本局版本 / 另一版本"], rows)
    if vs:
        F0["verSameN"] = str(vs["n"])
        F0["verSameIdentical"] = str(vs["identical"])
        F0["verSnaps"] = str(vs["snaps"])
        F0["verIssuedDiff"] = str(vs["issuedDiff"])
    # 同一条对照重跑一次是否逐拍相同
    RR = J.get("rerun") or []
    if RR:
        F0["rerunN"] = str(len(RR))
        F0["rerunSnaps"] = "、".join(str(x_["snaps"]) for x_ in RR)
        F0["rerunDiff"] = str(sum(x_["diff"] for x_ in RR))
        F0["rerunWhat"] = "；".join({"mt-a": "A089，断面 0，C1，种子 1", "mt-b": "A089，断面 630，C2，种子 0"}.get(x_["a"], x_["a"]) for x_ in RR)
    # 只换种子时 ln ρ 的差（正文和「种子间差别」表用）
    SS = J.get("seedSpread") or []
    rows = []
    for T0_, h_ in ((0, 1500), (630, 900), (1500, 900), (4284, 900)):
        for ch_ in ("C1", "C2p"):
            xs = [x_["range"] for x_ in SS if x_["T0"] == T0_ and x_["h"] == h_ and x_["ch"] == ch_]
            if xs:
                rows.append([f"{T0_} → {T0_ + h_}", "C1" if ch_ == "C1" else "C2（走偏）", len(xs), r3(med(xs), 2), f"{r3(min(xs), 2)} ~ {r3(max(xs), 2)}"])
        xs = [x_["range"] for x_ in SS if x_["T0"] == T0_ and x_["h"] == h_]
        if xs:
            F0[f"seed{T0_}n"] = str(len({x_["g"] for x_ in SS if x_["T0"] == T0_ and x_["h"] == h_}))
            F0[f"seed{T0_}min"], F0[f"seed{T0_}max"], F0[f"seed{T0_}med"] = r3(min(xs), 2), r3(max(xs), 2), r3(med(xs), 2)
    T["种子间差别"] = md(["断面 → 观察拍", "通道", "有两个以上种子的局数", "ln ρ 最大 − 最小：各局中位数", "各局最小 ~ 最大"], rows)
    nz = J.get("noise") or []
    rows = []
    for T0 in (0, 630, 1500, 4284):
        xs = [x["maxDev"] for x in nz if x["T0"] == T0]
        if xs:
            rows.append([T0, len(xs), r3(med(xs)), r3(max(xs))])
    T["噪声底"] = md(["断面", "局数", "|ln ρ(只扰动随机数) − ln ρ(历史)| 中位数", "最大"], rows)
    rows = []
    for ch in ("历史", "C2", "C1", "C0"):
        x = (J.get("seatElasticity") or {}).get(ch)
        if x:
            rows.append([ch, x["games"], x["n"], r3(x["slope"], 2), r3(x["r"], 2)])
    T["席位弹性"] = md(["通道", "局数", "席位数", "斜率", "相关系数"], rows)

    # ---- 逐局一行
    rows = []
    for g in GAMES:
        e = E.get(g) or {}
        spans = []
        for w in WINS:
            x = (e.get("win") or {}).get(w)
            if x and x["n"] and x["heldShare"] >= 0.5:
                a, b = (w.split("~") + [""])[:2] if "~" in w else (w.split(" ")[0], "终局")
                if spans and spans[-1][1] == a:
                    spans[-1][1] = b
                else:
                    spans.append([a, b])
        sp = "、".join(f"{a}~{b}" for a, b in spans) if spans else "没有"
        d = (J.get("games") or {}).get(g, {}).get("t0_1500") or {}
        rb = d["rule"] + d["base"] if d.get("rule") is not None and d.get("base") is not None else None
        row = [g, (e.get("ver") or "").capitalize(), sp, r3(d.get("rhoH")), sg(d.get("total")), sg(d.get("spawn")), sg(rb), sg(d.get("hold"))]
        for T0 in (630, 1500, 4284):
            x = (J.get("win") or {}).get(g, {}).get(f"t{T0}_h900")
            row.append(sg(x["hold"]) if x else "—")
        rows.append(row)
    T["逐局"] = md(["局", "版本", "历史上过半指令被按住的时段（发令拍）", "1500 拍的 ρ", "到 1500 拍的落后", "出生站位", "既有规则（含基础延迟）", "按住与成批放行", "按住与成批放行：630 → 1530", "1500 → 2400", "4284 → 5184"], rows, align="lllrrrrrrrr")

    # ---- 种子数一览
    rows = []
    for g in GAMES:
        row = [g]
        d = (J.get("games") or {}).get(g, {})
        for TT in (1500,):
            x = d.get(f"t0_{TT}")
            row.append("/".join(str(k) for k in x["n"]) if x else "—")
        for T0 in (630, 1500, 4284):
            x = (J.get("win") or {}).get(g, {}).get(f"t{T0}_h900")
            row.append("/".join(str(k) for k in x["n"]) if x else "—")
        rows.append(row)
    T["种子数"] = md(["局", "断面 0（C0 / C1 / C2 走偏）", "断面 630", "断面 1500", "断面 4284"], rows)

    # ---- 复现：录像里落地的指令 vs 影子在同一位置发的指令（108_closure_mismatch.py）
    M = jload("closure_mismatch.json")
    rows = []
    for g in GAMES:
        x = (M.get(g) or {}).get("0_1500")
        if not x:
            continue
        c = (J.get("closure") or {}).get(f"{g}@0")
        fd = "—" if not c else ("没有" if c["firstDiff"] is None else c["firstDiff"])
        rows.append([g, x["n"], x["exact"], x["deadEq"], x["bad"], "没有" if x["firstBad"] is None else x["firstBad"], fd])
    x = (M.get("all") or {}).get("0_1500")
    if x:
        rows.append(["**合计**", f"**{x['n']:,}**", f"**{x['exact']:,}**", f"**{x['deadEq']}**", f"**{x['bad']}**", "", ""])
    T["复现-指令差异"] = md(["局", "0~1500 拍录像里落地的指令", "影子发的完全相同", "目标不同但等价", "不等价", "第一条不等价指令的落地拍", "C2 第一处领土与历史不同的记录拍"], rows)

    # ---- 三层汇总（结论用）
    p6, p15 = (J.get("path") or {}).get("630"), (J.get("path") or {}).get("1500")
    lv, chg = sh.get("level1500"), sh.get("change630_1500")
    rows = []
    if p6 and p15 and lv and chg:
        def shr(x, k):
            return f"{pc(x[k]['share'])}（{pc(x[k]['lo'])} ~ {pc(x[k]['hi'])}）"
        val = {"spawn": lambda p: p["spawn"], "hold": lambda p: p["hold"], "rulebase": lambda p: p["rule"] + p["base"], "rule": lambda p: p["rule"], "base": lambda p: p["base"]}
        for k, nm in (("spawn", "**出生站位**"), ("hold", "**按住与成批放行**"), ("rulebase", "**既有规则**（在基础延迟的通道下）"),
                      ("rule", "　其中：规则在零延迟下（余项）"), ("base", "　其中：基础延迟")):
            a, b = val[k](p6), val[k](p15)
            rows.append([nm, sg(a), sg(b), shr(lv, k), sg(b - a), shr(chg, k)])
        rows.append(["合计（−ln ρ 历史）", sg(p6["total"]), sg(p15["total"]), "100%", sg(p15["total"] - p6["total"]), "100%"])
    T["三层-汇总"] = md(["层", "到 630 拍", "到 1500 拍", "占 1500 拍落后的比例", "630 → 1500 拍的变化", "占这段新增落后的比例"], rows)

    # ---- 1500 拍我方的领土与兵力：历史 vs C1
    rows = []
    dens = {}
    for g in GAMES:
        ft = (J.get("fate") or {}).get(g) or {}
        hh, c1 = ft.get("历史"), ft.get("C1")
        if not hh or not c1 or not hh["LS"] or not c1["LS"]:
            continue
        dh, d1 = hh["BS"] / hh["LS"], c1["BS"] / c1["LS"]
        dens[g] = dh / d1
        rows.append([g, f"{hh['LS']:,}", f"{hh['BS']:,}", r3(dh, 1), f"{c1['LS']:,}", f"{c1['BS']:,}", r3(d1, 1), r3(dh / d1, 2)])
    # 1500 → 2400 拍「既有规则」这一层 与 1500 拍时每格余额（历史 ÷ C1）的秩相关
    w15 = ((J.get("win3") or {}).get("1500") or {}).get("games") or {}
    cx = [(dens[g_], w15[g_]["rulebase"]) for g_ in GAMES if g_ in dens and g_ in w15]
    if len(cx) >= 6:
        rho_ = spearman([a_ for a_, _ in cx], [b_ for _, b_ in cx])[0]
        if rho_ is not None:
            F0["w3_1500_rbDensCorr"] = sg(rho_)
            F0["w3_1500_rbDensN"] = str(len(cx))
    T["兵力-1500"] = md(["局", "历史：我方领土（格）", "我方余额", "每格余额", "C1：我方领土（格）", "我方余额", "每格余额", "每格余额 历史 ÷ C1"], rows)

    # ---- 站位基准取法的敏感性
    rows = []
    sm = J.get("sum_t0_1500")
    gs = (S.get("gammaSens") or {}).get("1500")
    if sm and sm.get("n"):
        n = sm["n"]
        tot, rest = sm["total"] / n, (sm["base"] + sm["hold"]) / n
        rows.append([f"本报告的基准：γ = {r3(sm.get('gamma'))}（含已出局者）", sg(sm["spawn"] / n), sg(sm["rule"] / n), pc(sm["spawn"] / sm["total"])])
        if gs:
            for nm, k in (("γ 减一个标准误", "minusSe"), ("γ 加一个标准误", "plusSe")):
                rows.append([nm, sg(gs[k]), sg(tot - gs[k] - rest), pc(gs[k] / tot)])
        rows.append([f"只用还在场的人估弹性：β = {r3(sm.get('beta'))}", sg(sm["spawnB"] / n), sg(sm["ruleB"] / n), pc(sm["spawnB"] / sm["total"])])
        rows.append(["直接用天然地盘之比（弹性取 1）", sg(sm["spawnV"] / n), sg(sm["ruleV"] / n), pc(sm["spawnV"] / sm["total"])])
    T["敏感性-基准"] = md(["站位基准的取法", "出生站位（11 局平均）", "规则（余项）", "出生站位占 1500 拍落后的比例"], rows, align="lrrr")

    # ---- 正文用数：正文里的 {{名字}} 换成这里的值
    F = dict(F0)
    G = J.get("games") or {}
    for TT, x in (J.get("path") or {}).items():
        F[f"rho{TT}"] = r3(math.exp(-x["total"]), 2)
        for k in ("spawn", "rule", "base", "hold", "total"):
            F[f"{k}{TT}"] = sg(x[k])
            F[f"{k}{TT}x"] = r3(math.exp(-x[k]), 2)
        rb = x["rule"] + x["base"]
        F[f"rb{TT}"] = sg(rb)
        F[f"rb{TT}x"] = r3(math.exp(-rb), 2)
        F[f"base{TT}cut"] = pc(1 - math.exp(-x["base"]))
        F[f"base{TT}up"] = pc(math.exp(x["base"]) - 1)
        F[f"hold{TT}cut"] = pc(1 - math.exp(-x["hold"]))
        F[f"bias{TT}"] = sg(x["bias"], 3)
    r630 = [G[g]["t0_630"]["rhoH"] for g in GAMES if G.get(g, {}).get("t0_630")]
    r1500 = [G[g]["t0_1500"]["rhoH"] for g in GAMES if G.get(g, {}).get("t0_1500")]
    if r630:
        F["n630ge1"] = str(sum(1 for x in r630 if x >= 1))
        F["rho630min"], F["rho630max"] = r3(min(r630), 2), r3(max(r630), 2)
    if r1500:
        F["rho1500min"], F["rho1500max"] = r3(min(r1500), 2), r3(max(r1500), 2)
        F["n1500lt1"] = str(sum(1 for x in r1500 if x < 1))
    vs = [x["v"] for x in (S.get("games") or {}).values()]
    if vs:
        F["vmin"], F["vmax"] = r3(min(vs), 2), r3(max(vs), 2)
        for t in ("630", "1500"):
            a = [x[f"vg{t}"] for x in (S.get("games") or {}).values() if x.get(f"vg{t}")]
            F[f"vg{t}min"], F[f"vg{t}max"] = r3(min(a), 2), r3(max(a), 2)
    for t in ("300", "630", "900", "1200", "1500"):
        x = (S.get("gamma") or {}).get(t)
        if x:
            F[f"gamma{t}"], F[f"gammaSe{t}"] = r3(x["g"], 2), r3(x["se"], 2)
    if gs:
        F["spawn1500lo"], F["spawn1500hi"] = sg(gs["minusSe"]), sg(gs["plusSe"])
    fs = S.get("fillSquad")
    if fs:
        F["fillS630"], F["fillS1500"], F["goneS"] = r3(fs["r630"], 2), r3(fs["r1500"], 2), pc(fs["gone"])
    # 按住与成批放行：各局
    hd = {g: G[g]["t0_1500"]["hold"] for g in GAMES if G.get(g, {}).get("t0_1500") and G[g]["t0_1500"].get("hold") is not None}
    if len(hd) >= 4:
        order = sorted(hd, key=lambda g: -hd[g])
        top, rest = order[:3], order[3:]
        F["holdTop3"] = "、".join(f"{g}（{sg(hd[g])}）" for g in top)
        F["holdTop3names"] = "、".join(top)
        F["holdTop3share"] = pc(sum(hd[g] for g in top) / sum(hd.values()))
        F["holdRestMin"], F["holdRestMax"] = sg(min(hd[g] for g in rest)), sg(max(hd[g] for g in rest))
        F["holdRestN"] = str(len(rest))
        F["holdRestMean"] = sg(mean([hd[g] for g in rest]))
        F["holdTop3drop"] = "、".join(pc(E[g]["dropped"] / E[g]["intents"], 1) for g in top if E.get(g, {}).get("intents"))
        heldS, dropS = [], []
        for g in GAMES:
            n = h_ = dr = 0
            for w in SPAN[0]:
                x = (E.get(g, {}).get("win") or {}).get(w)
                if x:
                    n += x["n"]
                    h_ += x["gt35"] + x["dropped"]
                    dr += x["dropped"]
            heldS.append(h_ / n if n else None)
            dropS.append(dr / n if n else None)
        hv = [hd.get(g) for g in GAMES]
        F["holdCorrHeld"] = r3(spearman(heldS, hv)[0], 2)
        F["holdCorrDrop"] = r3(spearman(dropS, hv)[0], 2)
        notes["分层-1500-相关2"] = f"按住与成批放行这一项 与 0~1500 拍没落地的指令占比：秩相关 {F['holdCorrDrop']}（{len(hd)} 局）"
    rbv = {g: G[g]["t0_1500"]["rule"] + G[g]["t0_1500"]["base"] for g in GAMES if G.get(g, {}).get("t0_1500") and G[g]["t0_1500"].get("rule") is not None}
    if rbv:
        for g, x in rbv.items():
            F[f"rb_{g}"] = sg(x)
        F["rbNegN"] = str(sum(1 for x in rbv.values() if x < 0))
        F["rbPosList"] = "、".join(f"{g}（{sg(rbv[g])}）" for g in GAMES if g in rbv and rbv[g] >= 0)
        F["rbPosN"] = str(sum(1 for x in rbv.values() if x >= 0))
        F["rbMin"], F["rbMax"] = sg(min(rbv.values())), sg(max(rbv.values()))
    bs = {g: G[g]["t0_1500"]["base"] for g in GAMES if G.get(g, {}).get("t0_1500") and G[g]["t0_1500"].get("base") is not None}
    if bs:
        F["base1500min"], F["base1500max"] = sg(min(bs.values())), sg(max(bs.values()))
        F["base1500med"] = sg(med(list(bs.values())))
    for key, nm in (("LS", "S"), ("LO", "O"), ("bot", "A")):
        for ch, cn in (("历史", "H"), ("C2p", "C2"), ("C1", "C1"), ("C0", "C0")):
            if acc.get((key, ch)):
                F[f"land{nm}_{cn}"] = f"{mean(acc[(key, ch)]):.1f}%"
    lo_all = [(G[g]["land1500"]["历史"]["LO"], G[g]["land1500"]["C2p"]["LO"]) for g in GAMES if G.get(g, {}).get("land1500", {}).get("C2p")]
    if lo_all:
        nd = sum(1 for a, b in lo_all if b < a)
        F["loDropN"] = str(nd)
        F["loDropOf"] = str(len(lo_all))
        F["loDropPhrase"] = f"{len(lo_all)} 局无一例外" if nd == len(lo_all) else f"{len(lo_all)} 局里 {nd} 局如此"
    for TT in (630, 1500):
        sp = J.get(f"split_{TT}")
        if sp:
            for i, nm in enumerate(("baseS", "baseO", "holdS", "holdO", "biasS", "biasO")):
                F[f"sp{TT}_{nm}"] = sg(sp["mean"][i], 3)
    ft = J.get("fate") or {}
    ratio = [ft[g]["C1"]["issued"] / ft[g]["C0"]["issued"] for g in GAMES if ft.get(g, {}).get("C1") and ft.get(g, {}).get("C0")]
    if ratio:
        F["c1c0issued"] = r3(med(ratio), 2)
    r21 = {g: ft[g]["C2"]["issued"] / ft[g]["C1"]["issued"] for g in GAMES if ft.get(g, {}).get("C1") and ft.get(g, {}).get("C2")}
    for g, x in r21.items():
        F[f"c2c1issued_{g}"] = r3(x, 1)
    for g, x in dens.items():
        F[f"dens_{g}"] = r3(x, 2)
    if len(dens) >= 6:
        od = sorted(dens, key=lambda g: -dens[g])
        F["densTop2"] = "、".join(f"{g}（{r3(dens[g], 2)} 倍）" for g in od[:2])
        F["densNext2"] = "、".join(f"{g}（{r3(dens[g], 2)} 倍）" for g in od[2:4])
        F["dens7min"], F["dens7max"] = r3(min(dens[g] for g in od[4:]), 2), r3(max(dens[g] for g in od[4:]), 2)
        F["dens7n"] = str(len(od) - 4)
    a70 = G.get("A070", {}).get("land1500") or {}
    if a70.get("C0") and a70.get("历史") and a70["历史"]["LS"]:
        F["a070c0x"] = r3(a70["C0"]["LS"] / a70["历史"]["LS"], 1)
    cls = [(g, (J.get("closure") or {}).get(f"{g}@0")) for g in GAMES]
    cls = [(g, c) for g, c in cls if c]
    if cls:
        ex = [g for g, c in cls if c["firstDiff"] is None and c["trajBoth"] == c["trajRows"]]
        df = [(g, c) for g, c in cls if g not in ex]
        F["clsExactN"] = str(len(ex))
        F["clsDiffN"] = str(len(df))
        dv = [c["LSratio"] - 1 for g, c in df if c["LSratio"]]
        if dv:
            F["clsLSmin"], F["clsLSmax"] = f"{100 * min(dv):+.1f}%", f"{100 * max(dv):+.1f}%"
        fdl = [c["firstDiff"] for g, c in df if c["firstDiff"] is not None]
        if fdl:
            F["clsFirstDiffMin"] = str(min(fdl))
    x = (M.get("all") or {}).get("0_1500")
    if x:
        F["mmN"], F["mmExact"], F["mmDead"], F["mmBad"] = f"{x['n']:,}", f"{x['exact']:,}", str(x["deadEq"]), str(x["bad"])
        F["mmBadShare"] = pc(x["bad"] / x["n"], 1)
        F["mmBadGames"] = str(sum(1 for g in GAMES if (M.get(g) or {}).get("0_1500", {}).get("bad")))
    sm = J.get("sum_t0_1500")
    if sm and sm.get("n"):
        n = sm["n"]
        F["bias1500mean"], F["bias1500med"] = sg(sm["bias"] / n, 3), sg(sm["median"]["bias"], 3)
        F["spawnB1500"], F["ruleB1500"], F["spawnV1500"], F["ruleV1500"] = sg(sm["spawnB"] / n), sg(sm["ruleB"] / n), sg(sm["spawnV"] / n), sg(sm["ruleV"] / n)
        F["spawnBshare"], F["spawnVshare"] = pc(sm["spawnB"] / sm["total"]), pc(sm["spawnV"] / sm["total"])
    for ch, nm in (("历史", "H"), ("C2", "C2"), ("C1", "C1"), ("C0", "C0")):
        x = (J.get("seatElasticity") or {}).get(ch)
        if x:
            F[f"slope{nm}"] = r3(x["slope"], 2)
    for key in ("level1500", "change630_1500"):
        x = sh.get(key)
        if x:
            tag = "L" if key == "level1500" else "C"
            F[f"tot{tag}"] = sg(x["total"] / x["n"])
            for k in ("spawn", "hold", "rulebase", "rule", "base"):
                F[f"sh{tag}_{k}"] = pc(x[k]["share"])
                F[f"sh{tag}_{k}_rng"] = f"{pc(x[k]['lo'])} ~ {pc(x[k]['hi'])}"
    F["nRuns"] = str(J.get("nRuns", ""))

    SRC = {"J": J, "E": E, "S": S, "M": M}
    FMT = {"sg": sg, "sg3": lambda v: sg(v, 3), "r2": lambda v: r3(v, 2), "r3": r3, "r1": lambda v: r3(v, 1), "pc": pc, "pc1": lambda v: pc(v, 1),
           "int": lambda v: f"{v:,}", "int0": lambda v: f"{round(v):,}", "g": lambda v: f"{v:g}", "x": lambda v: r3(math.exp(-v), 2), "str": str}
    used = {}

    def lookup(expr):
        """{{名字}} → F；{{J:games.A070.t0_1500.hold|sg}} → 直接取 JSON 里的值再排格式。"""
        if expr in F:
            used[expr] = F[expr]
            return F[expr]
        if ":" in expr and "|" in expr:
            head, fm = expr.rsplit("|", 1)
            s, path_ = head.split(":", 1)
            cur = SRC.get(s)
            try:
                for part in path_.split("."):
                    cur = cur[int(part)] if isinstance(cur, list) else cur[part]
                val = FMT[fm](cur)
            except (KeyError, IndexError, TypeError, ValueError):
                return None
            used[expr] = val
            return val
        return None

    src = os.path.join(HERE, "cp_report_src.md")
    res = []
    missing = []
    if os.path.exists(src):
        import re
        text = open(src, encoding="utf-8").read().split("\n")
        for line in text:
            s = line.strip()
            if s.startswith("@@表 ") and s.endswith("@@"):
                key = s[4:-2].strip()
                if key in T:
                    prev = next((x for x in reversed(res) if x.strip()), "")
                    if T[key].startswith("（这张表") and prev == T[key]:
                        while res and not res[-1].strip():
                            res.pop()      # 连着两张都还没有数据的表：只留一句
                    else:
                        res.append(T[key])
                else:
                    missing.append("表 " + key)
                    res.append(f"（缺表：{key}）")
                continue
            if s.startswith("@@") and s.endswith("@@"):
                missing.append(s)

            def rep(m):
                v = lookup(m.group(1).strip())
                if v is None or v == "—":
                    missing.append(m.group(1).strip())
                    return f"【缺：{m.group(1).strip()}】"
                return v
            res.append(re.sub(r"\{\{([^{}]+)\}\}", rep, line))

    out = ["# 断面对照：报告用表（107_cp_report.py 生成）", ""]
    for k, v in T.items():
        out += [f"## {k}", "", v, ""]
        for nk, nv in notes.items():
            if nk.startswith(k):
                out += [nv, ""]
    left = [nk for nk in notes if not any(nk.startswith(k) for k in T)]
    for nk in left:
        out += [f"{nk}：{notes[nk]}", ""]
    out += ["## 正文用数", "", "正文里用到的、不在上面表格里直接出现的数（名字 → 值）：", ""]
    for k in sorted(set(list(F.keys()) + list(used.keys()))):
        out.append(f"- {k} → {used.get(k, F.get(k))}")
    out.append("")
    open(os.path.join(CROSS, "cp_report_tables.md"), "w", encoding="utf-8").write("\n".join(out))

    if res:
        os.makedirs(os.path.join(BASE, "reports"), exist_ok=True)
        open(os.path.join(BASE, "reports", "OFFLINE-CHECKPOINT-ATTRIBUTION.md"), "w", encoding="utf-8").write("\n".join(res))
        print(f"REPORT-OK {len(res)} 行；还缺 {len(missing)} 处：{missing}")
    print(f"TABLES-OK {len(T)} 张；正文用数 {len(F)} 个")


if __name__ == "__main__":
    main()
