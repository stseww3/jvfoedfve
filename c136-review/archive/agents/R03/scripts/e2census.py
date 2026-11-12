#!/usr/bin/env python3
"""e2census.py — 只用日志（不用重放）就能数的几条判据，在 123 局发现集上机械计数。

只读 /agent/repos/c136-data/manifest.jsonl 与 bundles/<局>/{events.csv,traj.csv,spawn.csv}（不碰 validation_bundles/）。
写 out/cross/E2-census.txt。跑一遍几秒钟。

    python3 scripts/e2census.py

判据（每条都只是「日志里看得见的那一半」，表里同时给出在 R03 复盘的 11 局上与重放精确值的对照，看这个替身准不准）：
  [E2-1] 调度日志按受捐额度分段的条数与「疑似被拒」条数（events.csv 的 DISPATCH/DONATE 行；likelyRejected 列是数据包生成时打的标：
         35 拍内同一个号再次发起且 myBal 没降）。分段：<2142 / 2142~3212 / 3213~4283 / ≥4284 拍。
  [E2-2] 1500 拍起逐号快照里「没有邻居也没有中立边」（nb=0 且 neut=0）的占比，及其中密度 ≥95 的占比（traj.csv，90 拍一个快照）。
  [E2-3] 编队在 1530 拍快照的密度（兵合计 ÷ 地合计），以及 630→1530 拍编队地合计的倍数（traj.csv）。
  [E2-4] 选点间距：每个号最后一行选点坐标到最近的编队友的像素距离（spawn.csv），取全队中位，再除以 sqrt(全图陆地 ÷ 开局人数)（= 人均占地的边长）。
结局列：card 的 outcome.resultLabel；峰值÷人头 = outcome.peakSquadLandShare ÷ (squadBots ÷ seededPlayers)。
"""
import csv
import json
import math
import os
import random
import sys
from collections import defaultdict

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = "/agent/repos/c136-data"
MINE = ["A051", "A087", "A066", "A025", "A045", "A067", "A071", "A090", "A042", "A046", "A041"]
BANDS = ((0, 2142, "<2142"), (2142, 3213, "2142~3212"), (3213, 4284, "3213~4283"), (4284, 10 ** 9, "≥4284"))


def rows_of(mid, name):
    p = os.path.join(DATA, "bundles", mid, name)
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8", errors="replace", newline="") as f:
        return list(csv.DictReader(f))


def num(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def med(a):
    s = sorted(a)
    if not s:
        return None
    k = len(s)
    return s[k // 2] if k % 2 else (s[k // 2 - 1] + s[k // 2]) / 2.0


def quart(a, q):
    s = sorted(a)
    if not s:
        return None
    return s[min(len(s) - 1, max(0, int(round(q * (len(s) - 1)))))]


def ranks(v):
    idx = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(idx):
        j = i
        while j + 1 < len(idx) and v[idx[j + 1]] == v[idx[i]]:
            j += 1
        for k in range(i, j + 1):
            r[idx[k]] = (i + j) / 2.0 + 1
        i = j + 1
    return r


def pearson(a, b):
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    sa = math.sqrt(sum((x - ma) ** 2 for x in a))
    sb = math.sqrt(sum((x - mb) ** 2 for x in b))
    return 0.0 if sa == 0 or sb == 0 else sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (sa * sb)


def spearman(x, y, iters=20000, seed=136):
    rx, ry = ranks(x), ranks(y)
    rho = pearson(rx, ry)
    rng = random.Random(seed)
    p = list(ry)
    hit = 0
    for _ in range(iters):
        rng.shuffle(p)
        if abs(pearson(rx, p)) >= abs(rho) - 1e-12:
            hit += 1
    return rho, (hit + 1) / (iters + 1)


def partial_spearman(x, y, z, iters=20000, seed=136):
    """控制 z 之后 x 与 y 的偏秩相关：三列各取秩，x、y 的秩分别对 z 的秩做一元回归取残差，再算残差的相关；p = 打乱 y 残差的置换 p。"""
    rx, ry, rz = ranks(x), ranks(y), ranks(z)

    def resid(a, b):
        n = len(a)
        ma, mb = sum(a) / n, sum(b) / n
        sbb = sum((v - mb) ** 2 for v in b)
        k = sum((u - ma) * (v - mb) for u, v in zip(a, b)) / sbb if sbb else 0.0
        return [(u - ma) - k * (v - mb) for u, v in zip(a, b)]
    ex, ey = resid(rx, rz), resid(ry, rz)
    rho = pearson(ex, ey)
    rng = random.Random(seed)
    p = list(ey)
    hit = 0
    for _ in range(iters):
        rng.shuffle(p)
        if abs(pearson(ex, p)) >= abs(rho) - 1e-12:
            hit += 1
    return rho, (hit + 1) / (iters + 1)


def pf(p):
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def f(v, nd=2):
    return "—" if v is None else f"{v:.{nd}f}"


def pct(a, b, nd=0):
    return f"{100.0 * a / b:.{nd}f}%" if b else "—"


def measure(card):
    mid = card["matchId"]
    m = {"mid": mid, "cohort": card["cohort"], "result": card["outcome"]["resultLabel"], "players": card.get("seededPlayers") or 0,
         "bots": card.get("squadBots") or 0, "land": card.get("mapLand") or 0, "teams": card.get("actualTeams"), "mode": card.get("mode"),
         "end": card["outcome"].get("endTick")}
    head = m["bots"] / m["players"] if m["players"] else None
    m["peakOverHead"] = (card["outcome"].get("peakSquadLandShare") or 0) / head if head else None
    # [E2-1]
    ev = [e for e in rows_of(mid, "events.csv") if e.get("type") in ("DISPATCH", "DONATE")]
    m["log"] = [0] * 4
    m["rej"] = [0] * 4
    m["off"] = [0] * 4
    for e in ev:
        t = num(e.get("t"), -1)
        for k, (a, b, _) in enumerate(BANDS):
            if a <= t < b:
                m["log"][k] += 1
                m["rej"][k] += str(e.get("likelyRejected")) == "True"
                m["off"][k] += e.get("kind") == "offense_dispatch"
    # [E2-2] [E2-3]
    tr = rows_of(mid, "traj.csv")
    snaps = boxed = boxed_dense = 0
    at = defaultdict(lambda: [0.0, 0.0])
    who = defaultdict(set)
    for r in tr:
        t, terr, bal = num(r.get("t"), -1), num(r.get("terr")), num(r.get("bal"))
        if terr <= 0:
            continue
        at[int(t)][0] += terr
        at[int(t)][1] += bal
        who[int(t)].add(r.get("bot"))
        if t >= 1500:
            snaps += 1
            if num(r.get("nb")) == 0 and num(r.get("neut")) == 0:
                boxed += 1
                boxed_dense += num(r.get("dens")) >= 95
    m["snaps"], m["boxed"], m["boxedDense"] = snaps, boxed, boxed_dense
    m["boxedShare"] = 100.0 * boxed / snaps if snaps else None
    m["dens1530"] = at[1530][1] / at[1530][0] if at.get(1530) and at[1530][0] else None
    # 地的倍数：630 拍有快照的号（至少要有八成的号有快照，否则不算）在 1530 拍的地合计 ÷ 630 拍的地合计；1530 拍没有快照的号按 0 算
    m["grow"] = None
    if m["bots"] and len(who.get(630, ())) >= 0.8 * m["bots"] and at[630][0]:
        l1530 = sum(num(r.get("terr")) for r in tr if int(num(r.get("t"), -1)) == 1530 and r.get("bot") in who[630])
        m["grow"] = l1530 / at[630][0]
    # [E2-4]
    last = {}
    for r in rows_of(mid, "spawn.csv"):
        if r.get("x") not in (None, "") and r.get("y") not in (None, ""):
            last[r["bot"]] = (num(r["x"]), num(r["y"]))
    ds = []
    for b, (x, y) in last.items():
        o = [math.hypot(x - x2, y - y2) for b2, (x2, y2) in last.items() if b2 != b]
        if o:
            ds.append(min(o))
    m["spawnMed"] = med(ds)
    side = math.sqrt(m["land"] / m["players"]) if m["players"] and m["land"] else None
    m["spawnRel"] = m["spawnMed"] / side if ds and side else None
    return m


def exact_for_mine():
    """R03 复盘的 11 局里的重放精确值（从 out/cross/X12-summary.txt 的对应行读，不在这里重算）。"""
    out = {}
    p = os.path.join(ROOT, "out", "cross", "X12-summary.txt")
    if not os.path.exists(p):
        return out
    want = {"G1 调度/捐款 成交÷日志": "exec", "H1 被围占比 1500起": "boxed", "E1 出生份额": "spawn", "A7 密度比 1500": "densRatio", "A2 人均地比 1500": "land1500",
            "B8 人均得AI+中立地比 630~1500": "aiGain"}
    for line in open(p, encoding="utf-8"):
        for key, tag in want.items():
            if line.startswith(key):
                vals = line.split("|")[1].split()
                out[tag] = dict(zip(MINE, [None if v == "—" else float(v) for v in vals]))
    return out


def main():
    cards = [json.loads(line) for line in open(os.path.join(DATA, "manifest.jsonl"), encoding="utf-8")]
    M = [measure(c) for c in cards]
    by = {m["mid"]: m for m in M}
    L = ["# E2 发现集普查（e2census.py；123 局发现集，只用 manifest.jsonl 与每局的 events.csv / traj.csv / spawn.csv，不用重放；判据口径见脚本文件头）",
         "# 这是日志里看得见的替身量，不是重放精确值；[V] 段给出在 R03 复盘的 11 局上两者的对照。三个编队规模用的策略版本不同，不混在一起比。",
         f"# 发现集 {len(M)} 局：" + "，".join(f"{c} {sum(1 for m in M if m['cohort'] == c)} 局" for c in ("squad10", "squad8", "squad20")),
         ""]

    groups = [("squad10 全部", lambda m: m["cohort"] == "squad10"), ("squad10 输", lambda m: m["cohort"] == "squad10" and m["result"] == "lost"),
              ("squad10 赢", lambda m: m["cohort"] == "squad10" and m["result"] == "won"), ("squad8 全部", lambda m: m["cohort"] == "squad8"),
              ("squad20 全部", lambda m: m["cohort"] == "squad20")]

    L += ["[E2-1] 调度日志按额度分段：条数 → 其中疑似被拒（占比）；有调度日志的局数；<2142 拍日志 ≥10 条的局数及这些局里疑似被拒占比的中位",
          "组 | 局数（有调度日志的） | " + " | ".join(f"{nm}：日志→疑似被拒" for _, _, nm in BANDS) + " | <2142 日志 ≥10 条的局数 其中疑似被拒占比 ≥80% 的局数 | <2142 段进攻档占比"]
    for name, sel in groups:
        ms = [m for m in M if sel(m)]
        has = [m for m in ms if sum(m["log"])]
        cells = []
        for k in range(4):
            a, b = sum(m["log"][k] for m in ms), sum(m["rej"][k] for m in ms)
            cells.append(f"{a}→{b}（{pct(b, a)}）")
        early = [m for m in ms if m["log"][0] >= 10]
        hi = sum(1 for m in early if m["rej"][0] >= 0.8 * m["log"][0])
        off = sum(m["off"][0] for m in ms)
        L.append(f"{name} | {len(ms)}（{len(has)}） | " + " | ".join(cells) + f" | {len(early)} {hi} | {pct(off, sum(m['log'][0] for m in ms))}")

    L += ["", "[E2-2] 1500 拍起逐号快照：被围（nb=0 且 neut=0）占比",
          "组 | 局数 | 快照合计 | 被围（占比） | 被围里密度 ≥95（占被围） | 每局被围占比：下四分位 / 中位 / 上四分位 | 被围占比 ≥40% 的局数"]
    for name, sel in groups:
        ms = [m for m in M if sel(m) and m["snaps"]]
        s, b, d = sum(m["snaps"] for m in ms), sum(m["boxed"] for m in ms), sum(m["boxedDense"] for m in ms)
        sh = [m["boxedShare"] for m in ms]
        L.append(f"{name} | {len(ms)} | {s:,} | {b:,}（{pct(b, s)}） | {d:,}（{pct(d, b)}） | {f(quart(sh, 0.25), 0)}% / {f(med(sh), 0)}% / {f(quart(sh, 0.75), 0)}% | {sum(1 for v in sh if v >= 40)}")

    L += ["", "[E2-3] 编队 1530 拍密度、630→1530 拍地的倍数；[E2-4] 选点间距（全队中位 ÷ 人均占地边长）",
          "组 | 局数 | 1530 拍密度：下四分位 / 中位 / 上四分位 | 地的倍数：下四分位 / 中位 / 上四分位 | 选点间距（相对）：下四分位 / 中位 / 上四分位 | 峰值÷人头：中位"]
    for name, sel in groups:
        ms = [m for m in M if sel(m)]
        d = [m["dens1530"] for m in ms if m["dens1530"] is not None]
        g = [m["grow"] for m in ms if m["grow"] is not None]
        s = [m["spawnRel"] for m in ms if m["spawnRel"] is not None]
        pk = [m["peakOverHead"] for m in ms if m["peakOverHead"] is not None]
        L.append(f"{name} | {len(ms)} | {f(quart(d, 0.25), 1)} / {f(med(d), 1)} / {f(quart(d, 0.75), 1)} | {f(quart(g, 0.25))} / {f(med(g))} / {f(quart(g, 0.75))} | "
                 f"{f(quart(s, 0.25))} / {f(med(s))} / {f(quart(s, 0.75))} | {f(med(pk))}")

    L += ["", "[E2-5] squad10 发现集里的秩相关（Spearman ρ；p = 随机打乱 20,000 次的双侧置换 p，种子 136；只是排序同向与否，不是因果）",
          "列 A × 列 B | n | ρ | p"]
    sq10 = [m for m in M if m["cohort"] == "squad10"]
    pairs = [("选点间距（相对）", "spawnRel", "地的倍数 630→1530", "grow"), ("选点间距（相对）", "spawnRel", "峰值÷人头", "peakOverHead"),
             ("1530 拍密度", "dens1530", "地的倍数 630→1530", "grow"), ("1530 拍密度", "dens1530", "峰值÷人头", "peakOverHead"),
             ("地的倍数 630→1530", "grow", "峰值÷人头", "peakOverHead"), ("开局人数", "players", "地的倍数 630→1530", "grow"),
             ("开局人数", "players", "峰值÷人头", "peakOverHead"), ("被围占比", "boxedShare", "峰值÷人头", "peakOverHead"),
             ("开局人数", "players", "1530 拍密度", "dens1530")]
    for la, ka, lb, kb in pairs:
        ms = [m for m in sq10 if m.get(ka) is not None and m.get(kb) is not None]
        rho, p = spearman([m[ka] for m in ms], [m[kb] for m in ms])
        L.append(f"{la} × {lb} | {len(ms)} | {rho:+.2f} | {pf(p)}")
    L.append(f"# 共 {len(pairs)} 对；按 Bonferroni 折算的门槛是 {0.05 / len(pairs):.4f}")
    L += ["", "[E2-5b] 同上，控制开局人数之后的偏秩相关（三列取秩，A、B 的秩各自对开局人数的秩回归取残差，再算残差的相关；p = 置换）",
          "列 A × 列 B（控制开局人数） | n | 偏 ρ | p"]
    for la, ka, lb, kb in (("地的倍数 630→1530", "grow", "峰值÷人头", "peakOverHead"), ("1530 拍密度", "dens1530", "峰值÷人头", "peakOverHead"),
                           ("被围占比", "boxedShare", "峰值÷人头", "peakOverHead"), ("选点间距（相对）", "spawnRel", "地的倍数 630→1530", "grow"),
                           ("1530 拍密度", "dens1530", "地的倍数 630→1530", "grow")):
        ms = [m for m in sq10 if m.get(ka) is not None and m.get(kb) is not None and m.get("players")]
        rho, p = partial_spearman([m[ka] for m in ms], [m[kb] for m in ms], [m["players"] for m in ms])
        L.append(f"{la} × {lb} | {len(ms)} | {rho:+.2f} | {pf(p)}")

    L += ["", "[E2-6] squad10：按开局人数分三档看 630→1530 拍地的倍数与 1530 拍密度（人数少的房间 AI 地多，倍数天然高）",
          "开局人数档 | 局数（赢/输） | 地的倍数 中位：赢 / 输 | 1530 拍密度 中位：赢 / 输 | 峰值÷人头 中位：赢 / 输"]
    ps = sorted(m["players"] for m in sq10)
    c1, c2 = ps[len(ps) // 3], ps[2 * len(ps) // 3]
    for lo, hi, nm in ((0, c1, f"<{c1} 人"), (c1, c2, f"{c1}~{c2 - 1} 人"), (c2, 10 ** 9, f"≥{c2} 人")):
        ms = [m for m in sq10 if lo <= m["players"] < hi]
        w = [m for m in ms if m["result"] == "won"]
        l_ = [m for m in ms if m["result"] != "won"]

        def mm(xs, k):
            return f(med([m[k] for m in xs if m[k] is not None]))
        L.append(f"{nm} | {len(ms)}（{len(w)}/{len(l_)}） | {mm(w, 'grow')} / {mm(l_, 'grow')} | {mm(w, 'dens1530')} / {mm(l_, 'dens1530')} | {mm(w, 'peakOverHead')} / {mm(l_, 'peakOverHead')}")

    ex = exact_for_mine()
    L += ["", "[V] 替身量对精确值：R03 复盘的 11 局（精确值取自 out/cross/X12-summary.txt）",
          "局 | 日志疑似被拒占比（整局） 对 重放里没成交占比（100% − 成交÷日志） | 快照被围占比 对 决策拍被围占比 | 选点间距（相对） 对 出生份额 | 地的倍数 对 人均得AI+中立地比 630~1500"]
    xs = defaultdict(list)
    for mid in MINE:
        m = by[mid]
        rej_all = 100.0 * sum(m["rej"]) / sum(m["log"]) if sum(m["log"]) else None
        e_exec = ex.get("exec", {}).get(mid)
        e_nonexec = None if e_exec is None else 100.0 - e_exec
        pairs_v = (("rej", rej_all, e_nonexec), ("boxed", m["boxedShare"], ex.get("boxed", {}).get(mid)), ("spawn", m["spawnRel"], ex.get("spawn", {}).get(mid)),
                   ("grow", m["grow"], ex.get("aiGain", {}).get(mid)))
        for tag, a, b in pairs_v:
            if a is not None and b is not None:
                xs[tag].append((a, b))
        L.append(f"{mid} | {f(rej_all, 0)}% 对 {f(e_nonexec, 0)}% | {f(m['boxedShare'], 0)}% 对 {f(ex.get('boxed', {}).get(mid), 0)}% | {f(m['spawnRel'])} 对 {f(ex.get('spawn', {}).get(mid))} | "
                 f"{f(m['grow'])} 对 {f(ex.get('aiGain', {}).get(mid))}")
    cells = []
    for tag, nm in (("rej", "疑似被拒 × 没成交"), ("boxed", "快照被围 × 决策拍被围"), ("spawn", "选点间距 × 出生份额"), ("grow", "地的倍数 × 人均得AI+中立地比")):
        v = xs[tag]
        if len(v) >= 5:
            rho, p = spearman([a for a, _ in v], [b for _, b in v])
            cells.append(f"{nm} ρ={rho:+.2f}（n={len(v)}，p{'' if pf(p).startswith('<') else '='}{pf(p)}）")
    L.append("替身量与精确值的秩相关：" + "；".join(cells))

    L += ["", "[D] 逐局明细（squad10 的 75 局；* = R03 复盘的 11 局）",
          "局 | 结局 | 人数/队数 | <2142 日志→疑似被拒 | 整局日志→疑似被拒 | 被围占比 | 1530 拍密度 | 地的倍数 | 选点间距（相对） | 峰值÷人头"]
    for m in sorted(sq10, key=lambda m: m["mid"]):
        star = "*" if m["mid"] in MINE else ""
        L.append(f"{m['mid']}{star} | {m['result']} | {m['players']}/{m['teams']} | {m['log'][0]}→{m['rej'][0]} | {sum(m['log'])}→{sum(m['rej'])} | {f(m['boxedShare'], 0)}% | "
                 f"{f(m['dens1530'], 1)} | {f(m['grow'])} | {f(m['spawnRel'])} | {f(m['peakOverHead'])}")
    os.makedirs(os.path.join(ROOT, "out", "cross"), exist_ok=True)
    p = os.path.join(ROOT, "out", "cross", "E2-census.txt")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print(f"写 {os.path.relpath(p, ROOT)}（{len(L)} 行）")


if __name__ == "__main__":
    main()
