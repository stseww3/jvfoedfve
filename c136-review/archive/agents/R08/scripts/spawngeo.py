#!/usr/bin/env python3
"""spawngeo.py — 出生点的几何账（真值落点）：贴边、扎堆、异队编队友挨着。

    python3 spawngeo.py <matchId> [--quiet]        # 读 out/<matchId>/resim.json，写 spawngeo.txt + spawngeo_sum.json

[QA] 离地图边的距离：编队 vs 其他真人（中位、四分位、≤12% 短边的个数）
[QB] 最近的真人 / 最近的编队友 / 最近的非编队真人（像素）：编队 vs 其他真人
[QC] 编队号的团（单链聚类，相距 ≤ LINK 像素连成一团）：每团的号、队的构成、团里异队的号对数
[QD] 贴同一条边排成一排（离同一条边 ≤ EDGE 像素、沿边相邻间距 ≤ 2×LINK 的 ≥3 个号）
[QE] 每个编队号最近的 3 个真人：是不是编队友、是不是同队
"""
import json
import math
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from truth import Truth, OUT  # noqa: E402

LINK = 260


def q(vals, f):
    s = sorted(vals)
    if not s:
        return 0
    return s[min(len(s) - 1, int(f * len(s)))]


def main():
    argv = sys.argv[1:]
    quiet = "--quiet" in argv
    mid = [a for a in argv if not a.startswith("--")][0]
    T = Truth(mid)
    R = T.R
    W, Hh = R["W"], R["Hh"]
    edge_lim = round(0.12 * min(W, Hh))
    xy = {p: R["spawnXY"][p] for p in range(T.H) if R["spawnXY"][p]}
    sq = [p for p in sorted(T.sqIds) if p in xy]
    oth = [p for p in xy if p not in T.sqIds]
    nm = {p: n for n, p in T.squad.items()}

    def edge(p):
        x, y = xy[p]
        return min(x, W - x, y, Hh - y)

    def which_edge(p):
        x, y = xy[p]
        d = {"左": x, "右": W - x, "上": y, "下": Hh - y}
        return min(d, key=d.get)

    def dist(a, b):
        return math.hypot(xy[a][0] - xy[b][0], xy[a][1] - xy[b][1])

    def nearest(p, pool):
        c = [dist(p, o) for o in pool if o != p]
        return min(c) if c else float("inf")

    out = []
    eS, eO = [edge(p) for p in sq], [edge(p) for p in oth]
    out.append(f"[QA] {mid} 出生点离地图边的距离（地图 {W}×{Hh}，短边的 12% = {edge_lim} 像素）")
    out.append(f"  编队 {len(sq)} 个号：中位 {statistics.median(eS):.0f}、下四分位 {q(eS, 0.25)}、上四分位 {q(eS, 0.75)}；离边 ≤{edge_lim} 的 {sum(1 for v in eS if v <= edge_lim)} 个（{100 * sum(1 for v in eS if v <= edge_lim) / len(eS):.0f}%）")
    out.append(f"  其他真人 {len(oth)} 个：中位 {statistics.median(eO):.0f}、下四分位 {q(eO, 0.25)}、上四分位 {q(eO, 0.75)}；离边 ≤{edge_lim} 的 {sum(1 for v in eO if v <= edge_lim)} 个（{100 * sum(1 for v in eO if v <= edge_lim) / max(len(eO), 1):.0f}%）")
    out.append("  逐号（离边从近到远）：" + "；".join(f"{nm[p]}(T{T.team(p)}) {edge(p)}（{which_edge(p)}）" for p in sorted(sq, key=edge)))

    allp = list(xy)
    nnS = [nearest(p, allp) for p in sq]
    nnO = [nearest(p, allp) for p in oth]
    nmS = [nearest(p, sq) for p in sq]
    nwS = [nearest(p, oth) for p in sq]
    out.append("")
    out.append("[QB] 最近的真人（像素）")
    out.append(f"  编队：最近的任意真人 中位 {statistics.median(nnS):.0f}｜最近的编队友 中位 {statistics.median(nmS):.0f}｜最近的非编队真人 中位 {statistics.median(nwS):.0f}｜最近的真人就是编队友的 {sum(1 for a, b in zip(nmS, nwS) if a <= b)}/{len(sq)} 个")
    out.append(f"  其他真人：最近的任意真人 中位 {statistics.median(nnO):.0f}")

    # 单链聚类
    par = {p: p for p in sq}

    def find(a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a

    for i, a in enumerate(sq):
        for b in sq[i + 1:]:
            if dist(a, b) <= LINK:
                par[find(a)] = find(b)
    groups = {}
    for p in sq:
        groups.setdefault(find(p), []).append(p)
    gl = sorted(groups.values(), key=lambda g: -len(g))
    out.append("")
    out.append(f"[QC] 编队号的团（相距 ≤{LINK} 像素连成一团）：{len(gl)} 团；≥3 个号的团 {sum(1 for g in gl if len(g) >= 3)} 个，装了 {sum(len(g) for g in gl if len(g) >= 3)} 个号")
    summ_groups = []
    for g in gl:
        teams = {}
        for p in g:
            teams[T.team(p)] = teams.get(T.team(p), 0) + 1
        cross = sum(1 for i, a in enumerate(g) for b in g[i + 1:] if not T.same(a, b) and dist(a, b) <= LINK)
        same = sum(1 for i, a in enumerate(g) for b in g[i + 1:] if T.same(a, b) and dist(a, b) <= LINK)
        cx = sum(xy[p][0] for p in g) / len(g)
        cy = sum(xy[p][1] for p in g) / len(g)
        out.append(f"  {len(g)} 个号（中心 {cx:.0f},{cy:.0f}）：" + " ".join(f"{nm[p]}(T{T.team(p)})" for p in sorted(g, key=lambda p: xy[p]))
                   + "｜队的构成 " + " ".join(f"T{k}×{v}" for k, v in sorted(teams.items())) + f"｜≤{LINK} 像素的号对：异队 {cross}、同队 {same}")
        summ_groups.append(dict(n=len(g), bots=[nm[p] for p in g], teams=teams, crossPairs=cross, samePairs=same))

    out.append("")
    out.append(f"[QD] 贴同一条边排成一排（离这条边 ≤{edge_lim} 像素；沿边相邻间距 ≤{2 * LINK}）")
    rows = []
    for side in ("上", "下", "左", "右"):
        on = [p for p in sq if which_edge(p) == side and edge(p) <= edge_lim]
        key = (lambda p: xy[p][0]) if side in ("上", "下") else (lambda p: xy[p][1])
        on.sort(key=key)
        run = []
        for p in on + [None]:
            if p is not None and (not run or key(p) - key(run[-1]) <= 2 * LINK):
                run.append(p)
                continue
            if len(run) >= 3:
                gaps = [key(run[i + 1]) - key(run[i]) for i in range(len(run) - 1)]
                out.append(f"  {side}沿 {len(run)} 个号：" + " ".join(f"{nm[x]}(T{T.team(x)})@{key(x)}" for x in run) + f"｜相邻间距 {gaps}｜队 " + " ".join(sorted({f'T{T.team(x)}' for x in run})))
                rows.append(dict(side=side, bots=[nm[x] for x in run], gaps=gaps, teams=sorted({T.team(x) for x in run})))
            run = [p] if p is not None else []
    if not rows:
        out.append("  无")

    out.append("")
    out.append("[QE] 每个编队号最近的 3 个真人：号 | 最近 3 个（距离；* = 编队友；= 同队 / ≠ 异队）")
    nn3cross = 0
    for p in sq:
        near = sorted((o for o in allp if o != p), key=lambda o: dist(p, o))[:3]
        cells = []
        for o in near:
            mate = o in T.sqIds
            if mate and not T.same(o, p):
                nn3cross += 1
            cells.append(f"{T.nm(o)} {dist(p, o):.0f}{'=' if T.same(o, p) else '≠'}")
        out.append(f"    {nm[p]:<16} | " + "；".join(cells))
    out.append(f"  最近 3 个真人里是异队编队友的：{nn3cross} / {3 * len(sq)}")

    summ = dict(matchId=mid, W=W, H=Hh, edgeLimit=edge_lim,
                squad=dict(n=len(sq), edgeMedian=statistics.median(eS), nearEdge=sum(1 for v in eS if v <= edge_lim), nnAny=statistics.median(nnS), nnMate=statistics.median(nmS), nnWild=statistics.median(nwS),
                           nearestIsMate=sum(1 for a, b in zip(nmS, nwS) if a <= b)),
                others=dict(n=len(oth), edgeMedian=statistics.median(eO), nearEdge=sum(1 for v in eO if v <= edge_lim), nnAny=statistics.median(nnO)),
                groups=summ_groups, edgeRows=rows, nn3CrossTeamMates=nn3cross)
    txt = "\n".join(out) + "\n"
    with open(os.path.join(OUT, mid, "spawngeo.txt"), "w", encoding="utf-8") as f:
        f.write(txt)
    with open(os.path.join(OUT, mid, "spawngeo_sum.json"), "w", encoding="utf-8") as f:
        json.dump(summ, f, ensure_ascii=False, indent=1)
    if quiet:
        print(f"{mid}: spawngeo.txt {len(out)} 行")
    else:
        print(txt)


if __name__ == "__main__":
    main()
