#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""103_cp_table.py — R07：把 100_checkpoint.mjs 的各次运行汇总成表（任务卡 0002 的分层归因）。

读：out/_cache/cp/<局>/*.json（各次运行）、out/<局>/voronoi.json（46_voronoi.mjs：出生点的天然地盘）
写：out/_cross/cp_runs.tsv（每次运行 × 每个观察拍一行；进 git，报告里的数都从这里出）
    out/_cross/checkpoint_attribution.txt / .json（报告用的表）

量的定义：
  ρ(t) = 我方号人均领土 ÷ 其他真人人均领土（人数都按开局第 1 拍有地的席位数算，中途离开或死亡的席位仍算在分母里）
  v    = 我方号人均天然地盘 ÷ 其他真人人均天然地盘（天然地盘 = 全图陆地按直线距离分给最近的真人出生点）
  别的真人在离线对照里只会照录像出招。局面一旦和历史走偏，他们那些针对原局面下的指令就不再合适，领土会比历史上少
  （11 局里无一例外，见表 1b）。所以通道之间必须在「同样走偏」的局面里比：
     C2p = C2 的扰动种子（1、2：接管那一拍让引擎随机数多走 1、2 步）；C2 种子 0 不走偏，只用来验证能否复现历史。
  从断面 0 出发、看到 T 拍（数都是自然对数差，正数 = 让我方落后）：
     −ln ρ历史(T) = [−ln v_γ]             出生站位：天然地盘比别的真人少（v_γ 见 106_spawn_par.py；另两种基准 v_β、v 只做敏感性）
                  + [ln ρC0 − ln ρC1]     基础延迟：正常线上通道（每条指令晚 1~2 个回合）相对零延迟
                  + [ln ρC1 − ln ρC2p]    按住与成批放行：历史实录轨迹相对正常通道
                  + 规则（余项）          = 合计 − 以上三项 = [ln v_γ − ln ρC0] + [ln ρC2p − ln ρ历史]
                                           前一个方括号：零延迟下原策略相对「同样出生点上的一般真人」；后一个：走偏带来的虚高，要扣回去
  从断面 T0>0 出发、看 h 拍：Δ通道 = ln ρ通道(T0+h) − ln ρ历史(T0)
     基础延迟 = ΔC0 − ΔC1；按住与成批放行 = ΔC1 − ΔC2p；走偏带来的虚高 = ΔC2p − Δ历史
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
# 4284 拍正好是赠兵规则换档的一拍。A079、A082 各有赠兵在这一拍落地、而影子在发令那一拍判定额度不够（离线通道不发），
# 从 4284 拍接管时 C2 与历史有差别：A079 窗末我方领土差 1% 左右，A082 差六成以上。两局改为从 4285 拍接管
# （4284 拍落地的指令照录像执行）后都逐拍复现（表 0b）。
# A082 这一局 4284 断面的各条对照都用 4285 拍接管的运行（--t0 4285 --h 899，窗末仍是 5184 拍）；
# A079 的差别与 A033 同一量级，保持从 4284 拍接管（表 0 里如实列出差别）。
SHIFT = {"A082": 4285}
# 不计入窗口汇总（平均、中位数、三层）的局：A082 的 4284 断面这一窗没有指令被按住，但结果对极小的差别都很敏感
# （少一条赠兵、换一组延迟，ln ρ 的变化就差 0.5 以上，见表 0c 和报告 §6.2），C1 与 C2 之差不能当作通道的作用。
EXCL_WIN = {4284: ("A082",)}
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
    old4284 = {}   # SHIFT 里的局原来从 4284 拍接管的结果：只在 §3 的说明里用
    alt4285 = {}   # 不在 SHIFT 里的局从 4285 拍接管的运行：只用来验证和取窗末的历史值，不进各表
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
                continue
            if "-t4285-" in tag and g not in SHIFT:
                alt4285[(g, tag)] = j
                continue
            if g in SHIFT and not tag.startswith("H-"):
                if "-t4284-" in tag:
                    old4284[(g, tag)] = j
                    continue
                if f"-t{SHIFT[g]}-" in tag:
                    # 这一局的 4284 断面实际从 SHIFT[g] 拍接管：断面时的局面相同，名字和断面拍都按 4284 记
                    tag = tag.replace(f"-t{SHIFT[g]}-", "-t4284-")
                    j["T0real"], j["T0"] = j["T0"], 4284
            runs[(g, tag)] = j
    # 4284 断面的窗末（5184 拍）不是 30 的倍数，H.json 没有这一拍的记录（最近的是 5190 拍）。
    # 有不扰动的历史重放（H-t4284-s0：全按录像、不动随机数、跑到 5184 拍）时，先核对它与 H.json 在共同的记录拍上逐个相同，
    # 再把它最后一拍的记录补进历史的记录里；这样窗末的历史值与各通道取的是同一拍。
    hist_end_exact, hist_end_bad = [], []
    for g in GAMES:
        j = runs.pop((g, "H-t4284-s0"), None)
        h = base.get(g)
        if not j or not h:
            continue
        hs = {s["t"]: s for s in h["snaps"]}
        key = lambda s: (s["LS"], s["LO"], s["BS"], s["BO"], s["aS"], s["aO"])
        if any(s["t"] in hs and key(s) != key(hs[s["t"]]) for s in j["snaps"]):
            hist_end_bad.append(g)
            continue
        last = j["snaps"][-1]
        if last["t"] not in hs:
            h["snaps"].append(last)
            h["snaps"].sort(key=lambda s: s["t"])
        hist_end_exact.append(g)
    # 还没有这条历史重放的局：如果不扰动的 C2（种子 0）从接管到最后一个共同记录拍，我方和其他真人的领土、余额、在场人数
    # 都与 H.json 逐个相同，就用这条 C2 在 5184 拍的记录当作历史在 5184 拍的值（两条轨迹到 5160 拍为止完全相同）；
    # 否则窗末的历史值只能取 H.json 里最近的记录拍（5190 拍，晚 6 拍）。
    hist_end_c2, hist_end_late = [], []
    for g in GAMES:
        h = base.get(g)
        if not h or g in hist_end_exact:
            continue
        s0 = snap_at(h["snaps"], 4284, 1)
        if not s0 or s0["aS"] == 0:
            continue
        hs = {s["t"]: s for s in h["snaps"]}
        key = lambda s: (s["LS"], s["LO"], s["BS"], s["BO"], s["aS"], s["aO"])
        src = None
        # 候选：这一局 4284 断面不扰动的 C2；从 4285 拍接管的不扰动的 C2（A079 的验证运行）
        for j in (runs.get((g, "C2-t4284-s0")), alt4285.get((g, "C2-t4285-s0")), jload(os.path.join(CP, g, "mt-bd4285.json"))):
            if j and j["chan"] == "C2" and j["seed"] == 0 and j["snaps"][-1]["t"] == 5184 and 5184 not in hs and \
                    all(key(x) == key(hs[x["t"]]) for x in j["snaps"] if x["t"] in hs) and \
                    sum(1 for x in j["snaps"] if x["t"] in hs and x["t"] >= 4284) >= 29:
                src = j
                break
        if src:
            h["snaps"].append(dict(src["snaps"][-1], fromC2=True))
            h["snaps"].sort(key=lambda s: s["t"])
            hist_end_c2.append(g)
        else:
            hist_end_late.append(g)
    vor = {g: jload(os.path.join(OUT, g, "voronoi.json")) for g in GAMES}
    spar = jload(os.path.join(CROSS, "spawn_par.json")) or {"games": {}, "beta": {}}

    def vbeta(g, T):
        return (spar["games"].get(g) or {}).get(f"vb{T}")

    def vgam(g, T):
        return (spar["games"].get(g) or {}).get(f"vg{T}")

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
    J = {"games": {}, "nRuns": len(runs), "histEnd5184": {"exact": hist_end_exact, "mismatch": hist_end_bad, "fromC2": hist_end_c2, "late": hist_end_late}}
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
    all_exact_4284 = all(g in hist_end_exact for g in GAMES if g not in hist_end_bad and (snap_at(base[g]["snaps"], 4284, 1) or {}).get("aS"))
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
            # 比到最后一个两边都有记录的拍。4284 断面的窗末 5184 拍不在历史基线的记录拍里：只要还有一局没有
            # 不扰动的历史重放（H-t4284-s0），这个断面各局就都比到 5160 拍，免得各局比的不是同一拍
            hs_c = hs if T0 != 4284 or all_exact_4284 else {t: x for t, x in hs.items() if t <= 5160}
            last = next(s for s in reversed(j["snaps"]) if s["t"] in hs_c)
            xl = hs_c[last["t"]]
            a = f"{last['LS'] / xl['LS']:.3f}" if xl and xl["LS"] else ("两边都是 0" if last["LS"] == 0 else f"历史为 0，C2 为 {last['LS']}")
            b = f"{last['LO'] / xl['LO']:.3f}" if xl and xl["LO"] else "-"
            ps = j.get("posStat") or {}
            ff = j["div"]["firstOkDiff"] if j.get("div") else -1
            P(f"{g}\t{T0}\t{j['validate']['both']} / {j['validate']['rows']}\t{'到 ' + str(last['t']) + ' 拍没有不同' if first is None else first}\t{a}\t{b}\t{'没有' if ff < 0 else ff}\t{ps.get('hist', '-')} / {j['chanStat']['landed']}")
            J["closure"][f"{g}@{T0}"] = {"trajBoth": j["validate"]["both"], "trajRows": j["validate"]["rows"], "firstDiff": first, "lastT": last["t"],
                                         "LSratio": last["LS"] / xl["LS"] if xl and xl["LS"] else None, "LOratio": last["LO"] / xl["LO"] if xl and xl["LO"] else None,
                                         "firstOkFlip": ff, "posHist": ps.get("hist"), "landed": j["chanStat"]["landed"]}
    P("")

    # ---------- 表 0b：4284 断面的接管推后 1 拍（4284 拍落地的录像指令照常执行）时，C2 种子 0 对历史的复现
    #   用来验证：A079、A082 在 4284 断面不能复现，是因为有赠兵正好在接管那一拍落地（§3）
    P("## 表 0b：接管推后 1 拍（4285 拍）时 C2 种子 0 对历史的复现")
    P("局\t第一处余额或领土与历史不同的记录拍\t第一处领土不同的记录拍\t看到最后一拍时：我方领土 C2 ÷ 历史\t其他真人领土 C2 ÷ 历史")
    J["closureBd"] = {}
    for g in GAMES:
        j = jload(os.path.join(CP, g, "mt-bd4285.json"))
        h = base.get(g)
        if not j or not h:
            continue
        hs = {s["t"]: s for s in h["snaps"]}
        first = firstB = None
        for s in j["snaps"]:
            x = hs.get(s["t"])
            if not x or s["t"] < j["T0"]:
                continue
            if first is None and (s["LS"], s["LO"]) != (x["LS"], x["LO"]):
                first = s["t"]
            if firstB is None and (s["LS"], s["LO"], s["BS"], s["BO"]) != (x["LS"], x["LO"], x["BS"], x["BO"]):
                firstB = s["t"]
        last = next(x for x in reversed(j["snaps"]) if x["t"] in hs)
        xl = hs[last["t"]]
        J["closureBd"][g] = {"T0": j["T0"], "firstDiff": first, "firstDiffBal": firstB, "lastT": last["t"],
                             "LSratio": last["LS"] / xl["LS"] if xl and xl["LS"] else None, "LOratio": last["LO"] / xl["LO"] if xl and xl["LO"] else None}
        c = J["closureBd"][g]
        P(f"{g}\t{'没有' if firstB is None else firstB}\t{'没有' if first is None else first}\t{'-' if c['LSratio'] is None else format(c['LSratio'], '.3f')}\t{'-' if c['LOratio'] is None else format(c['LOratio'], '.3f')}")
    # 余额第一处不同的记录拍（4284 断面）
    def first_bal(j, h):
        hs = {s["t"]: s for s in h["snaps"]}
        return next((s["t"] for s in j["snaps"] if s["t"] >= 4284 and hs.get(s["t"]) and
                     (s["LS"], s["LO"], s["BS"], s["BO"]) != (hs[s["t"]]["LS"], hs[s["t"]]["LO"], hs[s["t"]]["BS"], hs[s["t"]]["BO"])), None)
    for g in GAMES:
        j = runs.get((g, "C2-t4284-s0"))
        h = base.get(g)
        c = J["closure"].get(f"{g}@4284")
        if not j or not h or not c:
            continue
        c["firstDiffBal"] = first_bal(j, h)
        if g in SHIFT:
            c["T0real"] = j.get("T0real")
    # SHIFT 里的局：原来从 4284 拍接管的结果（只用来说明为什么改从 4285 拍接管）
    P("## 表 0c：改从 4285 拍接管的局，原来从 4284 拍接管时的结果")
    P("局\tC2 种子 0：第一处余额不同的记录拍\t第一处领土不同的记录拍\t5184 拍我方领土 C2 ÷ 历史\t其他真人领土 C2 ÷ 历史\t原来各条对照这一窗 ln ρ 的变化")
    J["shift4284"] = {}
    for g, T1 in SHIFT.items():
        h = base.get(g)
        if not h:
            continue
        nS, nO = h["nSquad"], h["nOther"]
        r0 = ln(rho(snap_at(h["snaps"], 4284, 1), nS, nO))
        old = {}
        for (gg, tag), j in sorted(old4284.items()):
            if gg != g:
                continue
            r1 = ln(rho(j["snaps"][-1], nS, nO))
            old[tag] = {"d": sub(r1, r0), "LS": j["snaps"][-1]["LS"], "aS": j["snaps"][-1]["aS"]}
        ent = {"T0real": T1, "old": old}
        j = old4284.get((g, "C2-t4284-s0"))
        if j:
            hs = {s["t"]: s for s in h["snaps"]}
            first = next((s["t"] for s in j["snaps"] if s["t"] >= 4284 and hs.get(s["t"]) and (s["LS"], s["LO"]) != (hs[s["t"]]["LS"], hs[s["t"]]["LO"])), None)
            hs_c = hs if all_exact_4284 else {t: x for t, x in hs.items() if t <= 5160}
            last = next(s for s in reversed(j["snaps"]) if s["t"] in hs_c)
            xl = hs_c[last["t"]]
            ent["closure"] = {"lastT": last["t"], "firstDiff": first, "firstDiffBal": first_bal(j, h),
                              "LSratio": last["LS"] / xl["LS"] if xl and xl["LS"] else None, "LOratio": last["LO"] / xl["LO"] if xl and xl["LO"] else None}
        J["shift4284"][g] = ent
        c = ent.get("closure") or {}
        P(f"{g}\t{c.get('firstDiffBal', '-')}\t{c.get('firstDiff', '-')}\t{f(c.get('LSratio'))}\t{f(c.get('LOratio'))}\t" + "；".join(f"{k} {f(v['d'], 3, True)}" for k, v in old.items()))
    P("")

    # ---------- 表 0d：不计入窗口汇总的局（A082 的 4284 断面）：手头每一条离线轨迹的窗末结果
    P("## 表 0d：不计入窗口汇总的局：各条离线轨迹在窗末（5184 拍）的结果")
    P("局\t接管拍\t通道\t种子\t变体\tln ρ 的变化\t我方领土\t我方在场号\t每个记录拍的领土是否都与历史相同")
    J["armsWin"] = {}
    for T0x, gs_ in EXCL_WIN.items():
        for g in gs_:
            h = base.get(g)
            if not h:
                continue
            nS, nO = h["nSquad"], h["nOther"]
            hs = {s["t"]: s for s in h["snaps"]}
            r0 = ln(rho(snap_at(h["snaps"], T0x, 1), nS, nO))
            lst = []
            for src in (runs, old4284):
                for (gg, tag), j in sorted(src.items()):
                    if gg != g or j["T0"] != T0x or j["snaps"][-1]["t"] != T0x + 900:
                        continue
                    sfx = "-s" + str(j["seed"])
                    variant = tag.split(sfx, 1)[1].lstrip("-") if sfx in tag else ""
                    e = j["snaps"][-1]
                    same = all((x["LS"], x["LO"]) == (hs[x["t"]]["LS"], hs[x["t"]]["LO"]) for x in j["snaps"] if x["t"] in hs and x["t"] <= 5160)
                    lst.append({"take": j.get("T0real", T0x), "chan": j["chan"], "seed": j["seed"], "variant": variant,
                                "d": sub(ln(rho(e, nS, nO)), r0), "LS": e["LS"], "aS": e["aS"], "sameAsHist": same})
            lst.sort(key=lambda x: (-x["take"], {"H": 0, "C2": 1, "C1": 2, "C0": 3}.get(x["chan"], 9), x["variant"], x["seed"]))
            eh = snap_at(h["snaps"], T0x + 900)
            J["armsWin"][f"{g}@{T0x}"] = {"hist": {"d": sub(ln(rho(eh, nS, nO)), r0), "LS": eh["LS"], "aS": eh["aS"], "t": eh["t"]}, "arms": lst}
            for x in lst:
                P(f"{g}\t{x['take']}\t{x['chan']}\t{x['seed']}\t{x['variant'] or '-'}\t{f(x['d'], 3, True)}\t{x['LS']}\t{x['aS']}\t{'相同' if x['sameAsHist'] else '不同'}")
    P("")

    # ---------- 表 0e：扰动种子对 C2 的作用：C2 种子 1 与种子 0（不扰动）相比
    P("## 表 0e：只在接管那一拍扰动引擎随机数：C2 种子 1 与种子 0 相比")
    P("局\t断面\t每个记录拍的领土和余额是否都相同\t窗末 ln ρ(种子 1) − ln ρ(种子 0)")
    J["pert"] = []
    for T0 in T0S:
        for g in GAMES:
            j0, j1 = runs.get((g, f"C2-t{T0}-s0")), runs.get((g, f"C2-t{T0}-s1"))
            h = base.get(g)
            if not j0 or not j1 or not h:
                continue
            a = {x["t"]: x for x in j0["snaps"]}
            common = [x for x in j1["snaps"] if x["t"] in a and x["t"] >= T0]
            same = all((x["LS"], x["LO"], x["BS"], x["BO"]) == (a[x["t"]]["LS"], a[x["t"]]["LO"], a[x["t"]]["BS"], a[x["t"]]["BO"]) for x in common)
            d = sub(ln(rho(j1["snaps"][-1], h["nSquad"], h["nOther"])), ln(rho(j0["snaps"][-1], h["nSquad"], h["nOther"])))
            J["pert"].append({"g": g, "T0": T0, "same": same, "d": d})
            P(f"{g}\t{T0}\t{'相同' if same else '不同'}\t{f(d, 3, True)}")
    P("")

    # ---------- 表 0g：保持从 4284 拍接管的局里，另有从 4285 拍接管的运行的（A079）：两种接管拍下 C1 与不扰动的 C2 之差
    P("## 表 0g：保持从 4284 拍接管的局，改从 4285 拍接管时的结果（验证用）")
    P("局\t接管拍\tΔC2 种子 0\tΔC1 种子 0\tΔC1 − ΔC2")
    J["alt4285"] = {}
    for g in GAMES:
        h = base.get(g)
        a2, a1 = alt4285.get((g, "C2-t4285-s0")), alt4285.get((g, "C1-t4285-s0"))
        b2, b1 = runs.get((g, "C2-t4284-s0")), runs.get((g, "C1-t4284-s0"))
        if not h or not (a2 and a1 and b2 and b1):
            continue
        nS, nO = h["nSquad"], h["nOther"]
        r0 = ln(rho(snap_at(h["snaps"], 4284, 1), nS, nO))
        dd = {k: sub(ln(rho(j["snaps"][-1], nS, nO)), r0) for k, j in (("c2_4285", a2), ("c1_4285", a1), ("c2_4284", b2), ("c1_4284", b1))}
        dd["gap4285"], dd["gap4284"] = sub(dd["c1_4285"], dd["c2_4285"]), sub(dd["c1_4284"], dd["c2_4284"])
        J["alt4285"][g] = dd
        P(f"{g}\t4285\t{f(dd['c2_4285'], 3, True)}\t{f(dd['c1_4285'], 3, True)}\t{f(dd['gap4285'], 3, True)}")
        P(f"{g}\t4284\t{f(dd['c2_4284'], 3, True)}\t{f(dd['c1_4284'], 3, True)}\t{f(dd['gap4284'], 3, True)}")
    P("")

    # ---------- 表 0h：C2 的帧内先后改成随机（--pos rand，名字后缀 -rp）与放回历史原位置相比
    P("## 表 0h：C2 的帧内先后改成随机，与放回历史原位置的同一条相比")
    P("局\t断面（实际接管拍）\t种子\t排在这一帧录像指令之前 / 之后的条数\t每个记录拍的领土和余额是否都相同")
    J["rpCheck"] = []
    for (g, tag), j in sorted(runs.items()):
        if not tag.endswith("-rp"):
            continue
        k = runs.get((g, tag[:-3]))
        if not k:
            continue
        a = {x["t"]: x for x in k["snaps"]}
        same = all((x["LS"], x["LO"], x["BS"], x["BO"]) == (a[x["t"]]["LS"], a[x["t"]]["LO"], a[x["t"]]["BS"], a[x["t"]]["BO"]) for x in j["snaps"] if x["t"] in a)
        ps = j.get("posStat") or {}
        J["rpCheck"].append({"g": g, "T0": j["T0"], "T0real": j.get("T0real", j["T0"]), "seed": j["seed"], "before": ps.get("before"), "after": ps.get("after"), "same": same})
        P(f"{g}\t{j['T0']}（{j.get('T0real', j['T0'])}）\t{j['seed']}\t{ps.get('before')} / {ps.get('after')}\t{'相同' if same else '不同'}")
    P("")

    # ---------- 表 0f：各断面时内置 AI 占全图陆地的比例（扰动种子只改变内置 AI 的随机行为，它的作用随这个比例变小）
    P("## 表 0f：历史上各断面时内置 AI 占全图陆地的比例")
    P("断面\t局数\t中位数\t最小\t最大")
    J["botShare"] = {}
    for T0 in (630, 1500, 2400, 4284):
        xs = []
        for g in GAMES:
            h = base.get(g)
            sx = snap_at(h["snaps"], T0, 1) if h else None
            if sx:
                xs.append(sx["botL"] / h["land"])
        if xs:
            J["botShare"][str(T0)] = {"n": len(xs), "median": med(xs), "min": min(xs), "max": max(xs)}
            P(f"{T0}\t{len(xs)}\t{100 * med(xs):.1f}%\t{100 * min(xs):.1f}%\t{100 * max(xs):.1f}%")
    P("")

    # ---------- 表 1：断面 0 的分层
    PERT = (1, 2)
    for T in (630, 1500):
        gm = (spar.get("gamma", {}).get(str(T)) or {}).get("g")
        bt = (spar["beta"].get(str(T)) or {}).get("b")
        P(f"## 表 1-{T}：断面 0 → {T} 拍的分层（出生站位的基准用 v_γ，γ = {f(gm, 2)}：同一批对局里其他真人到 {T} 拍「期望领土 ∝ 天然地盘^γ」，见 spawn_par.txt）")
        P("局\tv\tv_γ\tρ历史\tρC2 种子 0\tρC2p\tρC1\tρC0\t出生站位 −ln v_γ\t规则（余项）\t基础延迟 ln ρC0 − ln ρC1\t按住与成批放行 ln ρC1 − ln ρC2p\t合计 −ln ρ历史"
          "\t其中走偏带来的虚高 ln ρC2p − ln ρ历史（已并在规则里扣回）\t零延迟下相对基准：ln v_γ − ln ρC0\t正常延迟下相对基准：ln v_γ − ln ρC1\t种子数 C0/C1/C2p\t种子标准差 C1 / C2p"
          f"\t若基准改用 v_β（β = {f(bt, 2)}）：出生站位 / 规则\t若基准改用 v：出生站位 / 规则")
        keys = ("spawn", "rule", "base", "hold", "total")
        agg = {k: [] for k in keys + ("bias", "raw0", "raw1", "spawnB", "ruleB", "spawnV", "ruleV")}
        for g in GAMES:
            if g not in base:
                continue
            v = vpar(g)
            vg = vgam(g, T) or v
            vb = vbeta(g, T) or v
            rh = hist_rho(g, T)
            c2s0 = lnm(g, "C2", 0, T, seeds=(0,))
            c2p, c1, c0 = lnm(g, "C2", 0, T, seeds=PERT), lnm(g, "C1", 0, T), lnm(g, "C0", 0, T)
            if rh is None or v is None:
                continue
            lh = math.log(rh)
            d = {"spawn": -math.log(vg), "base": sub(c0[0], c1[0]), "hold": sub(c1[0], c2p[0]), "total": -lh}
            ok = d["base"] is not None and d["hold"] is not None
            d["rule"] = d["total"] - d["spawn"] - d["base"] - d["hold"] if ok else None
            bias = sub(c2p[0], lh)
            raw0 = sub(math.log(vg), c0[0])
            raw1 = sub(math.log(vg), c1[0])
            spawnB, spawnV = -math.log(vb), -math.log(v)
            ruleB = d["total"] - spawnB - d["base"] - d["hold"] if ok else None
            ruleV = d["total"] - spawnV - d["base"] - d["hold"] if ok else None
            ex = lambda c: f(math.exp(c[0])) if c[0] is not None else "-"
            J["games"].setdefault(g, {})[f"t0_{T}"] = dict(d, v=v, vg=vg, vb=vb, rhoH=rh, rhoC2s0=math.exp(c2s0[0]) if c2s0[0] is not None else None,
                                                             rhoC2p=math.exp(c2p[0]) if c2p[0] is not None else None, rhoC1=math.exp(c1[0]) if c1[0] is not None else None,
                                                             rhoC0=math.exp(c0[0]) if c0[0] is not None else None, n=[c0[2], c1[2], c2p[2]], sdC1=c1[1], sdC2p=c2p[1],
                                                             bias=bias, raw0=raw0, raw1=raw1, spawnB=spawnB, ruleB=ruleB, spawnV=spawnV, ruleV=ruleV)
            if ok:
                for k in keys:
                    agg[k].append(d[k])
                for k, x in (("bias", bias), ("raw0", raw0), ("raw1", raw1), ("spawnB", spawnB), ("ruleB", ruleB), ("spawnV", spawnV), ("ruleV", ruleV)):
                    agg[k].append(x)
            P(f"{g}\t{v:.3f}\t{vg:.3f}\t{rh:.3f}\t{ex(c2s0)}\t{ex(c2p)}\t{ex(c1)}\t{ex(c0)}\t" + "\t".join(f(d[k], sign=True) for k in keys)
              + f"\t{f(bias, sign=True)}\t{f(raw0, sign=True)}\t{f(raw1, sign=True)}\t{c0[2]}/{c1[2]}/{c2p[2]}\t{f(c1[1], 2)} / {f(c2p[1], 2)}"
              + f"\t{f(spawnB, sign=True)} / {f(ruleB, sign=True)}\t{f(spawnV, sign=True)} / {f(ruleV, sign=True)}")
        n = len(agg["total"])
        if n:
            tail = lambda fn: (f"\t{f(fn(agg['bias']), sign=True)}\t{f(fn(agg['raw0']), sign=True)}\t{f(fn(agg['raw1']), sign=True)}\t\t"
                               f"\t{f(fn(agg['spawnB']), sign=True)} / {f(fn(agg['ruleB']), sign=True)}\t{f(fn(agg['spawnV']), sign=True)} / {f(fn(agg['ruleV']), sign=True)}")
            P(f"{n} 局相加\t\t\t\t\t\t\t\t" + "\t".join(f(sum(agg[k]), sign=True) for k in keys) + tail(sum))
            P(f"{n} 局平均\t\t\t\t\t\t\t\t" + "\t".join(f(mean(agg[k]), sign=True) for k in keys) + tail(mean))
            P(f"{n} 局中位数\t\t\t\t\t\t\t\t" + "\t".join(f(med(agg[k]), sign=True) for k in keys) + tail(med))
            tot = sum(agg["total"])
            if abs(tot) > 1e-9:
                pc = lambda k: f"{100 * sum(agg[k]) / tot:.0f}%"
                P(f"占合计的比例\t\t\t\t\t\t\t\t" + "\t".join(pc(k) for k in keys) + f"\t{pc('bias')}\t\t\t\t\t{pc('spawnB')} / {pc('ruleB')}\t{pc('spawnV')} / {pc('ruleV')}")
            J[f"sum_t0_{T}"] = {k: sum(agg[k]) for k in agg}
            J[f"sum_t0_{T}"].update(n=n, gamma=gm, beta=bt, median={k: med(agg[k]) for k in agg})
        P("")

    # ---------- 表 1s：占比（各局相加后的比例）和它在「换一批局」下的波动（对 11 局有放回重抽 4000 次，取 5% / 95% 分位）
    def boot_shares(rowsd, keys):
        import random
        rnd_ = random.Random(20261112)
        n = len(rowsd)
        tot = sum(r["total"] for r in rowsd)
        point = {k: sum(r[k] for r in rowsd) / tot for k in keys}
        draws = {k: [] for k in keys}
        for _ in range(4000):
            smp = [rowsd[rnd_.randrange(n)] for _ in range(n)]
            t = sum(r["total"] for r in smp)
            if abs(t) < 1e-9:
                continue
            for k in keys:
                draws[k].append(sum(r[k] for r in smp) / t)
        out = {}
        for k in keys:
            v = sorted(draws[k])
            out[k] = {"share": point[k], "lo": v[int(0.05 * len(v))], "hi": v[int(0.95 * len(v)) - 1]}
        return out

    SK = ("spawn", "rule", "base", "hold", "rulebase")
    SKN = {"spawn": "出生站位", "rule": "规则（余项）", "base": "基础延迟", "hold": "按住与成批放行", "rulebase": "规则 + 基础延迟"}
    lv = {}
    for T in (630, 1500):
        lv[T] = {}
        for g in GAMES:
            d = J["games"].get(g, {}).get(f"t0_{T}")
            if d and all(d.get(k) is not None for k in ("spawn", "rule", "base", "hold", "total")):
                lv[T][g] = dict({k: d[k] for k in ("spawn", "rule", "base", "hold", "total")}, rulebase=d["rule"] + d["base"])
    P("## 表 1s：各项占失分的比例（各局相加后的比例；括号里是对这些局有放回重抽 4000 次的 5% ~ 95% 分位，反映「换一批局」时比例会怎么变）")
    P("口径\t局数\t合计（各局相加）\t" + "\t".join(SKN[k] for k in SK))
    J["shares"] = {}
    if lv[1500]:
        rowsd = list(lv[1500].values())
        bs = boot_shares(rowsd, SK)
        J["shares"]["level1500"] = dict(bs, n=len(rowsd), total=sum(r["total"] for r in rowsd))
        P(f"到 1500 拍的落后（−ln ρ历史）\t{len(rowsd)}\t{sum(r['total'] for r in rowsd):+.3f}\t" + "\t".join(f"{100 * bs[k]['share']:.0f}%（{100 * bs[k]['lo']:.0f}% ~ {100 * bs[k]['hi']:.0f}%）" for k in SK))
    common = [g for g in GAMES if g in lv[630] and g in lv[1500]]
    if common:
        rowsd = [{k: lv[1500][g][k] - lv[630][g][k] for k in SK + ("total",)} for g in common]
        bs = boot_shares(rowsd, SK)
        J["shares"]["change630_1500"] = dict(bs, n=len(rowsd), total=sum(r["total"] for r in rowsd), mean={k: sum(r[k] for r in rowsd) / len(rowsd) for k in SK + ("total",)})
        P(f"630 → 1500 拍之间新增的落后\t{len(rowsd)}\t{sum(r['total'] for r in rowsd):+.3f}\t" + "\t".join(f"{100 * bs[k]['share']:.0f}%（{100 * bs[k]['lo']:.0f}% ~ {100 * bs[k]['hi']:.0f}%）" for k in SK))
        P("630 → 1500 拍之间各项的变化（各局平均）\t" + f"{len(rowsd)}\t{sum(r['total'] for r in rowsd) / len(rowsd):+.3f}\t" + "\t".join(f"{sum(r[k] for r in rowsd) / len(rowsd):+.3f}" for k in SK))
        J["change630_1500_games"] = {g: r for g, r in zip(common, rowsd)}
    P("")

    # ---------- 表 1p：断面 0 出发，各观察拍的四项（各局平均）
    P("## 表 1p：断面 0 出发，到各观察拍的四项（各局平均；只用四项都算得出的局）")
    P("观察拍\tγ\t局数\tρ历史（几何平均）\t出生站位\t规则（余项）\t基础延迟\t按住与成批放行\t合计\t走偏带来的虚高\t正常延迟下相对基准 ln v_γ − ln ρC1")
    J["path"] = {}
    for T in (300, 630, 900, 1200, 1500):
        gm = (spar.get("gamma", {}).get(str(T)) or {}).get("g")
        acc = {k: [] for k in ("spawn", "rule", "base", "hold", "total", "bias", "raw1")}
        for g in GAMES:
            if g not in base:
                continue
            vg = vgam(g, T)
            rh = hist_rho(g, T)
            c2p, c1, c0 = lnm(g, "C2", 0, T, seeds=PERT), lnm(g, "C1", 0, T), lnm(g, "C0", 0, T)
            if not vg or not rh or c2p[0] is None or c1[0] is None or c0[0] is None:
                continue
            d = {"spawn": -math.log(vg), "base": c0[0] - c1[0], "hold": c1[0] - c2p[0], "total": -math.log(rh)}
            d["rule"] = d["total"] - d["spawn"] - d["base"] - d["hold"]
            d["bias"] = c2p[0] - math.log(rh)
            d["raw1"] = math.log(vg) - c1[0]
            for k in acc:
                acc[k].append(d[k])
        n = len(acc["total"])
        if not n:
            continue
        m = {k: sum(v) / n for k, v in acc.items()}
        J["path"][str(T)] = dict(m, n=n, gamma=gm, median={k: med(v) for k, v in acc.items()})
        P(f"{T}\t{f(gm, 2)}\t{n}\t{math.exp(-m['total']):.3f}\t" + "\t".join(f(m[k], sign=True) for k in ("spawn", "rule", "base", "hold", "total", "bias", "raw1")))
    P("")

    # ---------- 表 1d：断面 0 出发，两项通道差逐拍怎么长出来（每 60 拍；各局平均）
    P("## 表 1d：断面 0 出发，两项通道差逐拍（各局平均；每局先对种子取平均）")
    P("观察拍\t局数\t基础延迟 ln ρC0 − ln ρC1\t其中我方领土 ln(C0 ÷ C1)\t按住与成批放行 ln ρC1 − ln ρC2p\t其中我方领土 ln(C1 ÷ C2p)\t基础延迟：各局中位数\t按住与成批放行：各局中位数")
    J["chanPath"] = {}

    def run_ln(g, tags, t, key):
        h = base[g]
        vals = []
        for tg in tags:
            j = runs.get((g, tg))
            if not j:
                continue
            s = snap_at(j["snaps"], t, 1)
            if not s:
                continue
            x = rho(s, h["nSquad"], h["nOther"]) if key == "rho" else s[key]
            if x and x > 0:
                vals.append(math.log(x))
        return mean(vals)

    C0T, C1T, C2T = [f"C0-t0-s{i}" for i in (0, 1, 2)], [f"C1-t0-s{i}" for i in (0, 1, 2)], [f"C2-t0-s{i}" for i in (1, 2)]
    for t in range(60, 1501, 60):
        acc = {k: [] for k in ("base", "baseS", "hold", "holdS")}
        for g in GAMES:
            if g not in base:
                continue
            c0, c1, c2 = run_ln(g, C0T, t, "rho"), run_ln(g, C1T, t, "rho"), run_ln(g, C2T, t, "rho")
            s0, s1, s2 = run_ln(g, C0T, t, "LS"), run_ln(g, C1T, t, "LS"), run_ln(g, C2T, t, "LS")
            if None in (c0, c1, c2, s0, s1, s2):
                continue
            acc["base"].append(c0 - c1); acc["baseS"].append(s0 - s1); acc["hold"].append(c1 - c2); acc["holdS"].append(s1 - s2)
        n = len(acc["base"])
        if not n:
            continue
        J["chanPath"][str(t)] = dict({k: sum(v) / n for k, v in acc.items()}, n=n, baseMed=med(acc["base"]), holdMed=med(acc["hold"]))
        P(f"{t}\t{n}\t" + "\t".join(f(sum(acc[k]) / n, sign=True) for k in ("base", "baseS", "hold", "holdS")) + f"\t{f(med(acc['base']), sign=True)}\t{f(med(acc['hold']), sign=True)}")
    P("")

    # ---------- 表 1b：断面 0 → 1500 拍，领土的去向
    P("## 表 1b：断面 0 → 1500 拍时全图陆地的分布（占全图陆地的百分比；多个种子取平均）")
    P("局\t通道\t我方号\t其他真人\t内置 AI\t没人占\t我方号存活 / 开局\t种子数")
    for g in GAMES:
        h = base.get(g)
        if not h:
            continue
        land = h["land"]
        for ch, tags in (("历史", None), ("C2 种子 0", ["C2-t0-s0"]), ("C2p", ["C2-t0-s1", "C2-t0-s2"]), ("C1", ["C1-t0-s0", "C1-t0-s1", "C1-t0-s2"]), ("C0", ["C0-t0-s0", "C0-t0-s1", "C0-t0-s2"])):
            js = [h] if tags is None else [runs[(g, t)] for t in tags if (g, t) in runs]
            ss = [snap_at(j["snaps"], 1500) for j in js]
            ss = [x for x in ss if x]
            if not ss:
                continue
            m = lambda k: sum(x[k] for x in ss) / len(ss)
            free = land - m("LS") - m("LO") - m("botL")
            P(f"{g}\t{ch}\t{100 * m('LS') / land:.1f}\t{100 * m('LO') / land:.1f}\t{100 * m('botL') / land:.1f}\t{100 * free / land:.1f}\t{m('aS'):.1f} / {h['nSquad']}\t{len(ss)}")
            J["games"].setdefault(g, {}).setdefault("land1500", {})[ch] = {"LS": m("LS") / land, "LO": m("LO") / land, "bot": m("botL") / land, "aS": m("aS"), "n": len(ss)}
    P("")

    # ---------- 表 1c：同一组对照拆成「我方领土」和「其他真人领土」两半
    def lnL(g, chan, T0, hh, key, seeds):
        v = [math.log(r[key]) for r in sel(g, chan, T0, hh, seeds=seeds) if r[key] > 0]
        return mean(v)

    for T in (630, 1500):
        P(f"## 表 1c-{T}：断面 0 → {T} 拍，把 ρ 的变化拆成我方领土和其他真人领土（自然对数差；ρ 的差 = 我方的差 − 其他真人的差）")
        P("局\t基础延迟：我方 ln(C0 ÷ C1)\t其他真人 ln(C0 ÷ C1)\t按住与成批放行：我方 ln(C1 ÷ C2p)\t其他真人 ln(C1 ÷ C2p)\t走偏：我方 ln(C2p ÷ 历史)\t其他真人 ln(C2p ÷ 历史)")
        acc = [[] for _ in range(6)]
        for g in GAMES:
            h = base.get(g)
            if not h:
                continue
            sh = snap_at(h["snaps"], T)
            vals = []
            for key, hk in (("LS", "LS"), ("LO", "LO")):
                c0, c1, c2p = lnL(g, "C0", 0, T, key, (0, 1, 2)), lnL(g, "C1", 0, T, key, (0, 1, 2)), lnL(g, "C2", 0, T, key, (1, 2))
                lh = math.log(sh[hk]) if sh and sh[hk] > 0 else None
                vals.append((sub(c0, c1), sub(c1, c2p), sub(c2p, lh)))
            row = [vals[0][0], vals[1][0], vals[0][1], vals[1][1], vals[0][2], vals[1][2]]
            if all(x is None for x in row):
                continue
            for i, x in enumerate(row):
                acc[i].append(x)
            J["games"].setdefault(g, {})[f"split_{T}"] = {"baseS": row[0], "baseO": row[1], "holdS": row[2], "holdO": row[3], "biasS": row[4], "biasO": row[5]}
            P(f"{g}\t" + "\t".join(f(x, sign=True) for x in row))
        if any(any(x is not None for x in a) for a in acc):
            P("平均\t" + "\t".join(f(mean(a), sign=True) for a in acc))
            P("中位数\t" + "\t".join(f(med(a), sign=True) for a in acc))
            J[f"split_{T}"] = {"mean": [mean(a) for a in acc], "median": [med(a) for a in acc]}
        P("")

    # ---------- 表 2h：各断面往后 900 拍，历史上发生了什么（只用整局重放，不需要对照）
    P("## 表 2h：各断面往后 900 拍的历史（整局重放）")
    P("局\t断面\tρ(断面)\tρ(900 拍后)\tln ρ 的变化\t我方在场号 断面 → 900 拍后\t其他真人在场 断面 → 900 拍后\t我方占全图陆地 断面 → 900 拍后")
    J["histWin"] = {}
    for T0 in (630, 1500, 4284):
        acc = []
        for g in GAMES:
            h = base.get(g)
            if not h:
                continue
            s0 = snap_at(h["snaps"], T0, 1)
            s1 = snap_at(h["snaps"], T0 + 900)
            if not s0:
                continue
            r0 = rho(s0, h["nSquad"], h["nOther"])
            r1 = rho(s1, h["nSquad"], h["nOther"]) if s1 else None
            d = math.log(r1) - math.log(r0) if r0 and r1 else None
            rec = {"rho0": r0, "rho1": r1, "d": d, "aS0": s0["aS"], "aS1": s1["aS"] if s1 else None, "aO0": s0["aO"], "aO1": s1["aO"] if s1 else None,
                   "ls0": s0["LS"] / h["land"], "ls1": s1["LS"] / h["land"] if s1 else None, "nSquad": h["nSquad"], "end": h["endTick"]}
            J["histWin"].setdefault(g, {})[str(T0)] = rec
            if d is not None:
                acc.append(d)
            P(f"{g}\t{T0}\t{f(r0)}\t{f(r1)}\t{f(d, sign=True)}\t{s0['aS']} → {s1['aS'] if s1 else '-'}\t{s0['aO']} → {s1['aO'] if s1 else '-'}\t{100 * rec['ls0']:.1f}% → " + (f"{100 * rec['ls1']:.1f}%" if s1 else "-"))
        if acc:
            J["histWin"].setdefault("sum", {})[str(T0)] = {"mean": mean(acc), "median": med(acc), "n": len(acc), "up": sum(1 for x in acc if x > 0), "down": sum(1 for x in acc if x < 0)}
            P(f"平均（{len(acc)} 局，不含我方已全灭的）\t{T0}\t\t\t{f(mean(acc), sign=True)}")
    P("")

    # ---------- 表 2：各断面的窗口分解
    J["win"] = {}
    J["winSum"] = {}
    for T0 in (630, 1500, 4284):
        for hh in (300, 600, 900):
            P(f"## 表 2-{T0}+{hh}：断面 {T0} → {T0 + hh} 拍")
            P("局\tρ(断面)\tΔ历史\tΔC2 种子 0\tΔC2p\tΔC1\tΔC0\t基础延迟 ΔC0 − ΔC1\t按住与成批放行 ΔC1 − ΔC2p\t走偏带来的虚高 ΔC2p − Δ历史\t种子数 C0/C1/C2p\t种子标准差 C1 / C2p\t别的真人指令结果翻转（C1，占条数）")
            ks = ("dH", "d2s0", "d2p", "d1", "d0", "base", "hold", "bias")
            acc = {k: [] for k in ks}
            for g in GAMES:
                h = base.get(g)
                if not h:
                    continue
                r0 = rho(snap_at(h["snaps"], T0, 1), h["nSquad"], h["nOther"])
                rh = hist_rho(g, T0 + hh)
                if r0 is None or r0 <= 0:
                    continue
                c2s0, c2p, c1, c0 = lnm(g, "C2", T0, hh, seeds=(0,)), lnm(g, "C2", T0, hh, seeds=(1, 2)), lnm(g, "C1", T0, hh), lnm(g, "C0", T0, hh)
                if c1[0] is None and c2p[0] is None and c0[0] is None and c2s0[0] is None:
                    continue
                l0 = math.log(r0)
                d = {"dH": sub(ln(rh), l0), "d2s0": sub(c2s0[0], l0), "d2p": sub(c2p[0], l0), "d1": sub(c1[0], l0), "d0": sub(c0[0], l0)}
                d["base"] = sub(d["d0"], d["d1"]); d["hold"] = sub(d["d1"], d["d2p"]); d["bias"] = sub(d["d2p"], d["dH"])
                fl = sel(g, "C1", T0, hh)
                flip = (sum(x["oppOkFlip"] for x in fl) / max(1, sum(x["oppCmds"] for x in fl))) if fl else None
                # 平均和中位数只用「历史、C2p、C1 都有定义」的局（我方全灭时 ln ρ 没有定义），免得各列的局不一样
                excl = g in EXCL_WIN.get(T0, ())
                core_ok = all(d[k] is not None for k in ("dH", "d2p", "d1")) and not excl
                for k in acc:
                    acc[k].append(d[k] if core_ok else None)
                J["win"].setdefault(g, {})[f"t{T0}_h{hh}"] = dict(d, rho0=r0, rhoH=rh, n=[c0[2], c1[2], c2p[2]], sdC1=c1[1], sdC2p=c2p[1], flip=flip, excl=excl)
                dh = "历史上已全灭" if rh is not None and rh == 0 else f(d["dH"], sign=True)
                P(f"{g}\t{r0:.3f}\t{dh}\t" + "\t".join(f(d[k], sign=True) for k in ks[1:]) + f"\t{c0[2]}/{c1[2]}/{c2p[2]}\t{f(c1[1], 2)} / {f(c2p[1], 2)}\t{f(100 * flip, 1) + '%' if flip is not None else '-'}")
            if any(x is not None for x in acc["d1"]):
                P("中位数\t\t" + "\t".join(f(med(acc[k]), sign=True) for k in ks))
                P("平均\t\t" + "\t".join(f(mean(acc[k]), sign=True) + f"（{sum(1 for x in acc[k] if x is not None)} 局）" for k in ks))
                J["winSum"][f"t{T0}_h{hh}"] = {k: {"mean": mean(acc[k]), "median": med(acc[k]), "n": sum(1 for x in acc[k] if x is not None)} for k in ks}
            P("")

    # ---------- 表 2e：窗口末尾的水平值（我方全灭时 ρ = 0，ln ρ 没有定义，所以另列水平值）
    P("## 表 2e：各断面 → 900 拍后的水平值（多个种子取平均；我方全灭时 ρ = 0，ln ρ 没有定义）")
    P("局\t断面\t断面时：ρ / 我方领土 / 我方在场号\t历史：ρ / 我方领土 / 在场号\tC2p\tC1\tC0")
    J["winLevel"] = {}
    for T0 in (630, 1500, 4284):
        for g in GAMES:
            h = base.get(g)
            if not h:
                continue
            s0, s1 = snap_at(h["snaps"], T0, 1), snap_at(h["snaps"], T0 + 900)
            if not s0 or not s1:
                continue
            rec = {"rho0": rho(s0, h["nSquad"], h["nOther"]), "LS0": s0["LS"], "aS0": s0["aS"],
                   "H": {"rho": rho(s1, h["nSquad"], h["nOther"]), "LS": s1["LS"], "aS": s1["aS"], "n": 1}}
            for key, chan, seeds in (("C2p", "C2", PERT), ("C1", "C1", (0, 1, 2)), ("C0", "C0", (0, 1, 2))):
                rr = sel(g, chan, T0, 900, seeds=seeds)
                if rr:
                    rec[key] = {"rho": mean([float(r["rho"]) for r in rr]), "LS": mean([r["LS"] for r in rr]), "aS": mean([r["aS"] for r in rr]), "n": len(rr)}
            if not any(k in rec for k in ("C2p", "C1", "C0")):
                continue
            J["winLevel"].setdefault(g, {})[str(T0)] = rec

            def lv(k):
                x = rec.get(k)
                return f"{x['rho']:.3f} / {x['LS']:.0f} / {x['aS']:g}" if x else "-"
            P(f"{g}\t{T0}\t{rec['rho0']:.3f} / {rec['LS0']} / {rec['aS0']}\t" + "\t".join(lv(k) for k in ("H", "C2p", "C1", "C0")))
    P("")

    # ---------- 表 2w：各断面窗口的三层（站位基准用窗口两端的 v_γ；1500 拍以后的 v_γ 来自 105_human_fill.mjs --late）
    late = (spar.get("late") or {}).get("games") or {}

    def vg_any(g, T):
        x = (spar["games"].get(g) or {}).get(f"vg{T}")
        return x if x is not None else (late.get(g) or {}).get(f"vg{T}")

    P("## 表 2w：各断面往后 900 拍的三层（正数 = 这一层让我方在这一窗里更落后）")
    P("（合计 = −Δ历史；出生站位 = 窗口两端 −ln v_γ 之差（630 断面的窗口末端用 1500 拍的 v_γ）；按住与成批放行 = ΔC1 − ΔC2p；规则（基础延迟通道下，含走偏的虚高）= 合计 − 前两项）")
    P("局\t断面\t合计\t出生站位\t按住与成批放行\t规则（基础延迟通道下）\t其中走偏带来的虚高\t基础延迟 ΔC0 − ΔC1")
    J["win3"] = {}
    ENDPAR = {630: 1500, 1500: 2400, 4284: 5184}
    for T0 in (630, 1500, 4284):
        rowsd = []
        names_ = []
        for g in GAMES:
            w = J["win"].get(g, {}).get(f"t{T0}_h900")
            if not w or w.get("dH") is None or w.get("hold") is None or w.get("excl"):
                continue
            v0, v1 = vg_any(g, T0), vg_any(g, ENDPAR[T0])
            if not v0 or not v1:
                continue
            total = -w["dH"]
            spawn = math.log(v0) - math.log(v1)
            hold = w["hold"]
            rule = total - spawn - hold
            rec = {"total": total, "spawn": spawn, "hold": hold, "rulebase": rule, "bias": w.get("bias"), "base": w.get("base")}
            rowsd.append(rec)
            names_.append(g)
            P(f"{g}\t{T0}\t{f(total, sign=True)}\t{f(spawn, sign=True)}\t{f(hold, sign=True)}\t{f(rule, sign=True)}\t{f(rec['bias'], sign=True)}\t{f(rec['base'], sign=True)}")
        if not rowsd:
            continue
        n = len(rowsd)
        m = {k: sum(r[k] for r in rowsd) / n for k in ("total", "spawn", "hold", "rulebase")}
        out = {"n": n, "mean": m, "games": dict(zip(names_, rowsd))}
        if abs(m["total"]) > 0.2:
            bs = boot_shares(rowsd, ("spawn", "hold", "rulebase"))
            out["shares"] = bs
        J["win3"][str(T0)] = out
        P(f"平均（{n} 局）\t{T0}\t{f(m['total'], sign=True)}\t{f(m['spawn'], sign=True)}\t{f(m['hold'], sign=True)}\t{f(m['rulebase'], sign=True)}")
        if "shares" in out:
            P(f"占合计的比例\t{T0}\t100%\t" + "\t".join(f"{100 * out['shares'][k]['share']:.0f}%（{100 * out['shares'][k]['lo']:.0f}% ~ {100 * out['shares'][k]['hi']:.0f}%）" for k in ("spawn", "hold", "rulebase")))
    P("")

    # ---------- 表 3：版本对照
    P("## 表 3：另一个历史版本（原文）在同一断面、同一通道下：ln ρ(Vb) − ln ρ(Va)")
    P("（A007 历史上用 Va，其余 10 局用 Vb；另一版本和本局版本用同样的种子比；C2 只用扰动种子，因为种子 0 的本局版本不走偏）")
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
                    # C2 的种子 0 不走偏（等于历史），另一版本一接管就走偏，两者不能直接比：C2 只用扰动种子
                    common = sorted(x for x in set(ra) & set(rn) if not (ch == "C2" and x == 0))
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
    J["verRows"] = [{"g": g, "T0": t, "h": h2, "ch": ch, "d": d} for ch in ("C1", "C2") for g, t, h2, d in verd[ch]]
    # 表 3a：断面 0 换版本，直接比两次运行的每个记录拍（两版在 coreFrom=1500 拍以前走同一段逻辑，应当逐拍相同）
    P("## 表 3a：断面 0、C1、种子 0：换成另一个版本后，0~1500 拍每个记录拍是否与本局版本相同")
    P("局\t记录拍数\t不同的记录拍数\t发出 本局版本 / 另一版本\t落地 本局版本 / 另一版本")
    same = []
    for g in GAMES:
        alt = "vb" if g == "A007" else "va"
        ja, jb = runs.get((g, "C1-t0-s0")), runs.get((g, f"C1-t0-s0-{alt}"))
        if not ja or not jb:
            continue
        sa = {x["t"]: x for x in ja["snaps"]}
        sb = {x["t"]: x for x in jb["snaps"]}
        ks = ("LS", "LO", "BS", "BO", "botL", "seat", "seatB", "aS", "aO")
        common = sorted(set(sa) & set(sb))
        nd = sum(1 for t in common if any(sa[t][k] != sb[t][k] for k in ks))
        rec = {"g": g, "snaps": len(common), "diff": nd, "issuedA": ja["chanStat"]["issued"], "issuedB": jb["chanStat"]["issued"], "landedA": ja["chanStat"]["landed"], "landedB": jb["chanStat"]["landed"],
               "landSame": ja.get("landSum") == jb.get("landSum")}
        same.append(rec)
        P(f"{g}\t{rec['snaps']}\t{nd}\t{rec['issuedA']} / {rec['issuedB']}\t{rec['landedA']} / {rec['landedB']}")
    if same:
        J["verSame"] = {"rows": same, "n": len(same), "identical": sum(1 for r in same if r["diff"] == 0), "snaps": min(r["snaps"] for r in same),
                        "issuedDiff": sum(1 for r in same if r["issuedA"] != r["issuedB"]), "landSame": sum(1 for r in same if r["landSame"])}
    P("")
    J["ver"] = {}
    for ch in ("C1", "C2"):
        for T0, hh in ((0, 630), (0, 1500), (630, 900), (1500, 900)):
            xs = [d for g, t, h2, d in verd[ch] if t == T0 and h2 == hh]
            if xs:
                P(f"{ch}，断面 {T0} 看 {hh} 拍：{len(xs)} 局，中位数 {med(xs):+.3f}，最小 {min(xs):+.3f}，最大 {max(xs):+.3f}，Vb 更高的 {sum(1 for x in xs if x > 0)} 局")
                J["ver"][f"{ch}_t{T0}_h{hh}"] = {"n": len(xs), "median": med(xs), "min": min(xs), "max": max(xs), "pos": sum(1 for x in xs if x > 0)}
    P("")

    # ---------- 表 4：延迟取法的敏感性（都和同一局、同一种子的 C0 比）
    P("## 表 4：基础延迟取法的敏感性（种子 0；每格 = ln ρ(这一种取法) − ln ρ(C0)；负数 = 比零延迟差）")
    P("# C0：策略决策那一拍立刻生效（可以不在回合边界上，线上不存在这种通道）；C0b：同 C0，但一个决策拍只受理一条；")
    P("# 只等回合边界：在途 0 拍，只等到下一个回合边界（平均约 3 拍）；默认：C1 的实测取法（合计约 12 拍）；5~12、10~18：d 在这个范围里均匀抽（再等到回合边界）")
    P("局\t断面\t看多少拍\tC0b\t只等回合边界\tC1 默认\tC1 的 d 取 5~12\tC1 的 d 取 10~18")
    SV = (("c0b", "C0b", ""), ("d0", "C1", "d0_0"), ("emp", "C1", ""), ("d5", "C1", "d5_12"), ("d10", "C1", "d10_18"))
    sens = {}
    sens_rows = []
    for g in GAMES:
        for T0 in (0, 630):
            for hh in ((630, 1500) if T0 == 0 else (300, 900)):
                c0 = lnm(g, "C0", T0, hh, seeds=(0,))
                vals = []
                for k, ch, variant in SV:
                    x = lnm(g, ch, T0, hh, variant=variant, seeds=(0,))
                    vals.append(sub(x[0], c0[0]))
                if sum(1 for x in vals if x is not None) < 2:
                    continue
                for (k, ch, variant), x in zip(SV, vals):
                    sens.setdefault((T0, hh), {}).setdefault(k, []).append(x)
                sens_rows.append(dict({"g": g, "T0": T0, "h": hh}, **{k: x for (k, ch, variant), x in zip(SV, vals)}))
                P(f"{g}\t{T0}\t{hh}\t" + "\t".join(f(x, sign=True) for x in vals))
    J["sensRows"] = sens_rows
    J["sens"] = {}
    for (T0, hh), dct in sorted(sens.items()):
        cells = []
        for k, ch, variant in SV:
            xs = [x for x in dct.get(k, []) if x is not None]
            cells.append(f"{med(xs):+.3f}（{len(xs)} 局，{min(xs):+.3f} ~ {max(xs):+.3f}）" if xs else "-")
            if xs:
                J["sens"][f"t{T0}_h{hh}_{k}"] = {"n": len(xs), "median": med(xs), "mean": mean(xs), "min": min(xs), "max": max(xs)}
        P(f"中位数（局数，最小 ~ 最大）\t{T0}\t{hh}\t" + "\t".join(cells))
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
                    J.setdefault("leave", []).append({"g": g, "T0": T0, "h": hh, "C1": cells[0], "C2": cells[1]})
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
            J.setdefault("fate", {}).setdefault(g, {})[ch] = {k: r[k] for k in ("issued", "landed", "landedOk", "mapDrop", "capDrop", "second", "delayP50", "delayP90", "LS", "BS", "outS")}
        h = base.get(g)
        if h:
            s = snap_at(h["snaps"], 1500)
            P(f"{g}\t历史\t\t\t\t\t\t\t\t{s['LS']}\t{s['BS']}\t{s['outS']}")
            J.setdefault("fate", {}).setdefault(g, {})["历史"] = {"LS": s["LS"], "BS": s["BS"], "outS": s["outS"]}
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
        J["noise"] = [{"g": g, "T0": T0, "h": hh, "maxDev": d, "n": n} for g, T0, hh, d, n in nz]

    # ---------- 表 10：同一条对照重跑（mt-a = A089 C1 断面 0 种子 1；mt-b = A089 C2 断面 630 种子 0）：每个记录拍是否相同
    rer = []
    for g, ta, tb in (("A089", "mt-a", "C1-t0-s1"), ("A089", "mt-b", "C2-t630-s0")):
        ja, jb = jload(os.path.join(CP, g, ta + ".json")), runs.get((g, tb))
        if not ja or not jb:
            continue
        sa = {x["t"]: x for x in ja["snaps"]}
        sb = {x["t"]: x for x in jb["snaps"]}
        ks2 = ("LS", "LO", "BS", "BO", "botL", "seat", "seatB", "aS", "aO")
        common = sorted(set(sa) & set(sb))
        rer.append({"g": g, "a": ta, "b": tb, "snaps": len(common), "diff": sum(1 for t in common if any(sa[t][k] != sb[t][k] for k in ks2)),
                    "cmdSame": ja.get("cmdSum") == jb.get("cmdSum")})
    if rer:
        P("## 表 10：同一条对照在不同进程里重跑一次：记录拍是否相同")
        P("局\t两次运行\t记录拍数\t不同的记录拍数\t指令汇总是否相同")
        for x in rer:
            P(f"{x['g']}\t{x['a']} / {x['b']}\t{x['snaps']}\t{x['diff']}\t{'相同' if x['cmdSame'] else '不同'}")
        P("")
        J["rerun"] = rer

    # ---------- 表 9：同一局、同一通道、同一断面，只换种子：ln ρ 的最大值 − 最小值
    ss = []
    for g in GAMES:
        for T0, hh in ((0, 1500), (630, 900), (1500, 900), (4284, 900)):
            for ch, chan, seeds in (("C1", "C1", (0, 1, 2)), ("C2p", "C2", PERT)):
                xs = [math.log(float(r["rho"])) for r in sel(g, chan, T0, hh, seeds=seeds) if float(r["rho"]) > 0]
                if len(xs) >= 2:
                    ss.append({"g": g, "T0": T0, "h": hh, "ch": ch, "n": len(xs), "range": max(xs) - min(xs)})
    if ss:
        P("## 表 9：只换种子，ln ρ 的最大值 − 最小值（C1 种子 0~2；C2p 种子 1~2）")
        P("局\t断面\t看多少拍\t通道\t种子数\tln ρ 最大 − 最小")
        for x in ss:
            P(f"{x['g']}\t{x['T0']}\t{x['h']}\t{x['ch']}\t{x['n']}\t{x['range']:.3f}")
        P("")
        J["seedSpread"] = ss

    open(os.path.join(CROSS, "checkpoint_attribution.txt"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    json.dump(J, open(os.path.join(CROSS, "checkpoint_attribution.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n".join(L))


if __name__ == "__main__":
    main()
