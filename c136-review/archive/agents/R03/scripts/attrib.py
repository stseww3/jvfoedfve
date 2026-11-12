#!/usr/bin/env python3
"""attrib.py — 会审提案第二部分（历史失分机制的纯离线定量归因）用的三张表。只读已有缓存，不重跑重放。

  [AT-1] 600~1500 拍「转化」这一层的逐号面板：同一局里，哪个号的转化低，和它的延迟、目标已死、冻结、没有 AI 邻居、
         名下格数各自的局内秩相关（局内比较，去掉了房间大小、地图这些局间差别）。
  [AT-2] 出生份额这一层的经验版本：同一局里其他真人「名下格数 → 1500 拍的地」的关系，套到编队每个号的名下格数上，
         得到「名下一样大的其他真人该有多少地」，再看编队实际拿到它的几成。要 scripts/cells.mjs 的输出。
  [AT-3] 延迟的来源里能在离线排除的一条：策略自己每拍算多久（HL-TICK 的 avgMs / maxMs / skip）。

  输入：out/cache/<局>-{resim,shadow,freeze}.json、out/dossier/<局>-{land,delay}-facts.json、out/council/cells/<局>.json 或 out/council/cells-py/<局>.json、
        bundles/<局>/traj.csv、manifest.jsonl（发现集）
  输出：out/council/ATTR-facts.txt

用法：timeout 120 python3 scripts/attrib.py
"""
import csv
import json
import math
import os
import random
import statistics
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
OUT = os.path.join(ROOT, "out")
DATA = os.environ.get("C136_DATA", "/agent/repos/c136-data")
MIDS = "A051 A087 A066 A025 A045 A067 A071 A090 A042 A046 A041".split()
WIN = "A025"
NEUTRAL = 512
SEED = 136
NPERM = 5000

_cache = {}


def J(path):
    if path not in _cache:
        with open(path, encoding="utf8") as f:
            _cache[path] = json.load(f)
    return _cache[path]


def resim(m): return J(os.path.join(OUT, "cache", f"{m}-resim.json"))
def shadow(m): return J(os.path.join(OUT, "cache", f"{m}-shadow.json"))
def freeze(m): return J(os.path.join(OUT, "cache", f"{m}-freeze.json"))
def landf(m): return J(os.path.join(OUT, "dossier", f"{m}-land-facts.json"))
def delayf(m): return J(os.path.join(OUT, "dossier", f"{m}-delay-facts.json"))


CELL_SRC = {}


def cells(m):
    # 先用 cells.mjs 的输出（质心口径，要重计算位）；没有就用 cells_py.py 的输出（包围盒中心口径，不用 node）
    for sub in ("cells", "cells-py"):
        p = os.path.join(OUT, "council", sub, f"{m}.json")
        if os.path.exists(p):
            CELL_SRC[m] = sub
            return J(p)
    return None


def med(xs):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def ranks(v):
    order = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2.0 + 1
        i = j + 1
    return r


def pearson(a, b):
    n = len(a)
    if n < 3:
        return None
    ma, mb = sum(a) / n, sum(b) / n
    sa = sum((x - ma) ** 2 for x in a); sb = sum((y - mb) ** 2 for y in b)
    if sa <= 0 or sb <= 0:
        return None
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(sa * sb)


def zrank(v):
    """局内秩 → 减去均值、除以无并列时的标准差。"""
    n = len(v)
    r = ranks(v)
    mu = (n + 1) / 2.0
    sd = math.sqrt((n * n - 1) / 12.0)
    return [(x - mu) / sd for x in r]


def within_corr(groups, nperm=NPERM, seed=SEED):
    """groups: [(xs, ys)]，每个元素是一局里的号。返回 (局内秩相关, 号数, 局数, 置换 p)。置换 = 每局内部打乱 x。"""
    gs = [(zrank(xs), zrank(ys)) for xs, ys in groups if len(xs) >= 4]
    if not gs:
        return None, 0, 0, None
    ax = [x for g in gs for x in g[0]]; ay = [y for g in gs for y in g[1]]
    r = pearson(ax, ay)
    if r is None:
        return None, len(ax), len(gs), None
    rnd = random.Random(seed)
    hit = 0
    for _ in range(nperm):
        px = []
        for zx, _zy in gs:
            s = zx[:]
            rnd.shuffle(s)
            px.extend(s)
        rr = pearson(px, ay)
        if rr is not None and abs(rr) >= abs(r) - 1e-12:
            hit += 1
    return r, len(ax), len(gs), (hit + 1) / (nperm + 1)


def fp(p):
    if p is None:
        return "—"
    return "p<0.001" if p < 0.001 else f"p={p:.3f}"


def fr(r):
    return "—" if r is None else f"{r:+.2f}"


L = []


def w(s=""):
    L.append(s)


# ---------------------------------------------------------------- AT-1
FACTORS = [
    ("cells", "名下格数"),
    ("conv630", "630 拍 地÷名下"),
    ("lag", "600~1500 成交延迟中位"),
    ("dead", "600~1500 目标已死占陆攻"),
    ("frozen", "600~1500 冻结占决策拍"),
    ("frozenSq", "其中卡在编队友"),
    ("noai", "600~1500 没有 AI 邻居占决策拍"),
    ("target", "600~1500 有目标并发令占决策拍"),
]
OUTCOMES = [
    ("conv", "1500 拍 地÷名下"),
    ("growth", "1500 拍地 ÷ 630 拍地"),
    ("spendShare", "630~1500 送去打 AI+中立的兵 ÷ 利息"),
    ("dens", "1500 拍 兵÷地"),
]


def panel_rows():
    rows = []
    for m in MIDS:
        R = resim(m); S = shadow(m); LF = landf(m); DF = delayf(m); FZ = freeze(m)
        H = R["H"]
        cap = {c["t"]: c for c in LF["capture"]}
        idx = {t: i for i, t in enumerate(R["snapT"])}
        i630, i1500 = idx[630], idx[1500]
        spend = Counter()
        for c in R["cmdLog"]:
            if c[2] == 1 and c[5] == 1 and c[4] >= H and 630 <= c[0] < 1500:
                spend[c[1]] += c[6]
        for bot, s in R["squad"].items():
            p = s["id"]
            if p < 0:
                continue
            pb0 = cap[630]["perBot"].get(bot); pb1 = cap[1500]["perBot"].get(bot)
            if not pb0 or not pb1 or pb0["terr"] <= 0 or pb1["terr"] <= 0:
                continue
            if 0 <= R["leftT"][p] < 1500 or 0 <= R["deathT"][p] < 1500:
                continue
            cl = LF["voronoi"]["perBot"][bot]["cells"]
            lg = DF["lag"]["byBot"].get(bot)
            lag = lg[1]["p50"] if lg and lg[1]["n"] else None
            fz = FZ["bots"].get(bot)
            natk = ndead = 0
            for pr in S["bots"][bot]["match"]["pairs"]:
                if pr[2] == 1 and pr[1] >= 0 and 600 <= pr[1] < 1500 and pr[7] != NEUTRAL:
                    natk += 1
                    if pr[4] == NEUTRAL:
                        ndead += 1
            inc = R["snapInc"][i1500][p] - R["snapInc"][i630][p]
            rows.append({
                "m": m, "bot": bot, "cells": cl, "L630": pb0["terr"], "L1500": pb1["terr"],
                "conv": pb1["terr"] / cl, "conv630": pb0["terr"] / cl, "growth": pb1["terr"] / pb0["terr"],
                "lag": lag, "dead": (ndead / natk) if natk >= 3 else None,
                "frozen": fz["frozen"] / fz["ticks"] if fz and fz["ticks"] else None,
                "frozenSq": fz["frozenBy"]["squad"] / fz["ticks"] if fz and fz["ticks"] else None,
                "noai": fz["noai"] / fz["ticks"] if fz and fz["ticks"] else None,
                "target": fz["target"] / fz["ticks"] if fz and fz["ticks"] else None,
                "spendShare": spend[p] / inc if inc > 0 else None,
                "dens": R["snapBal"][i1500][p] / pb1["terr"],
            })
    return rows


def at1():
    rows = panel_rows()
    w("[AT-1] 600~1500 拍转化层的逐号面板（局内比较）")
    w(f"面板：{len(rows)} 个号（11 局里 1500 拍仍在控、有地的编队号）。每个量先在局内排秩，再把 11 局的局内秩并在一起算相关；p 值 = 每局内部打乱 {NPERM} 次（种子 {SEED}）。")
    w("[AT-1a] 各局的号数与各量的局内中位（最小~最大）")
    w("局 | 号数 | 名下格数 | 630 拍 地÷名下 | 1500 拍 地÷名下 | 成交延迟中位（拍） | 目标已死占陆攻 | 冻结占决策拍 | 没有 AI 邻居占决策拍 | 630~1500 打 AI+中立 ÷ 利息 | 1500 拍 兵÷地")
    by = defaultdict(list)
    for r in rows:
        by[r["m"]].append(r)

    def rng(rs, k, f):
        v = [r[k] for r in rs if r[k] is not None]
        if not v:
            return "—"
        return f"{f(med(v))}（{f(min(v))}~{f(max(v))}）"

    for m in MIDS:
        rs = by[m]
        w(f"{m} | {len(rs)} | {rng(rs, 'cells', lambda x: f'{x:,.0f}')} | {rng(rs, 'conv630', lambda x: f'{x:.2f}')} | {rng(rs, 'conv', lambda x: f'{x:.2f}')} | {rng(rs, 'lag', lambda x: f'{x:.0f}')} | "
          f"{rng(rs, 'dead', lambda x: f'{100 * x:.0f}%')} | {rng(rs, 'frozen', lambda x: f'{100 * x:.0f}%')} | {rng(rs, 'noai', lambda x: f'{100 * x:.0f}%')} | {rng(rs, 'spendShare', lambda x: f'{100 * x:.1f}%')} | {rng(rs, 'dens', lambda x: f'{x:.0f}')}")
    w("[AT-1b] 局内秩相关（行 = 可能的原因，列 = 结果；每格：相关 号数/局数 p）")
    w("原因 \\ 结果 | " + " | ".join(o[1] for o in OUTCOMES))
    npairs = 0
    table = {}
    for fk, fname in FACTORS:
        cells_ = []
        for ok, _ in OUTCOMES:
            groups = []
            for m in MIDS:
                xs, ys = [], []
                for r in by[m]:
                    if r[fk] is None or r[ok] is None:
                        continue
                    xs.append(r[fk]); ys.append(r[ok])
                groups.append((xs, ys))
            r_, n, g, p = within_corr(groups)
            table[(fk, ok)] = (r_, n, g, p)
            npairs += 1
            cells_.append(f"{fr(r_)} {n}/{g} {fp(p)}")
        w(f"{fname} | " + " | ".join(cells_))
    thr = 0.05 / npairs
    passed = [f"{dict(FACTORS)[fk]} × {dict(OUTCOMES)[ok]}（{fr(v[0])}）" for (fk, ok), v in table.items() if v[3] is not None and v[3] < thr]
    w(f"  同时检验 {npairs} 对，Bonferroni 门槛 {thr:.4f}；过线的：" + ("；".join(passed) if passed else "无"))
    # 去掉胜局
    w("[AT-1c] 只用 10 个输局（去掉 A025）时，结果列「1500 拍 地÷名下」的局内秩相关")
    cells_ = []
    for fk, fname in FACTORS:
        groups = []
        for m in MIDS:
            if m == WIN:
                continue
            xs, ys = [], []
            for r in by[m]:
                if r[fk] is None:
                    continue
                xs.append(r[fk]); ys.append(r["conv"])
            groups.append((xs, ys))
        r_, n, g, p = within_corr(groups)
        cells_.append(f"{fname} {fr(r_)}（{n}/{g}，{fp(p)}）")
    w("  " + "；".join(cells_))
    # 控制名下格数与 630 拍转化之后
    w("[AT-1d] 控制「名下格数」之后的局内偏秩相关（结果 = 1500 拍 地÷名下；先把原因和结果各自对名下格数的局内秩做回归取残差）")
    cells_ = []
    pvals = []
    for fk, fname in FACTORS:
        if fk in ("cells",):
            continue
        ax, ay = [], []
        gs = []
        for m in MIDS:
            rs = [r for r in by[m] if r[fk] is not None]
            if len(rs) < 5:
                continue
            zc = zrank([r["cells"] for r in rs]); zx = zrank([r[fk] for r in rs]); zy = zrank([r["conv"] for r in rs])
            gs.append((zc, zx, zy))

        def resid(zc, z):
            b = sum(a * c for a, c in zip(z, zc)) / max(1e-12, sum(c * c for c in zc))
            return [a - b * c for a, c in zip(z, zc)]

        def stat(gs_):
            ax_, ay_ = [], []
            for zc, zx, zy in gs_:
                ax_.extend(resid(zc, zx)); ay_.extend(resid(zc, zy))
            return pearson(ax_, ay_), len(ax_)

        r_, n = stat(gs)
        rnd = random.Random(SEED)
        hit = 0
        for _ in range(NPERM):
            pg = []
            for zc, zx, zy in gs:
                # 在名下格数相近的号之间打乱很难做，这里打乱原因的残差
                rx = resid(zc, zx)
                rnd.shuffle(rx)
                pg.append((rx, resid(zc, zy)))
            a = [x for g in pg for x in g[0]]; b = [y for g in pg for y in g[1]]
            rr = pearson(a, b)
            if rr is not None and r_ is not None and abs(rr) >= abs(r_) - 1e-12:
                hit += 1
        pv = (hit + 1) / (NPERM + 1)
        cells_.append(f"{fname} {fr(r_)}（{n} 个号，{fp(pv)}）")
        pvals.append((fname, pv))
    w("  " + "；".join(cells_))
    thr = 0.05 / len(pvals)
    w(f"  同时检验 {len(pvals)} 对，Bonferroni 门槛 {thr:.4f}；过线的：" + ("；".join(f for f, pv in pvals if pv < thr) or "没有"))
    w("注：延迟按号取 600~1500 拍成交指令的延迟中位（没有成交的号不进这一格）；目标已死 = 这个号 600~1500 拍发出、成交了的打 AI/真人的陆攻里，落地时目标已经没地的占比（不足 3 条的不进）；")
    w("    冻结 / 没有 AI 邻居 / 有目标 是 freeze-scan.mjs 的决策拍分类（影子重跑口径，每 5 拍一个决策拍）。这是同一局里号与号的比较，不是反事实：邻居号的状态互相牵连，延迟高的号往往也是被冻住的号的邻居。")
    w()
    return rows


# ---------------------------------------------------------------- AT-2
def ols(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx <= 0:
        return None, None
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    return b, my - b * mx


def at2():
    w("[AT-2] 出生份额这一层的经验版本：其他真人「名下格数 → 1500 拍的地」")
    have = [m for m in MIDS if cells(m)]
    if len(have) < len(MIDS):
        w(f"  （缺 {len(MIDS) - len(have)} 局的名下格数，先跑 scripts/cells_py.py 或 scripts/cells.mjs）")
        w()
        return
    npy = sum(1 for m in MIDS if CELL_SRC.get(m) == "cells-py")
    w("口径：名下格数 = 每格陆地归直线距离最近的真人出生点（与 land-ledger.mjs 的出生份额同一算法）；其他真人 = 开局有地、不是编队号的真人席位；1500 拍的地取重放快照；1500 拍已经没地的记作出局。")
    w(f"名下格数的来源：cells.mjs（出生点取质心）{len(MIDS) - npy} 局，cells_py.py（出生点取包围盒中心）{npy} 局；后者与 land-facts 的逐号核对见 out/council/cells-py/_check.txt。")
    w("[AT-2a] 各局其他真人的名下格数与支撑范围")
    w("局 | 其他真人（开局有地） | 其中 1500 拍还有地 | 其他真人名下 中位（最小~最大） | 编队每号名下 中位（最小~最大） | 名下不大于编队最大那个号的其他真人：开局 / 1500 拍还有地 | 名下在编队中位 0.67~1.5 倍之间的：开局 / 1500 拍还有地")
    data = {}
    for m in MIDS:
        C = cells(m); R = resim(m)
        idx = {t: i for i, t in enumerate(R["snapT"])}
        i630, i1500 = idx[630], idx[1500]
        LF = landf(m)
        ctl = set(LF["capture"][[c["t"] for c in LF["capture"]].index(1500)]["perBot"].keys())
        sqid = {s["id"]: b for b, s in R["squad"].items() if s["id"] >= 0}
        others, squad = [], []
        for p in C["pts"]:
            rec = {"id": p["id"], "cells": p["cells"], "L630": R["snapTerr"][i630][p["id"]], "L1500": R["snapTerr"][i1500][p["id"]],
                   "left": 0 <= R["leftT"][p["id"]] < 1500}
            if p["squad"]:
                rec["bot"] = sqid.get(p["id"])
                rec["ctl"] = rec["bot"] in ctl
                squad.append(rec)
            else:
                others.append(rec)
        data[m] = (others, squad)
        oc = [o["cells"] for o in others]; sc = [s["cells"] for s in squad]
        smax, smed = max(sc), med(sc)
        le = [o for o in others if o["cells"] <= smax]
        near = [o for o in others if 0.67 * smed <= o["cells"] <= 1.5 * smed]
        alive = lambda v: sum(1 for o in v if o["L1500"] > 0)
        w(f"{m} | {len(others)} | {alive(others)} | {med(oc):,.0f}（{min(oc):,}~{max(oc):,}） | {smed:,.0f}（{min(sc):,}~{max(sc):,}） | {len(le)} / {alive(le)} | {len(near)} / {alive(near)}")
    # 回归：其他真人里 1500 拍还有地的，ln 地 对 ln 名下，局固定效应
    w("[AT-2b] 其他真人里 1500 拍还有地的人：ln(1500 拍的地) 对 ln(名下格数) 的斜率（斜率 1 = 地与名下成正比，三层恒等式第一层就是这个假设）")
    w("局 | 人数 | 斜率 | 秩相关")
    px, py = [], []
    per = {}
    for m in MIDS:
        others, _ = data[m]
        v = [(math.log(o["cells"]), math.log(o["L1500"])) for o in others if o["L1500"] > 0 and o["cells"] > 0]
        xs = [a for a, _ in v]; ys = [b for _, b in v]
        b, a = ols(xs, ys) if len(v) >= 6 else (None, None)
        rs = pearson(ranks(xs), ranks(ys)) if len(v) >= 6 else None
        per[m] = (b, a, xs, ys)
        w(f"{m} | {len(v)} | {'—' if b is None else f'{b:.2f}'} | {fr(rs)}")
        if len(v) >= 3:
            mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
            px.extend(x - mx for x in xs); py.extend(y - my for y in ys)
    bpool, _ = ols(px, py)
    # 按局自助法
    rnd = random.Random(SEED)
    ms = [m for m in MIDS if len(per[m][2]) >= 3]
    boots = []
    for _ in range(2000):
        sx, sy = [], []
        for _i in range(len(ms)):
            m = rnd.choice(ms)
            xs, ys = per[m][2], per[m][3]
            mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
            sx.extend(x - mx for x in xs); sy.extend(y - my for y in ys)
        b, _ = ols(sx, sy)
        if b is not None:
            boots.append(b)
    boots.sort()
    lo, hi = boots[int(0.025 * len(boots))], boots[int(0.975 * len(boots))]
    w(f"合并（每局各自减去均值后合在一起，{len(px)} 人）：斜率 {bpool:.2f}，按局重抽 2000 次的 95% 区间 {lo:.2f}~{hi:.2f}")
    # 输局合并
    lx, ly = [], []
    for m in MIDS:
        if m == WIN or len(per[m][2]) < 3:
            continue
        xs, ys = per[m][2], per[m][3]
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        lx.extend(x - mx for x in xs); ly.extend(y - my for y in ys)
    bl, _ = ols(lx, ly)
    w(f"只用 10 个输局：斜率 {bl:.2f}（{len(lx)} 人）")
    # 存活
    w("[AT-2c] 名下小的其他真人活不活得到 1500 拍：各局把其他真人按名下格数分成小的一半和大的一半")
    w("局 | 小的一半：人数 1500 拍还有地 | 大的一半：人数 1500 拍还有地")
    ts = [0, 0, 0, 0]
    for m in MIDS:
        others, _ = data[m]
        s = sorted(others, key=lambda o: o["cells"])
        h = len(s) // 2
        a, b = s[:h], s[h:]
        aa = sum(1 for o in a if o["L1500"] > 0); bb = sum(1 for o in b if o["L1500"] > 0)
        ts[0] += len(a); ts[1] += aa; ts[2] += len(b); ts[3] += bb
        w(f"{m} | {len(a)} {aa}（{100 * aa / max(1, len(a)):.0f}%） | {len(b)} {bb}（{100 * bb / max(1, len(b)):.0f}%）")
    w(f"合计 | {ts[0]} {ts[1]}（{100 * ts[1] / ts[0]:.0f}%） | {ts[2]} {ts[3]}（{100 * ts[3] / ts[2]:.0f}%）；同期 1500 拍前出局或离线的编队号见 [AT-2d] 的「在控」一列")
    # 套到编队
    w("[AT-2d] 把其他真人的关系套到编队每个号的名下格数上：1500 拍人均地比 = 经验出生层 × 剩余转化")
    w("  经验出生层 = 「名下和编队的号一样大的其他真人」按合并斜率推出来的人均地 ÷ 其他真人实际人均地（都只算 1500 拍还有地的）；剩余转化 = 编队实际人均地 ÷ 这个推出来的人均地。")
    w(f"  推法：ln 地 = 本局截距 + {bpool:.2f} × ln 名下（截距取本局其他真人的均值点），再乘上本局残差的指数均值把对数回归的偏差修掉。恒等式那两列是 X2 的口径（出生份额 × 转化），放在一起对照。")
    w("局 | 编队在控号数 | 人均地比 1500（本表口径） | 经验出生层 | 剩余转化 | 恒等式：出生份额 | 恒等式：转化 | 编队的名下是否落在其他真人的名下范围里（低于其他真人最小值的号数）")
    g1, g2, g0, n = 0.0, 0.0, 0.0, 0
    for m in MIDS:
        others, squad = data[m]
        b, a, xs, ys = per[m]
        if len(xs) < 3:
            w(f"{m} | —")
            continue
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        smear = sum(math.exp(y - (my + bpool * (x - mx))) for x, y in zip(xs, ys)) / len(xs)
        sq = [s for s in squad if s.get("ctl") and s["L1500"] > 0]
        exp_ = [math.exp(my + bpool * (math.log(s["cells"]) - mx)) * smear for s in sq]
        oth_mean = sum(math.exp(y) for y in ys) / len(ys)
        act = sum(s["L1500"] for s in sq) / len(sq)
        e = sum(exp_) / len(exp_)
        ratio = act / oth_mean
        l1, l2 = e / oth_mean, act / e
        omin = min(o["cells"] for o in others if o["L1500"] > 0)
        below = sum(1 for s in sq if s["cells"] < omin)
        TL = None
        try:
            rv = J(os.path.join(ROOT, "reviews", f"{m}.json"))["latencyAndLand"]["threeLayer"]
            TL = (rv["cellsPerHeadSquad"] / rv["cellsPerHeadOthers"], rv["convSquad"] / rv["convOthers"])
        except Exception:
            pass
        w(f"{m} | {len(sq)} | {ratio:.2f} | {l1:.2f} | {l2:.2f} | {'—' if not TL else f'{TL[0]:.2f}'} | {'—' if not TL else f'{TL[1]:.2f}'} | {below}/{len(sq)}")
        if m != WIN:
            g1 += math.log(l1); g2 += math.log(l2); g0 += math.log(ratio); n += 1
    w(f"10 个输局的几何平均：人均地比 {math.exp(g0 / n):.2f} = 经验出生层 {math.exp(g1 / n):.2f} × 剩余转化 {math.exp(g2 / n):.2f}")

    def split(slope):
        a1 = a2 = 0.0
        k = 0
        for m in MIDS:
            if m == WIN:
                continue
            others, squad = data[m]
            _b, _a, xs, ys = per[m]
            if len(xs) < 3:
                continue
            mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
            smear = sum(math.exp(y - (my + slope * (x - mx))) for x, y in zip(xs, ys)) / len(xs)
            sq = [s_ for s_ in squad if s_.get("ctl") and s_["L1500"] > 0]
            e = sum(math.exp(my + slope * (math.log(s_["cells"]) - mx)) * smear for s_ in sq) / len(sq)
            oth_mean = sum(math.exp(y) for y in ys) / len(ys)
            act = sum(s_["L1500"] for s_ in sq) / len(sq)
            a1 += math.log(e / oth_mean); a2 += math.log(act / e); k += 1
        return math.exp(a1 / k), math.exp(a2 / k), a1 / (a1 + a2)

    parts = []
    for name, sl in (("合并斜率", bpool), ("区间下端", lo), ("区间上端", hi), ("斜率取 1（地与名下成正比）", 1.0)):
        e1, e2, shr = split(sl)
        parts.append(f"{name} {sl:.2f}：经验出生层 {e1:.2f} × 剩余转化 {e2:.2f}，对数差距里出生层占 {100 * shr:.0f}%")
    w("  这个拆法对斜率的敏感度（10 个输局的几何平均）：" + "；".join(parts))
    w("注：其他真人名下小，多半是因为挤在真人堆里（四周是能打也会打过来的真人）；编队名下小，是因为和打不了的编队友排在一起。两种「小」不是一回事，这张表只回答「按别人的经验，名下这么大的人 1500 拍有多少地」。")
    w("    编队的名下常常比本局任何一个活到 1500 拍的其他真人都小（最后一列），那些号的推算是外推。")
    w()


# ---------------------------------------------------------------- AT-3
def at3():
    w("[AT-3] 延迟的来源：策略自己每拍算多久（HL-TICK 行尾的 avgMs / maxMs / skip；三个数都是开局以来的累计值：平均每拍毫秒、最慢一拍毫秒、跳过的拍数）")
    w("  一拍名义 56 毫秒、一个回合 392 毫秒。策略算得慢要造成几十上百拍的落后，单拍耗时得到几百毫秒的量级，或者有跳拍。")
    w("[AT-3a] 11 局：每个号最后一行 HL-TICK 的三个数，对照这个号 600~1500 拍的成交延迟中位")
    w("局 | 号数 | avgMs 中位（最大） | maxMs 中位（最大） | skip>0 的号 | 600~1500 延迟中位 >30 拍的号：个数、它们的 maxMs 最大值 | 延迟中位 ≤14 拍的号：个数、它们的 maxMs 最大值")
    allrows = []
    for m in MIDS:
        DF = delayf(m)
        last = {}
        with open(os.path.join(DATA, "bundles", m, "traj.csv"), encoding="utf8") as f:
            for r in csv.DictReader(f):
                try:
                    t = int(r["t"]); a = float(r["avgMs"]); mx = float(r["maxMs"]); sk = int(r["skip"])
                except (ValueError, KeyError):
                    continue
                if r["bot"] not in last or t >= last[r["bot"]][0]:
                    last[r["bot"]] = (t, a, mx, sk)
        # 对局包的 traj.csv 里可能混着别的房间的号（A025 3 个、A071 1 个）：只留这一局回放里认出来的号
        inroom = {b_ for b_, s_ in resim(m)["squad"].items() if s_["id"] >= 0 and not s_.get("mismatch")}
        last = {b_: v_ for b_, v_ in last.items() if b_ in inroom}
        hi, lo = [], []
        for bot, v in last.items():
            lg = DF["lag"]["byBot"].get(bot)
            lag = lg[1]["p50"] if lg and lg[1]["n"] else None
            allrows.append((m, bot, v, lag))
            if lag is not None and lag > 30:
                hi.append(v[2])
            if lag is not None and lag <= 14:
                lo.append(v[2])
        av = [v[1] for v in last.values()]; mxs = [v[2] for v in last.values()]
        w(f"{m} | {len(last)} | {med(av):.2f}（{max(av):.2f}） | {med(mxs):.1f}（{max(mxs):.1f}） | {sum(1 for v in last.values() if v[3] > 0)} | "
          f"{len(hi)} 个、{max(hi) if hi else '—'} | {len(lo)} 个、{max(lo) if lo else '—'}")
    hi = [r for r in allrows if r[3] is not None and r[3] > 30]; lo = [r for r in allrows if r[3] is not None and r[3] <= 14]
    w(f"合计：延迟中位 >30 拍的 {len(hi)} 个号，maxMs 中位 {med([r[2][2] for r in hi]):.1f}、最大 {max(r[2][2] for r in hi):.1f}，avgMs 中位 {med([r[2][1] for r in hi]):.2f}，skip>0 的 {sum(1 for r in hi if r[2][3] > 0)} 个；"
      f"延迟中位 ≤14 拍的 {len(lo)} 个号，maxMs 中位 {med([r[2][2] for r in lo]):.1f}、最大 {max(r[2][2] for r in lo):.1f}，avgMs 中位 {med([r[2][1] for r in lo]):.2f}，skip>0 的 {sum(1 for r in lo if r[2][3] > 0)} 个")
    x = [r[2][2] for r in allrows if r[3] is not None]; y = [r[3] for r in allrows if r[3] is not None]
    rs = pearson(ranks(x), ranks(y))
    w(f"  {len(x)} 个号上 maxMs 与 600~1500 延迟中位的秩相关 {fr(rs)}（不分局，混着房间大小）")
    # 发现集
    w("[AT-3b] 发现集 123 局：每个号最后一行 HL-TICK 的三个数")
    n = 0; av = []; mxs = []; sk = 0; over56 = 0; over392 = 0; nm = 0
    with open(os.path.join(DATA, "manifest.jsonl"), encoding="utf8") as f:
        mids = [json.loads(l)["matchId"] for l in f if l.strip()]
    for m in mids:
        p = os.path.join(DATA, "bundles", m, "traj.csv")
        if not os.path.exists(p):
            continue
        last = {}
        with open(p, encoding="utf8") as f:
            for r in csv.DictReader(f):
                try:
                    t = int(r["t"]); a = float(r["avgMs"]); mx = float(r["maxMs"]); s = int(r["skip"])
                except (ValueError, KeyError, TypeError):
                    continue
                if r["bot"] not in last or t >= last[r["bot"]][0]:
                    last[r["bot"]] = (t, a, mx, s)
        if last:
            nm += 1
        for v in last.values():
            n += 1; av.append(v[1]); mxs.append(v[2])
            if v[3] > 0: sk += 1
            if v[2] > 56: over56 += 1
            if v[2] > 392: over392 += 1
    av.sort(); mxs.sort()
    q = lambda v, f: v[min(len(v) - 1, int(f * len(v)))]
    w(f"  {nm} 局 {n} 个号：avgMs 中位 {q(av, 0.5):.2f}、九成位 {q(av, 0.9):.2f}、最大 {av[-1]:.2f}；maxMs 中位 {q(mxs, 0.5):.1f}、九成位 {q(mxs, 0.9):.1f}、最大 {mxs[-1]:.1f}；"
      f"最慢一拍超过 56 毫秒（一拍）的 {over56} 个号，超过 392 毫秒（一个回合）的 {over392} 个号；skip>0 的 {sk} 个号")
    w()


# ---------------------------------------------------------------- AT-4
def at4():
    w("[AT-4] 价格门的 over 放行：余额超过软上限（100×地）时出手打真人，买到的地是什么价")
    w("口径：重放的逐对战损账（每 30 拍一个窗口：进攻方 p 打真人 q 这一对在窗口里烧掉的兵、得到的格数）；窗口开始那一拍进攻方的余额 > 100×地 记作「超软」。")
    w("      策略 buyLand L5353、L5359：超软（over）时不再因为报价高于 worth 而停手；这里数的是全部超软窗口，不只是被这一条放行的那些（区分两者要在影子重跑里记每次报价，见提案）。")
    for lo, hi, name in ((1500, 4284, "1500~4284 拍"), (4284, 10 ** 9, "4284 拍起")):
        w(f"[AT-4{'a' if lo == 1500 else 'b'}] {name}")
        w("局 | 编队：打真人烧的兵 其中超软时（占比） | 编队 兵/格：超软 对 不超软 | 对手：打真人烧的兵 其中超软时（占比） | 对手 兵/格：超软 对 不超软")
        rs, ro, shs, sho = [], [], [], []
        for m in MIDS:
            R = resim(m)
            H = R["H"]
            sq = set(s["id"] for s in R["squad"].values() if s["id"] >= 0)
            tg = R["nTeams"] >= 2
            teams = R["teams"]
            my = teams[min(sq)] if tg else -1
            idx = {t: i for i, t in enumerate(R["snapT"])}
            sb, st = R["snapBal"], R["snapTerr"]
            acc = {"s": [[0, 0], [0, 0]], "o": [[0, 0], [0, 0]]}
            for t, p, q, tiles, burnt, dB, dS, n in R["pairLog"]:
                if p >= H or q >= H or t - 30 < lo or t > hi:
                    continue
                if p in sq:
                    g = "s"
                    if q in sq:
                        continue
                elif tg and teams[p] == my:
                    continue
                else:
                    g = "o"
                i = idx.get(t - 30)
                if i is None:
                    continue
                ov = 1 if st[i][p] > 0 and sb[i][p] > 100 * st[i][p] else 0
                acc[g][ov][0] += burnt; acc[g][ov][1] += tiles

            def cell(a):
                tot = a[0][0] + a[1][0]
                sh = a[1][0] / tot if tot > 0 else None
                p1 = a[1][0] / a[1][1] if a[1][1] > 0 else None
                p0 = a[0][0] / a[0][1] if a[0][1] > 0 else None
                return tot, sh, p1, p0

            ts, ss, s1, s0 = cell(acc["s"]); to, so, o1, o0 = cell(acc["o"])
            f = lambda x: "—" if x is None else f"{x:.0f}"
            fs = lambda x: "—" if x is None else f"{100 * x:.0f}%"
            w(f"{m} | {ts / 1e4:.0f}万 {acc['s'][1][0] / 1e4:.0f}万（{fs(ss)}） | {f(s1)} 对 {f(s0)} | {to / 1e4:.0f}万 {acc['o'][1][0] / 1e4:.0f}万（{fs(so)}） | {f(o1)} 对 {f(o0)}")
            if m != WIN:
                if s1 and s0:
                    rs.append(s1 / s0)
                if o1 and o0:
                    ro.append(o1 / o0)
                if ss is not None:
                    shs.append(ss)
                if so is not None:
                    sho.append(so)
        if rs and ro:
            w(f"输局：编队超软时烧的兵占比 中位 {100 * med(shs):.0f}%（{100 * min(shs):.0f}%~{100 * max(shs):.0f}%，{len(shs)} 局），对手 {100 * med(sho):.0f}%（{100 * min(sho):.0f}%~{100 * max(sho):.0f}%）；"
              f"兵/格 超软÷不超软：编队 中位 {med(rs):.2f}（{min(rs):.2f}~{max(rs):.2f}，{len(rs)} 局，大于 1 的 {sum(1 for x in rs if x > 1)} 局），对手 中位 {med(ro):.2f}（{min(ro):.2f}~{max(ro):.2f}，{len(ro)} 局，大于 1 的 {sum(1 for x in ro if x > 1)} 局）")
    w("注：兵/格 = 这一对在窗口里烧掉的兵 ÷ 得到的格数，含被对方反击槽对消的兵；A046 没有队伍，编队友之间互打的窗口不计入编队一栏。")
    w()


def at5():
    w("[AT-5] 匹配对照：名下一样大的其他真人，630~1500 拍把兵换成地了没有")
    w("口径：对照 = 同一局里名下格数在这个编队号的 1/1.5~1.5 倍之间、630 拍和 1500 拍都有地、1500 拍前没有离线的其他真人；至少要有 2 个对照。每格 = 编队号的值 ÷ 它的对照的中位，再取局内各号的中位。")
    w("      利息 = 630~1500 拍这个席位实得的利息（重放逐拍累计）；余额净增 = 1500 拍余额 − 630 拍余额。名下格数来源同 [AT-2]。")
    w("局 | 在控号数 | 有对照的号 | 每号对照人数中位 | 630 拍 地÷名下 | 1500 拍 地÷名下 | 1500 拍地 ÷ 630 拍地 | 1500 拍 兵÷地 | 630~1500 利息 | 1500 拍余额 ÷ 这一段利息 | 余额净增 ÷ 这一段利息")
    KEYS = ["c630", "c1500", "grow", "dens", "inc", "hoard", "keep"]
    pooled = {k: [] for k in KEYS}
    permatch = {k: [] for k in KEYS}
    raw = {"s": {k: [] for k in KEYS}, "o": {k: [] for k in KEYS}}
    for m in MIDS:
        C = cells(m)
        if not C:
            w(f"{m} | （缺名下格数）")
            continue
        R = resim(m)
        idx = {t: i for i, t in enumerate(R["snapT"])}
        a, b = idx[630], idx[1500]
        LF = landf(m)
        ctl = set(LF["capture"][[c["t"] for c in LF["capture"]].index(1500)]["perBot"].keys())
        sqid = {v["id"]: k for k, v in R["squad"].items() if v["id"] >= 0}

        def rec(p):
            i = p["id"]
            L0, L1 = R["snapTerr"][a][i], R["snapTerr"][b][i]
            if L0 <= 0 or L1 <= 0 or p["cells"] <= 0:
                return None
            B0, B1 = R["snapBal"][a][i], R["snapBal"][b][i]
            inc = R["snapInc"][b][i] - R["snapInc"][a][i]
            if inc <= 0:
                return None
            return {"cells": p["cells"], "c630": L0 / p["cells"], "c1500": L1 / p["cells"], "grow": L1 / L0, "dens": B1 / L1, "inc": inc, "hoard": B1 / inc, "keep": (B1 - B0) / inc}

        others = []
        for p in C["pts"]:
            if p["squad"] or 0 <= R["leftT"][p["id"]] < 1500:
                continue
            r_ = rec(p)
            if r_:
                others.append(r_)
        ratios = {k: [] for k in KEYS}
        nm = []
        nctl = 0
        for p in C["pts"]:
            if not p["squad"] or sqid.get(p["id"]) not in ctl:
                continue
            r_ = rec(p)
            if not r_:
                continue
            nctl += 1
            M = [o for o in others if r_["cells"] / 1.5 <= o["cells"] <= r_["cells"] * 1.5]
            if len(M) < 2:
                continue
            nm.append(len(M))
            for k in KEYS:
                mo = med([o[k] for o in M])
                if mo and mo > 0:
                    ratios[k].append(r_[k] / mo)
                    if m != WIN:
                        raw["s"][k].append(r_[k]); raw["o"][k].append(mo)
        if not nm:
            w(f"{m} | {nctl} | 0 | — | — | — | — | — | — | — | —")
            continue
        w(f"{m} | {nctl} | {len(nm)} | {med(nm):.0f} | " + " | ".join(f"{med(ratios[k]):.2f}" for k in KEYS))
        if m != WIN:
            for k in KEYS:
                pooled[k].extend(ratios[k])
                permatch[k].append(med(ratios[k]))
    names = {"c630": "630 拍 地÷名下", "c1500": "1500 拍 地÷名下", "grow": "1500 拍地 ÷ 630 拍地", "dens": "1500 拍 兵÷地", "inc": "630~1500 利息", "hoard": "1500 拍余额 ÷ 这一段利息", "keep": "余额净增 ÷ 这一段利息"}
    w("输局合并（编队号的值 ÷ 对照中位）：")
    for k in KEYS:
        v = pooled[k]; pm = permatch[k]
        if not v:
            continue
        w(f"  {names[k]}：{len(v)} 个号的中位 {med(v):.2f}，大于 1 的 {sum(1 for x in v if x > 1)} 个；按局取中位 {min(pm):.2f}~{max(pm):.2f}，{len(pm)} 局里大于 1 的 {sum(1 for x in pm if x > 1)} 局")
    w("输局里这些号与它们的对照的原值（号的中位 对 对照中位的中位）：" + "；".join(
        f"{names[k]} {med(raw['s'][k]):.2f} 对 {med(raw['o'][k]):.2f}" for k in ("c630", "c1500", "grow", "hoard", "keep")) +
      f"；1500 拍 兵÷地 {med(raw['s']['dens']):.0f} 对 {med(raw['o']['dens']):.0f}")
    w("注：对照只按名下格数配，没有配「四周是谁」。其他真人名下小多半是挤在真人堆里，编队名下小是和编队友排在一起（[AT-2] 的注）。A041、A025、A071 这几局名下和编队一样小的其他真人只有 1~2 个，多数号没有对照。")
    w()


def at6():
    w("[AT-6] 4284 拍前后：打在编队身上的兵是谁的、这些进攻者的进项里捐款占多少；编队内互捐的税折成地")
    w("口径：进攻者 = 这一段里对编队号有战损记录的敌方真人（重放逐对战损账，30 拍一个窗口）；进项 = 这一段的实得利息 + 收到的捐款到账（重放成交口径）。")
    w("      捐款占进项按「打在编队身上的兵」加权：每个进攻者的 捐款÷(利息+捐款) 乘上它烧在编队身上的兵占全部的份额，再相加。")
    w("[AT-6a] 敌方真人打编队：1500~4284 拍 对 4284 拍起")
    w("局 | 1500~4284：烧在编队身上的兵 进攻者人数 前 3 名占比 | 进攻者进项：利息 捐款到账 | 捐款占进项（加权） | 4284 起：烧在编队身上的兵 进攻者人数 前 3 名占比 | 进攻者进项：利息 捐款到账 | 捐款占进项（加权） | 每 1000 拍烧在编队身上的兵：前 → 后")
    sh1, sh2, rate = [], [], []
    for m in MIDS:
        R = resim(m)
        H = R["H"]
        sq = set(v["id"] for v in R["squad"].values() if v["id"] >= 0)
        tg = R["nTeams"] >= 2
        teams = R["teams"]
        my = teams[min(sq)] if tg else -1
        T = R["snapT"]
        end = R["endTick"]

        def near(t):
            return min(range(len(T)), key=lambda i: abs(T[i] - t))

        cells_ = []
        rr = []
        for lo, hi in ((1500, 4284), (4284, end + 1)):
            A = defaultdict(float)
            for t, p, q, tiles, burnt, dB, dS, n in R["pairLog"]:
                if p >= H or q not in sq or p in sq or t - 30 < lo or t > hi:
                    continue
                if tg and teams[p] == my:
                    continue
                A[p] += burnt
            tot = sum(A.values())
            ia, ib = near(lo), near(min(hi, end))
            don = defaultdict(float)
            for c in R["cmdLog"]:
                if c[2] == 2 and c[5] and lo <= c[0] < hi and c[4] in A:
                    don[c[4]] += c[6]
            I = {p: max(0, R["snapInc"][ib][p] - R["snapInc"][ia][p]) for p in A}
            wsh = sum((A[p] / tot) * (don[p] / (I[p] + don[p])) for p in A if I[p] + don[p] > 0) if tot > 0 else None
            top3 = sum(sorted(A.values(), reverse=True)[:3]) / tot if tot > 0 else None
            span = (min(hi, end) - lo) / 1000
            rr.append(tot / span if span > 0 else None)
            cells_.append(f"{tot / 1e4:.0f}万 {len(A)} 人 {100 * top3:.0f}% | {sum(I.values()) / 1e4:.0f}万 {sum(don.values()) / 1e4:.0f}万 | {100 * wsh:.0f}%" if tot > 0 else "— | — | —")
            if m != WIN and wsh is not None:
                (sh1 if lo == 1500 else sh2).append(wsh)
        w(f"{m} | " + " | ".join(cells_) + f" | {rr[0] / 1e4:.0f}万 → {rr[1] / 1e4:.0f}万")
        if m != WIN and rr[0] and rr[1]:
            rate.append(rr[1] / rr[0])
    w(f"输局：捐款占进攻者进项（加权）1500~4284 拍 中位 {100 * med(sh1):.0f}%（{100 * min(sh1):.0f}%~{100 * max(sh1):.0f}%），4284 拍起 中位 {100 * med(sh2):.0f}%（{100 * min(sh2):.0f}%~{100 * max(sh2):.0f}%）；"
      f"每 1000 拍烧在编队身上的兵 后 ÷ 前 中位 {med(rate):.2f}（{min(rate):.2f}~{max(rate):.2f}，大于 1 的 {sum(1 for x in rate if x > 1)}/{len(rate)} 局）")
    w("[AT-6b] 4284 拍那一刻编队已经落后多少（重放快照；敌方真人 = 不在编队那一队的真人，A046 没有队伍、取全部其他真人）")
    w("局 | 编队有地号数 | 编队地 ÷ 敌方真人地 | 编队兵 ÷ 敌方真人兵 | 敌方最大一家的地 ÷ 编队合计地 | 敌方最大一家的兵 ÷ 编队合计兵 | 编队所在队合计地 ÷ 敌方最大一队的地")
    r1, r2, r3 = [], [], []
    for m in MIDS:
        R = resim(m)
        H = R["H"]
        sq = set(v["id"] for v in R["squad"].values() if v["id"] >= 0)
        tg = R["nTeams"] >= 2
        teams = R["teams"]
        my = teams[min(sq)] if tg else -1
        T = R["snapT"]
        i = min(range(len(T)), key=lambda k: abs(T[k] - 4284))
        L_, B_ = R["snapTerr"][i], R["snapBal"][i]
        en = [p for p in range(H) if p not in sq and not (tg and teams[p] == my)]
        sL = sum(L_[p] for p in sq); sB = sum(B_[p] for p in sq)
        eL = sum(L_[p] for p in en); eB = sum(B_[p] for p in en)
        bigL = max(L_[p] for p in en); bigB = max(B_[p] for p in en)
        if tg:
            tl = defaultdict(int)
            for p in range(H):
                tl[teams[p]] += L_[p]
            oth = max(v for k, v in tl.items() if k != my)
            tr = f"{tl[my] / oth:.2f}"
        else:
            tr = "—"
        w(f"{m} | {sum(1 for p in sq if L_[p] > 0)} | {sL / eL:.2f} | {sB / eB:.2f} | {bigL / sL:.2f} | {bigB / sB:.2f} | {tr}")
        if m != WIN:
            r1.append(sL / eL); r2.append(bigL / sL); r3.append(bigB / sB)
    w(f"输局：编队地 ÷ 敌方真人地 中位 {med(r1):.2f}（{min(r1):.2f}~{max(r1):.2f}）；敌方最大一家的地 ÷ 编队合计地 中位 {med(r2):.2f}（{min(r2):.2f}~{max(r2):.2f}）；敌方最大一家的兵 ÷ 编队合计兵 中位 {med(r3):.2f}（{min(r3):.2f}~{max(r3):.2f}）")
    w("[AT-6c] 4284 拍前编队内成交的互捐：付掉的税，按编队自己 1500~4284 拍打真人的 兵/格 折成地（定价，不是反事实：税不付也不等于这些兵会去买地）")
    w("局 | 编队内成交 笔数 到账 税 | 编队 1500~4284 打真人 兵/格 | 税折成格数 | ÷ 4284 拍编队合计地 | ÷ 1500~4284 编队打真人得的格数")
    tt = tg_ = 0
    n_ = 0
    e1, e2 = [], []
    for m in MIDS:
        R = resim(m)
        H = R["H"]
        sq = set(v["id"] for v in R["squad"].values() if v["id"] >= 0)
        if R["nTeams"] < 2:
            w(f"{m} | （没有队伍，没有互捐）")
            continue
        n = got = tax = 0
        for c in R["cmdLog"]:
            if c[2] == 2 and c[5] and c[0] < 4284 and c[1] in sq and c[4] in sq:
                n += 1; got += c[6]; tax += c[7]
        burnt = tiles = 0
        for t, p, q, ti, bu, dB, dS, k in R["pairLog"]:
            if p in sq and q < H and q not in sq and 1500 <= t - 30 and t <= 4284:
                burnt += bu; tiles += ti
        T = R["snapT"]
        i = min(range(len(T)), key=lambda k: abs(T[k] - 4284))
        sL = sum(R["snapTerr"][i][p] for p in sq)
        price = burnt / tiles if tiles > 0 else None
        eq = tax / price if price else None
        w(f"{m} | {n} 笔 {got / 1e4:.0f}万 {tax / 1e4:.0f}万 | {price:.0f} | {eq:,.0f} | {100 * eq / sL:.1f}% | {100 * eq / tiles:.1f}%")
        if m != WIN:
            tt += tax; tg_ += got; n_ += n
            e1.append(eq / sL); e2.append(eq / tiles)
    w(f"9 个有队伍的输局合计：{n_} 笔、到账 {tg_ / 1e4:.0f}万、税 {tt / 1e4:.0f}万；税折成的格数 ÷ 4284 拍编队合计地 中位 {100 * med(e1):.1f}%（{100 * min(e1):.1f}%~{100 * max(e1):.1f}%），÷ 同期打真人得的格数 中位 {100 * med(e2):.1f}%（{100 * min(e2):.1f}%~{100 * max(e2):.1f}%）")
    w("注：没成交的调度「留在后排的兵」没有折算：同一个调度决定在没落地时会一拍一拍重发，日志里的金额不能相加；要折算得用闭环反事实臂（见提案）。")
    w()


def main():
    w("# 归因事实表（attrib.py）。11 局 = A051 A087 A066 A025 A045 A067 A071 A090 A042 A046 A041；胜局只有 A025。")
    w()
    at1(); at2(); at3(); at4(); at5(); at6()
    os.makedirs(os.path.join(OUT, "council"), exist_ok=True)
    path = os.path.join(OUT, "council", "ATTR-facts.txt")
    with open(path, "w", encoding="utf8") as f:
        f.write("\n".join(L) + "\n")
    print(f"写 {os.path.relpath(path, ROOT)}（{len(L)} 行）")


if __name__ == "__main__":
    sys.exit(main())
