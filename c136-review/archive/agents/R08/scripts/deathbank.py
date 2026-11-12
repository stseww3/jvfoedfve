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

OUT = os.path.join(os.path.dirname(HERE), "out")
RUN = os.path.join(OUT, "_run", "deathbank")
PERIODS = [("0~600", 0, 600), ("600~1500", 600, 1500), ("1500~3000", 1500, 3000), ("3000~4284", 3000, 4284), ("4284+", 4284, 10 ** 9)]
GROUPS = ["own", "wild", "apex", "pool"]
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
    for fp in files:
        R = json.load(open(fp, encoding="utf-8"))
        mid = R["matchId"]
        card = cards.get(mid)
        if card is None:
            continue
        cohort = card.get("cohort")
        H = R["H"]
        names = [str(x).strip() for x in R["names"]]
        low = [x.lower() for x in names]
        left = R["leftT"]
        own_set = set(i for i in R["squad"].values() if i >= 0) | facts_own(mid, H, low)
        if not own_set:
            continue

        def grp(s):
            if s in own_set:
                return "own"
            if "[apex]" in low[s]:
                return "apex"
            if low[s] in pool:
                return "pool"
            return "wild"

        played = [s for s in range(H) if R["seats"][s][0] > 0]          # 整局有过地的席位
        for s in played:
            seats_n[grp(s)] += 1
        seen = set()
        won = bool(XT.get(mid, {}).get("won"))
        m = dict(mid=mid, cohort=cohort, H=H, end=R["endTick"], won=won, own=len([s for s in played if s in own_set]), rows=0)
        mc = Counter()
        for t, p, kind, terr, bal, peak, state, out, n_atk, press, top, boats in R["deaths"]:
            if p in seen or p >= H:
                continue
            if kind == "eliminate" and terr == 0 and peak == 0 and bal == 0:
                continue                                                  # 清场以后的空除名
            seen.add(p)
            g = grp(p)
            online = state != 2
            r = dict(mid=mid, cohort=cohort, won=won, t=t, p=p, g=g, online=online, kind=kind, terr=terr, bal=bal, peak=peak, out=out, nAtk=n_atk, press=press, boats=boats)
            recs.append(r)
            m["rows"] += 1
            if online:
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

    J = {"matches": len(per_match), "rows": len(recs)}
    P(f"deathbank.py — 四分之一峰值线出局时账上的兵（真相口径）：{len(per_match)} 局（squad10 {sum(1 for m in per_match if m['cohort'] == 'squad10')} / squad20 {sum(1 for m in per_match if m['cohort'] == 'squad20')}），整局重演")
    P()
    P("[DB-A] 覆盖")
    P("  整局有过地的真人席位：" + "；".join(f"{GROUP_CN[g]} {seats_n[g]}" for g in GROUPS) + f"；出局记录 {len(recs)} 行")
    P("  其中在线时出局的：" + "；".join(f"{GROUP_CN[g]} {seats_dead_online[g]}（{pct(seats_dead_online[g], seats_n[g])}）" for g in GROUPS))
    J["seats"] = dict(seats_n)
    J["deadOnline"] = dict(seats_dead_online)
    P()
    P("[DB-B] 出局的方式")
    P("  组 | 在线 / 空壳 | 出局 | 被吃光（地 = 0）| 地还在就被除名（四分之一线）| 陆上清场但海上有船 | 地还在的：出局前 地÷峰值 的 10% / 25% / 50% / 75% / 90% 分位 | 其中 地÷峰值 > 0.25 的")
    J["mode"] = {}
    for g in GROUPS:
        for online in (True, False):
            rs = [r for r in recs if r["g"] == g and r["online"] == online]
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
        rs = [r for r in recs if r["g"] == g and r["online"]]
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
        rs = [r for r in recs if r["g"] == g and r["online"] and r["terr"] > 0]
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
            rs = [r for r in recs if r["g"] == g and r["online"] and period_of(r["t"]) == i]
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
    P("[DB-F] 和日志口径对账（xscan [XS-B]：123 局里 905 个阵亡号、出局时账上合计 148529470 兵、≥10 万的 373 个）")
    own_on = [r for r in recs if r["g"] == "own" and r["online"]]
    own_sh = [r for r in recs if r["g"] == "own" and not r["online"]]
    P(f"  这里是 {len(per_match)} 局（有录像、有地图、重演对得上的局）：我方在线时出局 {len(own_on)} 个号、账上合计 {sum(r['bal'] for r in own_on)} 兵、≥10 万的 {sum(1 for r in own_on if r['bal'] >= 100000)} 个；"
      f"另有离开以后（空壳）才出局的 {len(own_sh)} 个号、出局时账上 {sum(r['bal'] for r in own_sh)} 兵（这部分日志口径看不到）")
    P()
    P("[DB-G] 逐局：局 | 档 | 真人 | 录像拍 | 主队赢 | 有过地的我方号 | 在线时出局 | 其中地还在就被除名 | 账上的兵合计 | ≥10 万的号 | 野人在线时出局 / 账上的兵合计")
    for m in sorted(per_match, key=lambda m: m["mid"]):
        P(f"  {m['mid']} | {m['cohort']} | {m['H']} | {m['end']} | {'赢' if m['won'] else '–'} | {m['own']} | {m.get('ownDead', 0)} | {m.get('ownLine', 0)} | {m.get('ownBal', 0)} | {m.get('own100k', 0)} | {m.get('wildDead', 0)} / {m.get('wildBal', 0)}")
    J["perMatch"] = per_match

    os.makedirs(os.path.join(OUT, "_cross"), exist_ok=True)
    open(os.path.join(OUT, "_cross", "deathbank.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    json.dump(J, open(os.path.join(OUT, "_cross", "deathbank.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if not quiet:
        print("\n".join(lines))


if __name__ == "__main__":
    main()
