#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""103_cp_table.py — R07：把 100_checkpoint.mjs 的各次运行汇总成表（任务卡 0002 的三层归因）。

读：out/_cache/cp/<局>/*.json（各次运行）、out/<局>/voronoi.json（46_voronoi.mjs：出生点的天然地盘）、out/<局>/release_map.json
写：out/_cross/cp_runs.tsv（每次运行 × 每个观察拍一行；进 git，报告里的数都从这里出）
    out/_cross/checkpoint_attribution.txt / .json（报告用的表）

量的定义：
  ρ(t) = 我方号人均领土 ÷ 其他真人人均领土（人数都按开局第 1 拍有地的席位数算，中途离开或死亡的席位仍算在分母里）
  v    = 我方号人均天然地盘 ÷ 其他真人人均天然地盘（天然地盘 = 全图陆地按直线距离分给最近的真人出生点）
  从断面 0 出发、看到 T 拍：
     −ln ρ历史(T) = [−ln v] + [ln v − ln ρC1(T)] + [ln ρC1(T) − ln ρC2(T)] + [ln ρC2(T) − ln ρ历史(T)]
                   出生站位     规则（正常通道下相对天然地盘）   按住与成批放行           模型没对上的部分
     另列 ln ρC0(T) − ln ρC1(T)：基础延迟（零延迟的模拟器比正常线上通道多出来的）
  从断面 T0>0 出发、看 h 拍：Δ通道 = ln ρ通道(T0+h) − ln ρ(T0)；按住与成批放行 = ΔC1 − ΔC2；基础延迟 = ΔC0 − ΔC1；没对上 = ΔC2 − Δ历史
用法：python3 103_cp_table.py
"""
import csv
import glob
import json
import math
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out")
CP = os.path.join(OUT, "_cache", "cp")
CROSS = os.path.join(OUT, "_cross")
GAMES = ["A007", "A033", "A039", "A053", "A061", "A062", "A070", "A079", "A082", "A089", "A091"]
T0S = [0, 630, 1500, 4284]
HORIZ = {0: [300, 630, 900, 1200, 1500], 630: [150, 300, 450, 600, 900], 1500: [150, 300, 450, 600, 900], 4284: [150, 300, 450, 600, 900]}


def jload(p):
    try:
        return json.load(open(p, encoding="utf-8"))
    except (OSError, ValueError):
        return None


def snap_at(snaps, t, tol=16):
    best = None
    for s in snaps:
        if abs(s["t"] - t) <= tol and (best is None or abs(s["t"] - t) < abs(best["t"] - t)):
            best = s
    return best


def rho(s, nS, nO):
    if not s or s["LO"] <= 0 or nS <= 0 or nO <= 0:
        return None
    return (s["LS"] / nS) / (s["LO"] / nO)


def ln(x):
    return math.log(x) if x and x > 0 else None


def mean(a):
    a = [x for x in a if x is not None]
    return sum(a) / len(a) if a else None


def sd(a):
    a = [x for x in a if x is not None]
    return statistics.pstdev(a) if len(a) >= 2 else None


def f(x, nd=3):
    return "-" if x is None else f"{x:.{nd}f}"


def sub(a, b):
    return None if a is None or b is None else a - b


def main():
    os.makedirs(CROSS, exist_ok=True)
    runs = {}      # (mid, tag) → json
    base = {}
    for g in GAMES:
        for p in sorted(glob.glob(os.path.join(CP, g, "*.json"))):
            tag = os.path.basename(p)[:-5]
            j = jload(p)
            if not j:
                continue
            if tag == "H":
                base[g] = j
            else:
                runs[(g, tag)] = j
    vor = {g: jload(os.path.join(OUT, g, "voronoi.json")) for g in GAMES}
    rmap = {g: jload(os.path.join(OUT, g, "release_map.json")) for g in GAMES}

    def vpar(g):
        v = vor[g]
        if not v:
            return None
        gs = v["groups"]
        nS, vS = gs["我方号"]["n"], gs["我方号"]["vor"]
        nO = sum(x["n"] for k, x in gs.items() if k != "我方号")
        vO = sum(x["vor"] for k, x in gs.items() if k != "我方号")
        return (vS / nS) / (vO / nO)

    # ---------- cp_runs.tsv
    rows = []
    for (g, tag), j in sorted(runs.items()):
        h = base.get(g)
        if not h:
            continue
        nS, nO = h["nSquad"], h["nOther"]
        T0 = j["T0"]
        s0 = snap_at(j["snaps"], T0, 1) or snap_at(h["snaps"], T0, 1)
        variant = tag.split("-s" + str(j["seed"]), 1)[1].lstrip("-") if ("-s" + str(j["seed"])) in tag else ""
        for hh in HORIZ.get(T0, []):
            t = T0 + hh
            s = snap_at(j["snaps"], t)
            sh = snap_at(h["snaps"], s["t"], 1) if s else None
            if not s:
                continue
            dv = j.get("div")
            okd = n_o = trabs = trh = 0
            if dv:
                for w in dv["win"]:
                    if w["t0"] < t:
                        okd += w["okDiff"]; n_o += w["n"]; trabs += w["trAbs"]; trh += w["trH"]
            cs = j["chanStat"]
            rows.append({
                "mid": g, "tag": tag, "ver": j["ver"], "native": 1 if j["ver"] == j["nativeVer"] else 0, "chan": j["chan"], "variant": variant,
                "T0": T0, "seed": j["seed"], "h": hh, "t": s["t"],
                "LS": s["LS"], "LO": s["LO"], "BS": s["BS"], "BO": s["BO"], "aS": s["aS"], "aO": s["aO"], "outS": s["outS"],
                "rho": f(rho(s, nS, nO), 4), "rho0": f(rho(s0, nS, nO), 4),
                "H_LS": sh["LS"] if sh else "", "H_LO": sh["LO"] if sh else "", "H_rho": f(rho(sh, nS, nO), 4) if sh else "",
                "issued": cs["issued"], "landed": cs["landed"], "landedOk": cs["landedOk"], "mapDrop": cs["mapDrop"], "capDrop": cs["capDrop"],
                "second": cs["second"], "donRej": cs["donRej"], "inflight": cs["inflight"],
                "delayP50": j["delayQ"]["p50"] if j["delayQ"]["p50"] is not None else "", "delayP90": j["delayQ"]["p90"] if j["delayQ"]["p90"] is not None else "",
                "oppCmds": n_o, "oppOkFlip": okd, "oppTroopDiff": f(trabs / trh, 3) if trh else "", "firstOkFlip": dv["firstOkDiff"] if dv else "",
                "leaveSkipped": j["leaveSkipped"], "err": j["errCount"], "end": j["endTick"], "over": j["over"],
            })
    cols = list(rows[0].keys()) if rows else []
    with open(os.path.join(CROSS, "cp_runs.tsv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, delimiter="\t")
        w.writeheader()
        w.writerows(rows)

    # ---------- 取数的小工具
    def get(g, chan, T0, hh, variant="", ver_native=True, seeds=(0, 1, 2)):
        """返回 [(seed, ρ)]"""
        out = []
        for r in rows:
            if r["mid"] == g and r["chan"] == chan and r["T0"] == T0 and r["h"] == hh and r["variant"] == variant and (r["native"] == 1) == ver_native and r["seed"] in seeds:
                if r["rho"] != "-":
                    out.append((r["seed"], float(r["rho"])))
        return out

    def lnmean(g, chan, T0, hh, **kw):
        v = [math.log(x) for _, x in get(g, chan, T0, hh, **kw) if x > 0]
        return (mean(v), sd(v), len(v))

    def hist_rho(g, t):
        h = base[g]
        return rho(snap_at(h["snaps"], t), h["nSquad"], h["nOther"])

    L = []
    P = L.append
    J = {"games": {}}
    P("# 历史断面离线对照：三层失分归因的底表（103_cp_table.py）")
    P("# ρ = 我方号人均领土 ÷ 其他真人人均领土；v = 我方号人均天然地盘 ÷ 其他真人人均天然地盘；数是自然对数差（0.10 ≈ 差 10%，0.69 = 差一倍）")
    P("# 每个通道 3 个种子（种子 0 不扰动；1、2 在接管那一拍让引擎随机数多走 1、2 步，C1 的延迟也换一组）；括号里是 3 个种子的标准差")
    P("")
    n_runs = len(runs)
    P(f"运行数：{n_runs} 次；基线 {len(base)} 局")
    P("")

    # ---------- 表 0：通道模型对历史的复现（C2 种子 0）
    P("## 表 0：C2（历史实录轨迹）种子 0 对历史的复现：局 | 断面 | +300 / +600 / +900 拍时 我方领土 C2 ÷ 历史、其他真人领土 C2 ÷ 历史 | 首次出现别的真人指令结果与历史不同的拍")
    for g in GAMES:
        for T0 in T0S:
            cells = []
            ff = ""
            for hh in ([300, 630, 900, 1500] if T0 == 0 else [300, 600, 900]):
                r = [x for x in rows if x["mid"] == g and x["chan"] == "C2" and x["T0"] == T0 and x["seed"] == 0 and x["variant"] == "" and x["native"] == 1 and x["h"] == hh]
                if not r or r[0]["H_LS"] == "":
                    cells.append("-")
                    continue
                r = r[0]
                ff = r["firstOkFlip"]
                a = f"{r['LS'] / r['H_LS']:.3f}" if r["H_LS"] else ("=" if r["LS"] == 0 else "历史为 0")
                b = f"{r['LO'] / r['H_LO']:.3f}" if r["H_LO"] else "-"
                cells.append(f"+{hh}: {a} / {b}")
            if any(c != "-" for c in cells):
                P(f"{g}\t{T0}\t" + "\t".join(cells) + f"\t{ff}")
    P("")

    # ---------- 表 1：断面 0 的三层分解
    for T in (630, 1500):
        P(f"## 表 1-{T}：断面 0 → {T} 拍。局 | v | ρ历史 | ρC2 | ρC1 | ρC0 | 出生站位 −ln v | 规则 ln v − ln ρC1 | 按住与成批放行 ln ρC1 − ln ρC2 | 没对上 ln ρC2 − ln ρ历史 | 合计 −ln ρ历史 | 另：基础延迟 ln ρC0 − ln ρC1 | 噪声底（只扰动随机数的历史重放，ln ρ 的标准差）")
        agg = {"spawn": [], "rule": [], "hold": [], "resid": [], "total": [], "base": []}
        for g in GAMES:
            v = vpar(g)
            rh = hist_rho(g, T)
            c2 = lnmean(g, "C2", 0, T)
            c1 = lnmean(g, "C1", 0, T)
            c0 = lnmean(g, "C0", 0, T)
            hp = lnmean(g, "H", 0, T, seeds=(1, 2))
            if rh is None or c1[0] is None or c2[0] is None:
                continue
            noise = None
            hpv = [math.log(x) for _, x in get(g, "H", 0, T, seeds=(1, 2)) if x > 0]
            if hpv:
                noise = statistics.pstdev(hpv + [math.log(rh)])
            spawn = -math.log(v)
            rule = math.log(v) - c1[0]
            hold = c1[0] - c2[0]
            resid = c2[0] - math.log(rh)
            total = -math.log(rh)
            basd = sub(c0[0], c1[0])
            for k, x in (("spawn", spawn), ("rule", rule), ("hold", hold), ("resid", resid), ("total", total), ("base", basd)):
                agg[k].append(x)
            J["games"].setdefault(g, {})[f"t0_{T}"] = {"v": v, "rhoH": rh, "lnC2": c2, "lnC1": c1, "lnC0": c0, "spawn": spawn, "rule": rule, "hold": hold, "resid": resid, "total": total, "base": basd, "noise": noise}
            P(f"{g}\t{v:.3f}\t{rh:.3f}\t{math.exp(c2[0]):.3f}\t{math.exp(c1[0]):.3f}\t{f(math.exp(c0[0]) if c0[0] is not None else None)}\t{spawn:+.3f}\t{rule:+.3f}\t{hold:+.3f}（±{f(math.hypot(c1[1] or 0, c2[1] or 0), 2)}）\t{resid:+.3f}\t{total:+.3f}\t{f(basd)}\t{f(noise)}")
        if agg["total"]:
            P("中位数\t\t\t\t\t\t" + "\t".join(f"{statistics.median(agg[k]):+.3f}" for k in ("spawn", "rule", "hold", "resid", "total")) + f"\t{statistics.median([x for x in agg['base'] if x is not None]):+.3f}")
            P("合计（11 局相加）\t\t\t\t\t\t" + "\t".join(f"{sum(agg[k]):+.3f}" for k in ("spawn", "rule", "hold", "resid", "total")) + f"\t{sum(x for x in agg['base'] if x is not None):+.3f}")
            J[f"sum_t0_{T}"] = {k: sum(x for x in agg[k] if x is not None) for k in agg}
        P("")

    # ---------- 表 2：各断面的窗口分解
    for T0 in (630, 1500, 4284):
        for hh in (300, 600, 900):
            P(f"## 表 2-{T0}+{hh}：断面 {T0} → {T0 + hh} 拍。局 | ρ(断面) | Δ历史 | ΔC2 | ΔC1 | ΔC0 | 按住与成批放行 ΔC1 − ΔC2（±种子标准差）| 基础延迟 ΔC0 − ΔC1 | 没对上 ΔC2 − Δ历史 | 噪声底 | 别的真人指令结果翻转（C1，占条数）")
            acc = {"hold": [], "base": [], "resid": [], "dH": [], "dC1": []}
            for g in GAMES:
                h = base[g]
                r0 = rho(snap_at(h["snaps"], T0, 1), h["nSquad"], h["nOther"])
                rh = hist_rho(g, T0 + hh)
                if r0 is None or r0 <= 0:
                    continue
                c2 = lnmean(g, "C2", T0, hh)
                c1 = lnmean(g, "C1", T0, hh)
                c0 = lnmean(g, "C0", T0, hh)
                if c1[0] is None or c2[0] is None:
                    continue
                l0 = math.log(r0)
                dH = sub(ln(rh), l0)
                d2, d1, d0 = c2[0] - l0, c1[0] - l0, sub(c0[0], l0)
                hpv = [math.log(x) for _, x in get(g, "H", T0, hh, seeds=(1, 2)) if x > 0]
                noise = statistics.pstdev(hpv + [math.log(rh)]) if hpv and rh else None
                fl = [x for x in rows if x["mid"] == g and x["chan"] == "C1" and x["T0"] == T0 and x["h"] == hh and x["variant"] == "" and x["native"] == 1]
                flip = (sum(x["oppOkFlip"] for x in fl) / max(1, sum(x["oppCmds"] for x in fl))) if fl else None
                hold = d1 - d2
                basd = sub(d0, d1)
                resid = sub(d2, dH)
                acc["hold"].append(hold); acc["base"].append(basd); acc["resid"].append(resid); acc["dH"].append(dH); acc["dC1"].append(d1)
                J["games"].setdefault(g, {})[f"t{T0}_h{hh}"] = {"rho0": r0, "dH": dH, "dC2": d2, "dC1": d1, "dC0": d0, "hold": hold, "holdSd": math.hypot(c1[1] or 0, c2[1] or 0), "base": basd, "resid": resid, "noise": noise, "flip": flip}
                P(f"{g}\t{r0:.3f}\t{f(dH)}\t{d2:+.3f}\t{d1:+.3f}\t{f(d0)}\t{hold:+.3f}（±{f(math.hypot(c1[1] or 0, c2[1] or 0), 2)}）\t{f(basd)}\t{f(resid)}\t{f(noise)}\t{f(100 * flip, 1) + '%' if flip is not None else '-'}")
            if acc["hold"]:
                okv = lambda k: [x for x in acc[k] if x is not None]
                P(f"中位数\t\t{statistics.median(okv('dH')):+.3f}\t\t{statistics.median(okv('dC1')):+.3f}\t\t{statistics.median(okv('hold')):+.3f}\t{statistics.median(okv('base')):+.3f}\t{statistics.median(okv('resid')):+.3f}")
            P("")

    # ---------- 表 3：版本对照（Va ↔ Vb）
    P("## 表 3：另一个历史版本在同一断面、同一通道下（ln ρ另一版本 − ln ρ本局版本；本局版本：A007 = Va，其余 = Vb；另一版本各 2 个种子）")
    P("局\t断面\t看多少拍\tC1：另一版本 − 本局版本\tC2：另一版本 − 本局版本")
    verd = {"C1": [], "C2": []}
    for g in GAMES:
        for T0 in (0, 630, 1500):
            for hh in ((630, 1500) if T0 == 0 else (300, 900)):
                cells = []
                for ch in ("C1", "C2"):
                    alt = "vb" if g == "A007" else "va"
                    a = lnmean(g, ch, T0, hh, variant=alt, ver_native=False, seeds=(0, 1))
                    n = lnmean(g, ch, T0, hh)
                    dlt = sub(a[0], n[0])
                    cells.append(f(dlt))
                    if dlt is not None:
                        verd[ch].append((g, T0, hh, dlt))
                        J["games"].setdefault(g, {})[f"ver_{ch}_t{T0}_h{hh}"] = dlt
                if any(c != "-" for c in cells):
                    P(f"{g}\t{T0}\t{hh}\t" + "\t".join(cells))
    for ch in ("C1", "C2"):
        vb_minus_va = [(-d if g == "A007" else -d) for g, T0, hh, d in verd[ch]]
        # 统一成 Vb − Va：A007 的另一版本是 Vb（d = Vb − Va）；其余局的另一版本是 Va（d = Va − Vb → 取负）
        vb_minus_va = [(d if g == "A007" else -d) for g, T0, hh, d in verd[ch]]
        if vb_minus_va:
            P(f"{ch}：统一成 ln ρ(Vb) − ln ρ(Va)，{len(vb_minus_va)} 个断面窗口：中位数 {statistics.median(vb_minus_va):+.3f}，最小 {min(vb_minus_va):+.3f}，最大 {max(vb_minus_va):+.3f}，>0 的 {sum(1 for x in vb_minus_va if x > 0)} 个")
            J[f"ver_{ch}"] = {"n": len(vb_minus_va), "median": statistics.median(vb_minus_va), "min": min(vb_minus_va), "max": max(vb_minus_va), "pos": sum(1 for x in vb_minus_va if x > 0)}
    P("")

    # ---------- 表 4：延迟敏感性
    P("## 表 4：基础延迟取法的敏感性（断面 0 → 630 / 1500，断面 630 → +300 / +900；ln ρ − ln ρ(C1 默认，种子 0)）")
    P("局\t断面\t看多少拍\tC0b（零延迟 + 一拍一条）− C0\td 取 5~12 均匀\td 取 10~18 均匀")
    for g in GAMES:
        for T0 in (0, 630):
            for hh in ((630, 1500) if T0 == 0 else (300, 900)):
                c1 = lnmean(g, "C1", T0, hh, seeds=(0,))
                c0 = lnmean(g, "C0", T0, hh, seeds=(0,))
                c0b = lnmean(g, "C0b", T0, hh, seeds=(0,))
                u = lnmean(g, "C1", T0, hh, variant="d5_12", seeds=(0,))
                w = lnmean(g, "C1", T0, hh, variant="d10_18", seeds=(0,))
                if c1[0] is None:
                    continue
                P(f"{g}\t{T0}\t{hh}\t{f(sub(c0b[0], c0[0]))}\t{f(sub(u[0], c1[0]))}\t{f(sub(w[0], c1[0]))}")
    P("")

    # ---------- 表 5：席位离开敏感性
    P("## 表 5：不执行录像里我方号的离开（A061、A062；ln ρ不离开 − ln ρ照录像离开，种子 0）")
    P("局\t断面\t看多少拍\tC1\tC2")
    for g in ("A061", "A062"):
        for T0 in (0, 630, 1500):
            for hh in ((630, 1500) if T0 == 0 else (300, 900)):
                cells = []
                for ch in ("C1", "C2"):
                    a = lnmean(g, ch, T0, hh, variant="nl", seeds=(0,))
                    n = lnmean(g, ch, T0, hh, seeds=(0,))
                    cells.append(f(sub(a[0], n[0])))
                if any(c != "-" for c in cells):
                    P(f"{g}\t{T0}\t{hh}\t" + "\t".join(cells))
    P("")

    # ---------- 表 6：通道里的指令去向（断面 0 → 1500，种子 0）
    P("## 表 6：断面 0 → 1500 我方指令的去向（种子 0）：局 | 通道 | 发出 | 落地 | 生效 | 按历史轨迹没落地 | 同一拍第二条被拒 | 在途拍数 P50 / P90 | 1500 拍我方领土 | 我方余额 | 我方在外的进攻兵")
    for g in GAMES:
        for ch in ("C0", "C1", "C2"):
            r = [x for x in rows if x["mid"] == g and x["chan"] == ch and x["T0"] == 0 and x["seed"] == 0 and x["variant"] == "" and x["native"] == 1 and x["h"] == 1500]
            if not r:
                continue
            r = r[0]
            P(f"{g}\t{ch}\t{r['issued']}\t{r['landed']}\t{r['landedOk']}\t{r['mapDrop']}\t{r['second']}\t{r['delayP50']} / {r['delayP90']}\t{r['LS']}\t{r['BS']}\t{r['outS']}")
        h = base[g]
        s = snap_at(h["snaps"], 1500)
        rm = rmap[g]
        n_land = sum(1 for b, sv in rm["seats"].items() for p in sv["pts"] if p[0] + p[1] < 1500) if rm else ""
        P(f"{g}\t历史\t\t{n_land}\t\t\t\t\t{s['LS']}\t{s['BS']}\t{s['outS']}")
    P("")

    # ---------- 表 7：席位层面，领土对天然地盘的弹性
    P("## 表 7：席位层面（我方每个号）：1500 拍领土的对数对天然地盘的对数回归（局内去均值；断面 0 的运行，种子 0）")
    P("通道\t席位数\t斜率\t相关系数")
    for ch in ("历史", "C2", "C1", "C0"):
        xs, ys = [], []
        for g in GAMES:
            v = vor[g]
            h = base[g]
            if ch == "历史":
                j = h
            else:
                j = runs.get((g, f"{ch}-t0-s0"))
            if not j or not v:
                continue
            s = snap_at(j["snaps"], 1500)
            if not s:
                continue
            px, py = [], []
            for i, sq in enumerate(h["squad"]):
                vv = v["squad"].get(sq["bot"], {}).get("vor")
                tt = s["seat"][i]
                if vv and tt and tt > 0:
                    px.append(math.log(vv)); py.append(math.log(tt))
            if len(px) >= 3:
                mx, my = mean(px), mean(py)
                xs += [x - mx for x in px]; ys += [y - my for y in py]
        if len(xs) >= 10:
            sxx = sum(x * x for x in xs); sxy = sum(x * y for x, y in zip(xs, ys)); syy = sum(y * y for y in ys)
            P(f"{ch}\t{len(xs)}\t{sxy / sxx:.2f}\t{sxy / math.sqrt(sxx * syy):.2f}")
            J.setdefault("seatElasticity", {})[ch] = {"n": len(xs), "slope": sxy / sxx, "r": sxy / math.sqrt(sxx * syy)}
    P("")

    open(os.path.join(CROSS, "checkpoint_attribution.txt"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    json.dump(J, open(os.path.join(CROSS, "checkpoint_attribution.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n".join(L[:400]))


if __name__ == "__main__":
    main()
