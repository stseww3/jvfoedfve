#!/usr/bin/env python3
"""deathbank.py — 「四分之一峰值线出局时账上还有多少兵」的真相口径账（整局重演；我方号和野人同一把尺子）。

引擎的出局规则（game.js aliveTick L1298-1312）：地 ≤ ⌊峰值/4⌋ 就 collapse → eliminate，账上的兵和在途的兵一起清零。
日志口径（xscan.py [XS-B] / [XS-C]）只看得到本编队的号，余额是客户端最后一次看到的；这里用重演器在引擎清零之前那一拍的真值，
并且把同一批局里的野人席位放在旁边当对照——同一条引擎规则，别人出局时账上是什么样。

原料：deathbank.mjs（squad10 的局）和 namepool.mjs（squad20 的局）→ out/_run/deathbank/<局>.json
    python3 deathbank.py [--quiet]     → out/_cross/deathbank.txt、deathbank.json

口径：
  · 我方号 = 对局包里有日志、席位和名字对得上的号 ∪ 重演器认出来的号；[APEX] = 名字带 [APEX]、不在我方号里的席位；
    池名 = 名字在名字池里、不在我方号里的席位；其余真人席位 = 野人。（和 xtruth.seat_groups 同一套分法。）
  · 一行「出局」= 引擎对这个席位调了一次 eliminate（除名），或者「陆上清场但海上有船」（地和兵清零、暂不除名）。出生阶段的不算。
    同一个席位两种都发生过的（先清场、后来船也没了再除名），只取第一次（清零发生的那一次）。
  · 在线 = 出局那一拍还没发过离开指令；空壳 = 离开以后由引擎按内置 AI 接管的席位。
  · 「地还在」= 出局前那一拍还有地（>0）——也就是被四分之一线除名的，不是被吃光的。
  · 账上的兵 = 出局前那一拍的余额；在途的兵 = 它自己派出去还没结算完的进攻兵；压在它身上的兵 = 那一拍所有正在打它的人挂在它身上的进攻兵。

节：
  [DB-A] 覆盖：多少局、多少真人席位、多少行出局。
  [DB-B] 出局的方式：按席位分组 × 在线 / 空壳——被吃光 / 地还在就被四分之一线除名；除名时 地÷峰值 的分布。
  [DB-C] 在线出局的席位账上的兵：合计、每个号平均、中位、≥10 万的占比、密度（兵÷地）、账上的兵 ÷ 压在它身上的兵。
  [DB-D] 按时段。
  [DB-E] 按编队档、按主队输赢。
  [DB-H] 出局那一拍这笔兵在引擎里有没有去处：4284 拍前后 × 同队还有没有活着、在线的真人。
  [DB-F] 和日志口径（xscan [XS-B]）对账。
  [DB-G] 逐局一行。
"""
import glob
import json
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import xbatch as XB  # noqa: E402
import facts  # noqa: E402
import roompairs as RP  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")
RUN = os.path.join(OUT, "_run", "deathbank")
PERIODS = [("0~600", 0, 600), ("600~1500", 600, 1500), ("1500~3000", 1500, 3000), ("3000~4284", 3000, 4284), ("4284+", 4284, 10 ** 9)]
GROUPS = ["own", "wild", "apex", "pool"]
COHORTS = ("squad10", "squad20")
GROUP_CN = dict(own="我方号", wild="野人", apex="[APEX]（没有日志的）", pool="池名（没有日志的）")


def pct(a, b, nd=0):
    return "–" if not b else f"{100 * a / b:.{nd}f}%"


def q(xs, p):
    if not xs:
        return None
    s = sorted(xs)
    return s[min(len(s) - 1, int(p * (len(s) - 1) + 0.5))]


def fq(xs, ps=(0.1, 0.25, 0.5, 0.75, 0.9), nd=2):
    if not xs:
        return "–"
    return " / ".join(f"{q(xs, p):.{nd}f}" for p in ps)


def period_of(t):
    for i, (_, a, z) in enumerate(PERIODS):
        if a <= t < z:
            return i
    return len(PERIODS) - 1


def facts_own(mid, H, low):
    F = facts.build(mid)
    own = set()
    for me, b in F["bots"].items():
        mr = b.get("meReal") if b.get("meReal") is not None else me
        if mr is not None and 0 <= mr < H and any(low[mr].endswith(lab.lower()) for lab in b["labels"]):
            own.add(mr)
    return own


def main():
    quiet = "--quiet" in sys.argv
    pool = XB.name_pool()
    cards = dict(XB.discovery_ids())
    try:
        XT = {m["matchId"]: m for m in json.load(open(os.path.join(OUT, "_cross", "xtruth.json"), encoding="utf-8"))["matches"]}
    except Exception:
        XT = {}
    lines = []

    def P(s=""):
        lines.append(s)

    files = sorted(glob.glob(os.path.join(RUN, "*.json")))
    recs = []        # 每行出局一条
    per_match = []
    seats_n = Counter()
    seats_dead_online = Counter()
    # 第一遍：每份包的我方号；同一份录像（同一个物理房间）被两份包用到时，把两边的我方号并起来
    loaded = []
    own_by_rec = defaultdict(dict)
    for fp in files:
        R = json.load(open(fp, encoding="utf-8"))
        mid = R["matchId"]
        card = cards.get(mid)
        if card is None:
            continue
        H = R["H"]
        low = [str(x).strip().lower() for x in R["names"]]
        rec = R.get("replayFrom") or mid
        own_set = set(i for i in R["squad"].values() if i >= 0) | facts_own(mid, H, low)
        if not own_set:
            continue
        loaded.append((mid, card.get("cohort"), R, low, rec, own_set))
        for s in own_set:
            own_by_rec[rec][s] = mid
    seen_rec = set()
    for mid, cohort, R, low, rec, own_set in loaded:
        H = R["H"]
        left = R["leftT"]
        first = rec not in seen_rec          # 这份录像第一次出现：野人 / [APEX] / 池名席位在跨档合计里只算这一次
        seen_rec.add(rec)
        cut, _checked = RP.cut_of(rec)       # 模拟器和引擎第一次对不上的那一拍；那以后的出局不算

        def grp(s):
            if s in own_set:
                return "own"
            if s in own_by_rec[rec]:
                return "peer"                # 同房另一份包的号：在那一份包里算我方号，这里不重复算
            if "[apex]" in low[s]:
                return "apex"
            if low[s] in pool:
                return "pool"
            return "wild"

        played = [s for s in range(H) if R["seats"][s][0] > 0]          # 整局有过地的席位
        teams = R["teams"]
        team_game = R["gameMode"] != 0
        death_t = R["deathT"]
        for s in played:
            g = grp(s)
            if g == "own" or (first and g != "peer"):
                seats_n[g] += 1
        seen = set()
        won = bool(XT.get(mid, {}).get("won"))
        m = dict(mid=mid, cohort=cohort, H=H, end=R["endTick"] if cut is None else min(R["endTick"], cut), rec=rec, cut=cut, dropped=0, exact=R.get("exact"), mismT=R.get("mismT"),
                 won=won, own=len([s for s in played if s in own_set]), rows=0, wildSeats=len([s for s in played if grp(s) == "wild"]))
        mc = Counter()
        for t, p, kind, terr, bal, peak, state, out, n_atk, press, top, boats in R["deaths"]:
            if p in seen or p >= H:
                continue
            if kind == "eliminate" and terr == 0 and peak == 0 and bal == 0:
                continue                                                  # 清场以后的空除名
            if cut is not None and t >= cut:
                m["dropped"] += 1
                continue
            seen.add(p)
            g = grp(p)
            if g == "peer":
                continue
            dup = g != "own" and not first
            online = state != 2
            # 出局那一拍同队还活着、在线的真人（引擎里捐款只能给同队；t ≥ 4284 以后不查受捐额度）
            mates_own = mates_any = 0
            if team_game and teams[p] != 0:
                for s2 in played:
                    if s2 == p or teams[s2] != teams[p]:
                        continue
                    if 0 <= death_t[s2] <= t or 0 <= left[s2] <= t:
                        continue
                    mates_any += 1
                    if s2 in own_set:
                        mates_own += 1
            r = dict(mid=mid, cohort=cohort, won=won, t=t, p=p, g=g, dup=dup, online=online, kind=kind, terr=terr, bal=bal, peak=peak, out=out, nAtk=n_atk, press=press, boats=boats,
                     matesOwn=mates_own, matesAny=mates_any, teamGame=team_game)
            recs.append(r)
            m["rows"] += 1
            if online and not dup:
                seats_dead_online[g] += 1
            if g == "own" and online:
                mc["ownDead"] += 1
                mc["ownBal"] += bal
                mc["ownOut"] += out
                if terr > 0:
                    mc["ownLine"] += 1
                    mc["ownLineBal"] += bal
                if bal >= 100000:
                    mc["own100k"] += 1
            if g == "wild" and online:
                mc["wildDead"] += 1
                mc["wildBal"] += bal
        m.update(mc)
        per_match.append(m)

    pooled = [r for r in recs if not r["dup"]]      # 跨档合计用：同一个房间的野人 / [APEX] / 池名席位只算一次
    n_rooms = len({m["rec"] for m in per_match})
    borrowed = [m for m in per_match if m["rec"] != m["mid"]]
    cuts = {}
    for m in per_match:
        if m["cut"] is not None:
            cuts.setdefault(m["rec"], [m["cut"], 0, []])
            cuts[m["rec"]][1] = max(cuts[m["rec"]][1], m["dropped"])
            cuts[m["rec"]][2].append(m["mid"])
    J = {"matches": len(per_match), "rows": len(pooled), "rooms": n_rooms}
    P(f"deathbank.py — 四分之一峰值线出局时账上的兵（真相口径）：{len(per_match)} 局（squad10 {sum(1 for m in per_match if m['cohort'] == 'squad10')} / squad20 {sum(1 for m in per_match if m['cohort'] == 'squad20')}），整局重演")
    P()
    P("[DB-A] 覆盖")
    P(f"  {len(per_match)} 份对局包是 {n_rooms} 个物理房间。用同房另一份包的录像重演的 {len(borrowed)} 局"
      + ("：" + "；".join(f"{m['mid']} ← {m['rec']}（到 {m['end']} 拍，日志逐行核对 {m['exact'][0]} / {m['exact'][1]}" + (f"，第一次对不上在 {m['mismT']} 拍" if m["mismT"] is not None else "") + "）" for m in borrowed) if borrowed else "")
      + "（roompairs.py）")
    P(f"  模拟器的重演和真引擎中途对不上的录像 {len(cuts)} 份（fidabl.txt [FA-E]）；对不上以后的出局记录不算："
      + ("；".join(f"{rec} 从 {c[0]} 拍起（丢掉 {c[1]} 行" + (f"；{' '.join(x for x in c[2] if x != rec)} 用的是同一份录像" if any(x != rec for x in c[2]) else "") + "）" for rec, c in sorted(cuts.items())) or "无"))
    P("  同一个房间出了两份包时：两边的号各算各的我方号；房间里的野人 / [APEX] / 池名席位在 [DB-A]~[DB-D] 的合计里只算一次，在 [DB-I] 按档分开的对照里两档各算一次")
    P("  整局有过地的真人席位：" + "；".join(f"{GROUP_CN[g]} {seats_n[g]}" for g in GROUPS) + f"；出局记录 {len(pooled)} 行")
    P("  其中在线时出局的：" + "；".join(f"{GROUP_CN[g]} {seats_dead_online[g]}（{pct(seats_dead_online[g], seats_n[g])}）" for g in GROUPS))
    J["seats"] = dict(seats_n)
    J["deadOnline"] = dict(seats_dead_online)
    P()
    P("[DB-B] 出局的方式")
    P("  组 | 在线 / 空壳 | 出局 | 被吃光（地 = 0）| 地还在就被除名（四分之一线）| 陆上清场但海上有船 | 地还在的：出局前 地÷峰值 的 10% / 25% / 50% / 75% / 90% 分位 | 其中 地÷峰值 > 0.25 的")
    J["mode"] = {}
    for g in GROUPS:
        for online in (True, False):
            rs = [r for r in pooled if r["g"] == g and r["online"] == online]
            if not rs:
                continue
            eaten = [r for r in rs if r["terr"] == 0]
            line = [r for r in rs if r["terr"] > 0]
            lb = [r for r in rs if r["kind"] != "eliminate"]
            ratio = [r["terr"] / r["peak"] for r in line if r["peak"] > 0]
            over = sum(1 for x in ratio if x > 0.25)
            P(f"  {GROUP_CN[g]} | {'在线' if online else '空壳'} | {len(rs)} | {len(eaten)}（{pct(len(eaten), len(rs))}）| {len(line)}（{pct(len(line), len(rs))}）| {len(lb)} | {fq(ratio, nd=3)} | {over}")
            J["mode"][f"{g}|{'on' if online else 'shell'}"] = dict(n=len(rs), eaten=len(eaten), line=len(line), boats=len(lb), ratioQ=[q(ratio, p) for p in (0.1, 0.25, 0.5, 0.75, 0.9)], over=over)
    P()
    P("[DB-C] 在线时出局的席位：出局前那一拍账上的兵")
    P("  组 | 出局的号 | 账上的兵合计 | 每个号平均 | 中位 | ≥10 万的号 | ≥100 万的号 | 在途的兵合计 | 密度（兵÷地；地还在的号）10% / 50% / 90% 分位 | 账上的兵 ÷ 压在它身上的兵（有人在打它的号）25% / 50% / 75% 分位 | 账上的兵比压在身上的兵多的号")
    J["bank"] = {}
    for g in GROUPS:
        rs = [r for r in pooled if r["g"] == g and r["online"]]
        if not rs:
            continue
        bals = [r["bal"] for r in rs]
        dens = [r["bal"] / r["terr"] for r in rs if r["terr"] > 0]
        rel = [r["bal"] / r["press"] for r in rs if r["press"] > 0]
        more = sum(1 for r in rs if r["press"] > 0 and r["bal"] > r["press"])
        n_press = sum(1 for r in rs if r["press"] > 0)
        P(f"  {GROUP_CN[g]} | {len(rs)} | {sum(bals)} | {sum(bals) / len(rs):.0f} | {q(bals, 0.5)} | {sum(1 for b in bals if b >= 100000)}（{pct(sum(1 for b in bals if b >= 100000), len(rs))}）| "
          f"{sum(1 for b in bals if b >= 1000000)}（{pct(sum(1 for b in bals if b >= 1000000), len(rs))}）| {sum(r['out'] for r in rs)} | {fq(dens, (0.1, 0.5, 0.9), 1)} | {fq(rel, (0.25, 0.5, 0.75), 2)} | {more} / {n_press}（{pct(more, n_press)}）")
        J["bank"][g] = dict(n=len(rs), bal=sum(bals), mean=sum(bals) / len(rs), median=q(bals, 0.5), ge100k=sum(1 for b in bals if b >= 100000), ge1m=sum(1 for b in bals if b >= 1000000),
                            out=sum(r["out"] for r in rs), densQ=[q(dens, p) for p in (0.1, 0.5, 0.9)], relQ=[q(rel, p) for p in (0.25, 0.5, 0.75)], more=more, nPress=n_press)
    P("  只看「地还在就被四分之一线除名」的在线席位：")
    P("  组 | 号 | 账上的兵合计 | 每个号平均 | 中位 | ≥10 万的号 | 出局前的地合计 | 峰值合计")
    J["bankLine"] = {}
    for g in GROUPS:
        rs = [r for r in pooled if r["g"] == g and r["online"] and r["terr"] > 0]
        if not rs:
            continue
        bals = [r["bal"] for r in rs]
        P(f"  {GROUP_CN[g]} | {len(rs)} | {sum(bals)} | {sum(bals) / len(rs):.0f} | {q(bals, 0.5)} | {sum(1 for b in bals if b >= 100000)}（{pct(sum(1 for b in bals if b >= 100000), len(rs))}）| {sum(r['terr'] for r in rs)} | {sum(r['peak'] for r in rs)}")
        J["bankLine"][g] = dict(n=len(rs), bal=sum(bals), median=q(bals, 0.5), ge100k=sum(1 for b in bals if b >= 100000), terr=sum(r["terr"] for r in rs), peak=sum(r["peak"] for r in rs))
    P()
    P("[DB-D] 按时段（在线时出局的席位）：出局的号 / 账上的兵合计 / 每个号平均 / ≥10 万的占比")
    P("  时段 | 我方号 | 野人")
    J["period"] = []
    for i, (cn, _, _) in enumerate(PERIODS):
        cells = []
        jr = {}
        for g in ("own", "wild"):
            rs = [r for r in pooled if r["g"] == g and r["online"] and period_of(r["t"]) == i]
            b = sum(r["bal"] for r in rs)
            k = sum(1 for r in rs if r["bal"] >= 100000)
            cells.append(f"{len(rs)} / {b} / {b / len(rs):.0f} / {pct(k, len(rs))}" if rs else "0")
            jr[g] = dict(n=len(rs), bal=b, ge100k=k)
        J["period"].append(jr)
        P(f"  {cn} | {cells[0]} | {cells[1]}")
    P()
    P("[DB-E] 按编队档、按主队输赢（我方在线时出局的号）")
    P("  分组 | 局 | 有过地的我方号 | 在线时出局的 | 其中地还在就被除名的 | 账上的兵合计 | 每个出局号平均 | ≥10 万的号 | 有 ≥10 万出局号的局")
    J["split"] = {}
    for label, sel in (("squad10", lambda m: m["cohort"] == "squad10"), ("squad20", lambda m: m["cohort"] == "squad20"),
                       ("主队赢的局", lambda m: m["won"]), ("主队没赢的局", lambda m: not m["won"]), ("全部", lambda m: True)):
        ms = [m for m in per_match if sel(m)]
        if not ms:
            continue
        d = sum(m.get("ownDead", 0) for m in ms)
        b = sum(m.get("ownBal", 0) for m in ms)
        P(f"  {label} | {len(ms)} | {sum(m['own'] for m in ms)} | {d}（{pct(d, sum(m['own'] for m in ms))}）| {sum(m.get('ownLine', 0) for m in ms)} | {b} | {b / d if d else 0:.0f} | {sum(m.get('own100k', 0) for m in ms)} | "
          f"{sum(1 for m in ms if m.get('own100k', 0))}（{pct(sum(1 for m in ms if m.get('own100k', 0)), len(ms))}）")
        J["split"][label] = dict(matches=len(ms), own=sum(m["own"] for m in ms), dead=d, line=sum(m.get("ownLine", 0) for m in ms), bal=b, ge100k=sum(m.get("own100k", 0) for m in ms),
                                 matches100k=sum(1 for m in ms if m.get("own100k", 0)))
    P()
    P("[DB-H] 我方在线时出局的号：出局那一拍，账上的兵在引擎里有没有去处（捐款只能给同队；t ≥ 4284 以后引擎不再查受捐额度）")
    P("  档 | 时段 | 出局那一拍同队还有谁活着、在线 | 号 | 账上的兵合计 | 其中 ≥10 万的号 | 出局前的地合计")
    J["outlet"] = []
    own_on_all = [r for r in recs if r["g"] == "own" and r["online"]]
    late = [r for r in own_on_all if r["t"] >= 4284]
    J["outletTotal"] = {}
    for co in COHORTS + ("全部",):
        base = [r for r in own_on_all if co == "全部" or r["cohort"] == co]
        if not base:
            continue
        for cn, sel_t in (("4284 拍以前", lambda r: r["t"] < 4284), ("4284 拍以后", lambda r: r["t"] >= 4284)):
            for mn, sel_m in (("有我方号", lambda r: r["matesOwn"] > 0), ("没有我方号、有别的真人", lambda r: r["matesOwn"] == 0 and r["matesAny"] > 0),
                              ("一个都没有（含自由混战）", lambda r: r["matesAny"] == 0)):
                rs = [r for r in base if sel_t(r) and sel_m(r)]
                b = sum(r["bal"] for r in rs)
                P(f"  {co} | {cn} | {mn} | {len(rs)} | {b} | {sum(1 for r in rs if r['bal'] >= 100000)} | {sum(r['terr'] for r in rs)}")
                J["outlet"].append(dict(cohort=co, period=cn, mates=mn, n=len(rs), bal=b, ge100k=sum(1 for r in rs if r["bal"] >= 100000)))
        lt = [r for r in base if r["t"] >= 4284]
        tb, lb2 = sum(r["bal"] for r in base), sum(r["bal"] for r in lt)
        P(f"  {co} 合计 {len(base)} 个号、{tb} 兵；其中 4284 拍以后出局的 {len(lt)} 个号（{pct(len(lt), len(base))}）、{lb2} 兵（{pct(lb2, tb)}）")
        J["outletTotal"][co] = dict(n=len(base), bal=tb, lateN=len(lt), lateBal=lb2)
    P()
    P("[DB-I] 按编队档分开（在线时出局的席位；本编队和同一批局里的野人并排）")
    P("  档 | 组 | 局 | 有过地的席位 | 在线时出局 | 被吃光 | 地还在就被除名 | 除名前 地÷峰值 中位 | 账上的兵合计 | 中位 | ≥10 万的号 | 密度中位 | 账上的兵 ÷ 压在它身上的兵 中位")
    J["cohort"] = {}
    table = []
    seats_by = Counter()
    for m in per_match:
        seats_by[(m["cohort"], "own")] += m["own"]
        seats_by[(m["cohort"], "wild")] += m["wildSeats"]
    for co in COHORTS:
        n_m = sum(1 for m in per_match if m["cohort"] == co)
        if not n_m:
            continue
        for g in ("own", "wild"):
            rs = [r for r in recs if r["cohort"] == co and r["g"] == g and r["online"]]
            n_seats = seats_by[(co, g)]
            line = [r for r in rs if r["terr"] > 0]
            ratio = [r["terr"] / r["peak"] for r in line if r["peak"] > 0]
            bals = [r["bal"] for r in rs]
            dens = [r["bal"] / r["terr"] for r in rs if r["terr"] > 0]
            rel = [r["bal"] / r["press"] for r in rs if r["press"] > 0]
            k = sum(1 for b in bals if b >= 100000)
            cells = [f"{len(rs)}（{pct(len(rs), n_seats)}）", str(len(rs) - len(line)), str(len(line)), fq(ratio, (0.5,), 3), str(sum(bals)), str(q(bals, 0.5)) if bals else "–",
                     f"{k}（{pct(k, len(rs))}）", fq(dens, (0.5,), 1), fq(rel, (0.5,), 2)]
            P(f"  {co} | {GROUP_CN[g]} | {n_m} | {n_seats} | " + " | ".join(cells))
            J["cohort"][f"{co}|{g}"] = dict(matches=n_m, seats=n_seats, n=len(rs), line=len(line), bal=sum(bals), median=q(bals, 0.5) if bals else None, ge100k=k)
            table.append(f"| {co} | {'本编队' if g == 'own' else '野人'} | {cells[0]} | {cells[1]} | {cells[2]} | {cells[3]} | {cells[5]} | {cells[6]} | {cells[7]} | {cells[8]} |")
    P()
    P("[DB-F] 和日志口径对账（xscan [XS-B]：123 局里 905 个阵亡号、出局时账上合计 148529470 兵、≥10 万的 373 个）")
    own_on = [r for r in recs if r["g"] == "own" and r["online"]]
    own_sh = [r for r in recs if r["g"] == "own" and not r["online"]]
    P(f"  这里是 {len(per_match)} 局（有录像、有地图、重演对得上的局；和引擎对不上以后的不算）：我方在线时出局 {len(own_on)} 个号、账上合计 {sum(r['bal'] for r in own_on)} 兵、≥10 万的 {sum(1 for r in own_on if r['bal'] >= 100000)} 个；"
      f"另有离开以后（空壳）才出局的 {len(own_sh)} 个号、出局时账上 {sum(r['bal'] for r in own_sh)} 兵（这部分日志口径看不到）")
    P()
    P("[DB-G] 逐局：局 | 档 | 真人 | 算到哪一拍（录像取自别的包 / 和引擎对不上而截短的另注）| 主队赢 | 有过地的我方号 | 在线时出局 | 其中地还在就被除名 | 账上的兵合计 | ≥10 万的号 | 野人在线时出局 / 账上的兵合计")
    for m in sorted(per_match, key=lambda m: m["mid"]):
        note = (f"（录像取自 {m['rec']}）" if m["rec"] != m["mid"] else "") + ("（截短）" if m["cut"] is not None else "")
        P(f"  {m['mid']} | {m['cohort']} | {m['H']} | {m['end']}{note} | {'赢' if m['won'] else '–'} | {m['own']} | {m.get('ownDead', 0)} | {m.get('ownLine', 0)} | {m.get('ownBal', 0)} | {m.get('own100k', 0)} | {m.get('wildDead', 0)} / {m.get('wildBal', 0)}")
    J["perMatch"] = per_match

    # 会审稿用的填空（council_fill.py 读）：每一项都和上面打印出来的写法一模一样
    n10 = sum(1 for m in per_match if m["cohort"] == "squad10")
    n20 = sum(1 for m in per_match if m["cohort"] == "squad20")
    tot_bal = sum(r["bal"] for r in own_on_all)
    o = {(d["cohort"], d["period"], d["mates"]): d for d in J["outlet"]}
    la, lb_, lc = o[("全部", "4284 拍以后", "有我方号")], o[("全部", "4284 拍以后", "没有我方号、有别的真人")], o[("全部", "4284 拍以后", "一个都没有（含自由混战）")]
    # 能整局重演的局单（fidlist.py 从 xtruth.json 生成；fid_batch.sh 照它分批跑）+ 靠同房另一份录像才有对局段的局（roompairs.py）
    try:
        want = [r[0] for r in json.load(open(os.path.join(OUT, "_run", "fidabl_list.json"), encoding="utf-8"))]
    except Exception:
        want = None
    try:
        extra = [r[0] for r in json.load(open(os.path.join(OUT, "_run", "fid_extra.json"), encoding="utf-8"))]
    except Exception:
        extra = []
    have = {m["mid"] for m in per_match}
    have_extra = [x for x in extra if x in have]
    cut_txt = "；".join(f"{rec} 从 {c[0]} 拍起" + (f"（{' '.join(x for x in c[2] if x != rec)} 用的是同一份录像）" if any(x != rec for x in c[2]) else "") for rec, c in sorted(cuts.items()))
    if want is None:
        cover = f"{len(per_match)} 局：squad10 {n10} 局、squad20 {n20} 局"
    else:
        miss = [x for x in want + extra if x not in have]
        cover = (f"能整局重演的 {len(want)} 局" + ("全部跑完" if not [x for x in want if x not in have] else f"里跑完了 {len([x for x in want if x in have])} 局")
                 + (f"，另加 {len(have_extra)} 局自己的录像只有出生期、用同房另一份包的录像重演的（{' '.join(have_extra)}）" if have_extra else "")
                 + f"，合计 {len(per_match)} 局、{n_rooms} 个物理房间：squad10 {n10} 局、squad20 {n20} 局"
                 + (f"；还没跑完的 {len(miss)} 局在后台排队（{' '.join(miss)}）" if miss else ""))
    cover += (f"。用同房另一份包更长的录像重演的 {len(borrowed)} 局（" + "；".join(f"{m['mid']} ← {m['rec']}" for m in borrowed) + "）" if borrowed else "")
    cover += (f"。模拟器的重演中途和真引擎对不上的录像 {len(cuts)} 份，对不上以后的出局不算（{cut_txt}）" if cuts else "")
    lines.insert(1, f"  覆盖：{cover}")
    J["report"] = {
        "DB_N": str(len(per_match)), "DB_N10": str(n10), "DB_N20": str(n20), "DB_COVER": cover,
        "DB_TABLE": "\n".join(table),
        "DB_OWN_DEAD": str(len(own_on_all)), "DB_OWN_BAL": str(tot_bal),
        "DB_OWN_MED": str(J["bank"]["own"]["median"]), "DB_OWN_100K": f"{J['bank']['own']['ge100k']}（{pct(J['bank']['own']['ge100k'], J['bank']['own']['n'])}）",
        "DB_WILD_DEAD": str(J["bank"]["wild"]["n"]), "DB_WILD_MED": str(J["bank"]["wild"]["median"]),
        "DB_WILD_100K": f"{J['bank']['wild']['ge100k']}（{pct(J['bank']['wild']['ge100k'], J['bank']['wild']['n'])}）",
        "DB_LATE_N": str(len(late)), "DB_LATE_NPCT": pct(len(late), len(own_on_all)),
        "DB_LATE_BAL": str(sum(r["bal"] for r in late)), "DB_LATE_BALPCT": pct(sum(r["bal"] for r in late), tot_bal),
        "DB_LATE_OWN_N": str(la["n"]), "DB_LATE_OWN_BAL": str(la["bal"]), "DB_LATE_OWN_100K": str(la["ge100k"]),
        "DB_LATE_ANY_N": str(lb_["n"]), "DB_LATE_ANY_BAL": str(lb_["bal"]),
        "DB_LATE_NONE_N": str(lc["n"]), "DB_LATE_NONE_BAL": str(lc["bal"]),
        "DB_SHELL_N": str(len(own_sh)), "DB_SHELL_BAL": str(sum(r["bal"] for r in own_sh)),
        "DB_ROOMS": str(n_rooms), "DB_CUT_ROWS": str(sum(c[1] for c in cuts.values())),
        "DB_WIN_M": str(J["split"].get("主队赢的局", {}).get("matches", 0)), "DB_WIN_SEATS": str(J["split"].get("主队赢的局", {}).get("own", 0)),
        "DB_WIN_DEAD": str(J["split"].get("主队赢的局", {}).get("dead", 0)),
        "DB_LOSE_M": str(J["split"].get("主队没赢的局", {}).get("matches", 0)), "DB_LOSE_SEATS": str(J["split"].get("主队没赢的局", {}).get("own", 0)),
        "DB_LOSE_DEAD": str(J["split"].get("主队没赢的局", {}).get("dead", 0)),
    }

    # 按档 × 时段 × 同队还有谁：DB_<S10|S20>_<PRE|LATE>_<OWN|ANY|NONE>_<N|BAL|100K>，以及每档的合计
    for co, ck in (("squad10", "S10"), ("squad20", "S20")):
        tot = J["outletTotal"].get(co)
        if not tot:
            continue
        J["report"].update({f"DB_{ck}_DEAD": str(tot["n"]), f"DB_{ck}_BAL": str(tot["bal"]), f"DB_{ck}_LATE_N": str(tot["lateN"]), f"DB_{ck}_LATE_NPCT": pct(tot["lateN"], tot["n"]),
                            f"DB_{ck}_LATE_BAL": str(tot["lateBal"]), f"DB_{ck}_LATE_BALPCT": pct(tot["lateBal"], tot["bal"])})
        for cn, pk in (("4284 拍以前", "PRE"), ("4284 拍以后", "LATE")):
            for mn, mk in (("有我方号", "OWN"), ("没有我方号、有别的真人", "ANY"), ("一个都没有（含自由混战）", "NONE")):
                d = o[(co, cn, mn)]
                J["report"].update({f"DB_{ck}_{pk}_{mk}_N": str(d["n"]), f"DB_{ck}_{pk}_{mk}_BAL": str(d["bal"]), f"DB_{ck}_{pk}_{mk}_100K": str(d["ge100k"])})
        c_own, c_wild = J["cohort"].get(f"{co}|own"), J["cohort"].get(f"{co}|wild")
        if c_own and c_wild:
            J["report"].update({f"DB_{ck}_SEATS": str(c_own["seats"]), f"DB_{ck}_DEADPCT": pct(c_own["n"], c_own["seats"]), f"DB_{ck}_MED": str(c_own["median"]),
                                f"DB_{ck}_100K": f"{c_own['ge100k']}（{pct(c_own['ge100k'], c_own['n'])}）",
                                f"DB_{ck}_WILD_DEAD": str(c_wild["n"]), f"DB_{ck}_WILD_MED": str(c_wild["median"]),
                                f"DB_{ck}_WILD_100K": f"{c_wild['ge100k']}（{pct(c_wild['ge100k'], c_wild['n'])}）"})

    os.makedirs(os.path.join(OUT, "_cross"), exist_ok=True)
    open(os.path.join(OUT, "_cross", "deathbank.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    json.dump(J, open(os.path.join(OUT, "_cross", "deathbank.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if not quiet:
        print("\n".join(lines))


if __name__ == "__main__":
    main()
