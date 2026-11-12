#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""106_spawn_par.py — R07：「出生站位」这一层的基准。

读：out/_cache/fill/<局>.json（105_human_fill.mjs：每个真人的天然地盘格数、各拍领土）
写：out/_cross/spawn_par.txt / .json、out/_cross/human_fill.tsv（每个真人一行，进 git）

三个基准（报告正文用第二个，另外两个只做敏感性）：
  v       = 我方号人均天然地盘 ÷ 其他真人人均天然地盘（等于假设「全图陆地最后按最近出生点分完」）
  v_γ(T)  = 我方号人均 (天然地盘^γ) ÷ 其他真人人均 (天然地盘^γ)，γ 取同一批对局里「其他真人」在 T 拍的实际情况：
            领土(T) 的期望 = 每局一个常数 × 天然地盘^γ（泊松拟似然；已经出局的人按 0 算在里面，和 ρ 的算法一致；各局合并估一个 γ）
            含义：把我方每个出生点换成「同局其他真人的平均水平」，到 T 拍人均领土应当是其他真人人均的多少。
            γ = 1 就是 v；γ 越小说明到 T 拍为止天然地盘大的人还没把大的那部分变成领土。
  v_β(T)  = 同上，但 β 用对数回归估（ln 领土 = 每局一个常数 + β·ln 天然地盘；只用 T 拍还在场、有地的其他真人）
用法：python3 106_spawn_par.py
"""
import json
import math
import os
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out")
GAMES = ["A007", "A033", "A039", "A053", "A061", "A062", "A070", "A079", "A082", "A089", "A091"]
AT = ["300", "630", "900", "1200", "1500"]


def fit_fe(rows):
    """rows: [(局, x, y)]；y = a_局 + b x。返回 b、标准误、n、局数、组内 R²"""
    by = {}
    for g, x, y in rows:
        by.setdefault(g, []).append((x, y))
    sxx = sxy = syy = 0.0
    n = 0
    for g, pts in by.items():
        if len(pts) < 2:
            continue
        mx = sum(p[0] for p in pts) / len(pts)
        my = sum(p[1] for p in pts) / len(pts)
        for x, y in pts:
            sxx += (x - mx) ** 2
            sxy += (x - mx) * (y - my)
            syy += (y - my) ** 2
        n += len(pts)
    if sxx <= 0 or n < 5:
        return None
    b = sxy / sxx
    k = sum(1 for pts in by.values() if len(pts) >= 2)
    rss = syy - b * sxy
    dof = n - k - 1
    se = math.sqrt(rss / dof / sxx) if dof > 0 else None
    return {"b": b, "se": se, "n": n, "games": k, "r2": 1 - rss / syy if syy > 0 else None}


def ppml_gamma(by):
    """by: {局: [(天然地盘, 领土)]}（领土可以是 0）。期望 = c_局 · x^γ，泊松拟似然，c_局 解析消掉后对 γ 一维求根。"""
    def score(g):
        s = 0.0
        for pts in by.values():
            Y = sum(y for _, y in pts)
            S = sum(x ** g for x, _ in pts)
            if Y <= 0 or S <= 0:
                continue
            for x, y in pts:
                s += (y - Y * x ** g / S) * math.log(x)
        return s
    lo, hi = -2.0, 4.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if score(mid) > 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def fit_ppml(by):
    """返回 γ、逐局剔除一局的刀切标准误、剔除一局后的最小 / 最大 γ、人数、其中领土为 0 的人数"""
    if len(by) < 3:
        return None
    g = ppml_gamma(by)
    jk = [ppml_gamma({k: v for k, v in by.items() if k != m}) for m in by]
    n = len(jk)
    mj = sum(jk) / n
    se = math.sqrt((n - 1) / n * sum((x - mj) ** 2 for x in jk))
    return {"g": g, "se": se, "lo": min(jk), "hi": max(jk), "n": sum(len(v) for v in by.values()), "zeros": sum(1 for v in by.values() for _, y in v if y == 0), "games": n}


def main():
    data = {}
    for g in GAMES:
        p = os.path.join(OUT, "_cache", "fill", f"{g}.json")
        if os.path.exists(p):
            data[g] = json.load(open(p, encoding="utf-8"))
    L = []
    P = L.append
    J = {"games": {}, "beta": {}, "gamma": {}}
    P("# 「出生站位」一层的基准（106_spawn_par.py）")
    P(f"# 已有 {len(data)} / {len(GAMES)} 局的逐人数据")
    P("")
    tsv = ["局\t席位\t我方号\t队\t天然地盘\t天然地盘里开局的内置 AI 地\t最近的别的真人落点距离\t最近的敌方真人落点距离\t" + "\t".join(f"{t} 拍领土\t{t} 拍状态" for t in AT)]
    for g, d in data.items():
        for s in d["sites"]:
            tsv.append(f"{g}\t{s['p']}\t{s['bot'] or ''}\t{s['team']}\t{s['vor']}\t{s['aiIn']}\t{s['nearest']}\t{s['nearestEnemy']}\t"
                       + "\t".join(f"{s['at'].get(t, {}).get('terr', '')}\t{s['at'].get(t, {}).get('st', '')}" for t in AT))
    os.makedirs(os.path.join(OUT, "_cross"), exist_ok=True)
    open(os.path.join(OUT, "_cross", "human_fill.tsv"), "w", encoding="utf-8").write("\n".join(tsv) + "\n")

    # β：其他真人，各拍
    P("## 表 A：其他真人的「领土对天然地盘」弹性 β（各局合并、每局一个常数；只用当拍还在场且有地的其他真人）")
    P("拍\tβ\t标准误\t人数\t局数\t组内 R²\t只用人数 ≥ 30 的局：β（人数）\t只用人数 < 30 的局：β（人数）")
    for t in AT:
        rows, big, small = [], [], []
        for g, d in data.items():
            oth = [s for s in d["sites"] if not s["bot"]]
            pts = [(g, math.log(s["vor"]), math.log(s["at"][t]["terr"])) for s in oth if s["vor"] > 0 and t in s["at"] and s["at"][t]["st"] == 1 and s["at"][t]["terr"] > 0]
            rows += pts
            (big if len(oth) >= 30 else small).extend(pts)
        r = fit_fe(rows)
        rb, rs = fit_fe(big), fit_fe(small)
        if not r:
            continue
        J["beta"][t] = r
        J["beta"][t + "_big"] = rb
        J["beta"][t + "_small"] = rs
        fb = f"{rb['b']:.2f}（{rb['n']}）" if rb else "-"
        fs = f"{rs['b']:.2f}（{rs['n']}）" if rs else "-"
        P(f"{t}\t{r['b']:.3f}\t{r['se']:.3f}\t{r['n']}\t{r['games']}\t{r['r2']:.2f}\t{fb}\t{fs}")
    P("")

    P("## 表 A2：同一件事改用「期望领土 = 每局一个常数 × 天然地盘^γ」估（泊松拟似然；已出局的人按 0 算在里面；在场但操作者已离开的号的地照算，和 ρ 一致）")
    P("拍\tγ\t刀切标准误（逐次剔除一局）\t剔除一局后 γ 的最小 ~ 最大\t人数\t其中领土为 0 的人数")
    for t in AT:
        by = {}
        for g, d in data.items():
            pts = [(s["vor"], s["at"][t]["terr"] if s["at"][t]["st"] != 0 else 0) for s in d["sites"] if not s["bot"] and s["vor"] > 0 and t in s["at"]]
            if pts:
                by[g] = pts
        r = fit_ppml(by)
        if not r:
            continue
        J["gamma"][t] = r
        P(f"{t}\t{r['g']:.3f}\t{r['se']:.3f}\t{r['lo']:.3f} ~ {r['hi']:.3f}\t{r['n']}\t{r['zeros']}")
    P("")

    P("## 表 B：每局的基准。v = 人均天然地盘之比；v_γ(T) 用表 A2 里 T 拍的 γ；v_β(T) 用表 A 里 T 拍的 β")
    P("局\t真人\t我方号\t我方人均天然地盘\t其他真人人均天然地盘\tv\t−ln v\tv_γ(630)\t−ln v_γ(630)\tv_γ(1500)\t−ln v_γ(1500)\tv_β(630)\t−ln v_β(630)\tv_β(1500)\t−ln v_β(1500)\t我方天然地盘中位 ÷ 其他真人中位")
    for g, d in data.items():
        sq = [s for s in d["sites"] if s["bot"]]
        oth = [s for s in d["sites"] if not s["bot"]]
        if not sq or not oth:
            continue
        mS = sum(s["vor"] for s in sq) / len(sq)
        mO = sum(s["vor"] for s in oth) / len(oth)
        v = mS / mO
        rec = {"n": len(d["sites"]), "nS": len(sq), "nO": len(oth), "vorS": mS, "vorO": mO, "v": v}
        cells = []
        for key, src, fld in (("vg", "gamma", "g"), ("vb", "beta", "b")):
            for t in ("630", "1500"):
                b = (J[src].get(t) or {}).get(fld)
                if b is None:
                    cells += ["-", "-"]
                    continue
                vb = (sum(s["vor"] ** b for s in sq) / len(sq)) / (sum(s["vor"] ** b for s in oth) / len(oth))
                rec[f"{key}{t}"] = vb
                cells += [f"{vb:.3f}", f"{-math.log(vb):+.3f}"]
        for t in AT:   # 其余各拍的 v_γ 只进 JSON（103_cp_table.py 的逐拍表用）
            gm = (J["gamma"].get(t) or {}).get("g")
            if gm is not None:
                rec[f"vg{t}"] = (sum(s["vor"] ** gm for s in sq) / len(sq)) / (sum(s["vor"] ** gm for s in oth) / len(oth))
        medr = statistics.median(s["vor"] for s in sq) / statistics.median(s["vor"] for s in oth)
        rec["medRatio"] = medr
        J["games"][g] = rec
        P(f"{g}\t{len(d['sites'])}\t{len(sq)}\t{mS:.0f}\t{mO:.0f}\t{v:.3f}\t{-math.log(v):+.3f}\t" + "\t".join(cells) + f"\t{medr:.2f}")
    P("")

    # 其他真人按天然地盘大小分档的「填满率」
    P("## 表 C：其他真人按天然地盘大小分档，到 630 / 1500 拍把天然地盘变成了多少领土（各局合并；领土 ÷ 天然地盘 的中位数；含已出局的按 0 算）")
    P("天然地盘（格）\t人数\t630 拍 领土 ÷ 天然地盘（中位）\t1500 拍（中位）\t1500 拍已出局或离开的比例")
    bins = [(0, 3000), (3000, 6000), (6000, 10000), (10000, 20000), (20000, 10**9)]
    for lo, hi in bins:
        xs = [s for d in data.values() for s in d["sites"] if not s["bot"] and lo <= s["vor"] < hi]
        if not xs:
            continue
        r630 = statistics.median((s["at"].get("630", {}).get("terr", 0) if s["at"].get("630", {}).get("st") == 1 else 0) / s["vor"] for s in xs)
        r1500 = statistics.median((s["at"].get("1500", {}).get("terr", 0) if s["at"].get("1500", {}).get("st") == 1 else 0) / s["vor"] for s in xs)
        gone = sum(1 for s in xs if s["at"].get("1500", {}).get("st") != 1) / len(xs)
        name = f"{lo}~{hi}" if hi < 10**9 else f"{lo} 以上"
        P(f"{name}\t{len(xs)}\t{r630:.2f}\t{r1500:.2f}\t{100 * gone:.0f}%")
    xs = [s for d in data.values() for s in d["sites"] if s["bot"]]
    if xs:
        r630 = statistics.median((s["at"].get("630", {}).get("terr", 0) if s["at"].get("630", {}).get("st") == 1 else 0) / s["vor"] for s in xs)
        r1500 = statistics.median((s["at"].get("1500", {}).get("terr", 0) if s["at"].get("1500", {}).get("st") == 1 else 0) / s["vor"] for s in xs)
        gone = sum(1 for s in xs if s["at"].get("1500", {}).get("st") != 1) / len(xs)
        P(f"我方号（全部，天然地盘中位 {statistics.median(s['vor'] for s in xs):.0f} 格）\t{len(xs)}\t{r630:.2f}\t{r1500:.2f}\t{100 * gone:.0f}%")
        J["fillSquad"] = {"n": len(xs), "r630": r630, "r1500": r1500, "gone": gone}
    P("")

    # γ 本身有抽样误差：出生站位这一项（各局 −ln v_γ 的平均）跟着变多少
    P("## 表 D：出生站位这一项（各局 −ln v_γ 的平均）对 γ 取值的敏感度")
    P("拍\tγ\t各局平均 −ln v_γ\tγ 减一个标准误\tγ 加一个标准误\t剔除一局后 γ 最小时\t剔除一局后 γ 最大时")
    J["gammaSens"] = {}
    for t in ("630", "1500"):
        r = J["gamma"].get(t)
        if not r:
            continue

        def mean_spawn(gm):
            vals = []
            for d in data.values():
                sq = [s for s in d["sites"] if s["bot"]]
                oth = [s for s in d["sites"] if not s["bot"]]
                if sq and oth:
                    vals.append(-math.log((sum(s["vor"] ** gm for s in sq) / len(sq)) / (sum(s["vor"] ** gm for s in oth) / len(oth))))
            return sum(vals) / len(vals) if vals else None
        cols = [mean_spawn(x) for x in (r["g"], r["g"] - r["se"], r["g"] + r["se"], r["lo"], r["hi"])]
        J["gammaSens"][t] = {"mid": cols[0], "minusSe": cols[1], "plusSe": cols[2], "jkLo": cols[3], "jkHi": cols[4]}
        P(f"{t}\t{r['g']:.3f}\t" + "\t".join(f"{x:+.3f}" for x in cols))
    P("")

    open(os.path.join(OUT, "_cross", "spawn_par.txt"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    json.dump(J, open(os.path.join(OUT, "_cross", "spawn_par.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n".join(L))


if __name__ == "__main__":
    main()
