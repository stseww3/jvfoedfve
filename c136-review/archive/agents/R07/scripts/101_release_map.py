#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""101_release_map.py — R07：把录像里我方落地的指令和影子发令逐条对齐，得到每个号的「历史放行轨迹」（C2 用）。

输入：out/_cache/cp/<局>/H.json（100_checkpoint.mjs --chan H 的输出）
  · intents：历史策略在真实局面上影子运行时每个决策拍受理的那一条指令（桥接语义：一拍一条）
  · landed ：录像里我方每条指令的落地拍、种类、比例、目标
做法：每个号分别做。把这个号的落地帧按时间排好，每一帧里的指令倒过来（同一帧后发的先执行），
  在影子发令序列里找一段连续的发令和它逐条相同（种类、比例；目标不同记 0.3 个不符），
  要求各帧对上的发令段先后不交叉（先发的先落地）。用动态规划取总不符最少的对法；
  同分时取在途拍数和上一帧最接近的。
输出：out/<局>/release_map.json、release_map.txt
  · pts ：这个号每条落地指令的（发令拍, 在途拍数）
  · segs：成批放行且后面有指令没落地的段 {a: 这批第一条的发令拍, b: 下一批第一条的发令拍, T: 落地拍, n: 落地条数}
  · pool：全队在途拍数的滑动中位数（号在历史上已经不在、而离线对照里还在时用）
用法：python3 101_release_map.py <局> [<局> …]
"""
import bisect
import collections
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out")
PERIODS = [(0, 600, "0~600"), (600, 1500, "600~1500"), (1500, 3000, "1500~3000"), (3000, 10**9, "3000 以后")]


def cost(land, intent):
    """land: [t, bot, kind, dX, dZ, ...]；intent: (t, kind, pct, target)"""
    kind, dx, dz = land[2], land[3], land[4]
    _, ik, ip, it = intent
    if kind != ik:
        return 1.0
    if kind == "attack":
        if dx != ip:
            return 1.0
        return 0.0 if min(dz, 512) == min(it, 512) else 0.3
    if kind == "donate":
        if dx != ip:
            return 1.0
        return 0.0 if dz == it else 0.3
    if kind == "boat":
        if dx != ip:
            return 1.0
        return 0.0 if dz == it else 0.3
    if kind == "retreat":
        return 0.0 if dx == it else 0.3
    if kind == "recall":
        return 0.0 if dz == it else 0.3
    if kind == "chase":
        return 0.0 if (dx == ip and dz == it) else 0.3
    return 1.0


def align(frames, I):
    """frames: [(T, [land...])] 按 T 升序；I: [(t, kind, pct, target)] 按 t 升序。返回每帧对上的起点下标（-1 = 没对上）。"""
    m = len(frames)
    ts = [x[0] for x in I]
    cands = []
    for T, L in frames:
        rev = L[::-1]
        n = len(rev)
        hi = bisect.bisect_right(ts, T - 1)
        lo = bisect.bisect_left(ts, T - 1500)
        cl = []
        for j in range(lo, hi - n + 1):
            c = 0.0
            for a, b in zip(rev, I[j:j + n]):
                c += cost(a, b)
                if c > n * 0.7:
                    break
            if c <= n * 0.7:
                cl.append((c, j))
        cl.sort()
        if cl:
            best = cl[0][0]
            cl = [x for x in cl if x[0] <= best + 2.0][:80]
        cands.append([(j, c) for c, j in cl] + [(-1, 0.6 * n + 0.5)])
    # 动态规划：state = (帧, 起点)
    INF = float("inf")
    prev = {}
    back = []
    for k in range(m):
        T, L = frames[k]
        n = len(L)
        cur = {}
        bk = {}
        for j, c in cands[k]:
            lag = (T - I[j][0]) if j >= 0 else None
            if k == 0:
                cur[j] = (c * 100 + (0.001 * lag if lag is not None else 0), (j + n) if j >= 0 else 0, lag if lag is not None else 11)
                bk[j] = None
                continue
            bc = None
            for pj, (pc, pend, plag) in prev.items():
                if j >= 0 and j < pend:
                    continue
                cc = pc + c * 100
                if lag is not None:
                    cc += 0.02 * abs(lag - plag)
                if bc is None or cc < bc[0]:
                    bc = (cc, (j + n) if j >= 0 else pend, lag if lag is not None else plag, pj)
            if bc is not None:
                cur[j] = (bc[0], bc[1], bc[2])
                bk[j] = bc[3]
        prev = cur
        back.append(bk)
    if not prev:
        return [-1] * m
    j = min(prev, key=lambda x: prev[x][0])
    path = [0] * m
    for k in range(m - 1, -1, -1):
        path[k] = j
        j = back[k][j]
    return path


def qtile(a, f):
    if not a:
        return None
    s = sorted(a)
    return s[min(len(s) - 1, int(f * len(s)))]


def run(mid):
    hp = os.path.join(OUT, "_cache", "cp", mid, "H.json")
    h = json.load(open(hp, encoding="utf-8"))
    bots = [s["bot"] for s in h["squad"]]
    intents = collections.defaultdict(list)
    rejDon = collections.Counter()
    for t, b, kind, pct, target, rej in h["intents"]:
        if rej:
            rejDon[b] += 1
            continue
        intents[b].append((t, kind, pct, target))
    landed = collections.defaultdict(list)
    for r in h["landed"]:
        if r[2] == "leave":
            continue
        landed[r[1]].append(r)
    seats = {}
    tot = collections.Counter()
    lag_by_period = collections.defaultdict(list)
    all_pts = []
    lines = []
    for b in bots:
        I = intents[b]
        fr = collections.OrderedDict()
        for r in sorted(landed[b], key=lambda x: x[0]):
            fr.setdefault(r[0], []).append(r)
        frames = list(fr.items())
        path = align(frames, I)
        matched = [None] * len(I)   # intent 下标 → 落地拍
        pts = []
        st = collections.Counter()
        for k, (T, L) in enumerate(frames):
            j = path[k]
            n = len(L)
            st["landed"] += n
            if j < 0:
                st["unmatched"] += n
                continue
            for a, it_i in zip(L[::-1], range(j, j + n)):
                c = cost(a, I[it_i])
                st["exact" if c == 0 else "pctOnly" if c < 1 else "mis"] += 1
                matched[it_i] = T
                pts.append([I[it_i][0], T - I[it_i][0]])
        # 没落地的发令（不算捐款：捐款被配额拒掉本来就不进录像）
        dropped_idx = [i for i in range(len(I)) if matched[i] is None and I[i][1] != "donate"]
        st["intents"] = len(I)
        st["dropped"] = len(dropped_idx)
        st["donUnmatched"] = sum(1 for i in range(len(I)) if matched[i] is None and I[i][1] == "donate")
        st["rejDon"] = rejDon[b]
        # 成批放行且后面有指令没落地的段
        segs = []
        ks = [k for k in range(len(frames)) if path[k] >= 0]
        last_land_t = frames[-1][0] if frames else -1
        for q, k in enumerate(ks):
            T, L = frames[k]
            j = path[k]
            n = len(L)
            nj = path[ks[q + 1]] if q + 1 < len(ks) else len(I)
            nd = sum(1 for i in range(j + n, nj) if I[i][1] != "donate")
            if nd >= 1:
                b_tick = I[nj][0] if nj < len(I) else (I[-1][0] + 5)
                segs.append({"a": I[j][0], "b": b_tick, "T": T, "n": n, "dropped": nd})
        pts.sort()
        seats[b] = {"pts": pts, "segs": segs, "stat": dict(st)}
        for s, lag in pts:
            all_pts.append((s, lag))
            for lo, hi, name in PERIODS:
                if lo <= s < hi:
                    lag_by_period[name].append(lag)
        for k_, v_ in st.items():
            tot[k_] += v_
        tot["segs"] += len(segs)
        tot["segLanded"] += sum(s["n"] for s in segs)
        tot["segDropped"] += sum(s["dropped"] for s in segs)
        lines.append(f"{b}\t{st['landed']}\t{st['exact']}\t{st['pctOnly']}\t{st['mis']}\t{st['unmatched']}\t{st['intents']}\t{st['dropped']}\t{st['rejDon']}\t{len(segs)}\t"
                     + "、".join(f"{s['a']}~{s['b']}→{s['T']}（{s['n']} 条，另 {s['dropped']} 条没落地）" for s in segs[:6]) + ("…" if len(segs) > 6 else ""))
    # 全队在途拍数的滑动中位数
    all_pts.sort()
    pool = []
    if all_pts:
        ss = [p[0] for p in all_pts]
        t_end = ss[-1]
        for c in range(0, t_end + 51, 50):
            lo = bisect.bisect_left(ss, c - 150)
            hi = bisect.bisect_right(ss, c + 150)
            if hi > lo:
                pool.append([c, statistics.median(p[1] for p in all_pts[lo:hi])])
    res = {"matchId": mid, "ver": h["ver"], "seats": seats, "pool": pool, "total": dict(tot),
           "lagByPeriod": {k: {"n": len(v), "p50": qtile(v, 0.5), "p90": qtile(v, 0.9), "max": max(v)} for k, v in lag_by_period.items()}}
    os.makedirs(os.path.join(OUT, mid), exist_ok=True)
    json.dump(res, open(os.path.join(OUT, mid, "release_map.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    L = []
    P = L.append
    P(f"# {mid} 历史放行轨迹（101_release_map.py；策略 {h['ver']}；录像落地 vs 影子发令逐条对齐）")
    P(f"# 录像里我方落地 {tot['landed']} 条：种类、比例、目标都对上 {tot['exact']}，种类和比例对上 {tot['pctOnly']}，不符 {tot['mis']}，没对上 {tot['unmatched']}"
      f"（对上率 {(tot['exact'] + tot['pctOnly']) / max(1, tot['landed']):.1%}）")
    P(f"# 影子发令 {tot['intents']} 条（不含发令时就会被配额拒掉的捐款 {tot['rejDon']} 条）：落地 {tot['exact'] + tot['pctOnly'] + tot['mis']}，没落地 {tot['dropped']}（另有没落地的捐款 {tot['donUnmatched']} 条）")
    P(f"# 成批放行且后面有指令没落地的段 {tot['segs']} 个：段里落地 {tot['segLanded']} 条，没落地 {tot['segDropped']} 条")
    P("# 在途拍数（落地拍 − 发令拍），按发令拍分段：" + "；".join(
        f"{name} {res['lagByPeriod'][name]['n']} 条 P50 {res['lagByPeriod'][name]['p50']} / P90 {res['lagByPeriod'][name]['p90']} / 最大 {res['lagByPeriod'][name]['max']}"
        for _, _, name in PERIODS if name in res["lagByPeriod"]))
    P("号\t落地\t全对上\t种类比例对上\t不符\t没对上\t影子发令\t没落地\t发令时被拒的捐款\t段数\t前几段（发令拍范围→落地拍）")
    L.extend(lines)
    open(os.path.join(OUT, mid, "release_map.txt"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L[:5]))


if __name__ == "__main__":
    for mid in sys.argv[1:]:
        run(mid)
