#!/usr/bin/env python3
"""audit_hypotheses.py — M2：六大局内假设的红队审计（发现集 123 局）。

输入（全部只读）：
  /agent/repos/c136-data/bundles/<局号>/…           对局包（日志快照、事件、选点、录像）
  /agent/repos/c136-data/src/strategy/*.js           线上策略五个版本
  ../out/rooms/rooms-discovery.json                  本人 M1 的房间/队伍重建
  ../out/engine/discovery/<局号>.json                 engine_probe.cjs 的真引擎探针结果（107 个带录像的包）

输出：
  ../out/hypothesis-audit.json     全部数字
  ../reports/HYPOTHESIS-AUDIT.md   由 hypothesis_audit_template.md 渲染（报告里不手填数字）

用法：
  python3 audit_data.py discovery                                  # 写探针作业单
  bash c136-review/tools/run-heavy.sh node engine_probe.cjs ../out/engine/jobs-discovery.json ../out/engine/discovery
  python3 audit_hypotheses.py                                      # 出 JSON 和报告
"""
from __future__ import annotations

import json
import os
import re
import statistics
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import audit_data as D  # noqa: E402
import baseline_full as BF  # noqa: E402
import c136lib as L  # noqa: E402
import replay as RP  # noqa: E402
import stats as S  # noqa: E402

DATA = "/agent/repos/c136-data"
OUT = os.path.normpath(os.path.join(HERE, "..", "out"))
REPORTS = os.path.normpath(os.path.join(HERE, "..", "reports"))
STRAT = {"Va": "v27-team-c116-va.js", "Vb": "v27-team-c116-vb.js", "Vc": "v27-team-c116.js",
         "c110": "v27-team-c110.js", "g09": "v27-team-g09.js"}
VERS = ["Va", "Vb", "Vc", "c110", "g09"]
VER_LABEL = {"Va": "squad10·Va", "Vb": "squad10·Vb", "Vc": "squad10·Vc", "c110": "squad20·c110", "g09": "squad8·g09"}
FLOOR_CAP = {"Va": 78, "Vb": 88, "Vc": 88, "c110": 88, "g09": 38}
PHASES = ["<1071", "1071–2141", "2142–3212", "3213–4283", "≥4284"]
LOSS = ("LOSS", "LOSS_LIKELY")


def phase(t: int) -> str:
    return "<1071" if t < 1071 else "1071–2141" if t < 2142 else "2142–3212" if t < 3213 else "3213–4283" if t < 4284 else "≥4284"


def wil(k: int, n: int) -> dict:
    if n <= 0:
        return {"k": k, "n": n, "p": None, "lo": None, "hi": None}
    lo, hi = S.wilson(k, n)
    return {"k": k, "n": n, "p": k / n, "lo": lo, "hi": hi}


def q(xs, p):
    xs = sorted(xs)
    if not xs:
        return None
    i = min(len(xs) - 1, max(0, int(round(p * (len(xs) - 1)))))
    return xs[i]


def dist(xs) -> dict:
    xs = [x for x in xs if x is not None]
    if not xs:
        return {"n": 0, "min": None, "p10": None, "p25": None, "med": None, "p75": None, "p90": None, "max": None, "mean": None, "sum": 0}
    return {"n": len(xs), "min": min(xs), "p10": q(xs, .10), "p25": q(xs, .25), "med": q(xs, .50), "p75": q(xs, .75),
            "p90": q(xs, .90), "max": max(xs), "mean": sum(xs) / len(xs), "sum": sum(xs)}


def is_team_room(rec_or_room) -> bool:
    return rec_or_room["outcome"] not in ("NON_TEAM", "NO_PLAY")


# ----------------------------------------------------------------------------
# 装配：对局 + 探针 + 捐款账 + 每条下单的引擎判定
# ----------------------------------------------------------------------------

def verdict_of(ev) -> str:
    """一条下单在某个到达拍的引擎判定（ev = 探针 evals 的一行）。"""
    _, _lag, _B, v, _fee, cost, acc, cap, free, alive_d, ok_rec = ev[:11]
    if not alive_d:
        return "donorDead"
    if not ok_rec:
        return "recGone"
    if v < 1:
        return "recFull"
    if free:
        return "fits"
    if cost > cap:
        return "singleOver"
    if acc + cost > cap:
        return "accOver"
    return "fits"


def prepare() -> list[dict]:
    games = D.load_games("discovery")
    for g in games:
        g["E"] = D.load_engine(g["mid"])
        g["ledger"] = D.build_ledger(g)
        g["rroom"] = g["roomByIdx"].get(g["replayRoom"]) if g["replayRoom"] is not None else None
        E = g["E"]
        if E and g["ledger"]:
            evs = defaultdict(dict)
            for ev in E["evals"]:
                evs[ev[0]][ev[1]] = ev
            for i, a in enumerate(g["ledger"]["attempts"]):
                e = evs.get(i, {})
                a["ev"] = e
                vs = [verdict_of(e[k]) for k in (7, 14, 21) if k in e]
                a["verdict"] = None if not vs else (vs[0] if len(set(vs)) == 1 else "mixed")
        if E:
            E["snapIdx"] = {t: i for i, t in enumerate(E["snapT"])}
            E["recOf"] = {rec["me"]: rec for rec in g["bots"] if rec["inReplay"]}
    return games


def snap_index(E: dict, t: int) -> int:
    """t 拍之前（含）最近一张探针快照的下标。"""
    i = E["snapIdx"].get((t // 90) * 90)
    if i is None:
        i = 0 if t < E["snapT"][0] else len(E["snapT"]) - 1
    return i


# ----------------------------------------------------------------------------
# 假设 ①：配额拒单 → act(g) 提前 return 停摆
# ----------------------------------------------------------------------------

def code_facts() -> dict:
    out = {}
    for ver, fn in STRAT.items():
        lines = open(os.path.join(DATA, "src", "strategy", fn), encoding="utf-8").read().split("\n")
        calls = [i + 1 for i, s in enumerate(lines) if "tryDonateToTeammate(" in s and not re.match(r"\s*tryDonateToTeammate\(g", s)]
        defs = [i + 1 for i, s in enumerate(lines) if re.match(r"\s*tryDonateToTeammate\(g", s)]
        guarded = [i for i in calls if "this.cmds === cmdsBefore" in lines[i - 1]]
        cb = [i + 1 for i, s in enumerate(lines) if "const cmdsBefore = this.cmds" in s]
        buy = [i + 1 for i, s in enumerate(lines) if s.strip() == "this.buyLand(g);"]
        acts = [i + 1 for i, s in enumerate(lines) if s.startswith("  act(g) {")]
        main_act = acts[-1]
        buy_main = [i for i in buy if i > main_act]
        boss_ret = [i + 1 for i, s in enumerate(lines) if "tryEmergencyBossRescue(g) && g.online) return" in s and i + 1 > main_act]
        boss_gate = [i + 1 for i, s in enumerate(lines) if re.search(r"const bossId = this\.findBossId\(g\)", s)]
        out[ver] = {"file": fn, "actLine": main_act, "cmdsBeforeLine": cb[-1] if cb else None,
                    "buyLandLine": buy_main[0] if buy_main else None, "donateCallLines": calls, "donateDefLine": defs[0] if defs else None,
                    "donateCallsGuarded": len(guarded), "donateCalls": len(calls),
                    "orderOk": bool(cb and buy_main and calls and cb[-1] < buy_main[0] < calls[-1]),
                    "bossReturnLines": boss_ret, "bossGateLines": boss_gate[:3]}
    return out


def boss_presence(games) -> dict:
    """选点日志里的 bossDist：-1 表示本局队伍里没有 Boss 号（tryEmergencyBossRescue 的前提不成立）。"""
    n = 0
    with_boss = 0
    for g in games:
        for r in L.load_spawn(g["card"]):
            n += 1
            if r["bossDist"] is not None and r["bossDist"] >= 0:
                with_boss += 1
    boss_log = 0
    for g in games:
        p = os.path.join(L.bundle_dir(g["card"]), "in_game.log")
        with open(p, encoding="utf-8", errors="replace") as f:
            for line in f:
                if "boss" in line and ("HL-BOSS" in line or "boss-rescue" in line or "boss donate" in line or "BOSS-RESCUE" in line):
                    boss_log += 1
    return {"spawnRows": n, "spawnRowsWithBoss": with_boss, "bossActionLogLines": boss_log}


def h1(games) -> dict:
    J = {"code": code_facts(), "boss": boss_presence(games)}
    by = {v: Counter() for v in VERS}
    by_phase = {v: {p: Counter() for p in PHASES} for v in VERS}
    by_kind = defaultdict(Counter)
    by_box = defaultdict(Counter)
    conf = {v: Counter() for v in VERS}
    verd = {v: Counter() for v in VERS}
    verd_phase = defaultdict(Counter)
    lags = defaultdict(list)
    foot = defaultdict(list)
    rej_dme = defaultdict(list)
    flow = {v: {p: Counter() for p in PHASES} for v in VERS}
    util = defaultdict(list)
    unexpl_ex = []
    fit = defaultdict(list)
    fit_abs = defaultdict(list)
    want_abs = defaultdict(list)
    episodes = defaultdict(list)
    assoc = []
    ep_snap = defaultdict(Counter)
    ep_share = defaultdict(list)
    ep_nshare = defaultdict(list)
    for g in games:
        v = g["ver"]
        by[v]["games"] += 1
        for e in g["events"]:
            if e["type"] not in ("DISPATCH", "DONATE"):
                continue
            by[v]["logged"] += 1
            if e["botRec"] is None:
                by[v]["orphan"] += 1
            if e["likelyRejected"]:
                by[v]["heurRej"] += 1
            if e["likelyRejected"] is not None:
                by[v]["heurKnown"] += 1
        led = g["ledger"]
        if not led:
            continue
        by[v]["gamesReplay"] += 1
        by[v]["unmatchedExec"] += led["unmatchedExec"]
        E_land = g["E"]["info"]["land"] if g["E"] else None
        per_win = Counter()
        for a in led["attempts"]:
            by[v]["covered"] += 1
            ph = phase(a["t"])
            by_phase[v][ph]["n"] += 1
            kind = a.get("kind") or "?"
            by_kind[(v, kind)]["n"] += 1
            bx = a.get("boxedIn")
            by_box[(v, bx)]["n"] += 1
            per_win[(a["botRec"]["me"], a["t"] // 90)] += 1
            if a["exec"]:
                by[v]["exec"] += 1
                by_phase[v][ph]["exec"] += 1
                by_kind[(v, kind)]["exec"] += 1
                by_box[(v, bx)]["exec"] += 1
                lags[v].append(a["lag"])
            else:
                vd = a.get("verdict") or "noEval"
                verd[v][vd] += 1
                verd_phase[(v, ph)][vd] += 1
                if a.get("dMe") is not None:
                    rej_dme[v].append(a["dMe"])
                e14 = a.get("ev", {}).get(14)
                if e14 is not None and vd in ("singleOver", "accOver") and E_land:
                    base, den = D.quota_denominator(a["t"] + 14, E_land, e14[11])
                    fit_v = max(0, (e14[7] - e14[6] - base) * den // 100)
                    want_v = max(1, e14[3])
                    fit[v].append(min(1.0, fit_v / want_v))
                    fit_abs[v].append(fit_v)
                    want_abs[v].append(want_v)
                if vd == "fits" and len(unexpl_ex) < 12:
                    unexpl_ex.append({"mid": g["mid"], "bot": a["bot"], "t": a["t"], "pct": a["pct"]})
            if a["likelyRejected"] is not None:
                conf[v][("heurRej" if a["likelyRejected"] else "heurOk") + ("_exec" if a["exec"] else "_rej")] += 1
        for k, n in per_win.items():
            foot[v].append(n)
        by_bot = defaultdict(list)
        for a in led["attempts"]:
            by_bot[a["botRec"]["me"]].append(a)
        ep_of = defaultdict(list)
        for me_, lst in by_bot.items():
            lst.sort(key=lambda a: a["t"])
            i = 0
            while i < len(lst):
                if lst[i]["exec"]:
                    i += 1
                    continue
                j = i
                while j + 1 < len(lst) and not lst[j + 1]["exec"] and lst[j + 1]["t"] - lst[j]["t"] <= EP_GAP:
                    j += 1
                nxt = lst[j + 1] if j + 1 < len(lst) else None
                ep = {"t0": lst[i]["t"], "t1": lst[j]["t"] + 25, "n": j - i + 1,
                      "endExec": bool(nxt and nxt["exec"] and nxt["t"] - lst[j]["t"] <= EP_GAP),
                      "bal": statistics.median(a["myBal"] for a in lst[i:j + 1] if a.get("myBal") is not None) if any(a.get("myBal") is not None for a in lst[i:j + 1]) else None}
                episodes[v].append(ep)
                ep_of[me_].append(ep)
                i = j + 1
        cover_to = g["replayTicks"] - D.COVER_MARGIN
        if g["rroom"] is not None and is_team_room(g["rroom"]):
            n_rej = sum(1 for a in led["attempts"] if not a["exec"] and a["t"] < 4284)
            n_att = sum(1 for a in led["attempts"] if a["t"] < 4284)
            n_sn = sum(1 for rec in g["bots"] if rec["inReplay"] for sn in rec["snaps"] if 1500 <= sn["t"] < 4284 and sn["t"] <= cover_to)
            if n_sn >= 30:
                assoc.append({"cohort": g["cohort"], "outcome": g["rroom"]["outcome"], "rate": n_rej / n_sn, "rejShare": n_rej / n_att if n_att else None})
        ep_gt = defaultdict(Counter)
        for rec in g["bots"]:
            if not rec["inReplay"]:
                continue
            eps = ep_of.get(rec["me"], [])
            for sn in rec["snaps"]:
                if sn["t"] < 1500 or sn["t"] > cover_to:
                    continue
                ep_snap[v]["n"] += 1
                ep_snap[v]["bal"] += sn["bal"]
                gt = ep_gt[(rec["roomIdx"], sn["t"])]
                gt["bal"] += sn["bal"]
                gt["n"] += 1
                if any(ep["t0"] <= sn["t"] <= ep["t1"] for ep in eps):
                    ep_snap[v]["in"] += 1
                    ep_snap[v]["balIn"] += sn["bal"]
                    gt["balIn"] += sn["bal"]
                    gt["nIn"] += 1
        for (ridx, t_), c in ep_gt.items():
            if c["bal"] > 0 and c["n"] >= 3 and t_ < 4284:
                ep_share[v].append(c["balIn"] / c["bal"])
                ep_nshare[v].append(c["nIn"] / c["n"])
        E = g["E"]
        if E:
            last_acc = {}
            for d in E["dons"]:
                t, donor, pct, to, b0, b1, r0, r1, acc0, acc1, cap, rec_terr, don_terr, d_our, r_our = d
                if d_our:
                    ph = phase(t)
                    flow[v][ph]["n"] += 1
                    flow[v][ph]["v"] += r1 - r0
                if r_our and t < 4284:
                    last_acc[to] = acc1
            if E["lastTick"] >= 4284:
                cap_end = D.quota_cap(4283)
                for to, acc in last_acc.items():
                    util[v].append(acc / cap_end)
    rows = {}
    for v in VERS:
        c = by[v]
        rows[v] = {"games": c["games"], "gamesReplay": c["gamesReplay"], "logged": c["logged"], "orphan": c["orphan"],
                   "heurRej": wil(c["heurRej"], c["heurKnown"]), "covered": c["covered"],
                   "uncovered": c["logged"] - c["orphan"] - c["covered"],
                   "exec": wil(c["exec"], c["covered"]), "notExec": wil(c["covered"] - c["exec"], c["covered"]),
                   "unmatchedExec": c["unmatchedExec"]}
    J["byVersion"] = rows
    s10 = Counter()
    for v in ("Va", "Vb", "Vc"):
        for k in ("covered", "exec", "logged", "heurRej", "heurKnown"):
            s10[k] += by[v][k]
    J["squad10"] = {"covered": s10["covered"], "exec": wil(s10["exec"], s10["covered"]),
                    "notExec": wil(s10["covered"] - s10["exec"], s10["covered"]),
                    "heurRej": wil(s10["heurRej"], s10["heurKnown"])}
    J["byPhase"] = {v: {p: wil(by_phase[v][p]["exec"], by_phase[v][p]["n"]) for p in PHASES} for v in VERS}
    J["byKind"] = [{"ver": v, "kind": k, **wil(c["exec"], c["n"])} for (v, k), c in sorted(by_kind.items())]
    J["byBoxed"] = [{"ver": v, "boxedIn": b, **wil(c["exec"], c["n"])} for (v, b), c in sorted(by_box.items(), key=lambda x: (x[0][0], str(x[0][1])))]
    J["boxedShare"] = {v: wil(by_box[(v, True)]["n"], sum(by_box[(v, b_)]["n"] for b_ in (True, False))) for v in VERS}
    J["heuristic"] = {}
    for v in VERS:
        c = conf[v]
        tp, fn, fp, tn = c["heurRej_rej"], c["heurOk_rej"], c["heurRej_exec"], c["heurOk_exec"]
        J["heuristic"][v] = {"tp": tp, "fn": fn, "fp": fp, "tn": tn,
                             "sens": wil(tp, tp + fn), "spec": wil(tn, tn + fp), "ppv": wil(tp, tp + fp)}
    order = ["singleOver", "accOver", "recFull", "recGone", "donorDead", "mixed", "fits", "noEval"]
    J["verdict"] = {}
    for v in VERS:
        n = sum(verd[v].values())
        J["verdict"][v] = {"n": n, **{k: verd[v][k] for k in order},
                           "quotaShare": (verd[v]["singleOver"] + verd[v]["accOver"]) / n if n else None,
                           "fitsShare": verd[v]["fits"] / n if n else None}
    tot = Counter()
    for v in ("Va", "Vb", "Vc"):
        tot.update(verd[v])
    n = sum(tot.values())
    J["verdictSquad10"] = {"n": n, **{k: tot[k] for k in order}, "quotaShare": (tot["singleOver"] + tot["accOver"]) / n,
                           "singleShare": tot["singleOver"] / n, "accShare": tot["accOver"] / n, "fitsShare": tot["fits"] / n}
    J["verdictPhase"] = [{"ver": v, "phase": p, "n": sum(c.values()), **{k: c[k] for k in order}} for (v, p), c in sorted(verd_phase.items(), key=lambda x: (VERS.index(x[0][0]), PHASES.index(x[0][1])))]
    J["lag"] = {}
    for v in VERS:
        xs = lags[v]
        J["lag"][v] = {**dist(xs), "ge21": wil(sum(1 for x in xs if x >= 21), len(xs)), "ge35": wil(sum(1 for x in xs if x >= 35), len(xs)),
                       "ge90": wil(sum(1 for x in xs if x >= 90), len(xs))}
    J["footprint"] = {v: {**dist(foot[v]), "shareOfActTicksMed": (q(foot[v], .5) or 0) / 18, "shareOfActTicksMax": (max(foot[v]) if foot[v] else 0) / 18} for v in VERS}
    J["flow"] = {v: {p: {"n": flow[v][p]["n"], "v": flow[v][p]["v"]} for p in PHASES} for v in VERS}
    for v in VERS:
        tv = sum(flow[v][p]["v"] for p in PHASES)
        tn = sum(flow[v][p]["n"] for p in PHASES)
        J["flow"][v]["total"] = {"n": tn, "v": tv, "shareAfterLiftV": flow[v]["≥4284"]["v"] / tv if tv else None,
                                 "shareAfterLiftN": flow[v]["≥4284"]["n"] / tn if tn else None}
    J["quotaUtilAt4283"] = {v: {**dist(util[v]), "ge80": wil(sum(1 for x in util[v] if x >= 0.8), len(util[v]))} for v in VERS}
    J["rightSize"] = {}
    for v in VERS:
        xs = fit[v]
        J["rightSize"][v] = {"n": len(xs), "ratio": dist(xs), "ge50": wil(sum(1 for x in xs if x >= 0.5), len(xs)),
                             "ge25": wil(sum(1 for x in xs if x >= 0.25), len(xs)), "lt5": wil(sum(1 for x in xs if x < 0.05), len(xs)),
                             "fitV": dist(fit_abs[v]), "wantV": dist(want_abs[v])}
    xs = fit["Va"] + fit["Vb"] + fit["Vc"]
    J["rightSizeSquad10"] = {"n": len(xs), "ge50": wil(sum(1 for x in xs if x >= 0.5), len(xs)), "ge25": wil(sum(1 for x in xs if x >= 0.25), len(xs)),
                             "lt5": wil(sum(1 for x in xs if x < 0.05), len(xs)), "ratio": dist(xs),
                             "fitV": dist(fit_abs["Va"] + fit_abs["Vb"] + fit_abs["Vc"]), "wantV": dist(want_abs["Va"] + want_abs["Vb"] + want_abs["Vc"])}
    J["outcome"] = {}
    for coh in ("squad10", "squad20"):
        W_ = [r["rate"] for r in assoc if r["cohort"] == coh and r["outcome"] == "WIN"]
        L_ = [r["rate"] for r in assoc if r["cohort"] == coh and r["outcome"] in LOSS]
        J["outcome"][coh] = {"win": dist(W_), "loss": dist(L_), "auc": BF.auc_ci(W_, L_) if W_ and L_ else None}
    J["episodeGap"] = EP_GAP
    J["episodes"] = {}
    for v in VERS:
        eps = episodes[v]
        c = ep_snap[v]
        J["episodes"][v] = {"n": len(eps), "attempts": dist([e["n"] for e in eps]), "dur": dist([e["t1"] - e["t0"] for e in eps]),
                            "ge360": wil(sum(1 for e in eps if e["t1"] - e["t0"] >= 360), len(eps)),
                            "ge900": wil(sum(1 for e in eps if e["t1"] - e["t0"] >= 900), len(eps)),
                            "endExec": wil(sum(1 for e in eps if e["endExec"]), len(eps)),
                            "bal": dist([e["bal"] for e in eps if e["bal"] is not None]),
                            "snapShare": wil(c["in"], c["n"]), "balShare": c["balIn"] / c["bal"] if c["bal"] else None,
                            "balSharePre": dist(ep_share[v]), "botSharePre": dist(ep_nshare[v]),
                            "botTicks": sum(e["t1"] - e["t0"] for e in eps)}
    J["unexplainedExamples"] = unexpl_ex
    # 配额天花板示例：三种地图大小下，单个受捐方在各阶段累计最多能收多少兵（不含每笔 2 点底数）
    J["ceiling"] = []
    for land in (300000, 500000, 660000):
        uv = 1 + land // 300
        J["ceiling"].append({"land": land, "t1500": D.quota_cap(1500) * 30 * uv // 100, "t2141": D.quota_cap(2141) * 30 * uv // 100,
                             "t2142": D.quota_cap(2142) * 100 * uv // 100, "t3212": D.quota_cap(3212) * 100 * uv // 100,
                             "cap1500": D.quota_cap(1500), "cap2141": D.quota_cap(2141), "cap3212": D.quota_cap(3212), "cap4283": D.quota_cap(4283)})
    return J


# ----------------------------------------------------------------------------
# 假设 ②：6.25% 全额余额税在小比例捐款下的损耗
# ----------------------------------------------------------------------------

PCT_BUCKETS = [("<64", 0, 64), ("64–127", 64, 128), ("128–179", 128, 180), ("180–255", 180, 256), ("256–383", 256, 384), ("≥384", 384, 2000)]


def pct_bucket(p: int) -> str:
    for name, lo, hi in PCT_BUCKETS:
        if lo <= p < hi:
            return name
    return "?"


def h2(games) -> dict:
    J = {}
    agg = {v: Counter() for v in VERS}
    bucket = defaultdict(Counter)
    ph = defaultdict(Counter)
    burn = defaultdict(list)
    fee_vs_attack = defaultdict(list)
    pcts = defaultdict(list)
    wild = Counter()
    wild_pcts = []
    stack = defaultdict(Counter)
    fee_formula = Counter()
    fee_int = defaultdict(list)
    relay = defaultdict(Counter)
    chain_n = defaultdict(list)
    chain_fee = defaultdict(list)
    back_games = defaultdict(list)
    game_fees = defaultdict(list)
    best_pair = [None, None]
    trunc_all = Counter()
    for g in games:
        E = g["E"]
        if not E:
            continue
        v = g["ver"]
        ours = E["ours"]
        game_burn = 0.0
        game_fee = 0
        per_tick = Counter()
        for d in E["dons"]:
            t, donor, pct, to, b0, b1, r0, r1, acc0, acc1, cap, rec_terr, don_terr, d_our, r_our = d
            if b0 == b1:
                continue
            fee = (64 * b0) // 1024            # 引擎 rD：手续费 = floor(64×捐出方余额/1024)
            arrive = (b0 - b1) - fee           # 转出额（到账）；收款方有欠兵时其中一部分先抵欠
            fee_formula["n"] += 1
            if r1 - r0 == arrive:
                fee_formula["exact"] += 1
            elif r1 - r0 < arrive:
                fee_formula["debt"] += 1
            else:
                fee_formula["other"] += 1
            if not d_our:
                wild["n"] += 1
                wild["v"] += arrive
                wild["fee"] += fee
                wild_pcts.append(pct)
                continue
            a = agg[v]
            a["n"] += 1
            a["v"] += arrive
            a["fee"] += fee
            if pct < 180:
                a["lt180"] += 1
                a["lt180v"] += arrive
                a["lt180fee"] += fee
            if fee >= arrive:
                a["feeGeArrive"] += 1
            pcts[v].append(pct)
            coh = g["cohort"]
            b = bucket[(coh, pct_bucket(pct))]
            b["n"] += 1
            b["v"] += arrive
            b["fee"] += fee
            p = ph[(v, "≥4284" if t >= 4284 else "<4284")]
            p["n"] += 1
            p["v"] += arrive
            p["fee"] += fee
            want = min((b0 * (pct + 1)) // 1024, b0 - fee)
            p["want"] += want
            if arrive < 0.98 * want:
                p["truncN"] += 1
                p["truncV"] += want - arrive
                trunc_all["n"] += 1
                trunc_all["atCap"] += 1 if d[7] == 150 * d[11] else 0
            per_tick[(t, donor)] += 1
            if per_tick[(t, donor)] >= 2:
                stack[v]["extraN"] += 1
                stack[v]["extraFee"] += fee
            i = snap_index(E, t)
            team_bal = sum(E["bots"][str(pp)][i][1] for pp in ours if E["bots"][str(pp)][i][2])
            if team_bal > 0:
                game_burn += fee / team_bal
            game_fee += fee
        # 手续费 vs 利息收入；接力（收到后 100 拍内又转出）；解禁后单号连续转账
        T_ = E["snapT"]
        land_ = E["info"]["land"]
        interest = {"pre": 0, "post": 0}
        for pp in ours:
            arr = E["bots"][str(pp)]
            for i_, t_ in enumerate(T_):
                if t_ < 1500 or not arr[i_][2] or arr[i_][0] <= 0:
                    continue
                act_, _base = D.interest_rate(t_, arr[i_][0], land_, arr[i_][1])
                interest["post" if t_ >= 4284 else "pre"] += 9 * (act_ * arr[i_][1] // 10000)
        fee_ph = {"pre": 0, "post": 0}
        our_d = [d for d in E["dons"] if d[13] and d[4] != d[5]]
        by_donor = defaultdict(list)
        for d in our_d:
            fee_ph["post" if d[0] >= 4284 else "pre"] += (64 * d[4]) // 1024
            by_donor[d[1]].append(d)
        if is_team_room(g["rroom"]):
            for k in ("pre", "post"):
                if interest[k] > 0 and (k == "pre" or E["lastTick"] >= 4284 + 360):
                    fee_int[(v, k)].append(fee_ph[k] / interest[k])
            for d in our_d:
                t, donor, to = d[0], d[1], d[3]
                arrive = (d[4] - d[5]) - (64 * d[4]) // 1024
                k = "post" if t >= 4284 else "pre"
                relay[(v, k)]["n"] += 1
                relay[(v, k)]["v"] += arrive
                nxt = [x for x in by_donor.get(to, ()) if t < x[0] <= t + 100]
                if nxt:
                    relay[(v, k)]["relayN"] += 1
                    relay[(v, k)]["relayV"] += arrive
                if any(x[3] == donor for x in by_donor.get(to, ()) if t < x[0] <= t + 300):
                    relay[(v, k)]["backN"] += 1
                    relay[(v, k)]["backV"] += arrive
            post_all = [d for d in our_d if d[0] >= 4284]
            if post_all:
                tot_v = sum((d[4] - d[5]) - (64 * d[4]) // 1024 for d in post_all)
                tot_f = sum((64 * d[4]) // 1024 for d in post_all)
                back_d = [d for d in post_all if any(x[3] == d[1] for x in by_donor.get(d[3], ()) if d[0] < x[0] <= d[0] + 300)]
                back_v = sum((d[4] - d[5]) - (64 * d[4]) // 1024 for d in back_d)
                back_f = sum((64 * d[4]) // 1024 for d in back_d)
                back_games[v].append({"mid": g["mid"], "outcome": g["rroom"]["outcome"], "n": len(post_all), "v": tot_v, "fee": tot_f,
                                      "backShare": back_v / tot_v if tot_v else 0.0, "backFee": back_f})
            game_fees[v].append({"mid": g["mid"], "outcome": g["rroom"]["outcome"], "fee": sum(fee_ph.values())})
            pair_n = Counter()
            for d in post_all:
                pair_n[tuple(sorted((d[1], d[3])))] += 1
            for pr_, n_ in pair_n.items():
                dirs = {(d[1], d[3]) for d in post_all if tuple(sorted((d[1], d[3]))) == pr_}
                if len(dirs) == 2 and (best_pair[0] is None or n_ > best_pair[0]):
                    best_pair[0] = n_
                    best_pair[1] = (g["mid"], pr_, v)
            for donor, lst in by_donor.items():
                post = [d for d in lst if d[0] >= 4284]
                if post:
                    chain_n[v].append(len(post))
                    chain_fee[v].append(sum((64 * d[4]) // 1024 for d in post) / max(1, post[0][4]))
        if agg[v]["n"] and is_team_room(g["rroom"]):
            burn[v].append(game_burn)
            atk = sum(c[5] - c[6] for c in E["cmds"] if c[1] != 2)
            if atk > 0:
                fee_vs_attack[v].append(game_fee / atk)
    J["feeFormula"] = {"n": fee_formula["n"], "exact": fee_formula["exact"], "debt": fee_formula["debt"], "other": fee_formula["other"]}
    J["byVersion"] = {}
    for v in VERS:
        a = agg[v]
        J["byVersion"][v] = {"n": a["n"], "v": a["v"], "fee": a["fee"], "feeOverArrive": a["fee"] / a["v"] if a["v"] else None,
                             "pct": dist(pcts[v]), "lt180": wil(a["lt180"], a["n"]),
                             "lt180FeeOverArrive": a["lt180fee"] / a["lt180v"] if a["lt180v"] else None,
                             "lt180FeeShare": a["lt180fee"] / a["fee"] if a["fee"] else None,
                             "feeGeArrive": a["feeGeArrive"], "burnPerGame": dist(burn[v]), "feeOverAttack": dist(fee_vs_attack[v]),
                             "stackExtraN": stack[v]["extraN"], "stackExtraFee": stack[v]["extraFee"],
                             "stackExtraFeeShare": stack[v]["extraFee"] / a["fee"] if a["fee"] else None}
    J["feeOverInterest"] = {v: {"pre": dist(fee_int[(v, "pre")]), "post": dist(fee_int[(v, "post")])} for v in VERS}
    J["relay"] = []
    for v in VERS:
        for k in ("pre", "post"):
            c = relay[(v, k)]
            if c["n"]:
                J["relay"].append({"ver": v, "phase": "≥4284" if k == "post" else "<4284", "n": c["n"], "v": c["v"],
                                   "relay": wil(c["relayN"], c["n"]), "relayV": c["relayV"] / c["v"] if c["v"] else None,
                                   "back": wil(c["backN"], c["n"]), "backV": c["backV"] / c["v"] if c["v"] else None})
    J["chains"] = {v: {"donors": len(chain_n[v]), "count": dist(chain_n[v]), "ge5": wil(sum(1 for x in chain_n[v] if x >= 5), len(chain_n[v])),
                       "ge10": wil(sum(1 for x in chain_n[v] if x >= 10), len(chain_n[v])),
                       "feeOverFirstBal": dist(chain_fee[v])} for v in VERS}
    J["truncAtCap"] = wil(trunc_all["atCap"], trunc_all["n"])
    J["example"] = None
    if best_pair[1]:
        mid_, pr_, v_ = best_pair[1]
        g_ = next(x for x in games if x["mid"] == mid_)
        E_ = g_["E"]
        seq = [d for d in E_["dons"] if d[0] >= 4284 and tuple(sorted((d[1], d[3]))) == pr_ and d[4] != d[5]]
        start = next((i for i in range(len(seq) - 1) if seq[i][1] != seq[i + 1][1] and seq[i + 1][0] - seq[i][0] <= 300), 0)
        rows_ = []
        for d in seq[start:start + 8]:
            fee_ = (64 * d[4]) // 1024
            rows_.append({"t": d[0], "from": E_["names"][d[1]], "to": E_["names"][d[3]], "pct": d[2], "donorBal": d[4], "recBal0": d[6], "recBal1": d[7],
                          "recCap": 150 * d[11], "want": min((d[4] * (d[2] + 1)) // 1024, d[4] - fee_),
                          "arrive": d[7] - d[6], "fee": fee_})
        J["example"] = {"mid": mid_, "ver": v_, "names": [E_["names"][pr_[0]], E_["names"][pr_[1]]], "n": len(seq),
                        "fee": sum((64 * d[4]) // 1024 for d in seq), "arrive": sum(d[7] - d[6] for d in seq),
                        "tFirst": seq[0][0], "tLast": seq[-1][0], "rows": rows_, "outcome": g_["rroom"]["outcome"]}
    J["pctGuard"] = {}
    for ver, fn in STRAT.items():
        lines = open(os.path.join(DATA, "src", "strategy", fn), encoding="utf-8").read().split("\n")
        d0 = next((i for i, x in enumerate(lines) if re.match(r"\s*tryDonateToTeammate\(g", x)), None)
        hits = []
        if d0 is not None:
            for i in range(d0, min(len(lines), d0 + 260)):
                m = re.search(r"if \(pct < (\d+)\) return false;", lines[i])
                if m:
                    hits.append({"line": i + 1, "threshold": int(m.group(1))})
        J["pctGuard"][ver] = {"file": fn, "guards": hits, "last": hits[-1] if hits else None}
    J["concentration"] = {}
    J["pingPong"] = {}
    for v in VERS:
        gf = sorted(game_fees[v], key=lambda x: -x["fee"])
        tot = sum(x["fee"] for x in gf)
        J["concentration"][v] = {"games": len(gf), "fee": tot, "top2Share": sum(x["fee"] for x in gf[:2]) / tot if tot else None,
                                 "top5Share": sum(x["fee"] for x in gf[:5]) / tot if tot else None,
                                 "top": [{"mid": x["mid"], "outcome": x["outcome"], "fee": x["fee"]} for x in gf[:5]],
                                 "top2Wins": sum(1 for x in gf[:2] if x["outcome"] == "WIN"),
                                 "feeWinGames": sum(x["fee"] for x in gf if x["outcome"] == "WIN") / tot if tot else None,
                                 "winGames": sum(1 for x in gf if x["outcome"] == "WIN")}
        bg = back_games[v]
        hi = [x for x in bg if x["backShare"] >= 0.5]
        tf = sum(x["fee"] for x in bg)
        J["pingPong"][v] = {"games": len(bg), "backShare": dist([x["backShare"] for x in bg]), "ge50": wil(len(hi), len(bg)),
                            "ge50Outcomes": dict(Counter(x["outcome"] for x in hi)), "ge50Games": sorted(x["mid"] for x in hi),
                            "backFee": sum(x["backFee"] for x in bg), "backFeeShare": sum(x["backFee"] for x in bg) / tf if tf else None,
                            "postFee": tf}
    J["byBucket"] = []
    for coh in ("squad10", "squad20"):
        for name, lo, hi in PCT_BUCKETS:
            b = bucket[(coh, name)]
            J["byBucket"].append({"cohort": coh, "bucket": name, "n": b["n"], "v": b["v"], "fee": b["fee"],
                                  "feeOverArrive": b["fee"] / b["v"] if b["v"] else None})
    J["byPhase"] = [{"ver": v, "phase": p, "n": c["n"], "v": c["v"], "fee": c["fee"], "feeOverArrive": c["fee"] / c["v"] if c["v"] else None,
                     "trunc": wil(c["truncN"], c["n"]), "truncShare": c["truncV"] / c["want"] if c["want"] else None,
                     "feeOverWant": c["fee"] / c["want"] if c["want"] else None}
                    for (v, p), c in sorted(ph.items(), key=lambda x: (VERS.index(x[0][0]), x[0][1]))]
    J["wild"] = {"n": wild["n"], "v": wild["v"], "fee": wild["fee"], "feeOverArrive": wild["fee"] / wild["v"] if wild["v"] else None,
                 "pct": dist(wild_pcts), "lt180": wil(sum(1 for p in wild_pcts if p < 180), len(wild_pcts))}
    J["theory"] = [{"pct": p, "arrive": (p + 1) / 1024, "feeOverArrive": 64 / (p + 1)} for p in (55, 102, 128, 153, 180, 220, 280, 320, 380, 511, 1023)]
    # 没有录像的包（squad8 全部、squad20 的 6 个）：只能按日志估计（下单时余额 × 公式；按“疑似成交”的启发式挑单）
    est = defaultdict(Counter)
    for g in games:
        if g["E"]:
            continue
        for e in g["events"]:
            if e["type"] not in ("DISPATCH", "DONATE") or e["pct"] is None or e["myBal"] is None:
                continue
            c = est[g["ver"]]
            c["logged"] += 1
            if e["likelyRejected"] is False:
                vv, fee = D.donate_amounts(e["myBal"], e["pct"], None, None)
                c["n"] += 1
                c["v"] += vv
                c["fee"] += fee
                if e["pct"] < 180:
                    c["lt180"] += 1
    J["estimateNoReplay"] = {v: {"logged": c["logged"], "n": c["n"], "v": c["v"], "fee": c["fee"],
                                 "feeOverArrive": c["fee"] / c["v"] if c["v"] else None, "lt180": wil(c["lt180"], c["n"])}
                             for v, c in est.items()}
    return J


# ----------------------------------------------------------------------------
# 假设 ③：内陆 nb=0 号高密度憋死
# ----------------------------------------------------------------------------

def h3(games) -> dict:
    J = {}
    per = {v: Counter() for v in VERS}
    maxruns = defaultdict(list)
    forgone = defaultdict(list)
    behave = {v: Counter() for v in VERS}
    behave_phase = defaultdict(Counter)
    fate = {v: Counter() for v in VERS}
    lost = defaultdict(list)
    room_share = []
    idle_at_lift = defaultdict(list)
    bal_share = defaultdict(list)
    for g in games:
        v = g["ver"]
        led = g["ledger"]
        att_by = defaultdict(list)
        if led:
            for a in led["attempts"]:
                att_by[a["botRec"]["me"]].append(a)
        E = g["E"]
        death_bal = {d[1]: d[3] for d in E["deaths"]} if E else {}
        g_forgone = 0
        g_interest = 0
        room_cnt = defaultdict(Counter)
        lift = defaultdict(Counter)
        rt = defaultdict(Counter)
        for rec in g["bots"]:
            if not is_team_room(rec):
                continue
            land = rec["land"]
            snaps = [s for s in rec["snaps"] if s["t"] >= 1500]
            if not snaps:
                continue
            per[v]["bots"] += 1
            n_high = 0
            run = 0
            maxrun = 0
            prev_high_t = None
            for s in snaps:
                per[v]["snaps"] += 1
                rc = room_cnt[rec["roomIdx"]]
                rc["snaps"] += 1
                boxed = s["nb"] == 0 and s["neut"] == 0
                high = boxed and s["dens"] >= 95
                act, base = D.interest_rate(s["t"], s["terr"], land, s["bal"])
                g_interest += 9 * (act * s["bal"] // 10000)
                per[v]["bal"] += s["bal"]
                rtc = rt[(rec["roomIdx"], s["t"])]
                rtc["bal"] += s["bal"]
                rtc["n"] += 1
                if boxed:
                    rtc["boxed"] += s["bal"]
                if high:
                    rtc["high"] += s["bal"]
                    rtc["nHigh"] += 1
                if s["t"] == 4230:
                    lift[rec["roomIdx"]]["bal"] += s["bal"]
                    if high:
                        lift[rec["roomIdx"]]["high"] += s["bal"]
                if boxed:
                    per[v]["boxed"] += 1
                    per[v]["boxedBal"] += s["bal"]
                if not high:
                    run = 0
                    prev_high_t = None
                    continue
                per[v]["high"] += 1
                per[v]["highBal"] += s["bal"]
                rc["high"] += 1
                n_high += 1
                if s["dens"] >= 100:
                    per[v]["ge100"] += 1
                if s["dens"] >= 145:
                    per[v]["ge145"] += 1
                g_forgone += 9 * ((base - act) * s["bal"] // 10000)
                run = run + 1 if (prev_high_t is not None and s["t"] - prev_high_t == 90) else 1
                prev_high_t = s["t"]
                maxrun = max(maxrun, run)
                if led and rec["inReplay"] and s["t"] + 90 <= g["replayTicks"] - D.COVER_MARGIN:
                    A = [a for a in att_by.get(rec["me"], []) if s["t"] < a["t"] <= s["t"] + 90]
                    k = "noAttempt" if not A else ("executed" if any(a["exec"] for a in A) else "allRejected")
                    behave[v][k] += 1
                    behave_phase[(v, "≥4284" if s["t"] >= 4284 else "<4284")][k] += 1
            if n_high >= 1:
                per[v]["botsAny"] += 1
                maxruns[v].append(maxrun)
            if n_high >= 10:
                per[v]["bots10"] += 1
                ev = rec["event"] or "unknown"
                fate[v][ev] += 1
                if ev == "died":
                    b = death_bal.get(rec["me"]) if rec["inReplay"] else None
                    if b is None:
                        b = rec["snaps"][-1]["bal"]
                    lost[v].append(b)
        for (ridx, t_), c in rt.items():
            if c["bal"] <= 0 or c["n"] < 3:
                continue
            k = "post" if t_ >= 4284 else "pre"
            bal_share[(v, k, "high")].append(c["high"] / c["bal"])
            bal_share[(v, k, "boxed")].append(c["boxed"] / c["bal"])
            bal_share[(v, k, "nHigh")].append(c["nHigh"] / c["n"])
        if g_interest > 0:
            forgone[v].append(g_forgone / g_interest)
        for ridx, c in room_cnt.items():
            room = g["roomByIdx"][ridx]
            if c["snaps"] >= 30:
                room_share.append({"mid": g["mid"], "cohort": g["cohort"], "ver": v, "outcome": room["outcome"],
                                   "share": c["high"] / c["snaps"], "snaps": c["snaps"]})
        for ridx, c in lift.items():
            if c["bal"] > 0:
                idle_at_lift[v].append(c["high"] / c["bal"])
    J["byVersion"] = {}
    for v in VERS:
        c = per[v]
        J["byVersion"][v] = {"bots": c["bots"], "snaps": c["snaps"], "boxed": wil(c["boxed"], c["snaps"]), "high": wil(c["high"], c["snaps"]),
                             "ge100": c["ge100"], "ge145": c["ge145"], "botsAny": wil(c["botsAny"], c["bots"]), "bots10": wil(c["bots10"], c["bots"]),
                             "maxRun": dist(maxruns[v]), "balShareHigh": c["highBal"] / c["bal"] if c["bal"] else None,
                             "balShareBoxed": c["boxedBal"] / c["bal"] if c["bal"] else None,
                             "balShareHighPre": dist(bal_share[(v, "pre", "high")]), "balShareHighPost": dist(bal_share[(v, "post", "high")]),
                             "balShareBoxedPre": dist(bal_share[(v, "pre", "boxed")]), "balShareBoxedPost": dist(bal_share[(v, "post", "boxed")]),
                             "botShareHighPre": dist(bal_share[(v, "pre", "nHigh")]), "botShareHighPost": dist(bal_share[(v, "post", "nHigh")]),
                             "forgoneShare": dist(forgone[v]), "idleAtLift": dist(idle_at_lift[v]),
                             "behave": {k: behave[v][k] for k in ("noAttempt", "allRejected", "executed")},
                             "behaveN": sum(behave[v].values()),
                             "fate": dict(fate[v]), "lostAtDeath": dist(lost[v])}
    J["behavePhase"] = [{"ver": v, "phase": p, "n": sum(c.values()), **{k: c[k] for k in ("noAttempt", "allRejected", "executed")}}
                        for (v, p), c in sorted(behave_phase.items(), key=lambda x: (VERS.index(x[0][0]), x[0][1]))]
    J["behaveBy"] = {v: {k: {"n": sum(behave_phase[(v, ph)].values()), **{kk: behave_phase[(v, ph)][kk] for kk in ("noAttempt", "allRejected", "executed")},
                             "allRejectedShare": wil(behave_phase[(v, ph)]["allRejected"], sum(behave_phase[(v, ph)].values())),
                             "noAttemptShare": wil(behave_phase[(v, ph)]["noAttempt"], sum(behave_phase[(v, ph)].values()))}
                         for k, ph in (("pre", "<4284"), ("post", "≥4284"))} for v in VERS}
    J["outcome"] = {}
    for coh in ("squad10", "squad20"):
        W = [r["share"] for r in room_share if r["cohort"] == coh and r["outcome"] == "WIN"]
        Ls = [r["share"] for r in room_share if r["cohort"] == coh and r["outcome"] in LOSS]
        J["outcome"][coh] = {"win": dist(W), "loss": dist(Ls), "auc": BF.auc_ci(W, Ls) if W and Ls else None}
    return J


# ----------------------------------------------------------------------------
# 假设 ④：选点过密 → 内圈开局饿死
# ----------------------------------------------------------------------------

SENS_T = (630, 900, 1200, 1530)
EP_GAP = 100          # 同一号相邻两次未成交下单间隔 ≤100 拍（4 个轮转周期）算同一段“想送送不出去”


def h4(games) -> dict:
    J = {}
    per = {v: Counter() for v in VERS}
    role = defaultdict(Counter)
    mad = defaultdict(list)
    first_t = defaultdict(list)
    terr_at = defaultdict(list)
    cmp_ = defaultdict(lambda: defaultdict(list))
    paired = defaultdict(list)
    rooms = []
    dup = {v: Counter() for v in VERS}
    sens = {v: Counter() for v in VERS}
    role_stat = defaultdict(lambda: defaultdict(list))
    mad_xy = defaultdict(list)
    for g in games:
        v = g["ver"]
        spawn = {}
        for r in L.load_spawn(g["card"]):
            cur = spawn.get(r["bot"])
            r_back = not r["role"].startswith("RANK_")
            if cur is None or (r_back and cur["role"].startswith("RANK_")) or (r_back == (not cur["role"].startswith("RANK_")) and r["line"] > cur["line"]):
                spawn[r["bot"]] = r
        by_room = defaultdict(list)
        for rec in g["bots"]:
            if not is_team_room(rec):
                continue
            early = [s for s in rec["snaps"] if s["t"] <= 630]
            if not early:
                continue
            per[v]["bots"] += 1
            bx = [s for s in early if s["nb"] == 0 and s["neut"] == 0 and s["terr"] < 2500]
            eb = bool(bx)
            for T_ in SENS_T:
                bT = [s for s in rec["snaps"] if s["t"] <= T_ and s["nb"] == 0 and s["neut"] == 0]
                if bT:
                    sens[v][("any", T_)] += 1
                if any(s["terr"] < 2500 for s in bT):
                    sens[v][("small", T_)] += 1
            s1530 = next((s for s in rec["snaps"] if s["t"] == 1530), None)
            if s1530 is not None:
                terr1530, bal1530 = s1530["terr"], s1530["bal"]
            elif rec["lastT"] is not None and rec["lastT"] < 1530 and rec["event"] in ("died", "left"):
                terr1530, bal1530 = 0, 0
            else:
                terr1530 = bal1530 = None
            died3000 = rec["event"] == "died" and rec["tick"] is not None and rec["tick"] < 3000
            sp = None
            for nm in rec["names"]:
                sp = sp or spawn.get(nm)
            k = "early" if eb else "other"
            if eb:
                per[v]["early"] += 1
                first_t[v].append(bx[0]["t"])
                terr_at[v].append(bx[0]["terr"])
            if sp:
                rs = role_stat[(v, sp["role"] if not sp["role"].startswith("RANK_") else "RANK_*")]
                rs["n"].append(1)
                s630 = next((s for s in rec["snaps"] if s["t"] == 630), None)
                if s630 is not None:
                    rs["terr630"].append(s630["terr"])
                if terr1530 is not None:
                    rs["terr1530"].append(terr1530)
                    rs["bal1530"].append(bal1530)
                if s1530 is not None:
                    rs["boxed1530"].append(1 if (s1530["nb"] == 0 and s1530["neut"] == 0) else 0)
                rs["died3000"].append(1 if died3000 else 0)
                if sp["minAllyDist"] is not None and sp["minAllyDist"] >= 0 and terr1530 is not None:
                    mad_xy[v].append((sp["minAllyDist"], terr1530, (g["mid"], rec["roomIdx"])))
                role[(v, k)][sp["role"]] += 1
                if sp["minAllyDist"] is not None and sp["minAllyDist"] >= 0:
                    mad[(v, k)].append(sp["minAllyDist"])
            if terr1530 is not None:
                cmp_[(v, k)]["terr1530"].append(terr1530)
                cmp_[(v, k)]["bal1530"].append(bal1530)
            cmp_[(v, k)]["n"].append(1)
            cmp_[(v, k)]["died3000"].append(1 if died3000 else 0)
            cmp_[(v, k)]["peak"].append(rec["peak"] if rec["peak"] is not None else None)
            by_room[rec["roomIdx"]].append((eb, terr1530, bal1530))
        for ridx, lst in by_room.items():
            room = g["roomByIdx"][ridx]
            a = [x[1] for x in lst if x[0] and x[1] is not None]
            b = [x[1] for x in lst if not x[0] and x[1] is not None]
            if a and b:
                paired[v].append(statistics.median(a) - statistics.median(b))
            rooms.append({"mid": g["mid"], "cohort": g["cohort"], "ver": v, "outcome": room["outcome"], "nBots": len(lst),
                          "nEarly": sum(1 for x in lst if x[0]), "terr1530": sum(x[1] for x in lst if x[1] is not None),
                          "seeded": room["seeded"], "land": room["land"]})
        E = g["E"]
        if E and g["rroom"] is not None and is_team_room(g["rroom"]):
            final = {}
            for p, px in E["spawn"]:
                final[p] = px
            dup[v]["rooms"] += 1
            pix = Counter(final.values())
            if any(n >= 2 for n in pix.values()):
                dup[v]["roomsDup"] += 1
            if any(p not in final for p in E["ours"]):
                dup[v]["roomsNoSpawnCmd"] += 1
            dup[v]["botsNoSpawnCmd"] += sum(1 for p in E["ours"] if p not in final)
            dup[v]["bots"] += len(E["ours"])
    J["byVersion"] = {}
    for v in VERS:
        c = per[v]
        e, o = cmp_[(v, "early")], cmp_[(v, "other")]
        pd = paired[v]
        J["byVersion"][v] = {"bots": c["bots"], "early": wil(c["early"], c["bots"]), "firstT": dist(first_t[v]), "terrAtBox": dist(terr_at[v]),
                             "minAllyDistEarly": dist(mad[(v, "early")]), "minAllyDistOther": dist(mad[(v, "other")]),
                             "terr1530Early": dist(e["terr1530"]), "terr1530Other": dist(o["terr1530"]),
                             "bal1530Early": dist(e["bal1530"]), "bal1530Other": dist(o["bal1530"]),
                             "died3000Early": wil(sum(e["died3000"]), len(e["died3000"])), "died3000Other": wil(sum(o["died3000"]), len(o["died3000"])),
                             "pairedDiff": dist(pd), "pairedNeg": wil(sum(1 for x in pd if x < 0), len(pd)),
                             "dup": dict(dup[v])}
    J["dupSquad10"] = {k: sum(dup[v].get(k, 0) for v in ("Va", "Vb", "Vc")) for k in ("rooms", "roomsDup", "roomsNoSpawnCmd", "botsNoSpawnCmd", "bots")}
    J["sensitivity"] = {v: {f"{k}_{T_}": wil(sens[v][(k, T_)], per[v]["bots"]) for k in ("any", "small") for T_ in SENS_T} for v in VERS}
    J["squad10Early"] = wil(sum(sens[v][("small", 630)] for v in ("Va", "Vb", "Vc")), sum(per[v]["bots"] for v in ("Va", "Vb", "Vc")))
    J["squad10Small1530"] = wil(sum(sens[v][("small", 1530)] for v in ("Va", "Vb", "Vc")), sum(per[v]["bots"] for v in ("Va", "Vb", "Vc")))
    J["squad10Any1530"] = wil(sum(sens[v][("any", 1530)] for v in ("Va", "Vb", "Vc")), sum(per[v]["bots"] for v in ("Va", "Vb", "Vc")))
    J["roleStats"] = []
    for (v, r), rs in sorted(role_stat.items(), key=lambda x: (VERS.index(x[0][0]), -len(x[1]["n"]))):
        J["roleStats"].append({"ver": v, "role": r, "n": len(rs["n"]), "terr630": dist(rs["terr630"]), "terr1530": dist(rs["terr1530"]),
                               "bal1530": dist(rs["bal1530"]), "boxed1530": wil(sum(rs["boxed1530"]), len(rs["boxed1530"])),
                               "died3000": wil(sum(rs["died3000"]), len(rs["died3000"]))})
    J["minAllyDist"] = {}
    for v in VERS:
        xy = mad_xy[v]
        ok = len(xy) >= 20 and len({x for x, _, _ in xy}) > 3
        by_room = defaultdict(list)
        for x, y, k in xy:
            by_room[k].append((x, y))
        wx, wy, rx, ry = [], [], [], []
        for k, lst in by_room.items():
            if len(lst) < 5:
                continue
            mx = statistics.median(x for x, _ in lst)
            my = statistics.median(y for _, y in lst)
            rx.append(mx)
            ry.append(my)
            for x, y in lst:
                wx.append(x - mx)
                wy.append(y - my)
        room_info = {(r["mid"]): r for r in rooms if r["ver"] == v}
        sx, sy, lx, ly = [], [], [], []
        for k, lst in by_room.items():
            ri = room_info.get(k[0])
            if len(lst) < 5 or ri is None or not ri["land"] or not ri["seeded"]:
                continue
            mx = statistics.median(x for x, _ in lst)
            sx.append(mx)
            sy.append(sum(y for _, y in lst) / ri["land"])
            lx.append(mx)
            ly.append(ri["land"] / ri["seeded"])
        J["minAllyDist"][v] = {"spearmanRoomShare": BF.spearman(sx, sy) if ok and len(sx) >= 8 else None,
                               "spearmanRoomLandPerSeat": BF.spearman(lx, ly) if ok and len(lx) >= 8 else None,
                               "n": len(xy), "dist": dist([x for x, _, _ in xy]),
                               "spearmanTerr1530": BF.spearman([x for x, _, _ in xy], [y for _, y, _ in xy]) if ok else None,
                               "spearmanWithinRoom": BF.spearman(wx, wy) if ok and len(wx) >= 20 else None,
                               "spearmanRoomLevel": BF.spearman(rx, ry) if ok and len(rx) >= 8 else None, "rooms": len(rx)}
    J["roles"] = []
    for v in VERS:
        allr = Counter()
        for k in ("early", "other"):
            allr.update(role[(v, k)])
        for r, n in sorted(allr.items(), key=lambda x: -x[1]):
            J["roles"].append({"ver": v, "role": r, "n": n, "early": role[(v, "early")][r], "share": role[(v, "early")][r] / n})
    J["rooms"] = {}
    for coh in ("squad10", "squad20", "squad8"):
        R = [r for r in rooms if r["cohort"] == coh and r["nBots"] >= 5]
        W = [r["nEarly"] / r["nBots"] for r in R if r["outcome"] == "WIN"]
        Ls = [r["nEarly"] / r["nBots"] for r in R if r["outcome"] in LOSS]
        xs = [r["nEarly"] / r["nBots"] for r in R if r["terr1530"] > 0]
        ys = [r["terr1530"] / r["land"] for r in R if r["terr1530"] > 0]
        J["rooms"][coh] = {"rooms": len(R), "earlyShare": dist([r["nEarly"] / r["nBots"] for r in R]),
                           "win": dist(W), "loss": dist(Ls), "auc": BF.auc_ci(W, Ls) if W and Ls else None,
                           "spearmanShare1530": BF.spearman(xs, ys) if len(xs) >= 8 else None,
                           "withEarly": wil(sum(1 for r in R if r["nEarly"] > 0), len(R))}
    return J


# ----------------------------------------------------------------------------
# 号 × 90 拍窗口（真引擎）：受攻、出兵、清仓批、之后的结局
# ----------------------------------------------------------------------------

def bot_windows(games):
    rows = []
    deaths = []
    for g in games:
        E = g["E"]
        if not E or g["rroom"] is None or not is_team_room(g["rroom"]):
            continue
        T = E["snapT"]
        idx = E["snapIdx"]
        inc = {(r[0], r[1]): r for r in E["inc"]}
        death = {d[1]: d for d in E["deaths"]}
        spend = defaultdict(float)
        grp = defaultdict(list)
        for c in E["cmds"]:
            grp[(c[0], c[2])].append(c)
            if c[1] != 2:
                spend[(c[2], c[0] // 90 + 1)] += c[5] - c[6]
        don_out = defaultdict(float)
        for d_ in E["dons"]:
            if d_[13]:
                don_out[(d_[1], d_[0] // 90 + 1)] += d_[4] - d_[5]
        dump = defaultdict(lambda: [0, 0])     # (号, 窗口) -> [叠批清仓次数, 单发清仓次数]
        for (t, p), Lc in grp.items():
            atk = [c for c in Lc if c[1] != 2]
            if not atk or Lc[0][5] <= 0:
                continue
            frac = sum(c[5] - c[6] for c in atk) / Lc[0][5]
            if frac >= 0.5:
                dump[(p, t // 90 + 1)][0 if len(atk) >= 3 else 1] += 1
        peak_share = g["rroom"].get("primaryPeakShareSeen")
        for p in E["ours"]:
            arr = E["bots"][str(p)]
            rec = E["recOf"].get(p)
            for i, t in enumerate(T):
                if t < 1500 or t + 90 > E["lastTick"]:
                    continue
                terr, bal, alive, state = arr[i][:4]
                if not alive or state == 2 or terr < 200:
                    continue
                w = t // 90 + 1
                r = inc.get((p, w))
                hum, hum_n, ai, ai_n, sq, sq_n = (r[2], r[3], r[4], r[5], r[6], r[7]) if r else (0, 0, 0, 0, 0, 0)
                d = death.get(p)
                td = d[0] if d else None
                j = idx.get(t + 180)
                dm = dump.get((p, w), (0, 0))
                rows.append({"mid": g["mid"], "cohort": g["cohort"], "ver": g["ver"], "p": p, "t": t, "terr": terr, "bal": bal,
                             "dens": bal / terr, "hum": hum, "humN": hum_n, "ai": ai, "aiN": ai_n, "sq": sq, "sqN": sq_n,
                             "ratio": hum / max(1, bal), "humPerLand": hum / max(1, terr), "die360": td is not None and td <= t + 360,
                             "die180": td is not None and td <= t + 180,
                             "seen360": t + 360 <= E["lastTick"] or (td is not None and td <= t + 360),
                             "ownfrac": spend.get((p, w), 0.0) / max(1, bal), "terr180": arr[j][0] if j is not None else None,
                             "stackDump": dm[0] > 0, "singleDump": dm[1] > 0 and dm[0] == 0,
                             "outcome": g["rroom"]["outcome"], "lead": peak_share is not None and peak_share >= 0.35})
        for d in E["deaths"]:
            t, p, terr_prev, bal_prev, attackers = d
            w = t // 90 + 1
            a = inc.get((p, w))
            b = inc.get((p, w - 1))
            hum_n = max(a[3] if a else 0, b[3] if b else 0)
            hum = (a[2] if a else 0) + (b[2] if b else 0)
            ai = (a[4] if a else 0) + (b[4] if b else 0)
            sq = (a[6] if a else 0) + (b[6] if b else 0)
            i = idx.get((t // 90 - 2) * 90)
            dens_before = None
            if i is not None and E["bots"][str(p)][i][0] > 0:
                dens_before = E["bots"][str(p)][i][1] / E["bots"][str(p)][i][0]
            if hum_n >= 2:
                kind = "multiHuman"
            elif hum_n == 1:
                kind = "singleHuman"
            elif sq > 0:
                kind = "squadMate"
            elif ai > 0:
                kind = "aiOnly"
            else:
                kind = "other"
            arr_p = E["bots"][str(p)]
            fc = FLOOR_CAP[g["ver"]]
            cand = [k for k, tt in enumerate(T) if tt <= t]
            i0 = None
            for k in reversed(cand):
                if T[k] < 630:
                    break
                if arr_p[k][0] >= 200 and arr_p[k][1] / arr_p[k][0] >= fc:
                    i0 = k
                    break
            path = {"path": "neverAbove"}
            if i0 is not None:
                gap = t - T[i0]
                b0 = max(1, arr_p[i0][1])
                ws = range(T[i0] // 90 + 1, t // 90 + 2)
                atk = sum(spend.get((p, w_), 0.0) for w_ in ws)
                don = sum(don_out.get((p, w_), 0.0) for w_ in ws)
                hin = sum(inc[(p, w_)][2] for w_ in ws if (p, w_) in inc)
                ain = sum(inc[(p, w_)][4] for w_ in ws if (p, w_) in inc)
                sdump = sum(dump[(p, w_)][0] for w_ in ws if (p, w_) in dump)
                tot_ = atk + don + hin + ain
                dom = "none" if tot_ <= 0 else max((("ownAttack", atk), ("ownDonation", don), ("incoming", hin + ain)), key=lambda x: x[1])[0]
                path = {"path": "fast" if gap <= 720 else "slow", "gap": gap, "b0": b0, "atk": atk / b0, "don": don / b0,
                        "hum": hin / b0, "ai": ain / b0, "dom": dom, "stackDump": sdump > 0, "t0": T[i0]}
            deaths.append({**path, "mid": g["mid"], "cohort": g["cohort"], "ver": g["ver"], "p": p, "t": t, "kind": kind, "hum_": hum, "ai_": ai, "sq": sq,
                           "densBefore": dens_before, "balPrev": bal_prev, "terrPrev": terr_prev,
                           "killerOur": bool(attackers and attackers[0][4]), "outcome": g["rroom"]["outcome"],
                           "lead": peak_share is not None and peak_share >= 0.35})
    return rows, deaths


def die_tab(R, buckets):
    out = []
    for name, f in buckets:
        Sx = [r for r in R if f(r) and r["seen360"]]
        d = sum(1 for r in Sx if r["die360"])
        out.append({"bucket": name, **wil(d, len(Sx)), "medDens": q([r["dens"] for r in Sx], .5), "medRatio": q([r["ratio"] for r in Sx], .5)})
    return out


RATIO_B = [("0（无真人进攻）", lambda r: r["hum"] == 0), ("0–0.25", lambda r: 0 < r["ratio"] < .25), ("0.25–0.5", lambda r: .25 <= r["ratio"] < .5),
           ("0.5–1", lambda r: .5 <= r["ratio"] < 1), ("1–2", lambda r: 1 <= r["ratio"] < 2), ("≥2", lambda r: r["ratio"] >= 2)]
HUMN_B = [("0", lambda r: r["humN"] == 0), ("1", lambda r: r["humN"] == 1), ("2", lambda r: r["humN"] == 2), ("≥3", lambda r: r["humN"] >= 3)]
DENS_B = [("<30", lambda r: r["dens"] < 30), ("30–60", lambda r: 30 <= r["dens"] < 60), ("60–78", lambda r: 60 <= r["dens"] < 78),
          ("78–88", lambda r: 78 <= r["dens"] < 88), ("88–100", lambda r: 88 <= r["dens"] < 100), ("≥100", lambda r: r["dens"] >= 100)]
OWN_B = [("<5%", lambda r: r["ownfrac"] < .05), ("5–30%", lambda r: .05 <= r["ownfrac"] < .3), ("≥30%", lambda r: r["ownfrac"] >= .3)]


def death_paths(Dd) -> dict:
    n = len(Dd)
    fast = [d for d in Dd if d["path"] == "fast"]
    slow = [d for d in Dd if d["path"] == "slow"]
    never = [d for d in Dd if d["path"] == "neverAbove"]
    dom = Counter(d["dom"] for d in fast)
    return {"n": n, "neverAbove": wil(len(never), n), "slow": wil(len(slow), n), "fast": wil(len(fast), n),
            "fastGap": dist([d["gap"] for d in fast]), "slowGap": dist([d["gap"] for d in slow]),
            "fastAtk": dist([d["atk"] for d in fast]), "fastDon": dist([d["don"] for d in fast]), "fastHum": dist([d["hum"] for d in fast]),
            "fastDomOwnAttack": wil(dom["ownAttack"], len(fast)), "fastDomOwnDonation": wil(dom["ownDonation"], len(fast)),
            "fastDomIncoming": wil(dom["incoming"], len(fast)), "fastDomNone": wil(dom["none"], len(fast)),
            "fastOwnGe50": wil(sum(1 for d in fast if d["atk"] + d["don"] >= 0.5), len(fast)),
            "fastAtkGe50": wil(sum(1 for d in fast if d["atk"] >= 0.5), len(fast)),
            "fastStackDump": wil(sum(1 for d in fast if d["stackDump"]), len(fast)),
            "fastHumLt50": wil(sum(1 for d in fast if d["hum"] < 0.5), len(fast))}


DUAL_REVIEW = ("G04", "B039", "B041", "B043", "B033", "B045", "B003", "A057", "A049")   # 任务卡 M3 点名的双审重叠局
LEAD_SHARE = 0.35
LEAD_WIN = 1800


def h5_lead(games) -> dict:
    """
    领先局：真引擎逐 90 拍的队伍领土。两个口径——
      share35 ：主队领土份额在 t≥1500 的某张快照 ≥35%（统筹的口径；两队局里 35% 其实是落后）；
      rank1   ：同一张快照上主队份额 ≥35% 且是全场领土最多的队。
    对 rank1 且最后输掉的房间，从“领先时的份额峰值”往后看 LEAD_WIN 拍：掉的地是谁的、我方号的收支与受攻。
    """
    out_rows = []
    for g in games:
        E = g["E"]
        room = g["rroom"]
        if not E or room is None or not is_team_room(room) or g["cohort"] not in ("squad10", "squad20"):
            continue
        prim = room.get("primaryTeam")
        if prim is None:
            continue
        T = E["snapT"]
        land = E["info"]["land"]
        nT = len(E["teamTerr"][0])
        if prim >= nT:
            continue
        sh = [E["teamTerr"][i][prim] / land for i in range(len(T))]
        idxs = [i for i, t in enumerate(T) if t >= 1500]
        if not idxs:
            continue
        r1 = [i for i in idxs if sh[i] >= LEAD_SHARE and E["teamTerr"][i][prim] >= max(E["teamTerr"][i][k] for k in range(1, nT) if k != prim)]
        ipk_all = max(idxs, key=lambda i: sh[i])
        log_peak = room.get("primaryPeakShareSeen")
        rec = {"mid": g["mid"], "cohort": g["cohort"], "ver": g["ver"], "outcome": room["outcome"], "teams": room.get("tBest"),
               "peakEngine": sh[ipk_all], "peakT": T[ipk_all], "peakLog": log_peak,
               "share35": sh[ipk_all] >= LEAD_SHARE, "rank1": bool(r1), "rank1Snaps": len(r1), "rank1First": T[r1[0]] if r1 else None,
               "leadLog": log_peak is not None and log_peak >= LEAD_SHARE}
        if r1:
            ipk = max(r1, key=lambda i: sh[i])
            t0 = T[ipk]
            t1 = min(t0 + LEAD_WIN, E["lastTick"])
            j = max(i for i in range(len(T)) if T[i] <= t1)
            ours = [pp for pp in E["ours"] if E["team"][pp] == prim]
            oset = set(ours)
            def our_terr(i):
                return sum(E["bots"][str(pp)][i][0] for pp in ours if E["bots"][str(pp)][i][2])
            def our_alive(i):
                return sum(1 for pp in ours if E["bots"][str(pp)][i][2])
            bal0 = sum(E["bots"][str(pp)][ipk][1] for pp in ours if E["bots"][str(pp)][ipk][2])
            team0, team1 = E["teamTerr"][ipk][prim], E["teamTerr"][j][prim]
            o0, o1 = our_terr(ipk), our_terr(j)
            drop_team = team0 - team1
            drop_ours = o0 - o1
            w0, w1 = t0 // 90 + 1, t1 // 90
            atk = sum(c[5] - c[6] for c in E["cmds"] if c[2] in oset and c[1] != 2 and t0 <= c[0] < t1)
            hum = sum(r[2] for r in E["inc"] if r[0] in oset and w0 <= r[1] <= w1)
            enemy_teams = {E["team"][r[8]] for r in E["inc"] if r[0] in oset and w0 <= r[1] <= w1 and r[8] is not None and 0 <= r[8] < len(E["team"])
                           and E["team"][r[8]] != prim and r[9] > 0}
            grp = defaultdict(list)
            for c in E["cmds"]:
                if c[2] in oset and c[1] != 2 and t0 <= c[0] < t1:
                    grp[(c[0], c[2])].append(c)
            dumps = sum(1 for Lc in grp.values() if len(Lc) >= 3 and Lc[0][5] > 0 and sum(c[5] - c[6] for c in Lc) / Lc[0][5] >= 0.5)
            below20 = next((T[i] for i in range(ipk, len(T)) if sh[i] < 0.20), None)
            a0, a1 = our_alive(ipk), our_alive(j)
            rec.update({"t0": t0, "share0": sh[ipk], "shareAfter": sh[j], "span": T[j] - t0,
                        "ourAlive0": a0, "ourAlive1": a1, "wild0": E["teamN"][ipk][prim] - a0, "wild1": E["teamN"][j][prim] - a1,
                        "ourTerrShare0": o0 / team0 if team0 else None,
                        "dropTeam": drop_team, "dropOurs": drop_ours, "dropWild": drop_team - drop_ours,
                        "oursShareOfDrop": drop_ours / drop_team if drop_team > 0 else None,
                        "ourTerrChange": (o1 - o0) / o0 if o0 else None,
                        "wildTerrChange": ((team1 - o1) - (team0 - o0)) / (team0 - o0) if team0 - o0 > 0 else None,
                        "atkOverBal": atk / bal0 if bal0 else None, "humOverBal": hum / bal0 if bal0 else None,
                        "enemyTeams": len(enemy_teams), "stackDumps": dumps,
                        "peakToBelow20": (below20 - t0) if below20 is not None else None})
        out_rows.append(rec)
    J = {"rows": [r for r in out_rows if r["rank1"]], "byCohort": {}, "window": LEAD_WIN}
    for coh in ("squad10", "squad20"):
        R = [r for r in out_rows if r["cohort"] == coh]
        S35 = [r for r in R if r["share35"]]
        R1 = [r for r in R if r["rank1"]]
        Lo = [r for r in R1 if r["outcome"] in LOSS]
        Wn = [r for r in R1 if r["outcome"] == "WIN"]
        def oc(X):
            c = Counter(r["outcome"] for r in X)
            return {"n": len(X), "win": c["WIN"], "loss": c["LOSS"] + c["LOSS_LIKELY"], "unknown": c["UNKNOWN"],
                    "lossShare": wil(c["LOSS"] + c["LOSS_LIKELY"], c["WIN"] + c["LOSS"] + c["LOSS_LIKELY"])}
        by_t = []
        for name, f in (("2 队", lambda r: r["teams"] == 2), ("3 队", lambda r: r["teams"] == 3), ("≥4 队", lambda r: (r["teams"] or 0) >= 4)):
            by_t.append({"teams": name, "rooms": sum(1 for r in R if f(r)), "share35": oc([r for r in S35 if f(r)]), "rank1": oc([r for r in R1 if f(r)])})
        Ld = [r for r in Lo if r.get("dropTeam") is not None and r["dropTeam"] > 0]
        extra = [r for r in S35 if not r["rank1"]]
        J["byCohort"][coh] = {"rooms": len(R), "share35": oc(S35), "leadLog": oc([r for r in R if r["leadLog"]]), "rank1": oc(R1), "byTeams": by_t,
                              "neverRank1": {"n": len(extra), "twoTeam": sum(1 for r in extra if r["teams"] == 2), "loss": sum(1 for r in extra if r["outcome"] in LOSS)},
                              "rank1Snaps": dist([r["rank1Snaps"] for r in R1]),
                              "loss": {"n": len(Lo), "withDrop": len(Ld),
                                       "share0": dist([r["share0"] for r in Lo]), "shareAfter": dist([r["shareAfter"] for r in Lo]),
                                       "ourTerrShare0": dist([r["ourTerrShare0"] for r in Lo if r["ourTerrShare0"] is not None]),
                                       "oursShareOfDrop": dist([r["oursShareOfDrop"] for r in Ld]),
                                       "oursOverProportional": wil(sum(1 for r in Ld if r["oursShareOfDrop"] > r["ourTerrShare0"]), len(Ld)),
                                       "oursMajorityOfDrop": wil(sum(1 for r in Ld if r["oursShareOfDrop"] > 0.5), len(Ld)),
                                       "wildMajorityOfDrop": wil(sum(1 for r in Ld if r["oursShareOfDrop"] <= 0.5), len(Ld)),
                                       "ourTerrChange": dist([r["ourTerrChange"] for r in Lo if r["ourTerrChange"] is not None]),
                                       "wildTerrChange": dist([r["wildTerrChange"] for r in Lo if r["wildTerrChange"] is not None]),
                                       "atkOverBal": dist([r["atkOverBal"] for r in Lo if r["atkOverBal"] is not None]),
                                       "humOverBal": dist([r["humOverBal"] for r in Lo if r["humOverBal"] is not None]),
                                       "enemyTeamsGe2": wil(sum(1 for r in Lo if r["enemyTeams"] >= 2), len(Lo)),
                                       "noHumanFire": wil(sum(1 for r in Lo if r["humOverBal"] is not None and r["humOverBal"] < 0.1), len(Lo)),
                                       "anyStackDump": wil(sum(1 for r in Lo if r["stackDumps"] > 0), len(Lo)),
                                       "ourDeaths": dist([r["ourAlive0"] - r["ourAlive1"] for r in Lo]),
                                       "peakToBelow20": dist([r["peakToBelow20"] for r in Lo if r.get("peakToBelow20") is not None])},
                              "win": {"n": len(Wn), "atkOverBal": dist([r["atkOverBal"] for r in Wn if r["atkOverBal"] is not None]),
                                      "humOverBal": dist([r["humOverBal"] for r in Wn if r["humOverBal"] is not None]),
                                      "ourTerrShare0": dist([r["ourTerrShare0"] for r in Wn if r["ourTerrShare0"] is not None])}}
    return J


def is_focus(r) -> bool:
    return r["humN"] >= 2 and r["ratio"] >= 0.25


def h5(rows, deaths) -> dict:
    J = {}
    for coh in ("squad10", "squad20"):
        R = [r for r in rows if r["cohort"] == coh]
        F = [r for r in R if is_focus(r)]
        Fs = [r for r in F if r["seen360"]]
        Dd = [d for d in deaths if d["cohort"] == coh]
        kinds = Counter(d["kind"] for d in Dd)
        below = [d for d in Dd if d["densBefore"] is not None]
        nb = sum(1 for d in below if d["densBefore"] < FLOOR_CAP[d["ver"]])
        lead_d = [d for d in Dd if d["lead"]]
        by_bot = defaultdict(list)
        for r in F:
            by_bot[(r["mid"], r["p"])].append(r)
        n_any = n_floor = n_ratio1 = 0
        for d in Dd:
            fr = [r for r in by_bot.get((d["mid"], d["p"]), ()) if d["t"] - 360 <= r["t"] <= d["t"]]
            if fr:
                n_any += 1
            if any(r["dens"] >= FLOOR_CAP[r["ver"]] for r in fr):
                n_floor += 1
            if any(r["dens"] >= FLOOR_CAP[r["ver"]] and r["ratio"] >= 1 for r in fr):
                n_ratio1 += 1
        two = []
        for rn, rf in RATIO_B[2:]:
            for dn, dlo, dhi in (("<60", 0, 60), ("60–88", 60, 88), ("≥88", 88, 1e9)):
                Sx = [r for r in R if rf(r) and dlo <= r["dens"] < dhi and r["seen360"]]
                two.append({"ratio": rn, "dens": dn, **wil(sum(1 for r in Sx if r["die360"]), len(Sx))})
        # 同一受攻强度下，开火窗口内自己有没有出兵
        J[coh] = {"windows": len(R), "bots": len({(r["mid"], r["p"]) for r in R}), "games": len({r["mid"] for r in R}),
                  "byHumN": die_tab(R, HUMN_B), "byRatio": die_tab(R, RATIO_B),
                  "focus": {"windows": len(F), "bots": len({(r["mid"], r["p"]) for r in F}), "games": len({r["mid"] for r in F}),
                            "die360": wil(sum(1 for r in Fs if r["die360"]), len(Fs)),
                            "shareOfWindows": len(F) / len(R) if R else None,
                            "byDens": die_tab(F, DENS_B), "byOwn": die_tab(F, OWN_B),
                            "humPerLand": dist([r["humPerLand"] for r in F]),
                            "humPerLandGtFloor": wil(sum(1 for r in F if r["humPerLand"] > FLOOR_CAP[r["ver"]]), len(F)),
                            "atOrAboveFloor": die_tab([r for r in F if r["dens"] >= FLOOR_CAP[r["ver"]]],
                                                      [("受攻比 <0.5", lambda r: r["ratio"] < .5), ("0.5–1", lambda r: .5 <= r["ratio"] < 1), ("≥1", lambda r: r["ratio"] >= 1)]),
                            "passiveShare": wil(sum(1 for r in F if r["ownfrac"] < .05), len(F)),
                            "belowFloorShare": wil(sum(1 for r in F if r["dens"] < FLOOR_CAP[r["ver"]]), len(F))},
                  "ratioDens": two,
                  "deaths": {"n": len(Dd), **{k: kinds[k] for k in ("multiHuman", "singleHuman", "aiOnly", "squadMate", "other")},
                             "multiShare": wil(kinds["multiHuman"], len(Dd)),
                             "afterFocus": wil(n_any, len(Dd)), "afterFocusAtFloor": wil(n_floor, len(Dd)),
                             "afterFocusAtFloorRatio1": wil(n_ratio1, len(Dd)),
                             "belowFloor": wil(nb, len(below)), "densBefore": dist([d["densBefore"] for d in below]),
                             "balAtDeath": dist([d["balPrev"] for d in Dd])},
                  "path": death_paths(Dd),
                  "lead": {"rooms": len({d["mid"] for d in lead_d} | {r["mid"] for r in R if r["lead"]}),
                           "deaths": len(lead_d), "multiShare": wil(sum(1 for d in lead_d if d["kind"] == "multiHuman"), len(lead_d)),
                           "outcomes": dict(Counter({r["mid"]: r["outcome"] for r in R if r["lead"]}.values()))}}
        # 把受攻比切细后分层：同一受攻比档内，比较“线上 vs 线下”、“Vb vs Va”
        fine = [(.25, .5), (.5, .75), (.75, 1), (1, 1.5), (1.5, 2), (2, 3), (3, 1e9)]
        def strata_of(g1, g2):
            out_ = []
            for lo, hi in fine:
                Sx = [r for r in Fs if lo <= r["ratio"] < hi]
                A_ = [r for r in Sx if g1(r)]
                B_ = [r for r in Sx if g2(r)]
                out_.append((sum(1 for r in A_ if r["die360"]), len(A_), sum(1 for r in B_ if r["die360"]), len(B_)))
            return out_
        st_floor = strata_of(lambda r: r["dens"] < FLOOR_CAP[r["ver"]], lambda r: r["dens"] >= FLOOR_CAP[r["ver"]])
        cm = {"floor": {**S.cmh(st_floor), "n1": sum(x[1] for x in st_floor), "n2": sum(x[3] for x in st_floor),
                        "k1": sum(x[0] for x in st_floor), "k2": sum(x[2] for x in st_floor)}}
        if coh == "squad10":
            st_ver = strata_of(lambda r: r["ver"] == "Va", lambda r: r["ver"] == "Vb")
            cm["version"] = {**S.cmh(st_ver), "n1": sum(x[1] for x in st_ver), "n2": sum(x[3] for x in st_ver),
                             "k1": sum(x[0] for x in st_ver), "k2": sum(x[2] for x in st_ver)}
        J[coh]["cmh"] = cm
        J[coh]["focus"]["ratioByVer"] = {ver: dist([r["ratio"] for r in F if r["ver"] == ver]) for ver in VERS if any(r["ver"] == ver for r in F)}
        for ver in (("Va", "Vb") if coh == "squad10" else ("c110",)):
            Fv = [r for r in F if r["ver"] == ver]
            J[coh]["focus"]["byDens_" + ver] = die_tab(Fv, [("<60", lambda r: r["dens"] < 60), ("60–88", lambda r: 60 <= r["dens"] < 88), ("≥88", lambda r: r["dens"] >= 88)])
    return J


# ----------------------------------------------------------------------------
# 假设 ⑥：squad20 拆队与和平投票
# ----------------------------------------------------------------------------

def h6(games, rows, deaths) -> dict:
    J = {}
    split = defaultdict(Counter)
    assist = Counter()
    peace_logs = []
    room_teams = []
    peace_kinds = Counter()
    sq_att = Counter()
    dose = defaultdict(Counter)
    prim2 = defaultdict(Counter)
    dose_w = defaultdict(list)
    dose_e = defaultdict(list)
    rp = {"squad10": Counter(), "squad20": Counter()}
    for g in games:
        coh = g["cohort"]
        E = g["E"]
        n_peace = [e for e in g["events"] if e["type"] == "PEACE"]
        if n_peace:
            room = g["roomByIdx"][g["mainRoom"]]
            lands = []
            p = os.path.join(L.bundle_dir(g["card"]), "in_game.log")
            with open(p, encoding="utf-8", errors="replace") as f:
                for line in f:
                    if "[HL-PEACE]" in line:
                        m = re.search(r"teamLand=([0-9.]+)%", line)
                        if m:
                            lands.append(float(m.group(1)))
                        peace_kinds["initiated" if "initiated peace vote" in line else "votedYes" if "voted YES" in line else "other"] += 1
            peace_logs.append({"mid": g["mid"], "n": len(n_peace), "kinds": dict(Counter(e["kind"] for e in n_peace)),
                               "tMin": min(e["t"] for e in n_peace), "tMax": max(e["t"] for e in n_peace),
                               "landMin": min(lands) if lands else None, "landMax": max(lands) if lands else None,
                               "outcome": room["outcome"], "hasReplay": bool(g["replay"]), "timeUtc": g["card"]["timeUtc"]})
        if g["replay"] and coh in rp:
            ours = {rec["me"] for rec in g["bots"] if rec["inReplay"]}
            for (tick, cid, player, a, c) in g["replay"]["cmds"]:
                if cid == 5 and a == RP.PEACE_CALL:
                    rp[coh]["callOurs" if player in ours else "callWild"] += 1
                elif cid == 7:
                    rp[coh]["voteOurs" if player in ours else "voteWild"] += 1
            rp[coh]["games"] += 1
        if coh != "squad20":
            continue
        room = g["roomByIdx"][g["mainRoom"]]
        if is_team_room(room):
            nt = len([k for k, n in room["teams"].items() if n > 0])
            key = "1" if nt == 1 else "2" if nt == 2 else "3" if nt == 3 else "≥4"
            c = split[key]
            c["rooms"] += 1
            c["bots"] += room["nBots"]
            if room.get("tBest"):
                room_teams.append(room["tBest"])
            if room["outcome"] == "WIN":
                c["primWin"] += 1
            if room["outcome"] in ("WIN",) + LOSS:
                c["primKnown"] += 1
            if room.get("ourTeamsIncludeWinner") is True:
                c["anyWin"] += 1
            if room.get("ourTeamsIncludeWinner") is not None:
                c["anyKnown"] += 1
            c["expPrim"] += 1.0 / room["tBest"] if room.get("tBest") else 0
            c["expAny"] += nt / room["tBest"] if room.get("tBest") and room.get("ourTeamsIncludeWinner") is not None else 0
            if room.get("winner") is not None and room.get("tBest"):
                for tk, to in room["teamOutcomes"].items():
                    nb_ = to["nBots"]
                    if nb_ <= 0:
                        continue
                    kb = "1" if nb_ == 1 else "2–3" if nb_ <= 3 else "4–6" if nb_ <= 6 else "≥7"
                    dose[kb]["n"] += 1
                    dose[kb]["win"] += 1 if str(room["winner"]) == str(tk) else 0
                    dose[kb]["exp"] += 1.0 / room["tBest"]
                    dose[kb]["bots"] += nb_
                    dose_w[kb].append(1 if str(room["winner"]) == str(tk) else 0)
                    dose_e[kb].append(1.0 / room["tBest"])
                    is_prim = str(tk) == str(room["primaryTeam"])
                    kp = "primary" if is_prim else "secondary"
                    if nt >= 2:
                        prim2[kp]["n"] += 1
                        prim2[kp]["win"] += 1 if str(room["winner"]) == str(tk) else 0
                        prim2[kp]["exp"] += 1.0 / room["tBest"]
                        prim2[kp]["bots"] += nb_
                        dose_w[kp].append(1 if str(room["winner"]) == str(tk) else 0)
                        dose_e[kp].append(1.0 / room["tBest"])
        me2rec = {}
        for rec in g["bots"]:
            me2rec[(rec["roomIdx"], rec["me"])] = rec
        for e in g["events"]:
            if e["type"] != "ASSIST" or e["botRec"] is None:
                continue
            b = e["botRec"]
            al = me2rec.get((b["roomIdx"], e["ally"]))
            if al is None or al["team"] is None or b["team"] is None:
                assist["unknown"] += 1
            elif al["team"] == b["team"]:
                assist["same"] += 1
            else:
                assist["cross"] += 1
        if E and g["rroom"] is not None and is_team_room(g["rroom"]):
            for r in E["inc"]:
                if r[6] > 0:
                    sq_att["windows"] += 1
                    sq_att["troops"] += r[6]
            for r in E["out"]:
                sq_att["outHuman"] += r[3]
                sq_att["outSquad"] += r[5]
                sq_att["outAi"] += r[4]
                sq_att["outNeutral"] += r[2]
            sq_att["games"] += 1
            if g["replayTicks"] >= 1500:
                sq_att["gamesGe1500"] += 1
    J["split"] = [{"teams": k, "rooms": c["rooms"], "bots": c["bots"], "prim": wil(c["primWin"], c["primKnown"]),
                   "any": wil(c["anyWin"], c["anyKnown"]), "expPrim": c["expPrim"] / c["rooms"] if c["rooms"] else None,
                   "expAny": c["expAny"] / c["anyKnown"] if c["anyKnown"] else None}
                  for k, c in sorted(split.items())]
    J["dose"] = [{"botsOnTeam": k, "teams": dose[k]["n"], "bots": dose[k]["bots"], "win": wil(dose[k]["win"], dose[k]["n"]),
                  "expected": dose[k]["exp"] / dose[k]["n"] if dose[k]["n"] else None,
                  "excess": S.excess_test(dose_w[k], dose_e[k]) if dose[k]["n"] else None}
                 for k in ("1", "2–3", "4–6", "≥7")]
    J["primaryVsSecondary"] = {k: {"teams": c["n"], "bots": c["bots"], "win": wil(c["win"], c["n"]), "expected": c["exp"] / c["n"] if c["n"] else None,
                                   "excess": S.excess_test(dose_w[k], dose_e[k])}
                               for k, c in prim2.items()}
    J["assist"] = {"same": assist["same"], "cross": assist["cross"], "unknown": assist["unknown"],
                   "crossShare": wil(assist["cross"], assist["same"] + assist["cross"])}
    lines = open(os.path.join(DATA, "src", "strategy", STRAT["c110"]), encoding="utf-8").read().split("\n")
    d0 = next((i for i, x in enumerate(lines) if re.match(r"\s*tryPeaceVote\(g\) \{", x)), None)
    J["peaceCode"] = {"file": STRAT["c110"], "defLine": d0 + 1 if d0 is not None else None,
                      "guardLine": d0 + 2 if d0 is not None and "findBossId(g) < 0) return" in lines[d0 + 1] else None,
                      "minTickLine": next((i + 1 for i in range(d0, d0 + 6) if "g.t < 1610" in lines[i]), None) if d0 is not None else None}
    J["teamRooms"] = sum(c["rooms"] for c in split.values())
    J["splitRooms"] = sum(c["rooms"] for k, c in split.items() if k != "1")
    J["peaceLogs"] = sorted(peace_logs, key=lambda x: x["mid"])
    J["peaceLogTotal"] = sum(x["n"] for x in peace_logs)
    J["peaceLineKinds"] = {k: peace_kinds[k] for k in ("initiated", "votedYes", "other")}
    sq20 = sorted([g for g in games if g["cohort"] == "squad20"], key=lambda g: g["card"]["timeUtc"])
    last_peace = max((x["timeUtc"] for x in peace_logs), default=None)
    nxt = next((g for g in sq20 if last_peace and g["card"]["timeUtc"] > last_peace), None)
    J["peaceNext"] = {"mid": nxt["mid"], "timeUtc": nxt["card"]["timeUtc"]} if nxt else None
    J["peaceLast"] = next(({"mid": x["mid"], "timeUtc": x["timeUtc"]} for x in peace_logs if x["timeUtc"] == last_peace), None)
    J["squad20NoPeace"] = sum(1 for g in sq20 if g["mid"] not in {x["mid"] for x in peace_logs})
    J["peaceLogBundles"] = len(peace_logs)
    J["peaceLogBundlesWithReplay"] = sum(1 for x in peace_logs if x["hasReplay"])
    J["peaceKinds"] = dict(Counter(k for x in peace_logs for k in x["kinds"]))
    J["peaceReplay"] = {k: dict(v) for k, v in rp.items()}
    J["peaceOursInReplay"] = sum(v.get("callOurs", 0) + v.get("voteOurs", 0) for v in rp.values())
    J["roomTeams"] = {"min": min(room_teams) if room_teams else None, "max": max(room_teams) if room_teams else None}
    tot_out = sq_att["outHuman"] + sq_att["outSquad"]
    J["squadAttacks"] = {"gamesGe1500": sq_att["gamesGe1500"], "games": sq_att["games"], "windows": sq_att["windows"], "troops": sq_att["troops"], "outHuman": sq_att["outHuman"],
                         "outSquad": sq_att["outSquad"], "outAi": sq_att["outAi"], "outNeutral": sq_att["outNeutral"],
                         "squadShareOfHumanDirected": sq_att["outSquad"] / tot_out if tot_out else None}
    D20 = [d for d in deaths if d["cohort"] == "squad20"]
    J["deaths20"] = {"n": len(D20), "killerOur": wil(sum(1 for d in D20 if d["killerOur"]), len(D20)),
                     "anySquadTroops": wil(sum(1 for d in D20 if d["sq"] > 0), len(D20))}
    R20 = [r for r in rows if r["cohort"] == "squad20"]
    J["windows20"] = {"n": len(R20), "withSquadAttack": wil(sum(1 for r in R20 if r["sq"] > 0), len(R20)),
                      "withHumanAttack": wil(sum(1 for r in R20 if r["hum"] > 0), len(R20))}
    return J


# ----------------------------------------------------------------------------
# 附加项 X：执行层——指令成批落地与延迟
# ----------------------------------------------------------------------------

def hx(games, rows) -> dict:
    J = {}
    hist = {(w, c): Counter() for w in ("ours", "wild") for c in ("squad10", "squad20")}
    per_game = []
    lagsum = defaultdict(list)
    dumps = defaultdict(Counter)
    dump_frac = defaultdict(list)
    drop = defaultdict(Counter)
    drop_total = Counter()
    drop_listed = Counter()
    tool = Counter()
    drop_cov = Counter()
    for g in games:
        coh = g["cohort"]
        an = L.load_json(g["card"], "anomalies.json")
        evs = D.drop30_full(g["card"])          # 全量；anomalies.json 的 drop30Events 只列前 30 条
        drop_total[coh] += len(evs)
        listed_ = [(e["bot"], e["t0"]) for e in an.get("drop30Events", [])]
        drop_listed[coh] += len(listed_)
        tool["bundles"] += 1
        tool["countMatches"] += 1 if len(evs) == an.get("drop30Count") else 0
        tool["firstThirtySorted"] += 1 if listed_ == sorted((e["bot"], e["t0"]) for e in evs)[:30] else 0
        if len(evs) > len(listed_):
            tool["truncated"] += 1
            tool["botsWithDrop"] += len({e["bot"] for e in evs})
            tool["botsHidden"] += len({e["bot"] for e in evs} - {b_ for b_, _ in listed_})
        r = g["replay"]
        E = g["E"]
        if not r or not E or coh not in ("squad10", "squad20"):
            continue
        ours = set(E["ours"])
        grp = Counter()
        for (tick, cid, player, a, c) in r["cmds"]:
            if tick < 0 or cid not in (1, 2, 3, 4, 10):
                continue
            grp[(tick, player)] += 1
        n_our = n_our3 = 0
        for (tick, player), n in grp.items():
            who = "ours" if player in ours else "wild"
            hist[(who, coh)][n] += 1
            if who == "ours":
                n_our += n
                if n >= 3:
                    n_our3 += n
        room = g["rroom"]
        if n_our >= 50 and len(ours) >= 5 and room is not None:
            per_game.append({"mid": g["mid"], "cohort": coh, "ver": g["ver"], "outcome": room["outcome"], "share3": n_our3 / n_our, "n": n_our})
        eg = defaultdict(list)
        for c in E["cmds"]:
            eg[(c[0], c[2])].append(c)
        for (t, p), Lc in eg.items():
            atk = [c for c in Lc if c[1] != 2]
            if len(atk) < 3 or Lc[0][5] <= 0:
                continue
            frac = sum(c[5] - c[6] for c in atk) / Lc[0][5]
            ph = "<1500" if t < 1500 else "1500–2399" if t < 2400 else "2400–4283" if t < 4284 else "≥4284"
            dumps[(coh, ph)]["stacks"] += 1
            if frac >= 0.5:
                dumps[(coh, ph)]["dump50"] += 1
                dumps[(coh, "all")]["dump50"] += 1
                dumps[(coh, "all")]["games_" + g["mid"]] = 1
                dumps[(coh, "all")]["bots_" + g["mid"] + "_" + str(p)] = 1
                if t >= 1500:
                    dump_frac[coh].append(frac)
                    dumps[(coh, "core")]["dump50"] += 1
            if frac >= 0.9:
                dumps[(coh, ph)]["dump90"] += 1
        byp = defaultdict(list)
        for c in E["cmds"]:
            byp[c[2]].append(c)
        for e in evs:
            rec = g["name2bot"].get(e["bot"])
            if rec is None or not rec["inReplay"] or e["t1"] > E["lastTick"]:
                continue
            ph = "开局（t0<1500）" if e["t0"] < 1500 else "中后期（t0≥1500）"
            drop_cov[coh] += 1
            cs = [c for c in byp.get(rec["me"], []) if e["t0"] < c[0] <= e["t1"]]
            g2 = defaultdict(list)
            for c in cs:
                g2[c[0]].append(c)
            own = sum(c[5] - c[6] for c in cs)
            don = sum(c[5] - c[6] for c in cs if c[1] == 2)
            stack = sum(c[5] - c[6] for t, Lc in g2.items() if len(Lc) >= 3 for c in Lc)
            d = e["bal0"] - e["bal1"]
            if own >= 0.8 * d:
                k = "ownStack" if stack >= 0.5 * own else "ownDonation" if don >= 0.5 * own else "ownSingle"
            elif own >= 0.3 * d:
                k = "mixed"
            else:
                k = "defence"
            drop[(coh, ph)][k] += 1
    led_l = defaultdict(list)
    for g in games:
        if g["ledger"]:
            for a in g["ledger"]["attempts"]:
                if a["exec"]:
                    led_l[g["cohort"]].append(a["lag"])
    J["stackHist"] = {}
    for (who, coh), h in hist.items():
        tot = sum(n * c for n, c in h.items())
        J["stackHist"][f"{who}_{coh}"] = {"groups": sum(h.values()), "cmds": tot, "max": max(h) if h else 0,
                                          "share3": sum(n * c for n, c in h.items() if n >= 3) / tot if tot else None,
                                          "share5": sum(n * c for n, c in h.items() if n >= 5) / tot if tot else None,
                                          "groups9": h.get(9, 0), "groups5": sum(c for n, c in h.items() if n >= 5)}
    J["perGame"] = {}
    for coh in ("squad10", "squad20"):
        P = [x for x in per_game if x["cohort"] == coh]
        W = [x["share3"] for x in P if x["outcome"] == "WIN"]
        Ls = [x["share3"] for x in P if x["outcome"] in LOSS]
        J["perGame"][coh] = {"games": len(P), "share3": dist([x["share3"] for x in P]), "win": dist(W), "loss": dist(Ls),
                             "auc": BF.auc_ci(W, Ls) if W and Ls else None}
    J["perGameVer"] = {v: dist([x["share3"] for x in per_game if x["ver"] == v]) for v in VERS}
    J["lag"] = {coh: {**dist(xs), "ge21": wil(sum(1 for x in xs if x >= 21), len(xs)), "ge35": wil(sum(1 for x in xs if x >= 35), len(xs)),
                      "ge90": wil(sum(1 for x in xs if x >= 90), len(xs))} for coh, xs in led_l.items()}
    J["dumps"] = []
    for coh in ("squad10", "squad20"):
        for ph in ("<1500", "1500–2399", "2400–4283", "≥4284"):
            c = dumps[(coh, ph)]
            J["dumps"].append({"cohort": coh, "phase": ph, "stacks": c["stacks"], "dump50": c["dump50"], "dump90": c["dump90"]})
    J["dumpSummary"] = {}
    for coh in ("squad10", "squad20"):
        c = dumps[(coh, "all")]
        J["dumpSummary"][coh] = {"dump50": c["dump50"], "core": dumps[(coh, "core")]["dump50"],
                                 "games": sum(1 for k in c if k.startswith("games_")), "bots": sum(1 for k in c if k.startswith("bots_")),
                                 "fracCore": dist(dump_frac[coh])}
    J["drop30"] = []
    for (coh, ph), c in sorted(drop.items()):
        n = sum(c.values())
        J["drop30"].append({"cohort": coh, "phase": ph, "n": n, **{k: c[k] for k in ("ownDonation", "ownSingle", "ownStack", "mixed", "defence")},
                            "ownShare": (c["ownDonation"] + c["ownSingle"] + c["ownStack"]) / n if n else None,
                            "stackShare": c["ownStack"] / n if n else None, "defenceShare": c["defence"] / n if n else None})
    J["drop30Total"] = dict(drop_total)
    J["drop30Listed"] = dict(drop_listed)
    J["drop30All"] = {"full": sum(drop_total.values()), "listed": sum(drop_listed.values()),
                      **{k: tool[k] for k in ("bundles", "countMatches", "firstThirtySorted", "truncated", "botsWithDrop", "botsHidden")}}
    J["drop30Covered"] = dict(drop_cov)
    # 清仓批之后的结局：同为“有敌邻/在交战”的窗口比较（粗对照）
    J["afterDump"] = {}
    for coh in ("squad10", "squad20"):
        R = [r for r in rows if r["cohort"] == coh and r["seen360"]]
        def rate(f):
            Sx = [r for r in R if f(r)]
            return wil(sum(1 for r in Sx if r["die360"]), len(Sx))
        J["afterDump"][coh] = {"stackDump": rate(lambda r: r["stackDump"]), "singleDump": rate(lambda r: r["singleDump"]),
                               "attackNoDump": rate(lambda r: not r["stackDump"] and not r["singleDump"] and r["ownfrac"] >= 0.05),
                               "noAttack": rate(lambda r: r["ownfrac"] < 0.05),
                               "stackDumpUnderFire": rate(lambda r: r["stackDump"] and r["hum"] > 0),
                               "attackNoDumpUnderFire": rate(lambda r: not r["stackDump"] and not r["singleDump"] and r["ownfrac"] >= 0.05 and r["hum"] > 0)}
    return J


# ----------------------------------------------------------------------------
# 数据口径
# ----------------------------------------------------------------------------

def census(games) -> dict:
    J = {"games": len(games), "byCohort": {}, "engine": {}}
    tags = Counter()
    cover = defaultdict(list)
    short = []
    for g in games:
        c = J["byCohort"].setdefault(g["cohort"], Counter())
        c["games"] += 1
        if g["replay"]:
            c["replay"] += 1
        if g["E"]:
            c["engine"] += 1
        if g["replay"]:
            last_log = max((b["lastT"] or 0) for b in g["bots"]) if g["bots"] else 0
            rt = g["replayTicks"]
            if rt <= 1:
                c["replayEmpty"] += 1
            if rt < 1500:
                c["replayLt1500"] += 1
            if rt >= last_log - 90:
                c["replayFull"] += 1
            cover[g["cohort"]].append(min(1.0, rt / last_log) if last_log else 0.0)
            if rt < last_log - 90:
                short.append({"mid": g["mid"], "cohort": g["cohort"], "replayTicks": rt, "logTicks": last_log})
        for e in g["events"]:
            tags[(g["cohort"], e["type"])] += 1
    J["byCohort"] = {k: {**{"replay": 0, "engine": 0, "replayEmpty": 0, "replayLt1500": 0, "replayFull": 0}, **dict(v),
                         "coverShare": dist(cover[k])} for k, v in J["byCohort"].items()}
    J["events"] = [{"cohort": k[0], "type": k[1], "n": n} for k, n in sorted(tags.items())]
    J["shortReplays"] = sorted(short, key=lambda x: (x["replayTicks"], x["mid"]))
    for k, v in J["byCohort"].items():
        v["noReplay"] = v["games"] - v["replay"]
    by_mid = {g["mid"]: g for g in games}
    J["dualReview"] = []
    for mid in DUAL_REVIEW:
        g = by_mid.get(mid)
        if g is None:
            J["dualReview"].append({"mid": mid, "inDiscovery": False})
            continue
        last_log = max((b["lastT"] or 0) for b in g["bots"]) if g["bots"] else 0
        J["dualReview"].append({"mid": mid, "inDiscovery": True, "cohort": g["cohort"], "hasReplay": bool(g["replay"]),
                                "replayTicks": g["replayTicks"] if g["replay"] else None, "logTicks": last_log,
                                "engineGe1500": bool(g["replay"]) and g["replayTicks"] >= 1500})
    J["dualNoMidgame"] = [x["mid"] for x in J["dualReview"] if x.get("inDiscovery") and not x["engineGe1500"]]
    tot = ok = 0
    n_cmd = n_cmd_rp = 0
    for g in games:
        E = g["E"]
        if not E:
            continue
        for rec in g["bots"]:
            if not rec["inReplay"]:
                continue
            arr = E["bots"].get(str(rec["me"]))
            for s in rec["snaps"]:
                i = E["snapIdx"].get(s["t"])
                if i is None:
                    continue
                tot += 1
                if arr[i][0] == s["terr"] and arr[i][1] == s["bal"]:
                    ok += 1
        ours = set(E["ours"])
        n_cmd += len(E["cmds"])
        n_cmd_rp += sum(1 for (t, cid, p, a, c) in g["replay"]["cmds"] if p in ours and cid in (1, 2, 3, 4, 10) and t >= 0)
    J["engine"] = {"games": sum(1 for g in games if g["E"]), "snapPoints": tot, "snapExact": ok, "cmdsEngine": n_cmd, "cmdsReplay": n_cmd_rp}
    return J


# ----------------------------------------------------------------------------
# 表格
# ----------------------------------------------------------------------------

def P(x, d=1):
    return "—" if x is None else f"{100 * x:.{d}f}%"


def N(x):
    if x is None:
        return "—"
    if isinstance(x, float):
        return f"{x:,.0f}"
    return f"{x:,}"


def F(x, d=2):
    return "—" if x is None else f"{x:.{d}f}"


def W(r, ci=False):
    if r is None or not r.get("n"):
        return "—"
    out = f"{r['k']:,}/{r['n']:,} = {P(r['p'])}"
    if ci:
        out += f" [{P(r['lo'])}, {P(r['hi'])}]"
    return out


def md(headers, rows, align=None):
    align = align or [":--"] + [":-:"] * (len(headers) - 1)
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(align) + " |"]
    for r in rows:
        out.append("| " + " | ".join(str(x) for x in r) + " |")
    return "\n".join(out)


def render(template: str, J: dict, T: dict) -> str:
    """模板渲染：{{TABLE:名}} 换成表；{{路径|格式}} 换成 JSON 里的数。报告里不允许手写数字。"""
    def sub_table(m):
        return T[m.group(1)]

    def sub_val(m):
        path, _, fmt = m.group(1).partition("|")
        v = BF.get_path(J, path.strip())
        fmt = fmt.strip()
        if fmt in ("pct", "pct0", "pct2"):
            return P(v, {"pct": 1, "pct0": 0, "pct2": 2}[fmt])
        if fmt == "n":
            return N(v)
        if fmt == "w":
            return W(v)
        if fmt == "wci":
            return W(v, True)
        if fmt == "wp":
            return P(v["p"])
        if fmt == "wan":
            return f"{v / 1e4:,.1f} 万"
        if fmt == "yi":
            return f"{v / 1e8:,.2f} 亿"
        if fmt in ("f0", "f1", "f2", "f3"):
            return F(v, int(fmt[1]))
        if fmt == "list":
            return "、".join(str(x) for x in v)
        return str(v)
    out = re.sub(r"\{\{TABLE:([A-Za-z0-9_]+)\}\}", sub_table, template)
    out = re.sub(r"\{\{([^{}]+)\}\}", sub_val, out)
    return out


def build_tables(J) -> dict:
    T = {}
    VL = VER_LABEL
    c = J["census"]
    T["census"] = md(["编队", "发现集对局包", "带录像", "真引擎重放完成", "录像只有出生阶段（≤1 拍）", "录像不到 1500 拍", "录像盖到日志最后一拍", "录像长度 ÷ 日志长度（中位）"],
                     [[k, v.get("games", 0), v.get("replay", 0), v.get("engine", 0), v.get("replayEmpty", 0), v.get("replayLt1500", 0), v.get("replayFull", 0),
                       P(v["coverShare"]["med"]) if v["coverShare"]["n"] else "—"] for k, v in sorted(c["byCohort"].items())])
    T["census_dual"] = md(["任务卡点名的双审重叠局", "编队", "录像", "录像末拍", "日志最后一拍", "有 t≥1500 的引擎真值"],
                          [[r["mid"], r.get("cohort", "—"), ("有" if r.get("hasReplay") else "无") if r.get("inDiscovery") else "不在发现集", N(r["replayTicks"]) if r.get("replayTicks") is not None else "—",
                            N(r["logTicks"]) if r.get("logTicks") else "—", "是" if r.get("engineGe1500") else "否"] for r in c["dualReview"]])
    T["census_short"] = md(["对局包", "编队", "录像末拍", "日志最后一拍"], [[r["mid"], r["cohort"], N(r["replayTicks"]), N(r["logTicks"])] for r in c["shortReplays"]])
    h = J["h1"]
    T["h1_code"] = md(["版本", "文件", "主 `act(g)` 起始行", "`const cmdsBefore`", "`this.buyLand(g)`", "`tryDonateToTeammate` 唯一调用行", "调用处数 / 带 `cmds === cmdsBefore` 守卫", "Boss 急救 `return` 行"],
                      [[VL[v], f"`{x['file']}`", x["actLine"], x["cmdsBeforeLine"], x["buyLandLine"], "、".join(str(i) for i in x["donateCallLines"]),
                        f"{x['donateCalls']} / {x['donateCallsGuarded']}", "、".join(str(i) for i in x["bossReturnLines"])] for v, x in h["code"].items()])
    T["h1_truth"] = md(["版本", "对局包（带录像）", "日志下单", "录像覆盖内", "真实成交", "未成交", "旧口径“疑似被拒”", "覆盖外下单"],
                       [[VL[v], f"{x['games']}（{x['gamesReplay']}）", N(x["logged"]), N(x["covered"]), W(x["exec"], True), W(x["notExec"]), W(x["heurRej"]), N(x["uncovered"])]
                        for v, x in h["byVersion"].items()])
    T["h1_phase"] = md(["版本"] + [f"t {p}" for p in PHASES],
                       [[VL[v]] + [W(h["byPhase"][v][p]) for p in PHASES] for v in VERS if h["byVersion"][v]["covered"]])
    T["h1_kind"] = md(["版本", "下单类别", "下单", "成交率"], [[VL[r["ver"]], f"`{r['kind']}`", N(r["n"]), W(r, True)] for r in h["byKind"]])
    T["h1_boxed"] = md(["版本", "日志 `boxedIn`", "下单", "成交率"],
                       [[VL[r["ver"]], {True: "true", False: "false", None: "（未打印）"}[r["boxedIn"]], N(r["n"]), W(r, True)] for r in h["byBoxed"]])
    T["h1_heur"] = md(["版本", "判“拒”且真未成交", "判“成”但真未成交", "判“拒”但真成交", "判“成”且真成交", "对未成交的检出率", "对成交的正确率", "判“拒”的准确率"],
                      [[VL[v], N(x["tp"]), N(x["fn"]), N(x["fp"]), N(x["tn"]), W(x["sens"]), W(x["spec"]), W(x["ppv"])]
                       for v, x in h["heuristic"].items() if x["tp"] + x["fn"] + x["fp"] + x["tn"]])
    T["h1_verdict"] = md(["版本", "未成交下单", "单笔就超上限", "累计超上限", "收款方已满", "收款方已出局/非队友", "三个到达拍判定不一致", "配额内放得下（未解释）", "配额解释占比"],
                         [[VL[v], N(x["n"]), N(x["singleOver"]), N(x["accOver"]), N(x["recFull"]), N(x["recGone"]), N(x["mixed"]), N(x["fits"]), P(x["quotaShare"])]
                          for v, x in h["verdict"].items() if x["n"]])
    T["h1_rightsize"] = md(["版本", "被配额拒的下单", "想送的到账额（中位）", "当时配额还放得下（中位）", "放得下 ≥ 想送的 50%", "≥ 25%", "< 5%（配额基本用尽）"],
                           [[VL[v], N(x["n"]), N(x["wantV"]["med"]), N(x["fitV"]["med"]), W(x["ge50"]), W(x["ge25"]), W(x["lt5"])]
                            for v, x in h["rightSize"].items() if x["n"]])
    T["h1_flow"] = md(["版本"] + [f"t {p}" for p in PHASES] + ["合计", "解禁后（t≥4284）占到账兵力"],
                      [[VL[v]] + [f"{N(h['flow'][v][p]['n'])} 笔 / {N(h['flow'][v][p]['v'])} 兵" for p in PHASES]
                       + [f"{N(h['flow'][v]['total']['n'])} 笔 / {N(h['flow'][v]['total']['v'])} 兵", P(h["flow"][v]["total"]["shareAfterLiftV"])]
                       for v in VERS if h["flow"][v]["total"]["n"]])
    T["h1_lag"] = md(["版本", "成交笔数", "延迟中位（拍）", "P90", "最大", "≥21 拍", "≥35 拍", "≥90 拍"],
                     [[VL[v], N(x["n"]), x["med"], x["p90"], x["max"], W(x["ge21"]), W(x["ge35"]), W(x["ge90"])] for v, x in h["lag"].items() if x["n"]])
    T["h1_ceiling"] = md(["地图陆地格数", "上限点数（t=1500 / 2141 / 3212 / 4283）", "t=1500 累计可收", "t=2141", "t=2142（分母 ×100/30）", "t=3212"],
                         [[N(x["land"]), f"{x['cap1500']} / {x['cap2141']} / {x['cap3212']} / {x['cap4283']}", N(x["t1500"]), N(x["t2141"]), N(x["t2142"]), N(x["t3212"])] for x in h["ceiling"]])
    T["h1_foot"] = md(["版本", "有下单的“号×90 拍窗口”", "窗口内下单次数（中位）", "最多", "占 18 个决策拍的比例（中位 / 最多）"],
                      [[VL[v], N(x["n"]), x["med"], x["max"], f"{P(x['shareOfActTicksMed'])} / {P(x['shareOfActTicksMax'])}"] for v, x in h["footprint"].items() if x["n"]])
    T["h1_episodes"] = md(["版本", "“想送送不出去”的段数", "每段连续被拒次数：中位 / P90 / 最多", "每段时长（拍）：中位 / P90 / 最长", "≥360 拍", "≥900 拍", "以一笔成交收尾", "段内捐出方余额中位",
                           "解禁前（t<4284）每个房间×快照里，处在这种段里的号占我方余额：均值 / 中位 / P90"],
                          [[VL[v], N(x["n"]), f"{x['attempts']['med']} / {x['attempts']['p90']} / {x['attempts']['max']}", f"{N(x['dur']['med'])} / {N(x['dur']['p90'])} / {N(x['dur']['max'])}",
                            W(x["ge360"]), W(x["ge900"]), W(x["endExec"]), N(x["bal"]["med"]),
                            f"{P(x['balSharePre']['mean'])} / {P(x['balSharePre']['med'])} / {P(x['balSharePre']['p90'])}" if x["balSharePre"]["n"] else "—"]
                           for v, x in h["episodes"].items() if x["n"]])
    T["h1_outcome"] = md(["编队", "赢的房间：解禁前每个“号×快照”的被拒次数（中位，P25–P75）", "输的房间", "AUC（赢 > 输的概率）"],
                         [[k, f"{x['win']['n']} 间：{F(x['win']['med'])}（{F(x['win']['p25'])}–{F(x['win']['p75'])}）",
                           f"{x['loss']['n']} 间：{F(x['loss']['med'])}（{F(x['loss']['p25'])}–{F(x['loss']['p75'])}）",
                           f"{F(x['auc']['auc'])} [{F(x['auc']['lo'])}, {F(x['auc']['hi'])}]" if x["auc"] else "—"] for k, x in h["outcome"].items()])
    h = J["h2"]
    T["h2_interest"] = md(["版本", "解禁前（1500≤t<4284）：局数", "每局“我方手续费 ÷ 我方号同期利息收入”中位（P25–P75）", "P90 / 最大", "解禁后（t≥4284）：局数", "中位（P25–P75）", "P90 / 最大"],
                          [[VL[v], x["pre"]["n"], f"{P(x['pre']['med'])}（{P(x['pre']['p25'])}–{P(x['pre']['p75'])}）", f"{P(x['pre']['p90'])} / {P(x['pre']['max'])}",
                            x["post"]["n"], f"{P(x['post']['med'])}（{P(x['post']['p25'])}–{P(x['post']['p75'])}）" if x["post"]["n"] else "—",
                            f"{P(x['post']['p90'])} / {P(x['post']['max'])}" if x["post"]["n"] else "—"] for v, x in h["feeOverInterest"].items() if x["pre"]["n"]])
    T["h2_relay"] = md(["版本", "阶段", "我方成交捐款（组队房间）", "到账兵力", "收款号 100 拍内又转出：笔数", "按兵力", "收款号 300 拍内又转回给原捐出号：笔数", "按兵力"],
                       [[VL[r["ver"]], "t " + r["phase"], N(r["n"]), N(r["v"]), W(r["relay"]), P(r["relayV"]), W(r["back"]), P(r["backV"])] for r in h["relay"]])
    T["h2_pingpong"] = md(["版本", "解禁后有成交捐款的组队局", "每局“来回倒”兵力占比：中位 / P75 / P90 / 最大", "占比 ≥50% 的局", "这些局的结局", "对局包", "解禁后手续费合计", "其中“来回倒”那些笔的手续费"],
                          [[VL[v], x["games"], f"{P(x['backShare']['med'])} / {P(x['backShare']['p75'])} / {P(x['backShare']['p90'])} / {P(x['backShare']['max'])}", W(x["ge50"]),
                            "、".join(f"{k} {n}" for k, n in sorted(x["ge50Outcomes"].items())) or "—", "、".join(x["ge50Games"]) or "—", N(x["postFee"]),
                            f"{N(x['backFee'])}（{P(x['backFeeShare'])}）"] for v, x in h["pingPong"].items() if x["games"]])
    T["h2_conc"] = md(["版本", "有录像的组队局", "手续费合计", "最高 2 局占比", "最高 5 局占比", "赢的局数 / 赢的局占手续费", "手续费最高的 5 局（结局，手续费）"],
                      [[VL[v], x["games"], N(x["fee"]), P(x["top2Share"]), P(x["top5Share"]), f"{x['winGames']} / {P(x['feeWinGames'])}",
                        "；".join(f"{t['mid']}（{t['outcome']}，{N(t['fee'])}）" for t in x["top"])] for v, x in h["concentration"].items() if x["games"] and x["fee"]])
    T["h2_chains"] = md(["版本", "解禁后有成交捐款的号", "每个号解禁后的成交笔数：中位 / P90 / 最多", "≥5 笔", "≥10 笔", "这些笔的手续费合计 ÷ 该号第一笔时的余额：中位 / P90"],
                        [[VL[v], x["donors"], f"{x['count']['med']} / {x['count']['p90']} / {x['count']['max']}", W(x["ge5"]), W(x["ge10"]),
                          f"{P(x['feeOverFirstBal']['med'])} / {P(x['feeOverFirstBal']['p90'])}"] for v, x in h["chains"].items() if x["donors"]])
    ex = h["example"]
    T["h2_example"] = md(["拍", "捐出号 → 收款号", "`pct`", "捐出号转出前余额", "按 `pct` 想送", "收款号余额：前 → 后", "收款号余额上限（150×领土）", "实际到账", "手续费"],
                         [[N(r["t"]), f"{r['from']} → {r['to']}", r["pct"], N(r["donorBal"]), N(r["want"]), f"{N(r['recBal0'])} → {N(r['recBal1'])}", N(r["recCap"]), N(r["arrive"]), N(r["fee"])] for r in ex["rows"]]) if ex else ""
    T["h2_guard"] = md(["版本", "文件", "`tryDonateToTeammate` 里 `if (pct < N) return false;` 的行号与 N"],
                       [[VL[v], f"`{x['file']}`", "；".join(f"第 {g_['line']} 行：N={g_['threshold']}" for g_ in x["guards"]) or "没有这样的语句"] for v, x in h["pctGuard"].items()])
    T["h2_version"] = md(["版本", "成交捐款", "到账兵力", "手续费", "手续费 ÷ 到账", "`pct` 中位（P10–P90）", "`pct<180` 占比", "其手续费 ÷ 到账", "手续费 ≥ 到账的笔数"],
                         [[VL[v], N(x["n"]), N(x["v"]), N(x["fee"]), P(x["feeOverArrive"]), f"{x['pct']['med']}（{x['pct']['p10']}–{x['pct']['p90']}）", W(x["lt180"]),
                           P(x["lt180FeeOverArrive"]), N(x["feeGeArrive"])] for v, x in h["byVersion"].items() if x["n"]])
    T["h2_burn"] = md(["版本", "有成交捐款的组队局", "每局累计“手续费 ÷ 当时我方总余额”中位（P25–P75）", "P90 / 最大", "每局“手续费 ÷ 进攻出兵量”中位（P25–P75）", "同拍叠单多交的手续费（笔 / 兵 / 占全部手续费）"],
                      [[VL[v], x["burnPerGame"]["n"], f"{P(x['burnPerGame']['med'])}（{P(x['burnPerGame']['p25'])}–{P(x['burnPerGame']['p75'])}）",
                        f"{P(x['burnPerGame']['p90'])} / {P(x['burnPerGame']['max'])}",
                        f"{P(x['feeOverAttack']['med'])}（{P(x['feeOverAttack']['p25'])}–{P(x['feeOverAttack']['p75'])}）",
                        f"{N(x['stackExtraN'])} / {N(x['stackExtraFee'])} / {P(x['stackExtraFeeShare'])}"] for v, x in h["byVersion"].items() if x["n"]])
    T["h2_bucket"] = md(["编队", "`pct` 档", "成交笔数", "到账兵力", "手续费", "手续费 ÷ 到账"],
                        [[r["cohort"], r["bucket"], N(r["n"]), N(r["v"]), N(r["fee"]), P(r["feeOverArrive"])] for r in h["byBucket"] if r["n"]])
    T["h2_phase"] = md(["版本", "阶段", "成交笔数", "到账兵力", "手续费", "手续费 ÷ 到账", "不截断时应有的手续费 ÷ 到账", "到账被截断的笔数", "被截掉的兵力 ÷ 想送的兵力"],
                       [[VL[r["ver"]], "t " + r["phase"], N(r["n"]), N(r["v"]), N(r["fee"]), P(r["feeOverArrive"]), P(r["feeOverWant"]), W(r["trunc"]), P(r["truncShare"])] for r in h["byPhase"]])
    T["h2_theory"] = md(["`pct`"] + [str(r["pct"]) for r in h["theory"]],
                        [["到账占捐出方余额"] + [P(r["arrive"]) for r in h["theory"]], ["手续费 ÷ 到账（64/(pct+1)）"] + [P(r["feeOverArrive"]) for r in h["theory"]]])
    T["h2_est"] = md(["版本（无录像的包）", "日志下单", "旧口径判“成交”的笔数", "估计到账", "估计手续费", "手续费 ÷ 到账", "`pct<180` 占比"],
                     [[VL[v], N(x["logged"]), N(x["n"]), N(x["v"]), N(x["fee"]), P(x["feeOverArrive"]), W(x["lt180"])] for v, x in sorted(h["estimateNoReplay"].items())])
    h = J["h3"]
    T["h3_version"] = md(["版本", "号", "快照（t≥1500）", "`nb=0,neut=0`", "且 `dens≥95`", "其中 ≥100 / ≥145", "出现过的号", "≥10 张（≥900 拍）的号", "最长连续张数中位（P90）"],
                         [[VL[v], N(x["bots"]), N(x["snaps"]), W(x["boxed"]), W(x["high"]), f"{N(x['ge100'])} / {N(x['ge145'])}", W(x["botsAny"]), W(x["bots10"]),
                           f"{x['maxRun']['med']}（{x['maxRun']['p90']}）" if x["maxRun"]["n"] else "—"] for v, x in h["byVersion"].items()])
    T["h3_share"] = md(["版本", "解禁前（1500≤t<4284）每个房间×快照：憋死号占我方号数（均值 / P90）", "憋死号占我方余额（均值 / 中位 / P90）", "所有被封号（不论密度）占我方余额（均值）",
                        "解禁后（t≥4284）：憋死号占我方号数（均值 / P90）", "憋死号占我方余额（均值 / 中位 / P90）"],
                       [[VL[v], f"{P(x['botShareHighPre']['mean'])} / {P(x['botShareHighPre']['p90'])}",
                         f"{P(x['balShareHighPre']['mean'])} / {P(x['balShareHighPre']['med'])} / {P(x['balShareHighPre']['p90'])}", P(x["balShareBoxedPre"]["mean"]),
                         f"{P(x['botShareHighPost']['mean'])} / {P(x['botShareHighPost']['p90'])}" if x["botShareHighPost"]["n"] else "—",
                         f"{P(x['balShareHighPost']['mean'])} / {P(x['balShareHighPost']['med'])} / {P(x['balShareHighPost']['p90'])}" if x["balShareHighPost"]["n"] else "—"]
                        for v, x in h["byVersion"].items() if x["balShareHighPre"]["n"]])
    T["h3_interest"] = md(["版本", "对局包", "每局“被软上限压掉的利息 ÷ 我方实得利息”中位", "P75", "P90", "t=4230 时憋死号余额占我方余额：中位 / P90 / 最大"],
                          [[VL[v], x["forgoneShare"]["n"], P(x["forgoneShare"]["med"]), P(x["forgoneShare"]["p75"]), P(x["forgoneShare"]["p90"]),
                            f"{P(x['idleAtLift']['med'])} / {P(x['idleAtLift']['p90'])} / {P(x['idleAtLift']['max'])}"] for v, x in h["byVersion"].items()])
    T["h3_behave"] = md(["版本", "阶段", "憋死快照后的 90 拍窗口", "没下单", "下单全被拒", "至少成交一笔"],
                        [[VL[r["ver"]], "t " + r["phase"], N(r["n"]), f"{N(r['noAttempt'])}（{P(r['noAttempt'] / r['n'])}）", f"{N(r['allRejected'])}（{P(r['allRejected'] / r['n'])}）",
                          f"{N(r['executed'])}（{P(r['executed'] / r['n'])}）"] for r in h["behavePhase"] if r["n"]])
    T["h3_fate"] = md(["版本", "憋死 ≥900 拍的号", "阵亡", "活到结算", "中途离开", "阵亡前一拍余额：中位", "P90", "最大"],
                      [[VL[v], x["bots10"]["k"], x["fate"].get("died", 0), x["fate"].get("end", 0), x["fate"].get("left", 0), N(x["lostAtDeath"]["med"]),
                        N(x["lostAtDeath"]["p90"]), N(x["lostAtDeath"]["max"])] for v, x in h["byVersion"].items() if x["bots10"]["k"]])
    T["h3_outcome"] = md(["编队", "赢的房间（憋死快照占比中位，P25–P75）", "输的房间", "AUC（赢 > 输的概率）"],
                         [[k, f"{x['win']['n']} 间：{P(x['win']['med'])}（{P(x['win']['p25'])}–{P(x['win']['p75'])}）",
                           f"{x['loss']['n']} 间：{P(x['loss']['med'])}（{P(x['loss']['p25'])}–{P(x['loss']['p75'])}）",
                           f"{F(x['auc']['auc'])} [{F(x['auc']['lo'])}, {F(x['auc']['hi'])}]" if x["auc"] else "—"] for k, x in h["outcome"].items()])
    h = J["h4"]
    T["h4_version"] = md(["版本", "有开局快照的号", "统筹定义：t≤630 被封且领土<2500", "被封（不限领土）：t≤630", "t≤900", "t≤1200", "t≤1530", "被封且领土<2500：t≤1530"],
                         [[VL[v], N(x["bots"]), W(x["early"], True), W(h["sensitivity"][v]["any_630"]), W(h["sensitivity"][v]["any_900"]), W(h["sensitivity"][v]["any_1200"]),
                           W(h["sensitivity"][v]["any_1530"]), W(h["sensitivity"][v]["small_1530"])] for v, x in h["byVersion"].items() if x["bots"]])
    T["h4_effect"] = md(["版本", "开局被封的号", "第一次被封的拍（中位）", "当时领土（中位）", "t=1530 领土中位：被封号 / 同版本其他号", "t=1530 余额中位：被封号 / 其他号", "t<3000 阵亡：被封号", "其他号",
                         "同房间配对：被封号领土 − 同房间其他号中位（各房间差值的中位）", "差值为负的房间"],
                        [[VL[v], x["early"]["k"], N(x["firstT"]["med"]), N(x["terrAtBox"]["med"]), f"{N(x['terr1530Early']['med'])} / {N(x['terr1530Other']['med'])}",
                          f"{N(x['bal1530Early']['med'])} / {N(x['bal1530Other']['med'])}", W(x["died3000Early"]), W(x["died3000Other"]),
                          N(x["pairedDiff"]["med"]) if x["pairedDiff"]["n"] else "—", W(x["pairedNeg"])] for v, x in h["byVersion"].items() if x["early"]["k"]])
    T["h4_role"] = md(["版本", "选点角色", "号", "t=630 领土中位", "t=1530 领土中位", "t=1530 余额中位", "t=1530 已被封", "t<3000 阵亡"],
                      [[VL[r["ver"]], f"`{r['role']}`", r["n"], N(r["terr630"]["med"]), N(r["terr1530"]["med"]), N(r["bal1530"]["med"]), W(r["boxed1530"]), W(r["died3000"])]
                       for r in h["roleStats"] if r["n"] >= 10])
    T["h4_corr"] = md(["版本", "号", "`minAllyDist` 中位（P10–P90）", "号级 ρ（间距, t=1530 领土）", "房间内（去房间中位数后）ρ", "房间级 ρ（间距中位, 领土中位）", "房间级 ρ（间距中位, 每席位陆地格数）"],
                      [[VL[v], x["n"], f"{x['dist']['med']}（{x['dist']['p10']}–{x['dist']['p90']}）", F(x["spearmanTerr1530"]), F(x["spearmanWithinRoom"]), F(x["spearmanRoomLevel"]),
                        F(x["spearmanRoomLandPerSeat"])] for v, x in h["minAllyDist"].items() if x["n"]])
    T["h4_dup"] = md(["版本", "带录像的组队房间", "两个我方号最终出生令落同一像素的房间", "有号一条出生令都没执行的房间", "这样的号 / 我方号"],
                     [[VL[v], x["dup"].get("rooms", 0), x["dup"].get("roomsDup", 0), x["dup"].get("roomsNoSpawnCmd", 0), f"{x['dup'].get('botsNoSpawnCmd', 0)} / {x['dup'].get('bots', 0)}"]
                      for v, x in h["byVersion"].items() if x["dup"].get("rooms")])
    T["h4_rooms"] = md(["编队", "房间（≥5 个号）", "有 ≥1 个“开局被封且<2500”号的房间", "赢的房间：这种号占比均值", "输的房间", "AUC"],
                       [[k, x["rooms"], W(x["withEarly"]), f"{x['win']['n']} 间：{P(x['win']['mean'])}", f"{x['loss']['n']} 间：{P(x['loss']['mean'])}",
                         f"{F(x['auc']['auc'])} [{F(x['auc']['lo'])}, {F(x['auc']['hi'])}]" if x["auc"] else "—"] for k, x in h["rooms"].items()])
    h = J["h5"]
    rows = []
    for coh in ("squad10", "squad20"):
        for r in h[coh]["byHumN"]:
            rows.append([coh, r["bucket"], N(r["n"]), W(r, True), F(r["medDens"], 1)])
    T["h5_humn"] = md(["编队", "之后 90 拍内对它出兵的真人数", "号×窗口", "360 拍内阵亡", "窗口起点密度中位"], rows)
    rows = []
    for coh in ("squad10", "squad20"):
        for r in h[coh]["byRatio"]:
            rows.append([coh, r["bucket"], N(r["n"]), W(r, True), F(r["medDens"], 1)])
    T["h5_ratio"] = md(["编队", "90 拍内真人对它的出兵量 ÷ 它的余额", "号×窗口", "360 拍内阵亡", "窗口起点密度中位"], rows)
    rows = []
    for coh in ("squad10", "squad20"):
        for r in h[coh]["focus"]["byDens"]:
            rows.append([coh, r["bucket"], N(r["n"]), W(r, True), F(r["medRatio"], 2)])
    T["h5_focus_dens"] = md(["编队", "集火窗口起点密度（兵/格）", "集火窗口", "360 拍内阵亡", "受攻比中位"], rows)
    rows = []
    for coh in ("squad10", "squad20"):
        for r in h[coh]["ratioDens"]:
            rows.append([coh, r["ratio"], r["dens"], W(r, True)])
    T["h5_ratio_dens"] = md(["编队", "受攻比（真人出兵 ÷ 余额）", "起点密度", "360 拍内阵亡"], rows)
    rows = []
    for coh in ("squad10", "squad20"):
        for r in h[coh]["focus"]["byOwn"]:
            rows.append([coh, r["bucket"], N(r["n"]), W(r, True), F(r["medDens"], 1)])
    T["h5_own"] = md(["编队", "集火窗口内自己的进攻出兵 ÷ 余额", "集火窗口", "360 拍内阵亡", "起点密度中位"], rows)
    rows = []
    for coh, vers in (("squad10", ("Va", "Vb")), ("squad20", ("c110",))):
        for ver in vers:
            for r in h[coh]["focus"]["byDens_" + ver]:
                rows.append([VL[ver], f"{FLOOR_CAP[ver]}", r["bucket"], N(r["n"]), W(r, True)])
    T["h5_ver"] = md(["版本", "`oppFloorCap`", "集火窗口起点密度", "集火窗口", "360 拍内阵亡"], rows)
    T["h5_deaths"] = md(["编队", "阵亡（带录像的组队房间）", "死前最后两个 90 拍窗口里，同一窗口有 ≥2 个真人对它出兵", "只有 1 个真人", "只有同编队异队号", "只有内置 AI", "没有记录到进攻", "死前约 180–270 拍的密度中位", "当时低于本版本 `oppFloorCap`", "死前一拍余额中位",
                         "死前 360 拍内有过集火窗口", "其中集火开始时还在留守线上", "在线上且受攻比 ≥1"],
                        [[coh, N(x["deaths"]["n"]), W(x["deaths"]["multiShare"], True), N(x["deaths"]["singleHuman"]), N(x["deaths"]["squadMate"]), N(x["deaths"]["aiOnly"]),
                          N(x["deaths"]["other"]), F(x["deaths"]["densBefore"]["med"], 1), W(x["deaths"]["belowFloor"]), N(x["deaths"]["balAtDeath"]["med"]),
                          W(x["deaths"]["afterFocus"]), W(x["deaths"]["afterFocusAtFloor"]), W(x["deaths"]["afterFocusAtFloorRatio1"])]
                         for coh, x in ((k, h[k]) for k in ("squad10", "squad20"))])
    rows = []
    for coh in ("squad10", "squad20"):
        x = h[coh]["path"]
        rows.append([coh, N(x["n"]), W(x["neverAbove"]), W(x["slow"]), f"{N(x['slowGap']['med'])}" if x["slowGap"]["n"] else "—", W(x["fast"]),
                     f"{N(x['fastGap']['med'])}（{N(x['fastGap']['p25'])}–{N(x['fastGap']['p75'])}）" if x["fastGap"]["n"] else "—"])
    T["h5_path"] = md(["编队", "阵亡", "t≥630 之后从没到过留守线密度", "慢：最后一次在线上距阵亡 >720 拍", "其间隔中位（拍）", "快：≤720 拍前还在线上", "其间隔中位（P25–P75）"], rows)
    rows = []
    for coh in ("squad10", "squad20"):
        x = h[coh]["path"]
        rows.append([coh, N(x["fast"]["k"]), f"{F(x['fastHum']['med'])}（{F(x['fastHum']['p25'])}–{F(x['fastHum']['p75'])}）",
                     f"{F(x['fastAtk']['med'])}（{F(x['fastAtk']['p25'])}–{F(x['fastAtk']['p75'])}）", f"{F(x['fastDon']['p90'])}",
                     W(x["fastDomIncoming"]), W(x["fastDomOwnAttack"]), W(x["fastDomOwnDonation"]), W(x["fastAtkGe50"]), W(x["fastStackDump"]), W(x["fastHumLt50"])])
    T["h5_fast"] = md(["编队", "“快”路径阵亡", "其间真人对它的出兵 ÷ 线上那一刻余额：中位（P25–P75）", "其间自己进攻出兵 ÷ 同一余额：中位（P25–P75）", "其间自己捐款 ÷ 同一余额：P90",
                       "三项里最大的是“被打”", "是“自己进攻”", "是“自己捐款”", "自己进攻出兵 ≥ 余额的 50%", "其间有同拍清仓批", "真人出兵 < 余额的 50%"], rows)
    rows = []
    for coh in ("squad10", "squad20"):
        for r in h[coh]["focus"]["atOrAboveFloor"]:
            rows.append([coh, r["bucket"], N(r["n"]), W(r, True), F(r["medDens"], 1)])
    T["h5_atfloor"] = md(["编队", "集火开始时密度 ≥ 本版本 `oppFloorCap` 的窗口", "窗口", "360 拍内阵亡", "起点密度中位"], rows)
    rows = []
    for coh in ("squad10", "squad20"):
        for k, (g1, g2) in (("floor", ("集火开始时在留守线下", "在留守线上")), ("version", ("Va", "Vb"))):
            x = h[coh]["cmh"].get(k)
            if not x:
                continue
            rows.append([coh, f"{g2} 对 {g1}", f"{x['k1']}/{x['n1']} = {P(x['k1'] / x['n1'])}" if x["n1"] else "—", f"{x['k2']}/{x['n2']} = {P(x['k2'] / x['n2'])}" if x["n2"] else "—",
                         F(x["or_mh"]), ("+" if x["rd_mh"] >= 0 else "−") + f"{abs(100 * x['rd_mh']):.1f} 个百分点", BF.pval(x["p"]), f"{x['used']}/{x['strata']}"])
    T["h5_cmh"] = md(["编队", "比较（后者对前者）", "前者：360 拍内阵亡", "后者：360 拍内阵亡", "按受攻比 7 档分层后的合并赔率比", "分层合并的阵亡率差", "p（把窗口当独立样本，偏乐观）", "用到的分层"], rows)
    L5 = J["h5lead"]
    rows = []
    for coh in ("squad10", "squad20"):
        x = L5["byCohort"][coh]
        def oc(o):
            return f"{o['n']} 间（赢 {o['win']} / 输 {o['loss']} / 未知 {o['unknown']}）"
        rows.append([coh, "全部", x["rooms"], oc(x["leadLog"]), oc(x["share35"]), oc(x["rank1"])])
        for r in x["byTeams"]:
            rows.append([coh, r["teams"], r["rooms"], "—", oc(r["share35"]), oc(r["rank1"])])
    T["h5_lead_def"] = md(["编队", "开局队伍数", "带录像的组队房间", "统筹口径（日志 `peakPrimaryTeamShareSeen` ≥35%）", "真引擎：主队份额到过 ≥35%", "真引擎：≥35% 且当时是领土最多的队"], rows)
    T["h5_lead_rows"] = md(["对局包", "版本", "结局", "队伍数", "领先峰值拍", "峰值份额 → 1800 拍后", "我方号存活", "野人队友存活", "峰值时我方号占主队领土", "掉的地里我方号占比", "我方号领土变化", "野人队友领土变化",
                            "我方进攻出兵 ÷ 峰值时余额", "真人对我方出兵 ÷ 同一余额", "打我方号的敌队数", "同拍清仓批", "峰值到跌破 20%（拍）"],
                           [[r["mid"], VL[r["ver"]], r["outcome"], r["teams"], N(r["t0"]), f"{P(r['share0'])} → {P(r['shareAfter'])}", f"{r['ourAlive0']} → {r['ourAlive1']}", f"{r['wild0']} → {r['wild1']}",
                             P(r["ourTerrShare0"]), P(r["oursShareOfDrop"]) if r["oursShareOfDrop"] is not None else "—", P(r["ourTerrChange"]),
                             P(r["wildTerrChange"]) if r["wildTerrChange"] is not None else "—（没有野人队友）", F(r["atkOverBal"]), F(r["humOverBal"]), r["enemyTeams"], r["stackDumps"],
                             N(r["peakToBelow20"]) if r["peakToBelow20"] is not None else "—"]
                            for r in L5["rows"] if r["outcome"] != "WIN"])
    h = J["h6"]
    T["h6_dose"] = md(["该队上的我方号数", "房间×队", "我方号合计", "该队获胜", "随机期望（Σ1/队伍数 ÷ 行数）", "超额（实际 − 期望）", "双侧 p"],
                      [[r["botsOnTeam"], r["teams"], r["bots"], W(r["win"], True), P(r["expected"]), ("+" if r["excess"]["excess_per_game"] >= 0 else "−") + f"{abs(100 * r['excess']['excess_per_game']):.1f} 个百分点",
                        F(r["excess"]["p_two_sided"], 3)] for r in h["dose"] if r["teams"]])
    T["h6_primsec"] = md(["拆队房间里的队", "房间×队", "我方号合计", "该队获胜", "随机期望", "双侧 p"],
                         [[{"primary": "主队（我方号最多的队）", "secondary": "其余有我方号的队"}[k], x["teams"], x["bots"], W(x["win"], True), P(x["expected"]), F(x["excess"]["p_two_sided"], 3)]
                          for k, x in sorted(h["primaryVsSecondary"].items())])
    T["h6_split"] = md(["我方号分布的队伍数", "房间", "我方号", "主队获胜", "主队随机期望（Σ1/T ÷ 房间数）", "任一有我方号的队获胜", "其随机期望（Σ我方队数/T ÷ 房间数）"],
                       [[r["teams"], r["rooms"], r["bots"], W(r["prim"]), P(r["expPrim"]), W(r["any"]), P(r["expAny"])] for r in h["split"]])
    T["h6_peace"] = md(["对局包", "开局时间（UTC）", "`[HL-PEACE]` 行数", "发起拍范围", "发起时本队领土占比", "主队结局", "录像"],
                       [[r["mid"], r["timeUtc"], r["n"], f"{r['tMin']}–{r['tMax']}", f"{r['landMin']}%–{r['landMax']}%", r["outcome"], "有" if r["hasReplay"] else "无"] for r in h["peaceLogs"]])
    h = J["hx"]
    T["x_stack"] = md(["谁的指令", "所在局", "（拍, 号）组数", "指令数", "≥3 条同拍落地的指令占比", "≥5 条", "正好 9 条的组数", "单组最多"],
                      [[{"ours": "我方号", "wild": "同局其他真人"}[k.split("_")[0]], k.split("_")[1], N(x["groups"]), N(x["cmds"]), P(x["share3"]), P(x["share5"]), N(x["groups9"]), x["max"]]
                       for k, x in sorted(h["stackHist"].items())])
    T["x_dumps"] = md(["编队", "阶段", "≥3 条进攻指令同拍落地的组", "其中一拍打掉 ≥50% 余额", "≥90%"],
                      [[r["cohort"], "t " + r["phase"], N(r["stacks"]), N(r["dump50"]), N(r["dump90"])] for r in h["dumps"]])
    T["x_drop30"] = md(["编队", "阶段", "`DROP30` 事件（录像覆盖内）", "自己捐款", "自己单发/双发出兵", "自己 ≥3 条同拍出兵", "混合", "不是自己花的（挨打）"],
                       [[r["cohort"], r["phase"], N(r["n"]), f"{N(r['ownDonation'])}（{P(r['ownDonation'] / r['n'])}）", f"{N(r['ownSingle'])}（{P(r['ownSingle'] / r['n'])}）",
                         f"{N(r['ownStack'])}（{P(r['ownStack'] / r['n'])}）", f"{N(r['mixed'])}（{P(r['mixed'] / r['n'])}）", f"{N(r['defence'])}（{P(r['defence'] / r['n'])}）"] for r in h["drop30"]])
    lab = [("stackDump", "窗口内有“同拍 ≥3 条、一拍打掉 ≥50% 余额”"), ("singleDump", "窗口内有 1–2 条指令一拍打掉 ≥50% 余额"),
           ("attackNoDump", "有进攻出兵（≥5% 余额）但没有上述清仓"), ("noAttack", "基本没出兵（<5% 余额）"),
           ("stackDumpUnderFire", "有同拍清仓批，且同窗口有真人对它出兵"), ("attackNoDumpUnderFire", "有进攻出兵无清仓，且同窗口有真人对它出兵")]
    T["x_after"] = md(["编队", "号×90 拍窗口（t≥1500）", "窗口数", "360 拍内阵亡"],
                      [[coh, name, N(h["afterDump"][coh][k]["n"]), W(h["afterDump"][coh][k], True)] for coh in ("squad10", "squad20") for k, name in lab])
    T["x_pergame"] = md(["编队", "对局包", "每局“≥3 条同拍”指令占比中位（P25–P75）", "赢的房间", "输的房间", "AUC（赢 > 输的概率）"],
                        [[k, x["games"], f"{P(x['share3']['med'])}（{P(x['share3']['p25'])}–{P(x['share3']['p75'])}）", f"{x['win']['n']} 间：中位 {P(x['win']['med'])}",
                          f"{x['loss']['n']} 间：中位 {P(x['loss']['med'])}", f"{F(x['auc']['auc'])} [{F(x['auc']['lo'])}, {F(x['auc']['hi'])}]" if x["auc"] else "—"]
                         for k, x in h["perGame"].items()])
    T["x_lag"] = md(["编队", "成交捐款", "下单→成交延迟中位（拍）", "P90", "最大", "≥21 拍", "≥35 拍", "≥90 拍"],
                    [[k, N(x["n"]), x["med"], x["p90"], x["max"], W(x["ge21"]), W(x["ge35"]), W(x["ge90"])] for k, x in sorted(h["lag"].items())])
    return T


def main(argv) -> int:
    games = prepare()
    rows, deaths = bot_windows(games)
    J = {"meta": {"script": "audit_hypotheses.py", "set": "discovery", "floorCap": FLOOR_CAP, "nVersions": len(VERS)},
         "census": census(games), "h1": h1(games), "h2": h2(games), "h3": h3(games), "h4": h4(games),
         "h5": h5(rows, deaths), "h5lead": h5_lead(games), "h6": h6(games, rows, deaths), "hx": hx(games, rows)}
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "hypothesis-audit.json"), "w", encoding="utf-8") as f:
        json.dump(J, f, ensure_ascii=False, indent=1, default=str)
    tpl_path = os.path.join(HERE, "hypothesis_audit_template.md")
    if os.path.exists(tpl_path) and "--json-only" not in argv:
        T = build_tables(J)
        with open(tpl_path, encoding="utf-8") as f:
            tpl = f.read()
        os.makedirs(REPORTS, exist_ok=True)
        with open(os.path.join(REPORTS, "HYPOTHESIS-AUDIT.md"), "w", encoding="utf-8") as f:
            f.write(render(tpl, J, T))
        print("wrote reports/HYPOTHESIS-AUDIT.md")
    print("wrote out/hypothesis-audit.json")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
