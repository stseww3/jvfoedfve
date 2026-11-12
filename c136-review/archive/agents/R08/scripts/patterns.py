#!/usr/bin/env python3
"""patterns.py — 模式的机械计数：按 reviews_src/patterns_catalog.py 里写明的定义，只用日志口径（facts.json + in_game.log）逐局数。

每个检出函数对应目录里 detect 写着「scripts/patterns.py: <函数名>」的一个模式；另外把几个只看日志就能数的模式
（NEW-EG-G2、NEW-MT-07、NEW-DF-07、NEW-EC-09、NEW-DN-07、NEW-DN-17）一并数出来。
需要录像的模式（NEW-IO-*、NEW-SP-04/05、NEW-EC-05 …）不在这里数，见 crossmatch.py 汇总各局的硬账。

用法：
    python3 patterns.py <局> [--room N] [--quiet]        → out/<局>/patterns.txt、patterns_sum.json
    python3 patterns.py --all 局1 局2 …                  → 逐局跑，再写 out/_cross/patterns_matrix.txt / .json
口径说明：一行 = 一次命中（号 + 起止拍 + 关键读数）；「兑现」= 定义里写的后续后果也发生了。
"""
import json
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "reviews_src"))
import facts  # noqa: E402
import r08lib as L  # noqa: E402
import patterns_catalog as PC  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")
BIG = 10 ** 9


class M:
    """一局的日志事实。"""

    def __init__(self, mid, room=None, F=None):
        """F：已经在内存里的 facts.full(mid)（xscan.py 跨局扫描用，不落盘）；不给就读 out/<局>/facts[_room<N>].json。"""
        self.mid = mid
        if F is None:
            suf = "" if room in (None, 0) else f"_room{room}"
            p = os.path.join(OUT, mid, f"facts{suf}.json")
            if not os.path.exists(p):
                p = os.path.join(OUT, mid, "facts.json")
            F = json.load(open(p, encoding="utf-8"))
        self.F = F
        self.card = F["card"]
        self.land = self.card["mapLand"]
        self.bots = {int(k): b for k, b in F["bots"].items() if b.get("ticks")}
        self.dons = F.get("dons") or []
        self.drop30 = F.get("drop30") or []
        self.ochk = F.get("ochk") or []
        self.end = self.card["outcome"].get("endTick") or 0

    def name(self, me):
        return self.bots[me]["name"]

    def death(self, b):
        return b["deathTick"] if b.get("event") == "died" and b.get("deathTick") is not None else None

    def after(self, b, t, span):
        return [s for s in b["ticks"] if t < s["t"] <= t + span]

    def collapsed(self, b, t, terr_ref, span=450, frac=0.7):
        """t 之后 span 拍内领土跌到 terr_ref 的 frac 以下，或者阵亡。"""
        d = self.death(b)
        if d is not None and t < d <= t + span:
            return True
        return any(s["terr"] <= frac * terr_ref for s in self.after(b, t, span))


def runs(tk, pred):
    """连续满足 pred(s) 的快照段：[(i0, i1)]（闭区间下标）。"""
    out, i0 = [], None
    for i, s in enumerate(tk):
        if pred(s):
            if i0 is None:
                i0 = i
        else:
            if i0 is not None:
                out.append((i0, i - 1))
            i0 = None
    if i0 is not None:
        out.append((i0, len(tk) - 1))
    return out


# ---------------------------------------------------------------- 出生 / 开局

def sp_fallback(m):
    it = [dict(bot=b["name"], minAllyDist=b["spawnInfo"].get("minAllyDist")) for b in m.bots.values()
          if b.get("spawnInfo") and b["spawnInfo"].get("voronoi") == 500]
    return dict(hit=len(it) >= 2, n=len(it), items=it)


def sp_cluster(m):
    near = [b for b in m.bots.values() if b.get("spawnInfo") and (b["spawnInfo"].get("minAllyDist") or BIG) <= 110]
    ok = len(near) >= 3 and any((b["spawnInfo"].get("voronoi") or BIG) < 3000 for b in near)
    it = [dict(bot=b["name"], minAllyDist=b["spawnInfo"]["minAllyDist"], voronoi=b["spawnInfo"].get("voronoi")) for b in near]
    return dict(hit=ok, n=len(it) if ok else 0, items=it if ok else [])


def sp_mixed_solutions(m):
    path = os.path.join(L.bundle_dir(m.mid), "in_game.log")
    last_coord, min_sep = None, None
    last_pt = {}
    with open(path, encoding="utf-8", errors="replace") as f:
        for ln in f:
            if "[BACKEND-SPAWN-COORD] Solved" in ln:
                mm = re.search(r"minSep=(\d+)px", ln)
                min_sep = int(mm.group(1)) if mm else None
                last_coord = {a.replace("[Nope] ", "").strip(): (int(x), int(y)) for a, x, y in re.findall(r"([^|:]+?)\([A-Z_]+\)->\((\d+),(\d+)\)", ln.split("):", 1)[-1])}
            elif "[HL-SPAWN-BACKEND]" in ln:
                mm = re.search(r"\t\[([^\]]+)\] \[HL-SPAWN-BACKEND\] me=(\d+) .*?-> \((\d+),(\d+)\)", ln)
                if mm:
                    last_pt[mm.group(1).replace("[Nope] ", "")] = (int(mm.group(3)), int(mm.group(4)))
    if not last_coord:
        return dict(hit=False, n=0, items=[], note="日志里没有 BACKEND-SPAWN-COORD 行")
    it = []
    for b in m.bots.values():
        for lab in b["labels"]:
            if lab in last_pt and lab in last_coord:
                d = ((last_pt[lab][0] - last_coord[lab][0]) ** 2 + (last_pt[lab][1] - last_coord[lab][1]) ** 2) ** 0.5
                if d > 4:
                    it.append(dict(bot=b["name"], got=last_pt[lab], lastSolve=last_coord[lab], dist=round(d)))
                break
    pts = [(b["name"], last_pt[lab]) for b in m.bots.values() for lab in b["labels"][:1] if lab in last_pt]
    close = [(a[0], c[0], round(((a[1][0] - c[1][0]) ** 2 + (a[1][1] - c[1][1]) ** 2) ** 0.5)) for i, a in enumerate(pts) for c in pts[i + 1:]
             if min_sep and ((a[1][0] - c[1][0]) ** 2 + (a[1][1] - c[1][1]) ** 2) ** 0.5 < min_sep / 2]
    return dict(hit=bool(it), n=len(it), items=it, realized=len(close), closePairs=close, minSep=min_sep)


def op_boxed_early(m):
    it = []
    for b in m.bots.values():
        s = next((s for s in b["ticks"] if s["t"] < 900 and s["nb"] == 0 and s["neut"] == 0 and s["terr"] < 2500), None)
        if s:
            it.append(dict(bot=b["name"], t=s["t"], terr=s["terr"], line=s["line"]))
    return dict(hit=bool(it), n=len(it), items=it)


def op_crumb_lock(m):
    it = []
    for b in m.bots.values():
        tk = b["ticks"]
        for i0, i1 in runs(tk, lambda s: s["nb"] == 0 and 1 <= s["neut"] <= 8):
            # 在这一段里找领土变化 <2% 的最长子段
            j0 = i0
            while j0 <= i1:
                base = tk[j0]["terr"]
                j1 = j0
                while j1 + 1 <= i1 and abs(tk[j1 + 1]["terr"] - base) < 0.02 * max(base, 1):
                    j1 += 1
                if j1 - j0 + 1 >= 6:
                    it.append(dict(bot=b["name"], t0=tk[j0]["t"], t1=tk[j1]["t"], ticks=tk[j1]["t"] - tk[j0]["t"], terr=base,
                                   bal0=tk[j0]["bal"], bal1=tk[j1]["bal"], dCmds=tk[j1]["cmds"] - tk[j0]["cmds"], dBoats=tk[j1]["boats"] - tk[j0]["boats"]))
                j0 = j1 + 1
    return dict(hit=bool(it), n=len(it), items=it, ticks=sum(x["ticks"] for x in it))


def op_boat_breakout(m):
    it = []
    for b in m.bots.values():
        for s in b["ticks"]:
            if s["t"] < 1500 and s["nb"] == 0 and s["neut"] == 0 and s["terr"] < 3000:
                boat = any(x["boats"] > s["boats"] for x in m.after(b, s["t"], 180))
                grow = max((x["terr"] for x in m.after(b, s["t"], 450)), default=0)
                if boat and grow >= 1.5 * s["terr"]:
                    it.append(dict(bot=b["name"], t=s["t"], terr=s["terr"], terrAfter=grow))
                    break
    return dict(hit=bool(it), n=len(it), items=it)


def op_on_schedule(m):
    vals = []
    for b in m.bots.values():
        s = [x for x in b["ticks"] if x["t"] <= 630]
        if s:
            vals.append(s[-1]["terr"])
    avg = sum(vals) / len(vals) if vals else 0
    bad = [i["name"] for oc in m.ochk for i in oc["items"] if i["ok"] != "OK"]
    ok = bool(vals) and avg >= 2500 and not bad
    return dict(hit=ok, n=len(vals) if ok else 0, items=[], avgTerrAt630=round(avg), openingCheckBad=bad)


# ---------------------------------------------------------------- 经济

def ec_thin_big(m):
    it = []
    for b in m.bots.values():
        s = next((s for s in b["ticks"] if 1440 <= s["t"] <= 1710 and s["terr"] >= 8000 and s["dens"] < 5), None)
        if s:
            it.append(dict(bot=b["name"], t=s["t"], terr=s["terr"], dens=s["dens"], realized=m.collapsed(b, s["t"], s["terr"], 900)))
    return dict(hit=bool(it), n=len(it), items=it, realized=sum(1 for x in it if x["realized"]))


def ec_hoard_1nb(m):
    it = []
    for me, b in m.bots.items():
        tk = b["ticks"]
        for i0, i1 in runs(tk, lambda s: 1 <= s["nb"] <= 2 and s["neut"] == 0):
            j0 = i0
            while j0 <= i1:
                base = tk[j0]["terr"]
                j1 = j0
                while j1 + 1 <= i1 and abs(tk[j1 + 1]["terr"] - base) < 0.02 * max(base, 1) and tk[j1 + 1]["cmds"] - tk[j0]["cmds"] <= 2:
                    j1 += 1
                a, c = tk[j0], tk[j1]
                if j1 - j0 + 1 >= 8 and c["t"] - a["t"] >= 630 and a["dens"] > 0 and c["dens"] >= 2 * a["dens"]:
                    cost = []
                    for me2, b2 in m.bots.items():
                        if me2 == me or b2.get("team") != b.get("team") or b.get("team") is None:
                            continue
                        d2 = m.death(b2)
                        s0 = [x for x in b2["ticks"] if x["t"] <= a["t"]]
                        if d2 is not None and a["t"] < d2 <= c["t"]:
                            cost.append(b2["name"] + " 阵亡")
                        elif s0 and any(x["terr"] <= 0.5 * s0[-1]["terr"] for x in b2["ticks"] if a["t"] < x["t"] <= c["t"]):
                            cost.append(b2["name"] + " 腰斩")
                    it.append(dict(bot=b["name"], t0=a["t"], t1=c["t"], ticks=c["t"] - a["t"], terr=base, dens0=a["dens"], dens1=c["dens"], nb=a["nb"],
                                   dCmds=c["cmds"] - a["cmds"], cost=cost))
                j0 = j1 + 1
    return dict(hit=bool(it), n=len(it), items=it, realized=sum(1 for x in it if x["cost"]), ticks=sum(x["ticks"] for x in it))


def ec_over_softcap(m):
    it = []
    for b in m.bots.values():
        tk = b["ticks"]
        rr = [(i0, i1) for i0, i1 in runs(tk, lambda s: s["terr"] > 0 and s["bal"] > 100 * s["terr"]) if i1 - i0 + 1 >= 2]
        if rr:
            n = sum(i1 - i0 + 1 for i0, i1 in rr)
            it.append(dict(bot=b["name"], snapshots=n, firstT=tk[rr[0][0]]["t"], lastT=tk[rr[-1][1]]["t"],
                           hardCap=sum(1 for i0, i1 in rr for s in tk[i0:i1 + 1] if s["bal"] >= 149.5 * s["terr"])))
    return dict(hit=bool(it), n=len(it), items=it, snapshots=sum(x["snapshots"] for x in it), hardCapSnapshots=sum(x["hardCap"] for x in it))


def ec_hold_survive(m):
    it = []
    for b in m.bots.values():
        tk = [s for s in b["ticks"] if 1500 <= s["t"] <= 2400]
        ok = False
        for i0, i1 in runs(tk, lambda s: s["nb"] == 1):
            for j in range(i0, i1 - 3):
                if tk[j + 4]["cmds"] - tk[j]["cmds"] <= 2:
                    ok = (tk[j]["t"], tk[j + 4]["t"])
                    break
            if ok:
                break
        d = m.death(b)
        alive = (d is None and b["ticks"][-1]["t"] >= 3500) or (d is not None and d >= 3500)
        if ok and alive:
            it.append(dict(bot=b["name"], t0=ok[0], t1=ok[1], death=d))
    return dict(hit=bool(it), n=len(it), items=it)


def ec_team_standoff(m):
    """连续 ≥10 条快照（≥900 拍）里首尾都存活的号：合计领土 +≤5%、合计余额 ≥3 倍、合计指令 ≤ 号数×10。取互不重叠的最长窗。"""
    ts = sorted({s["t"] for b in m.bots.values() for s in b["ticks"]})
    snap = {me: {s["t"]: s for s in b["ticks"]} for me, b in m.bots.items()}
    best = []
    for ia, ta in enumerate(ts):
        cand = None
        for tb in ts[ia + 1:]:
            if tb - ta < 900:
                continue
            both = [me for me in m.bots if ta in snap[me] and tb in snap[me] and snap[me][ta]["terr"] > 0 and snap[me][tb]["terr"] > 0]
            if len(both) < 2:
                continue
            l0 = sum(snap[me][ta]["terr"] for me in both)
            l1 = sum(snap[me][tb]["terr"] for me in both)
            b0 = sum(snap[me][ta]["bal"] for me in both)
            b1 = sum(snap[me][tb]["bal"] for me in both)
            dc = sum(snap[me][tb]["cmds"] - snap[me][ta]["cmds"] for me in both)
            if l1 <= 1.05 * l0 and b0 > 0 and b1 >= 3 * b0 and dc <= 10 * len(both):
                cand = dict(t0=ta, t1=tb, ticks=tb - ta, bots=len(both), terr0=l0, terr1=l1, bal0=b0, bal1=b1, mult=round(b1 / b0, 2), cmds=dc)
        if cand:
            best.append(cand)
    best.sort(key=lambda x: -x["ticks"])
    chosen = []
    for c in best:
        if all(c["t1"] <= o["t0"] or c["t0"] >= o["t1"] for o in chosen):
            chosen.append(c)
    for c in chosen:
        lost = []
        for me, b in m.bots.items():
            d = m.death(b)
            s0 = snap[me].get(c["t0"])
            if d is not None and c["t0"] < d <= c["t1"]:
                lost.append(b["name"] + " 阵亡")
            elif s0 and s0["terr"] > 0 and any(x["terr"] <= 0.5 * s0["terr"] for x in b["ticks"] if c["t0"] < x["t"] <= c["t1"]):
                lost.append(b["name"] + " 腰斩")
        c["lost"] = lost
    chosen.sort(key=lambda x: x["t0"])
    return dict(hit=bool(chosen), n=len(chosen), items=chosen, ticks=sum(c["ticks"] for c in chosen), realized=sum(1 for c in chosen if c["lost"]))


def ec_hardcap_idle(m):
    """NEW-EC-09：顶硬上限（余额 ≥149.5×领土）且有敌邻、指令数不变的快照窗。"""
    it = []
    for b in m.bots.values():
        tk = b["ticks"]
        n = 0
        t0 = t1 = None
        for i in range(1, len(tk)):
            a, c = tk[i - 1], tk[i]
            if a["terr"] > 0 and a["bal"] >= 149.5 * a["terr"] and c["bal"] >= 149.5 * c["terr"] and a["nb"] >= 1 and c["cmds"] == a["cmds"]:
                n += 1
                t0 = a["t"] if t0 is None else t0
                t1 = c["t"]
        if n:
            it.append(dict(bot=b["name"], windows=n, firstT=t0, lastT=t1))
    return dict(hit=bool(it), n=len(it), items=it, windows=sum(x["windows"] for x in it))


# ---------------------------------------------------------------- 捐款

def dn_threshold_unreachable(m):
    it = []
    for me, b in m.bots.items():
        d = m.death(b)
        if d is None:
            continue
        tk = b["ticks"]
        pk = max(tk, key=lambda s: s["terr"])
        ss = [s for s in facts.segments(b) if s["cls"] == "S" and s["t0"] >= pk["t"]]
        t_start = ss[0]["t0"] if ss else pk["t"]
        mates = []
        for me2, b2 in m.bots.items():
            if me2 == me or b2.get("team") != b.get("team") or b.get("team") is None:
                continue
            s2 = next((s for s in b2["ticks"] if s["t"] == t_start), None)
            if s2 and s2["terr"] >= 100:
                mates.append((b2["name"], s2["dens"]))
        got = [x for x in m.dons if x.get("ally") == me and t_start <= x["t"] <= d and x.get("accepted")]
        if mates and not any(dn >= 106 for _, dn in mates) and not got:
            it.append(dict(bot=b["name"], tStart=t_start, death=d, mates=len(mates), maxMateDens=max(dn for _, dn in mates)))
    return dict(hit=bool(it), n=len(it), items=it)


def dn_no_channel_early(m):
    ts = sorted({s["t"] for b in m.bots.values() for s in b["ticks"] if s["t"] < 1500})
    it = []
    for t in ts:
        rows = [(b, s) for b in m.bots.values() for s in b["ticks"] if s["t"] == t and s["terr"] > 0]
        for b, s in rows:
            if s["bal"] > 100 * s["terr"]:
                poor = [b2["name"] for b2, s2 in rows if b2 is not b and b2.get("team") == b.get("team") and b.get("team") is not None and s2["dens"] < 1]
                if poor:
                    it.append(dict(t=t, rich=b["name"], poor=poor))
    return dict(hit=bool(it), n=len({x["t"] for x in it}), items=it)


def dn_tax_gt_gift(m):
    it = [dict(t=d["t"], donor=m.bots[d["donor"]]["name"] if d["donor"] in m.bots else d["donor"], ally=d.get("allyName"), pct=d["pct"], myBal=d["myBal"],
               loss=round(d["myBal"] * (64 - (d["pct"] + 1)) / 1024), accepted=bool(d.get("accepted")), line=d["line"])
          for d in m.dons if d.get("pct") is not None and d["pct"] < 63]
    return dict(hit=bool(it), n=len(it), items=it, taxMinusGift=sum(x["loss"] for x in it), accepted=sum(1 for x in it if x["accepted"]))


def dn_pingpong(m):
    """NEW-DN-07：两个号在 600 拍内互相捐款（日志 HL-DONATE，成交的）。"""
    acc = [d for d in m.dons if d.get("accepted") and d.get("ally") in m.bots and d["donor"] in m.bots]
    it = []
    seen = set()
    for d in acc:
        for e in acc:
            if e["donor"] == d["ally"] and e["ally"] == d["donor"] and 0 < e["t"] - d["t"] <= 600:
                key = (d["line"], e["line"])
                if key in seen:
                    continue
                seen.add(key)
                it.append(dict(a=m.name(d["donor"]), b=m.name(d["ally"]), t0=d["t"], t1=e["t"], gap=e["t"] - d["t"]))
                break
    pairs = {tuple(sorted((x["a"], x["b"]))) for x in it}
    return dict(hit=bool(it), n=len(it), items=it, pairs=len(pairs))


def dn_rescue_bounce(m):
    """NEW-DN-17：A 对 B 发 rescue 之后 ≤60 拍，B 发 surplus 且 dMe ≥140。"""
    it = []
    for d in m.dons:
        if "rescue" not in (d.get("kind") or ""):
            continue
        for e in m.dons:
            if e["donor"] == d.get("ally") and "surplus" in (e.get("kind") or "") and 0 < e["t"] - d["t"] <= 60 and (e.get("dMe") or 0) >= 140:
                bb = m.bots.get(e["donor"])
                it.append(dict(a=m.bots[d["donor"]]["name"] if d["donor"] in m.bots else d["donor"], b=bb["name"] if bb else e["donor"], tRescue=d["t"], tBack=e["t"],
                               rescueTax=round(d["myBal"] * 64 / 1024), backTax=round(e["myBal"] * 64 / 1024), backTo=e.get("allyName"),
                               bDeath=m.death(bb) if bb else None, lines=[d["line"], e["line"]]))
                break
    return dict(hit=bool(it), n=len(it), items=it)


# ---------------------------------------------------------------- 进攻

def _price2(d):
    return d["perPx2"] if (d.get("dterr2") is not None and d["dterr2"] > 0 and d.get("perPx2") is not None) else d.get("perPx")


def at_overcap_dump(m):
    it = []
    for d in m.drop30:
        b = m.bots.get(int(d["me"]))
        if not b or d["dterr"] <= 0:
            continue
        pr = _price2(d)
        if pr is None or pr < 150:
            continue
        over = [s for s in b["ticks"] if 0 <= d["t0"] - s["t"] <= 180 and s["bal"] > 100 * s["terr"]]
        if over:
            it.append(dict(bot=b["name"], t0=d["t0"], t1=d["t1"], bal0=d["bal0"], bal1=d["bal1"], dterr=d["dterr"], perCell=round(pr), dens0=d["dens0"]))
    return dict(hit=bool(it), n=len(it), items=it)


def at_drained(m):
    it = []
    for d in m.drop30:
        b = m.bots.get(int(d["me"]))
        if not b or d["dterr"] <= 0:
            continue
        tk = b["ticks"]
        i = next((k for k, s in enumerate(tk) if s["t"] == d["t1"]), None)
        if i is None:
            continue
        dens1 = tk[i]["dens"]
        if dens1 > 0.5 * d["dens0"]:
            continue
        if i + 1 < len(tk) and tk[i + 1]["dens"] > 0.5 * d["dens0"] and tk[i + 1]["terr"] >= tk[i]["terr"] * 0.98:
            continue  # 下一段回流把密度拉回去了
        it.append(dict(bot=b["name"], t0=d["t0"], t1=d["t1"], dens0=d["dens0"], dens1=dens1, terr1=d["terr1"], realized=m.collapsed(b, d["t1"], d["terr1"], 450)))
    return dict(hit=bool(it), n=len(it), items=it, realized=sum(1 for x in it if x["realized"]))


def at_pricey_bite(m):
    it = []
    for d in m.drop30:
        b = m.bots.get(int(d["me"]))
        if not b or d["dterr"] <= 0:
            continue
        pr = _price2(d)
        if pr is not None and pr >= 90 and pr >= 3 * d["dens0"]:
            it.append(dict(bot=b["name"], t0=d["t0"], t1=d["t1"], perCell=round(pr), dens0=d["dens0"], dterr=d["dterr"], gone=round(d["gone"])))
    return dict(hit=bool(it), n=len(it), items=it)


def at_cheap_buy(m):
    it = []
    for d in m.drop30:
        b = m.bots.get(int(d["me"]))
        if not b:
            continue
        if d.get("px2") is not None and d["px2"] >= 500 and d.get("perPx2") is not None and d["perPx2"] <= 12:
            it.append(dict(bot=b["name"], t0=d["t0"], t1=d.get("t2") or d["t1"], cells=d["px2"], perCell=round(d["perPx2"], 1), dens0=d["dens0"]))
    return dict(hit=bool(it), n=len(it), items=it, cells=sum(x["cells"] for x in it))


def at_buffer_removed(m):
    it = []
    for b in m.bots.values():
        tk = b["ticks"]
        i = 0
        while i < len(tk):
            k = tk[i]["nb"]
            j = i
            while j + 1 < len(tk) and tk[j + 1]["nb"] == k:
                j += 1
            if k >= 1 and j - i + 1 >= 3:
                need = k + 1 if k == 1 else k + 2
                base = tk[j]
                nxt = [s for s in tk[j + 1:] if s["t"] - base["t"] <= 180]
                hit = next((s for s in nxt if s["terr"] >= 1.05 * base["terr"] and s["nb"] >= need), None)
                if hit:
                    later = [s for s in tk if hit["t"] <= s["t"] <= hit["t"] + 450]
                    peak = max(s["terr"] for s in later)
                    d = m.death(b)
                    real = any(s["terr"] <= 0.7 * peak for s in later) or (d is not None and hit["t"] < d <= hit["t"] + 450)
                    it.append(dict(bot=b["name"], t0=base["t"], t1=hit["t"], nb0=k, nb1=hit["nb"], terr0=base["terr"], terr1=hit["terr"], realized=real))
            i = j + 1
    return dict(hit=bool(it), n=len(it), items=it, realized=sum(1 for x in it if x["realized"]))


# ---------------------------------------------------------------- 防守 / 死因

def df_passive(m):
    """严格口径：一段连续的 Δcmds=0、Δboats=0 的窗里，领土相对段内某个起点掉 ≥30%。"""
    it = []
    for b in m.bots.values():
        tk = b["ticks"]
        i = 0
        while i < len(tk) - 1:
            j = i
            while j + 1 < len(tk) and tk[j + 1]["cmds"] == tk[i]["cmds"] and tk[j + 1]["boats"] == tk[i]["boats"]:
                j += 1
            if j > i:
                seg = tk[i:j + 1]
                pk = max(range(len(seg)), key=lambda q: (seg[q]["terr"], -q))
                lo = min(seg[pk:], key=lambda s: s["terr"])
                d = m.death(b)
                died_in = d is not None and j == len(tk) - 1
                end_terr = 0 if died_in else lo["terr"]
                if seg[pk]["terr"] >= 300 and end_terr <= 0.7 * seg[pk]["terr"]:
                    it.append(dict(bot=b["name"], t0=seg[pk]["t"], t1=d if died_in else lo["t"], terr0=seg[pk]["terr"], terr1=end_terr, bal0=seg[pk]["bal"],
                                   dens0=seg[pk]["dens"], nb0=seg[pk]["nb"], died=died_in))
            i = max(j, i + 1)
    return dict(hit=bool(it), n=len(it), items=it, bots=len({x["bot"] for x in it}), died=sum(1 for x in it if x["died"]),
                cellsLost=sum(x["terr0"] - x["terr1"] for x in it))


def df_passive_wide(m):
    """宽口径：领土从局部峰值掉 ≥30%（到阵亡或谷底），期间陆攻（cmds − boats − 捐款 − 戳刺）≤1。"""
    it = []
    for me, b in m.bots.items():
        tk = b["ticks"]
        d = m.death(b)
        i = 0
        while i < len(tk):
            # 局部峰值：之后一直不创新高
            j = i
            while j + 1 < len(tk) and tk[j + 1]["terr"] <= tk[i]["terr"]:
                j += 1
            if j > i:
                lo = min(range(i, j + 1), key=lambda q: (tk[q]["terr"], q))
                died_in = d is not None and j == len(tk) - 1
                end_i = j if died_in else lo
                end_terr = 0 if died_in else tk[lo]["terr"]
                if tk[i]["terr"] >= 300 and end_terr <= 0.7 * tk[i]["terr"] and end_i > i:
                    t0, t1 = tk[i]["t"], (d if died_in else tk[end_i]["t"])
                    dc = tk[end_i]["cmds"] - tk[i]["cmds"]
                    db = tk[end_i]["boats"] - tk[i]["boats"]
                    nd = sum(1 for x in m.dons if x["donor"] == me and t0 < x["t"] <= t1)
                    na = sum(1 for x in (b.get("assists") or []) if t0 < x["t"] <= t1)
                    land_atk = dc - db - nd - na
                    if land_atk <= 1:
                        it.append(dict(bot=b["name"], t0=t0, t1=t1, terr0=tk[i]["terr"], terr1=end_terr, cmds=dc, boats=db, donations=nd, assists=na,
                                       landAttacks=land_atk, died=died_in, dens0=tk[i]["dens"]))
                i = max(end_i, i + 1)
            else:
                i += 1
    return dict(hit=bool(it), n=len(it), items=it, bots=len({x["bot"] for x in it}), died=sum(1 for x in it if x["died"]),
                cellsLost=sum(x["terr0"] - x["terr1"] for x in it))


def df_full_death(m):
    """NEW-DF-07：满仓速死（fulldeath.py 的口径）。"""
    import fulldeath
    rows = fulldeath.analyse(m.mid, m.F)
    rows = [r for r in rows if r["bot"] in {b["name"] for b in m.bots.values()}]
    st = [r for r in rows if r["strict"]]
    wd = [r for r in rows if r["wide"]]
    return dict(hit=bool(st), n=len(st), items=[dict(bot=r["bot"], startT=r["startT"], terr=r["startTerr"], bal=r["startBal"], dens=r["startDens"],
                                                      ticksToDeath=r["ticksToDeath"], cmds=r["cmds"]) for r in st],
                wide=len(wd), deaths=len(rows), bal=sum(r["startBal"] for r in st), cmds=sum(r["cmds"] for r in st))


def df_quarter_bank(m):
    """NEW-DF-08：阵亡号的结果行里 balance ≥10 万、出局前最后的领土 ≤ 历史峰值的 30%（四分之一线出局，账上的兵清零）。"""
    it, all_bal, deaths = [], 0, 0
    for b in m.bots.values():
        if m.death(b) is None:
            continue
        deaths += 1
        bal = b.get("resBalance") or 0
        all_bal += bal
        pk = b.get("resPeak") or 0
        lt = b.get("lastTerritory") or 0
        if bal >= 100_000 and pk > 0 and lt <= 0.30 * pk:
            it.append(dict(bot=b["name"], t=m.death(b), peak=pk, lastTerr=lt, balance=bal, dens=round(bal / lt, 1) if lt else None))
    return dict(hit=bool(it), n=len(it), items=it, balance=sum(x["balance"] for x in it), deaths=deaths, allDeathsBalance=all_bal)


def boxed_runs(b, min_ticks=0):
    """连续 nb=0 且 neut=0（还有地）的快照段：[(首快照, 末快照)]，只留跨度 ≥ min_ticks 的。"""
    tk = b["ticks"]
    out = []
    for i0, i1 in runs(tk, lambda s: s["terr"] > 0 and s["nb"] == 0 and s["neut"] == 0):
        if tk[i1]["t"] - tk[i0]["t"] >= min_ticks:
            out.append((tk[i0], tk[i1]))
    return out


def mt_ffa_boxed(m):
    """NEW-MT-11：自由混战的房间（对局卡 mode = 7，结果行都不带队号），整局日志 0 笔捐款；
    命中 = 号有一段 ≥900 拍的被围（nb=0 且 neut=0）。兑现 = 这一段里非船指令 ≤2 条、余额至少翻倍。"""
    ffa = m.card.get("mode") == 7 and all(b.get("team") is None for b in m.bots.values())
    if not ffa:
        return dict(hit=False, n=0, items=[], ffa=False)
    it = []
    for b in m.bots.values():
        for a, z in boxed_runs(b, 900):
            nonboat = (z["cmds"] - a["cmds"]) - (z["boats"] - a["boats"])
            it.append(dict(bot=b["name"], t0=a["t"], t1=z["t"], ticks=z["t"] - a["t"], terr0=a["terr"], terr1=z["terr"], bal0=a["bal"], bal1=z["bal"],
                           nonBoat=nonboat, boats=z["boats"] - a["boats"], realized=nonboat <= 2 and z["bal"] >= 2 * max(a["bal"], 1)))
    return dict(hit=bool(it), n=len(it), items=it, realized=sum(1 for x in it if x["realized"]), ffa=True, donations=len(m.dons),
                ticks=sum(x["ticks"] for x in it))


def mt_boxed_long(m):
    """（NEW-MT-09 的日志侧影子，任何模式）一个号连续 ≥900 拍 nb=0 且 neut=0。兑现 = 这一段里非船指令 ≤2 条、余额至少翻倍。
    日志分不清围住它的是同队真人、异队编队友还是海——有录像的局用 enclose.py 的 A / B / C 类。"""
    it = []
    for me, b in m.bots.items():
        for a, z in boxed_runs(b, 900):
            nonboat = (z["cmds"] - a["cmds"]) - (z["boats"] - a["boats"])
            nd = sum(1 for x in m.dons if x["donor"] == me and a["t"] < x["t"] <= z["t"])
            it.append(dict(bot=b["name"], t0=a["t"], t1=z["t"], ticks=z["t"] - a["t"], terr0=a["terr"], bal0=a["bal"], bal1=z["bal"], densEnd=z["dens"],
                           nonBoat=nonboat, boats=z["boats"] - a["boats"], donations=nd,
                           realized=(nonboat - nd) <= 2 and z["bal"] >= 2 * max(a["bal"], 1)))
    return dict(hit=bool(it), n=len(it), items=it, realized=sum(1 for x in it if x["realized"]), bots=len({x["bot"] for x in it}),
                ticks=sum(x["ticks"] for x in it))


def mt_unseen_loss(m):
    """NEW-MT-06：看不见的失地——相邻两条快照（相隔 90 拍）都是 nb=0、neut=0，cmds 没变，领土却在掉。"""
    it = []
    for b in m.bots.values():
        tk = b["ticks"]
        wins = [(p["t"], s["t"], p["terr"] - s["terr"]) for p, s in zip(tk, tk[1:])
                if s["t"] - p["t"] == 90 and p["terr"] > 0 and p["nb"] == 0 and p["neut"] == 0 and s["nb"] == 0 and s["neut"] == 0
                and s["cmds"] == p["cmds"] and s["terr"] < p["terr"]]
        if wins:
            it.append(dict(bot=b["name"], windows=len(wins), cells=sum(w[2] for w in wins), firstT=wins[0][0], lastT=wins[-1][1]))
    return dict(hit=bool(it), n=sum(x["windows"] for x in it), items=it, bots=len(it), cells=sum(x["cells"] for x in it))


# ---------------------------------------------------------------- 海上 / 执行

def se_big_intercept(m):
    it = []
    for b in m.bots.values():
        ic = sorted(b.get("intercepts") or [], key=lambda x: x["t"])
        big = [x for x in ic if x["pct"] >= 200]
        many = any(sum(1 for y in ic if 0 <= y["t"] - x["t"] <= 900) >= 5 for x in ic)
        if big or many:
            it.append(dict(bot=b["name"], intercepts=len(ic), big=len(big), fiveIn900=many))
    return dict(hit=bool(it), n=len(it), items=it)


def ex_burst_drain(m):
    it = []
    for b in m.bots.values():
        tk = b["ticks"]
        for i in range(1, len(tk)):
            a, c = tk[i - 1], tk[i]
            if (c["cmds"] - a["cmds"]) - (c["boats"] - a["boats"]) >= 5 and a["dens"] >= 5 and a["bal"] > 0 and c["bal"] <= 0.4 * a["bal"] and c["terr"] >= 0.9 * a["terr"]:
                it.append(dict(bot=b["name"], t0=a["t"], t1=c["t"], cmds=(c["cmds"] - a["cmds"]) - (c["boats"] - a["boats"]), bal0=a["bal"], bal1=c["bal"],
                               terr0=a["terr"], terr1=c["terr"], realized=m.collapsed(b, c["t"], c["terr"], 450)))
    return dict(hit=bool(it), n=len(it), items=it, realized=sum(1 for x in it if x["realized"]))


def ex_assist_burst(m):
    it = []
    for b in m.bots.values():
        asz = sorted(b.get("assists") or [], key=lambda x: x["t"])
        i = 0
        while i < len(asz):
            j = i
            while j + 1 < len(asz) and asz[j + 1]["enemy"] == asz[i]["enemy"] and asz[j + 1]["t"] - asz[j]["t"] <= 4:
                j += 1
            if j - i + 1 >= 3:
                n = j - i + 1
                it.append(dict(bot=b["name"], t0=asz[i]["t"], t1=asz[j]["t"], n=n, enemy=asz[i].get("enemyName"), drainPct=round(100 * (1 - 0.8877 ** n))))
            i = j + 1
    return dict(hit=bool(it), n=len(it), items=it)


# ---------------------------------------------------------------- 终局 / 多队

def eg_inherit(m):
    """NEW-EG-G2：一个编队号阵亡落在另一个号的快照窗里，后者这一窗有非船指令、领土 +≥500，之后两条快照没吐回去。"""
    it = []
    deaths = [(m.death(b), b["name"]) for b in m.bots.values() if m.death(b) is not None]
    for b in m.bots.values():
        tk = b["ticks"]
        for i in range(1, len(tk)):
            a, c = tk[i - 1], tk[i]
            dd = [n for t, n in deaths if a["t"] < t <= c["t"] and n != b["name"]]
            if not dd:
                continue
            if (c["cmds"] - a["cmds"]) - (c["boats"] - a["boats"]) >= 1 and c["terr"] - a["terr"] >= 500:
                nxt = tk[i + 1:i + 3]
                if all(s["terr"] >= a["terr"] + 500 for s in nxt):
                    it.append(dict(bot=b["name"], t0=a["t"], t1=c["t"], gain=c["terr"] - a["terr"], cmds=(c["cmds"] - a["cmds"]) - (c["boats"] - a["boats"]), died=dd))
    return dict(hit=bool(it), n=len(it), items=it, cells=sum(x["gain"] for x in it))


def mt_protect_lock(m):
    """NEW-MT-07：最后 ≥2 条快照里编队在线号合占陆地 ≥70%、分属 ≥2 个队、≥70% 的在线号 nb=0，结果行的 alivePlayers 比在线编队号多。"""
    ts = sorted({s["t"] for b in m.bots.values() for s in b["ticks"]})
    hits = []
    for t in ts[-6:]:
        rows = [(b, s) for b in m.bots.values() for s in b["ticks"] if s["t"] == t and s["terr"] > 0]
        if not rows:
            continue
        share = sum(s["terr"] for _, s in rows) / m.land
        teams = {b.get("team") for b, _ in rows}
        nb0 = sum(1 for _, s in rows if s["nb"] == 0)
        if share >= 0.70 and len(teams) >= 2 and nb0 >= 0.7 * len(rows):
            hits.append(dict(t=t, online=len(rows), share=round(100 * share, 1), teams=len(teams), nb0=nb0))
    alive = [b.get("alivePlayers") for b in m.bots.values() if b.get("alivePlayers") is not None]
    ok = len(hits) >= 2 and (not alive or min(alive) > hits[-1]["online"])
    return dict(hit=ok, n=len(hits) if ok else 0, items=hits if ok else [], minAlivePlayers=min(alive) if alive else None)


DETECTORS = [
    ("NEW-SP-01", "sp_fallback", sp_fallback), ("NEW-SP-02", "sp_cluster", sp_cluster), ("NEW-SP-03", "sp_mixed_solutions", sp_mixed_solutions),
    ("NEW-OP-01", "op_boxed_early", op_boxed_early), ("NEW-OP-02", "op_crumb_lock", op_crumb_lock), ("NEW-OP-G2", "op_boat_breakout", op_boat_breakout),
    ("NEW-OP-G1", "op_on_schedule", op_on_schedule),
    ("NEW-EC-01", "ec_thin_big", ec_thin_big), ("NEW-EC-02", "ec_hoard_1nb", ec_hoard_1nb), ("NEW-EC-03", "ec_over_softcap", ec_over_softcap),
    ("NEW-EC-G1", "ec_hold_survive", ec_hold_survive), ("NEW-EC-04", "ec_team_standoff", ec_team_standoff), ("NEW-EC-09", "ec_hardcap_idle", ec_hardcap_idle),
    ("NEW-DN-01", "dn_threshold_unreachable", dn_threshold_unreachable), ("NEW-DN-03", "dn_no_channel_early", dn_no_channel_early),
    ("NEW-DN-02", "dn_tax_gt_gift", dn_tax_gt_gift), ("NEW-DN-07", "dn_pingpong", dn_pingpong), ("NEW-DN-17", "dn_rescue_bounce", dn_rescue_bounce),
    ("NEW-AT-01", "at_overcap_dump", at_overcap_dump), ("NEW-AT-02", "at_drained", at_drained), ("NEW-AT-03", "at_pricey_bite", at_pricey_bite),
    ("NEW-AT-04", "at_buffer_removed", at_buffer_removed), ("NEW-AT-G1", "at_cheap_buy", at_cheap_buy),
    ("NEW-DF-01", "df_passive", df_passive), ("NEW-DF-01w", "df_passive_wide", df_passive_wide), ("NEW-DF-07", "df_full_death", df_full_death),
    ("NEW-SE-01", "se_big_intercept", se_big_intercept), ("NEW-EX-02", "ex_burst_drain", ex_burst_drain), ("NEW-EX-03", "ex_assist_burst", ex_assist_burst),
    ("NEW-EG-G2", "eg_inherit", eg_inherit), ("NEW-MT-07", "mt_protect_lock", mt_protect_lock),
    ("NEW-DF-08", "df_quarter_bank", df_quarter_bank), ("NEW-MT-11", "mt_ffa_boxed", mt_ffa_boxed),
    ("NEW-MT-09L", "mt_boxed_long", mt_boxed_long), ("NEW-MT-06", "mt_unseen_loss", mt_unseen_loss),
]


def fmt_item(x):
    return "{" + ", ".join(f"{k}={v}" for k, v in x.items()) + "}"


def run(mid, room=None, quiet=False):
    m = M(mid, room)
    res = {}
    out = [f"[XP] {mid}{'（房间 %s）' % room if room else ''} 模式机械计数（只看日志）：编队 {len(m.bots)} 个号，陆地 {m.land}，终局拍 {m.end}。"
           "模式 | 函数 | 命中? | 次数 | 兑现 | 其它合计 | 明细（最多 8 条）"]
    for pid, fn, f in DETECTORS:
        try:
            r = f(m)
        except Exception as e:  # noqa: BLE001
            r = dict(hit=False, n=0, items=[], error=repr(e))
        res[pid] = r
        nm = PC.BY_ID.get(pid.rstrip("wL"), {}).get("name", "")[:26]
        extra = {k: v for k, v in r.items() if k not in ("hit", "n", "items", "realized", "closePairs")}
        out.append(f"  {pid:<11} {nm} | {fn} | {'是' if r['hit'] else '否'} | {r['n']} | {r.get('realized', '-')} | "
                   + (" ".join(f"{k}={v}" for k, v in extra.items()) or "-") + " | " + "；".join(fmt_item(x) for x in r["items"][:8])
                   + (f" …共 {len(r['items'])} 条" if len(r["items"]) > 8 else ""))
    od = os.path.join(OUT, mid)
    suf = "" if room in (None, 0) else f"_room{room}"
    open(os.path.join(od, f"patterns{suf}.txt"), "w", encoding="utf-8").write("\n".join(out) + "\n")
    json.dump(dict(matchId=mid, room=room, bots=len(m.bots), patterns=res), open(os.path.join(od, f"patterns_sum{suf}.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1, default=str)
    if not quiet:
        print("\n".join(out))
    else:
        print(f"{mid}: patterns{suf}.txt {len(out)} 行；命中 {sum(1 for r in res.values() if r['hit'])}/{len(res)} 个模式")
    return res


def main():
    args = sys.argv[1:]
    quiet = "--quiet" in args
    room = int(args[args.index("--room") + 1]) if "--room" in args else None
    if "--all" in args:
        mids = [a for a in args if not a.startswith("--")]
        allres = {}
        for mid in mids:
            allres[mid] = run(mid, quiet=True)
        od = os.path.join(OUT, "_cross")
        os.makedirs(od, exist_ok=True)
        out = ["[XM] 模式 × 局（只看日志的机械计数；格子 = 次数，带 * = 有兑现的次数，- = 没命中）",
               "  模式 | 名称 | " + " | ".join(mids) + " | 命中局数 | 次数合计"]
        for pid, fn, _ in DETECTORS:
            cells = []
            for mid in mids:
                r = allres[mid][pid]
                cells.append("-" if not r["hit"] else (f"{r['n']}" + (f"*{r['realized']}" if r.get("realized") else "")))
            nm = PC.BY_ID.get(pid.rstrip("wL"), {}).get("name", "")[:22]
            out.append(f"  {pid:<11} | {nm} | " + " | ".join(f"{c:>5}" for c in cells) + f" | {sum(1 for mid in mids if allres[mid][pid]['hit'])} | "
                       f"{sum(allres[mid][pid]['n'] for mid in mids if allres[mid][pid]['hit'])}")
        open(os.path.join(od, "patterns_matrix.txt"), "w", encoding="utf-8").write("\n".join(out) + "\n")
        json.dump({mid: {pid: {k: v for k, v in r.items() if k != "items"} for pid, r in rr.items()} for mid, rr in allres.items()},
                  open(os.path.join(od, "patterns_matrix.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
        print("\n".join(out))
        return
    run(args[0], room, quiet)


if __name__ == "__main__":
    main()
