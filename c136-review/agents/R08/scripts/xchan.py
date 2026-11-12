#!/usr/bin/env python3
"""xchan.py — 给模拟器定「指令通道」和「对手行为」用的事实：发现集全部录像的指令流（只解码，不做地图模拟）。

先解码（和 xbatch.py 共用）：
    bash c136-review/tools/run-heavy.sh node c136-review/agents/R08/scripts/replay_cmds.mjs \
         --out-dir c136-review/agents/R08/out/_run/streams <局> <局> …
再计数：
    python3 xchan.py [--quiet]        → out/_cross/xchan.txt、xchan.json

只读 /agent/repos/c136-data/bundles/（发现集）；验证集不碰。分组（own / [APEX] / 名字池 / 野人）和 xbatch.py 一样；「机器号」= 前三组。
指令号：1 陆攻(pct, 目标)；2 捐款(pct, 目标)；3 发船(pct, 水格<<3|方向)；4 追船 / 召回；5 撤军；8 / 9 离开。

节：
  [XC-A] 执行拍的格点：指令落在「拍号 mod 7」的哪一格；同一个席位相邻两个落地拍隔几个回合。
  [XC-B] 同一个席位同一拍落地几条：按组 × 时段的分布（按指令条数加权）。
  [XC-C] 追帧：一个席位连续几个回合每回合都有落地、其中至少一个回合 ≥3 条的一串——串长（回合）、串里的条数、顶到 9 条的回合占比、串之前这个席位静了多少拍。
  [XC-D] 同步：一个 180 拍的窗里，有指令的机器号席位里几成有批；同一个服务器拍上有批的机器号席位数。
  [XC-E] 节奏：每个「这一段有指令的席位」每 100 拍落地几条（陆攻 / 船 / 捐款），机器号对野人。
  [XC-F] 陆攻的比例：pct 的中位、≥ 一半余额的占比、接近全压（pct ≥ 1000）的占比。
  [XC-G] 野人的捐款：按引擎受捐额度的四段，条数、全压的占比、收得最多的那个号收了几成、给它捐的人数。
  [XC-H] 离开指令的时间。
  [XC-I] 房间的构成：开局真人数、队数、编队号分在几个队里、同房有没有第二支机器编队（对局卡 + 录像头）。
"""
import json
import os
import re
import statistics
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import facts  # noqa: E402
import xbatch as XB  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")
RUN = os.path.join(OUT, "_run", "streams")
PERIODS = [("0~600", 0, 600), ("600~1500", 600, 1500), ("1500~3000", 1500, 3000), ("3000+", 3000, 10 ** 9)]
DON_BANDS = [("0~2142", 0, 2142), ("2142~3213", 2142, 3213), ("3213~4284", 3213, 4284), ("4284+", 4284, 10 ** 9)]
KIND_CN = {1: "陆攻", 2: "捐款", 3: "发船"}


def period_of(t, bands=PERIODS):
    for i, (_, a, z) in enumerate(bands):
        if a <= t < z:
            return i
    return len(bands) - 1


def q(xs, p):
    if not xs:
        return None
    xs = sorted(xs)
    k = (len(xs) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def fmt(x, nd=0):
    if x is None:
        return "–"
    return f"{x:.{nd}f}"


def pct(a, b, nd=0):
    return "–" if not b else f"{100 * a / b:.{nd}f}%"


def groups(mid, meta, pool):
    H = meta["humanCount"]
    names = [str(x).strip() for x in (meta.get("names") or [""] * H)]
    low = [x.lower() for x in names]
    F = facts.build(mid)
    own = set()
    for me, b in F["bots"].items():
        mr = b.get("meReal") if b.get("meReal") is not None else me
        if mr is not None and 0 <= mr < H and any(low[mr].endswith(lab.lower()) for lab in b["labels"]):
            own.add(mr)
    grp = {}
    for s in range(H):
        if s in own:
            grp[s] = "own"
        elif "[apex]" in low[s]:
            grp[s] = "apex"
        elif low[s] in pool or re.sub(r"^\[[^\]]*\]\s*", "", low[s]) in pool:
            grp[s] = "pool"
        else:
            grp[s] = "wild"
    return grp


def main():
    quiet = "--quiet" in sys.argv
    pool = XB.name_pool()
    ids = XB.discovery_ids()
    lines = []

    def P(s=""):
        lines.append(s)

    n_match = 0
    grid = {"bot": Counter(), "wild": Counter()}
    gap_turn = {"bot": Counter(), "wild": Counter()}
    per_tick_dist = {g: [Counter() for _ in PERIODS] for g in ("bot", "wild")}      # n -> 指令条数
    max_tick = {"bot": 0, "wild": 0}
    runs = []            # (period, turns, cmds, nineTurns, silenceBefore, cohort)
    sync_win = []        # (matchId, w, activeSeats, batchSeats)
    same_tick_seats = Counter()
    cadence = {g: [dict(seats=0, ticks=0, k=Counter()) for _ in PERIODS] for g in ("bot", "wild")}
    atk_pct = {g: [[] for _ in PERIODS] for g in ("bot", "wild")}
    don = [dict(matches=0, cmds=0, full=0, top_share=[], top_donors=[], donors=[], per_match=[]) for _ in DON_BANDS]
    don_bot = [dict(cmds=0, full=0) for _ in DON_BANDS]
    leaves = {"bot": [], "wild": []}
    seats_total = {"bot": 0, "wild": 0}
    per_match_sync = []
    per_match_rows = []
    second_squad = 0
    replay_rows = []

    for mid, card in ids:
        p = os.path.join(RUN, f"{mid}.json")
        if not os.path.exists(p):
            continue
        S = json.load(open(p, encoding="utf-8"))
        meta, cmds = S["meta"], S["cmds"]
        H = meta["humanCount"]
        grp = groups(mid, meta, pool)
        n_match += 1
        last_tick = meta.get("lastTick") or max((c[0] for c in cmds), default=0)
        for s in range(H):
            seats_total["wild" if grp[s] == "wild" else "bot"] += 1
        if sum(1 for s in range(H) if grp[s] in ("apex", "pool")) >= 5:
            second_squad += 1
        n_own = sum(1 for s in range(H) if grp[s] == "own")
        replay_rows.append((mid, card.get("cohort"), last_tick, n_own, meta.get("numberTeams")))
        per_tick = defaultdict(int)
        seat_ticks = defaultdict(set)
        seat_kind = [defaultdict(Counter) for _ in PERIODS]
        don_m = [dict(n=0, full=0, rec=Counter(), donors=defaultdict(set), givers=set()) for _ in DON_BANDS]
        for t, cid, pl, dx, dz in cmds:
            if pl >= H:
                continue
            g = "wild" if grp[pl] == "wild" else "bot"
            if cid in (8, 9):
                leaves[g].append(t)
                continue
            if t < 0 or cid not in (1, 2, 3):
                continue
            grid[g][t % 7] += 1
            per_tick[(pl, t)] += 1
            seat_ticks[pl].add(t)
            seat_kind[period_of(t)][pl][cid] += 1
            if cid == 1:
                atk_pct[g][period_of(t)].append(dx)
            if cid == 2:
                b = period_of(t, DON_BANDS)
                if g == "wild":
                    d = don_m[b]
                    d["n"] += 1
                    d["full"] += dx >= 1000
                    d["rec"][dz] += 1
                    d["donors"][dz].add(pl)
                    d["givers"].add(pl)
                else:
                    don_bot[b]["cmds"] += 1
                    don_bot[b]["full"] += dx >= 1000
        for b, d in enumerate(don_m):
            if d["n"]:
                don[b]["matches"] += 1
                don[b]["cmds"] += d["n"]
                don[b]["full"] += d["full"]
                don[b]["per_match"].append(d["n"])
                don[b]["donors"].append(len(d["givers"]))
                if d["n"] >= 10:
                    top, c = d["rec"].most_common(1)[0]
                    don[b]["top_share"].append(c / d["n"])
                    don[b]["top_donors"].append(len(d["donors"][top]))
                mx_donors = max(len(v) for v in d["donors"].values())
                don[b]["feed3"] = don[b].get("feed3", 0) + (mx_donors >= 3)
                don[b]["feed4"] = don[b].get("feed4", 0) + (mx_donors >= 4)
        for (pl, t), n in per_tick.items():
            g = "wild" if grp[pl] == "wild" else "bot"
            per_tick_dist[g][period_of(t)][min(n, 10)] += n
            max_tick[g] = max(max_tick[g], n)
        # 相邻落地拍隔几个回合
        for pl, ts in seat_ticks.items():
            g = "wild" if grp[pl] == "wild" else "bot"
            xs = sorted(ts)
            for a, b in zip(xs, xs[1:]):
                d = b - a
                gap_turn[g][min(d // 7 if d % 7 == 0 else -1, 30)] += 1
        # 追帧串（机器号）
        for pl, ts in seat_ticks.items():
            if grp[pl] == "wild":
                continue
            xs = sorted(ts)
            i = 0
            while i < len(xs):
                j = i
                while j + 1 < len(xs) and xs[j + 1] - xs[j] == 7:
                    j += 1
                seg = xs[i:j + 1]
                cnt = [per_tick[(pl, t)] for t in seg]
                if max(cnt) >= 3:
                    silence = (seg[0] - xs[i - 1]) if i > 0 else None
                    runs.append((period_of(seg[0]), len(seg), sum(cnt), sum(1 for c in cnt if c >= 9), silence, card.get("cohort"), max(cnt)))
                i = j + 1
        # 同步：180 拍窗
        win_active = defaultdict(set)
        win_batch = defaultdict(set)
        tick_batch_seats = defaultdict(set)
        for (pl, t), n in per_tick.items():
            if grp[pl] == "wild":
                continue
            w = t // 180 * 180
            win_active[w].add(pl)
            if n >= 3:
                win_batch[w].add(pl)
                tick_batch_seats[t].add(pl)
        shares = []
        for w in sorted(win_active):
            if 600 <= w < 1500 and len(win_active[w]) >= 5:
                sync_win.append((mid, w, len(win_active[w]), len(win_batch[w])))
                shares.append(len(win_batch[w]) / len(win_active[w]))
        if shares:
            per_match_sync.append((mid, card.get("cohort"), max(shares), statistics.median(shares)))
        for t, ss in tick_batch_seats.items():
            if 600 <= t < 3000:
                same_tick_seats[min(len(ss), 6)] += 1
        # 节奏
        for i, (_, a, z) in enumerate(PERIODS):
            span = min(z, last_tick) - a
            if span <= 0:
                continue
            for pl, kc in seat_kind[i].items():
                g = "wild" if grp[pl] == "wild" else "bot"
                c = cadence[g][i]
                c["seats"] += 1
                c["ticks"] += span
                for k, v in kc.items():
                    c["k"][k] += v
        per_match_rows.append(dict(matchId=mid, cohort=card.get("cohort"), H=H))

    P(f"[XC-A] 执行拍的格点（{n_match} 份录像；陆攻 / 捐款 / 发船，t ≥ 0）")
    for g, cn in (("bot", "机器号"), ("wild", "野人")):
        tot = sum(grid[g].values())
        P(f"  {cn}：{tot} 条；拍号 mod 7 = 0 的 {pct(grid[g][0], tot, 1)}；其余各格 " + " / ".join(f"{r}:{grid[g][r]}" for r in range(1, 7)))
    P("  同一个席位相邻两个落地拍隔几个回合（1 回合 = 7 拍）：组 | 1 | 2 | 3 | 4~5 | 6~10 | 11~29 | ≥30 | 不是 7 的整数倍")
    for g, cn in (("bot", "机器号"), ("wild", "野人")):
        c = gap_turn[g]
        tot = sum(c.values())
        cell = lambda ks: pct(sum(c[k] for k in ks), tot)
        P(f"    {cn} | {cell([1])} | {cell([2])} | {cell([3])} | {cell([4, 5])} | {cell(range(6, 11))} | {cell(range(11, 30))} | {cell([30])} | {cell([-1])}")
    P()
    P("[XC-B] 同一个席位同一拍落地几条（按指令条数加权）：组 | 时段 | 指令 | 1 条 | 2 条 | 3~4 条 | 5~8 条 | 9 条 | ≥10 条")
    for g, cn in (("bot", "机器号"), ("wild", "野人")):
        for i, (pn, _, _) in enumerate(PERIODS):
            c = per_tick_dist[g][i]
            tot = sum(c.values())
            cell = lambda ks: pct(sum(c[k] for k in ks), tot, 1)
            P(f"    {cn} | {pn} | {tot} | {cell([1])} | {cell([2])} | {cell([3, 4])} | {cell([5, 6, 7, 8])} | {cell([9])} | {cell([10])}")
    P(f"  一拍最多：机器号 {max_tick['bot']} 条，野人 {max_tick['wild']} 条")
    P()
    P("[XC-C] 追帧串（机器号；一个席位连续几个回合都有落地、其中至少一个回合 ≥3 条）")
    P("  时段 | 串数 | 串长（回合）P50 / P90 / 最大 | 串里的条数 P50 / P90 / 最大 | 有回合顶到 9 条的串 | 串之前这个席位静了多少拍 P50 / P90 / 最大 | 静了 ≥70 拍的占比")
    for i, (pn, _, _) in enumerate(PERIODS):
        rs = [r for r in runs if r[0] == i]
        if not rs:
            continue
        tl = [r[1] for r in rs]
        cc = [r[2] for r in rs]
        si = [r[4] for r in rs if r[4] is not None]
        P(f"    {pn} | {len(rs)} | {fmt(q(tl, .5))} / {fmt(q(tl, .9))} / {max(tl)} | {fmt(q(cc, .5))} / {fmt(q(cc, .9))} / {max(cc)} | {pct(sum(1 for r in rs if r[3] > 0), len(rs))}"
          f" | {fmt(q(si, .5))} / {fmt(q(si, .9))} / {max(si) if si else '–'} | {pct(sum(1 for x in si if x >= 70), len(si))}")
    rs = [r for r in runs if r[0] in (1, 2)]
    by_len = Counter(min(r[1], 6) for r in rs)
    P("  600~3000 的串按串长：" + "；".join(f"{k if k < 6 else '≥6'} 回合 {by_len[k]}（{pct(by_len[k], len(rs))}）" for k in sorted(by_len)))
    big = [r for r in rs if r[2] >= 9]
    P(f"  600~3000 一串 ≥9 条的 {len(big)} 串（{pct(len(big), len(rs))}），≥18 条的 {sum(1 for r in rs if r[2] >= 18)} 串，最大 {max((r[2] for r in rs), default=0)} 条")
    for coh in ("squad10", "squad20"):
        r2 = [r for r in rs if r[5] == coh]
        if r2:
            cc = [r[2] for r in r2]
            si = [r[4] for r in r2 if r[4] is not None]
            P(f"    {coh}：{len(r2)} 串，串里的条数 P50 / P90 {fmt(q(cc, .5))} / {fmt(q(cc, .9))}，串之前静了 P50 / P90 {fmt(q(si, .5))} / {fmt(q(si, .9))} 拍")
    P()
    P("[XC-D] 同步（600~1500，180 拍一窗，窗里有指令的机器号席位 ≥5 个）")
    tot_a = sum(x[2] for x in sync_win)
    tot_b = sum(x[3] for x in sync_win)
    sh = [x[3] / x[2] for x in sync_win]
    P(f"  {len(sync_win)} 个窗：有指令的机器号席位合计 {tot_a}，其中这一窗有批的 {tot_b}（{pct(tot_b, tot_a)}）；逐窗占比 P25 / P50 / P75 = {fmt(q(sh, .25), 2)} / {fmt(q(sh, .5), 2)} / {fmt(q(sh, .75), 2)}")
    P(f"  有批的窗（≥1 个席位有批）{sum(1 for x in sync_win if x[3] > 0)} 个，其中一半以上的席位都有批的 {sum(1 for x in sync_win if x[3] >= 0.5 * x[2])} 个，全部席位都有批的 {sum(1 for x in sync_win if x[3] == x[2])} 个")
    mx = [x[2] for x in per_match_sync]
    P(f"  逐局「最卡的那一窗里有批的席位占比」：{len(per_match_sync)} 局，P25 / P50 / P75 = {fmt(q(mx, .25), 2)} / {fmt(q(mx, .5), 2)} / {fmt(q(mx, .75), 2)}；≥0.8 的 {sum(1 for x in mx if x >= 0.8)} 局，0 的 {sum(1 for x in mx if x == 0)} 局")
    tot = sum(same_tick_seats.values())
    P("  同一个服务器拍上有批的机器号席位数（600~3000）：" + "；".join(f"{k if k < 6 else '≥6'} 个 {same_tick_seats[k]}（{pct(same_tick_seats[k], tot)}）" for k in sorted(same_tick_seats)))
    P()
    P("[XC-E] 节奏：每个「这一段有指令的席位」每 100 拍落地的条数（按录像长度截断）：组 | 时段 | 席位 | 陆攻 | 发船 | 捐款")
    for g, cn in (("bot", "机器号"), ("wild", "野人")):
        for i, (pn, _, _) in enumerate(PERIODS):
            c = cadence[g][i]
            if not c["ticks"]:
                continue
            r = lambda k: f"{100 * c['k'][k] / c['ticks']:.2f}"
            P(f"    {cn} | {pn} | {c['seats']} | {r(1)} | {r(3)} | {r(2)}")
    P(f"  真人席位合计：机器号 {seats_total['bot']}，野人 {seats_total['wild']}")
    P()
    P("[XC-F] 陆攻的比例（指令带的 pct，÷1024 = 落地时余额的几成）：组 | 时段 | 条数 | pct÷1024 的 P25 / P50 / P75 | ≥ 一半余额 | pct ≥ 1000（接近全压）")
    for g, cn in (("bot", "机器号"), ("wild", "野人")):
        for i, (pn, _, _) in enumerate(PERIODS):
            xs = atk_pct[g][i]
            if not xs:
                continue
            P(f"    {cn} | {pn} | {len(xs)} | {fmt(q(xs, .25) / 1024, 2)} / {fmt(q(xs, .5) / 1024, 2)} / {fmt(q(xs, .75) / 1024, 2)} | {pct(sum(1 for x in xs if x >= 512), len(xs), 1)} | {pct(sum(1 for x in xs if x >= 1000), len(xs), 1)}")
    P()
    P("[XC-G] 野人的捐款（录像里落地的；按引擎受捐额度换档的拍分段）")
    P("  时段 | 有野人捐款的局 | 条数 | 每局条数 中位 / 最大 | 捐的人数 中位 | pct ≥ 1000 的占比 | ≥10 条的局里：收得最多的那个号收的占比 中位（局数）| 给它捐的人数 中位 / 最大 | 对照：机器号的捐款条数（pct ≥ 1000 的占比）")
    for b, (bn, _, _) in enumerate(DON_BANDS):
        d = don[b]
        P(f"    {bn} | {d['matches']} | {d['cmds']} | {fmt(q(d['per_match'], .5))} / {max(d['per_match']) if d['per_match'] else '–'} | {fmt(q(d['donors'], .5))} | {pct(d['full'], d['cmds'])}"
          f" | {fmt(q(d['top_share'], .5), 2)}（{len(d['top_share'])}）| {fmt(q(d['top_donors'], .5))} / {max(d['top_donors']) if d['top_donors'] else '–'}"
          f" | {don_bot[b]['cmds']}（{pct(don_bot[b]['full'], don_bot[b]['cmds'])}）")
    P("  「集中喂一个号」的局数（同一段里有一个号收到 ≥3 个 / ≥4 个不同野人的捐款）：" + "；".join(
        f"{bn} {don[b].get('feed3', 0)} / {don[b].get('feed4', 0)}（有野人捐款的 {don[b]['matches']} 局里）" for b, (bn, _, _) in enumerate(DON_BANDS)))
    P()
    P("[XC-H] 离开指令（8 / 9）的拍：组 | 条数 | P10 / P25 / P50 / P75 / P90 | ≤1500 拍的占比")
    for g, cn in (("bot", "机器号"), ("wild", "野人")):
        xs = [t for t in leaves[g] if t >= 0]
        P(f"    {cn} | {len(xs)} | {fmt(q(xs, .1))} / {fmt(q(xs, .25))} / {fmt(q(xs, .5))} / {fmt(q(xs, .75))} / {fmt(q(xs, .9))} | {pct(sum(1 for t in xs if t <= 1500), len(xs))}")

    P()
    P(f"[XC-I] 房间的构成（发现集 {len(ids)} 局的对局卡；对局卡有 4 局读错过，见跨局报告 §9 第 10 条）")
    hs = [c.get("seededPlayers") for _, c in ids if c.get("seededPlayers")]
    P(f"  开局真人数 P10 / P25 / P50 / P75 / P90 / 最大 = {fmt(q(hs, .1))} / {fmt(q(hs, .25))} / {fmt(q(hs, .5))} / {fmt(q(hs, .75))} / {fmt(q(hs, .9))} / {max(hs)}；≤24 人的 {sum(1 for h in hs if h <= 24)} 局，≥80 人的 {sum(1 for h in hs if h >= 80)} 局")
    lands = [c.get("mapLand") for _, c in ids if c.get("mapLand")]
    P(f"  全图陆地 P10 / P50 / P90 = {fmt(q(lands, .1))} / {fmt(q(lands, .5))} / {fmt(q(lands, .9))} 格")
    tc = Counter((c.get("actualTeams") if c.get("actualTeams") is not None else c.get("nominalTeams")) for _, c in ids)
    P("  队数（actualTeams）：" + "；".join(f"{k} 队 {v} 局" for k, v in sorted(tc.items(), key=lambda kv: (kv[0] is None, kv[0]))))
    for coh in ("squad10", "squad20", "squad8"):
        rows = [c for _, c in ids if c.get("cohort") == coh]
        if not rows:
            continue
        dst = Counter(min(c.get("distinctSquadTeams") or 0, 4) for c in rows)
        share = [(c.get("squadBots") or 0) / c["seededPlayers"] for c in rows if c.get("seededPlayers")]
        blk = []
        for c in rows:
            tsc = c.get("teamSplitCounts") or {}
            if tsc and c.get("squadBots"):
                blk.append(max(tsc.values()) / c["squadBots"])
        P(f"  {coh}（{len(rows)} 局）：编队号分在几个队里 " + "；".join(f"{k if k < 4 else '≥4'} 个队 {dst[k]} 局" for k in sorted(dst))
          + f"；编队占开局真人的 P25 / P50 / P75 = {fmt(q(share, .25), 2)} / {fmt(q(share, .5), 2)} / {fmt(q(share, .75), 2)}"
          + f"；最大的那一块占编队号的 P25 / P50 / P75 = {fmt(q(blk, .25), 2)} / {fmt(q(blk, .5), 2)} / {fmt(q(blk, .75), 2)}")
    P(f"  有录像的 {n_match} 局里，同房另有一支机器编队（[APEX] + 名字池的席位 ≥5）的 {second_squad} 局")
    nt = Counter(r[4] for r in replay_rows)
    P("  录像头里的队数（numberTeams；0 = 自由混战）：" + "；".join(f"{k} 队 {v} 局" for k, v in sorted(nt.items(), key=lambda kv: (kv[0] is None, kv[0] or 0))))
    valid = None
    try:
        with open(os.path.join(OUT, "_cross", "xtruth.json"), encoding="utf-8") as f:
            valid = {m["matchId"] for m in json.load(f)["matches"] if m.get("valid") and not m.get("spawnOnly")}
    except (OSError, KeyError, ValueError):
        pass
    if valid is not None:
        P("  录像够不够长（xtruth.py 里重演和日志逐行对得上、且有对局段的局）：断面 | 录像到这一拍的局 | 其中 squad10 / squad20")
        ok = [r for r in replay_rows if r[0] in valid]
        for T in (630, 1500, 3000, 4284, 6000):
            rs2 = [r for r in ok if r[2] >= T]
            P(f"    t={T} | {len(rs2)} | {sum(1 for r in rs2 if r[1] == 'squad10')} / {sum(1 for r in rs2 if r[1] == 'squad20')}")
        P(f"    （对得上且有对局段的 {len(ok)} 局；t=0 的断面另外可以用只有出生期的录像）")

    txt = "\n".join(lines) + "\n"
    os.makedirs(os.path.join(OUT, "_cross"), exist_ok=True)
    with open(os.path.join(OUT, "_cross", "xchan.txt"), "w", encoding="utf-8") as f:
        f.write(txt)
    with open(os.path.join(OUT, "_cross", "xchan.json"), "w", encoding="utf-8") as f:
        json.dump(dict(matches=n_match, grid={g: dict(grid[g]) for g in grid}, runs=runs, perMatchSync=per_match_sync,
                       seats=seats_total), f, ensure_ascii=False)
    if not quiet:
        print(txt)
    print(f"xchan: {n_match} 份录像 → out/_cross/xchan.txt")


if __name__ == "__main__":
    main()
