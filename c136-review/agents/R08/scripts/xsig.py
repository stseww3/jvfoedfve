#!/usr/bin/env python3
"""xsig.py — 跨局头条结论的显著性（发现集）。只读 out/_cross/ 里 xscan / xtruth / xdose 的 JSON（先跑那三个脚本），不碰数据包。

    python3 xsig.py [--quiet]        → out/_cross/xsig.txt、xsig.json

节：
  [XG-A] 逐局符号检验：同一局里 own 对 野人（或 own 的 1500 拍对 630 拍），双侧二项
  [XG-B] 秩相关的置换检验（Spearman；5000 次置换，固定种子 136）
  [XG-C] 赢的局 vs 没赢的局：xscan 每个模式命中率的 Fisher 精确检验（双侧）
  [XG-D] 赢的局 vs 没赢的局：剂量 / 结果的中位数之差，置换检验（5000 次，固定种子 136）
  [XG-E] 多重比较：本表一共做了多少个检验，Bonferroni 门槛是多少，过门槛的有哪些
口径提醒：这里的显著只说明「发现集里这个差别不像是抽样噪声」，不等于因果；因果要靠验证集复现（E3）和模拟器配对消融（E4）。
"""
import json
import math
import os
import random
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out", "_cross")
NPERM = 5000
SEED = 136


def rank(v):
    order = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def pearson(rx, ry):
    n = len(rx)
    mx, my = sum(rx) / n, sum(ry) / n
    sx = sum((a - mx) ** 2 for a in rx) ** 0.5
    sy = sum((b - my) ** 2 for b in ry) ** 0.5
    if sx == 0 or sy == 0:
        return None
    return sum((a - mx) * (b - my) for a, b in zip(rx, ry)) / (sx * sy)


def spearman_perm(x, y, rng):
    """返回 (rho, 置换 p)：p = (|rho_perm| ≥ |rho| 的次数 + 1) ÷ (置换次数 + 1)"""
    if len(x) < 8:
        return None, None
    rx, ry = rank(x), rank(y)
    rho = pearson(rx, ry)
    if rho is None:
        return None, None
    n = len(rx)
    mx, my = sum(rx) / n, sum(ry) / n
    dx = [a - mx for a in rx]
    dy = [b - my for b in ry]
    den = (sum(a * a for a in dx) * sum(b * b for b in dy)) ** 0.5
    hit = 0
    for _ in range(NPERM):
        rng.shuffle(dy)
        if abs(sum(a * b for a, b in zip(dx, dy)) / den) >= abs(rho) - 1e-12:
            hit += 1
    return rho, (hit + 1) / (NPERM + 1)


def sign_p(k, n):
    """双侧二项：n 局里有 k 局朝一个方向（平局先剔掉），p = min(1, 2·P(X ≥ max(k, n−k)))"""
    if n == 0:
        return None
    m = max(k, n - k)
    tail = sum(math.comb(n, i) for i in range(m, n + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def fisher_p(a, b, c, d):
    """2×2 表 [[a, b], [c, d]] 的双侧 Fisher 精确检验"""
    n1, n2, k, n = a + b, c + d, a + c, a + b + c + d
    if n1 == 0 or n2 == 0:
        return None

    def pr(x):
        return math.comb(n1, x) * math.comb(n2, k - x) / math.comb(n, k)

    p0 = pr(a)
    lo, hi = max(0, k - n2), min(k, n1)
    return min(1.0, sum(pr(x) for x in range(lo, hi + 1) if pr(x) <= p0 * (1 + 1e-9)))


def median_perm(u, v, rng):
    """两组中位数之差的置换检验（双侧）"""
    if len(u) < 3 or len(v) < 3:
        return None, None
    obs = statistics.median(u) - statistics.median(v)
    pool = list(u) + list(v)
    nu = len(u)
    hit = 0
    for _ in range(NPERM):
        rng.shuffle(pool)
        if abs(statistics.median(pool[:nu]) - statistics.median(pool[nu:])) >= abs(obs) - 1e-12:
            hit += 1
    return obs, (hit + 1) / (NPERM + 1)


def fp(p):
    if p is None:
        return "—"
    if p < 1e-4:
        return f"{p:.1e}"
    return f"{p:.4f}"


def main():
    quiet = "--quiet" in sys.argv
    XS = json.load(open(os.path.join(OUT, "xscan.json"), encoding="utf-8"))
    XT = json.load(open(os.path.join(OUT, "xtruth.json"), encoding="utf-8"))
    XD = json.load(open(os.path.join(OUT, "xdose.json"), encoding="utf-8"))
    rng = random.Random(SEED)
    rows = XD["rows"]
    full = [r for r in XT["matches"] if r.get("valid") and not r.get("spawnOnly")]
    out = []
    P = out.append
    tests = []    # (名字, p)

    # ---- [XG-A] ----
    P("[XG-A] 逐局符号检验（同一局里比两个数；平局剔掉；双侧二项）：比较 | 有数的局 | 朝这个方向的局 | p")

    def sign_row(name, pairs):
        pairs = [(a, b) for a, b in pairs if a is not None and b is not None and a != b]
        k = sum(1 for a, b in pairs if a < b)
        p = sign_p(k, len(pairs))
        P(f"  {name} | {len(pairs)} | {k} | {fp(p)}")
        tests.append((f"A|{name}", p))

    sign_row("人均对照 t=1500 比 t=630 低", [(d.get("R1500"), d.get("R630")) for d in rows])
    sign_row("人均对照 t=900 比 t=630 低", [(d.get("R900"), d.get("R630")) for d in rows])
    sign_row("t=630 的人均对照 高于 1（own 人均地多于野人）", [(1.0, d.get("R630")) for d in rows])
    sign_row("t=1500 的人均对照 低于 1", [(d.get("R1500"), 1.0) for d in rows])
    sign_row("(600,1500] AI 地份额对照 低于 1（own 吃到的份额小于人头份额）", [(d.get("AISHARE"), 1.0) for d in rows])
    ne = []
    for r in full:
        c = r["cmds"][1] if len(r["cmds"]) > 1 else None
        if c and c["own"]["land"] >= 20 and c["wild"]["land"] >= 20:
            ne.append((1 - c["wild"]["ok"] / c["wild"]["land"], 1 - c["own"]["ok"] / c["own"]["land"]))
    sign_row("600~1500 陆攻没生效占比：野人 低于 own", ne)
    sign_row("挨着白给的内置 AI 时 90 拍内出手的比例：own 低于 野人", [(d.get("ACT"), d.get("ACTW")) for d in rows])
    sign_row("打 AI 的生效陆攻每条派出占余额：own 低于 野人", [(d.get("SIZE"), d.get("SIZEW")) for d in rows])
    pph, cpp, t0r, gate = [], [], [], []
    for r in full:
        if r.get("pairs") and r.get("yield600_1500"):
            ho, hw = r["yield600_1500"]["own"]["heads"], r["yield600_1500"]["wild"]["heads"]
            o = [sum(r["pairs"]["own"][c][i] for c in ("alone", "mate", "wild")) for i in range(11)]
            w = [sum(r["pairs"]["wild"][c][i] for c in ("alone", "mate", "wild")) for i in range(11)]
            if ho >= 3 and hw >= 5 and o[0] >= 10 and w[0] >= 10:
                pph.append((o[0] / ho, w[0] / hw))
                cpp.append((o[4] / o[0], w[4] / w[0]))
                t0r.append((o[7] / o[0], w[7] / w[0]))
        ru = r.get("rule")
        if ru:
            go = sum(ru["own"]["cls"][c][2] for c in ru["own"]["cls"])
            gw = sum(ru["wild"]["cls"][c][2] for c in ru["wild"]["cls"])
            if go >= 20 and gw >= 20:
                gate.append((sum(ru["wild"]["cls"][c][2] for c in ("px", "dp", "sb")) / gw, sum(ru["own"]["cls"][c][2] for c in ("px", "dp", "sb")) / go))
    sign_row("600~1500 人均对几个内置 AI 下过手：own 低于 野人", pph)
    sign_row("每对（号 → AI）吃到的格：own 低于 野人", cpp)
    sign_row("下手时那个 AI 的地：own 低于 野人", t0r)
    sign_row("白给样本里被留底规则挡住的占比（同一把尺子）：野人 低于 own", gate)

    # ---- [XG-B] ----
    P("")
    P(f"[XG-B] 秩相关的置换检验（Spearman；{NPERM} 次置换，种子 {SEED}）：两个量 | 局数 | rho | p")

    def corr_row(name, sel, a, b):
        pr = [(d[a], d[b]) for d in sel if d.get(a) is not None and d.get(b) is not None]
        rho, p = spearman_perm([x for x, _ in pr], [y for _, y in pr], rng) if len(pr) >= 8 else (None, None)
        P(f"  {name} | {len(pr)} | {'—' if rho is None else f'{rho:.2f}'} | {fp(p)}")
        tests.append((f"B|{name}", p))

    for a, an in (("A", "成批占比"), ("B", "没生效占比"), ("C", "没落地占比")):
        for b in ("R1500", "AISHARE"):
            corr_row(f"卡顿剂量 {a}（{an}）× {b}", rows, a, b)
    for b in ("R1500", "AISHARE"):
        corr_row(f"ACT（挨着白给的 AI 出手率）× {b}", rows, "ACT", b)
        corr_row(f"ALLOWHIT（规则放行后出手率）× {b}", rows, "ALLOWHIT", b)
        corr_row(f"GATE（被留底挡住的占比）× {b}", rows, "GATE", b)
        corr_row(f"SB（被 AI 仇恨项挡住的占比）× {b}", rows, "SB", b)
    corr_row("GATE × ACT", rows, "GATE", "ACT")
    corr_row("GATE × 卡顿剂量 B（两层是否独立）", rows, "GATE", "B")
    corr_row("DENS1500（兵密度对照）× R1500", rows, "DENS1500", "R1500")
    corr_row("EDGE（贴边比例）× R1500", rows, "EDGE", "R1500")
    corr_row("EDGE × AISHARE", rows, "EDGE", "AISHARE")
    corr_row("H（房间真人数）× R1500", rows, "H", "R1500")
    corr_row("H × AISHARE", rows, "H", "AISHARE")
    corr_row("R630 × R1500", rows, "R630", "R1500")
    calm = [d for d in rows if d.get("B") is not None and d["B"] <= 0.05]
    for b in ("ACT", "AISHARE", "R1500"):
        corr_row(f"几乎不卡的局里 GATE × {b}", calm, "GATE", b)
    sq20 = [d for d in rows if d["cohort"] == "squad20"]
    sq10 = [d for d in rows if d["cohort"] == "squad10"]
    for nm, sel in (("squad10", sq10), ("squad20", sq20)):
        corr_row(f"{nm}：卡顿剂量 B × R1500", sel, "B", "R1500")
        corr_row(f"{nm}：GATE × AISHARE", sel, "GATE", "AISHARE")

    # ---- [XG-C] ----
    P("")
    P(f"[XG-C] 赢的局（{XS['won']}）vs 没赢的局（{XS['lost']}）：xscan 模式命中率的 Fisher 精确检验（双侧；只列 p<0.10 的，其余见 xsig.json）：模式 | 赢的局命中 | 没赢的局命中 | p")
    fish = {}
    for pid, a in XS["agg"].items():
        w, l = a.get("wonHit"), a.get("lostHit")
        if w is None or l is None:
            continue
        p = fisher_p(w, a["won"] - w, l, a["lost"] - l)
        fish[pid] = dict(wonHit=w, won=a["won"], lostHit=l, lost=a["lost"], p=p)
        tests.append((f"C|{pid}", p))
    for pid, f in sorted(fish.items(), key=lambda kv: kv[1]["p"] if kv[1]["p"] is not None else 9):
        if f["p"] is not None and f["p"] < 0.10:
            P(f"  {pid} | {f['wonHit']}/{f['won']}（{100 * f['wonHit'] / f['won']:.0f}%） | {f['lostHit']}/{f['lost']}（{100 * f['lostHit'] / f['lost']:.0f}%） | {fp(f['p'])}")

    # ---- [XG-D] ----
    P("")
    P(f"[XG-D] 赢的局 vs 没赢的局：中位数之差的置换检验（双侧；{NPERM} 次，种子 {SEED}）：量 | 赢的局 中位（局数） | 没赢的局 中位（局数） | 差 | p")
    for k, nm in (("A", "成批占比"), ("B", "没生效占比"), ("C", "没落地占比"), ("R630", "t=630 人均对照"), ("R1500", "t=1500 人均对照"), ("AISHARE", "AI 地份额对照"),
                  ("ACT", "挨着白给的 AI 出手率"), ("ALLOWHIT", "规则放行后出手率"), ("GATE", "被留底挡住的占比"), ("EDGE", "贴边比例"), ("DENS1500", "兵密度对照"), ("H", "房间真人数")):
        u = [d[k] for d in rows if d["won"] and d.get(k) is not None]
        v = [d[k] for d in rows if not d["won"] and d.get(k) is not None]
        obs, p = median_perm(u, v, rng)
        P(f"  {k}（{nm}） | {statistics.median(u):.2f}（{len(u)}） | {statistics.median(v):.2f}（{len(v)}） | {'—' if obs is None else f'{obs:+.2f}'} | {fp(p)}")
        tests.append((f"D|{k}", p))

    # ---- [XG-E] ----
    done = [(n, p) for n, p in tests if p is not None]
    thr = 0.05 / max(1, len(done))
    P("")
    P(f"[XG-E] 多重比较：本表一共 {len(done)} 个检验，Bonferroni 门槛 0.05 ÷ {len(done)} = {thr:.5f}；置换检验能给出的最小 p 是 1 ÷ {NPERM + 1} = {1 / (NPERM + 1):.5f}")
    ok = [n for n, p in done if p <= thr]
    P(f"  过门槛的 {len(ok)} 个：" + "；".join(n.split("|", 1)[1] for n in ok))
    weak = [f"{n.split('|', 1)[1]}（p={fp(p)}）" for n, p in done if thr < p < 0.05]
    P(f"  p<0.05 但没过门槛的 {len(weak)} 个：" + "；".join(weak))

    with open(os.path.join(OUT, "xsig.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    with open(os.path.join(OUT, "xsig.json"), "w", encoding="utf-8") as f:
        json.dump(dict(nperm=NPERM, seed=SEED, tests=[dict(name=n, p=p) for n, p in tests], fisher=fish, bonferroni=thr), f, ensure_ascii=False, separators=(",", ":"))
    if not quiet:
        print("\n".join(out))


if __name__ == "__main__":
    main()
