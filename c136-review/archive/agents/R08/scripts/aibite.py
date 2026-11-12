#!/usr/bin/env python3
"""aibite.py — 内置 AI / 空壳怎么挑目标、咬了真人多少（aibite.mjs 的逐局结果汇总）。

    cd /agent/repos/c136-r08 && export PYTHONDONTWRITEBYTECODE=1
    timeout 120 python3 c136-review/agents/R08/scripts/aibite.py [--quiet]

读 out/_run/aibite/<局>.json（aibite.mjs）和 out/_run/xtruth/<局>.json（席位分组、对不对得上日志；和 xtruth.py 同一个判定）。
只用「对得上且有对局段」的局。输出 out/_cross/aibite.txt / aibite.json。

  [AB-A] 覆盖。
  [AB-B] 内置 AI 的每次决策：候选是什么构成、最后打了谁（引擎写的规则在真局里是不是这么走的）。
  [AB-C] AI 在几个真人里挑的时候：挑的是不是最近的、是不是最弱的；候选里同时有 own 和野人时挑谁。
  [AB-D] 真人被内置 AI 咬走的地、被打掉的余额：按组、按窗的人均。
  [AB-E] 一口咬下去的战果和目标兵密度的关系。
  [AB-F] 空壳（离开的真人，引擎按难度 6 接管）同样几张表的简版。
  [AB-G] 目标正压着这只 AI 的时候挨的那一口（赊账的第一圈还有没有）。
"""
import json
import os
import statistics
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import xtruth as XT  # noqa: E402
from xbatch import name_pool, discovery_ids  # noqa: E402

OUT = os.path.join(HERE, "..", "out")
RUN = os.path.join(OUT, "_run", "aibite")
RUNX = os.path.join(OUT, "_run", "xtruth")
WIN = [600, 900, 1260, 1500, 1800, 2400, 3000]
WN = [f"{WIN[i]}~{WIN[i + 1]}" for i in range(len(WIN) - 1)]
GROUPS = ("own", "apex", "pool", "wild")
GN = {"own": "本编队", "apex": "[APEX]", "pool": "名字池", "wild": "野人"}
CLS = ("有无主地", "只有 AI / 空壳", "只有真人", "真人和 AI / 空壳都有")
DBINS = [(0, 5), (5, 15), (15, 30), (30, 60), (60, 1e9)]
DBN = ["<5", "5~15", "15~30", "30~60", "≥60"]


def q(v, p):
    if not v:
        return None
    v = sorted(v)
    i = p * (len(v) - 1)
    lo = int(i)
    hi = min(lo + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (i - lo)


def fmt(x, nd=0):
    return "—" if x is None else f"{x:.{nd}f}"


def pct(a, b, nd=0):
    return "—" if not b else f"{100 * a / b:.{nd}f}%"


def sign_p(k, n):
    """双侧符号检验（二项，p=0.5）。"""
    if n == 0:
        return None
    from math import comb
    lo = min(k, n - k)
    tail = sum(comb(n, i) for i in range(lo + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def fp(p):
    return "—" if p is None else (f"{p:.2g}" if p < 0.001 else f"{p:.3f}")


def main():
    quiet = "--quiet" in sys.argv
    pool = name_pool()
    ids = discovery_ids()
    lines = []

    def P(x=""):
        lines.append(x)

    n_valid = 0
    reach = Counter()
    dec = [[[[0, 0, 0] for _ in range(4)] for _ in range(2)] for _ in range(len(WN))]
    # 挑选：actor → 统计
    sel = {a: dict(n=0, k=Counter(), nearest=0, weakest=0, thinnest=0, chance=0.0, mixed=0, mixed_own=0, mixed_exp=0.0,
                   mixed_own_stronger=0, mixed_own_denser=0) for a in (0, 1)}
    # 人均：[窗][组] = heads, land, bites, cells, dB, burnt, shellBites, shellCells, shellDB
    ph = [{g: defaultdict(float) for g in GROUPS} for _ in WN]
    per_match = [[] for _ in WN]   # (own 每人被咬的格, 野人每人被咬的格, own 每格地被咬的比例, 野人的)
    # 战果按密度：actor → 组 → 密度档 → 累计
    eff = {a: {g: [defaultdict(float) for _ in DBINS] for g in ("own", "wild")} for a in (0, 1)}
    bite_frac = {g: [] for g in ("own", "wild")}   # 一口咬走的格 ÷ 目标的地（内置 AI，600~1500）
    # 目标在 AI 出手那一拍有没有兵压在这只 AI 身上：组 → [没有, 有] → 密度档 → 累计
    ctrs = {g: [[defaultdict(float) for _ in DBINS] for _ in (0, 1)] for g in ("own", "wild")}
    send_frac = []                                   # 内置 AI 打真人时派出的兵 ÷ 自己的余额
    gap = []                                         # 同一个 AI 相邻两次打真人的间隔
    rows_json = []

    for mid, card in ids:
        p = os.path.join(RUN, f"{mid}.json")
        px = os.path.join(RUNX, f"{mid}.json")
        if not os.path.exists(p) or not os.path.exists(px):
            continue
        A = json.load(open(p, encoding="utf-8"))
        X = json.load(open(px, encoding="utf-8"))
        if "error" in A or "error" in X:
            continue
        names, low, F, own, valid, spawn_only, grp = XT.seat_groups(X, mid, pool)
        if not valid or spawn_only or A["endTick"] <= 600:
            continue
        n_valid += 1
        H = A["H"]
        for T in (900, 1500, 3000):
            if A["endTick"] >= T:
                reach[T] += 1
        for k in range(len(WN)):
            for a in (0, 1):
                for c in range(4):
                    for o in range(3):
                        dec[k][a][c][o] += A["dec"][k][a][c][o]
        last_bite = {}
        mrow = dict(matchId=mid, cohort=card.get("cohort"), bites=[0] * len(WN))
        for b in A["bites"]:
            t, atk, shell, tgt, dn, bal_atk, pn, pb, phm, cands, t_terr, t_bal, res = b[:13]
            ctr = b[13] if len(b) > 13 else None
            k = next((i for i in range(len(WN)) if WIN[i] < t <= WIN[i + 1]), -1)
            if k < 0:
                continue
            g = grp.get(tgt, "wild")
            S = sel[shell]
            if len(cands) >= 2:
                S["n"] += 1
                S["k"][min(len(cands), 5)] += 1
                me = next((c for c in cands if c[0] == tgt), None)
                if me is not None:
                    if me[3] <= min(c[3] for c in cands):
                        S["nearest"] += 1
                    if me[1] <= min(c[1] for c in cands):
                        S["weakest"] += 1
                    if me[2] <= min(c[2] for c in cands):
                        S["thinnest"] += 1
                S["chance"] += 1 / len(cands)
                gs = [grp.get(c[0], "wild") for c in cands]
                if "own" in gs and "wild" in gs:
                    S["mixed"] += 1
                    S["mixed_exp"] += gs.count("own") / len(gs)
                    if g == "own":
                        S["mixed_own"] += 1
                    o_str = statistics.mean(c[1] for c, gg in zip(cands, gs) if gg == "own")
                    w_str = statistics.mean(c[1] for c, gg in zip(cands, gs) if gg == "wild")
                    o_den = statistics.mean(c[2] for c, gg in zip(cands, gs) if gg == "own")
                    w_den = statistics.mean(c[2] for c, gg in zip(cands, gs) if gg == "wild")
                    S["mixed_own_stronger"] += o_str > w_str
                    S["mixed_own_denser"] += o_den > w_den
            if shell == 0:
                mrow["bites"][k] += 1
                if bal_atk > 0:
                    send_frac.append(dn / bal_atk)
                if atk in last_bite:
                    gap.append(t - last_bite[atk])
                last_bite[atk] = t
            if g in ("own", "wild"):
                d = t_bal / max(1, t_terr)
                bi = next(i for i, (lo, hi) in enumerate(DBINS) if lo <= d < hi)
                e = eff[shell][g][bi]
                e["n"] += 1
                e["dn"] += dn
                e["cells"] += res[0]
                e["burnt"] += res[1]
                e["dB"] += res[2]
                e["zero"] += res[0] == 0
                e["rings"] += res[3]
                if shell == 0 and t <= 1500 and t_terr > 0:
                    bite_frac[g].append(res[0] / t_terr)
                if shell == 0 and ctr is not None:
                    c_ = ctrs[g][1 if ctr > 0 else 0][bi]
                    c_["n"] += 1
                    c_["dn"] += dn
                    c_["cells"] += res[0]
                    c_["burnt"] += res[1]
                    c_["dB"] += res[2]
                    c_["zero"] += res[0] == 0
                    c_["rings"] += res[3]
                    c_["ctr"] += ctr
            ph[k][g]["bites" if shell == 0 else "sbites"] += 1
        for k in range(len(WN)):
            c = A["cp"].get(str(WIN[k]))
            if not c:
                continue
            hd = {g: 0 for g in GROUPS}
            ld = {g: 0 for g in GROUPS}
            ls = {g: 0 for g in GROUPS}
            for s in range(H):
                if c["terr"][s] <= 0:
                    continue
                g = grp[s]
                r = A["loss"][k][s]
                hd[g] += 1
                ld[g] += c["terr"][s]
                ls[g] += r[0]
                ph[k][g]["heads"] += 1
                ph[k][g]["land"] += c["terr"][s]
                ph[k][g]["bal"] += c["bal"][s]
                ph[k][g]["cells"] += r[0]
                ph[k][g]["burnt"] += r[1]
                ph[k][g]["dB"] += r[2]
                ph[k][g]["scells"] += r[4]
                ph[k][g]["sdB"] += r[6]
            if hd["own"] >= 3 and hd["wild"] >= 5:
                per_match[k].append((ls["own"] / hd["own"], ls["wild"] / hd["wild"], ls["own"] / max(1, ld["own"]), ls["wild"] / max(1, ld["wild"])))
        rows_json.append(mrow)

    P(f"[AB-A] 覆盖：对得上且录像过了 600 拍的 {n_valid} 局（到 900 拍的 {reach[900]} 局，到 1500 拍的 {reach[1500]} 局，到 3000 拍的 {reach[3000]} 局）；重演到 3000 拍为止")
    tot_ai = sum(dec[k][0][c][o] for k in range(len(WN)) for c in range(4) for o in range(3))
    tot_sh = sum(dec[k][1][c][o] for k in range(len(WN)) for c in range(4) for o in range(3))
    P(f"  内置 AI 走到「挑目标」这一步的决策 {tot_ai} 次，其中打真人 {sum(dec[k][0][c][2] for k in range(len(WN)) for c in range(4))} 次；空壳的决策 {tot_sh} 次，其中打真人 {sum(dec[k][1][c][2] for k in range(len(WN)) for c in range(4))} 次")
    if send_frac:
        P(f"  内置 AI 打真人时派出的兵 ÷ 自己的余额：P10 / P50 / P90 = {fmt(q(send_frac, .1), 2)} / {fmt(q(send_frac, .5), 2)} / {fmt(q(send_frac, .9), 2)}；"
          f"同一个 AI 相邻两次打真人隔的拍数 P25 / P50 / P75 = {fmt(q(gap, .25))} / {fmt(q(gap, .5))} / {fmt(q(gap, .75))}（{len(gap)} 个间隔）")
    P()

    P("[AB-B] 内置 AI 的决策：过滤前抽到的候选是什么构成 → 最后打了谁（引擎：先打无主地；否则有 AI / 空壳在候选里时 97% 只在它们里面挑）")
    P("  窗 | 决策数 | 候选里有无主地：占决策的比例（其中打无主地） | 只有 AI / 空壳：占比 | 只有真人：占比（其中打真人） | 真人和 AI / 空壳都有：占比（其中打真人）")
    def dec_row(name, ks, a=0):
        d = [[sum(dec[k][a][c][o] for k in ks) for o in range(3)] for c in range(4)]
        n = sum(sum(x) for x in d)
        if not n:
            return f"    {name} | 0"
        return (f"    {name} | {n} | {pct(sum(d[0]), n)}（{pct(d[0][0], sum(d[0]))}） | {pct(sum(d[1]), n)} | "
                f"{pct(sum(d[2]), n)}（{pct(d[2][2], sum(d[2]))}） | {pct(sum(d[3]), n)}（{pct(d[3][2], sum(d[3]), 1)}）")
    for k in range(len(WN)):
        P(dec_row(WN[k], [k]))
    P(dec_row("600~1500 合计", [0, 1, 2]))
    P(dec_row("1500~3000 合计", [3, 4, 5]))
    d_all = [[sum(dec[k][0][c][o] for k in range(len(WN))) for o in range(3)] for c in range(4)]
    hum = sum(d_all[c][2] for c in range(4))
    P(f"  打真人的 {hum} 次里：候选只有真人的 {d_all[2][2]} 次（{pct(d_all[2][2], hum)}）；候选里还有 AI / 空壳的 {d_all[3][2]} 次（{pct(d_all[3][2], hum)}）；候选里有无主地的 {d_all[0][2]} 次")
    P()

    P("[AB-C] 在几个真人里挑：最后那份候选名单里真人 ≥2 个的那些次（名单 = 引擎真正在里面挑的，已经去掉了正在打的）")
    for a, an in ((0, "内置 AI（难度 0）"), (1, "空壳（难度 6）")):
        S = sel[a]
        n = S["n"]
        if not n:
            P(f"  {an}：0 次")
            continue
        P(f"  {an}：{n} 次；候选真人数 2 / 3 / 4 / ≥5 个的 {S['k'][2]} / {S['k'][3]} / {S['k'][4]} / {S['k'][5]} 次")
        P(f"    挑中的是包围盒中心最近的那个：{pct(S['nearest'], n)}；是「余额 + 压在它身上的兵」最小的那个：{pct(S['weakest'], n)}；是兵密度最低的那个：{pct(S['thinnest'], n)}；"
          f"瞎挑会有的比例（Σ 1/候选数 ÷ 次数）：{pct(S['chance'], n)}")
        if S["mixed"]:
            P(f"    候选里 own 和野人都有的 {S['mixed']} 次：挑中 own 的 {pct(S['mixed_own'], S['mixed'])}；按人头瞎挑会有 {pct(S['mixed_exp'], S['mixed'])}；"
              f"这些次里 own 候选的余额比野人候选高的 {pct(S['mixed_own_stronger'], S['mixed'])}，兵密度比野人高的 {pct(S['mixed_own_denser'], S['mixed'])}")
    P()

    P("[AB-D] 真人被内置 AI 咬（人头 = 窗首在线、有地的席位；被咬 = 窗内内置 AI 从这个号身上吃到的格，逐对战损账的真值）")
    P("  窗 | 组 | 人头 | 窗首人均地 | 窗首兵密度 | 每人被 AI 出手的次数 | 每人被 AI 咬走的格 | 占窗首地的比例 | 每人被 AI 打掉的余额 | AI 每烧 1 兵打掉的余额 | 每人被空壳咬走的格")
    out_ph = {}
    for k in range(len(WN)):
        for g in GROUPS:
            r = ph[k][g]
            h = r["heads"]
            if not h:
                continue
            out_ph[f"{WN[k]}|{g}"] = dict(r)
            P(f"    {WN[k]} | {GN[g]} | {int(h)} | {fmt(r['land'] / h)} | {fmt(r['bal'] / max(1, r['land']), 1)} | {fmt(r['bites'] / h, 2)} | {fmt(r['cells'] / h)} | {pct(r['cells'], r['land'], 1)} | "
              f"{fmt(r['dB'] / h)} | {fmt(r['dB'] / max(1, r['burnt']), 2)} | {fmt(r['scells'] / h)}")
    for name, ks in (("600~1500 合计", [0, 1, 2]), ("1500~3000 合计", [3, 4, 5])):
        for g in ("own", "wild"):
            h0 = ph[ks[0]][g]["heads"]
            cells = sum(ph[k][g]["cells"] for k in ks)
            dB = sum(ph[k][g]["dB"] for k in ks)
            bites = sum(ph[k][g]["bites"] for k in ks)
            sc = sum(ph[k][g]["scells"] for k in ks)
            if h0:
                P(f"    {name} | {GN[g]} | 窗首人头 {int(h0)} | 每人被 AI 出手 {fmt(bites / h0, 2)} 次、被咬走 {fmt(cells / h0)} 格、被打掉 {fmt(dB / h0)} 兵；被空壳咬走 {fmt(sc / h0)} 格")
    P("  逐局（own ≥3 人头、野人 ≥5 人头的局；每局先各自算人均，再取各局的中位）：窗 | 局数 | own 每人被咬走的格 中位 | 野人 中位 | own 占窗首地的比例 中位 | 野人 中位 | own 人均被咬得比野人多的局 / 少的局（双侧符号检验 p）")
    for k in range(len(WN)):
        v = per_match[k]
        if not v:
            continue
        more = sum(1 for x in v if x[0] > x[1])
        less = sum(1 for x in v if x[0] < x[1])
        P(f"    {WN[k]} | {len(v)} | {fmt(q([x[0] for x in v], .5))} | {fmt(q([x[1] for x in v], .5))} | {fmt(100 * q([x[2] for x in v], .5), 2)}% | {fmt(100 * q([x[3] for x in v], .5), 2)}% | {more} / {less}（p={fp(sign_p(more, more + less))}）")
    P()

    P("[AB-E] 一口的战果和目标兵密度（内置 AI 打真人；战果 = 这一对从这次出手到下一次出手、最多 150 拍的逐对战损）")
    P("  组 | 目标兵密度 | 口数 | 一格没咬到的 | 每口咬走的格 | AI 每派 1000 兵咬走的格 | 目标每丢 1 格被打掉的余额 | AI 每烧 1 兵打掉目标的余额")
    out_eff = {}
    for g in ("own", "wild"):
        for bi, bn in enumerate(DBN):
            e = eff[0][g][bi]
            if not e["n"]:
                continue
            out_eff[f"{g}|{bn}"] = dict(e)
            P(f"    {GN[g]} | {bn} | {int(e['n'])} | {pct(e['zero'], e['n'])} | {fmt(e['cells'] / e['n'])} | {fmt(1000 * e['cells'] / max(1, e['dn']))} | "
              f"{fmt(e['dB'] / max(1, e['cells']), 1)} | {fmt(e['dB'] / max(1, e['burnt']), 2)}")
    for g in ("own", "wild"):
        n = sum(eff[0][g][bi]["n"] for bi in range(len(DBINS)))
        cells = sum(eff[0][g][bi]["cells"] for bi in range(len(DBINS)))
        dB = sum(eff[0][g][bi]["dB"] for bi in range(len(DBINS)))
        burnt = sum(eff[0][g][bi]["burnt"] for bi in range(len(DBINS)))
        zero = sum(eff[0][g][bi]["zero"] for bi in range(len(DBINS)))
        if n:
            P(f"  {GN[g]} 合计：{int(n)} 口，一格没咬到的 {pct(zero, n)}，每口咬走 {fmt(cells / n)} 格，目标每丢 1 格被打掉 {fmt(dB / max(1, cells), 1)} 余额，AI 每烧 1 兵打掉 {fmt(dB / max(1, burnt), 2)} 余额")
    for g in ("own", "wild"):
        v = bite_frac[g]
        if v:
            P(f"  {GN[g]}：600~1500 拍一口咬走的格 ÷ 目标当时的地：P50 / P90 / P99 / 最大 = {fmt(100 * q(v, .5), 1)}% / {fmt(100 * q(v, .9), 1)}% / {fmt(100 * q(v, .99), 1)}% / {fmt(100 * max(v), 1)}%（{len(v)} 口）")
    P()

    P("[AB-G] 目标正压着这只 AI 的时候挨的那一口（内置 AI 打真人；「压着」= AI 出手那一拍，目标压在它身上的兵 > 0）")
    P("  引擎 expandAttack：新发起的进攻第一圈，目标没有兵压在进攻方身上时（counter = 0）不够兵也算赢（赊账）；目标有兵压着就得真付得起。")
    P("  组·压没压着 | 目标兵密度档：口数 / 一格没咬到 / 每口咬走的格 / 每口圈数 / AI 每 1000 兵咬走的格 / 目标每口被打掉的余额")
    out_ctr = {}
    for g in ("own", "wild"):
        for has in (0, 1):
            cells_ = []
            tot = defaultdict(float)
            for bi, bn in enumerate(DBN):
                c_ = ctrs[g][has][bi]
                for k_, v_ in c_.items():
                    tot[k_] += v_
                if c_["n"] < 20:
                    cells_.append(f"{bn}：{int(c_['n'])} 口（太少）")
                    continue
                cells_.append(f"{bn}：{int(c_['n'])} / {pct(c_['zero'], c_['n'])} / {fmt(c_['cells'] / c_['n'])} / {fmt(c_['rings'] / c_['n'], 1)} / "
                              f"{fmt(1000 * c_['cells'] / max(1, c_['dn']))} / {fmt(c_['dB'] / c_['n'])}")
                out_ctr[f"{g}|{has}|{bn}"] = dict(c_)
            P(f"  {GN[g]}·{'压着' if has else '没压着'} | " + "｜".join(cells_))
            if tot["n"]:
                P(f"    合计 {int(tot['n'])} 口：一格没咬到 {pct(tot['zero'], tot['n'])}，每口咬走 {fmt(tot['cells'] / tot['n'])} 格、{fmt(tot['rings'] / tot['n'], 1)} 圈，"
                  f"AI 每 1000 兵咬走 {fmt(1000 * tot['cells'] / max(1, tot['dn']))} 格，目标每口被打掉 {fmt(tot['dB'] / tot['n'])} 余额"
                  + (f"，目标压在 AI 身上的兵每口平均 {fmt(tot['ctr'] / tot['n'])}" if has else ""))
                out_ctr[f"{g}|{has}|all"] = dict(tot)
    P()

    P("[AB-F] 空壳（离开的真人）的决策和战果")
    P("  窗 | 决策数 | 候选里有无主地：占比（其中打无主地） | 只有 AI / 空壳：占比 | 只有真人：占比（其中打真人） | 真人和 AI / 空壳都有：占比（其中打真人）")
    P(dec_row("600~1500 合计", [0, 1, 2], 1))
    P(dec_row("1500~3000 合计", [3, 4, 5], 1))
    for g in ("own", "wild"):
        n = sum(eff[1][g][bi]["n"] for bi in range(len(DBINS)))
        cells = sum(eff[1][g][bi]["cells"] for bi in range(len(DBINS)))
        dn = sum(eff[1][g][bi]["dn"] for bi in range(len(DBINS)))
        dB = sum(eff[1][g][bi]["dB"] for bi in range(len(DBINS)))
        if n:
            P(f"  空壳打 {GN[g]}：{int(n)} 口，每口派 {fmt(dn / n)} 兵、咬走 {fmt(cells / n)} 格、打掉 {fmt(dB / n)} 余额")

    txt = "\n".join(lines) + "\n"
    os.makedirs(os.path.join(OUT, "_cross"), exist_ok=True)
    with open(os.path.join(OUT, "_cross", "aibite.txt"), "w", encoding="utf-8") as f:
        f.write(txt)
    with open(os.path.join(OUT, "_cross", "aibite.json"), "w", encoding="utf-8") as f:
        json.dump(dict(matches=n_valid, dec=dec, sel={str(a): {k: (dict(v) if isinstance(v, Counter) else v) for k, v in sel[a].items()} for a in sel},
                       perHead=out_ph, eff=out_eff, counter=out_ctr, rows=rows_json), f, ensure_ascii=False, indent=1)
    if quiet:
        print(f"aibite: {n_valid} 局 → out/_cross/aibite.txt")
    else:
        print(txt)


if __name__ == "__main__":
    main()
