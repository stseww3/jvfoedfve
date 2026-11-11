#!/usr/bin/env python3
"""build_review.py — 把「机械事实」和「人工分析」合成一份复盘 JSON，并用联络员的 collect-reviews.py 清单自检。

    python3 c136-review/agents/R08/scripts/build_review.py <matchId> [...]

输入：
  - 机械部分：facts.py 从对局包算出的 context / outcome / timeline / deaths 骨架；
  - 分析部分：scripts/reviews_src/<matchId>.py 里的字典 R（phases、turningPoints、decisions、deathNotes ……）。
输出：c136-review/agents/R08/reviews/<matchId>.json；若同目录已有 <matchId>.md 一并做行数与措辞检查。
"""
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "reviews_src"))
import facts  # noqa: E402
import r08lib as L  # noqa: E402

ROOT = os.path.dirname(HERE)
REVIEWS = os.path.join(ROOT, "reviews")
STRATEGY = {"squad8": "v27-team-g09.js", "squad20": "v27-team-c110.js", "squad10": "v27-team-c116.js"}


def load_checker():
    p = os.path.normpath(os.path.join(ROOT, "..", "..", "tools", "collect-reviews.py"))
    spec = importlib.util.spec_from_file_location("collect_reviews", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def team_shares(b, land):
    tot = {int(k): v for k, v in (b.get("teamTotals") or {}).items()}
    if not tot:
        return None
    mine = b["team"]
    enemies = {k: v for k, v in tot.items() if k not in (0, mine)}
    top = max(enemies.items(), key=lambda kv: kv[1]) if enemies else (None, 0)
    return dict(mineTeam=mine, mineSharePct=round(100 * tot.get(mine, 0) / land, 2), topEnemyTeam=top[0],
                topEnemySharePct=round(100 * top[1] / land, 2),
                allPct={f"T{k}": round(100 * v / land, 1) for k, v in sorted(tot.items())})


def squad_point(F, t, src="HL-TICK"):
    """t 拍的编队合计。某个号这一拍的日志行丢了（前后都有快照）就沿用它的前一条，并记在 botsCarriedForward 里。"""
    bots, land = F["bots"], F["land"]
    sf = [(b,) + facts.snap_fill(b, t) for b in bots.values()]
    carried = sum(1 for _, s, f in sf if s and f)
    ss = [(b, s) for b, s, f in sf if s]
    if not ss:
        return None
    terr = sum(s["terr"] for _, s in ss)
    bal = sum(s["bal"] for _, s in ss)
    prim = F["primary"]
    pt = dict(t=t, src=src, botsWithSnapshot=len(ss), sqTerr=terr, sqSharePct=round(100 * terr / land, 2), sqBal=bal,
              sqDens=round(bal / max(terr, 1), 1),
              boxedIn=sum(1 for _, s in ss if s["nb"] == 0 and s["neut"] == 0),
              overSoftCap=sum(1 for _, s in ss if s["terr"] > 0 and s["bal"] > 100 * s["terr"]))
    if carried:
        pt["botsCarriedForward"] = carried
    if len(F["card"].get("teamSplitCounts") or {}) > 1:
        pterr = sum(s["terr"] for b, s in ss if b["team"] == prim)
        pt["primaryTeamBotsTerr"] = pterr
        pt["primaryTeamBotsSharePct"] = round(100 * pterr / land, 2)
    return pt


def auto_timeline(F):
    bots, land, end = F["bots"], F["land"], F["endTick"]
    pts = {}
    all_t = sorted({s["t"] for b in bots.values() for s in b["ticks"]})
    # 开局：没有 HL-TICK 的拍用 HL-OPENING（每个号在该拍之前最近一条开局指令时的领土）和 OPENING-CHECK
    first_tick = all_t[0] if all_t else 10 ** 9
    for target in (90, 270, 450):
        if target >= first_tick:
            continue
        terr, n = 0, 0
        for b in bots.values():
            ops = [o for o in b["openings"] if o["t"] <= target + 20]
            if ops:
                terr += ops[-1]["terr"]
                n += 1
        if n:
            pts[target] = dict(t=target, src="HL-OPENING(各号最近一条开局指令时的领土)", botsWithSnapshot=n, sqTerr=terr,
                               sqSharePct=round(100 * terr / land, 3))
    for oc in F["ochk"][-1:]:
        terr = sum(i["terr"] for i in oc["items"])
        pts[oc["tick"]] = dict(t=oc["tick"], src=f"OPENING-CHECK L{oc['line']}", botsWithSnapshot=len(oc["items"]), sqTerr=terr,
                               sqSharePct=round(100 * terr / land, 3), allOk=all(i["ok"] == "OK" for i in oc["items"]))
    want = [90, 180, 270, 450, 630, 900, 1260, 1530, 1800, 2070, 2520, 3060, 3510, 4050, 4500, 5040, 6030]
    t = 7020
    while t < end + 90:
        want.append(t)
        t += 990
    for w in want:
        near = [x for x in all_t if abs(x - w) <= 45]
        if near:
            x = min(near, key=lambda v: abs(v - w))
            p = squad_point(F, x)
            if p:
                pts.setdefault(x, p)
    if all_t:
        pts.setdefault(all_t[-1], squad_point(F, all_t[-1]))
        # 编队份额峰值
        pk = max(all_t, key=lambda x: sum(s["terr"] for b in bots.values() for s in [facts.snap_fill(b, x)[0]] if s))
        p = squad_point(F, pk)
        p["note"] = "编队领土份额峰值"
        pts[pk] = {**pts.get(pk, {}), **p}
    # 结算拍：全队份额
    for b in bots.values():
        if b.get("deathTick") is None:
            continue
        ts = team_shares(b, land)
        dt = int(b["deathTick"])
        prev = [x for x in all_t if x <= dt]
        base = dict(squad_point(F, prev[-1])) if prev else {}
        base.update(t=dt, src=f"RESULT L{b['resLine']} + 最近快照 t={prev[-1] if prev else '-'}",
                    event=f"{b['name']} {b['event']}")
        if ts:
            base["teamTotals"] = ts
        # 同一时刻（±10 拍）有 ≥2 个号写了带领土的结果行（left / end）：结果行自己的合计比「最近快照」准
        grp = [x for x in bots.values() if x.get("deathTick") is not None and abs(int(x["deathTick"]) - dt) <= 10
               and x.get("event") != "died" and isinstance(x.get("resTerritory"), (int, float))]
        if len(grp) >= 2:
            rt = int(sum(x["resTerritory"] for x in grp))
            base["resultRows"] = dict(bots=len(grp), sqTerr=rt, sqSharePct=round(100 * rt / land, 2),
                                      sqBal=int(sum(x.get("resBalance") or 0 for x in grp)),
                                      note="这些号结果行里的 territory / balance 合计（阵亡的号不计）")
        if dt in pts:
            pts[dt].setdefault("events", []).append(base["event"])
        else:
            pts[dt] = base
    # 规程要的锚点（t≈180 / 600 / 1500 / 3000）附近这个房间完全没有数据时，明写一个缺口点（不补数）
    for target, tol in ((180, 120), (600, 150), (1500, 250), (3000, 300)):
        if (end and end < target) or any(abs(x - target) <= tol for x in pts):
            continue
        before = [x for x in all_t if x < target]
        after = [x for x in all_t if x > target]
        pts[target] = dict(t=target, src="无数据", dataGap=True, botsWithSnapshot=0, sqTerr=None, sqSharePct=None,
                           note=f"这个房间在 t≈{target} 没有任何快照或开局行（之前最近一条 t={before[-1] if before else '无'}，之后最近一条 t={after[0] if after else '无'}）；只标缺口，不补数")
    return [pts[k] for k in sorted(pts)]


def auto_deaths(F, notes):
    out = []
    for me, b in F["bots"].items():
        if b["event"] not in ("died",) and not (notes.get(b["name"]) or notes.get(me)):
            continue
        tk = b["ticks"]
        pk = max(tk, key=lambda s: s["terr"]) if tk else None
        d = dict(bot=b["name"], me=me, labels=b["labels"], team=b["team"], event=b["event"], tick=b["deathTick"], place=b["place"],
                 resultPeak=b["resPeak"], logPeakTerr=pk["terr"] if pk else None, logPeakTick=pk["t"] if pk else None,
                 lastSnapshots=[dict(t=s["t"], terr=s["terr"], bal=s["bal"], dens=s["dens"], nb=s["nb"], neut=s["neut"], cmds=s["cmds"])
                                for s in tk[-4:]],
                 donationsReceivedLogged=sum(1 for d2 in F["dons"] if d2["ally"] == me),
                 donationsReceivedAccepted=sum(1 for d2 in F["dons"] if d2["ally"] == me and d2["accepted"]),
                 donationsGivenLast500=sum(1 for d2 in F["dons"] if d2["donor"] == me and b["deathTick"] and d2["t"] >= b["deathTick"] - 500),
                 resultLine=b["resLine"])
        extra = notes.get(b["name"]) or notes.get(me) or {}
        d.update(extra)
        out.append(d)
    out.sort(key=lambda d: (d["tick"] or 10 ** 9))
    return out


def load_truth(mid):
    """有真引擎重演产物（out/<mid>/resim.json）的局，把全场真值并进 timeline / deaths。"""
    if not os.path.exists(os.path.join(ROOT, "out", mid, "resim.json")):
        return None
    import truth
    return truth, truth.Truth(mid)


def merge_truth(mid, F, timeline, deaths):
    """把真引擎重演的全场真值并进 timeline / deaths；只在录像属于这个房间时做。返回 truthSource 或 None。"""
    tr = load_truth(mid) if F.get("hasTruth") else None
    if not tr:
        return None
    truth, T = tr
    for pt in timeline:
        if pt["t"] <= T.end + 30:
            pt["truth"] = truth.timeline_point(T, pt["t"])
        if str(pt.get("event", "")).endswith(" left"):
            pt["note"] = "结果表里的拍是掉线号冻结的本地拍；录像里真正的离开拍见 deaths[].truth.engineLeftTick"
    if timeline and timeline[-1]["t"] < T.end:
        timeline.append(dict(t=T.end, src="真引擎重演的最后一拍", truth=truth.timeline_point(T, T.end)))
    for d in deaths:
        me = d.get("meReal") if d.get("meReal") is not None else d.get("me")
        if isinstance(me, int) and me < T.H:
            d["truth"] = truth.death_summary(T, me)
    return dict(replayFrom=T.R.get("replayFrom"), peer=T.R.get("peer"), engineEndTick=T.end,
                trajRowsExact=f"{T.R['validate']['bothExact']}/{T.R['validate']['rows']}")


def side_room(mid, r, R):
    """多房间的包：主房间之外的房间单独出一节（骨架同主房间：身份、时间线、死亡链；有录像就并真值）。"""
    F = facts.build(mid, room=r)
    F["dons"] = facts.donation_ledger(F)
    card = F["card"]
    oc = card["outcome"]
    rm = (F.get("rooms") or {}).get(r) or {}
    notes = (R.get("sideRoomDeathNotes") or {}).get(r, {})
    tl = auto_timeline(F)
    deaths = auto_deaths(F, notes)
    for d in deaths:
        b = F["bots"].get(d["me"])
        if b is not None and b.get("meReal") is not None:
            d["meReal"] = b["meReal"]
    ts = merge_truth(mid, F, tl, deaths)
    out = dict(roomIdx=r, physRoom=rm.get("physRoom"), startUtc=rm.get("startUtc"), mapLand=F["land"], seededPlayers=card.get("seededPlayers"),
               mode=rm.get("mode"), endTick=oc["endTick"], winnerTeam=oc["winnerTeam"], primaryTeam=card["ourPrimaryTeam"],
               primaryTeamWon=oc["primaryTeamWon"], peakSquadLandShare=oc["peakSquadLandShare"], ourFinalTeamShare=oc["ourFinalTeamShare"],
               squad=[dict(me=me, meReal=b.get("meReal"), name=b["name"], labels=b["labels"], team=b["team"], spawn=b["spawn"],
                           spawnResolves=b.get("spawnCount", 0), event=b["event"], result=b["result"], tick=b["deathTick"], place=b["place"])
                      for me, b in F["bots"].items()],
               timeline=tl, deaths=deaths)
    if ts:
        out["truthSource"] = ts
    out.update((R.get("sideRoomExtra") or {}).get(r, {}))
    return out


def donfit_summary(mid, room):
    """donfit.py 的定案（余额序列拟合）；没有跑过就返回 None。"""
    p = os.path.join(ROOT, "out", mid, "donfit.json" if room is None else f"donfit_room{room}.json")
    if not os.path.exists(p):
        return None
    rows = json.load(open(p, encoding="utf-8"))["rows"]
    ex = [r for r in rows if r["status"] == "EXEC"]
    return dict(method="donfit.py：拿捐出方的余额观测序列（HL-TICK + 每条 HL-DONATE 的 myBal）逐段拟合，在途的单子允许晚落地；"
                       "成交几笔由余额拟合定，同样大小的候选里先挑不违反引擎受捐额度的、再挑最新发的；"
                       "同一个快照窗里还有攻击/船时只收『整单、额度内』的拟合，其余记判不了",
                quotaConflicts=sum(1 for r in ex if r.get("quotaOver")),
                logged=len(rows), executed=len(ex), notExecuted=sum(1 for r in rows if r["status"] == "NOEXEC"),
                undetermined=sum(1 for r in rows if r["status"] == "AMB"),
                delivered=sum(r.get("amt") or 0 for r in ex), tax=sum(r.get("fee") or 0 for r in ex),
                clippedByReceiverCap=sum(1 for r in ex if r.get("clip")),
                lagAtLeast20=sum(1 for r in ex if (r.get("lagLo") or 0) >= 20),
                refires=sum(1 for r in rows if r.get("dupOf") is not None),
                old20TickRuleRejectedButExecuted=sum(1 for r in ex if r.get("oldVerdict") == "REJ"))


def hard_ledgers(mid):
    """统筹广播 0007 的两本硬账：lagledger.py（延迟 / 执行延迟）和 landcap.py（好地实际抢到多少）的汇总 JSON，原样并进 ledger。"""
    out = {}
    for key, fn, src in (("latencyLedger", "lagledger_sum.json", "scripts/lagledger.py [GA]~[GG]（out/<局>/lagledger.txt）"),
                         ("latencyLedgerPeer", "lagledger_sum_peer.json", "scripts/lagledger.py --side peer"),
                         ("landCapture", "landcap_sum.json", "scripts/landcap.mjs + landcap.py [KA]~[KF]（out/<局>/landcap.txt）")):
        p = os.path.join(ROOT, "out", mid, fn)
        if os.path.exists(p):
            d = json.load(open(p, encoding="utf-8"))
            d["src"] = src
            out[key] = d
    return out


def build(mid):
    F = facts.build(mid)
    F["dons"] = facts.donation_ledger(F)
    F["drop30"] = facts.drop30(F, F["dons"])
    card = F["card"]
    src = os.path.join(HERE, "reviews_src", f"{mid}.py")
    spec = importlib.util.spec_from_file_location(f"src_{mid}", src)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    R = mod.R
    oc = card["outcome"]
    label = oc["resultLabel"]
    # 没有 end 行、领先的队也没到引擎的收尾线（facts.py OPEN_LEAD_SHARE）：对局没打完，不算赢也不算输
    result = "open" if label == "open" else ("won" if oc["primaryTeamWon"] or oc.get("ffaWin") else "lost")
    acc = [d for d in F["dons"] if d["accepted"]]
    doc = dict(
        matchId=mid, reviewer="R08", protocol="v2.0",
        context=dict(cohort=card["cohort"], strategyFile=STRATEGY.get(card["cohort"]), mapId=card["mapId"], mapSeed=card["mapSeed"],
                     mapLand=card["mapLand"], mode=card["mode"], seededPlayers=card["seededPlayers"], nominalTeams=card["nominalTeams"],
                     actualTeams=card["actualTeams"], baseWinExpectation=card["baseWinExpectation"], squadBots=card["squadBots"],
                     ourPrimaryTeam=card["ourPrimaryTeam"], teamSplitCounts=card["teamSplitCounts"],
                     teamSplit=len(card["teamSplitCounts"] or {}) > 1, sameMatchPeer=card.get("sameMatchPeer"),
                     dataCompleteness=card["dataCompleteness"], anomaliesSummary=card["anomaliesSummary"],
                     squad=[dict(me=me, name=b["name"], labels=b["labels"], team=b["team"], teamInferred=b.get("teamInferred", False),
                                 spawn=b["spawn"], spawnResolves=b.get("spawnCount", 0), spawnInfo=b.get("spawnInfo"))
                            for me, b in F["bots"].items()],
                     **R.get("contextExtra", {})),
        outcome=dict(result=result, resultLabel=label, primaryTeamWon=oc["primaryTeamWon"], anyBotWon=oc["anyBotWon"],
                     winnerTeam=oc["winnerTeam"], endTick=oc["endTick"], peakSquadLandShare=oc["peakSquadLandShare"],
                     peakPrimaryTeamShareSeen=oc["peakPrimaryTeamShareSeen"], ourFinalTeamShare=oc["ourFinalTeamShare"],
                     placements=[dict(bot=b["name"], me=me, team=b["team"], event=b["event"], result=b["result"], tick=b["deathTick"],
                                      place=b["place"]) for me, b in F["bots"].items()],
                     **({"openGame": oc["openGame"]} if oc.get("openGame") else {}),
                     **R.get("outcomeExtra", {})),
        timeline=auto_timeline(F),
        phases=R["phases"],
        turningPoints=R["turningPoints"],
        deaths=auto_deaths(F, R.get("deathNotes", {})),
        ledger=dict(drop30Count=len(F["drop30"]),
                    drop30ByClass={c: sum(1 for d in F["drop30"] if d["cls"] == c) for c in sorted({d["cls"] for d in F["drop30"]})},
                    donationsLogged=len(F["dons"]),
                    donationsObservedAccepted=sum(1 for d in F["dons"] if d["obsVerdict"] == "ACC"),
                    donationsObservedRejected=sum(1 for d in F["dons"] if d["obsVerdict"] == "REJ"),
                    donationsUndetermined=sum(1 for d in F["dons"] if d["obsVerdict"] == "?"),
                    donationsModelRejected=sum(1 for d in F["dons"] if d["modelRej"]),
                    note="观测判定=拿捐出方下一次已知余额和「被拒/成交」两个预期比；Undetermined=判不了。下面两项按「未判拒即成交」计，是上限。",
                    donatedArrivedUpperBound=sum(d["amountEff"] for d in acc), donationTaxUpperBound=sum(d["fee"] for d in acc),
                    cardLikelyRejected=(card.get("anomaliesSummary") or {}).get("likelyRejectedTransfers"),
                    **({"donfit": donfit_summary(mid, None)} if donfit_summary(mid, None) else {}),
                    **hard_ledgers(mid),
                    **R.get("ledgerExtra", {})),
        decisions=R["decisions"],
        newPatterns=R.get("newPatterns", []),
        lossArchetype=R["lossArchetype"],
        archetypeNote=R.get("archetypeNote", ""),
        winnerNotes=R["winnerNotes"],
        wentWell=R["wentWell"],
        unknowns=R["unknowns"],
        mechanicsQuestions=R["mechanicsQuestions"],
        scripts=R["scripts"],
        confidenceOverall=R["confidenceOverall"],
    )
    for k in ("peerComparison", "teamSplitNotes"):
        if k in R:
            doc[k] = R[k]
    ts = merge_truth(mid, F, doc["timeline"], doc["deaths"])
    if ts:
        doc["context"]["truthSource"] = ts
    if F.get("rooms") and len(F["rooms"]) > 1:
        doc["context"]["roomIdx"] = F["room"]
        doc["context"]["roomsInBundle"] = len(F["rooms"])
        doc["context"]["cardOriginal"] = card.get("cardOriginal")
        doc["sideRooms"] = [side_room(mid, r, R) for r in sorted(F["rooms"]) if r != F["room"]]
    os.makedirs(REVIEWS, exist_ok=True)
    out = os.path.join(REVIEWS, f"{mid}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    md_path = os.path.join(REVIEWS, f"{mid}.md")
    md = open(md_path, encoding="utf-8").read() if os.path.exists(md_path) else None
    chk = load_checker()
    fails, stats = chk.check_review(doc, md)
    print(f"{mid}: 写出 {out}（{os.path.getsize(out)} 字节）；清单未过 {len(fails)} 项：{fails}")
    print(f"    统计 {stats}")
    if md is not None:
        print(f"    md 行数 {md.count(chr(10))}")
    return fails


if __name__ == "__main__":
    bad = 0
    for m in sys.argv[1:]:
        bad += len(build(m))
    sys.exit(1 if bad else 0)
