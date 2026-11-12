#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""103_cp_table.py — R07：把 100_checkpoint.mjs 的各次运行汇总成表（任务卡 0002 的分层归因）。

读：out/_cache/cp/<局>/*.json（各次运行）、out/<局>/voronoi.json（46_voronoi.mjs：出生点的天然地盘）
写：out/_cross/cp_runs.tsv（每次运行 × 每个观察拍一行；进 git，报告里的数都从这里出）
    out/_cross/checkpoint_attribution.txt / .json（报告用的表）

量的定义：
  ρ(t) = 我方号人均领土 ÷ 其他真人人均领土（人数都按开局第 1 拍有地的席位数算，中途离开或死亡的席位仍算在分母里）
  v    = 我方号人均天然地盘 ÷ 其他真人人均天然地盘（天然地盘 = 全图陆地按直线距离分给最近的真人出生点）
  从断面 0 出发、看到 T 拍（数都是自然对数差，正数 = 让我方落后）：
     −ln ρ历史(T) = [−ln v]            出生站位：天然地盘比别的真人少
                  + [ln v − ln ρC0(T)]   规则：零延迟下，原策略把天然地盘变成领土的效率比别的真人低多少（负数 = 比别人高）
                  + [ln ρC0 − ln ρC1]    基础延迟：正常线上通道（每条指令晚 1~2 个回合）
                  + [ln ρC1 − ln ρC2]    按住与成批放行：历史实录轨迹相对正常通道
                  + [ln ρC2 − ln ρ历史]  没对上：通道模型没复现历史的部分
  从断面 T0>0 出发、看 h 拍：Δ通道 = ln ρ通道(T0+h) − ln ρ历史(T0)
     Δ历史 = ΔC0 − [ΔC0 − ΔC1] − [ΔC1 − ΔC2] − [ΔC2 − Δ历史]
用法：python3 103_cp_table.py
"""
import csv
import glob
import json
import math
import os
import statistics

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


def f(x, nd=3, sign=False):
    if x is None:
        return "-"
    return f"{x:+.{nd}f}" if sign else f"{x:.{nd}f}"


def sub(a, b):
    return None if a is None or b is None else a - b


def med(a):
    a = [x for x in a if x is not None]
    return statistics.median(a) if a else None


def main():
    os.makedirs(CROSS, exist_ok=True)
    runs = {}
    base = {}
    for g in GAMES:
        for p in sorted(glob.glob(os.path.join(CP, g, "*.json"))):
            tag = os.path.basename(p)[:-5]
            if tag.startswith("mt-") or tag.endswith("-dbg") or tag.endswith("-full"):
                continue
            j = jload(p)
            if not j:
                continue
            if tag == "H":
                base[g] = j
            else:
                runs[(g, tag)] = j
    vor = {g: jload(os.path.join(OUT, g, "voronoi.json")) for g in GAMES}

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
        s0 = snap_at(h["snaps"], T0, 1)
        sfx = "-s" + str(j["seed"])
        variant = tag.split(sfx, 1)[1].lstrip("-") if sfx in tag else ""
        for hh in HORIZ.get(T0, []):
            t = T0 + hh
            s = snap_at(j["snaps"], t)
            if not s:
                continue
            sh = snap_at(h["snaps"], s["t"], 1)
            dv = j.get("div")
            okd = n_o = trabs = trh = 0
            if dv:
                for w in dv["win"]:
                    if w["t0"] < t:
                        okd += w["okDiff"]; n_o += w["n"]; trabs += w["trAbs"]; trh += w["trH"]
            cs = j["chanStat"]
            ps = j.get("posStat") or {}
            rows.append({
                "mid": g, "tag": tag, "ver": j["ver"], "native": 1 if j["ver"] == j["nativeVer"] else 0, "chan": j["chan"], "variant": variant,
                "T0": T0, "seed": j["seed"], "h": hh, "t": s["t"],
                "LS": s["LS"], "LO": s["LO"], "botL": s["botL"], "BS": s["BS"], "BO": s["BO"], "aS": s["aS"], "aO": s["aO"], "outS": s["outS"],
                "rho": f(rho(s, nS, nO), 4), "rho0": f(rho(s0, nS, nO), 4),
                "H_LS": sh["LS"] if sh else "", "H_LO": sh["LO"] if sh else "", "H_botL": sh["botL"] if sh else "", "H_rho": f(rho(sh, nS, nO), 4) if sh else "",
                "issued": cs["issued"], "landed": cs["landed"], "landedOk": cs["landedOk"], "mapDrop": cs["mapDrop"], "capDrop": cs["capDrop"],
                "second": cs["second"], "donRej": cs["donRej"], "inflight": cs["inflight"],
                "posHist": ps.get("hist", ""), "posBefore": ps.get("before", ""), "posAfter": ps.get("after", ""),
                "delayP50": j["delayQ"]["p50"] if j["delayQ"]["p50"] is not None else "", "delayP90": j["delayQ"]["p90"] if j["delayQ"]["p90"] is not None else "",
                "oppCmds": n_o, "oppOkFlip": okd, "oppTroopDiff": f(trabs / trh, 3) if trh else "", "firstOkFlip": dv["firstOkDiff"] if dv else "",
                "leaveSkipped": j["leaveSkipped"], "err": j["errCount"], "end": j["endTick"], "over": j["over"], "land": h["land"],
            })
    if rows:
        with open(os.path.join(CROSS, "cp_runs.tsv"), "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), delimiter="\t")
            w.writeheader()
            w.writerows(rows)

    def sel(g, chan, T0, hh, variant="", native=True, seeds=(0, 1, 2)):
        return [r for r in rows if r["mid"] == g and r["chan"] == chan and r["T0"] == T0 and r["h"] == hh and r["variant"] == variant
                and (r["native"] == 1) == native and r["seed"] in seeds and r["rho"] != "-"]

    def lnm(g, chan, T0, hh, **kw):
        v = [math.log(float(r["rho"])) for r in sel(g, chan, T0, hh, **kw) if float(r["rho"]) > 0]
        return (mean(v), sd(v), len(v))

    def hist_rho(g, t):
        h = base[g]
        return rho(snap_at(h["snaps"], t), h["nSquad"], h["nOther"])

    L = []
    P = L.append
    J = {"games": {}, "nRuns": len(runs)}
    P("# 历史断面离线对照：分层归因的底表（103_cp_table.py）")
    P("# ρ = 我方号人均领土 ÷ 其他真人人均领土；v = 我方号人均天然地盘 ÷ 其他真人人均天然地盘")
    P("# 各层的数是自然对数差：正数 = 这一层让我方落后（0.10 ≈ 10%，0.69 = 差一倍），负数 = 这一层上我方占便宜")
    P("# 每个通道最多 3 个种子取平均（种子 0 不扰动；1、2 在接管那一拍让引擎随机数多走 1、2 步，C1 的延迟和帧内先后也换一组）；「n=」是用到的种子数")
    P("")
    cnt = {}
    for (g, tag), j in runs.items():
        k = (j["chan"], j["T0"])
        cnt[k] = cnt.get(k, 0) + 1
    P(f"运行数：{len(runs)} 次（不含 11 局基线）。按通道 × 断面：" + "，".join(f"{c}@{t} {n}" for (c, t), n in sorted(cnt.items(), key=lambda x: (x[0][1], x[0][0]))))
    P("")

    # ---------- 表 0：C2 种子 0 对历史的复现
    P("## 表 0：C2（历史实录轨迹）种子 0 对历史的复现")
    P("局\t断面\t轨迹表逐行相同的行数\t第一处我方或别的真人领土与历史不同的记录拍（每 30 拍记一次）\t看到最后一拍时：我方领土 C2 ÷ 历史\t其他真人领土 C2 ÷ 历史\t别的真人指令结果第一次与历史不同的拍\t注入指令落在历史原位置的条数 / 全部落地")
    J["closure"] = {}
    for g in GAMES:
        for T0 in T0S:
            j = runs.get((g, f"C2-t{T0}-s0"))
            h = base.get(g)
            if not j or not h:
                continue
            hs = {s["t"]: s for s in h["snaps"]}
            first = None
            for s in j["snaps"]:
                x = hs.get(s["t"])
                if x and s["t"] >= T0 and (s["LS"], s["LO"]) != (x["LS"], x["LO"]):
                    first = s["t"]
                    break
            last = j["snaps"][-1]
            xl = hs.get(last["t"]) or snap_at(h["snaps"], last["t"])
            a = f"{last['LS'] / xl['LS']:.3f}" if xl and xl["LS"] else ("两边都是 0" if last["LS"] == 0 else f"历史为 0，C2 为 {last['LS']}")
            b = f"{last['LO'] / xl['LO']:.3f}" if xl and xl["LO"] else "-"
            ps = j.get("posStat") or {}
            ff = j["div"]["firstOkDiff"] if j.get("div") else -1
            P(f"{g}\t{T0}\t{j['validate']['both']} / {j['validate']['rows']}\t{'到 ' + str(last['t']) + ' 拍没有不同' if first is None else first}\t{a}\t{b}\t{'没有' if ff < 0 else ff}\t{ps.get('hist', '-')} / {j['chanStat']['landed']}")
            J["closure"][f"{g}@{T0}"] = {"trajBoth": j["validate"]["both"], "trajRows": j["validate"]["rows"], "firstDiff": first, "lastT": last["t"],
                                         "LSratio": last["LS"] / xl["LS"] if xl and xl["LS"] else None, "LOratio": last["LO"] / xl["LO"] if xl and xl["LO"] else None,
                                         "firstOkFlip": ff, "posHist": ps.get("hist"), "landed": j["chanStat"]["landed"]}
    P("")

    # ---------- 表 1：断面 0 的分层
    for T in (630, 1500):
        P(f"## 表 1-{T}：断面 0 → {T} 拍的分层")
        P("局\tv\tρ历史\tρC2\tρC1\tρC0\t出生站位 −ln v\t规则（零延迟下）ln v − ln ρC0\t基础延迟 ln ρC0 − ln ρC1\t按住与成批放行 ln ρC1 − ln ρC2\t没对上 ln ρC2 − ln ρ历史\t合计 −ln ρ历史\t种子数 C0/C1/C2\tC1、C2 的种子标准差")
        keys = ("spawn", "rule", "base", "hold", "resid", "total")
        agg = {k: [] for k in keys}
        for g in GAMES:
            if g not in base:
                continue
            v = vpar(g)
            rh = hist_rho(g, T)
            c2, c1, c0 = lnm(g, "C2", 0, T), lnm(g, "C1", 0, T), lnm(g, "C0", 0, T)
            if rh is None or v is None:
                continue
            lh = math.log(rh)
            l2 = c2[0] if c2[0] is not None else None
            d = {"spawn": -math.log(v), "rule": sub(math.log(v), c0[0]), "base": sub(c0[0], c1[0]), "hold": sub(c1[0], l2), "resid": sub(l2, lh), "total": -lh}
            J["games"].setdefault(g, {})[f"t0_{T}"] = dict(d, v=v, rhoH=rh, rhoC2=math.exp(c2[0]) if c2[0] is not None else None, rhoC1=math.exp(c1[0]) if c1[0] is not None else None,
                                                             rhoC0=math.exp(c0[0]) if c0[0] is not None else None, n=[c0[2], c1[2], c2[2]], sdC1=c1[1], sdC2=c2[1])
            if all(d[k] is not None for k in keys):
                for k in keys:
                    agg[k].append(d[k])
            ex = lambda c: f(math.exp(c[0])) if c[0] is not None else "-"
            P(f"{g}\t{v:.3f}\t{rh:.3f}\t{ex(c2)}\t{ex(c1)}\t{ex(c0)}\t" + "\t".join(f(d[k], sign=True) for k in keys) + f"\t{c0[2]}/{c1[2]}/{c2[2]}\t{f(c1[1], 2)} / {f(c2[1], 2)}")
        n = len(agg["total"])
        if n:
            P(f"{n} 局相加\t\t\t\t\t\t" + "\t".join(f(sum(agg[k]), sign=True) for k in keys))
            P(f"{n} 局中位数\t\t\t\t\t\t" + "\t".join(f(med(agg[k]), sign=True) for k in keys))
            tot = sum(agg["total"])
            if abs(tot) > 1e-9:
                P(f"占合计的比例\t\t\t\t\t\t" + "\t".join(f"{100 * sum(agg[k]) / tot:.0f}%" for k in keys))
            pos = sum(max(0, sum(agg[k])) for k in ("spawn", "rule", "base", "hold"))
            J[f"sum_t0_{T}"] = {k: sum(agg[k]) for k in keys}
            J[f"sum_t0_{T}"]["n"] = n
        P("")

    # ---------- 表 1b：断面 0 → 1500 拍，领土的去向
    P("## 表 1b：断面 0 → 1500 拍时全图陆地的分布（占全图陆地的百分比；种子 0）")
    P("局\t通道\t我方号\t其他真人\t内置 AI\t没人占\t我方号存活 / 开局")
    for g in GAMES:
        h = base.get(g)
        if not h:
            continue
        land = h["land"]
        for ch in ("历史", "C2", "C1", "C0"):
            j = h if ch == "历史" else runs.get((g, f"{ch}-t0-s0"))
            if not j:
                continue
            s = snap_at(j["snaps"], 1500)
            if not s:
                continue
            free = land - s["LS"] - s["LO"] - s["botL"]
            P(f"{g}\t{ch}\t{100 * s['LS'] / land:.1f}\t{100 * s['LO'] / land:.1f}\t{100 * s['botL'] / land:.1f}\t{100 * free / land:.1f}\t{s['aS']} / {h['nSquad']}")
    P("")

    # ---------- 表 2：各断面的窗口分解
    J["win"] = {}
    for T0 in (630, 1500, 4284):
        for hh in (300, 600, 900):
            P(f"## 表 2-{T0}+{hh}：断面 {T0} → {T0 + hh} 拍")
            P("局\tρ(断面)\tΔ历史\tΔC2\tΔC1\tΔC0\t基础延迟 ΔC0 − ΔC1\t按住与成批放行 ΔC1 − ΔC2\t没对上 ΔC2 − Δ历史\t种子数 C0/C1/C2\tC1、C2 的种子标准差\t别的真人指令结果翻转（C1，占条数）")
            acc = {k: [] for k in ("dH", "d2", "d1", "d0", "base", "hold", "resid")}
            for g in GAMES:
                h = base.get(g)
                if not h:
                    continue
                r0 = rho(snap_at(h["snaps"], T0, 1), h["nSquad"], h["nOther"])
                rh = hist_rho(g, T0 + hh)
                if r0 is None or r0 <= 0:
                    continue
                c2, c1, c0 = lnm(g, "C2", T0, hh), lnm(g, "C1", T0, hh), lnm(g, "C0", T0, hh)
                if c1[0] is None and c2[0] is None and c0[0] is None:
                    continue
                l0 = math.log(r0)
                d = {"dH": sub(ln(rh), l0), "d2": sub(c2[0], l0), "d1": sub(c1[0], l0), "d0": sub(c0[0], l0)}
                d["base"] = sub(d["d0"], d["d1"]); d["hold"] = sub(d["d1"], d["d2"]); d["resid"] = sub(d["d2"], d["dH"])
                fl = sel(g, "C1", T0, hh)
                flip = (sum(x["oppOkFlip"] for x in fl) / max(1, sum(x["oppCmds"] for x in fl))) if fl else None
                for k in acc:
                    acc[k].append(d[k])
                J["win"].setdefault(g, {})[f"t{T0}_h{hh}"] = dict(d, rho0=r0, rhoH=rh, n=[c0[2], c1[2], c2[2]], sdC1=c1[1], sdC2=c2[1], flip=flip)
                dh = "历史上已全灭" if rh is not None and rh == 0 else f(d["dH"], sign=True)
                P(f"{g}\t{r0:.3f}\t{dh}\t{f(d['d2'], sign=True)}\t{f(d['d1'], sign=True)}\t{f(d['d0'], sign=True)}\t{f(d['base'], sign=True)}\t{f(d['hold'], sign=True)}\t{f(d['resid'], sign=True)}\t{c0[2]}/{c1[2]}/{c2[2]}\t{f(c1[1], 2)} / {f(c2[1], 2)}\t{f(100 * flip, 1) + '%' if flip is not None else '-'}")
            if any(x is not None for x in acc["d1"]):
                P("中位数\t\t" + "\t".join(f(med(acc[k]), sign=True) for k in ("dH", "d2", "d1", "d0", "base", "hold", "resid")))
                P("相加\t\t" + "\t".join(f(sum(x for x in acc[k] if x is not None), sign=True) + f"（{sum(1 for x in acc[k] if x is not None)} 局）" for k in ("dH", "d2", "d1", "d0", "base", "hold", "resid")))
            P("")

    # ---------- 表 3：版本对照
    P("## 表 3：另一个历史版本（原文）在同一断面、同一通道下：ln ρ(Vb) − ln ρ(Va)")
    P("（A007 历史上用 Va，其余 10 局用 Vb；另一版本和本局版本用同样的种子比）")
    P("局\t断面\t看多少拍\tC1：ln ρ(Vb) − ln ρ(Va)\tC2：ln ρ(Vb) − ln ρ(Va)\t种子数")
    verd = {"C1": [], "C2": []}
    for g in GAMES:
        alt = "vb" if g == "A007" else "va"
        for T0 in (0, 630, 1500):
            for hh in ((630, 1500) if T0 == 0 else (300, 900)):
                cells = []
                ns = []
                for ch in ("C1", "C2"):
                    ra = {r["seed"]: math.log(float(r["rho"])) for r in sel(g, ch, T0, hh, variant=alt, native=False) if float(r["rho"]) > 0}
                    rn = {r["seed"]: math.log(float(r["rho"])) for r in sel(g, ch, T0, hh) if float(r["rho"]) > 0}
                    common = sorted(set(ra) & set(rn))
                    if not common:
                        cells.append("-")
                        ns.append(0)
                        continue
                    dlt = mean([ra[s] - rn[s] for s in common])
                    vbva = dlt if g == "A007" else -dlt
                    cells.append(f(vbva, sign=True))
                    ns.append(len(common))
                    verd[ch].append((g, T0, hh, vbva))
                if any(c != "-" for c in cells):
                    P(f"{g}\t{T0}\t{hh}\t" + "\t".join(cells) + f"\t{ns[0]}/{ns[1]}")
    J["ver"] = {}
    for ch in ("C1", "C2"):
        for T0, hh in ((0, 630), (0, 1500), (630, 900), (1500, 900)):
            xs = [d for g, t, h2, d in verd[ch] if t == T0 and h2 == hh]
            if xs:
                P(f"{ch}，断面 {T0} 看 {hh} 拍：{len(xs)} 局，中位数 {med(xs):+.3f}，最小 {min(xs):+.3f}，最大 {max(xs):+.3f}，Vb 更高的 {sum(1 for x in xs if x > 0)} 局")
                J["ver"][f"{ch}_t{T0}_h{hh}"] = {"n": len(xs), "median": med(xs), "min": min(xs), "max": max(xs), "pos": sum(1 for x in xs if x > 0)}
    P("")

    # ---------- 表 4：延迟取法的敏感性
    P("## 表 4：基础延迟取法的敏感性（种子 0；ln ρ − ln ρ(C1 默认取法)）")
    P("局\t断面\t看多少拍\tC0b − C0（零延迟下改成一拍只受理一条）\tC1 的 d 改成 5~12 均匀\tC1 的 d 改成 10~18 均匀")
    sens = {"c0b": [], "d5": [], "d10": []}
    for g in GAMES:
        for T0 in (0, 630):
            for hh in ((630, 1500) if T0 == 0 else (300, 900)):
                c1 = lnm(g, "C1", T0, hh, seeds=(0,))
                c0 = lnm(g, "C0", T0, hh, seeds=(0,))
                c0b = lnm(g, "C0b", T0, hh, seeds=(0,))
                u = lnm(g, "C1", T0, hh, variant="d5_12", seeds=(0,))
                w = lnm(g, "C1", T0, hh, variant="d10_18", seeds=(0,))
                a, b, c = sub(c0b[0], c0[0]), sub(u[0], c1[0]), sub(w[0], c1[0])
                if a is None and b is None and c is None:
                    continue
                if T0 == 0 and hh == 1500:
                    sens["c0b"].append(a); sens["d5"].append(b); sens["d10"].append(c)
                P(f"{g}\t{T0}\t{hh}\t{f(a, sign=True)}\t{f(b, sign=True)}\t{f(c, sign=True)}")
    for k, name in (("c0b", "C0b − C0"), ("d5", "d 取 5~12"), ("d10", "d 取 10~18")):
        xs = [x for x in sens[k] if x is not None]
        if xs:
            P(f"断面 0 看 1500 拍，{name}：{len(xs)} 局，中位数 {med(xs):+.3f}，最小 {min(xs):+.3f}，最大 {max(xs):+.3f}")
            J.setdefault("sens", {})[k] = {"n": len(xs), "median": med(xs), "min": min(xs), "max": max(xs)}
    P("")

    # ---------- 表 5：席位离开
    P("## 表 5：不执行录像里我方号的离开（A061、A062；种子 0；ln ρ(不离开) − ln ρ(照录像离开)）")
    P("局\t断面\t看多少拍\tC1\tC2")
    for g in ("A061", "A062"):
        for T0 in (0, 630, 1500):
            for hh in ((630, 1500) if T0 == 0 else (300, 900)):
                cells = []
                for ch in ("C1", "C2"):
                    a = lnm(g, ch, T0, hh, variant="nl", seeds=(0,))
                    n = lnm(g, ch, T0, hh, seeds=(0,))
                    cells.append(f(sub(a[0], n[0]), sign=True))
                if any(c != "-" for c in cells):
                    P(f"{g}\t{T0}\t{hh}\t" + "\t".join(cells))
    P("")

    # ---------- 表 6：指令去向
    P("## 表 6：断面 0 → 1500 拍我方指令的去向（种子 0）")
    P("局\t通道\t发出\t落地\t生效\t按历史轨迹没落地\t超过每 3 回合 9 条被丢\t同一拍第二条被拒\t在途拍数 P50 / P90\t1500 拍我方领土\t我方余额\t我方在外的进攻兵")
    for g in GAMES:
        for ch in ("C0", "C1", "C2"):
            r = sel(g, ch, 0, 1500, seeds=(0,))
            if not r:
                continue
            r = r[0]
            P(f"{g}\t{ch}\t{r['issued']}\t{r['landed']}\t{r['landedOk']}\t{r['mapDrop']}\t{r['capDrop']}\t{r['second']}\t{r['delayP50']} / {r['delayP90']}\t{r['LS']}\t{r['BS']}\t{r['outS']}")
        h = base.get(g)
        if h:
            s = snap_at(h["snaps"], 1500)
            P(f"{g}\t历史\t\t\t\t\t\t\t\t{s['LS']}\t{s['BS']}\t{s['outS']}")
    P("")

    # ---------- 表 7：席位层面
    P("## 表 7：席位层面（我方每个号）：1500 拍领土的对数对天然地盘的对数回归（局内去均值；断面 0，种子 0）")
    P("通道\t局数\t席位数\t斜率\t相关系数")
    for ch in ("历史", "C2", "C1", "C0"):
        xs, ys, ng = [], [], 0
        for g in GAMES:
            v = vor[g]
            h = base.get(g)
            if not h or not v:
                continue
            j = h if ch == "历史" else runs.get((g, f"{ch}-t0-s0"))
            if not j:
                continue
            s = snap_at(j["snaps"], 1500)
            if not s:
                continue
            px, py = [], []
            for i, sq in enumerate(h["squad"]):
                vv = (v["squad"].get(sq["bot"]) or {}).get("vor")
                tt = s["seat"][i]
                if vv and tt and tt > 0:
                    px.append(math.log(vv)); py.append(math.log(tt))
            if len(px) >= 3:
                ng += 1
                mx, my = mean(px), mean(py)
                xs += [x - mx for x in px]; ys += [y - my for y in py]
        if len(xs) >= 10:
            sxx = sum(x * x for x in xs); sxy = sum(x * y for x, y in zip(xs, ys)); syy = sum(y * y for y in ys)
            P(f"{ch}\t{ng}\t{len(xs)}\t{sxy / sxx:.2f}\t{sxy / math.sqrt(sxx * syy):.2f}")
            J.setdefault("seatElasticity", {})[ch] = {"games": ng, "n": len(xs), "slope": sxy / sxx, "r": sxy / math.sqrt(sxx * syy)}
    P("")

    # ---------- 表 8：只扰动随机数的历史重放（噪声底）
    nz = []
    for g in GAMES:
        for T0 in T0S:
            for hh in ((1500,) if T0 == 0 else (900,)):
                rh = hist_rho(g, T0 + hh)
                xs = [math.log(float(r["rho"])) for r in sel(g, "H", T0, hh, seeds=(1, 2)) if float(r["rho"]) > 0]
                if xs and rh:
                    nz.append((g, T0, hh, max(abs(x - math.log(rh)) for x in xs), len(xs)))
    if nz:
        P("## 表 8：全按录像、只在断面那一拍扰动引擎随机数：ln ρ 偏离历史的最大值")
        P("局\t断面\t看多少拍\t|ln ρ(扰动) − ln ρ(历史)| 最大\t种子数")
        for g, T0, hh, d, n in nz:
            P(f"{g}\t{T0}\t{hh}\t{d:.3f}\t{n}")
        P("")

    open(os.path.join(CROSS, "checkpoint_attribution.txt"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    json.dump(J, open(os.path.join(CROSS, "checkpoint_attribution.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n".join(L))


if __name__ == "__main__":
    main()
