#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""104_channel_exposure.py — R07：11 局录像里我方指令的去向，按发令拍分窗（给断面归因报告的「通道实况」一节用）。

读：out/<局>/release_map.json（101_release_map.py）、out/_cache/cp/<局>/H.json（100_checkpoint.mjs --chan H）
写：out/_cross/channel_exposure.txt / .json
每一窗：影子发令条数（不含发令时就会被配额拒掉的捐款）、其中 14 拍内落地 / 15~35 拍落地 / 35 拍以上落地 / 没落地。
另：0~600 拍的在途拍数分布（C1 基础延迟的取法就照它）。
用法：python3 104_channel_exposure.py
"""
import bisect
import collections
import json
import os
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out")
GAMES = ["A007", "A033", "A039", "A053", "A061", "A062", "A070", "A079", "A082", "A089", "A091"]
WINS = [(0, 300), (300, 630), (630, 900), (900, 1200), (1200, 1500), (1500, 2400), (2400, 3300), (3300, 4284), (4284, 5184), (5184, 10**9)]


def wname(w):
    return f"{w[0]}~{w[1]}" if w[1] < 10**9 else f"{w[0]} 以后"


def main():
    L = []
    P = L.append
    J = {}
    P("# 11 局录像里我方指令的去向（104_channel_exposure.py）")
    P("# 发令 = 历史策略在真实局面上影子运行时每个决策拍受理的那一条（不含发令时就会被配额拒掉的捐款）；落地 = 录像里对上的那一条")
    P("")
    P("## 表 A：整局。局 | 版本 | 录像里我方落地 | 能和影子发令逐条对上（种类 + 比例）| 影子发令 | 没落地 | 没落地占发令 | 成批放行且后面有指令没落地的段 | 段内落地 / 段内没落地")
    lag_early = []
    for g in GAMES:
        rm = json.load(open(os.path.join(OUT, g, "release_map.json"), encoding="utf-8"))
        t = rm["total"]
        matched = t["exact"] + t["pctOnly"]
        P(f"{g}\t{rm['ver']}\t{t['landed']}\t{matched}（{100 * matched / t['landed']:.1f}%）\t{t['intents']}\t{t['dropped']}\t{100 * t['dropped'] / t['intents']:.1f}%\t{t['segs']}\t{t['segLanded']} / {t['segDropped']}")
        J[g] = {"ver": rm["ver"], "landed": t["landed"], "matched": matched, "intents": t["intents"], "dropped": t["dropped"], "segs": t["segs"]}
    P("")

    P("## 表 B：按发令拍分窗。局 | 窗 | 发令 | 14 拍内落地 | 15~35 拍落地 | 35 拍以上落地 | 没落地 | 落地的在途拍数中位 | 「35 拍以上或没落地」占发令")
    tot = collections.defaultdict(lambda: [0, 0, 0, 0, 0])
    for g in GAMES:
        rm = json.load(open(os.path.join(OUT, g, "release_map.json"), encoding="utf-8"))
        hp = os.path.join(OUT, "_cache", "cp", g, "H.json")
        if not os.path.exists(hp):
            P(f"{g}\t（缺 {hp}，先跑 100_checkpoint.mjs {g} --chan H）")
            continue
        h = json.load(open(hp, encoding="utf-8"))
        intents = [x for x in h["intents"] if not x[5]]
        J[g]["win"] = {}
        pts = []
        for b, sv in rm["seats"].items():
            pts += sv["pts"]
        pts.sort()
        its = sorted(x[0] for x in intents)
        for w in WINS:
            n = bisect.bisect_left(its, w[1]) - bisect.bisect_left(its, w[0])
            lg = [p[1] for p in pts if w[0] <= p[0] < w[1]]
            a = sum(1 for x in lg if x <= 14)
            b_ = sum(1 for x in lg if 14 < x <= 35)
            c = sum(1 for x in lg if x > 35)
            d = n - len(lg)
            if n == 0:
                continue
            med = statistics.median(lg) if lg else None
            bad = (c + max(0, d)) / n
            P(f"{g}\t{wname(w)}\t{n}\t{a}\t{b_}\t{c}\t{d}\t{'-' if med is None else f'{med:.0f}'}\t{100 * bad:.0f}%")
            J[g]["win"][wname(w)] = {"n": n, "le14": a, "15_35": b_, "gt35": c, "dropped": d, "medLag": med, "heldShare": bad}
            tt = tot[wname(w)]
            tt[0] += n; tt[1] += a; tt[2] += b_; tt[3] += c; tt[4] += d
            if w[1] <= 630:
                lag_early += [x for x in lg] if g != "A062" else []
        P("")
    P("## 表 C：11 局合计，按发令拍分窗。窗 | 发令 | 14 拍内落地 | 15~35 拍落地 | 35 拍以上落地 | 没落地 | 「35 拍以上或没落地」占发令")
    J["all"] = {}
    for w in WINS:
        k = wname(w)
        if k not in tot:
            continue
        n, a, b_, c, d = tot[k]
        P(f"{k}\t{n}\t{a}\t{b_}\t{c}\t{d}\t{100 * (c + max(0, d)) / n:.0f}%")
        J["all"][k] = {"n": n, "le14": a, "15_35": b_, "gt35": c, "dropped": d}
    P("")

    # 基础延迟：0~600 拍发令、落地的指令的在途拍数（不含 A062：它 0~600 拍就有成批放行）
    base = []
    for g in GAMES:
        if g == "A062":
            continue
        rm = json.load(open(os.path.join(OUT, g, "release_map.json"), encoding="utf-8"))
        for b, sv in rm["seats"].items():
            base += [p[1] for p in sv["pts"] if p[0] < 600]
    base.sort()
    P(f"## 表 D：基础延迟的实测分布（10 局，不含 A062；发令拍 < 600 且落地的 {len(base)} 条）")
    P(f"均值 {statistics.mean(base):.2f} 拍，中位 {statistics.median(base):.0f}，P90 {base[int(0.9 * len(base))]}，最大 {base[-1]}")
    cum = []
    for th in (7, 10, 12, 14, 19, 21, 28, 35):
        cum.append(f"≤{th} 拍 {100 * sum(1 for x in base if x <= th) / len(base):.1f}%")
    P("累计：" + "，".join(cum))
    J["baseDelay"] = {"n": len(base), "mean": statistics.mean(base), "median": statistics.median(base), "p90": base[int(0.9 * len(base))], "max": base[-1],
                      "cum": {str(th): sum(1 for x in base if x <= th) / len(base) for th in (7, 10, 12, 14, 19, 21, 28, 35)}}
    # C1 默认取法的理论分布：d = 7 或 8，各一半；另有 10% 再加 7 / 14 / 21（6% / 2.5% / 1.5%）；落地拍 = ⌈(t+d)/7⌉×7，t 在 5 拍一档的决策拍上
    sim = []
    for t in range(0, 35 * 20, 5):
        for d0, w0 in ((7, 0.5), (8, 0.5)):
            for ex, we in ((0, 0.90), (7, 0.06), (14, 0.025), (21, 0.015)):
                land = -(-(t + d0 + ex) // 7) * 7
                sim.append((land - t, w0 * we))
    sw = sum(w for _, w in sim)
    mean_sim = sum(l * w for l, w in sim) / sw
    P(f"C1 默认取法（d = 7 或 8 各一半，另 10% 再加 7 / 14 / 21 拍）换算成在途拍数：均值 {mean_sim:.2f} 拍；"
      + "，".join(f"≤{th} 拍 {100 * sum(w for l, w in sim if l <= th) / sw:.1f}%" for th in (7, 10, 12, 14, 19, 21, 28, 35)))
    J["c1Model"] = {"mean": mean_sim, "cum": {str(th): sum(w for l, w in sim if l <= th) / sw for th in (7, 10, 12, 14, 19, 21, 28, 35)}}

    os.makedirs(os.path.join(OUT, "_cross"), exist_ok=True)
    open(os.path.join(OUT, "_cross", "channel_exposure.txt"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    json.dump(J, open(os.path.join(OUT, "_cross", "channel_exposure.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n".join(L))


if __name__ == "__main__":
    main()
