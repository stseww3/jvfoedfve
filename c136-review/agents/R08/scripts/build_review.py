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
    bots, land = F["bots"], F["land"]
    ss = [(b, facts.snap_at(b, t, 0)) for b in bots.values()]
    ss = [(b, s) for b, s in ss if s]
    if not ss:
        return None
    terr = sum(s["terr"] for _, s in ss)
    bal = sum(s["bal"] for _, s in ss)
    prim = F["primary"]
    pt = dict(t=t, src=src, botsWithSnapshot=len(ss), sqTerr=terr, sqSharePct=round(100 * terr / land, 2), sqBal=bal,
              sqDens=round(bal / max(terr, 1), 1),
              boxedIn=sum(1 for _, s in ss if s["nb"] == 0 and s["neut"] == 0),
              overSoftCap=sum(1 for _, s in ss if s["terr"] > 0 and s["bal"] > 100 * s["terr"]))
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
        pk = max(all_t, key=lambda x: sum(s["terr"] for b in bots.values() for s in [facts.snap_at(b, x, 0)] if s))
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
        if dt in pts:
            pts[dt].setdefault("events", []).append(base["event"])
        else:
            pts[dt] = base
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
    result = "won" if oc["primaryTeamWon"] else "lost"
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
    tr = load_truth(mid)
    if tr:
        truth, T = tr
        for pt in doc["timeline"]:
            if pt["t"] <= T.end + 30:
                pt["truth"] = truth.timeline_point(T, pt["t"])
            if str(pt.get("event", "")).endswith(" left"):
                pt["note"] = "结果表里的拍是掉线号冻结的本地拍；录像里真正的离开拍见 deaths[].truth.engineLeftTick"
        if doc["timeline"] and doc["timeline"][-1]["t"] < T.end:
            doc["timeline"].append(dict(t=T.end, src="真引擎重演的最后一拍", truth=truth.timeline_point(T, T.end)))
        for d in doc["deaths"]:
            if isinstance(d.get("me"), int) and d["me"] < T.H:
                d["truth"] = truth.death_summary(T, d["me"])
        doc["context"]["truthSource"] = dict(replayFrom=T.R.get("replayFrom"), peer=T.R.get("peer"), engineEndTick=T.end,
                                             trajRowsExact=f"{T.R['validate']['bothExact']}/{T.R['validate']['rows']}")
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
