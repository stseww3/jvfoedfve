#!/usr/bin/env python3
"""facts.py — 一局的「事实底稿」：从标准化对局包机械地抽出复盘要用的全部数字。

    python3 c136-review/agents/R08/scripts/facts.py <matchId> [--quiet]

写出 c136-review/agents/R08/out/<matchId>/facts.json 与 digest.txt（digest 就是 stdout 的内容）。
复盘 JSON/MD 里出现的每个数字都能在 digest.txt 里按 [节号] 找到，行号是 in_game.log 的原始日志行号。

节：
  [A] 对局卡      [B] 身份表（玩家号 me ↔ 日志前缀名 label、队号、出生点、峰值、结局）
  [C] 检查点时间线（编队/主队合计）      [D] 结算拍的全队领土占比（team.totals）
  [E] 逐 bot 分段轨迹（G=扩张 H=持平 S=失地）   [F] DROP30（余额单段跌 ≥30%）归因
  [G] 捐款账本（税、到账、额度点数模型、是否被拒）   [H] 其它策略事件（ASSIST/INTERCEPT/PEACE）
  [I] 死亡链      [J] 停滞统计（被围/高密度/超软上限）      [K] 开局（出生点、HL-OPENING 逐周期）
"""
import json
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r08lib as L  # noqa: E402

MIN_OBS_LAG = 20
DON_RE = re.compile(r"t=(\d+) (.+?) pct=(\d+)/1024.*?-> ally=(\d+)\((.*?)\)(?: boxedIn=(\w+))? myBal=(-?\d+) dMe=(\d+)(?: dAlly=(\d+))?")
ASSIST_RE = re.compile(r"t=(\d+) (\d+)% squad-rescue poke -> enemy=(\d+)\((.*)\) for ally=(\d+)\((.*)\)")
INTER_RE = re.compile(r"t=(\d+) unified sea intercept pct=(\d+)/1024 -> boatId=(\d+) owner=(\d+)\((.*)\) boatTroops=(\d+)")
PEACE_RE = re.compile(r"t=(\d+) initiated peace vote \(teamLand=([\d.]+)%\)")
SPAWN_RE = re.compile(r"me=(\d+) slot=(\d+).*?-> \((\d+),(\d+)\)")
SPAWNB_RE = re.compile(r"bossDist=(-?\d+) minAllyDist=(\d+) voronoi=(\d+)")
SLOW_RE = re.compile(r"t=(\d+) took ([\d.]+)ms")
OCHK_RE = re.compile(r"\[OPENING-CHECK (\d+) bots @ tick (\d+)\] (.*)$")


def fmt(n):
    if n is None:
        return "-"
    if isinstance(n, float):
        return f"{n:.1f}"
    return str(n)


def build(mid, room=None):
    """room：一个对局包里混了几个物理房间时选哪个房间（默认主房间）；单房间的包忽略这个参数。"""
    card = L.load_card(mid)
    land = card["mapLand"]
    recs = L.parse_log(mid)
    truth = L.load_truth(mid)
    label_map, rinfo = L.room_label_map(mid)
    res_rows0 = L.load_results(mid)
    res_me = {}
    for rr in res_rows0:
        if rr.get("meId") is not None and rr.get("bot"):
            res_me[str(rr["bot"])] = int(rr["meId"])
    tracks, notes, unresolved = L.resolve_identities(recs, L.fingerprints(truth) if (truth and not label_map) else None, res_me,
                                                     label_map)
    end_tick = card["outcome"]["endTick"]
    primary = card.get("ourPrimaryTeam")

    bots = {}
    for me, tr in sorted(tracks.items()):
        b = dict(me=me, name=tr.name, labels=tr.labels, ticks=tr.ticks, team=None, result=None, event=None,
                 resLine=None, place=None, resPeak=None, deathTick=None, spawn=None, spawnInfo=None,
                 openings=[], donations=[], assists=[], intercepts=[], peaces=[], slow=[])
        for r in tr.lines:
            tag, body = r["tag"], r["body"]
            if tag in ("HL-SPAWN", "HL-SPAWN-BACKEND"):
                m = SPAWN_RE.search(r["raw"])
                if m:
                    b["spawn"] = (int(m.group(3)), int(m.group(4)))
                    b["spawnLine"] = r["line"]
                    b["spawnCount"] = b.get("spawnCount", 0) + 1
                    mb = SPAWNB_RE.search(r["raw"])
                    if mb:
                        b["spawnInfo"] = dict(bossDist=int(mb.group(1)), minAllyDist=int(mb.group(2)), voronoi=int(mb.group(3)))
            elif tag == "HL-OPENING":
                m = L.OPEN_RE.search(body)
                if m:
                    t, cyc, rings, spend, bal, terr = map(int, m.groups())
                    b["openings"].append(dict(t=t, cyc=cyc, rings=rings, spend=spend, bal=bal, terr=terr, line=r["line"]))
            elif tag == "HL-DONATE":
                m = DON_RE.search(body)
                if m:
                    b["donations"].append(dict(t=int(m.group(1)), kind=m.group(2).strip(), pct=int(m.group(3)),
                                               ally=int(m.group(4)), allyName=m.group(5), boxedIn=m.group(6),
                                               myBal=int(m.group(7)), dMe=int(m.group(8)),
                                               dAlly=int(m.group(9)) if m.group(9) else None, line=r["line"], donor=me))
            elif tag == "HL-ASSIST":
                m = ASSIST_RE.search(body)
                if m:
                    b["assists"].append(dict(t=int(m.group(1)), pct10=int(m.group(2)), enemy=int(m.group(3)), enemyName=m.group(4),
                                             ally=int(m.group(5)), allyName=m.group(6), line=r["line"]))
            elif tag == "HL-INTERCEPT":
                m = INTER_RE.search(body)
                if m:
                    b["intercepts"].append(dict(t=int(m.group(1)), pct=int(m.group(2)), boatId=int(m.group(3)), owner=int(m.group(4)),
                                                ownerName=m.group(5), boatTroops=int(m.group(6)), line=r["line"]))
            elif tag == "HL-PEACE":
                m = PEACE_RE.search(body)
                if m:
                    b["peaces"].append(dict(t=int(m.group(1)), teamLand=float(m.group(2)), line=r["line"]))
            elif tag == "HL-SLOW-TICK":
                m = SLOW_RE.search(body)
                if m:
                    b["slow"].append((int(m.group(1)), float(m.group(2))))
            elif tag == "RESULT":
                b["result"], b["event"], b["place"], b["resPeak"], b["resLine"] = r["result"], r["event"], r["place"], r["peak"], r["line"]
                if r.get("team"):
                    b["team"] = r["team"].get("mine")
                    b["teamTotals"] = r["team"].get("totals")
                    b["teamBest"] = r["team"].get("best")
        bots[me] = b

    # 结算拍号：results.csv 的 tick 列，按 (日志行号) 对上
    res_rows = L.load_results(mid)
    by_peak = defaultdict(list)
    for rr in res_rows:
        by_peak[(rr.get("event"), rr.get("peak"), rr.get("place"))].append(rr)
    for b in bots.values():
        if b["result"] is None:
            continue
        cands = by_peak.get((b["event"], b["resPeak"], b["place"]), [])
        if cands:
            rr = cands[0]
            b["deathTick"] = rr.get("tick")
            b["lastTerritory"] = rr.get("lastTerritory")
            b["resBalance"] = rr.get("balance")
            b["resTerritory"] = rr.get("territory")
            b["alivePlayers"] = rr.get("alivePlayers")
    # 多房间的包：每个号标上房间；真值（录像）只属于其中一个房间
    truth_room = None
    if rinfo:
        hits = defaultdict(int)
        for key, b in bots.items():
            ri = rinfo.get(key) or {}
            b["room"], b["meReal"], b["pseudoMe"] = ri.get("room"), ri.get("me"), bool(ri.get("pseudo"))
            if truth and b["meReal"] is not None and b["meReal"] < truth["H"]:
                nm = str(truth["names"][b["meReal"]]).strip().lower()
                if any(nm.endswith(lab.lower()) for lab in b["labels"]):
                    hits[b["room"]] += 1
        if hits:
            truth_room = max(hits, key=hits.get)
    if truth:
        # 全场真值：队号、离开拍、阵亡拍以重演为准
        for me, b in bots.items():
            if rinfo:
                if b.get("room") != truth_room or b.get("meReal") is None:
                    continue
                me = b["meReal"]
            if me < truth["H"]:
                b["team"] = truth["teams"][me] or b["team"]
                b["teamTruth"] = True
                b["leftTick"] = truth["leftT"][me] if truth["leftT"][me] >= 0 else None
                b["deathTickTruth"] = truth["deathT"][me] if truth["deathT"][me] >= 0 else None
                if b["event"] is None and b["leftTick"] is not None:
                    # 没有结算行、但录像里执行过「离开」：按离开处理，拍号取引擎执行离开的那一拍
                    b["event"], b["result"], b["deathTick"], b["leftInferred"] = "left", "left", b["leftTick"], True
    rooms_meta = None
    other_bots = {}
    sel_room = None
    if rinfo:
        sel_room = rinfo["_main"] if room is None else int(room)
        rooms_meta = rinfo["_rooms"]
        other_bots = {k: b for k, b in bots.items() if b.get("room") != sel_room}
        bots = {k: b for k, b in bots.items() if b.get("room") == sel_room}
        rm = rooms_meta.get(sel_room) or {}
        orig = {k: card.get(k) for k in ("mapLand", "seededPlayers", "squadBots", "ourPrimaryTeam", "teamSplitCounts", "distinctSquadTeams")}
        orig["outcome"] = dict(card["outcome"])
        land = rm.get("land") or land
        split = defaultdict(int)
        for b in bots.values():
            if b["team"] is not None:
                split[str(b["team"])] += 1
        primary = int(max(split, key=lambda k: (split[k], -int(k)))) if split else None
        end_tick = rm.get("lastTick") or end_tick
        all_t = sorted({s["t"] for b in bots.values() for s in b["ticks"]})
        peak_sq = max((sum(s["terr"] for b in bots.values() for s in [snap_at(b, t, 0)] if s) for t in all_t), default=0)
        tot_rows = [(b["deathTick"] or 0, b) for b in bots.values() if b.get("teamTotals")]
        prim_sh = [bb["teamTotals"].get(str(primary), 0) / land for _, bb in sorted(tot_rows, key=lambda x: x[0])] if primary else []
        last_tot = max(tot_rows, key=lambda x: x[0])[1]["teamTotals"] if tot_rows else None
        winner = rm.get("winner")
        if winner is None and last_tot:
            lt = {int(k): v for k, v in last_tot.items() if int(k) != 0}
            winner = max(lt, key=lt.get) if lt else None
        card = dict(card)
        oc = dict(card["outcome"])
        any_won = any(b["result"] == "won" for b in bots.values())
        oc.update(endTick=end_tick, winnerTeam=winner, primaryTeamWon=bool(winner is not None and winner == primary),
                  anyBotWon=any_won, peakSquadLandShare=round(peak_sq / land, 4),
                  peakPrimaryTeamShareSeen=round(max(prim_sh), 4) if prim_sh else None,
                  ourFinalTeamShare=round(prim_sh[-1], 4) if prim_sh else None)
        oc["resultLabel"] = "won" if oc["primaryTeamWon"] else "lost"
        card.update(mapLand=land, seededPlayers=rm.get("seeded") or card.get("seededPlayers"), squadBots=len(bots),
                    ourPrimaryTeam=primary, teamSplitCounts=dict(sorted(split.items())), distinctSquadTeams=len(split), outcome=oc,
                    roomIdx=sel_room, roomsInBundle=len(rooms_meta), cardOriginal=orig)
    name_of = {me: b["name"] for me, b in bots.items()}
    # 没拆队的局：离开（left，结算里 team=null）的号按主队算，并标记为推断
    if len(card.get("teamSplitCounts") or {}) == 1:
        for b in bots.values():
            if b["team"] is None:
                b["team"] = primary
                b["teamInferred"] = True

    # OPENING-CHECK
    ochk = []
    for r in recs:
        if r["tag"] == "OPENING-CHECK":
            m = OCHK_RE.search(r["raw"])
            if m:
                items = re.findall(r"([^|]+?):tick=(\d+),terr=(\d+),sent=(\d+)\((\w+)\)", m.group(3))
                ochk.append(dict(line=r["line"], n=int(m.group(1)), tick=int(m.group(2)),
                                 items=[dict(name=a.strip(), tick=int(b_), terr=int(c), sent=int(d), ok=e) for a, b_, c, d, e in items]))
    return dict(card=card, land=land, bots=bots, notes=notes, unresolved=[u["line"] for u in unresolved],
                hasTruth=bool(truth) and (not rinfo or truth_room == sel_room),
                endTick=end_tick, primary=primary, ochk=ochk, name_of=name_of, results=res_rows,
                room=sel_room, rooms=rooms_meta, truthRoom=truth_room, otherBots=other_bots)


def snap_at(b, t, tol=45):
    best = None
    for s in b["ticks"]:
        if abs(s["t"] - t) <= tol and (best is None or abs(s["t"] - t) < abs(best["t"] - t)):
            best = s
    return best


def snap_fill(b, t):
    """t 拍的快照；这一拍的日志行丢了（前后都有快照）就沿用前一条。返回 (快照, 是否沿用)。"""
    prev = None
    for s in b["ticks"]:
        if s["t"] == t:
            return s, False
        if s["t"] < t:
            prev = s
        else:
            return (prev, True) if prev is not None else (None, False)
    return None, False


def segments(b):
    """把 HL-TICK 序列切成 G/H/S 段。"""
    tk = b["ticks"]
    segs = []
    for i in range(1, len(tk)):
        a, c = tk[i - 1], tk[i]
        base = max(a["terr"], 1)
        cls = "G" if c["terr"] > base * 1.02 else "S" if c["terr"] < base * 0.98 else "H"
        if segs and segs[-1]["cls"] == cls and segs[-1]["t1"] == a["t"]:
            s = segs[-1]
            s["t1"], s["terr1"], s["bal1"], s["dens1"] = c["t"], c["terr"], c["bal"], c["dens"]
            s["nb"].append(c["nb"]); s["neut"].append(c["neut"])
            s["cmds1"], s["boats1"], s["line1"] = c["cmds"], c["boats"], c["line"]
            s["balMin"] = min(s["balMin"], c["bal"]); s["balMax"] = max(s["balMax"], c["bal"])
        else:
            segs.append(dict(cls=cls, t0=a["t"], t1=c["t"], terr0=a["terr"], terr1=c["terr"], bal0=a["bal"], bal1=c["bal"],
                             dens0=a["dens"], dens1=c["dens"], nb=[a["nb"], c["nb"]], neut=[a["neut"], c["neut"]],
                             cmds0=a["cmds"], cmds1=c["cmds"], boats0=a["boats"], boats1=c["boats"],
                             line0=a["line"], line1=c["line"], balMin=min(a["bal"], c["bal"]), balMax=max(a["bal"], c["bal"])))
    return segs


def interest_gain(terr, land, bal, t0, t1):
    """从 t0 到 t1 按引擎公式滚利息（领土不变的近似），返回期末余额。"""
    b = bal
    t = t0
    while t < t1:
        if t % 10 == 9:
            r = L.interest_rate(terr, land, b, t)
            b = min(b + max(L.g0(r * b, 10000), 1), 150 * terr)
        if t % 100 == 99:
            b = min(b + terr, 150 * terr)
        t += 1
    return b


def donation_ledger(F):
    """全队捐款按时间排，套引擎的税/到账/额度模型，并用捐出方下一次已知余额判断是否成交。"""
    land = F["land"]
    bots = F["bots"]
    dons = sorted([d for b in bots.values() for d in b["donations"]], key=lambda d: (d["t"], d["line"]))
    used = defaultdict(int)       # receiver -> 已用点数（只含我们自己人成交的捐款；队里别人的捐款看不到）
    # 捐出方余额观测序列
    obs = {}
    for me, b in bots.items():
        o = [(s["t"], s["bal"], s["terr"], "tick") for s in b["ticks"]] + [(d["t"], d["myBal"], None, "don") for d in b["donations"]]
        o.sort(key=lambda x: (x[0], 0 if x[3] == "don" else 1))
        obs[me] = o
    out = []
    for d in dons:
        me = d["donor"]
        B, pct, t = d["myBal"], d["pct"], d["t"]
        amt, fee = L.donate_quote(B, pct)
        recv = bots.get(d["ally"])
        rs = None
        if recv:
            prior = [s for s in recv["ticks"] if s["t"] <= t]
            rs = prior[-1] if prior else (recv["ticks"][0] if recv["ticks"] else None)
        recv_terr = rs["terr"] if rs else None
        recv_bal = rs["bal"] if rs else None
        room = None
        if rs:
            room = max(150 * rs["terr"] - rs["bal"], 0)
        amt_eff = min(amt, room) if room is not None else amt
        cap = L.quota_cap(t)
        cost = L.quota_points(t, amt_eff, land, recv_terr or 1)
        free = t >= 4284
        model_rej = (not free) and (used[d["ally"]] + cost > cap)
        # 观测：捐出方下一条余额
        donor_terr = None
        pr = [s for s in bots[me]["ticks"] if s["t"] <= t]
        if d.get("dMe"):
            donor_terr = max(1, round(B / d["dMe"]))     # 日志行自带的 dMe=B/L，比上一条快照的领土更贴近捐款当拍
        elif pr:
            donor_terr = pr[-1]["terr"]
        elif bots[me]["ticks"]:
            donor_terr = bots[me]["ticks"][0]["terr"]
        # 指令从发出到引擎执行有延迟（有录像的局中位数 12~16 拍），所以只认发令 20 拍以后的余额观测
        nxt = None
        for o in obs[me]:
            if o[0] >= t + MIN_OBS_LAG:
                nxt = o
                break
        # 判定：把「被拒（余额原封不动滚利息）」与「成交（扣税+到账后滚利息）」两个预期和下一次观测到的余额比。
        # 两个预期差不到 1% 余额、或观测值离两个预期都远（中间有别的收支）→ 判不了，记 "?"
        verdict = "?"
        ratio = None
        if nxt and donor_terr:
            b_rej = interest_gain(donor_terr, land, B, t, nxt[0])
            b_acc = interest_gain(donor_terr, land, max(B - fee - amt_eff, 0), t, nxt[0])
            ratio = nxt[1] / max(B, 1)
            gap = abs(b_rej - b_acc)
            e_rej, e_acc = abs(nxt[1] - b_rej), abs(nxt[1] - b_acc)
            if gap >= max(20, 0.01 * B) and min(e_rej, e_acc) <= 0.6 * gap and nxt[0] - t <= 120:
                verdict = "REJ" if e_rej <= e_acc else "ACC"
            d["nextObs"] = dict(t=nxt[0], bal=nxt[1], kind=nxt[3], expRej=b_rej, expAcc=b_acc)
        d.update(amount=amt, amountEff=amt_eff, fee=fee, cap=cap, cost=cost, usedBefore=used[d["ally"]], modelRej=model_rej,
                 obsVerdict=verdict, ratio=ratio, recvTerr=recv_terr, recvBal=recv_bal, room=room, free=free)
        accepted = (verdict == "ACC") or (verdict == "?" and not model_rej)
        d["accepted"] = accepted
        if accepted and not free:
            used[d["ally"]] += cost
        out.append(d)
    return out


def drop30(F, dons):
    bots = F["bots"]
    land = F["land"]
    out = []
    for me, b in bots.items():
        tk = b["ticks"]
        for i in range(1, len(tk)):
            a, c = tk[i - 1], tk[i]
            if a["bal"] >= 200 and c["bal"] < 0.7 * a["bal"]:
                dterr = c["terr"] - a["terr"]
                dn = [d for d in dons if d["donor"] == me and a["t"] <= d["t"] < c["t"]]
                don_out = sum(d["fee"] + d["amountEff"] for d in dn if d["accepted"])
                don_fee = sum(d["fee"] for d in dn if d["accepted"])
                exp_noact = interest_gain(a["terr"], land, a["bal"], a["t"], c["t"])
                gone = exp_noact - c["bal"]
                rel = dterr / max(a["terr"], 1)
                if rel > 0.02:
                    cls = "ATTACK-GAIN"
                elif rel < -0.02:
                    cls = "LOST-LAND"
                elif c["boats"] > a["boats"]:
                    cls = "BOAT"
                elif don_out > 0.5 * (a["bal"] - c["bal"]):
                    cls = "DONATE"
                elif c["cmds"] > a["cmds"]:
                    cls = "SPEND-NO-LAND"
                else:
                    cls = "PASSIVE-LOSS"
                per_px = gone / dterr if dterr > 0 else None
                # 余额不含在途进攻兵：下一段若「实际 > 公式」说明兵回流了，若领土续涨说明这一段的兵在下一段才变成地。
                # 所以再给一组「两段合计」：net2 = 本段少掉的 - 下一段多出来的；px2 = 两段净增领土。
                reb = dterr2 = net2 = px2 = per_px2 = t2 = None
                if i + 1 < len(tk):
                    n = tk[i + 1]
                    exp2 = interest_gain(c["terr"], land, c["bal"], c["t"], n["t"])
                    reb = n["bal"] - exp2
                    dterr2 = n["terr"] - c["terr"]
                    net2 = gone - reb
                    px2 = n["terr"] - a["terr"]
                    per_px2 = net2 / px2 if px2 > 0 else None
                    t2 = n["t"]
                # 「续攻口径」：派出去的兵可以连着打好几段（期间不再发指令、领土继续涨、余额照公式走）。
                # 从本段起往后接所有「Δcmds=0、Δboats=0、领土续涨」的段；紧接着的一段若只是回流（余额多于公式）也并进来。
                epi_net, epi_end, epi_terr, epi_n = gone, c["t"], c["terr"], 0
                for j in range(i + 1, min(len(tk), i + 8)):
                    p0, p1 = tk[j - 1], tk[j]
                    r = p1["bal"] - interest_gain(p0["terr"], land, p0["bal"], p0["t"], p1["t"])
                    quiet = p1["cmds"] == p0["cmds"] and p1["boats"] == p0["boats"]
                    if quiet and p1["terr"] > p0["terr"]:
                        epi_net -= r
                        epi_end, epi_terr, epi_n = p1["t"], p1["terr"], epi_n + 1
                    elif j == i + 1 and r > 0 and p1["terr"] >= p0["terr"]:
                        epi_net -= r
                        epi_end, epi_terr, epi_n = p1["t"], p1["terr"], epi_n + 1
                        break
                    else:
                        break
                epi_px = epi_terr - a["terr"]
                epi_per = epi_net / epi_px if epi_px > 0 else None
                out.append(dict(me=me, name=b["name"], t0=a["t"], t1=c["t"], bal0=a["bal"], bal1=c["bal"], dropPct=100 * (1 - c["bal"] / a["bal"]),
                                epiEnd=epi_end, epiNet=epi_net, epiPx=epi_px, epiPerPx=epi_per, epiSegs=epi_n,
                                terr0=a["terr"], terr1=c["terr"], dterr=dterr, dcmds=c["cmds"] - a["cmds"], dboats=c["boats"] - a["boats"],
                                nb0=a["nb"], nb1=c["nb"], neut0=a["neut"], neut1=c["neut"], donN=len(dn), donOut=don_out, donFee=don_fee,
                                expNoAct=exp_noact, gone=gone, perPx=per_px, cls=cls, line0=a["line"], line1=c["line"],
                                dens0=a["dens"], t2=t2, reb=reb, dterr2=dterr2, net2=net2, px2=px2, perPx2=per_px2))
    out.sort(key=lambda x: (x["t0"], x["me"]))
    return out


def idle_check(F):
    """相邻两条快照之间没有发指令（Δcmds=0、Δboats=0）且领土不变时，余额只该按引擎利息/地租公式增长。
    返回 (全部闲置段的相对残差列表, 离群段列表)。正残差=多出来的钱（收到捐款/撤军回款），负残差=少掉的钱（挨打掉血/还欠款）。"""
    land = F["land"]
    rel, outliers = [], []
    for me, b in F["bots"].items():
        tk = b["ticks"]
        for i in range(1, len(tk)):
            a, c = tk[i - 1], tk[i]
            if c["cmds"] != a["cmds"] or c["boats"] != a["boats"] or c["terr"] != a["terr"] or a["terr"] < 50:
                continue
            exp = interest_gain(a["terr"], land, a["bal"], a["t"], c["t"])
            resid = c["bal"] - exp
            r = resid / max(exp, 1)
            rel.append(r)
            if abs(r) > 0.03 and abs(resid) > 500:
                outliers.append(dict(me=me, name=b["name"], t0=a["t"], t1=c["t"], terr=a["terr"], bal0=a["bal"], bal1=c["bal"],
                                     exp=exp, resid=resid, rel=r, nb=c["nb"], line0=a["line"], line1=c["line"]))
    return rel, outliers


def inflow_check(F, dons):
    """相邻快照之间余额比「不动只滚利息」多出一截的段：在途进攻兵回流（进攻结束 [X8]）、收到捐款、或被拒/撤回的指令。
    余额 bal 不含在途兵，所以一次大额出兵会先表现为 DROP30，再在这里表现为回流。"""
    land = F["land"]
    out = []
    for me, b in F["bots"].items():
        tk = b["ticks"]
        for i in range(1, len(tk)):
            a, c = tk[i - 1], tk[i]
            if a["terr"] < 50:
                continue
            exp = interest_gain(a["terr"], land, a["bal"], a["t"], c["t"])
            extra = c["bal"] - exp
            if extra > max(5000, 0.10 * exp):
                din = [d for d in dons if d["ally"] == me and a["t"] <= d["t"] < c["t"] and d["accepted"]]
                out.append(dict(me=me, name=b["name"], t0=a["t"], t1=c["t"], terr0=a["terr"], terr1=c["terr"], bal0=a["bal"], bal1=c["bal"],
                                exp=exp, extra=extra, donIn=sum(d["amountEff"] for d in din), donN=len(din),
                                dcmds=c["cmds"] - a["cmds"], dboats=c["boats"] - a["boats"], line0=a["line"], line1=c["line"]))
    out.sort(key=lambda x: (x["t0"], x["me"]))
    return out


def digest(F):
    card, bots, land = F["card"], F["bots"], F["land"]
    o = []
    P = o.append
    oc = card["outcome"]
    P(f"[A] {card['matchId']} cohort={card['cohort']} map={card['mapId']}/{card['mapSeed']} land={land} mode={card['mode']} "
      f"nominalTeams={card['nominalTeams']} actualTeams={card['actualTeams']} base={card['baseWinExpectation']} seeded={card['seededPlayers']}")
    P(f"    squadBots={card['squadBots']} primaryTeam={card['ourPrimaryTeam']} split={card['teamSplitCounts']} "
      f"result={oc['resultLabel']} winnerTeam={oc['winnerTeam']} endTick={oc['endTick']} peakSquadShare={oc['peakSquadLandShare']} "
      f"peakPrimaryTeamShareSeen={oc['peakPrimaryTeamShareSeen']} finalTeamShare={oc['ourFinalTeamShare']}")
    P(f"    anomalies={card['anomaliesSummary']} peer={card.get('sameMatchPeer')}")
    if F.get("rooms"):
        P(f"    【多房间的包】本底稿只算房间 {F['room']}；录像（真值）属于房间 {F.get('truthRoom')}。各房间：" +
          "；".join(f"房间{k}: 陆地 {v['land']} 真人 {v['seeded']} 我方 {v['nBots']} 个号 开局 {v['startUtc']} 末拍 {v['lastTick']} 胜队 {v['winner']}"
                    for k, v in sorted(F["rooms"].items())))
        co = card.get("cardOriginal") or {}
        P(f"    对局卡原值（把几个房间混在一起算的）：squadBots={co.get('squadBots')} split={co.get('teamSplitCounts')} land={co.get('mapLand')} "
          f"outcome={co.get('outcome')}")
        P("    其它房间的号：" + " ".join(f"{b['name']}({k})r{b.get('room')}" for k, b in F["otherBots"].items()))
    if F["notes"]:
        P(f"    身份还原备注 {len(F['notes'])} 条；未归属日志行 {len(F['unresolved'])} 条")

    P("[B] 身份表 me | labels | team | spawn(x,y)[改点次数] | HL-TICK 首末拍 | 日志峰值领土@拍 | 结局 event@tick place peak")
    for me, b in bots.items():
        tk = b["ticks"]
        pk = max(tk, key=lambda s: s["terr"]) if tk else None
        P(f"    {me:>3} | {'>'.join(b['labels'])} | T{b['team'] if b['team'] is not None else '?'} | {b['spawn']}[{b.get('spawnCount', 0)}] | "
          f"{tk[0]['t'] if tk else '-'}..{tk[-1]['t'] if tk else '-'} | {pk['terr'] if pk else '-'}@{pk['t'] if pk else '-'} | "
          f"{b['event']}/{b['result']}@{b['deathTick']} place={b['place']} peak={b['resPeak']} L{b['resLine']}")

    # [C] checkpoints
    all_t = sorted({s["t"] for b in bots.values() for s in b["ticks"]})
    P("[C] 检查点 t | 有数的号数(其中沿用前一条快照的) | 编队领土 占比% | 编队余额 密度 | 主队成员(T=primary)领土 占比% | 被围(nb=0&neut=0)数 | 密度>=95数 | 超软上限数")
    prim = F["primary"]
    for t in all_t:
        sf = [(b,) + snap_fill(b, t) for b in bots.values()]
        nfill = sum(1 for _, s, f in sf if s and f)
        ss = [(b, s) for b, s, f in sf if s]
        if not ss:
            continue
        terr = sum(s["terr"] for _, s in ss)
        bal = sum(s["bal"] for _, s in ss)
        pterr = sum(s["terr"] for b, s in ss if b["team"] == prim)
        boxed = sum(1 for _, s in ss if s["nb"] == 0 and s["neut"] == 0)
        dense = sum(1 for _, s in ss if s["dens"] >= 95)
        over = sum(1 for _, s in ss if s["bal"] > 100 * s["terr"] and s["terr"] > 0)
        P(f"    {t:>6} | {len(ss):>2}({nfill}) | {terr:>7} {100 * terr / land:5.2f} | {bal:>9} {bal / max(terr, 1):6.1f} | {pterr:>7} {100 * pterr / land:5.2f} | "
          f"{boxed} | {dense} | {over}")

    P("[D] 结算拍的全队领土（team.totals）: tick | bot | event | mine | 各队占比% | 我方排名")
    rows = []
    for me, b in bots.items():
        if b.get("teamTotals"):
            rows.append((b["deathTick"] or 0, b))
    for tick, b in sorted(rows, key=lambda x: x[0]):
        tot = {int(k): v for k, v in b["teamTotals"].items()}
        mine = b["team"]
        teams = {k: v for k, v in tot.items() if k != 0}
        rank = 1 + sum(1 for k, v in teams.items() if v > teams.get(mine, 0))
        P(f"    {tick:>6} | {b['name']}({b['me']}) | {b['event']} | T{mine} | " +
          " ".join(f"T{k}={100 * v / land:.1f}" for k, v in sorted(tot.items())) + f" | {rank}/{len(teams)}")

    P("[E] 逐 bot 分段（cls t0-t1 | terr | bal | dens | nb范围 neut范围 | Δcmds Δboats | 行号）")
    for me, b in bots.items():
        segs = segments(b)
        P(f"  -- {b['name']}({me}) T{b['team']} {b['event']}@{b['deathTick']}")
        for s in segs:
            P(f"    {s['cls']} {s['t0']:>5}-{s['t1']:<5} | {s['terr0']:>6}->{s['terr1']:<6} | {s['bal0']:>8}->{s['bal1']:<8} | "
              f"{s['dens0']:>5}->{s['dens1']:<5} | nb{min(s['nb'])}-{max(s['nb'])} neut{min(s['neut'])}-{max(s['neut'])} | "
              f"c+{s['cmds1'] - s['cmds0']} b+{s['boats1'] - s['boats0']} | L{s['line0']}-{s['line1']}")

    dons = F["dons"]
    P(f"[F] DROP30（{len(F['drop30'])} 条）: t0-t1 bot | bal0->bal1 (-%) | terr0->terr1 | 归因 | 无动作应有余额/实际少了 | 每格花费 | 捐款笔数/流出 | Δcmds Δboats | nb/neut | 行号 "
      f"|| 下一段: 余额比公式多(+回流)/少(-) , Δterr | 两段合计净流出/净增领土=每格 || 续攻口径（接上后面不发指令、领土续涨的段）: 到哪一拍 净流出/净增领土=每格")
    for d in F["drop30"]:
        two = "-"
        if d.get("reb") is not None:
            two = f"{d['reb']:+d} , {d['dterr2']:+d} | {d['net2']}/{d['px2']}={fmt(d['perPx2'])}"
        P(f"    {d['t0']:>5}-{d['t1']:<5} {d['name']}({d['me']}) | {d['bal0']}->{d['bal1']} (-{d['dropPct']:.0f}%) | {d['terr0']}->{d['terr1']} | {d['cls']} | "
          f"{d['expNoAct']}/{d['gone']} | {fmt(d['perPx'])} | {d['donN']}/{d['donOut']} | c+{d['dcmds']} b+{d['dboats']} | "
          f"nb{d['nb0']}>{d['nb1']} neut{d['neut0']}>{d['neut1']} | L{d['line0']}-{d['line1']} || {two}"
          + (f" || →{d['epiEnd']} {d['epiNet']}/{d['epiPx']}={fmt(d['epiPerPx'])}" if d.get("epiSegs") else ""))

    P(f"[G] 捐款账本（{len(dons)} 笔）: t donor->recv kind pct | myBal 税 到账(受上限夹后) | 受方terr/bal | 额度 已用+本笔/上限 模型拒? | 下次余额观测 → 判定 | dMe dAlly boxedIn | 行号")
    for d in dons:
        nx = d.get("nextObs")
        nxs = f"t{nx['t']} bal={nx['bal']} (拒应{nx['expRej']} 成应{nx['expAcc']})" if nx else "-"
        P(f"    {d['t']:>5} {F['name_of'].get(d['donor'])}({d['donor']})->{d['allyName']}({d['ally']}) {d['kind']} pct={d['pct']} | "
          f"{d['myBal']} 税{d['fee']} 到{d['amountEff']} | {fmt(d['recvTerr'])}/{fmt(d['recvBal'])} | "
          f"{d['usedBefore']}+{d['cost']}/{d['cap']} {'模型拒' if d['modelRej'] else '模型过'}{'(免)' if d['free'] else ''} | {nxs} → {d['obsVerdict']} | "
          f"{d['dMe']} {fmt(d['dAlly'])} {d['boxedIn'] or '-'} | L{d['line']}")
    acc = [d for d in dons if d["accepted"]]
    P(f"    小结: 日志 {len(dons)} 笔；观测判成交 {sum(1 for d in dons if d['obsVerdict'] == 'ACC')}，观测判拒 {sum(1 for d in dons if d['obsVerdict'] == 'REJ')}，"
      f"判不了 {sum(1 for d in dons if d['obsVerdict'] == '?')}；额度模型判拒 {sum(1 for d in dons if d['modelRej'])}；"
      f"把「没判拒」的全算成交：到账上限 {sum(d['amountEff'] for d in acc)}，税上限 {sum(d['fee'] for d in acc)}")

    P("[H] 其它事件")
    for me, b in bots.items():
        for a in b["assists"]:
            P(f"    ASSIST t={a['t']} {b['name']}({me}) poke enemy={a['enemy']}({a['enemyName']}) for ally={a['ally']}({a['allyName']}) L{a['line']}")
    icp = sorted([(i["t"], b["name"], me, i) for me, b in bots.items() for i in b["intercepts"]])
    for t, nm, me, i in icp:
        P(f"    INTERCEPT t={t} {nm}({me}) pct={i['pct']} boat={i['boatId']} owner={i['owner']}({i['ownerName']}) troops={i['boatTroops']} L{i['line']}")
    for me, b in bots.items():
        for p in b["peaces"]:
            P(f"    PEACE t={p['t']} {b['name']}({me}) teamLand={p['teamLand']}% L{p['line']}")

    P("[I] 死亡链: bot | 峰值@拍 | 末 4 条快照 t:terr/bal/dens/nb/neut | 结算")
    for me, b in bots.items():
        tk = b["ticks"]
        if not tk:
            P(f"    {b['name']}({me}): 无快照；{b['event']}@{b['deathTick']}")
            continue
        pk = max(tk, key=lambda s: s["terr"])
        last = " ; ".join(f"{s['t']}:{s['terr']}/{s['bal']}/{s['dens']}/{s['nb']}/{s['neut']}" for s in tk[-4:])
        P(f"    {b['name']}({me}) T{b['team']} | {pk['terr']}@{pk['t']} | {last} | {b['event']}@{b['deathTick']} place={b['place']} "
          f"lastTerr={b.get('lastTerritory')} alive={b.get('alivePlayers')}")

    P("[J] 停滞统计: bot | 快照数 | 被围(nb=0&neut=0) | 其中dens>=95 | 无敌邻(nb=0) | dens>=95 | 超软上限(bal>100*terr) | 最长持平段 t0-t1 (terr, bal0->bal1)")
    for me, b in bots.items():
        tk = b["ticks"]
        if not tk:
            continue
        boxed = [s for s in tk if s["nb"] == 0 and s["neut"] == 0]
        segs = [s for s in segments(b) if s["cls"] == "H"]
        lh = max(segs, key=lambda s: s["t1"] - s["t0"]) if segs else None
        lhs = f"{lh['t0']}-{lh['t1']} ({lh['terr0']}, {lh['bal0']}->{lh['bal1']})" if lh else "-"
        P(f"    {b['name']}({me}) | {len(tk)} | {len(boxed)} | {sum(1 for s in boxed if s['dens'] >= 95)} | {sum(1 for s in tk if s['nb'] == 0)} | "
          f"{sum(1 for s in tk if s['dens'] >= 95)} | {sum(1 for s in tk if s['terr'] > 0 and s['bal'] > 100 * s['terr'])} | {lhs}")

    P("[K] 开局: bot | spawn | minAllyDist/voronoi | HL-OPENING (cyc:t rings spend/bal terr) | 早期快照 t:terr/nb/neut")
    for me, b in bots.items():
        ops = " ".join(f"{x['cyc']}:{x['t']} r{x['rings']} {x['spend']}/{x['bal']} T{x['terr']}" for x in b["openings"])
        early = " ".join(f"{s['t']}:{s['terr']}/{s['nb']}/{s['neut']}" for s in b["ticks"] if s["t"] <= 900)
        si = b.get("spawnInfo") or {}
        P(f"    {b['name']}({me}) | {b['spawn']} | {si.get('minAllyDist')}/{si.get('voronoi')} | {ops} | {early}")
    for oc_ in F["ochk"][-1:]:
        P(f"    OPENING-CHECK@{oc_['tick']} L{oc_['line']}: " + " ".join(f"{i['name']}={i['terr']}(sent{i['sent']})" for i in oc_["items"]))

    P("[M] 失地/阵亡时刻的队友状态: 受害号 | 开始失地拍(峰值后首个 S 段) → 结局拍 | 受害号在开始失地时 terr/bal/dens | 当时同队编队友 (name:dens/bal千) | 其中 dens>=106 / >=65 / >=40 的个数 | 窗口内全队对它成交捐款笔数/到账")
    for me, b in bots.items():
        tk = b["ticks"]
        if not tk or b["event"] != "died":
            continue
        pk = max(tk, key=lambda s: s["terr"])
        ssegs = [s for s in segments(b) if s["cls"] == "S" and s["t0"] >= pk["t"]]
        t_start = ssegs[0]["t0"] if ssegs else pk["t"]
        v = snap_at(b, t_start, 0)
        mates = []
        for me2, b2 in bots.items():
            if me2 == me or b2["team"] != b["team"]:
                continue
            s2 = snap_at(b2, t_start, 0)
            if s2 and s2["terr"] >= 100:
                mates.append((b2["name"], s2))
        dn = [d for d in dons if d["ally"] == me and t_start <= d["t"] <= (b["deathTick"] or 10 ** 9) and d["accepted"]]
        P(f"    {b['name']}({me}) | {t_start} → {b['deathTick']} | {v['terr']}/{v['bal']}/{v['dens']} | " +
          " ".join(f"{n}:{s['dens']:.0f}/{s['bal'] // 1000}k" for n, s in mates) +
          f" | {sum(1 for _, s in mates if s['dens'] >= 106)}/{sum(1 for _, s in mates if s['dens'] >= 65)}/{sum(1 for _, s in mates if s['dens'] >= 40)}"
          f" | {len(dn)}/{sum(d['amountEff'] for d in dn)}")

    inf = F.get("inflow") or []
    P(f"[N] 回流/额外入账（{len(inf)} 段，余额比「不动只滚利息」多 >10% 且 >5000）: t0-t1 bot | terr0->terr1 | bal0->bal1 | 公式应有 | 多出 | 其中已知成交捐款到账(笔数) | Δcmds Δboats | 行号")
    for x in inf:
        P(f"    {x['t0']:>5}-{x['t1']:<5} {x['name']}({x['me']}) | {x['terr0']}->{x['terr1']} | {x['bal0']}->{x['bal1']} | {x['exp']} | +{x['extra']} | "
          f"{x['donIn']}({x['donN']}) | c+{x['dcmds']} b+{x['dboats']} | L{x['line0']}-{x['line1']}")

    rel, outl = F["idle"]
    if rel:
        srt = sorted(abs(x) for x in rel)
        P(f"[L] 闲置段收支核对（Δcmds=0、Δboats=0、领土不变的相邻快照 {len(rel)} 段）：|实际/公式-1| 中位数 {100 * srt[len(srt) // 2]:.2f}%，"
          f"90 分位 {100 * srt[int(0.9 * (len(srt) - 1))]:.2f}%；离群（>3% 且 >500 兵）{len(outl)} 段：")
        for x in sorted(outl, key=lambda x: (x["t0"], x["me"])):
            P(f"    {x['t0']}-{x['t1']} {x['name']}({x['me']}) terr={x['terr']} bal {x['bal0']}->{x['bal1']} 公式应 {x['exp']} 残差 {x['resid']:+d} ({100 * x['rel']:+.1f}%) nb={x['nb']} L{x['line0']}-{x['line1']}")
    return "\n".join(o)


def full(mid, room=None):
    F = build(mid, room)
    F["dons"] = donation_ledger(F)
    F["drop30"] = drop30(F, F["dons"])
    F["idle"] = idle_check(F)
    F["inflow"] = inflow_check(F, F["dons"])
    return F


def main():
    mid = sys.argv[1]
    room = int(sys.argv[sys.argv.index("--room") + 1]) if "--room" in sys.argv else None
    F = full(mid, room)
    text = digest(F)
    od = os.path.join(L.OUT, mid)
    os.makedirs(od, exist_ok=True)
    # 多房间的包：主房间写 digest.txt / facts.json，其它房间写 digest_room<N>.txt / facts_room<N>.json
    suf = "" if (room is None or F.get("rooms") is None or room == L.room_label_map(mid)[1]["_main"]) else f"_room{room}"
    with open(os.path.join(od, f"digest{suf}.txt"), "w", encoding="utf-8") as f:
        f.write(text + "\n")
    slim = dict(card=F["card"], notes=F["notes"], unresolved=F["unresolved"],
                bots={str(me): {k: v for k, v in b.items() if k not in ("slow",)} for me, b in F["bots"].items()},
                dons=F["dons"], drop30=F["drop30"], ochk=F["ochk"], inflow=F["inflow"])
    with open(os.path.join(od, f"facts{suf}.json"), "w", encoding="utf-8") as f:
        json.dump(slim, f, ensure_ascii=False)
    if "--quiet" not in sys.argv:
        print(text)
    else:
        print(f"{mid}: digest {len(text.splitlines())} 行 -> {od}/digest{suf}.txt")


if __name__ == "__main__":
    main()
