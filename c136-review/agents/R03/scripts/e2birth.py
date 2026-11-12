#!/usr/bin/env python3
"""e2birth.py — 会审报告 4.3 节预先写明的发现集检验：出生份额 × 630→1530 拍地的倍数（squad10 档）。

预先定下的做法（写在看到样本外那 64 局的结果之前）：
  样本     manifest.jsonl 里 cohort=squad10、split=discovery 的局（75 局）。主检验只用不在我名下 11 局里的局（样本外）；
           全部局的结果并列给出，只作参考。
  排除     cells.mjs 没有输出的局；traj.csv 在 630 或 1530 拍没有任何编队号的行；630 拍编队合计地为 0；
           名下格数表里编队号不足 2 个或其他真人不足 2 个。排除的局逐条列出原因。
  出生份额 S = 编队号人均名下格数 ÷ 其他真人人均名下格数（out/council/cells/<局>.json，质心口径）。
  地的倍数 G = traj.csv 里编队各号 1530 拍的地之和 ÷ 630 拍的地之和（某个号在那一拍没有行，按 0 算）。
  密度     D = 1530 拍编队各号的兵之和 ÷ 地之和（1530 拍编队合计地为 0 的局不进这一项）。
  开局人数 N = 名下格数表里的真人数（含编队）。
  统计     跨局取秩；两个量各自对 N 的秩做一元回归取残差，残差的皮尔逊相关就是偏秩相关。
           置换检验：打乱 S 的残差 5000 次（种子 136），双侧。
  判读     主检验里 S 与 G 的偏秩相关为正、置换 p < 0.05 → 写「在发现集上复现」；否则写「没有复现」。
           S 与 D 的偏秩相关只作描述（预期为负），不进判读。输赢分组也只作描述。

  timeout 120 python3 scripts/e2birth.py        # 写 out/council/E2-birth.txt
只读 manifest.jsonl、bundles/<局>/traj.csv 和 out/council/cells/<局>.json，不跑重放。
"""
import csv
import json
import math
import os
import random
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
DATA = os.environ.get("C136_DATA", "/agent/repos/c136-data")
CELLS = os.path.join(ROOT, "out", "council", "cells")
OUT = os.path.join(ROOT, "out", "council", "E2-birth.txt")
MINE = "A051 A087 A066 A025 A045 A067 A071 A090 A042 A046 A041".split()
T0, T1 = 630, 1530
SEED, NPERM = 136, 5000


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
    sa = sum((x - ma) ** 2 for x in a)
    sb = sum((y - mb) ** 2 for y in b)
    if sa <= 0 or sb <= 0:
        return None
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(sa * sb)


def resid(z, c):
    mz, mc = sum(z) / len(z), sum(c) / len(c)
    den = sum((x - mc) ** 2 for x in c)
    b = sum((a - mz) * (x - mc) for a, x in zip(z, c)) / den if den > 0 else 0.0
    return [(a - mz) - b * (x - mc) for a, x in zip(z, c)]


def perm_p(x, y, seed=SEED, nperm=NPERM):
    r = pearson(x, y)
    if r is None:
        return None, None
    rnd = random.Random(seed)
    hit = 0
    xs = x[:]
    for _ in range(nperm):
        rnd.shuffle(xs)
        rr = pearson(xs, y)
        if rr is not None and abs(rr) >= abs(r) - 1e-12:
            hit += 1
    return r, (hit + 1) / (nperm + 1)


def spearman(a, b):
    return perm_p(ranks(a), ranks(b))


def partial(a, b, c):
    ra, rb, rc = ranks(a), ranks(b), ranks(c)
    return perm_p(resid(ra, rc), resid(rb, rc))


def fr(r):
    return "—" if r is None else f"{r:+.2f}"


def fp(p):
    if p is None:
        return "—"
    return "p<0.001" if p < 0.001 else f"p={p:.3f}"


def med(v):
    return statistics.median(v) if v else None


def load_match(row):
    mid = row["matchId"]
    cp = os.path.join(CELLS, f"{mid}.json")
    if not os.path.exists(cp):
        fp_ = os.path.join(CELLS, f"{mid}.fail.json")
        if os.path.exists(fp_):
            return None, "cells.mjs 算不出名下格数（" + json.load(open(fp_, encoding="utf-8")).get("error", "") + "）"
        return None, "cells.mjs 没有输出"
    c = json.load(open(cp, encoding="utf-8"))
    sq = [p["cells"] for p in c["pts"] if p["squad"]]
    ot = [p["cells"] for p in c["pts"] if not p["squad"]]
    if len(sq) < 2 or len(ot) < 2:
        return None, f"名下格数表里编队 {len(sq)} 个号、其他真人 {len(ot)} 个"
    tp = os.path.join(DATA, "bundles", mid, "traj.csv")
    if not os.path.exists(tp):
        return None, "没有 traj.csv"
    land = {T0: 0, T1: 0}
    bal = {T0: 0.0, T1: 0.0}
    nrow = {T0: 0, T1: 0}
    per = {}
    for r in csv.DictReader(open(tp, encoding="utf-8")):
        t = int(r["t"])
        per.setdefault(r["bot"], {})[t] = int(float(r["terr"]))
        if t in land:
            land[t] += int(float(r["terr"]))
            bal[t] += float(r["bal"])
            nrow[t] += 1
    # 事后敏感性检查用：某个号在这一拍没有行、但前后各 90 拍都有行，取前后两拍的平均（日志缺行，不是出局）
    fill = {T0: 0.0, T1: 0.0}
    nfill = {T0: 0, T1: 0}
    for bot, tt in per.items():
        for t in (T0, T1):
            if t in tt:
                fill[t] += tt[t]
            elif (t - 90) in tt and (t + 90) in tt:
                fill[t] += (tt[t - 90] + tt[t + 90]) / 2.0
                nfill[t] += 1
    if nrow[T0] == 0 or nrow[T1] == 0:
        return None, f"traj.csv 在 {T0} 拍有 {nrow[T0]} 行、{T1} 拍有 {nrow[T1]} 行"
    if land[T0] <= 0:
        return None, f"{T0} 拍编队合计地为 0"
    s = (sum(sq) / len(sq)) / (sum(ot) / len(ot))
    return dict(mid=mid, S=s, G=land[T1] / land[T0], D=(bal[T1] / land[T1]) if land[T1] > 0 else None,
                N=c["humans"], nsq=len(sq), n0=nrow[T0], n1=nrow[T1], land0=land[T0], land1=land[T1],
                won=row["outcome"]["resultLabel"] == "won", teams=row.get("actualTeams"), mine=mid in MINE,
                G2=(fill[T1] / fill[T0]) if fill[T0] > 0 else None, nfill0=nfill[T0], nfill1=nfill[T1]), None


def block(P, title, rows):
    P(title)
    if len(rows) < 5:
        P(f"  局数 {len(rows)}，太少，不算")
        return None
    S = [r["S"] for r in rows]
    G = [r["G"] for r in rows]
    N = [r["N"] for r in rows]
    P(f"  局数 {len(rows)}；出生份额中位 {med(S):.2f}（{min(S):.2f}~{max(S):.2f}），小于 1 的 {sum(1 for x in S if x < 1)} 局；"
      f"地的倍数中位 {med(G):.2f}（{min(G):.2f}~{max(G):.2f}）；开局人数中位 {med(N):.0f}（{min(N)}~{max(N)}）")
    r0, p0 = spearman(S, G)
    r1, p1 = partial(S, G, N)
    rn, pn = spearman(S, N)
    rg, pg = spearman(G, N)
    P(f"  出生份额 × 地的倍数：秩相关 {fr(r0)}（{fp(p0)}）；控制开局人数的偏秩相关 {fr(r1)}（{fp(p1)}）")
    P(f"  开局人数 × 出生份额：秩相关 {fr(rn)}（{fp(pn)}）；开局人数 × 地的倍数：秩相关 {fr(rg)}（{fp(pg)}）")
    dd = [r for r in rows if r["D"] is not None]
    if len(dd) >= 5:
        r2, p2 = spearman([r["S"] for r in dd], [r["D"] for r in dd])
        r3, p3 = partial([r["S"] for r in dd], [r["D"] for r in dd], [r["N"] for r in dd])
        P(f"  出生份额 × {T1} 拍密度（{len(dd)} 局）：秩相关 {fr(r2)}（{fp(p2)}）；控制开局人数的偏秩相关 {fr(r3)}（{fp(p3)}）")
    return r1, p1


def main():
    man = [json.loads(l) for l in open(os.path.join(DATA, "manifest.jsonl"), encoding="utf-8") if l.strip()]
    sq10 = [r for r in man if r.get("cohort") == "squad10" and r.get("split") == "discovery"]
    L = []
    P = L.append
    P("# E2-birth.txt — 发现集 squad10 档：出生份额 × 630→1530 拍地的倍数；脚本 scripts/e2birth.py（做法和判读写在脚本开头，先于结果）")
    P(f"# 出处：manifest.jsonl、bundles/<局>/traj.csv、out/council/cells/<局>.json。置换 {NPERM} 次，种子 {SEED}，双侧。")
    P("")
    rows, skipped = [], []
    for r in sorted(sq10, key=lambda r: r["matchId"]):
        d, why = load_match(r)
        if d is None:
            skipped.append((r["matchId"], why))
        else:
            rows.append(d)
    P("[E2-0] 样本")
    P(f"squad10 发现集 {len(sq10)} 局；进表 {len(rows)} 局（我名下的 {sum(1 for r in rows if r['mine'])} 局，样本外 {sum(1 for r in rows if not r['mine'])} 局）；排除 {len(skipped)} 局")
    for mid, why in skipped:
        P(f"排除 {mid}：{why}")
    P("")
    out = [r for r in rows if not r["mine"]]
    P("[E2-1] 偏秩相关")
    res = block(P, "主检验（样本外的局）：", out)
    block(P, "参考（全部进表的局）：", rows)
    block(P, "参考（我名下的局）：", [r for r in rows if r["mine"]])
    P("")
    P("[E2-2] 判读（预先写明：主检验里出生份额与地的倍数的偏秩相关为正、置换 p < 0.05 算复现）")
    if res is None or res[0] is None:
        P("判读：算不出来")
    else:
        ok = res[0] > 0 and res[1] < 0.05
        P(f"主检验偏秩相关 {fr(res[0])}，{fp(res[1])} → {'在发现集上复现' if ok else '没有复现'}")
    P("")
    P("[E2-3] 按输赢分组（只作描述，不在预先写的判读里）")
    P("组 | 局数 | 出生份额中位 | 地的倍数中位 | 1530 拍密度中位 | 开局人数中位")
    for name, g in (("样本外·输", [r for r in out if not r["won"]]), ("样本外·赢", [r for r in out if r["won"]]),
                    ("全部·输", [r for r in rows if not r["won"]]), ("全部·赢", [r for r in rows if r["won"]])):
        if not g:
            P(f"{name} | 0 | — | — | — | —")
            continue
        dv = [r["D"] for r in g if r["D"] is not None]
        P(f"{name} | {len(g)} | {med([r['S'] for r in g]):.2f} | {med([r['G'] for r in g]):.2f} | {(f'{med(dv):.1f}' if dv else '—')} | {med([r['N'] for r in g]):.0f}")
    P("")
    P("[E2-4] 逐局")
    P("局 | 样本外 | 输赢 | 实际队数 | 开局人数 | 名下格数表里的编队号数 | 出生份额 | 630 拍编队地（行数） | 1530 拍编队地（行数） | 地的倍数 | 1530 拍密度")
    for r in rows:
        P(f"{r['mid']} | {'否' if r['mine'] else '是'} | {'赢' if r['won'] else '输'} | {r['teams']} | {r['N']} | {r['nsq']} | {r['S']:.2f} | "
          f"{r['land0']:,}（{r['n0']}） | {r['land1']:,}（{r['n1']}） | {r['G']:.2f} | {(f'{r_D:.1f}' if (r_D := r['D']) is not None else '—')}")
    P("")
    P("[E2-5] 事后加的敏感性检查（看到 [E2-1] 的结果之后才加的；只作参考，不改 [E2-2] 的判读）")
    P("做法 | 样本外局数 | 出生份额 × 地的倍数：控制开局人数的偏秩相关")
    part = [r for r in out if r["nsq"] < r["n0"]]
    gap = [r for r in out if r["nfill0"] or r["nfill1"]]

    def line(name, rs, gk):
        rs = [r for r in rs if r[gk] is not None]
        if len(rs) < 5:
            P(f"{name} | {len(rs)} | 局数太少")
            return
        r1, p1 = partial([r["S"] for r in rs], [r[gk] for r in rs], [r["N"] for r in rs])
        P(f"{name} | {len(rs)} | {fr(r1)}（{fp(p1)}）")

    line("预先写的做法（同 [E2-1] 主检验）", out, "G")
    line("去掉编队号没认全的局", [r for r in out if r["nsq"] >= r["n0"]], "G")
    line("缺行按前后两拍补", out, "G2")
    line("两样都做", [r for r in out if r["nsq"] >= r["n0"]], "G2")
    P(f"说明：样本外 {len(out)} 局里，名下格数表里认出的编队号数少于 630 拍 traj 行数的 {len(part)} 局（{'、'.join(r['mid'] for r in part) or '没有'}）；"
      f"630 或 1530 拍有号缺行、但前后两拍都有行的 {len(gap)} 局（{'、'.join(r['mid'] for r in gap) or '没有'}）")
    # 口径对照：我名下 11 局在跨局汇总 X12 的 E1 行里也有出生份额（land-ledger 的口径），和这里的逐局比一下
    x12 = os.path.join(ROOT, "out", "cross", "X12-summary.txt")
    if os.path.exists(x12):
        e1 = next((l for l in open(x12, encoding="utf-8") if l.startswith("E1 ")), None)
        if e1:
            vals = [float(x) for x in e1.split(" | ")[1].split()]
            if len(vals) == len(MINE):
                mine = {r["mid"]: r["S"] for r in rows if r["mine"]}
                P("")
                P("[E2-6] 口径对照：我名下 11 局的出生份额，本表（cells.mjs，开局有地的全部真人）对 跨局汇总 X12 的 E1 行")
                P("局 | 本表 | X12 的 E1 | 差")
                ds = []
                for m, v in zip(MINE, vals):
                    if m in mine:
                        ds.append(abs(mine[m] - v))
                        P(f"{m} | {mine[m]:.2f} | {v:.2f} | {mine[m] - v:+.2f}")
                if ds:
                    P(f"合计：{len(ds)} 局，差的绝对值最大 {max(ds):.2f}、中位 {statistics.median(ds):.2f}")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print(f"写 {os.path.relpath(OUT, ROOT)}（{len(L)} 行；进表 {len(rows)} 局，排除 {len(skipped)} 局）")


if __name__ == "__main__":
    main()
