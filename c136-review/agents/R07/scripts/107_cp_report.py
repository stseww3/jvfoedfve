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
                pos = sm["spawn"] + sm["base"] + sm["hold"]
                if sm["spawn"] > 0 and sm["base"] > 0 and sm["hold"] > 0:
                    rows.append(["三个失分项之间的比例", "", "", "", "", "", pc(sm["spawn"] / pos), "", pc(sm["base"] / pos), pc(sm["hold"] / pos), ""])
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

    # ---- 各断面往后的窗口
    for T0 in (630, 1500, 4284):
        for hh in (300, 600, 900):
            rows = []
            hs, hd = [], []
            for g in GAMES:
                d = (J.get("win") or {}).get(g, {}).get(f"t{T0}_h{hh}")
                if not d:
                    continue
                hsh, hn = held(g, T0)
                dh = "历史上已全灭" if d.get("rhoH") == 0 else sg(d["dH"])
                rows.append([g, r3(d["rho0"]), pc(hsh) if hh == 900 else "", dh, sg(d["d2p"]), sg(d["d1"]), sg(d["d0"]), sg(d["base"]), sg(d["hold"]), sg(d["bias"])])
                hs.append(hsh)
                hd.append(d["hold"])
            ws = (J.get("winSum") or {}).get(f"t{T0}_h{hh}")
            if ws:
                ks = ("dH", "d2p", "d1", "d0", "base", "hold", "bias")
                rows.append(["**平均**", "", ""] + [f"**{sg(ws[k]['mean'])}**（{ws[k]['n']} 局）" for k in ks])
                rows.append(["中位数", "", ""] + [sg(ws[k]["median"]) for k in ks])
                if hh == 900:
                    rho, nn = spearman(hs, hd)
                    notes[f"窗口-{T0}-相关"] = f"断面 {T0} 往后 900 拍：按住与成批放行这一项 与 这一窗被按住的指令占比 的秩相关 {r3(rho, 2)}（{nn} 局）"
            head = ["局", "断面时的 ρ", "这 900 拍里历史上被按住的指令占比" if hh == 900 else "", "历史", "C2（同样走偏）", "C1", "C0", "基础延迟", "按住与成批放行", "走偏带来的虚高"]
            T[f"窗口-{T0}-{hh}"] = md(head, rows)
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
    T["敏感性-延迟"] = md(["通道取法", "发令到生效平均拍数", "到 630 拍：ln ρ − ln ρ(C0) 中位数", "最小 ~ 最大", "到 1500 拍：中位数", "最小 ~ 最大"], rows, align="llrrrr")
    rows = [[x["g"], x["T0"], x["h"], x["C1"], x["C2"]] for x in (J.get("leave") or [])]
    T["敏感性-离开"] = md(["局", "断面", "看多少拍", "C1：ln ρ(不离开) − ln ρ(照录像离开)", "C2"], rows)
    rows = []
    for k, x in sorted((J.get("ver") or {}).items()):
        ch, t0, hh = k.split("_")
        rows.append([ch, t0[1:], hh[1:], x["n"], sg(x["median"]), f"{sg(x['min'])} ~ {sg(x['max'])}", x["pos"]])
    T["版本对调"] = md(["通道", "断面", "看多少拍", "局数", "ln ρ(Vb) − ln ρ(Va) 中位数", "最小 ~ 最大", "Vb 更高的局数"], rows)
    rows = []
    for x in (J.get("verRows") or []):
        rows.append([x["g"], x["ch"], x["T0"], x["h"], sg(x["d"])])
    T["版本对调-逐局"] = md(["局", "通道", "断面", "看多少拍", "ln ρ(Vb) − ln ρ(Va)"], rows)
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

    out = ["# 断面对照：报告用表（107_cp_report.py 生成）", ""]
    for k, v in T.items():
        out += [f"## {k}", "", v, ""]
        for nk, nv in notes.items():
            if nk.startswith(k):
                out += [nv, ""]
    left = [nk for nk in notes if not any(nk.startswith(k) for k in T)]
    for nk in left:
        out += [f"{nk}：{notes[nk]}", ""]
    open(os.path.join(CROSS, "cp_report_tables.md"), "w", encoding="utf-8").write("\n".join(out))

    src = os.path.join(HERE, "cp_report_src.md")
    if os.path.exists(src):
        text = open(src, encoding="utf-8").read().split("\n")
        res = []
        missing = []
        for line in text:
            s = line.strip()
            if s.startswith("@@表 ") and s.endswith("@@"):
                key = s[4:-2].strip()
                if key in T:
                    res.append(T[key])
                else:
                    missing.append(key)
                    res.append(f"（缺表：{key}）")
            else:
                res.append(line)
        os.makedirs(os.path.join(BASE, "reports"), exist_ok=True)
        open(os.path.join(BASE, "reports", "OFFLINE-CHECKPOINT-ATTRIBUTION.md"), "w", encoding="utf-8").write("\n".join(res))
        print(f"REPORT-OK {len(res)} 行；缺表 {missing}")
    print(f"TABLES-OK {len(T)} 张")


if __name__ == "__main__":
    main()
