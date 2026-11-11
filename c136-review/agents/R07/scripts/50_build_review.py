#!/usr/bin/env python3
"""50_build_review.py — 把机械数据和手写分析合成 reviews/<matchId>.json，并按 collect-reviews.py 的清单自查（R07 v2.0）。

输入：
  out/<matchId>/digest.json            （40_game_digest.py）
  out/<matchId>/patterns.json          （42_patterns.py）
  out/<matchId>/donation_ledger.json   （30_donation_ledger.py，可缺）
  review_src/<matchId>.py（或 .json）  手写分析（Python 字典 SRC）：phases / turningPoints / deaths(cause 等) / decisions / newPatterns /
                                        lossArchetype / winnerNotes / wentWell / unknowns / mechanicsQuestions / confidenceOverall /
                                        timelineTs（要放进时间线的拍号）/ timelineNotes（{拍号: 备注}）/ contextExtra
输出：reviews/<matchId>.json；并检查 reviews/<matchId>.md 的行数。

时间线里的数字全部来自 digest.json：
  alive = 尚未结算的我方号数；logging = 该拍有 HL-TICK 的号数（策略停摆的号没有快照，squad* 只统计 logging 的号）；
  squadLandShare / squadTroops = 有快照的号合计；teamLandShare / teamRank / topEnemy* 只在 ±60 拍内有结算快照（results.teamTotals）时填写，否则为 null。
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
ARCHETYPES = {"early-wipe", "never-grew", "mid-collapse", "lead-thrown", "outscaled", "external", "win"}
VERDICTS = {"error", "good", "unclear"}
STATEMENT_TYPES = {"observed", "inferred", "guess"}
REQUIRED_TOP = ["matchId", "reviewer", "context", "outcome", "timeline", "phases", "turningPoints", "deaths", "decisions", "newPatterns",
                "lossArchetype", "winnerNotes", "wentWell", "unknowns", "mechanicsQuestions", "scripts", "confidenceOverall"]
PROPOSAL_HINTS = re.compile(r"(建议把|建议将|应该?改成|应调[到整为]|调到\s*\d|改为\s*\d|提高到\s*\d|降低到\s*\d)")


def near(points, target, tol):
    return any(abs(p - target) <= tol for p in points)


def check_review(doc, md_text):
    fails = []
    for k in REQUIRED_TOP:
        if k not in doc:
            fails.append(f"缺字段 {k}")
    outcome = doc.get("outcome") or {}
    result = outcome.get("result")
    end_tick = outcome.get("endTick") or 0
    ts = [p.get("t") for p in doc.get("timeline") or [] if isinstance(p.get("t"), (int, float))]
    if len(ts) < 8:
        fails.append(f"时间线只有 {len(ts)} 个点")
    for target, tol in ((180, 120), (600, 150), (1500, 250), (3000, 300)):
        if end_tick and end_tick < target:
            continue
        if not near(ts, target, tol):
            fails.append(f"时间线缺 t≈{target}")
    if end_tick and ts and max(ts) < end_tick - 300:
        fails.append("时间线没有终局点")
    for d in doc.get("deaths") or []:
        if not (d.get("cause") or "").strip():
            fails.append(f"阵亡号 {d.get('bot')} 没写死因")
    tps = doc.get("turningPoints") or []
    if result in ("lost", "over") and not tps:
        fails.append("输局没有转折点")
    for i, tp in enumerate(tps):
        if len(tp.get("evidence") or []) < 3:
            fails.append(f"转折点 {i + 1} 证据不足 3 条")
        pds = tp.get("priorDecisions") or []
        if not pds:
            fails.append(f"转折点 {i + 1} 没有窗口前的决策")
        elif not any((pd.get("codePath") or "").strip() for pd in pds):
            fails.append(f"转折点 {i + 1} 的决策没追到代码路径")
        if tp.get("statementType") not in STATEMENT_TYPES:
            fails.append(f"转折点 {i + 1} 没标观察/推断/猜测")
    decisions = doc.get("decisions") or []
    good = sum(1 for d in decisions if d.get("verdict") == "good")
    if len(decisions) < 10:
        fails.append(f"决策实例只有 {len(decisions)} 条")
    if good < 2:
        fails.append(f"判为「对」的决策只有 {good} 条")
    if [d for d in decisions if d.get("verdict") not in VERDICTS]:
        fails.append("有决策的 verdict 取值不合法")
    if [d for d in decisions if not (d.get("codePath") or "").strip()]:
        fails.append("有决策没有代码路径")
    if [d for d in decisions if not (d.get("patternId") or "").strip()]:
        fails.append("有决策没有模式编号")
    arch = doc.get("lossArchetype")
    if arch not in ARCHETYPES:
        fails.append(f"分型取值不合法：{arch}")
    if result == "won" and arch != "win":
        fails.append("赢局的分型应为 win")
    if result in ("lost", "over") and arch == "win":
        fails.append("输局的分型不能是 win")
    if not (doc.get("winnerNotes") or "").strip():
        fails.append("没写赢家")
    if not doc.get("scripts"):
        fails.append("没列脚本")
    blob = json.dumps(doc, ensure_ascii=False) + "\n" + (md_text or "")
    hints = [blob[max(0, m.start() - 20):m.end() + 20].replace("\n", " ") for m in PROPOSAL_HINTS.finditer(blob)]
    if md_text is None:
        fails.append("缺叙述版 .md")
    else:
        n = md_text.count("\n")
        if n > 160:
            fails.append(f"叙述版 {n} 行（上限 160）")
        if n < 80:
            fails.append(f"叙述版只有 {n} 行（任务卡要求 80~180）")
    return fails, hints


def main():
    mid = sys.argv[1]
    dg = json.load(open(os.path.join(ROOT, "out", mid, "digest.json"), encoding="utf-8"))
    src_py = os.path.join(HERE, "review_src", f"{mid}.py")
    if os.path.exists(src_py):
        sys.path.insert(0, os.path.dirname(src_py))
        ns = {"__file__": src_py}
        exec(compile(open(src_py, encoding="utf-8").read(), src_py, "exec"), ns)  # 手写分析以 Python 字典 SRC 的形式保存
        src = ns["SRC"]
    else:
        src = json.load(open(os.path.join(HERE, "review_src", f"{mid}.json"), encoding="utf-8"))
    pat_path = os.path.join(ROOT, "out", mid, "patterns.json")
    pat = json.load(open(pat_path, encoding="utf-8")) if os.path.exists(pat_path) else {}
    led_path = os.path.join(ROOT, "out", mid, "donation_ledger.json")
    led = json.load(open(led_path, encoding="utf-8")) if os.path.exists(led_path) else {}
    card = dg["card"]
    land = card["mapLand"]
    oc = card["outcome"]
    tts = dg.get("teamTotals") or []
    mine = card.get("ourPrimaryTeam")

    # 有回放的局（A 组）：队伍份额取真引擎重放的真值（60_truth.cjs 的 truth_teams.tsv，每 30 拍一行），不再只靠结算快照
    truth_teams = {}
    tt_path = os.path.join(ROOT, "out", mid, "truth_teams.tsv")
    if os.path.exists(tt_path):
        import csv
        for r in csv.DictReader(open(tt_path, encoding="utf-8"), delimiter="\t"):
            truth_teams.setdefault(int(r["t"]), {})[int(r["team"])] = (int(r["terr"]), int(r["bal"]))

    def team_at(t, tol=60):
        if truth_teams:
            tt = min(truth_teams, key=lambda x: abs(x - t))
            if abs(tt - t) <= 30:
                row = {k: v for k, v in truth_teams[tt].items() if k >= 1}
                if mine in row:
                    order = sorted(row, key=lambda k: -row[k][0])
                    enemies = [k for k in order if k != mine]
                    return {"at": tt, "teamLandShare": round(row[mine][0] / land, 4), "teamRank": order.index(mine) + 1, "nTeams": len(row),
                            "teamTroops": row[mine][1], "topEnemyTeam": enemies[0] if enemies else None,
                            "topEnemyShare": round(row[enemies[0]][0] / land, 4) if enemies else None}
        best = None
        for x in tts:
            if abs(x["t"] - t) <= tol and (best is None or abs(x["t"] - t) < abs(best["t"] - t)):
                best = x
        if not best:
            return None
        sh = best["shares"]
        me_team = str(best["mine"])
        enemies = sorted(((k, v) for k, v in sh.items() if str(k) != me_team), key=lambda kv: -kv[1])
        return {"at": best["t"], "teamLandShare": sh.get(me_team, sh.get(best["mine"])), "teamRank": best["rank"], "nTeams": best["nTeams"],
                "topEnemyTeam": int(enemies[0][0]) if enemies else None, "topEnemyShare": enemies[0][1] if enemies else None}

    # 有回放的局：我方号数与队伍分布以录像头为准（对局卡只统计了有结算行的号）
    squad_n = card.get("squadBots")
    split = card.get("teamSplitCounts")
    tp_path = os.path.join(ROOT, "out", mid, "truth_players.tsv")
    if os.path.exists(tp_path):
        import csv as _csv
        rows = [r for r in _csv.DictReader(open(tp_path, encoding="utf-8"), delimiter="\t") if r.get("squad")]
        if rows:
            squad_n = len(rows)
            split = {}
            for r in rows:
                split[r["team"]] = split.get(r["team"], 0) + 1

    by_t = {x["t"]: x for x in dg["timeline"]}
    timeline = []
    notes = {int(k): v for k, v in (src.get("timelineNotes") or {}).items()}
    for extra in src.get("timelineExtra") or []:
        timeline.append(extra)
    ocheck = dg.get("openingCheck")
    if ocheck:
        timeline.append({"t": ocheck["t"], "alive": ocheck["n"], "logging": ocheck["n"], "squadLandShare": ocheck["share"], "squadTroops": None,
                         "squadDensity": None, "boxedBots": 0, "teamLandShare": None, "teamRank": None, "teamTroops": None,
                         "topEnemyTeam": None, "topEnemyShare": None, "teamSnapshotAt": None,
                         "note": f"来自 [OPENING-CHECK]：{ocheck['n']} 个号领土合计 {ocheck['terrSum']}（单号 {ocheck['terrMin']}~{ocheck['terrMax']}）"})
    for t in src["timelineTs"]:
        x = by_t.get(t)
        if not x:
            raise SystemExit(f"timelineTs 里的 t={t} 不在 digest 时间线里")
        tm = team_at(t)
        timeline.append({"t": t, "alive": x["alive"], "logging": x["logging"], "squadLandShare": x["sqShare"], "squadTroops": x["sqBal"],
                         "squadDensity": x["sqDens"], "boxedBots": x["boxed"],
                         "teamLandShare": tm["teamLandShare"] if tm else None, "teamRank": tm["teamRank"] if tm else None,
                         "teamTroops": tm.get("teamTroops") if tm else None, "topEnemyTeam": tm["topEnemyTeam"] if tm else None, "topEnemyShare": tm["topEnemyShare"] if tm else None,
                         "teamSnapshotAt": tm["at"] if tm else None, "note": notes.get(t, "")})
    timeline.sort(key=lambda p: p["t"])

    final_tt = tts[-1] if tts else None
    our_final = None
    our_rank = None
    if final_tt:
        our_final = final_tt["shares"].get(str(final_tt["mine"]), final_tt["shares"].get(final_tt["mine"]))
        our_rank = final_tt["rank"]
    result = {"won": "won", "lost": "lost"}.get(oc.get("resultLabel"), oc.get("resultLabel"))
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT, timeout=20).stdout.strip()
    except Exception:  # noqa: BLE001
        sha = "unknown"
    doc = {
        "matchId": mid,
        "reviewer": "R07",
        "protocol": "v2.0",
        "summary": src.get("oneLine", ""),
        "context": {
            "time": card.get("timeUtc"), "squad": card.get("cohort"), "bots": squad_n,
            "strategyVersion": src.get("contextExtra", {}).get("strategyVersion", "unknown"),
            "gameVersion": src.get("contextExtra", {}).get("gameVersion", "unknown"),
            "map": f"map{card.get('mapId')} seed{card.get('mapSeed')}", "mapLand": land,
            "teams": card.get("actualTeams"), "nominalTeams": card.get("nominalTeams"), "humans": card.get("seededPlayers"),
            "ourTeam": mine, "teamSplitCounts": split, "baseWinExpectation": card.get("baseWinExpectation"),
            "dataCompleteness": {"results": card["dataCompleteness"].get("results"), "squadLog": card["dataCompleteness"].get("inGameLog"),
                                 "truth": bool(truth_teams), "replayCommands": bool(card["dataCompleteness"].get("replay")),
                                 "tickSnapshots": card["dataCompleteness"].get("tickSnapshots")},
            "contamination": src.get("contextExtra", {}).get("contamination", []),
            "anomaliesSummary": card.get("anomaliesSummary"),
            "notes": src.get("contextExtra", {}).get("notes", ""),
        },
        "outcome": {"result": result, "ourTeamRank": our_rank, "winnerTeam": oc.get("winnerTeam"), "endTick": oc.get("endTick"),
                    "ourFinalShare": our_final if our_final is not None else oc.get("ourFinalTeamShare"),
                    "peakSquadLandShare": oc.get("peakSquadLandShare"), "peakPrimaryTeamShareSeen": oc.get("peakPrimaryTeamShareSeen")},
        "timeline": timeline,
        "phases": src["phases"],
        "turningPoints": src["turningPoints"],
        "deaths": src["deaths"],
        "decisions": src["decisions"],
        "newPatterns": src.get("newPatterns", []),
        "lossArchetype": src["lossArchetype"],
        "winnerNotes": src["winnerNotes"],
        "wentWell": src.get("wentWell", []),
        "unknowns": src.get("unknowns", []),
        "mechanicsQuestions": src.get("mechanicsQuestions", []),
        "drop30Reconciliation": [dict({k: d[k] for k in ("bot", "t0", "t1", "bal0", "bal1", "dropPct", "terr0", "terr1", "dCmds", "dBoats",
                                                          "donOutN", "donOutAmt", "donOutFee", "donInN", "donInAmt", "assistN", "interceptN", "spendLo", "spendHi", "labels")},
                                      note=(src.get("drop30Notes") or {}).get(f"{d['bot']}@{d['t0']}", "")) for d in dg.get("drop30", [])],
        "mechanismChecks": src.get("mechanismChecks", {}),
        "patternCounts": pat.get("patterns", {}),
        "donationLedger": {"total": led.get("total"), "latency": led.get("latency"), "perBot": led.get("bots")} if led else None,
        "scripts": [f"c136-review/agents/R07/scripts/{s}@{sha}" for s in
                    ["r07lib.py", "r07replay.py", "40_game_digest.py", "30_donation_ledger.py", "42_patterns.py", "50_build_review.py", "r07md.py"]
                    + list(src.get("extraScripts", []))]
                   + [f"c136-review/agents/R07/out/{mid}/digest.txt", f"c136-review/agents/R07/out/{mid}/donation_ledger.txt",
                      f"c136-review/agents/R07/out/{mid}/patterns.json"] + list(src.get("extraOutputs", [])),
        "confidenceOverall": src["confidenceOverall"],
    }
    # 自动补全 deaths 的数值字段
    dmap = {d["bot"]: d for d in dg.get("deaths", [])}
    for d in doc["deaths"]:
        a = dmap.get(d["bot"])
        if a:
            d.setdefault("t", a["t"])
            d.setdefault("place", a["place"])
            d.setdefault("peakTerr", a["peak"])
            d.setdefault("lastTerr", a["lastTerr"])
            d.setdefault("balanceAtDeath", a["bal"])
            d.setdefault("densityLast500", [{"t": x["t"], "terr": x["terr"], "bal": x["bal"], "dens": x["dens"]} for x in a["last"]])
            d.setdefault("donIn500", {"n": a["donIn500"][0], "amt": a["donIn500"][1], "rejFlag": a["donIn500"][2]})
            d.setdefault("donOut500", {"n": a["donOut500"][0], "amt": a["donOut500"][1], "fee": a["donOut500"][2]})
            d.setdefault("assistedTimes500", a.get("assistFor500"))
            d.setdefault("assistsSent500", a.get("assistBy500"))
    os.makedirs(os.path.join(ROOT, "reviews"), exist_ok=True)
    out = os.path.join(ROOT, "reviews", f"{mid}.json")
    json.dump(doc, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    md_path = os.path.join(ROOT, "reviews", f"{mid}.md")
    if src.get("narrative"):
        import r07md
        open(md_path, "w", encoding="utf-8").write(r07md.render(doc, src))
    md = open(md_path, encoding="utf-8").read() if os.path.exists(md_path) else None
    fails, hints = check_review(doc, md)
    print(f"wrote {out}: timeline {len(timeline)}, turningPoints {len(doc['turningPoints'])}, deaths {len(doc['deaths'])}, decisions {len(doc['decisions'])}"
          f" (good {sum(1 for d in doc['decisions'] if d['verdict'] == 'good')}, error {sum(1 for d in doc['decisions'] if d['verdict'] == 'error')}, unclear {sum(1 for d in doc['decisions'] if d['verdict'] == 'unclear')}),"
          f" md lines {md.count(chr(10)) if md else None}")
    missing = set(dmap) - {d["bot"] for d in doc["deaths"]} if result != "won" else set()
    died = {b for b, a in dmap.items() if a.get("event") == "died"}
    missing = died - {d["bot"] for d in doc["deaths"]}
    if missing:
        fails.append(f"阵亡号缺死因链: {sorted(missing)}")
    print("CHECK:", "全过" if not fails else "；".join(fails))
    if hints:
        print("疑似参数建议措辞:", hints[:5])


if __name__ == "__main__":
    main()
