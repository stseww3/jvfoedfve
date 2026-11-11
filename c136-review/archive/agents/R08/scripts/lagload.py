#!/usr/bin/env python3
"""lagload.py — 指令时延和房间『活动量』的对照（每 180 拍一窗）。

    python3 lagload.py <matchId> [--quiet]      # 读 out/<matchId>/resim.json + shadowcmp.txt 的 [SF]；写 lagload.txt + lagload_sum.json

活动量（全房真值，录像重演得到，和编队无关）：
  · 换手的格数：这一窗里所有进攻（真人、内置 AI、打无主地）拿到的格数合计（pairLog 的 tiles）
  · 推进次数：pairLog 的 nExpand 合计（引擎 expandAttack 这一窗里推进了多少次——模拟一拍要做的工作量的代理）
  · 交战对数：这一窗里有推进的（进攻方, 目标）对数
  · 有地的玩家数：窗口中点时还有地的真人 / 内置 AI
时延：shadowcmp.py [SF] 的全队时延曲线（配上影子的已执行指令，中位 / P90 / 最大）。
输出 [LL-A] 逐窗表、[LL-B] 时延中位 ≥35 拍的窗 vs 其余窗的活动量对比、[LL-C] 秩相关（Spearman）、[LL-D] 时延波段（连续 ≥35 拍）的起止和当时的活动量。
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from truth import Truth, OUT  # noqa: E402

STEP = 180


def spearman(xs, ys):
    n = len(xs)
    if n < 3:
        return None

    def rank(v):
        order = sorted(range(n), key=lambda i: v[i])
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2 + 1
            i = j + 1
        return r

    rx, ry = rank(xs), rank(ys)
    mx, my = sum(rx) / n, sum(ry) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    sx = sum((a - mx) ** 2 for a in rx) ** 0.5
    sy = sum((b - my) ** 2 for b in ry) ** 0.5
    return sxy / (sx * sy) if sx and sy else None


def main():
    argv = sys.argv[1:]
    quiet = "--quiet" in argv
    mid = [a for a in argv if not a.startswith("--")][0]
    T = Truth(mid)
    R = T.R
    lag = {}
    p = os.path.join(OUT, mid, "shadowcmp.txt")
    if os.path.exists(p):
        on = False
        for line in open(p, encoding="utf-8"):
            if line.startswith("[SF]"):
                on = True
                continue
            if on:
                m = re.match(r"\s*(\d+)~\s*(\d+) \| 指令\s+(\d+) \| 时延 中位 (\d+) / P90 (\d+) / 最大 (\d+) \| 陆攻 (\d+) 条，其中无效 (\d+)", line)
                if m:
                    a = int(m.group(1))
                    lag[a] = dict(n=int(m.group(3)), p50=int(m.group(4)), p90=int(m.group(5)), mx=int(m.group(6)), atk=int(m.group(7)), void=int(m.group(8)))
                elif line.startswith("["):
                    break
    wins = {}
    for r in R["pairLog"]:
        w = ((r[0] - 1) // STEP) * STEP
        e = wins.setdefault(w, dict(tiles=0, expand=0, pairs=set(), humanTiles=0))
        e["tiles"] += r[3]
        e["expand"] += r[7] if len(r) > 7 else 0
        e["pairs"].add((r[1], r[2]))
        if r[1] < T.H and r[2] < T.H:
            e["humanTiles"] += r[3]
    H = T.H
    snapT = R["snapT"]
    ai_rows = [(r[0], sum(1 for x in r[1] if x[1] > 0)) for r in R.get("snapAi", [])]
    rows = []
    out = [f"[LL-A] {mid} 每 {STEP} 拍一窗：窗 | 全房换手的格数（其中真人打真人）| 推进次数 | 交战对数 | 有地的真人 / 内置 AI | 编队已执行指令 | 时延 中位 / P90 / 最大 | 陆攻无效占比"]
    for w in range(0, T.end, STEP):
        e = wins.get(w, dict(tiles=0, expand=0, pairs=set(), humanTiles=0))
        tm = min(w + STEP // 2, T.end)
        i = min(range(len(snapT)), key=lambda k: abs(snapT[k] - tm))
        nh = sum(1 for q in range(H) if R["snapTerr"][i][q] > 0)
        nai = min(ai_rows, key=lambda x: abs(x[0] - tm))[1] if ai_rows else None
        lg = lag.get(w)
        rows.append(dict(w=w, tiles=e["tiles"], humanTiles=e["humanTiles"], expand=e["expand"], pairs=len(e["pairs"]), humans=nh, ais=nai, lag=lg))
        out.append(f"  {w:>6}~{w + STEP - 1:<6} | {e['tiles']:>7}（{e['humanTiles']}）| {e['expand']:>6} | {len(e['pairs']):>4} | {nh} / {nai if nai is not None else '–'} | "
                   + (f"{lg['n']:>3} | {lg['p50']} / {lg['p90']} / {lg['mx']} | {100 * lg['void'] / max(lg['atk'], 1):.0f}%" if lg else "  – | – | –"))
    have = [r for r in rows if r["lag"] and r["lag"]["n"] >= 5]
    slow = [r for r in have if r["lag"]["p50"] >= 35]
    fast = [r for r in have if r["lag"]["p50"] < 35]

    def med(v):
        s = sorted(v)
        return s[len(s) // 2] if s else 0

    out.append("")
    out.append(f"[LL-B] 时延中位 ≥35 拍的窗 {len(slow)} 个 vs 其余 {len(fast)} 个（只算编队已配上 ≥5 条指令的窗）：")
    for key, lab in (("tiles", "换手的格数"), ("expand", "推进次数"), ("pairs", "交战对数"), ("humans", "有地的真人")):
        out.append(f"  {lab}：慢窗 中位 {med([r[key] for r in slow])}（最小 {min([r[key] for r in slow], default=0)}、最大 {max([r[key] for r in slow], default=0)}）｜快窗 中位 {med([r[key] for r in fast])}（最小 {min([r[key] for r in fast], default=0)}、最大 {max([r[key] for r in fast], default=0)}）")
    out.append("")
    out.append("[LL-C] 秩相关（Spearman；逐窗的时延中位 对 活动量）：")
    cor = {}
    for key, lab in (("tiles", "换手的格数"), ("expand", "推进次数"), ("pairs", "交战对数"), ("humans", "有地的真人")):
        c = spearman([r[key] for r in have], [r["lag"]["p50"] for r in have])
        cor[key] = round(c, 2) if c is not None else None
        out.append(f"  {lab}：{cor[key]}（{len(have)} 个窗）")
    # 前一窗的活动量（积压是累出来的）
    prev = [(have[i - 1]["tiles"], have[i]["lag"]["p50"]) for i in range(1, len(have)) if have[i]["w"] - have[i - 1]["w"] == STEP]
    c = spearman([a for a, _ in prev], [b for _, b in prev]) if len(prev) >= 3 else None
    cor["tilesPrev"] = round(c, 2) if c is not None else None
    out.append(f"  前一窗换手的格数：{cor['tilesPrev']}（{len(prev)} 个窗）")
    out.append("")
    out.append("[LL-D] 时延波段（连续的慢窗）：起止 | 窗数 | 时延中位的峰值 | 段内换手格数 中位 / 峰值 | 段前一窗、段后一窗的换手格数")
    waves = []
    cur = []
    for r in have + [None]:
        if r is not None and r["lag"]["p50"] >= 35 and (not cur or r["w"] - cur[-1]["w"] == STEP):
            cur.append(r)
            continue
        if cur:
            before = next((x for x in rows if x["w"] == cur[0]["w"] - STEP), None)
            after = next((x for x in rows if x["w"] == cur[-1]["w"] + STEP), None)
            waves.append(dict(t0=cur[0]["w"], t1=cur[-1]["w"] + STEP, n=len(cur), peakLag=max(x["lag"]["p50"] for x in cur), tilesMed=med([x["tiles"] for x in cur]), tilesMax=max(x["tiles"] for x in cur),
                              before=before["tiles"] if before else None, after=after["tiles"] if after else None))
            w = waves[-1]
            out.append(f"  {w['t0']}~{w['t1']} | {w['n']} | {w['peakLag']} | {w['tilesMed']} / {w['tilesMax']} | 前 {w['before']}、后 {w['after']}")
        cur = [r] if (r is not None and r["lag"]["p50"] >= 35) else []
    if not waves:
        out.append("  无")
    txt = "\n".join(out) + "\n"
    with open(os.path.join(OUT, mid, "lagload.txt"), "w", encoding="utf-8") as f:
        f.write(txt)
    with open(os.path.join(OUT, mid, "lagload_sum.json"), "w", encoding="utf-8") as f:
        json.dump(dict(matchId=mid, step=STEP, rows=rows, slowWindows=len(slow), fastWindows=len(fast), spearman=cor, waves=waves,
                       slowTilesMedian=med([r["tiles"] for r in slow]), fastTilesMedian=med([r["tiles"] for r in fast])), f, ensure_ascii=False, indent=1)
    if quiet:
        print(f"{mid}: lagload.txt {len(out)} 行")
    else:
        print(txt)


if __name__ == "__main__":
    main()
