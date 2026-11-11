#!/usr/bin/env python3
"""landcap.py — 好地实际抢到多少（HUB 广播 0007 第 3 项）。全部从真引擎重放出的归属网格算（eng_replay.cjs 写的 out/<id>/grids.bin.gz）。

口径：
  · 天然份额（Voronoi）：以开局第 0 拍每个真人脚下的出生格为源，沿陆地 4 邻接同时向外扩（多源 BFS），每个陆地格归给「走陆路最近」的真人；
    走陆路到不了任何真人的格（没有真人的岛）单列。另给一份直线距离版（每个陆地格归给直线最近的真人出生点）作对照。
    人头份额 = 我方号数 / 真人数。两个号出生在同一像素时，引擎只留一个号的出生格在网格上，另一个号的天然份额记 0（单列）。
  · 兑现率 = 某拍领土 ÷ 天然份额（陆路版）。看 t=630（开局滚雪球结束）和 t=1500（没重放到就用最后一拍）。
  · 天然份额里的地在该拍归谁：自己 / 我方别的号 / 其他真人 / 内置 AI / 无主地。
  · 内置 AI 地的去向：t=630 时「与我方领土接壤」或「一半以上的格落在我方天然份额里」的内置 AI，它们 t=630 的格在之后各快照归谁。
  · 三层归因（t=600~1500）：① 天然份额小（出生扎堆/偏角）；② 策略自己不出兵（影子逐拍流水里卡在底线/地价闸的决策拍）；③ 出了兵但迟到落空（latency.py 的 A1/B 类和改挂比例）。

用法：python3 landcap.py <matchId> [voronoi|capture|natural|ai|flow|layers|json|all]
"""
import gzip
import json
import os
import sys
from collections import defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from r06lib import OUT, load_match, pname  # noqa: E402

NEUTRAL = 512
NOTLAND = 65535


def fmt(n):
    n = int(n)
    a = abs(n)
    if a >= 10 ** 6:
        return f"{n / 1e6:.2f}M"
    if a >= 10 ** 5:
        return f"{n / 1e3:.0f}k"
    return str(n)


def med(v):
    v = sorted(v)
    return v[len(v) // 2] if v else None


def pc(a, b):
    return f"{100 * a / b:.1f}%" if b else '-'


class Ctx:
    pass


def load(mid):
    X = Ctx()
    X.M = M = load_match(mid)
    S = M.sim
    if not S or not S.get('grids'):
        return None
    X.S = S
    G = S['grids']
    X.W, X.Hh = G['W'], G['H']
    X.gt = G['ticks']
    raw = gzip.open(os.path.join(OUT, mid, G['file'])).read()
    n = X.W * X.Hh
    assert len(raw) == 2 * n * len(X.gt), (len(raw), n, len(X.gt))
    X.grid = {t: np.frombuffer(raw, dtype='<u2', count=n, offset=2 * n * i) for i, t in enumerate(X.gt)}
    X.H = S['humans']
    X.team = S['teams']
    X.squad = sorted(M.bots)
    X.land = X.grid[X.gt[0]] != NOTLAND
    X.nland = int(X.land.sum())
    X.last = S['endT']
    X.counts = {t: np.bincount(g[X.land].astype(np.int64), minlength=NEUTRAL + 1)[:NEUTRAL + 1] for t, g in X.grid.items()}
    return X


def tick_for(X, want):
    """网格快照里 <= want 的最后一拍（没有就取第一拍）。"""
    c = [t for t in X.gt if t <= want]
    return c[-1] if c else X.gt[0]


def name(X, p):
    return pname(X.M, p)


def bfs_voronoi(X):
    """陆路多源 BFS。返回 lab（每格归哪个真人；-1 = 陆路到不了；-2 = 不是陆地）和 dist。"""
    if getattr(X, '_vor', None) is not None:
        return X._vor
    W, n = X.W, X.W * X.Hh
    g0 = X.grid[X.gt[0]]
    lab = np.full(n, -2, dtype=np.int32)
    lab[X.land] = -1
    dist = np.full(n, -1, dtype=np.int32)
    src = np.flatnonzero(g0 < X.H)
    lab[src] = g0[src]
    dist[src] = 0
    front = src
    d = 0
    while front.size:
        d += 1
        ci, cl = [], []
        x = front % W
        for off, ok in ((-1, x != 0), (1, x != W - 1), (-W, front >= W), (W, front < n - W)):
            f = front[ok]
            nb = f + off
            m = lab[nb] == -1
            ci.append(nb[m])
            cl.append(lab[f[m]])
        idx = np.concatenate(ci)
        if not idx.size:
            break
        lbs = np.concatenate(cl)
        u, first = np.unique(idx, return_index=True)
        lab[u] = lbs[first]
        dist[u] = d
        front = u
    X._vor = (lab, dist)
    return X._vor


def euclid_voronoi(X):
    if getattr(X, '_euc', None) is not None:
        return X._euc
    S = X.S
    pts, ids = [], []
    for p in range(X.H):
        b = S['spawnAll'].get(str(p))
        if b:
            pts.append(((b[0] + b[2]) / 2, (b[1] + b[3]) / 2))
            ids.append(p)
    pts = np.array(pts, dtype=np.float32)
    cells = np.flatnonzero(X.land)
    cx = (cells % X.W).astype(np.float32)
    cy = (cells // X.W).astype(np.float32)
    lab = np.full(X.W * X.Hh, -2, dtype=np.int32)
    out = np.empty(cells.size, dtype=np.int32)
    CH = 100000
    for i in range(0, cells.size, CH):
        dx = cx[i:i + CH, None] - pts[None, :, 0]
        dy = cy[i:i + CH, None] - pts[None, :, 1]
        out[i:i + CH] = np.argmin(dx * dx + dy * dy, axis=1)
    lab[cells] = np.array(ids, dtype=np.int32)[out]
    X._euc = lab
    return lab


def shares(X):
    """每个真人的天然份额（陆路、直线）和出生点。"""
    if getattr(X, '_sh', None):
        return X._sh
    lab, dist = bfs_voronoi(X)
    eu = euclid_voronoi(X)
    vb = np.bincount(lab[lab >= 0], minlength=X.H)
    ve = np.bincount(eu[eu >= 0], minlength=X.H)
    sp = {}
    for p in range(X.H):
        b = X.S['spawnAll'].get(str(p))
        sp[p] = ((b[0] + b[2]) // 2, (b[1] + b[3]) // 2) if b else None
    # 录像里的出生像素（同像素时 spawnAll 里只有一个号有格）
    for p in range(X.H):
        if sp[p] is None and p in X.M.spawnXY:
            sp[p] = tuple(X.M.spawnXY[p])
    X._sh = dict(vb=vb, ve=ve, sp=sp, unreach=int((lab == -1).sum()))
    return X._sh


def nearest(X, p):
    sh = shares(X)
    a = sh['sp'][p]
    best = None
    for q in range(X.H):
        if q == p or sh['sp'][q] is None or a is None:
            continue
        d = ((a[0] - sh['sp'][q][0]) ** 2 + (a[1] - sh['sp'][q][1]) ** 2) ** 0.5
        if best is None or d < best[0]:
            best = (d, q)
    return best


def sec_voronoi(X):
    sh = shares(X)
    vb, ve = sh['vb'], sh['ve']
    sq = X.squad
    oth = [p for p in range(X.H) if p not in X.M.bots]
    tot = int(vb.sum())
    s_b, s_e = int(sum(vb[p] for p in sq)), int(sum(ve[p] for p in sq))
    head = len(sq) / X.H
    print(f"== {X.M.id} 天然份额（Voronoi，按真实出生点）：陆地 {X.nland} 格，真人 {X.H} 个（我方 {len(sq)} 个 = 人头份额 {100 * head:.1f}%）；走陆路到不了任何真人的 {sh['unreach']} 格（{pc(sh['unreach'], X.nland)}）")
    print(f"   陆路版：我方合计 {s_b} 格 = 可达陆地的 {pc(s_b, tot)}（÷人头份额 = {s_b / tot / head:.2f}）；每号中位 {med([int(vb[p]) for p in sq])} 格，其他真人中位 {med([int(vb[p]) for p in oth])} 格；"
          f"人均 我方 {s_b // len(sq)} / 其他真人 {(tot - s_b) // max(1, len(oth))} / 全场 {tot // X.H}")
    print(f"   直线版：我方合计 {s_e} 格 = 陆地的 {pc(s_e, X.nland)}（÷人头份额 = {s_e / X.nland / head:.2f}）；每号中位 {med([int(ve[p]) for p in sq])} 格，其他真人中位 {med([int(ve[p]) for p in oth])} 格")
    rank = sorted(range(X.H), key=lambda p: -vb[p])
    rk = {p: i + 1 for i, p in enumerate(rank)}
    par = tot / X.H
    small = [p for p in sq if vb[p] < 0.5 * par]
    print(f"   我方天然份额不到全场人均一半（< {par / 2:.0f} 格）的 {len(small)} 个号；排在全场真人前 16 名（前四分之一）的 {sum(1 for p in sq if rk[p] <= X.H // 4)} 个号、后 16 名的 {sum(1 for p in sq if rk[p] > X.H - X.H // 4)} 个号")
    by_team = defaultdict(lambda: [0, 0, 0, 0])
    for p in range(X.H):
        r = by_team[X.team[p]]
        r[0] += 1
        r[1] += int(vb[p])
        if p in X.M.bots:
            r[2] += 1
            r[3] += int(vb[p])
    print('   各队（人数 / 天然份额 / 人均；括号内 = 其中我方号数、我方的天然份额）：' + '；'.join(
        f"队{t} {r[0]} 人 {r[1]} 格 人均 {r[1] // max(1, r[0])}（我方 {r[2]} 个号 {r[3]} 格）" for t, r in sorted(by_team.items())))
    rows = []
    for p in sorted(sq, key=lambda p: -vb[p]):
        nb = nearest(X, p)
        kind = '-'
        if nb:
            q = nb[1]
            kind = ('我方' if q in X.M.bots else '其他真人') + ('同队' if X.team[q] == X.team[p] else '异队')
        rows.append(dict(me=p, name=name(X, p), team=X.team[p], vor=int(vb[p]), rank=rk[p], euclid=int(ve[p]), spawn=sh['sp'][p],
                         nearest=round(nb[0]) if nb else None, nearestWho=name(X, nb[1]) if nb else None, nearestKind=kind))
        r = rows[-1]
        print(f"      {r['name']:14s} 队{r['team']} 出生 {str(r['spawn']):12s} 天然份额 {r['vor']:6d} 格（全场第 {r['rank']:2d}/{X.H}；直线版 {r['euclid']:6d}）；最近的真人 {r['nearestWho']}（{kind}）{r['nearest']} 格")
    return dict(land=X.nland, humans=X.H, squad=len(sq), unreach=sh['unreach'], reach=tot, squadVor=s_b, squadVorPct=round(100 * s_b / tot, 2), headPct=round(100 * head, 2),
                ratio=round(s_b / tot / head, 3), squadMed=med([int(vb[p]) for p in sq]), otherMed=med([int(vb[p]) for p in oth]), squadEuclid=s_e,
                squadEuclidPct=round(100 * s_e / X.nland, 2), euclidSquadMed=med([int(ve[p]) for p in sq]), euclidOtherMed=med([int(ve[p]) for p in oth]),
                small=len(small), top16=sum(1 for p in sq if rk[p] <= X.H // 4), bottom16=sum(1 for p in sq if rk[p] > X.H - X.H // 4), bots=rows,
                teams={str(t): r for t, r in sorted(by_team.items())})


def cap_ticks(X):
    out = []
    for want in (630, 1500):
        t = tick_for(X, want)
        if t not in out and t > 0:
            out.append(t)
    if X.gt[-1] not in out and X.gt[-1] < 1500:
        out.append(X.gt[-1])
    return out


def sec_capture(X):
    sh = shares(X)
    vb = sh['vb']
    sq = X.squad
    oth = [p for p in range(X.H) if p not in X.M.bots]
    out = []
    print('-- 兑现率 = 领土 ÷ 天然份额（陆路版）。合计行 = 一群号的领土之和 ÷ 天然份额之和；中位 = 各号兑现率的中位（天然份额为 0 的号不算）')
    for t in cap_ticks(X):
        c = X.counts[t]
        def agg(ps):
            tv = sum(int(vb[p]) for p in ps)
            tt = sum(int(c[p]) for p in ps)
            rr = [c[p] / vb[p] for p in ps if vb[p] > 0]
            return tt, tv, (tt / tv if tv else 0), med(rr), sum(1 for p in ps if c[p] == 0)
        a, b = agg(sq), agg(oth)
        ai = int(c[X.H:NEUTRAL].sum())
        print(f"   t={t}：我方 领土 {a[0]} ÷ 天然 {a[1]} = {100 * a[2]:.1f}%（各号中位 {100 * a[3]:.1f}%；已出局 {a[4]} 个）｜其他真人 {b[0]} ÷ {b[1]} = {100 * b[2]:.1f}%（中位 {100 * b[3]:.1f}%；已出局 {b[4]} 个）"
              f"｜全场：真人 {a[0] + b[0]} 格（{pc(a[0] + b[0], X.nland)}）、内置 AI {ai} 格（{pc(ai, X.nland)}）、无主地 {int(c[NEUTRAL])} 格（{pc(int(c[NEUTRAL]), X.nland)}）")
        teams = defaultdict(lambda: [0, 0, 0, 0])
        for p in range(X.H):
            k = (X.team[p], p in X.M.bots)
            teams[k][0] += int(c[p])
            teams[k][1] += int(vb[p])
            teams[k][2] += 1
        print('      按队：' + '；'.join(f"队{k[0]}{'我方' if k[1] else '其他'} {v[2]} 人 {v[0]}÷{v[1]}={pc(v[0], v[1])}" for k, v in sorted(teams.items())))
        out.append(dict(t=t, squadTerr=a[0], squadVor=a[1], squadRate=round(a[2], 4), squadMedRate=round(float(a[3]), 4) if a[3] is not None else None, squadDead=a[4],
                        otherTerr=b[0], otherVor=b[1], otherRate=round(b[2], 4), otherMedRate=round(float(b[3]), 4) if b[3] is not None else None, otherDead=b[4],
                        aiLand=ai, neutral=int(c[NEUTRAL]), teams={f"{k[0]}{'s' if k[1] else 'o'}": v[:3] for k, v in sorted(teams.items())}))
    ts = cap_ticks(X)
    print('   各号（领土 / 兑现率）：' + ' '.join(f"t={t}" for t in ts))
    for p in sorted(sq, key=lambda p: -vb[p]):
        print(f"      {name(X, p):14s} 队{X.team[p]} 天然 {int(vb[p]):6d}｜" + '｜'.join(f"{int(X.counts[t][p]):6d} {pc(int(X.counts[t][p]), int(vb[p])):>7s}" for t in ts))
    # 其他真人的分布，给个参照
    for t in ts:
        c = X.counts[t]
        r_o = sorted(c[p] / vb[p] for p in oth if vb[p] > 0)
        r_s = sorted(c[p] / vb[p] for p in sq if vb[p] > 0)
        q = lambda v, f: 100 * v[min(len(v) - 1, int(f * len(v)))] if v else 0
        print(f"   t={t} 兑现率分位（25% / 50% / 75%）：我方 {q(r_s, .25):.0f}% / {q(r_s, .5):.0f}% / {q(r_s, .75):.0f}%；其他真人 {q(r_o, .25):.0f}% / {q(r_o, .5):.0f}% / {q(r_o, .75):.0f}%；"
              f"领土中位：我方 {med([int(c[p]) for p in sq])} 格、其他真人 {med([int(c[p]) for p in oth])} 格")
    return out


def owner_classes(X, g, cells_mask, me_lab=None):
    """cells_mask 里的格在网格 g 上归谁：self（= 该格的天然主人）/ squad / other / ai / neutral。me_lab = 每格的天然主人。"""
    o = g[cells_mask].astype(np.int64)
    is_sq = np.zeros(NOTLAND + 1, dtype=bool)
    is_sq[X.squad] = True
    res = dict(n=int(o.size))
    if me_lab is not None:
        own = me_lab[cells_mask]
        selfm = o == own
        res['self'] = int(selfm.sum())
    else:
        selfm = np.zeros(o.size, dtype=bool)
    res['squad'] = int((is_sq[o] & ~selfm).sum())
    res['other'] = int(((o < X.H) & ~is_sq[o] & ~selfm).sum())
    res['ai'] = int(((o >= X.H) & (o < NEUTRAL)).sum())
    res['neutral'] = int((o == NEUTRAL).sum())
    return res


def sec_natural(X):
    lab, _ = bfs_voronoi(X)
    is_sq = np.zeros(X.H + 1, dtype=bool)
    is_sq[X.squad] = True
    labc = np.where(lab >= 0, lab, X.H)
    sq_nat = is_sq[labc] & (lab >= 0)
    ot_nat = (~is_sq[labc]) & (lab >= 0)
    out = []
    print('-- 天然份额里的地在该拍归谁（自己 = 这格的天然主人本人）')
    for t in cap_ticks(X):
        g = X.grid[t]
        a = owner_classes(X, g, sq_nat, lab)
        b = owner_classes(X, g, ot_nat, lab)
        print(f"   t={t}：我方的天然份额 {a['n']} 格：自己 {pc(a['self'], a['n'])}、我方别的号 {pc(a['squad'], a['n'])}、其他真人 {pc(a['other'], a['n'])}、内置 AI {pc(a['ai'], a['n'])}、无主地 {pc(a['neutral'], a['n'])}"
              f"｜其他真人的天然份额 {b['n']} 格：自己 {pc(b['self'], b['n'])}、我方号 {pc(b['squad'], b['n'])}、别的其他真人 {pc(b['other'], b['n'])}、内置 AI {pc(b['ai'], b['n'])}、无主地 {pc(b['neutral'], b['n'])}")
        out.append(dict(t=t, squad=a, other=b))
    t = cap_ticks(X)[-1]
    g = X.grid[t]
    print(f"   各号天然份额在 t={t} 的归属（格）：自己 / 我方别的号 / 其他真人 / 内置 AI / 无主地；以及本号在别人天然份额里占的格")
    per = []
    for p in sorted(X.squad, key=lambda p: -int((lab == p).sum())):
        m = lab == p
        if not m.any():
            print(f"      {name(X, p):14s} 队{X.team[p]} 天然份额 0（出生格被同像素的号占了）；t={t} 领土 {int(X.counts[t][p])}")
            continue
        a = owner_classes(X, g, m, lab)
        outside = int(((g == p) & ~m).sum())
        per.append(dict(me=p, name=name(X, p), **a, outside=outside))
        print(f"      {name(X, p):14s} 队{X.team[p]} 天然 {a['n']:6d}：{a['self']:6d} / {a['squad']:6d} / {a['other']:6d} / {a['ai']:6d} / {a['neutral']:6d}｜在别人份额里占 {outside} 格")
    return dict(ticks=out, perBot=per, perBotTick=t)


def adj_mask(X, m):
    """与掩码 m 里的格 4 邻接的格（不含 m 自己）。"""
    W, Hh = X.W, X.Hh
    a = m.reshape(Hh, W)
    r = np.zeros_like(a)
    r[:, 1:] |= a[:, :-1]
    r[:, :-1] |= a[:, 1:]
    r[1:, :] |= a[:-1, :]
    r[:-1, :] |= a[1:, :]
    return (r & ~a).reshape(-1)


def ai_sets(X, t0):
    """t0 拍时：与我方领土接壤的内置 AI、一半以上的格在我方天然份额里的内置 AI。"""
    lab, _ = bfs_voronoi(X)
    g = X.grid[t0]
    is_sq = np.zeros(NOTLAND + 1, dtype=bool)
    is_sq[X.squad] = True
    sqm = is_sq[g]
    ring = adj_mask(X, sqm)
    o = g[ring]
    touch = set(int(x) for x in np.unique(o[(o >= X.H) & (o < NEUTRAL)]))
    is_sq_h = np.zeros(X.H + 1, dtype=bool)
    is_sq_h[X.squad] = True
    sq_nat = is_sq_h[np.where(lab >= 0, lab, X.H)] & (lab >= 0)
    aim = (g >= X.H) & (g < NEUTRAL)
    tot = np.bincount(g[aim].astype(np.int64), minlength=NEUTRAL)
    ins = np.bincount(g[aim & sq_nat].astype(np.int64), minlength=NEUTRAL)
    inside = set(int(p) for p in range(X.H, NEUTRAL) if tot[p] > 0 and ins[p] * 2 >= tot[p])
    return touch, inside, tot, ins


def sec_ai(X):
    t0 = tick_for(X, 630)
    touch, inside, tot, ins = ai_sets(X, t0)
    A = sorted(touch | inside)
    g0 = X.grid[t0]
    isA = np.zeros(NOTLAND + 1, dtype=bool)
    isA[A] = True
    mA = isA[g0]
    all_ai = (g0 >= X.H) & (g0 < NEUTRAL)
    nA, nAll = int(mA.sum()), int(all_ai.sum())
    dth = X.S.get('aiDeathT') or {}
    print(f"-- 内置 AI 地的去向。t={t0} 时全场内置 AI 在场 {int((tot > 0).sum())} 个、{nAll} 格；与我方领土接壤的 {len(touch)} 个（{int(sum(tot[p] for p in touch))} 格），"
          f"一半以上的格在我方天然份额里的 {len(inside)} 个（{int(sum(tot[p] for p in inside))} 格）；两者并集 {len(A)} 个、{nA} 格（下称「身边的 AI」）")
    out = dict(t0=t0, touch=len(touch), inside=len(inside), n=len(A), cells=nA, allAi=int((tot > 0).sum()), allCells=nAll, later=[])
    later = [t for t in X.gt if t > t0]
    for t in later:
        g = X.grid[t]
        a = owner_classes(X, g, mA)
        b = owner_classes(X, g, all_ai & ~mA)
        dead = sum(1 for p in A if str(p) in dth and dth[str(p)] <= t)
        print(f"   到 t={t}：身边的 AI 的 {nA} 格 → 我方 {a['squad']}（{pc(a['squad'], nA)}）、其他真人 {a['other']}（{pc(a['other'], nA)}）、仍是内置 AI {a['ai']}（{pc(a['ai'], nA)}）、无主地 {a['neutral']}（{pc(a['neutral'], nA)}）；"
              f"这 {len(A)} 个 AI 已出局 {dead} 个｜其余 AI 的 {nAll - nA} 格 → 我方 {b['squad']}（{pc(b['squad'], nAll - nA)}）、其他真人 {b['other']}（{pc(b['other'], nAll - nA)}）、仍是 AI {b['ai']}、无主地 {b['neutral']}")
        out['later'].append(dict(t=t, near=a, rest=b, dead=dead))
    # 按「只与我方接壤」/「同时也与其他真人接壤」拆
    is_sq = np.zeros(NOTLAND + 1, dtype=bool)
    is_sq[X.squad] = True
    oth_h = (g0 < X.H) & ~is_sq[g0]
    ring_o = adj_mask(X, oth_h)
    o = g0[ring_o]
    touch_o = set(int(x) for x in np.unique(o[(o >= X.H) & (o < NEUTRAL)]))
    only = [p for p in A if p not in touch_o]
    both = [p for p in A if p in touch_o]
    tl = later[-1] if later else None
    if tl is not None:
        g = X.grid[tl]
        for lab_, ps in (('只挨着我方（没有其他真人挨着）', only), ('同时也挨着其他真人', both)):
            m = np.zeros(NOTLAND + 1, dtype=bool)
            m[ps] = True
            mm = m[g0]
            a = owner_classes(X, g, mm)
            n = int(mm.sum())
            print(f"   {lab_}的 {len(ps)} 个 AI、{n} 格，到 t={tl}：我方 {pc(a['squad'], n)}、其他真人 {pc(a['other'], n)}、仍是 AI {pc(a['ai'], n)}、无主地 {pc(a['neutral'], n)}")
            out['only' if ps is only else 'both'] = dict(ais=len(ps), cells=n, squad=a['squad'], other=a['other'], ai=a['ai'], neutral=a['neutral'])
        # 每个身边的 AI：它的格最后主要落到谁手里
        credit = defaultdict(lambda: [0, 0])
        for p in A:
            m = g0 == p
            o = g[m].astype(np.int64)
            n = int(m.sum())
            sq = int(is_sq[o].sum())
            ot = int(((o < X.H) & ~is_sq[o]).sum())
            ai = int(((o >= X.H) & (o < NEUTRAL)).sum())
            k = '我方拿到一半以上' if sq * 2 >= n else ('其他真人拿到一半以上' if ot * 2 >= n else ('仍有一半以上是 AI 的' if ai * 2 >= n else '几家分/变无主地'))
            credit[k][0] += 1
            credit[k][1] += n
        print(f"   身边的 AI 逐个看（到 t={tl}）：" + '；'.join(f"{k} {v[0]} 个（{v[1]} 格）" for k, v in sorted(credit.items(), key=lambda kv: -kv[1][1])))
        out['credit'] = {k: v for k, v in credit.items()}
    return out


def sec_flow(X):
    """各号领土在两个快照之间的进出：t1 拍手里的格在 t0 拍归谁；t0 拍手里的格在 t1 拍归谁。"""
    t0 = tick_for(X, 630)
    t1 = tick_for(X, 1500)
    if t1 <= t0:
        return None
    g0, g1 = X.grid[t0], X.grid[t1]
    is_sq = np.zeros(NOTLAND + 1, dtype=bool)
    is_sq[X.squad] = True
    print(f"-- 领土进出 t={t0} → t={t1}（格）：进 = t={t1} 手里的格在 t={t0} 归谁（无主地 / 内置 AI / 其他真人 / 我方别的号）；出 = t={t0} 手里的格到 t={t1} 归谁")
    rows = []
    tot = defaultdict(int)
    for p in X.squad:
        m1 = g1 == p
        m0 = g0 == p
        o = g0[m1 & ~m0].astype(np.int64)
        gi = dict(neutral=int((o == NEUTRAL).sum()), ai=int(((o >= X.H) & (o < NEUTRAL)).sum()), other=int(((o < X.H) & ~is_sq[o]).sum()), squad=int(is_sq[o].sum()))
        o = g1[m0 & ~m1].astype(np.int64)
        lo = dict(neutral=int((o == NEUTRAL).sum()), ai=int(((o >= X.H) & (o < NEUTRAL)).sum()), other=int(((o < X.H) & ~is_sq[o]).sum()), squad=int(is_sq[o].sum()))
        r = dict(me=p, name=name(X, p), team=X.team[p], t0=int(m0.sum()), t1=int(m1.sum()), gain=gi, loss=lo)
        rows.append(r)
        for k, v in gi.items():
            tot['g_' + k] += v
        for k, v in lo.items():
            tot['l_' + k] += v
        print(f"      {r['name']:14s} 队{r['team']} {r['t0']:6d} → {r['t1']:6d}｜进：无主地 {gi['neutral']:5d}、内置 AI {gi['ai']:5d}、其他真人 {gi['other']:5d}、我方 {gi['squad']:5d}"
              f"｜出：→内置 AI {lo['ai']:5d}、→其他真人 {lo['other']:5d}、→我方 {lo['squad']:5d}、→无主地 {lo['neutral']:5d}")
    s0, s1 = sum(r['t0'] for r in rows), sum(r['t1'] for r in rows)
    print(f"   我方合计 {s0} → {s1}（{s1 - s0:+d}）：进 无主地 {tot['g_neutral']}、内置 AI {tot['g_ai']}、其他真人 {tot['g_other']}、我方内部 {tot['g_squad']}；出 →内置 AI {tot['l_ai']}、→其他真人 {tot['l_other']}、→我方内部 {tot['l_squad']}、→无主地 {tot['l_neutral']}")
    # 其他真人同期
    oth = [p for p in range(X.H) if p not in X.M.bots]
    is_o = np.zeros(NOTLAND + 1, dtype=bool)
    is_o[oth] = True
    m1, m0 = is_o[g1], is_o[g0]
    o0 = g0[m1].astype(np.int64)
    from_ai = int(((o0 >= X.H) & (o0 < NEUTRAL)).sum())
    from_sq = int(is_sq[o0].sum())
    from_ne = int((o0 == NEUTRAL).sum())
    o1 = g1[m0].astype(np.int64)
    to_ai = int(((o1 >= X.H) & (o1 < NEUTRAL)).sum())
    print(f"   其他真人（{len(oth)} 个）合计 {int(m0.sum())} → {int(m1.sum())}（{int(m1.sum()) - int(m0.sum()):+d}）：进 无主地 {from_ne}、内置 AI {from_ai}、我方 {from_sq}；出 →内置 AI {to_ai}、→我方 {tot['g_other']}")
    n_s, n_o = len(X.squad), len(oth)
    print(f"   人均从内置 AI 手里拿到的地：我方 {tot['g_ai'] // n_s} 格、其他真人 {from_ai // max(1, n_o)} 格；人均净增：我方 {(s1 - s0) // n_s}、其他真人 {(int(m1.sum()) - int(m0.sum())) // max(1, n_o)}")
    return dict(t0=t0, t1=t1, rows=rows, squad=dict(t0=s0, t1=s1, **tot), other=dict(n=n_o, t0=int(m0.sum()), t1=int(m1.sum()), fromAi=from_ai, fromSquad=from_sq, fromNeutral=from_ne, toAi=to_ai))


def sec_layers(X):
    """三层归因（t=600~1500）。"""
    sh = shares(X)
    vb = sh['vb']
    tot = int(vb.sum())
    par = tot / X.H
    sq = X.squad
    out = {}
    print('-- 三层归因（t=600~1500 没抢到内置 AI 的地，各层各有多大；三层不互斥，不相加）')
    small = [p for p in sq if vb[p] < 0.5 * par]
    s_b = int(sum(vb[p] for p in sq))
    print(f"   ① 出生位置：我方天然份额合计 {s_b} 格，按人头应有 {par * len(sq):.0f} 格，差 {s_b - par * len(sq):+.0f} 格（{100 * (s_b / (par * len(sq)) - 1):+.1f}%）；"
          f"天然份额不到全场人均一半的 {len(small)} 个号：" + '、'.join(f"{name(X, p)} {int(vb[p])}" for p in sorted(small, key=lambda p: vb[p])))
    out['spawn'] = dict(squadVor=s_b, par=round(par * len(sq)), small=[[name(X, p), int(vb[p])] for p in small])
    try:
        import simdigest as SD
        XS = SD.Sim(X.M.id)
    except Exception as e:  # noqa: BLE001
        XS = None
        print('   （simdigest 载入失败：', e, '）')
    if XS is not None:
        R = SD.gate_rows(XS, 600, 1500)
        if R:
            early = R[0]
            c = defaultdict(int)
            for p, d in early.items():
                for g, v in d.items():
                    c[g] += v
            n = sum(c.values())
            ok = c.get('ok', 0)
            sbs = sum(v for g, v in c.items() if g.startswith('sb:') and '不够' not in g)
            sbs_sq = sum(v for g, v in c.items() if g.startswith('sb:我方') and '不够' not in g)
            sb_no = sum(v for g, v in c.items() if g.startswith('sb:') and '不够' in g)
            print(f"   ② 策略自己不出兵：影子在 t=600~1499 有内置 AI 邻居的决策拍 {n} 个，可出兵 {ok}（{pc(ok, n)}）；卡在地价闸 botOk {c.get('botOk', 0)}（{pc(c.get('botOk', 0), n)}）、"
                  f"底线取 winR 项 {c.get('floor:winR', 0)}（{pc(c.get('floor:winR', 0), n)}）、取 dpKeep {c.get('floor:dpKeep', 0)}（{pc(c.get('floor:dpKeep', 0), n)}）、"
                  f"取 safeFinite 且去掉就能出兵 {sbs}（{pc(sbs, n)}；其中取的是我方号的兵 {sbs_sq}）、取 safeFinite 去掉也不够 {sb_no}；其余（need0 / already 等）{n - ok - c.get('botOk', 0) - c.get('floor:winR', 0) - c.get('floor:dpKeep', 0) - sbs - sb_no}")
            out['gates'] = dict(n=n, ok=ok, botOk=c.get('botOk', 0), winR=c.get('floor:winR', 0), dpKeep=c.get('floor:dpKeep', 0), safeFinite=sbs, safeFiniteSquad=sbs_sq, safeFiniteNoPass=sb_no)
    try:
        import latency as LT
        XL = LT.load(X.M.id)
        if XL.probe and XL.sim:
            rows, lost = LT.align(XL)
            m = [r for r in rows if r['k'] == 'atk' and 600 <= r['t'] < 1500]
            void = [r for r in m if not r['ok']]
            a1 = [r for r in void if r['raw'] == NEUTRAL and r.get('sTo') not in (None, NEUTRAL)]
            bb = [r for r in m if r['ok'] and r['raw'] == NEUTRAL and r.get('sTo') not in (None, NEUTRAL)]
            eps = [e for e in (XL.sim.get('episodes') or []) if 600 <= e['t0'] < 1500 and not e['redir'] and XL.H <= e['to'] < NEUTRAL]
            sent = sum(e['sent'] for e in eps)
            moved = sum(e['moved'] for e in eps if e['end'] == 'redirect')
            pend = [x for x in lost if 600 <= x['t'] < 1500 and not x['before'] and x['k'] == 'atk' and x['to'] >= XL.H and x['to'] < NEUTRAL]
            print(f"   ③ 出了兵但迟到：执行拍在 t=600~1499 的陆攻 {len(m)} 条里，落地时目标已出局、一兵没扣的 {len(a1)} 条（{pc(len(a1), len(m))}；想发 {fmt(sum(r['sAmt'] for r in a1))} 兵），"
                  f"落地时目标已出局、兵进了无主地线的 {len(bb)} 条（实发 {fmt(sum(r['sent'] for r in bb))}）；打内置 AI 的线出兵 {fmt(sent)}，其中目标出局时还挂在线上、被改挂到无主地的 {fmt(moved)}（{pc(moved, sent)}）；"
                  f"重放结束时还没落地的打内置 AI 的令 {len(pend)} 条")
            out['late'] = dict(atk=len(m), a1=len(a1), a1Amt=sum(r['sAmt'] for r in a1), b=len(bb), bSent=sum(r['sent'] for r in bb), aiSent=sent, aiMoved=moved, pending=len(pend))
    except Exception as e:  # noqa: BLE001
        print('   （latency 载入失败：', repr(e), '）')
    return out


def sec_natwho(X, me, ticks):
    """某个号的天然份额（陆路版）在各拍分别在谁手里（按名字列前 6 名）。用法：landcap.py <id> natwho <me> [t ...]"""
    lab, _ = bfs_voronoi(X)
    m = lab == me
    n = int(m.sum())
    print(f"{name(X, me)} 队{X.team[me]} 的天然份额 {n} 格在各拍的归属（格；内置 AI 合并成一项）")
    for want in ticks:
        t = tick_for(X, want)
        o = X.grid[t][m].astype(np.int64)
        cnt = np.bincount(o, minlength=NEUTRAL + 1)[:NEUTRAL + 1]
        ai = int(cnt[X.H:NEUTRAL].sum())
        rows = sorted(((int(cnt[p]), p) for p in range(X.H) if cnt[p] > 0), reverse=True)
        parts = [f"{'*' if p in X.squad else ''}{name(X, p).lstrip('*')}(队{X.team[p]}) {c}" for c, p in rows[:6]]
        print(f"   t={t}：内置 AI {ai}、无主地 {int(cnt[NEUTRAL])}；真人：" + '、'.join(parts))
    return 0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    mid = sys.argv[1]
    sec = sys.argv[2] if len(sys.argv) > 2 else 'all'
    X = load(mid)
    if X is None:
        print(f"（{mid}：没有归属网格 —— 需要先用 eng_replay.cjs 重放；没有录像的局这本账做不了）")
        return 0
    if sec == 'natwho':
        return sec_natwho(X, int(sys.argv[3]), [int(a) for a in sys.argv[4:]] or [630, 1500])
    doc = dict(matchId=mid, gridTicks=X.gt, replayLast=X.last)
    if sec in ('voronoi', 'all', 'json'):
        doc['voronoi'] = sec_voronoi(X)
    if X.last > 60:
        if sec in ('capture', 'all', 'json'):
            doc['capture'] = sec_capture(X)
        if sec in ('natural', 'all', 'json'):
            doc['natural'] = sec_natural(X)
        if sec in ('ai', 'all', 'json'):
            doc['ai'] = sec_ai(X)
        if sec in ('flow', 'all', 'json'):
            doc['flow'] = sec_flow(X)
        if sec in ('layers', 'all', 'json'):
            doc['layers'] = sec_layers(X)
    if sec == 'json':
        p = os.path.join(OUT, mid, 'landcap.json')
        json.dump(doc, open(p, 'w'), ensure_ascii=False, default=lambda o: int(o) if isinstance(o, (np.integer,)) else float(o))
        print('写入', p)
    return 0


if __name__ == '__main__':
    sys.exit(main())
