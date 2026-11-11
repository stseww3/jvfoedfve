#!/usr/bin/env python3
"""aigate.py — 1500 拍以后「打内置 AI」这条线的全程账（有录像的局）。

    python3 c136-review/agents/R08/scripts/aigate.py <matchId> [--tag full]

输入（都是本目录脚本的产物）：
  out/<局>/resim.json              真引擎重演的全场真值（resim_r08.mjs）
  out/<局>/shadow_<tag>.json       影子普查（shadow.mjs --core-census-until <末拍> --census-every 30 --tag <tag>）；
                                   没给 --tag 时读 shadow.json（普查只到 t=3000）
  out/<局>/facts.json              日志事实（录像结束以后的尾段只有它）
输出：out/<局>/aigate.txt（同时打印）。

各节：
  [GA] 逐窗普查：Policy.buyLand 对非真人邻居（c110 L5363-5368）逐关重算，最便宜那个被挡在哪一关；
       同一个点上「所有 AI 邻居吃光所需合计」「单个最大的 want」和 minCmd 的对比
  [GB] 逐号合计
  [GC] t≥2250 真正落地的打 AI 的陆攻：当时的 minCmd、目标的地和兵、之后 300 拍目标剩多少
  [GD] 各号顶在软上限 / 硬上限上的拍数，以及这些拍里被 AI 拿走的地和被打掉的兵
  [GE] t≥2250 打空地的指令：实发兵、手续费、之后 60 拍从空地拿到的格数
  [GF] 录像结束以后的尾段（只有日志）：领土单窗跳涨的时刻、两次跳涨之间的指令数和顶在硬上限的快照数
  [GG] 编队号互打：逐条指令当时的报价（影子口径的每格成本）对比 AI 邻居吃光所需
  [GH] 指定拍上逐报价重走 Policy.buyLand 的结论（要先用 shadow.mjs --trace 跑出 walk）
  [GI] 和内置 AI 的来回账，按时段
  [GJ] 扫尾段（只看日志）：nb=0 且领土 ≥80% 陆地的连续快照；配上 HL-SLOW-TICK（找船的水路搜索）找「一次都没搜」的空档
  [GK] 时间线（真值）：指定拍上各编队号的格 / 密度、编队合计、内置 AI 的个数 / 格 / 兵 / 吃光所需（--ticks 逗号分隔，可省）
"""
import bisect
import json
import os
import statistics
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out")
NEUTRAL = 512
WIN = 900


def med(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs)) if xs else 0


def main():
    args = sys.argv[1:]
    mid = args[0]
    tag = args[args.index("--tag") + 1] if "--tag" in args else None
    R = json.load(open(os.path.join(OUT, mid, "resim.json"), encoding="utf-8"))
    S = json.load(open(os.path.join(OUT, mid, f"shadow_{tag}.json" if tag else "shadow.json"), encoding="utf-8"))
    H, names, end = R["H"], R["names"], R["endTick"]
    snapT, snapTerr, snapBal = R["snapT"], R["snapTerr"], R["snapBal"]
    ai_by_t = {r[0]: {x[0]: (x[1], x[2]) for x in r[1]} for r in R["snapAi"]}
    ai_ts = sorted(ai_by_t)
    sq = {b["id"]: nm for nm, b in S["bots"].items()}
    lines = []
    P = lambda s="": (lines.append(s), print(s))

    def who(q):
        return "空地" if q == NEUTRAL else (names[q] if q < H else f"AI{q}")

    def state(q, t):
        if q < H:
            i = bisect.bisect_right(snapT, t) - 1
            return snapTerr[i][q], snapBal[i][q]
        j = bisect.bisect_right(ai_ts, t) - 1
        return ai_by_t[ai_ts[j]].get(q, (0, 0)) if j >= 0 else (0, 0)

    # ---------- [GA] / [GB] ----------
    rows = []   # (bot, row)
    for nm, b in S["bots"].items():
        for r in b.get("census2") or []:
            rows.append((nm, r))
    has_tot = bool(rows) and len(rows[0][1]) >= 25
    last_c = max((r[0] for _, r in rows), default=0)
    diffs = Counter()
    for b in S["bots"].values():
        cs = b.get("census2") or []
        diffs.update(cs[i + 1][0] - cs[i][0] for i in range(len(cs) - 1))
    step = diffs.most_common(1)[0][0] if diffs else "?"
    P(f"[GA] {mid} 1500 拍后打内置 AI 的门槛普查（影子按真值每 {step} 拍一次，到 t={last_c}；"
      f"c110 Policy.buyLand L5363-5368（门槛在 L5367）：want = 1.25×吃光所需 + 3×接壤格数，x = min(可用兵, want)，x < minCmd 就跳过；minCmd = feeK×floor(12×余额/1024)，feeK=4，L521-523）")
    P("     窗 | 号·点 | 接壤 AI 的 | 至少一个 AI 过门槛或已在打 | 全被挡 | 最便宜那个被挡的原因 | 中位：自己余额 / minCmd / AI 邻居合计 格·兵 / 吃光它们所需合计 / 单个最大 want | 最大 want < minCmd 的点 | 吃光所需合计 < minCmd 的点")
    wins = defaultdict(list)
    for nm, r in rows:
        wins[(r[0] - 1500) // WIN].append((nm, r))
    for w in sorted(wins):
        rs = wins[w]
        withai = [x for x in rs if x[1][3] > 0]
        ok = [x for x in withai if x[1][5] > 0]
        blocked = [x for x in withai if x[1][5] == 0]
        why = Counter(x[1][16] for x in blocked)
        t0 = 1500 + w * WIN
        tail = ""
        if has_tot:
            tail = (f" | {med([x[1][1] for x in withai])} / {med([x[1][13] for x in withai])} / {med([x[1][21] for x in withai])}·{med([x[1][22] for x in withai])} / "
                    f"{med([x[1][20] for x in withai])} / {med([x[1][23] for x in withai])} | {sum(1 for x in withai if x[1][23] < x[1][13])} | {sum(1 for x in withai if x[1][20] < x[1][13])}")
        P(f"     {t0}~{t0 + WIN} | {len(rs)} | {len(withai)} | {len(ok)} | {len(blocked)} | {' '.join(f'{k}:{v}' for k, v in why.most_common())}{tail}")
    P("[GB] 逐号（t≥1500 到普查结束）：号 | 号·点 | 接壤 AI 的 | 全被挡 | 原因 | 其中余额 > 100×领土（超软上限）的点：接壤 AI 的 / 全被挡")
    for nm in S["bots"]:
        rs = [r for n2, r in rows if n2 == nm]
        withai = [r for r in rs if r[3] > 0]
        blocked = [r for r in withai if r[5] == 0]
        why = Counter(r[16] for r in blocked)
        ov = [r for r in withai if r[19]]
        P(f"     {nm} | {len(rs)} | {len(withai)} | {len(blocked)} | {' '.join(f'{k}:{v}' for k, v in why.most_common())} | {len(ov)} / {sum(1 for r in ov if r[5] == 0)}")

    # ---------- [GC] ----------
    P("[GC] t≥2250 落地的打 AI 的陆攻（真值）：拍 | 号 | 目标 | 实发兵 + 手续费 | 发令前余额 / 领土（密度）| 当时的 minCmd | 目标当时 地 / 兵 | 300 拍后目标 地 | 300 拍后自己 地")
    n_ai = 0
    for c in R["cmdLog"]:
        t, p, ty, pct, tg, ok, tr, fee, B0, L0 = c[:10]
        if ty != 1 or t < 2250 or p not in sq or tg < H or tg >= NEUTRAL or not ok:
            continue
        n_ai += 1
        tt = state(tg, t)
        after = state(tg, min(end, t + 300))
        me_after = state(p, min(end, t + 300))
        P(f"     {t} | {names[p]} | {who(tg)} | {tr} + {fee} | {B0} / {L0}（{B0 / max(1, L0):.1f}）| {4 * (12 * B0 // 1024)} | {tt[0]} / {tt[1]} | {after[0]} | {me_after[0]}")
    P(f"     共 {n_ai} 条")

    # ---------- [GD] ----------
    P("[GD] 顶在上限上的拍数（真值每 10 拍一个点，t≥1500 到阵亡 / 录像结束）：号 | 点数×10 | 密度 ≥100 / ≥140 / ≥149 的拍数 | 密度 ≥100 的时候：被内置 AI 拿走的格数 / AI 实际耗兵 / 自己余额被打掉 | 同期自己从 AI 手里拿的格数 / 耗兵")
    dens_at = {}
    for p in sq:
        dens_at[p] = {}
        for i, t in enumerate(snapT):
            L0 = snapTerr[i][p]
            if L0 > 0:
                dens_at[p][t] = snapBal[i][p] / L0
    for p, nm in sq.items():
        ts = [t for t in dens_at[p] if t >= 1500]
        c100 = sum(10 for t in ts if dens_at[p][t] >= 100)
        c140 = sum(10 for t in ts if dens_at[p][t] >= 140)
        c149 = sum(10 for t in ts if dens_at[p][t] >= 149)
        lost = [0, 0, 0]
        got = [0, 0]
        for t, a, d, tiles, burnt, dB, dS, n in R["pairLog"]:
            tt = (t // 10) * 10
            dd = dens_at[p].get(tt) or dens_at[p].get(tt - 10) or dens_at[p].get(tt - 20) or 0
            if dd < 100 or t < 1500:
                continue
            if d == p and H <= a < NEUTRAL:
                lost[0] += tiles; lost[1] += burnt; lost[2] += dB
            if a == p and H <= d < NEUTRAL:
                got[0] += tiles; got[1] += burnt
        P(f"     {nm} | {len(ts) * 10} | {c100} / {c140} / {c149} | {lost[0]} / {lost[1]} / {lost[2]} | {got[0]} / {got[1]}")

    # ---------- [GE] ----------
    P("[GE] t≥2250 打空地的指令（真值）：号 | 条数（没生效的）| 实发兵合计 | 手续费合计 | 发令后 60 拍内从空地拿到的格数合计 | 每格连手续费 | 其中发令时密度 ≥100 的：条数 / 实发兵 / 手续费 / 拿到的格数")
    neut_gain = defaultdict(list)   # p -> [(t, tiles)]
    for t, a, d, tiles, burnt, dB, dS, n in R["pairLog"]:
        if d == NEUTRAL and a in sq:
            neut_gain[a].append((t, tiles))
    for p, nm in sq.items():
        cs = [c for c in R["cmdLog"] if c[1] == p and c[2] == 1 and c[0] >= 2250 and c[4] == NEUTRAL]
        if not cs:
            P(f"     {nm} | 0")
            continue
        used = set()
        tot = [0, 0, 0, 0]
        rich = [0, 0, 0, 0]
        for c in cs:
            t, _, _, pct, tg, ok, tr, fee, B0, L0 = c[:10]
            g = 0
            for k, (t2, tiles) in enumerate(neut_gain[p]):
                if t < t2 <= t + 90 and k not in used:     # 账是 30 拍一窗，窗末记账
                    used.add(k)
                    g += tiles
            tot[0] += 1; tot[1] += tr; tot[2] += fee; tot[3] += g
            if B0 >= 100 * max(1, L0):
                rich[0] += 1; rich[1] += tr; rich[2] += fee; rich[3] += g
        bad = sum(1 for c in cs if not c[5])
        P(f"     {nm} | {tot[0]}（{bad}）| {tot[1]} | {tot[2]} | {tot[3]} | {(tot[1] * 0 + tot[2] + 2 * tot[3]) / max(1, tot[3]):.1f} | {rich[0]} / {rich[1]} / {rich[2]} / {rich[3]}")
    P("     注：打空地每格耗 2 兵，多发的兵打完退回；手续费（余额的 12/1024）不退。「每格连手续费」=（2×格数 + 手续费）÷ 格数。")

    # ---------- [GF] ----------
    fp = os.path.join(OUT, mid, "facts.json")
    if os.path.exists(fp):
        F = json.load(open(fp, encoding="utf-8"))
        land = F["card"]["mapLand"] if "card" in F else R["land"]
        P(f"[GF] 录像结束（t={end}）以后只有日志的尾段：号 | 快照数 | 密度 ≥149 的快照数 | 指令数 / 船数（尾段内新增）| 领土最低@拍 | 单窗（90 拍）领土涨 ≥10% 的时刻")
        for me, b in F["bots"].items():
            tk = [s for s in b["ticks"] if s["t"] > end]
            if not tk:
                continue
            jumps = []
            prev = None
            for s in tk:
                if prev and s["terr"] - prev["terr"] >= 0.1 * prev["terr"] and s["terr"] - prev["terr"] > 3000:
                    jumps.append(f"{prev['t']}→{s['t']}：{prev['terr']}→{s['terr']}（指令 +{s['cmds'] - prev['cmds']}）")
                prev = s
            mn = min(tk, key=lambda s: s["terr"])
            P(f"     {b['name']} | {len(tk)} | {sum(1 for s in tk if s['dens'] >= 149)} | {tk[-1]['cmds'] - tk[0]['cmds']} / {tk[-1]['boats'] - tk[0]['boats']} | {mn['terr']}（{100 * mn['terr'] / land:.1f}%）@{mn['t']} | {'；'.join(jumps) or '无'}")
            # 最长的零指令段
            best = None
            i = 0
            allk = b["ticks"]
            while i < len(allk) - 1:
                j = i
                while j + 1 < len(allk) and allk[j + 1]["cmds"] == allk[i]["cmds"] and allk[j + 1]["boats"] == allk[i]["boats"]:
                    j += 1
                if j > i and (best is None or allk[j]["t"] - allk[i]["t"] > best[1]["t"] - best[0]["t"]):
                    best = (allk[i], allk[j])
                i = max(j, i + 1)
            if best:
                a, z = best
                P(f"       全程最长的零指令段：t={a['t']}~{z['t']}（{z['t'] - a['t']} 拍），领土 {a['terr']}→{z['terr']}（{100 * a['terr'] / land:.1f}%→{100 * z['terr'] / land:.1f}%），余额 {a['bal']}→{z['bal']}，密度 {a['dens']}→{z['dens']}，邻居数 {a['nb']}→{z['nb']}")

    # ---------- [GG] ----------
    P("[GG] 编队号互打的陆攻（真值）：拍 | 攻→守 | 实发兵 + 手续费 | 攻方 余额 / 领土（密度）| 守方 地 / 兵（密度）| 同一拍攻方的 AI 邻居：个数 / 合计格数 / 吃光所需合计（取影子普查里最近的一个点）")
    cen = defaultdict(list)
    for nm, r in rows:
        cen[nm].append(r)
    for c in R["cmdLog"]:
        t, p, ty, pct, tg, ok, tr, fee, B0, L0 = c[:10]
        if ty != 1 or p not in sq or tg not in sq or not ok:
            continue
        tt = state(tg, t)
        rs = cen.get(sq[p]) or []
        near = min(rs, key=lambda r: abs(r[0] - t)) if rs else None
        ai_txt = f"{near[4]} / {near[21]} / {near[20]}（t={near[0]}）" if near is not None and len(near) >= 25 and abs(near[0] - t) <= 60 else "-"
        P(f"     {t} | {names[p]}→{names[tg]} | {tr} + {fee} | {B0} / {L0}（{B0 / max(1, L0):.1f}）| {tt[0]} / {tt[1]}（{tt[1] / max(1, tt[0]):.1f}）| {ai_txt}")
    tot = defaultdict(lambda: [0, 0, 0])
    for t, a, d, tiles, burnt, dB, dS, n in R["pairLog"]:
        if a in sq and d in sq:
            k = (a, d)
            tot[k][0] += tiles; tot[k][1] += burnt; tot[k][2] += dB
    for (a, d), v in sorted(tot.items(), key=lambda kv: -kv[1][1]):
        P(f"     合计 {names[a]}→{names[d]}：{v[0]} 格，攻方耗兵 {v[1]}（{v[1] / max(1, v[0]):.1f}/格），守方余额被打掉 {v[2]}")
    if tot:
        P(f"     互打合计：{sum(v[0] for v in tot.values())} 格，攻方耗兵 {sum(v[1] for v in tot.values())}，守方余额被打掉 {sum(v[2] for v in tot.values())}")

    # ---------- [GH] ----------
    tr = [o for o in S.get("traces", []) if o.get("walk")]
    if tr:
        P("[GH] 逐报价重走 Policy.buyLand（shadow.mjs 的 walkBuyLand，照抄 c110 L5250-5534 的每一关但不发指令；只在 --trace 指定的拍上有）：")
        P("     号 拍 | 余额 / 领土（密度）| minCmd | 超软上限 | 内置 AI 报价：个数 / 合计格数 / 合计兵 / 吃光所需合计 / 单个最大 want / 每格成本（含手续费）最低~最高 | AI 报价的结论 | 真人报价：名字 每格成本 结论 金额（safe / keep / avail）")
        for o in sorted(tr, key=lambda o: (o["bot"], o["t"])):
            w = o["walk"]
            ai = [r for r in w["rows"] if not r["person"]]
            pe = [r for r in w["rows"] if r["person"]]
            vc = Counter(r.get("v", "?").split("(")[0] for r in ai)
            cs = [r["c"] for r in ai]
            pt = "；".join(f"{r['name']} {r['c']} {r.get('v', '?')} {r.get('x', '-')}（{r.get('safe', '-')} / {r.get('keep', '-')} / {r.get('avail', '-')}）"
                           + ("[bleeding]" if r.get("bleeding") else "") + ("[onMe]" if r.get("onMe") else "") for r in pe) or "无"
            P(f"     {o['bot']} {o['t']} | {w['B']} / {w['L']}（{w['B'] / max(1, w['L']):.1f}）| {w['minCmd']} | {'是' if w['over'] else '否'} | "
              f"{len(ai)} / {sum(r['terr'] for r in ai)} / {sum(r['bal'] for r in ai)} / {sum(r['need'] for r in ai)} / {max((r.get('want', 0) for r in ai), default=0)} / "
              f"{min(cs) if cs else '-'}~{max(cs) if cs else '-'} | {' '.join(f'{k}:{v}' for k, v in vc.most_common()) or '-'} | {pt}")
        P("     结论写法：skip:x<minCmd = 想发的兵（min(可用兵, 1.25×吃光所需+3×接壤格数)）小于 minCmd，L5367；skip:avail<=0(safe) = 留底 safeAt 吃光了可用兵，L5358-5361；"
          "skip:x<chunk = 可用兵不够吃光且不到余额的 20%，L5544；break:price>=worth = 报价不低于 worth 且没超软上限，L5265；SEND = 这一手会发出去。")

    # ---------- [GI] ----------
    P("[GI] 和内置 AI 的来回账，按时段（真值逐对战损账）：时段 | 编队被 AI 拿走的格数 / AI 实际耗兵 / 编队余额被打掉（每格）| 编队从 AI 手里拿的格数 / 耗兵（每格）| 编队从空地拿的格数 | 编队互打的格数 / 攻方耗兵 | 时段末：编队领土 / AI 领土 / AI 总兵 / 活着的 AI 数")
    cuts = [c for c in (1500, 2790, 4010, 5670, 9700, 9840, 21500, end) if c <= end]
    cuts = sorted(set(cuts))
    for i in range(len(cuts) - 1):
        a0, a1 = cuts[i], cuts[i + 1]
        lost = [0, 0, 0]; got = [0, 0]; neu = 0; civ = [0, 0]
        for t, a, d, tiles, burnt, dB, dS, n in R["pairLog"]:
            if not (a0 < t <= a1):
                continue
            if d in sq and H <= a < NEUTRAL:
                lost[0] += tiles; lost[1] += burnt; lost[2] += dB
            elif a in sq and H <= d < NEUTRAL:
                got[0] += tiles; got[1] += burnt
            elif a in sq and d == NEUTRAL:
                neu += tiles
            elif a in sq and d in sq:
                civ[0] += tiles; civ[1] += burnt
        j = bisect.bisect_right(snapT, a1) - 1
        sq_terr = sum(snapTerr[j][p] for p in sq)
        k = bisect.bisect_right(ai_ts, a1) - 1
        ai_now = ai_by_t[ai_ts[k]]
        alive = [v for v in ai_now.values() if v[0] > 0]
        P(f"     {a0}~{a1} | {lost[0]} / {lost[1]} / {lost[2]}（{lost[2] / max(1, lost[0]):.1f}）| {got[0]} / {got[1]}（{got[1] / max(1, got[0]):.1f}）| {neu} | {civ[0]} / {civ[1]} | "
          f"{sq_terr} / {sum(v[0] for v in alive)} / {sum(v[1] for v in alive)} / {len(alive)}")

    # ---------- [GJ] ----------
    if os.path.exists(fp):
        import re
        sys.path.insert(0, HERE)
        import r08lib
        slow_by_label = defaultdict(list)
        for rec in r08lib.parse_log(mid):
            if rec["tag"] == "HL-SLOW-TICK":
                m = re.search(r"t=(\d+) took ([\d.]+)ms", rec["body"])
                if m:
                    slow_by_label[rec["label"]].append((int(m.group(1)), float(m.group(2))))
        P("[GJ] 扫尾段（只看日志）：连续的 HL-TICK 快照 nb=0 且领土 ≥80% 陆地算一段。HL-SLOW-TICK 是驱动层记的『这一拍策略耗时超标』，在这些段里每一条都对得上一次找船的水路搜索（base boatOut L1037 的在途条数检查通过之后才搜），"
          "所以『没有慢拍的空档』= 那段时间一次水路搜索都没做")
        for me, b in F["bots"].items():
            tk = b["ticks"]
            slow = sorted({x for lb in b["labels"] for x in slow_by_label.get(lb, [])})
            if not slow:
                continue
            ms = [x[1] for x in slow]
            eps, i = [], 0
            while i < len(tk):
                if tk[i]["nb"] == 0 and tk[i]["terr"] >= 0.8 * land:
                    j = i
                    while j + 1 < len(tk) and tk[j + 1]["nb"] == 0 and tk[j + 1]["terr"] >= 0.8 * land:
                        j += 1
                    eps.append((i, j))
                    i = j + 1
                else:
                    i += 1
            if not eps:
                continue
            P(f"     {b['name']}：慢拍共 {len(slow)} 条，耗时 最小 {min(ms)} / 中位 {statistics.median(ms):.1f} / 最大 {max(ms)} ms；扫尾段 {len(eps)} 段")
            for i, j in eps:
                a, z = tk[i], tk[j]
                pre = tk[i - 1] if i > 0 else a
                nxt = tk[j + 1] if j + 1 < len(tk) else None
                P(f"       段 t={a['t']}~{z['t']}（{j - i + 1} 条快照）：领土 {a['terr']}→{z['terr']}（还差 {land - a['terr']}→{land - z['terr']} 格），余额 {a['bal']}→{z['bal']}，"
                  f"船 {pre['boats']}→{z['boats']}（+{z['boats'] - pre['boats']}），指令 {pre['cmds']}→{z['cmds']}；"
                  + (f"之后 t={nxt['t']}：nb={nxt['nb']}、领土 {nxt['terr']}、船 {nxt['boats']}" if nxt else f"之后没有快照（结果行：{b.get('event')} @ {b.get('deathTick')}）"))
                P("         逐快照 拍:领土/还差/neut/船/余额：" + "；".join(f"{s['t']}:{s['terr']}/{land - s['terr']}/{s['neut']}/{s['boats']}/{s['bal']}" for s in tk[i:j + 1]))
                lo, hi = pre["t"], (nxt["t"] if nxt else z["t"] + 90)
                ss = [x for x in slow if lo <= x[0] <= hi]
                P(f"         t={lo}~{hi} 的慢拍 {len(ss)} 条：" + " ".join(f"{t}({v:.0f})" for t, v in ss))
                ss = ss + [x for x in slow if x[0] > hi][:1]      # 空档要量到段后的第一条慢拍
                gaps = [(ss[k][0], ss[k + 1][0]) for k in range(len(ss) - 1) if ss[k + 1][0] - ss[k][0] >= 100]
                for g0, g1 in gaps:
                    inside = [s for s in tk if g0 <= s["t"] <= g1]
                    P(f"         空档 t={g0}→{g1}（{g1 - g0} 拍没有慢拍）：其间快照 " + "；".join(f"{s['t']}: 领土 {s['terr']} nb={s['nb']} neut={s['neut']} 船 {s['boats']} 余额 {s['bal']}" for s in inside))
                if nxt:
                    after = [x for x in slow if x[0] > z["t"]][:8]
                    P(f"         这一段之后的前 {len(after)} 条慢拍：" + " ".join(f"{t}({v:.0f})" for t, v in after)
                      + f"；之后到下一段 / 终局船数 {z['boats']}→{(tk[eps[eps.index((i, j)) + 1][0] - 1]['boats'] if eps.index((i, j)) + 1 < len(eps) else tk[-1]['boats'])}")

    # ---------- [GK] ----------
    ticks = [int(x) for x in args[args.index("--ticks") + 1].split(",")] if "--ticks" in args else \
        [630, 900, 1440, 1980, 2520, 2730, 2790, 3300, 3600, 3990, 4010, 4500, 4920, 5310, 5670, 6300, 9000, 9700, 9840, 10050, 12000, 21500, 21690, 30000, 36000, end - 1]
    land_k = R["land"] if "land" in R else json.load(open(fp, encoding="utf-8"))["card"]["mapLand"]
    P("[GK] 时间线（真值）：拍 | 各编队号 格（密度）| 编队合计 格 / 占陆地% / 兵 | 内置 AI：活着的个数 / 合计格（占陆地%）/ 合计兵 / 其中 0 兵的个数 / 吃光所需合计（1.78×兵 + 1.5×格）")
    ids = sorted(sq)
    for t in ticks:
        if t > end:
            continue
        j = bisect.bisect_right(snapT, t) - 1
        k = bisect.bisect_right(ai_ts, t) - 1
        alive = [v for v in ai_by_t[ai_ts[k]].values() if v[0] > 0]
        st_ = sum(snapTerr[j][p] for p in ids)
        P(f"     {snapT[j]} | " + " ".join(f"{sq[p]} {snapTerr[j][p]}（{snapBal[j][p] / max(1, snapTerr[j][p]):.1f}）" for p in ids)
          + f" | {st_} / {100 * st_ / land_k:.2f}% / {sum(snapBal[j][p] for p in ids)} | {len(alive)} / {sum(v[0] for v in alive)}（{100 * sum(v[0] for v in alive) / land_k:.1f}%）/ "
            f"{sum(v[1] for v in alive)} / {sum(1 for v in alive if v[1] == 0)} / {round(sum(1.78 * v[1] + 1.5 * v[0] for v in alive))}（AI 快照 t={ai_ts[k]}）")

    with open(os.path.join(OUT, mid, "aigate.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
