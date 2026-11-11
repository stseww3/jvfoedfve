#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
baseline_full.py — R10 里程碑 M1：160 局全量分层基线。

输出：
  out/baseline-full.json            全部数字（报告里的每个数都从这里取）
  out/baseline-full-internal.json   含验证集逐局明细（仅 R10 与 c136）
  reports/BASELINE-FULL.md          由 scripts/baseline_full_template.md 填数生成

两套口径：
  「卡片口径」  直接用 manifest 卡片上的 actualTeams / distinctSquadTeams / anyBotWon / primaryTeamWon，
               按任务卡要求分层（编队 × 队伍数 × 是否拆队）。
  「房间口径」  用 rooms.py 把每个包还原成 号 → 房间 → 队伍 → 结局 之后重算。

用法：
  python3 baseline_full.py            # 计算并写出全部文件
  python3 baseline_full.py --no-report
"""

from __future__ import annotations

import json
import math
import os
import random
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rooms as R                      # noqa: E402
import stats as S                      # noqa: E402
from c136lib import load_cards, load_events, load_traj, team_bucket  # noqa: E402

OUT = os.path.normpath(os.path.join(HERE, "..", "out"))
REP = os.path.normpath(os.path.join(HERE, "..", "reports"))
TEMPLATE = os.path.join(HERE, "baseline_full_template.md")

COHORTS = ("squad8", "squad10", "squad20")
TB = ("T=2", "T=3-4", "T>=5")
MAIN_ROOM_MIN_BOTS = 5          # 带标签编组：房间里我方号数 ≥ 5 才算「编队局」，否则算「散号房间」
SHARE_BINS = (0.0, 0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.65, 0.80, 1.0001)


# ----------------------------------------------------------------------------
# 小工具
# ----------------------------------------------------------------------------

def rate(k: int, n: int):
    """比例 + Wilson 95% 区间。"""
    if n == 0:
        return {"k": 0, "n": 0, "rate": None, "lo": None, "hi": None}
    lo, hi = S.wilson(k, n)
    return {"k": k, "n": n, "rate": k / n, "lo": lo, "hi": hi}


def excess(wins: list[int], exps: list[float]):
    if not wins:
        return {"n": 0, "wins": 0, "expected": 0.0, "excess_per_game": None, "p_upper": None, "p_lower": None,
                "p_two_sided": None, "mean_base": None}
    e = S.excess_test(wins, exps)
    e["mean_base"] = sum(exps) / len(exps)
    return e


def quantiles(xs: list[float]):
    xs = sorted(xs)
    n = len(xs)
    if n == 0:
        return {"n": 0}

    def q(p):
        if n == 1:
            return xs[0]
        pos = p * (n - 1)
        i = int(math.floor(pos))
        f = pos - i
        return xs[i] if i + 1 >= n else xs[i] * (1 - f) + xs[i + 1] * f
    return {"n": n, "mean": sum(xs) / n, "min": xs[0], "p25": q(0.25), "median": q(0.5), "p75": q(0.75),
            "p90": q(0.9), "max": xs[-1]}


def auc(pos: list[float], neg: list[float]):
    """Mann–Whitney AUC：随机取一个胜局和一个负局，胜局指标更大的概率（相等算半个）。"""
    if not pos or not neg:
        return None
    allv = sorted([(v, 1) for v in pos] + [(v, 0) for v in neg])
    # 平均秩
    ranks = {}
    i = 0
    rank_sum_pos = 0.0
    while i < len(allv):
        j = i
        while j < len(allv) and allv[j][0] == allv[i][0]:
            j += 1
        avg = (i + 1 + j) / 2.0
        for k in range(i, j):
            if allv[k][1] == 1:
                rank_sum_pos += avg
        i = j
    n1, n0 = len(pos), len(neg)
    return (rank_sum_pos - n1 * (n1 + 1) / 2.0) / (n1 * n0)


def auc_ci(pos: list[float], neg: list[float], seed: int = 136, reps: int = 2000):
    """AUC + 自助法 95% 区间（固定随机种子，可复现）。"""
    a = auc(pos, neg)
    if a is None:
        return {"auc": None, "lo": None, "hi": None, "nPos": len(pos), "nNeg": len(neg)}
    rng = random.Random(seed)
    bs = []
    for _ in range(reps):
        p = [pos[rng.randrange(len(pos))] for _ in pos]
        n = [neg[rng.randrange(len(neg))] for _ in neg]
        bs.append(auc(p, n))
    bs.sort()
    return {"auc": a, "lo": bs[int(0.025 * reps)], "hi": bs[int(0.975 * reps) - 1], "nPos": len(pos), "nNeg": len(neg)}


def stratified_auc(items: list[tuple[str, int, float]]):
    """items: (层, 是否胜, 指标)。只在同一层内配对：Σ层内胜负对里指标占优的对数 / Σ层内胜负对数。"""
    by = defaultdict(lambda: ([], []))
    for s, w, v in items:
        by[s][0 if w else 1].append(v)
    num = den = 0.0
    for s, (pos, neg) in by.items():
        a = auc(pos, neg)
        if a is None:
            continue
        num += a * len(pos) * len(neg)
        den += len(pos) * len(neg)
    return (num / den if den else None), int(den)


def spearman(xs: list[float], ys: list[float]):
    n = len(xs)
    if n < 3:
        return None

    def ranks(v):
        order = sorted(range(n), key=lambda i: v[i])
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j < n and v[order[j]] == v[order[i]]:
                j += 1
            for k in range(i, j):
                r[order[k]] = (i + 1 + j) / 2.0
            i = j
        return r
    rx, ry = ranks(xs), ranks(ys)
    mx, my = sum(rx) / n, sum(ry) / n
    sxx = sum((a - mx) ** 2 for a in rx)
    syy = sum((b - my) ** 2 for b in ry)
    if sxx == 0 or syy == 0:
        return None
    return sum((a - mx) * (b - my) for a, b in zip(rx, ry)) / math.sqrt(sxx * syy)


# ----------------------------------------------------------------------------
# A. 卡片口径
# ----------------------------------------------------------------------------

# 策略版本（来源：/agent/repos/c136-data/src/strategy/VERSION-TIMELINE.md）
#   squad10：Va = 2026-11-09T23:34:05Z 的热更之前开的局；Vb = 热更之后、2026-11-10T14:16:33Z 之前；Vc = 之后。
#   A018 开局于 23:33:05Z，开局约 990 拍后被热更（计数器在 t=990 清零），按统筹的划分记在 Vb。
#   squad20 / squad8 在数据期内局内策略没有换版本。
VB_FROM_UTC = "2026-11-09T23:33:00Z"
VC_FROM_UTC = "2026-11-10T14:16:33Z"
VERSIONS = ("Va", "Vb", "Vc")
VER = {}  # matchId -> 版本，main() 里填


def strategy_version(c: dict) -> str:
    if c["cohort"] == "squad10":
        t = c["timeUtc"]
        return "Va" if t < VB_FROM_UTC else ("Vb" if t < VC_FROM_UTC else "Vc")
    return "c110" if c["cohort"] == "squad20" else "g09"


def split_flag(d: int) -> str:
    return "未拆(=1)" if d == 1 else ("拆队(>1)" if d > 1 else "无队号(=0)")


def card_row(c: dict) -> dict:
    t = c["actualTeams"]
    return {"matchId": c["matchId"], "cohort": c["cohort"], "split": c["split"], "T": t, "tb": team_bucket(t),
            "d": c["distinctSquadTeams"], "sf": split_flag(c["distinctSquadTeams"]),
            "any": bool(c["outcome"]["anyBotWon"]), "prim": bool(c["outcome"]["primaryTeamWon"]),
            "base": 1.0 / t, "mode": c["mode"], "seeded": c["seededPlayers"], "ver": strategy_version(c)}


def card_stratum(rows: list[dict]) -> dict:
    n = len(rows)
    k_any = sum(r["any"] for r in rows)
    k_prim = sum(r["prim"] for r in rows)
    ex = excess([int(r["prim"]) for r in rows], [r["base"] for r in rows])
    # 「任一号获胜」的随机期望：我方占了 d 个队 → d/T（d=0 时为 0）
    ex_any = excess([int(r["any"]) for r in rows], [min(1.0, r["d"] / r["T"]) for r in rows]) if n else None
    return {"n": n, "any": rate(k_any, n), "prim": rate(k_prim, n),
            "base_mean": (sum(r["base"] for r in rows) / n) if n else None,
            "prim_excess": ex, "any_null_dT": ex_any,
            "any_minus_prim": ((k_any - k_prim) / n) if n else None}


def card_tables(cards: list[dict]) -> dict:
    rows = [card_row(c) for c in cards]
    out = {"byCohort": {}, "byCohortSplitSet": {}, "byCohortT": {}, "byCohortSplitFlag": {}, "byCohortTSplitFlag": {}}
    for co in COHORTS:
        rs = [r for r in rows if r["cohort"] == co]
        out["byCohort"][co] = card_stratum(rs)
        out["byCohortSplitSet"][co] = {s: card_stratum([r for r in rs if r["split"] == s]) for s in ("discovery", "validation")}
        out["byCohortT"][co] = {tb: card_stratum([r for r in rs if r["tb"] == tb]) for tb in TB}
        out["byCohortSplitFlag"][co] = {sf: card_stratum([r for r in rs if r["sf"] == sf])
                                        for sf in ("未拆(=1)", "拆队(>1)", "无队号(=0)")}
        out["byCohortTSplitFlag"][co] = {tb: {sf: card_stratum([r for r in rs if r["tb"] == tb and r["sf"] == sf])
                                              for sf in ("未拆(=1)", "拆队(>1)", "无队号(=0)")} for tb in TB}
    out["all"] = card_stratum(rows)
    a10 = [r for r in rows if r["cohort"] == "squad10"]
    out["byVersion"] = {v: card_stratum([r for r in a10 if r["ver"] == v]) for v in VERSIONS}
    out["byVersionT"] = {v: {tb: card_stratum([r for r in a10 if r["ver"] == v and r["tb"] == tb]) for tb in TB} for v in VERSIONS}
    return out


def squad20_card_decomp(cards: list[dict]) -> dict:
    rows = [card_row(c) for c in cards if c["cohort"] == "squad20"]
    n = len(rows)
    k_any = sum(r["any"] for r in rows)
    k_prim = sum(r["prim"] for r in rows)
    e_prim = sum(r["base"] for r in rows)
    e_any = sum(min(1.0, r["d"] / r["T"]) for r in rows)
    by_d = {}
    for label, f in (("d=0", lambda d: d == 0), ("d=1", lambda d: d == 1), ("d=2", lambda d: d == 2),
                     ("d=3", lambda d: d == 3), ("d=4", lambda d: d == 4), ("d>=5", lambda d: d >= 5)):
        rs = [r for r in rows if f(r["d"])]
        by_d[label] = {"n": len(rs), "any": rate(sum(r["any"] for r in rs), len(rs)),
                       "prim": rate(sum(r["prim"] for r in rs), len(rs)),
                       "mean_T": (sum(r["T"] for r in rs) / len(rs)) if rs else None,
                       "exp_prim": (sum(r["base"] for r in rs) / len(rs)) if rs else None,
                       "exp_any": (sum(min(1.0, r["d"] / r["T"]) for r in rs) / len(rs)) if rs else None}
    # 覆盖率 c = d/T 分档
    by_cov = {}
    for label, f in (("d/T=0", lambda c: c == 0), ("0<d/T<0.5", lambda c: 0 < c < 0.5),
                     ("0.5<=d/T<1", lambda c: 0.5 <= c < 1), ("d/T=1", lambda c: c >= 1)):
        rs = [r for r in rows if f(r["d"] / r["T"])]
        by_cov[label] = {"n": len(rs), "any": rate(sum(r["any"] for r in rs), len(rs)),
                         "prim": rate(sum(r["prim"] for r in rs), len(rs)),
                         "exp_any": (sum(min(1.0, r["d"] / r["T"]) for r in rs) / len(rs)) if rs else None,
                         "exp_prim": (sum(r["base"] for r in rs) / len(rs)) if rs else None}
    # 反事实：同样的 T 分布，如果 20 个号全在一个队（d=1），随机期望是多少
    by_t = {}
    for tb in TB:
        rs = [r for r in rows if r["tb"] == tb]
        by_t[tb] = {"n": len(rs), "any": rate(sum(r["any"] for r in rs), len(rs)),
                    "prim": rate(sum(r["prim"] for r in rs), len(rs)),
                    "mean_d": (sum(r["d"] for r in rs) / len(rs)) if rs else None,
                    "mean_T": (sum(r["T"] for r in rs) / len(rs)) if rs else None,
                    "gap": ((sum(r["any"] for r in rs) - sum(r["prim"] for r in rs)) / len(rs)) if rs else None,
                    "exp_any": (sum(min(1.0, r["d"] / r["T"]) for r in rs) / len(rs)) if rs else None,
                    "exp_prim": (sum(r["base"] for r in rs) / len(rs)) if rs else None}
    return {"n": n, "any": rate(k_any, n), "prim": rate(k_prim, n), "byT": by_t,
            "exp_prim_null": e_prim / n, "exp_any_null": e_any / n,
            "gap_obs": (k_any - k_prim) / n, "gap_null": (e_any - e_prim) / n,
            "any_excess": excess([int(r["any"]) for r in rows], [min(1.0, r["d"] / r["T"]) for r in rows]),
            "prim_excess": excess([int(r["prim"]) for r in rows], [r["base"] for r in rows]),
            "byD": by_d, "byCoverage": by_cov,
            "mean_d": sum(r["d"] for r in rows) / n, "mean_T": sum(r["T"] for r in rows) / n,
            "nAnyNotPrim": sum(1 for r in rows if r["any"] and not r["prim"])}


# ----------------------------------------------------------------------------
# B/C. 房间口径
# ----------------------------------------------------------------------------

def room_units(allb: list[dict]) -> list[dict]:
    """每个 (包, 房间) 一行。"""
    out = []
    for a in allb:
        for r in a["rooms"]:
            tagged = r["tagged"]
            t = r["tBest"]
            kind = "main"
            if tagged and r["nBots"] < MAIN_ROOM_MIN_BOTS:
                kind = "fragment"
            if (not tagged) and r["nBots"] < MAIN_ROOM_MIN_BOTS:
                kind = "fragment"
            sq630 = sum(b["terr630"] or 0 for b in r["bots"])
            sq1530 = sum(b["terr1530"] or 0 for b in r["bots"])
            cov630 = sum(1 for b in r["bots"] if b["terr630"] is not None)
            cov1530 = sum(1 for b in r["bots"] if b["terr1530"] is not None)
            alive630 = sum(1 for b in r["bots"] if (b["terr630"] or 0) > 0)
            alive1530 = sum(1 for b in r["bots"] if (b["terr1530"] or 0) > 0)
            prim_bots = [b for b in r["bots"] if r["primaryTeam"] is not None and b["team"] == r["primaryTeam"]]
            out.append({
                "matchId": a["matchId"], "cohort": a["cohort"], "split": a["split"], "roomIdx": r["roomIdx"],
                "ver": VER.get(a["matchId"]),
                # 我方号数占本队人数的比例：本队人数按 房间真人数 / 队伍数 估算（引擎按人数均分各队），上限 1
                "ownFrac": (min(1.0, r["nBots"] / (r["seeded"] / t)) if (t and r["seeded"]) else None),
                "isMainRoomOfBundle": r["roomIdx"] == a["mainRoom"], "kind": kind,
                "nBots": r["nBots"], "seeded": r["seeded"], "land": r["land"], "mode": r["mode"],
                "isTeamGame": r["isTeamGame"], "T": t, "tHow": r["tHow"], "tObs": r["tObs"], "tRule": r["tRule"],
                "tb": team_bucket(t) if t else None,
                "outcome": r["outcome"], "ownOutcome": r["own"]["outcome"], "winner": r["winner"],
                "primaryTeam": r["primaryTeam"], "primaryUncertain": r["primaryUncertain"],
                "primaryLastShare": r["primaryLastShare"], "primaryLastRank": r["primaryLastRank"],
                "teams": r["teams"], "nTeamUnknown": r["nTeamUnknown"], "teamOutcomes": r["teamOutcomes"],
                "events": r["events"], "endObserved": r["endObserved"], "lastTick": r["lastTick"],
                "nLeftEarly": r["nLeftEarly"] + r["nLeftT0"], "nLeftLate": r["nLeftMid"] + r["nLeftAtEnd"],
                "primaryTie": r["primaryTie"],
                "physRoom": r["physRoom"], "hasPeer": bool(r["physPeers"]),
                "peerSplits": sorted({p["split"] for p in r["physPeers"]}),
                "peerCohorts": sorted({p["cohort"] for p in r["physPeers"]}),
                "usedPeerRows": r["usedPeerRows"], "clanTeamConflict": r["clanTeamConflict"],
                "anyBotWonRow": r["anyBotWonRow"], "ourTeamsIncludeWinner": r["ourTeamsIncludeWinner"],
                "squadShare630": (sq630 / r["land"]) if r["land"] else None,
                "squadShare1530": (sq1530 / r["land"]) if r["land"] else None,
                "cov630": cov630, "cov1530": cov1530, "alive630": alive630, "alive1530": alive1530,
                "primShare630": (sum(b["terr630"] or 0 for b in prim_bots) / r["land"]) if r["land"] else None,
                "primShare1530": (sum(b["terr1530"] or 0 for b in prim_bots) / r["land"]) if r["land"] else None,
                "nPrimBots": len(prim_bots),
                "nSnapMissing": sum(b["nSnapMissing"] for b in r["bots"]), "nSnap": sum(b["nSnap"] for b in r["bots"]),
                "nBotsSkip": sum(1 for b in r["bots"] if (b["skipFinal"] or 0) > 0),
                "nBotsWithSnap": sum(1 for b in r["bots"] if b["nSnap"] > 0),
                "resets": sorted({t0 for b in r["bots"] for t0 in b["counterResetsAt"]}),
            })
    return out


def outcome_num(o: str, mode: str = "main"):
    """WIN/LOSS 及 LIKELY → 1/0；UNKNOWN → None。mode='strict' 时 LIKELY 也算 None。"""
    if o == "WIN":
        return 1
    if o == "LOSS":
        return 0
    if mode == "main":
        if o == "WIN_LIKELY":
            return 1
        if o == "LOSS_LIKELY":
            return 0
    return None


def room_stratum(us: list[dict]) -> dict:
    """us：组队局、有对局的房间。"""
    cnt = Counter(u["outcome"] for u in us)
    n = len(us)
    res_main = [(outcome_num(u["outcome"]), 1.0 / u["T"]) for u in us if outcome_num(u["outcome"]) is not None and u["T"]]
    res_strict = [(outcome_num(u["outcome"], "strict"), 1.0 / u["T"]) for u in us
                  if outcome_num(u["outcome"], "strict") is not None and u["T"]]
    w_main = sum(w for w, _ in res_main)
    w_strict = sum(w for w, _ in res_strict)
    unknown = n - len(res_main)
    ls = None
    if res_main and 0 < w_main < len(res_main):
        l = S.logit_shift([w for w, _ in res_main], [e for _, e in res_main])
        nb = sum(u["nBots"] for u in us) / len(us)
        ls = {"odds_ratio": l["odds_ratio"], "or_lo": math.exp(l["delta_lo"]), "or_hi": math.exp(l["delta_hi"]),
              "delta": l["delta_hat"], "lo": l["delta_lo"], "hi": l["delta_hi"],
              # 把整队的赔率倍数摊到每个号上（按这一层房间的平均号数）
              "meanBots": nb, "perBotBeta": l["delta_hat"] / nb, "perBotOdds": math.exp(l["delta_hat"] / nb)}
    return {
        "n": n, "counts": {k: cnt.get(k, 0) for k in ("WIN", "WIN_LIKELY", "UNKNOWN", "LOSS_LIKELY", "LOSS")},
        "logit": ls,
        "main": {"rate": rate(w_main, len(res_main)), "excess": excess([w for w, _ in res_main], [e for _, e in res_main])},
        "strict": {"rate": rate(w_strict, len(res_strict)),
                   "excess": excess([w for w, _ in res_strict], [e for _, e in res_strict])},
        "bounds": {"lo": (w_main / n) if n else None, "hi": ((w_main + unknown) / n) if n else None},
        "base_mean_all": (sum(1.0 / u["T"] for u in us if u["T"]) / max(1, sum(1 for u in us if u["T"]))) if us else None,
    }


def tagged_tables(units: list[dict]) -> dict:
    out = {}
    for co in ("squad8", "squad10"):
        us = [u for u in units if u["cohort"] == co]
        team_main = [u for u in us if u["isTeamGame"] is not False and u["kind"] == "main" and u["outcome"] != "NO_PLAY"]
        out[co] = {
            "nBundles": len({u["matchId"] for u in us}),
            "nRooms": len(us),
            "nNonTeam": sum(1 for u in us if u["isTeamGame"] is False),
            "nNoPlay": sum(1 for u in us if u["isTeamGame"] is not False and u["outcome"] == "NO_PLAY"),
            "nFragment": sum(1 for u in us if u["isTeamGame"] is not False and u["kind"] == "fragment" and u["outcome"] != "NO_PLAY"),
            "all": room_stratum(team_main),
            "byT": {tb: room_stratum([u for u in team_main if u["tb"] == tb]) for tb in TB},
            "bySplitSet": {s: room_stratum([u for u in team_main if u["split"] == s]) for s in ("discovery", "validation")},
            "bySeeded20": {"seeded=20": room_stratum([u for u in team_main if u["seeded"] == 20]),
                           "seeded>20": room_stratum([u for u in team_main if (u["seeded"] or 0) > 20]),
                           "seeded<20": room_stratum([u for u in team_main if (u["seeded"] or 0) < 20])},
            "fragments": room_stratum([u for u in us if u["isTeamGame"] is not False and u["kind"] == "fragment"
                                       and u["outcome"] != "NO_PLAY"]),
            "withFragments": room_stratum([u for u in us if u["isTeamGame"] is not False and u["outcome"] != "NO_PLAY"]),
            "byVersion": {v: room_stratum([u for u in team_main if u["ver"] == v]) for v in VERSIONS},
            "byVersionT": {v: {tb: room_stratum([u for u in team_main if u["ver"] == v and u["tb"] == tb]) for tb in TB}
                           for v in VERSIONS},
            "byOwnFrac": {"<1/3": room_stratum([u for u in team_main if u["ownFrac"] is not None and u["ownFrac"] < 1 / 3]),
                          "1/3~2/3": room_stratum([u for u in team_main if u["ownFrac"] is not None and 1 / 3 <= u["ownFrac"] < 2 / 3]),
                          ">=2/3": room_stratum([u for u in team_main if u["ownFrac"] is not None and u["ownFrac"] >= 2 / 3])},
            "noEarlyLeave": room_stratum([u for u in team_main if u["nLeftEarly"] == 0]),
            "someEarlyLeave": room_stratum([u for u in team_main if u["nLeftEarly"] > 0]),
            "noPeer": room_stratum([u for u in team_main if not u["hasPeer"]]),
            "withPeer": room_stratum([u for u in team_main if u["hasPeer"]]),
            "tHow": dict(Counter(u["tHow"] for u in team_main)),
            "nUsedPeerRows": sum(1 for u in team_main if u["usedPeerRows"]),
        }
    return out


def calibration(allb: list[dict]) -> dict:
    """
    用「胜方已知」的房间校准：我方某个号阵亡（died 行）那一刻，它所在队伍的份额 s → 这个队最后赢没赢。
    每条 died 行一个数据点。只用本包自己的行（同一物理房间的另一个包会各自贡献自己的行）。
    """
    pts = []
    for a in allb:
        for r in a["rooms"]:
            if r["winner"] is None or not r["land"] or r["isTeamGame"] is False:
                continue
            for row in r["totalsRows"]:
                if row["event"] != "died" or row["mine"] is None:
                    continue
                real = {int(k): v for k, v in row["totals"].items() if k != "0"}
                v = real.get(row["mine"], 0)
                share = v / r["land"]
                rank = 1 + sum(1 for x in real.values() if x > v)
                pts.append({"cohort": a["cohort"], "split": a["split"], "share": share, "rank": rank,
                            "win": int(row["mine"] == r["winner"]), "tick": row["tick"], "T": r["tBest"]})
    bins = []
    for lo, hi in zip(SHARE_BINS, SHARE_BINS[1:]):
        ps = [p for p in pts if lo <= p["share"] < hi]
        k = sum(p["win"] for p in ps)
        bins.append({"lo": lo, "hi": min(hi, 1.0), "n": len(ps), "wins": k, "rate": rate(k, len(ps)),
                     "rank1": sum(1 for p in ps if p["rank"] == 1),
                     "rank1_wins": sum(p["win"] for p in ps if p["rank"] == 1)})
    lik = {
        "WIN_LIKELY(rank1,share>=0.5)": rate(sum(p["win"] for p in pts if p["rank"] == 1 and p["share"] >= 0.5),
                                             sum(1 for p in pts if p["rank"] == 1 and p["share"] >= 0.5)),
        "LOSS_LIKELY(rank>1,share<0.2)": rate(sum(p["win"] for p in pts if p["rank"] != 1 and p["share"] < 0.2),
                                              sum(1 for p in pts if p["rank"] != 1 and p["share"] < 0.2)),
        "UNKNOWN(other)": rate(sum(p["win"] for p in pts if not ((p["rank"] == 1 and p["share"] >= 0.5) or (p["rank"] != 1 and p["share"] < 0.2))),
                               sum(1 for p in pts if not ((p["rank"] == 1 and p["share"] >= 0.5) or (p["rank"] != 1 and p["share"] < 0.2)))),
    }
    return {"nPoints": len(pts), "bins": bins, "likelyRules": lik}


def impute_p(share: float, calib: dict):
    for b in calib["bins"]:
        if b["lo"] <= share < b["hi"] or (b["hi"] >= 1.0 and share >= b["lo"]):
            return b["rate"]["rate"]
    return None


# ----------------------------------------------------------------------------
# D. squad20：按队伍为单位
# ----------------------------------------------------------------------------

def cond_logit(rooms_: list[dict], n_par: int):
    """
    条件 logit：P(房间 r 的胜方是队 j) = exp(x_j·β) / Σ_j' exp(x_j'·β)。
    rooms_：[{ "x": [[...每队的协变量...], ...], "w": 胜方下标 }]。牛顿法；返回 β、标准误、对数似然。
    """
    beta = [0.0] * n_par

    def ll_grad_hess(b):
        ll = 0.0
        g = [0.0] * n_par
        h = [[0.0] * n_par for _ in range(n_par)]
        for rm in rooms_:
            xs = rm["x"]
            eta = [sum(bi * xi for bi, xi in zip(b, x)) for x in xs]
            m = max(eta)
            ws = [math.exp(e - m) for e in eta]
            z = sum(ws)
            ps = [w / z for w in ws]
            ll += eta[rm["w"]] - m - math.log(z)
            mean = [sum(p * x[k] for p, x in zip(ps, xs)) for k in range(n_par)]
            for k in range(n_par):
                g[k] += xs[rm["w"]][k] - mean[k]
                for l in range(n_par):
                    h[k][l] -= sum(p * (x[k] - mean[k]) * (x[l] - mean[l]) for p, x in zip(ps, xs))
        return ll, g, h

    def solve(hm, gv):
        # 解 (−H) d = g，n_par ≤ 2
        if n_par == 1:
            return [gv[0] / (-hm[0][0])] if hm[0][0] != 0 else [0.0]
        a, b_, c, d = -hm[0][0], -hm[0][1], -hm[1][0], -hm[1][1]
        det = a * d - b_ * c
        if abs(det) < 1e-12:
            return [0.0, 0.0]
        return [(d * gv[0] - b_ * gv[1]) / det, (-c * gv[0] + a * gv[1]) / det]

    ll0 = ll_grad_hess(beta)[0]
    for _ in range(100):
        ll, g, h = ll_grad_hess(beta)
        step = solve(h, g)
        # 限步，防止发散
        mx = max(abs(s) for s in step) if step else 0.0
        if mx > 1.0:
            step = [s / mx for s in step]
        beta = [b + s for b, s in zip(beta, step)]
        if mx < 1e-9:
            break
    ll, g, h = ll_grad_hess(beta)
    se = []
    if n_par == 1:
        se = [math.sqrt(1.0 / -h[0][0])] if h[0][0] < 0 else [None]
    else:
        a, b_, c, d = -h[0][0], -h[0][1], -h[1][0], -h[1][1]
        det = a * d - b_ * c
        se = [math.sqrt(d / det) if det > 0 and d / det > 0 else None,
              math.sqrt(a / det) if det > 0 and a / det > 0 else None]
    return {"beta": beta, "se": se, "ll": ll, "ll0": ll0, "lr_chi2": 2 * (ll - ll0), "nRooms": len(rooms_)}


def chi2_sf(x: float, df: int) -> float:
    """卡方分布上尾概率，df ∈ {1, 2}。"""
    if x <= 0:
        return 1.0
    if df == 1:
        return math.erfc(math.sqrt(x / 2.0))
    if df == 2:
        return math.exp(-x / 2.0)
    raise ValueError(df)


def squad20_team_level(allb: list[dict], which: str) -> dict:
    """
    squad20 的房间（组队局、队伍数已知、号数 ≥ MAIN_ROOM_MIN_BOTS）按「房间 × 队伍」展开。
    which: 'all' | 'discovery' | 'validation'
    """
    # A 组在同一物理房间里的队伍
    a_team = {}
    for a in allb:
        if a["cohort"] != "squad10":
            continue
        for r in a["rooms"]:
            if r["physRoom"] is not None and r["primaryTeam"] is not None and r["nBots"] >= MAIN_ROOM_MIN_BOTS:
                a_team[r["physRoom"]] = (r["primaryTeam"], r["nBots"])
    rooms_ = []
    for a in allb:
        if a["cohort"] != "squad20" or (which != "all" and a["split"] != which):
            continue
        for r in a["rooms"]:
            if r["isTeamGame"] is False or not r["tBest"] or r["nBots"] < MAIN_ROOM_MIN_BOTS:
                continue
            if r["outcome"] == "NO_PLAY":
                continue
            rooms_.append((a, r))
    summary = {"nRooms": len(rooms_), "nWinnerKnown": 0, "nBots": 0, "nBotsTeamKnown": 0, "nBotsTeamUnknown": 0}
    team_units = []          # 每个 (房间, 我方占的队)
    cl_rooms = []            # 条件 logit 用：胜方已知的房间
    cover_obs, cover_exp = [], []
    any_obs = []
    prim_main, prim_exp = [], []
    for a, r in rooms_:
        t = r["tBest"]
        ks = {int(k): v for k, v in r["teams"].items()}
        summary["nBots"] += r["nBots"]
        summary["nBotsTeamKnown"] += sum(ks.values())
        summary["nBotsTeamUnknown"] += r["nTeamUnknown"]
        at = a_team.get(r["physRoom"])
        for tm, k in ks.items():
            o = r["teamOutcomes"][str(tm)]
            team_units.append({"matchId": a["matchId"], "split": a["split"], "roomIdx": r["roomIdx"], "team": tm, "k": k,
                               "T": t, "outcome": o["outcome"], "lastShare": o["lastShare"], "lastRank": o["lastRank"],
                               "withA": bool(at and at[0] == tm), "roomHasA": bool(at),
                               "isPrimary": tm == r["primaryTeam"], "seeded": r["seeded"]})
        if r["winner"] is not None:
            summary["nWinnerKnown"] += 1
            occ = len(ks)
            cover_obs.append(int(r["winner"] in ks))
            cover_exp.append(min(1.0, occ / t))
            any_obs.append(int(bool(r["anyBotWonRow"])))
            ids = sorted(set(range(1, t + 1)) | set(ks) | {r["winner"]})
            xs = [[float(ks.get(j, 0)), 1.0 if (at and at[0] == j) else 0.0] for j in ids]
            cl_rooms.append({"x": xs, "w": ids.index(r["winner"]), "matchId": a["matchId"],
                             "unknownFrac": r["nTeamUnknown"] / r["nBots"], "hasA": bool(at)})
        if r["primaryTeam"] is not None and not r["primaryUncertain"]:
            w = outcome_num(r["outcome"])
            if w is not None:
                prim_main.append(w)
                prim_exp.append(1.0 / t)
    # 按 k 分档
    by_k = {}
    for label, f in (("k=1", lambda k: k == 1), ("k=2", lambda k: k == 2), ("k=3", lambda k: k == 3),
                     ("k=4-5", lambda k: 4 <= k <= 5), ("k>=6", lambda k: k >= 6)):
        us = [u for u in team_units if f(u["k"])]
        res = [u for u in us if u["outcome"] in ("WIN", "LOSS")]
        w = sum(1 for u in res if u["outcome"] == "WIN")
        by_k[label] = {"n": len(us), "nResolved": len(res), "nOpen": len(us) - len(res), "rate": rate(w, len(res)),
                       "excess": excess([int(u["outcome"] == "WIN") for u in res], [1.0 / u["T"] for u in res])}
    res_all = [u for u in team_units if u["outcome"] in ("WIN", "LOSS")]
    cl1 = cond_logit([{"x": [[x[0]] for x in rm["x"]], "w": rm["w"]} for rm in cl_rooms], 1) if cl_rooms else None
    cl2 = cond_logit(cl_rooms, 2) if any(rm["hasA"] for rm in cl_rooms) else None
    cl_noA = [rm for rm in cl_rooms if not rm["hasA"]]
    cl1_noA = cond_logit([{"x": [[x[0]] for x in rm["x"]], "w": rm["w"]} for rm in cl_noA], 1) if cl_noA else None
    cl_lowunk = [rm for rm in cl_rooms if rm["unknownFrac"] <= 0.2]
    cl1_lowunk = cond_logit([{"x": [[x[0]] for x in rm["x"]], "w": rm["w"]} for rm in cl_lowunk], 1) if cl_lowunk else None

    def pack(cl):
        if cl is None:
            return None
        b, se = cl["beta"][0], cl["se"][0]
        o = {"beta_k": b, "se": se, "lo": (b - 1.96 * se) if se else None, "hi": (b + 1.96 * se) if se else None,
             "oddsPerBot": math.exp(b), "nRooms": cl["nRooms"], "lr_chi2": cl["lr_chi2"],
             "p_lr": chi2_sf(cl["lr_chi2"], len(cl["beta"]))}
        if len(cl["beta"]) > 1:
            o["beta_A"] = cl["beta"][1]
            o["se_A"] = cl["se"][1]
        return o
    return {
        "summary": summary,
        "teamUnits": {"n": len(team_units), "nResolved": len(res_all),
                      # 结局没看到的队：下界 = 全算负；上界 = 每个没看到结局的房间最多再多一个胜队
                      "boundLo": (sum(1 for u in res_all if u["outcome"] == "WIN") / len(team_units)) if team_units else None,
                      "boundHi": ((sum(1 for u in res_all if u["outcome"] == "WIN")
                                   + len({(u["matchId"], u["roomIdx"]) for u in team_units if u["outcome"] not in ("WIN", "LOSS")}))
                                  / len(team_units)) if team_units else None,
                      "expectedAllUnits": (sum(1.0 / u["T"] for u in team_units) / len(team_units)) if team_units else None,
                      "rate": rate(sum(1 for u in res_all if u["outcome"] == "WIN"), len(res_all)),
                      "excess": excess([int(u["outcome"] == "WIN") for u in res_all], [1.0 / u["T"] for u in res_all])},
        "byK": by_k,
        "coverage": {"n": len(cover_obs), "winnerAmongOurTeams": rate(sum(cover_obs), len(cover_obs)),
                     "expected_mean": (sum(cover_exp) / len(cover_exp)) if cover_exp else None,
                     "excess": excess(cover_obs, cover_exp),
                     "anyBotWonRow": rate(sum(any_obs), len(any_obs))},
        "primary": {"n": len(prim_main), "rate": rate(sum(prim_main), len(prim_main)), "excess": excess(prim_main, prim_exp)},
        "condLogit": {"kOnly": pack(cl1), "kPlusA": pack(cl2), "kOnly_roomsWithoutA": pack(cl1_noA),
                      "kOnly_unknownFrac<=0.2": pack(cl1_lowunk)},
        "_teamUnits": team_units,
    }


# ----------------------------------------------------------------------------
# E. 过程指标（发现集）
# ----------------------------------------------------------------------------

def process_metrics(units: list[dict], allb: list[dict], cards: list[dict], per: dict) -> dict:
    disc = [u for u in units if u["split"] == "discovery" and u["isTeamGame"] is not False
            and u["kind"] == "main" and u["outcome"] != "NO_PLAY"]
    card_by_id = {c["matchId"]: c for c in cards}
    out = {"squadShare": {}, "anomalies": {}}
    for co in COHORTS:
        us = [u for u in disc if u["cohort"] == co and u["T"]]
        block = {}
        for t in (630, 1530):
            key = f"squadShare{t}"
            pkey = f"primShare{t}"
            rows = []
            for u in us:
                w = outcome_num(u["outcome"])
                if w is None or u[key] is None:
                    continue
                if co == "squad20" and u["primaryUncertain"]:
                    continue
                share = u[key] if co != "squad20" else u[pkey]
                rows.append({"matchId": u["matchId"], "w": w, "share": share, "rel": share * u["T"],
                             "perBot": share / max(1, (u["nBots"] if co != "squad20" else u["nPrimBots"])) * u["seeded"],
                             "tb": u["tb"], "T": u["T"]})
            pos = [r["share"] for r in rows if r["w"] == 1]
            neg = [r["share"] for r in rows if r["w"] == 0]
            rel_pos = [r["rel"] for r in rows if r["w"] == 1]
            rel_neg = [r["rel"] for r in rows if r["w"] == 0]
            sa, pairs = stratified_auc([(r["tb"], r["w"], r["share"]) for r in rows])
            # 中位数切分：份额在中位数以上 / 以下的胜率
            med = quantiles([r["share"] for r in rows]).get("median")
            hi = [r for r in rows if med is not None and r["share"] > med]
            lo = [r for r in rows if med is not None and r["share"] <= med]
            block[str(t)] = {
                "n": len(rows), "nWin": len(pos), "nLoss": len(neg),
                "share_win": quantiles(pos), "share_loss": quantiles(neg),
                "auc": auc_ci(pos, neg), "auc_rel": auc_ci(rel_pos, rel_neg),
                "auc_stratT": sa, "auc_stratT_pairs": pairs,
                "spearman": spearman([r["share"] for r in rows], [float(r["w"]) for r in rows]),
                "median": med,
                "aboveMedian": {"rate": rate(sum(r["w"] for r in hi), len(hi)),
                                "base": (sum(1.0 / r["T"] for r in hi) / len(hi)) if hi else None},
                "belowMedian": {"rate": rate(sum(r["w"] for r in lo), len(lo)),
                                "base": (sum(1.0 / r["T"] for r in lo) / len(lo)) if lo else None},
                "fisher_p": S.fisher_exact(sum(r["w"] for r in lo), len(lo), sum(r["w"] for r in hi), len(hi)) if hi and lo else None,
            }
        # 卡片标签对照（同一批房间，标签换成卡片的 primaryTeamWon）
        for t in (630, 1530):
            key = f"squadShare{t}"
            rows = [(int(bool(card_by_id[u["matchId"]]["outcome"]["primaryTeamWon"])), u[key]) for u in us
                    if u[key] is not None and u["isMainRoomOfBundle"]]
            pos = [v for w, v in rows if w]
            neg = [v for w, v in rows if not w]
            block[str(t)]["auc_cardLabel"] = auc_ci(pos, neg)
        out["squadShare"][co] = block
    # 只看 squad10 的 Vb 版本（样本最多的一个版本），排除版本混杂
    vb = {}
    for t in (630, 1530):
        rows = [(outcome_num(u["outcome"]), u[f"squadShare{t}"], u["tb"]) for u in disc
                if u["cohort"] == "squad10" and u["ver"] == "Vb" and u["T"] and outcome_num(u["outcome"]) is not None
                and u[f"squadShare{t}"] is not None]
        sa, pairs = stratified_auc([(tb, w, v) for w, v, tb in rows])
        vb[str(t)] = {"n": len(rows), "nWin": sum(w for w, _, _ in rows), "nLoss": sum(1 - w for w, _, _ in rows),
                      "auc": auc_ci([v for w, v, _ in rows if w], [v for w, v, _ in rows if not w]),
                      "auc_stratT": sa, "auc_stratT_pairs": pairs,
                      "share_win": quantiles([v for w, v, _ in rows if w]), "share_loss": quantiles([v for w, v, _ in rows if not w])}
    out["squadShareVb"] = vb
    # squad20 按「房间 × 队伍」：这个队里我方号在第 t 拍的领土份额（合计、每号平均）对这个队最后胜负的预测力
    tl = {}
    for t in (630, 1530):
        rows = []
        for a in allb:
            if a["cohort"] != "squad20" or a["split"] != "discovery":
                continue
            for r in a["rooms"]:
                if r["isTeamGame"] is False or not r["tBest"] or r["nBots"] < MAIN_ROOM_MIN_BOTS or not r["land"]:
                    continue
                for tm, o in r["teamOutcomes"].items():
                    if o["outcome"] not in ("WIN", "LOSS"):
                        continue
                    bots = [b for b in r["bots"] if b["team"] is not None and str(b["team"]) == tm]
                    tot = sum(b[f"terr{t}"] or 0 for b in bots)
                    rows.append({"w": int(o["outcome"] == "WIN"), "sum": tot / r["land"], "mean": tot / r["land"] / len(bots),
                                 "tb": team_bucket(r["tBest"]), "k": len(bots)})
        pos_s = [x["sum"] for x in rows if x["w"]]
        neg_s = [x["sum"] for x in rows if not x["w"]]
        pos_m = [x["mean"] for x in rows if x["w"]]
        neg_m = [x["mean"] for x in rows if not x["w"]]
        sa, pairs = stratified_auc([(x["tb"], x["w"], x["mean"]) for x in rows])
        tl[str(t)] = {"n": len(rows), "nWin": len(pos_s), "nLoss": len(neg_s),
                      "auc_sum": auc_ci(pos_s, neg_s), "auc_mean": auc_ci(pos_m, neg_m),
                      "auc_mean_stratT": sa, "auc_mean_stratT_pairs": pairs,
                      "mean_win": quantiles(pos_m), "mean_loss": quantiles(neg_m)}
    out["squad20TeamLevel"] = tl
    # 拒单率、内陆高密度快照数 与 主房间结局（发现集；只用单房间的包，避免把两个房间的计数混在一起）
    avo = {}
    single = {a["matchId"] for a in allb if sum(1 for r in a["rooms"] if r["nBots"] >= MAIN_ROOM_MIN_BOTS) == 1}
    for co in COHORTS:
        us = [u for u in disc if u["cohort"] == co and u["matchId"] in single and u["isMainRoomOfBundle"]]
        rr, bx, bs, ls_ = [], [], [], []
        for u in us:
            w = outcome_num(u["outcome"])
            if w is None or (co == "squad20" and u["primaryUncertain"]):
                continue
            a = card_by_id[u["matchId"]]["anomaliesSummary"]
            if a["totalTransfers"] > 0:
                rr.append((w, a["likelyRejectedTransfers"] / a["totalTransfers"]))
            bx.append((w, a["boxedHighDensSnapshots"] / max(1, u["nBots"])))
            ls_.append((w, per[u["matchId"]]["snapLate"] / max(1, u["nBots"])))
            if per[u["matchId"]]["snapLate"] > 0:
                bs.append((w, per[u["matchId"]]["boxed"] / per[u["matchId"]]["snapLate"]))
        avo[co] = {"lateSnapPerBot": auc_ci([v for w, v in ls_ if w], [v for w, v in ls_ if not w]),
                   "lateSnap_win": quantiles([v for w, v in ls_ if w]), "lateSnap_loss": quantiles([v for w, v in ls_ if not w]),
                   "rejRate": auc_ci([v for w, v in rr if w], [v for w, v in rr if not w]),
                   "boxedPerLateSnap": auc_ci([v for w, v in bs if w], [v for w, v in bs if not w]),
                   "boxedLate_win": quantiles([v for w, v in bs if w]), "boxedLate_loss": quantiles([v for w, v in bs if not w]),
                   "boxedPerBot": auc_ci([v for w, v in bx if w], [v for w, v in bx if not w]),
                   "rejRate_win": quantiles([v for w, v in rr if w]), "rejRate_loss": quantiles([v for w, v in rr if not w]),
                   "boxed_win": quantiles([v for w, v in bx if w]), "boxed_loss": quantiles([v for w, v in bx if not w])}
    out["anomalyVsOutcome"] = avo
    # 异常计数：拒单、内陆高密度（squad10 另按策略版本拆开）
    groups = [(co, [c for c in cards if c["cohort"] == co and c["split"] == "discovery"]) for co in COHORTS]
    groups += [(f"squad10·{v}", [c for c in cards if c["cohort"] == "squad10" and c["split"] == "discovery"
                                  and strategy_version(c) == v]) for v in VERSIONS]
    for co, cs in groups:
        rej, tot, boxed, rates = [], [], [], []
        for c in cs:
            a = c["anomaliesSummary"]
            rej.append(a["likelyRejectedTransfers"])
            tot.append(a["totalTransfers"])
            boxed.append(a["boxedHighDensSnapshots"])
            if a["totalTransfers"] > 0:
                rates.append(a["likelyRejectedTransfers"] / a["totalTransfers"])
        out["anomalies"][co] = {
            "nBundles": len(cs),
            "transfers": quantiles([float(x) for x in tot]),
            "rejected": quantiles([float(x) for x in rej]),
            "rejRatePerBundle": quantiles(rates),
            "rejRatePooled": rate(sum(rej), sum(tot)),
            "nBundlesNoTransfers": sum(1 for x in tot if x == 0),
            "boxed": quantiles([float(x) for x in boxed]),
            "nBundlesBoxed0": sum(1 for x in boxed if x == 0),
            "boxedTotal": sum(boxed),
        }
    return out


def recount_anomalies(cards: list[dict]) -> dict:
    """从 events.csv / traj.csv 重数拒单数和内陆高密度快照数，与卡片对账。"""
    mism = []
    per = {}
    for c in cards:
        ev = load_events(c)
        tr = load_traj(c)
        n_tr = sum(1 for e in ev if e["type"] in ("DONATE", "DISPATCH"))
        n_don = sum(1 for e in ev if e["type"] == "DONATE")
        n_rej = sum(1 for e in ev if e["type"] in ("DONATE", "DISPATCH") and e["likelyRejected"])
        n_box = sum(1 for r in tr if r["nb"] == 0 and r["neut"] == 0 and r["dens"] >= 95 and r["t"] >= 1500)
        n_late = sum(1 for r in tr if r["t"] >= 1500)
        a = c["anomaliesSummary"]
        per[c["matchId"]] = {"transfers": n_tr, "donates": n_don, "rejected": n_rej, "boxed": n_box, "snapLate": n_late}
        if (n_tr, n_rej, n_box) != (a["totalTransfers"], a["likelyRejectedTransfers"], a["boxedHighDensSnapshots"]):
            mism.append({"matchId": c["matchId"], "split": c["split"], "card": [a["totalTransfers"], a["likelyRejectedTransfers"],
                                                                                 a["boxedHighDensSnapshots"]],
                         "recount": [n_tr, n_rej, n_box]})
    return {"nCards": len(cards), "nMismatch": len(mism), "mismatches": mism, "_per": per}


def boxed_rates(cards: list[dict], per: dict) -> dict:
    out = {}
    groups = [(co, [c for c in cards if c["cohort"] == co and c["split"] == "discovery"]) for co in COHORTS]
    groups += [(f"squad10·{v}", [c for c in cards if c["cohort"] == "squad10" and c["split"] == "discovery"
                                  and strategy_version(c) == v]) for v in VERSIONS]
    for co, cs in groups:
        b = sum(per[c["matchId"]]["boxed"] for c in cs)
        n = sum(per[c["matchId"]]["snapLate"] for c in cs)
        out[co] = {"boxed": b, "snapLate": n, "rate": rate(b, n)}
    return out


# ----------------------------------------------------------------------------
# F. 数据质量
# ----------------------------------------------------------------------------

def data_quality(allb: list[dict], units: list[dict]) -> dict:
    out = {"byCohort": {}, "resets": [], "physical": {}, "startGaps": None}
    for co in COHORTS:
        bs = [a for a in allb if a["cohort"] == co]
        bots = [b for a in bs for r in a["rooms"] for b in r["bots"]]
        with_snap = [b for b in bots if b["nSnap"] > 0]
        n_snap = sum(b["nSnap"] for b in with_snap)
        n_miss = sum(b["nSnapMissing"] for b in with_snap)
        skip = [b["skipFinal"] for b in with_snap if b["skipFinal"] is not None]
        maxms = [b["maxMsFinal"] for b in with_snap if b["maxMsFinal"] is not None]
        avgms = [b["avgMsFinal"] for b in with_snap if b["avgMsFinal"] is not None]
        ev = Counter(b["event"] or "none" for b in bots)
        how = Counter(b["teamHow"] or "unknown" for b in bots)
        rhow = Counter(b["resultHow"] or "none" for b in bots)
        edges = Counter()
        for a in bs:
            for r in a["rooms"]:
                for k, v in (r.get("allyEdges") or {}).items():
                    edges[k] += v
        out["byCohort"][co] = {
            "allyEdges": dict(edges),
            "nBundles": len(bs), "nBots": len(bots), "nRooms": sum(a["nRooms"] for a in bs),
            "nMultiRoomBundles": sum(1 for a in bs if a["nRooms"] > 1),
            "botsPerBundle": quantiles([float(a["nBots"]) for a in bs]),
            "events": dict(ev), "teamHow": dict(how), "resultHow": dict(rhow),
            "nRenamed": sum(1 for b in bots if len(b["names"]) > 1),
            "namesPerBot": quantiles([float(len(b["names"])) for b in bots]),
            "idIndependentOk": sum(a["idCheckIndependentOk"] for a in bs),
            "idIndependentBad": sum(a["idCheckIndependentBad"] for a in bs),
            "nSnap": n_snap, "nSnapMissing": n_miss, "missRate": rate(n_miss, n_snap + n_miss),
            "botsWithSkip": rate(sum(1 for x in skip if x > 0), len(skip)),
            "skipFinal": quantiles([float(x) for x in skip]),
            "maxMsFinal": quantiles([float(x) for x in maxms]),
            "avgMsFinal": quantiles([float(x) for x in avgms]),
        }
    for u in units:
        if u["resets"]:
            out["resets"].append({"matchId": u["matchId"] if u["split"] == "discovery" else "(validation)",
                                  "split": u["split"], "roomIdx": u["roomIdx"], "ticks": u["resets"]})
    phys = R.analyze_all.phys
    multi = [p for p in phys if len(p["members"]) > 1]
    out["physical"] = {
        "nPhysicalRooms": len(phys), "nShared": len(multi),
        "nSharedDiscOnly": sum(1 for p in multi if all(m["split"] == "discovery" for m in p["members"])),
        "nSharedValOnly": sum(1 for p in multi if all(m["split"] == "validation" for m in p["members"])),
        "nSharedMixed": sum(1 for p in multi if len({m["split"] for m in p["members"]}) > 1),
        "sharedDiscoveryPairs": [[f"{m['matchId']}#{m['roomIdx']}" for m in p["members"]] for p in multi
                                 if all(m["split"] == "discovery" for m in p["members"])],
        "nValidationBundlesSharingWithDiscovery": len({m["matchId"] for p in multi if len({x["split"] for x in p["members"]}) > 1
                                                       for m in p["members"] if m["split"] == "validation"}),
        "nDiscoveryBundlesSharingWithValidation": len({m["matchId"] for p in multi if len({x["split"] for x in p["members"]}) > 1
                                                       for m in p["members"] if m["split"] == "discovery"}),
        "discoveryBundlesSharingWithValidation": sorted({m["matchId"] for p in multi if len({x["split"] for x in p["members"]}) > 1
                                                         for m in p["members"] if m["split"] == "discovery"}),
    }
    # 20 人房间里我方的人数
    s20 = [u for u in units if u["seeded"] == 20]
    out["seeded20"] = {
        "nRooms": len(s20),
        "byCohort": {co: {"nRooms": sum(1 for u in s20 if u["cohort"] == co),
                          "ourBots": quantiles([float(u["nBots"]) for u in s20 if u["cohort"] == co])} for co in COHORTS},
        "nBundles": len({u["matchId"] for u in s20}),
    }
    return out


def start_gap_table(cards: list[dict]) -> dict:
    """同一 (land, seeded) 组里结算行开局墙钟的相邻间隔分布（分房间阈值的依据）。"""
    hist = Counter()
    for c in cards:
        b = R.read_bundle(c)
        g = defaultdict(list)
        for r in b["results"]:
            g[(r["land"], r["seededPlayers"])].append(r["_start"])
        for k, v in g.items():
            v.sort()
            for x, y in zip(v, v[1:]):
                d = y - x
                if d < 0.5:
                    hist["<0.5"] += 1
                elif d < 1.0:
                    hist["0.5-1.0"] += 1
                elif d < 1.6:
                    hist["1.0-1.6"] += 1
                elif d < 3.0:
                    hist["1.6-3.0"] += 1
                elif d < 12.0:
                    hist["3.0-12"] += 1
                else:
                    hist[">=12"] += 1
    return {k: hist.get(k, 0) for k in ("<0.5", "0.5-1.0", "1.0-1.6", "1.6-3.0", "3.0-12", ">=12")}


# ----------------------------------------------------------------------------
# 对账：卡片 vs 房间
# ----------------------------------------------------------------------------

def reconcile(cards: list[dict], allb: list[dict]) -> dict:
    by_id = {a["matchId"]: a for a in allb}
    rows = []
    for c in cards:
        a = by_id[c["matchId"]]
        main = next(r for r in a["rooms"] if r["roomIdx"] == a["mainRoom"])
        flags = []
        if main["isTeamGame"] is False:
            flags.append("非组队局")
        if main["isTeamGame"] is not False and main["outcome"] == "NO_PLAY":
            flags.append("全员掉线无结局")
        if a["nRooms"] > 1 and sum(1 for r in a["rooms"] if any(b["event"] for b in r["bots"])) > 1:
            flags.append("多房间")
        if main["isTeamGame"] is not False and main["tBest"] and main["tBest"] != c["actualTeams"]:
            flags.append("队伍数不同")
        card_w = bool(c["outcome"]["primaryTeamWon"])
        room_w = outcome_num(main["outcome"])
        if main["isTeamGame"] is not False and main["outcome"] != "NO_PLAY":
            if room_w is None:
                flags.append("结局未观察到")
            elif bool(room_w) != card_w:
                flags.append("主队胜负不同")
            elif main["outcome"] in ("WIN_LIKELY", "LOSS_LIKELY"):
                flags.append("结局为推定")
        if main["clanTeamConflict"]:
            flags.append("同标签分在两队")
        if main["primaryUncertain"]:
            flags.append("主队不确定")
        rows.append({"matchId": c["matchId"], "cohort": c["cohort"], "split": c["split"],
                     "cardT": c["actualTeams"], "cardD": c["distinctSquadTeams"], "cardPrim": card_w,
                     "cardAny": bool(c["outcome"]["anyBotWon"]),
                     "nRooms": a["nRooms"], "mainBots": main["nBots"], "roomT": main["tBest"], "tHow": main["tHow"],
                     "roomOutcome": main["outcome"], "primary": main["primaryTeam"], "teams": main["teams"],
                     "nTeamUnknown": main["nTeamUnknown"], "winner": main["winner"], "flags": flags,
                     "otherRooms": [{"roomIdx": r["roomIdx"], "nBots": r["nBots"], "T": r["tBest"], "outcome": r["outcome"],
                                     "seeded": r["seeded"]} for r in a["rooms"] if r["roomIdx"] != a["mainRoom"]]})
    cnt = {co: Counter() for co in COHORTS}
    cnt_split = {s: Counter() for s in ("discovery", "validation")}
    for r in rows:
        for f in r["flags"]:
            cnt[r["cohort"]][f] += 1
            cnt_split[r["split"]][f] += 1
        if not r["flags"]:
            cnt[r["cohort"]]["无差异"] += 1
            cnt_split[r["split"]]["无差异"] += 1
    return {"rows": rows, "flagCounts": {co: dict(v) for co, v in cnt.items()},
            "flagCountsBySplit": {s: dict(v) for s, v in cnt_split.items()}}


# ----------------------------------------------------------------------------
# 报告生成
# ----------------------------------------------------------------------------

def squad20_card_accounting(cards: list[dict], allb: list[dict]) -> dict:
    """
    squad20 的 50 张卡片按「主房间的结局看得见看不见」分类，再数卡片上的 anyBotWon / primaryTeamWon。
    用来说明卡片口径把「没看到结局」的局一律记成了没赢。
    """
    cb = {c["matchId"]: c for c in cards}
    cats = {k: {"n": 0, "any": 0, "prim": 0, "expAny": 0.0, "nExp": 0} for k in ("winnerKnown", "winnerUnknown", "noPlay", "nonTeam")}
    for a in allb:
        if a["cohort"] != "squad20":
            continue
        c = cb[a["matchId"]]
        r = next(x for x in a["rooms"] if x["roomIdx"] == a["mainRoom"])
        if r["isTeamGame"] is False:
            k = "nonTeam"
        elif r["outcome"] == "NO_PLAY":
            k = "noPlay"
        elif r["winner"] is not None:
            k = "winnerKnown"
        else:
            k = "winnerUnknown"
        cats[k]["n"] += 1
        cats[k]["any"] += int(c["outcome"]["anyBotWon"])
        cats[k]["prim"] += int(c["outcome"]["primaryTeamWon"])
        if k in ("winnerKnown", "winnerUnknown") and r["tBest"]:
            cats[k]["expAny"] += min(1.0, len(r["teams"]) / r["tBest"])
            cats[k]["nExp"] += 1
    out = {}
    for k, v in cats.items():
        out[k] = {"n": v["n"], "any": rate(v["any"], v["n"]), "prim": rate(v["prim"], v["n"]),
                  "expAnyCoverage": (v["expAny"] / v["nExp"]) if v["nExp"] else None}
    return out


def shared_rooms(allb: list[dict], phys: list[dict]) -> dict:
    """
    同一个物理房间里同时有 squad10（带 [APEX] 标签，整队在一个队）和 squad20（不带标签，被打散）的情况。
    逐房间列出：标签队在哪个队、结局；squad20 的号各在哪些队、赢的那个队里有没有 squad20 的号。
    公开输出只列两边都是发现集的房间；含验证集的只给合计。
    """
    byid = {a["matchId"]: a for a in allb}

    def room(mid, idx):
        return next(r for r in byid[mid]["rooms"] if r["roomIdx"] == idx)
    rows = []
    for p in phys:
        if len(p["members"]) < 2:
            continue
        mem = [(m["matchId"], m["roomIdx"]) for m in p["members"]]
        a_side = [(m, i) for m, i in mem if byid[m]["cohort"] == "squad10"]
        b_side = [(m, i) for m, i in mem if byid[m]["cohort"] == "squad20"]
        if not a_side or not b_side:
            continue
        ra, rb = room(*a_side[0]), room(*b_side[0])
        a_team = ra["primaryTeam"]
        a_out = ra["outcome"]
        b_teams = {t: o["nBots"] for t, o in rb["teamOutcomes"].items()}
        w = p["winner"]
        rows.append({
            "pair": [f"{m}#{i}" for m, i in (a_side[0], b_side[0])],
            "mixed": any(byid[m]["split"] != "discovery" for m, _ in mem),
            "seeded": p["seeded"], "T": p["tBest"], "winner": w,
            "aTeam": a_team, "aBots": ra["nBots"], "aOutcome": a_out,
            "bBots": rb["nBots"], "bTeams": b_teams, "bUnknownTeam": rb["nTeamUnknown"],
            "bOnATeam": b_teams.get(str(a_team), 0) if a_team is not None else None,
            "bOnWinner": (b_teams.get(str(w), 0) if w is not None else None),
            "aWon": (None if w is None or a_team is None else int(str(w) == str(a_team))),
            "bCoverage": (min(1.0, len(b_teams) / p["tBest"]) if p["tBest"] else None),
        })
    known = [r for r in rows if r["winner"] is not None and r["aWon"] is not None]
    agg = {
        "nRooms": len(rows), "nMixed": sum(1 for r in rows if r["mixed"]), "nWinnerKnown": len(known),
        "aWon": rate(sum(r["aWon"] for r in known), len(known)),
        "aExpected": (sum(1.0 / r["T"] for r in known) / len(known)) if known else None,
        "bOnWinner": rate(sum(1 for r in known if r["bOnWinner"]), len(known)),
        "bExpectedCoverage": (sum(r["bCoverage"] for r in known) / len(known)) if known else None,
        "nBOnATeam": sum(1 for r in rows if r["bOnATeam"]),
        "aWonWhenBOnTeam": rate(sum(r["aWon"] for r in known if r["bOnATeam"]), sum(1 for r in known if r["bOnATeam"])),
        "aWonWhenNoBOnTeam": rate(sum(r["aWon"] for r in known if not r["bOnATeam"]), sum(1 for r in known if not r["bOnATeam"])),
    }
    return {"agg": agg, "rowsDiscovery": [r for r in rows if not r["mixed"]], "_rowsAll": rows}


def pct(x, d=1):
    return "—" if x is None else f"{100 * x:.{d}f}%"


def fnum(x, d=3):
    return "—" if x is None else f"{x:.{d}f}"


def rate_str(r):
    if r is None or r["n"] == 0:
        return "—"
    return f"{r['k']}/{r['n']} = {pct(r['rate'])} [{pct(r['lo'])}, {pct(r['hi'])}]"


def pval(p):
    if p is None:
        return "—"
    return f"{p:.4f}" if p >= 0.0001 else f"{p:.1e}"


def get_path(d, path):
    cur = d
    for part in path.split("."):
        if isinstance(cur, list):
            cur = cur[int(part)]
        else:
            cur = cur[part]
    return cur


def table_card(block: dict, keys: list[tuple[str, str]]) -> str:
    """keys: [(显示名, 路径)]"""
    lines = ["| 分层 | 局数 | 任一号获胜 anyBotWon | 主队获胜 primaryTeamWon | 随机期望 均值(1/T) | 主队超额 | 精确 p(双侧) | any−prim |",
             "|---|---:|---|---|---:|---:|---:|---:|"]
    for name, path in keys:
        s = get_path(block, path)
        if s["n"] == 0:
            lines.append(f"| {name} | 0 | — | — | — | — | — | — |")
            continue
        ex = s["prim_excess"]
        lines.append(f"| {name} | {s['n']} | {rate_str(s['any'])} | {rate_str(s['prim'])} | {pct(s['base_mean'])} | "
                     f"{'+' if ex['excess_per_game'] >= 0 else ''}{pct(ex['excess_per_game'])} | {pval(ex['p_two_sided'])} | "
                     f"{pct(s['any_minus_prim'])} |")
    return "\n".join(lines)


def table_room(block: dict, keys: list[tuple[str, str]]) -> str:
    lines = ["| 分层 | 房间数 | 胜 | 推定胜 | 未知 | 推定负 | 负 | 胜率（含推定，不含未知） | 随机期望 | 超额 | 精确 p(双侧) | 胜率上下界（未知全负~全胜） | 只算确定结局 |",
             "|---|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---|---|"]
    for name, path in keys:
        s = get_path(block, path)
        if s["n"] == 0:
            lines.append(f"| {name} | 0 | | | | | | — | — | — | — | — | — |")
            continue
        c = s["counts"]
        ex = s["main"]["excess"]
        lines.append(
            f"| {name} | {s['n']} | {c['WIN']} | {c['WIN_LIKELY']} | {c['UNKNOWN']} | {c['LOSS_LIKELY']} | {c['LOSS']} | "
            f"{rate_str(s['main']['rate'])} | {pct(ex['mean_base'])} | "
            f"{'—' if ex['excess_per_game'] is None else ('+' if ex['excess_per_game'] >= 0 else '') + pct(ex['excess_per_game'])} | "
            f"{pval(ex['p_two_sided'])} | {pct(s['bounds']['lo'])} ~ {pct(s['bounds']['hi'])} | {rate_str(s['strict']['rate'])} |")
    return "\n".join(lines)


def build_tables(J: dict) -> dict:
    T = {}
    A = J["card"]["all160"]
    T["card_cohort"] = table_card(A, [(co, f"byCohort.{co}") for co in COHORTS] + [("合计 160", "all")])
    T["card_cohort_T"] = table_card(A, [(f"{co} · {tb}", f"byCohortT.{co}.{tb}") for co in COHORTS for tb in TB])
    T["card_cohort_split"] = table_card(A, [(f"{co} · {sf}", f"byCohortSplitFlag.{co}.{sf}") for co in COHORTS
                                            for sf in ("未拆(=1)", "拆队(>1)", "无队号(=0)")
                                            if get_path(A, f"byCohortSplitFlag.{co}.{sf}")["n"] > 0])
    T["card_full"] = table_card(A, [(f"{co} · {tb} · {sf}", f"byCohortTSplitFlag.{co}.{tb}.{sf}") for co in COHORTS for tb in TB
                                    for sf in ("未拆(=1)", "拆队(>1)", "无队号(=0)")
                                    if get_path(A, f"byCohortTSplitFlag.{co}.{tb}.{sf}")["n"] > 0])
    T["card_cohort_set"] = table_card(A, [(f"{co} · {'发现集' if s == 'discovery' else '验证集'}", f"byCohortSplitSet.{co}.{s}")
                                          for co in COHORTS for s in ("discovery", "validation")
                                          if get_path(A, f"byCohortSplitSet.{co}.{s}")["n"] > 0])
    T["card_version"] = table_card(A, [(f"squad10 · {v}", f"byVersion.{v}") for v in VERSIONS]
                                   + [(f"squad10 · {v} · {tb}", f"byVersionT.{v}.{tb}") for v in VERSIONS for tb in TB
                                      if get_path(A, f"byVersionT.{v}.{tb}")["n"] > 0])
    RT = J["room"]["tagged"]
    T["room_version"] = table_room(RT, [(f"squad10 · {v}", f"squad10.byVersion.{v}") for v in VERSIONS]
                                   + [(f"squad10 · {v} · {tb}", f"squad10.byVersionT.{v}.{tb}") for v in VERSIONS for tb in TB
                                      if get_path(RT, f"squad10.byVersionT.{v}.{tb}")["n"] > 0])
    T["room_tagged"] = table_room(RT, [(f"{co} 全部", f"{co}.all") for co in ("squad8", "squad10")]
                                  + [(f"{co} · {tb}", f"{co}.byT.{tb}") for co in ("squad8", "squad10") for tb in TB]
                                  + [("squad10 · 发现集", "squad10.bySplitSet.discovery"), ("squad10 · 验证集", "squad10.bySplitSet.validation")]
                                  + [("squad10 · 20 人房", "squad10.bySeeded20.seeded=20"), ("squad10 · 多于 20 人的房", "squad10.bySeeded20.seeded>20"),
                                     ("squad10 · 少于 20 人的房", "squad10.bySeeded20.seeded<20"),
                                     ("squad10 · 我方号数不到本队的 1/3", "squad10.byOwnFrac.<1/3"),
                                     ("squad10 · 我方号数占本队的 1/3 ~ 2/3", "squad10.byOwnFrac.1/3~2/3"),
                                     ("squad10 · 我方号数占本队的 2/3 以上", "squad10.byOwnFrac.>=2/3"),
                                     ("squad10 · 没有号在 2000 拍前离场的房间", "squad10.noEarlyLeave"),
                                     ("squad10 · 有号在 2000 拍前离场的房间", "squad10.someEarlyLeave"),
                                     ("squad10 · 房间里没有 squad20 的号", "squad10.noPeer"),
                                     ("squad10 · 房间里同时有 squad20 的号", "squad10.withPeer"),
                                     ("squad10 · 散号房间（我方不足 5 个号，不计入上面各行）", "squad10.fragments"),
                                     ("squad10 · 编队房间 + 散号房间", "squad10.withFragments")])
    # 校准表
    cal = J["room"]["calibration"]
    lines = ["| 阵亡那一刻本队份额 | 数据点 | 本队最后获胜 | 胜率 [95% 区间] | 其中当时排第一 | 排第一者获胜 |", "|---|---:|---:|---|---:|---:|"]
    for b in cal["bins"]:
        lines.append(f"| {pct(b['lo'], 0)} ~ {pct(b['hi'], 0)} | {b['n']} | {b['wins']} | {rate_str(b['rate'])} | {b['rank1']} | {b['rank1_wins']} |")
    T["calibration"] = "\n".join(lines)
    lines = ["| 推定规则 | 校准结果（胜方已知的房间里，符合条件的阵亡行 → 本队最后获胜的比例） |", "|---|---|"]
    for k, v in cal["likelyRules"].items():
        lines.append(f"| {k} | {rate_str(v)} |")
    T["calibration_rules"] = "\n".join(lines)
    # squad20 卡片分解
    D = J["squad20"]["card"]
    lines = ["| 我方占的队伍数 d | 局数 | 平均 T | 任一号获胜 | 随机期望 均值(d/T) | 主队获胜 | 随机期望 均值(1/T) |", "|---|---:|---:|---|---:|---|---:|"]
    for k, v in D["byD"].items():
        if v["n"]:
            lines.append(f"| {k} | {v['n']} | {fnum(v['mean_T'], 2)} | {rate_str(v['any'])} | {pct(v['exp_any'])} | {rate_str(v['prim'])} | {pct(v['exp_prim'])} |")
    T["sq20_byD"] = "\n".join(lines)
    lines = ["| 覆盖率 d/T | 局数 | 任一号获胜 | 随机期望 均值(d/T) | 主队获胜 | 随机期望 均值(1/T) |", "|---|---:|---|---:|---|---:|"]
    for k, v in D["byCoverage"].items():
        if v["n"]:
            lines.append(f"| {k} | {v['n']} | {rate_str(v['any'])} | {pct(v['exp_any'])} | {rate_str(v['prim'])} | {pct(v['exp_prim'])} |")
    T["sq20_byCov"] = "\n".join(lines)
    AC = J["squad20"]["cardAccounting"]
    lines = ["| 主房间的情况 | 卡片数 | 卡片 anyBotWon | 卡片 primaryTeamWon | 按占队比例的随机期望 均值(d/T) |", "|---|---:|---|---|---:|"]
    for k, nm in (("winnerKnown", "看到了结局（知道哪个队赢）"), ("winnerUnknown", "没看到结局（我方的号在结束前全部阵亡、离场或日志中断）"),
                  ("noPlay", "我方的号全部掉线或没有结算行，没有任何结局信息"), ("nonTeam", "不是组队局")):
        v = AC[k]
        lines.append(f"| {nm} | {v['n']} | {rate_str(v['any'])} | {rate_str(v['prim'])} | {pct(v['expAnyCoverage'])} |")
    T["sq20_accounting"] = "\n".join(lines)
    SR = J["sharedRooms"]
    lines = ["| 房间（squad10 包 / squad20 包） | 房间真人数 | 队伍数 | 赢的队 | [APEX] 所在队（号数）与结局 | squad20 的号在各队的数量（队号: 号数；另有 n 个队号未知） | 赢的队里 squad20 的号数 | 和 [APEX] 同队的 squad20 号数 |",
             "|---|---:|---:|---:|---|---|---:|---:|"]
    for r in SR["rowsDiscovery"]:
        bt = "，".join(f"{t}: {n}" for t, n in sorted(r["bTeams"].items())) or "—"
        lines.append(f"| {r['pair'][0]} / {r['pair'][1]} | {r['seeded']} | {r['T']} | {r['winner']} | 队 {r['aTeam']}（{r['aBots']}），"
                     f"{ {'WIN': '胜', 'LOSS': '负'}.get(r['aOutcome'], r['aOutcome']) } | {bt}；未知 {r['bUnknownTeam']} | {r['bOnWinner']} | {r['bOnATeam']} |")
    T["shared_rooms"] = "\n".join(lines)
    lines = ["| 队伍数 | 局数 | 平均占队数 d | 任一号获胜 | 随机期望 均值(d/T) | 主队获胜 | 随机期望 均值(1/T) |", "|---|---:|---:|---|---:|---|---:|"]
    for k, v in D["byT"].items():
        if v["n"]:
            lines.append(f"| {k} | {v['n']} | {fnum(v['mean_d'], 2)} | {rate_str(v['any'])} | {pct(v['exp_any'])} | {rate_str(v['prim'])} | {pct(v['exp_prim'])} |")
    T["sq20_byT"] = "\n".join(lines)
    # squad20 队伍级
    for which in ("all", "discovery", "validation"):
        Q = J["squad20"]["team"][which]
        lines = ["| 一个队里我方号数 k | 队伍数 | 结局已定 | 获胜 | 胜率 [95% 区间] | 随机期望 均值(1/T) | 超额 | 精确 p(双侧) |", "|---|---:|---:|---:|---|---:|---:|---:|"]
        for k, v in Q["byK"].items():
            ex = v["excess"]
            lines.append(f"| {k} | {v['n']} | {v['nResolved']} | {v['rate']['k']} | {rate_str(v['rate'])} | {pct(ex['mean_base'])} | "
                         f"{'—' if ex['excess_per_game'] is None else ('+' if ex['excess_per_game'] >= 0 else '') + pct(ex['excess_per_game'])} | {pval(ex['p_two_sided'])} |")
        v = Q["teamUnits"]
        ex = v["excess"]
        lines.append(f"| 合计 | {v['n']} | {v['nResolved']} | {v['rate']['k']} | {rate_str(v['rate'])} | {pct(ex['mean_base'])} | "
                     f"{'—' if ex['excess_per_game'] is None else ('+' if ex['excess_per_game'] >= 0 else '') + pct(ex['excess_per_game'])} | {pval(ex['p_two_sided'])} |")
        T[f"sq20_byK_{which}"] = "\n".join(lines)
        lines = ["| 模型 | 房间数 | 每多一个号的赔率倍数 exp(β) | β [95% 区间] | 似然比 p |", "|---|---:|---:|---|---:|"]
        names = {"kOnly": "只放号数 k", "kPlusA": "号数 k + 「这个队是 A 组所在的队」", "kOnly_roomsWithoutA": "只放 k，去掉有 A 组的房间",
                 "kOnly_unknownFrac<=0.2": "只放 k，只用队号未知的号 ≤ 20% 的房间"}
        for key, nm in names.items():
            m = Q["condLogit"][key]
            if m is None:
                lines.append(f"| {nm} | 0 | — | — | — |")
                continue
            extra = f"；A 队项 β_A = {fnum(m['beta_A'], 2)}（标准误 {fnum(m['se_A'], 2)}）" if "beta_A" in m else ""
            lines.append(f"| {nm} | {m['nRooms']} | {fnum(m['oddsPerBot'], 2)} | {fnum(m['beta_k'], 3)} [{fnum(m['lo'], 3)}, {fnum(m['hi'], 3)}]{extra} | {pval(m['p_lr'])} |")
        T[f"sq20_logit_{which}"] = "\n".join(lines)
    # 过程指标
    P = J["process"]["squadShare"]
    lines = ["| 编队 | 拍 | 房间数（胜/负） | 胜局份额 中位数 [p25, p75] | 负局份额 中位数 [p25, p75] | AUC [95% 区间] | 按队伍数分层的 AUC（层内胜负对数） | 份额×T 的 AUC | 卡片标签下的 AUC |",
             "|---|---:|---|---|---|---|---|---|---|"]
    for co in COHORTS:
        for t in ("630", "1530"):
            b = P[co][t]

            def q3(q):
                return "—" if not q.get("n") else f"{pct(q['median'], 2)} [{pct(q['p25'], 2)}, {pct(q['p75'], 2)}]"

            def a3(a):
                return "—" if a["auc"] is None else f"{fnum(a['auc'], 2)} [{fnum(a['lo'], 2)}, {fnum(a['hi'], 2)}]"
            lines.append(f"| {co} | {t} | {b['n']}（{b['nWin']}/{b['nLoss']}） | {q3(b['share_win'])} | {q3(b['share_loss'])} | {a3(b['auc'])} | "
                         f"{fnum(b['auc_stratT'], 2)}（{b['auc_stratT_pairs']}） | {a3(b['auc_rel'])} | {a3(b['auc_cardLabel'])}（{b['auc_cardLabel']['nPos']}/{b['auc_cardLabel']['nNeg']}） |")
    T["process_share"] = "\n".join(lines)
    lines = ["| 编队 | 拍 | 中位数 | 份额高于中位数：胜率 | 份额不高于中位数：胜率 | Fisher p |", "|---|---:|---:|---|---|---:|"]
    for co in COHORTS:
        for t in ("630", "1530"):
            b = P[co][t]
            lines.append(f"| {co} | {t} | {pct(b['median'], 2)} | {rate_str(b['aboveMedian']['rate'])} | {rate_str(b['belowMedian']['rate'])} | {pval(b['fisher_p'])} |")
    T["process_share_median"] = "\n".join(lines)
    VB = J["process"]["squadShareVb"]
    lines = ["| 拍 | 房间数（胜/负） | 胜局份额 中位数 [p25, p75] | 负局份额 中位数 [p25, p75] | AUC [95% 区间] | 按队伍数分层的 AUC（层内胜负对数） |", "|---:|---|---|---|---|---|"]
    for t in ("630", "1530"):
        b = VB[t]
        qv = lambda q: "—" if not q.get("n") else f"{pct(q['median'], 2)} [{pct(q['p25'], 2)}, {pct(q['p75'], 2)}]"
        av = b["auc"]
        lines.append(f"| {t} | {b['n']}（{b['nWin']}/{b['nLoss']}） | {qv(b['share_win'])} | {qv(b['share_loss'])} | "
                     f"{'—' if av['auc'] is None else fnum(av['auc'], 2) + ' [' + fnum(av['lo'], 2) + ', ' + fnum(av['hi'], 2) + ']'} | "
                     f"{fnum(b['auc_stratT'], 2)}（{b['auc_stratT_pairs']}） |")
    T["process_share_vb"] = "\n".join(lines)
    TL = J["process"]["squad20TeamLevel"]
    lines = ["| 拍 | 队伍数（胜/负） | 每号平均份额：胜队 中位数 [p25, p75] | 负队 中位数 [p25, p75] | 每号平均份额的 AUC [95% 区间] | 按队伍数分层的 AUC（层内胜负对数） | 合计份额的 AUC |",
             "|---:|---|---|---|---|---|---|"]
    for t in ("630", "1530"):
        b = TL[t]

        def q3b(q):
            return "—" if not q.get("n") else f"{pct(q['median'], 3)} [{pct(q['p25'], 3)}, {pct(q['p75'], 3)}]"

        def a3b(a):
            return "—" if a["auc"] is None else f"{fnum(a['auc'], 2)} [{fnum(a['lo'], 2)}, {fnum(a['hi'], 2)}]"
        lines.append(f"| {t} | {b['n']}（{b['nWin']}/{b['nLoss']}） | {q3b(b['mean_win'])} | {q3b(b['mean_loss'])} | {a3b(b['auc_mean'])} | "
                     f"{fnum(b['auc_mean_stratT'], 2)}（{b['auc_mean_stratT_pairs']}） | {a3b(b['auc_sum'])} |")
    T["process_share_sq20team"] = "\n".join(lines)
    AV = J["process"]["anomalyVsOutcome"]
    lines = ["| 编队 | 指标 | 胜局 中位数 [p25, p75]（局数） | 负局 中位数 [p25, p75]（局数） | AUC [95% 区间]（>0.5 表示胜局的值更大） |", "|---|---|---|---|---|"]
    for co in COHORTS:
        for key, nm, wk, lk, isp in (("rejRate", "疑似拒单率", "rejRate_win", "rejRate_loss", True),
                                     ("boxedPerBot", "内陆高密度快照数 / 号", "boxed_win", "boxed_loss", False),
                                     ("boxedPerLateSnap", "内陆高密度快照 占 t≥1500 快照的比例", "boxedLate_win", "boxedLate_loss", True),
                                     ("lateSnapPerBot", "t≥1500 的快照数 / 号（号活得多久）", "lateSnap_win", "lateSnap_loss", False)):
            a = AV[co]

            def qq(q):
                if not q.get("n"):
                    return "—"
                if isp:
                    return f"{pct(q['median'])} [{pct(q['p25'])}, {pct(q['p75'])}]（{q['n']}）"
                return f"{q['median']:.1f} [{q['p25']:.1f}, {q['p75']:.1f}]（{q['n']}）"
            au = a[key]
            lines.append(f"| {co} | {nm} | {qq(a[wk])} | {qq(a[lk])} | "
                         f"{'—' if au['auc'] is None else fnum(au['auc'], 2) + ' [' + fnum(au['lo'], 2) + ', ' + fnum(au['hi'], 2) + ']'} |")
    T["process_anom_outcome"] = "\n".join(lines)
    AN = J["process"]["anomalies"]
    BX = J["process"]["boxedRates"]
    lines = ["| 编队 | 发现集局数 | 每局转兵次数 中位数 [p25, p75]（最大） | 每局疑似拒单 中位数 [p25, p75]（最大） | 每局拒单率 中位数 [p25, p75] | 合并拒单率（Σ拒单/Σ转兵） | 没有转兵的局 |",
             "|---|---:|---|---|---|---|---:|"]
    GROUPS = list(COHORTS) + [f"squad10·{v}" for v in VERSIONS]
    for co in GROUPS:
        a = AN[co]

        def q(qq, d=0, p=False):
            if not qq.get("n"):
                return "—"
            if p:
                return f"{pct(qq['median'])} [{pct(qq['p25'])}, {pct(qq['p75'])}]"
            return f"{qq['median']:.{d}f} [{qq['p25']:.{d}f}, {qq['p75']:.{d}f}]（{qq['max']:.0f}）"
        lines.append(f"| {co} | {a['nBundles']} | {q(a['transfers'])} | {q(a['rejected'])} | {q(a['rejRatePerBundle'], p=True)} | {rate_str(a['rejRatePooled'])} | {a['nBundlesNoTransfers']} |")
    T["process_rej"] = "\n".join(lines)
    lines = ["| 编队 | 发现集局数 | 每局内陆高密度快照数 中位数 [p25, p75]（最大） | 一次都没有的局 | 合计快照数 | 占 t≥1500 全部快照的比例 |", "|---|---:|---|---:|---:|---|"]
    for co in GROUPS:
        a = AN[co]
        qq = a["boxed"]
        lines.append(f"| {co} | {a['nBundles']} | {qq['median']:.0f} [{qq['p25']:.0f}, {qq['p75']:.0f}]（{qq['max']:.0f}） | {a['nBundlesBoxed0']} | {a['boxedTotal']} | {rate_str(BX[co]['rate'])} |")
    T["process_boxed"] = "\n".join(lines)
    # 数据质量
    DQ = J["quality"]["byCohort"]
    lines = ["| 编队 | 包数 | 还原出的号 | 房间数 | 多房间的包 | 改过名的号 | 结算 died / end / left / 没有结算行 | 队号来源：结算行 / 同标签 / 捐款关系 / 未知 | 号码独立校验（对 / 错） |",
             "|---|---:|---:|---:|---:|---:|---|---|---|"]
    for co in COHORTS:
        d = DQ[co]
        ev, th = d["events"], d["teamHow"]
        lines.append(f"| {co} | {d['nBundles']} | {d['nBots']} | {d['nRooms']} | {d['nMultiRoomBundles']} | {d['nRenamed']} | "
                     f"{ev.get('died', 0)} / {ev.get('end', 0)} / {ev.get('left', 0)} / {ev.get('none', 0)} | "
                     f"{th.get('result', 0)} / {th.get('clan', 0)} / {th.get('donate', 0)} / {th.get('unknown', 0)} | "
                     f"{d['idIndependentOk']} / {d['idIndependentBad']} |")
    T["quality_identity"] = "\n".join(lines)
    lines = ["| 编队 | 快照行数 | 缺失的快照 | 缺失率 | 有跳拍（skip>0）的号 | 终局 skip 中位数 [p25, p75]（最大） | 单拍最长耗时 maxMs 中位数 [p75]（最大） |", "|---|---:|---:|---|---|---|---|"]
    for co in COHORTS:
        d = DQ[co]
        sk, mm = d["skipFinal"], d["maxMsFinal"]
        lines.append(f"| {co} | {d['nSnap']} | {d['nSnapMissing']} | {rate_str(d['missRate'])} | {rate_str(d['botsWithSkip'])} | "
                     f"{sk['median']:.0f} [{sk['p25']:.0f}, {sk['p75']:.0f}]（{sk['max']:.0f}） | {mm['median']:.1f} [{mm['p75']:.1f}]（{mm['max']:.1f}） |")
    T["quality_lag"] = "\n".join(lines)
    # 对账表（只列发现集；只列有实质差异的局，「结局为推定」「主队不确定」另以编号清单给出）
    subst = {"非组队局", "全员掉线无结局", "多房间", "队伍数不同", "主队胜负不同", "结局未观察到", "同标签分在两队"}
    rows = [r for r in J["reconcile"]["rows"] if r["split"] == "discovery" and subst & set(r["flags"])]
    out_cn = {"WIN": "胜", "LOSS": "负", "WIN_LIKELY": "推定胜", "LOSS_LIKELY": "推定负", "UNKNOWN": "未知",
              "NO_PLAY": "全员掉线", "NON_TEAM": "非组队"}
    thow_cn = {"totals": "结算行", "rule": "引擎规则", "rule>totals": "引擎规则；结算行里见到的队更少",
               "totals>rule": "结算行；比引擎规则多", "unknown": "未知"}

    def teams_str(teams, unk):
        parts = [f"队{t}×{n}" for t, n in sorted(teams.items(), key=lambda kv: int(kv[0]))]
        if unk:
            parts.append(f"队号未知×{unk}")
        return "、".join(parts) or "—"
    lines = ["| 局 | 卡片：队伍数 / 占队数 / 主队胜 / 任一号胜 | 房间数 | 主房间：我方号数；队伍数（来源）；我方各队号数；结局 | 其余房间 | 差异 |", "|---|---|---:|---|---|---|"]
    for r in rows:
        others = "；".join(f"{o['nBots']} 个号在 {o['seeded']} 人房，{'队伍数 ' + str(o['T']) + '，' if o['T'] else ''}{out_cn.get(o['outcome'], o['outcome'])}"
                          for o in r["otherRooms"]) or "—"
        tsrc = thow_cn.get(r["tHow"], r["tHow"])
        lines.append(f"| {r['matchId']} | {r['cardT']} / {r['cardD']} / {'是' if r['cardPrim'] else '否'} / {'是' if r['cardAny'] else '否'} | {r['nRooms']} | "
                     f"{r['mainBots']} 个号；{r['roomT'] if r['roomT'] else '—'}（{tsrc}）；{teams_str(r['teams'], r['nTeamUnknown'])}；"
                     f"{out_cn.get(r['roomOutcome'], r['roomOutcome'])} | {others} | {'、'.join(r['flags'])} |")
    T["reconcile_discovery"] = "\n".join(lines)
    fc = J["reconcile"]["flagCounts"]
    allflags = ["无差异", "非组队局", "全员掉线无结局", "多房间", "队伍数不同", "主队胜负不同", "结局未观察到", "结局为推定", "同标签分在两队", "主队不确定"]
    lines = ["| 差异类型 | squad8 | squad10 | squad20 | 其中发现集 | 其中验证集 |", "|---|---:|---:|---:|---:|---:|"]
    fs = J["reconcile"]["flagCountsBySplit"]
    for f in allflags:
        lines.append(f"| {f} | {fc['squad8'].get(f, 0)} | {fc['squad10'].get(f, 0)} | {fc['squad20'].get(f, 0)} | {fs['discovery'].get(f, 0)} | {fs['validation'].get(f, 0)} |")
    T["reconcile_counts"] = "\n".join(lines)
    return T


def render(template: str, J: dict, T: dict) -> str:
    def sub_table(m):
        return T[m.group(1)]

    def sub_val(m):
        path, _, fmt = m.group(1).partition("|")
        v = get_path(J, path.strip())
        fmt = fmt.strip()
        if fmt == "pct":
            return pct(v)
        if fmt == "pct0":
            return pct(v, 0)
        if fmt == "pct2":
            return pct(v, 2)
        if fmt == "rate":
            return rate_str(v)
        if fmt == "p":
            return pval(v)
        if fmt.startswith("f"):
            return fnum(v, int(fmt[1:] or 3))
        if fmt == "list":
            return "、".join(str(x) for x in v)
        if fmt == "spct":
            return ("+" if v >= 0 else "") + pct(v)
        if fmt == "pp":
            return f"{100 * v:.1f} 个百分点"
        if fmt == "spp":
            return ("+" if v >= 0 else "−") + f"{abs(100 * v):.1f} 个百分点"
        return str(v)
    out = re.sub(r"\{\{TABLE:([A-Za-z0-9_]+)\}\}", sub_table, template)
    out = re.sub(r"\{\{([^{}]+)\}\}", sub_val, out)
    return out


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------

def strip_private(obj):
    if isinstance(obj, dict):
        return {k: strip_private(v) for k, v in obj.items() if not k.startswith("_")}
    if isinstance(obj, list):
        return [strip_private(x) for x in obj]
    return obj


def main(argv: list[str]) -> int:
    cards = load_cards("all")
    VER.update({c["matchId"]: strategy_version(c) for c in cards})
    allb = R.analyze_all("all")
    units = room_units(allb)
    J = {"meta": {"nCards": len(cards), "nDiscovery": sum(1 for c in cards if c["split"] == "discovery"),
                  "nValidation": sum(1 for c in cards if c["split"] == "validation"),
                  "mainRoomMinBots": MAIN_ROOM_MIN_BOTS,
                  "scripts": ["scripts/baseline_full.py", "scripts/rooms.py", "scripts/c136lib.py", "scripts/stats.py"]}}
    J["card"] = {"all160": card_tables(cards),
                 "discovery": card_tables([c for c in cards if c["split"] == "discovery"]),
                 "validation": card_tables([c for c in cards if c["split"] == "validation"])}
    calib = calibration(allb)
    J["room"] = {"tagged": tagged_tables(units), "calibration": calib}
    J["squad20"] = {"card": squad20_card_decomp(cards),
                    "cardDiscovery": squad20_card_decomp([c for c in cards if c["split"] == "discovery"]),
                    "team": {w: squad20_team_level(allb, w) for w in ("all", "discovery", "validation")}}
    J["squad20"]["cardAccounting"] = squad20_card_accounting(cards, allb)
    J["sharedRooms"] = shared_rooms(allb, R.analyze_all.phys)
    rec = recount_anomalies(cards)
    J["process"] = process_metrics(units, allb, cards, rec["_per"])
    J["process"]["recount"] = {"nCards": rec["nCards"], "nMismatch": rec["nMismatch"],
                               "mismatchesDiscovery": [m for m in rec["mismatches"] if m["split"] == "discovery"],
                               "nMismatchValidation": sum(1 for m in rec["mismatches"] if m["split"] == "validation")}
    J["process"]["boxedRates"] = boxed_rates(cards, rec["_per"])
    J["quality"] = data_quality(allb, units)
    J["quality"]["startGaps"] = start_gap_table(cards)
    J["reconcile"] = reconcile(cards, allb)
    # 派生的几个单值，方便模板引用
    cnt = Counter()
    for u in units:
        if u["isTeamGame"] is False:
            cnt[("nonTeam", u["cohort"])] += 1
    J["derived"] = {
        "nonTeamBundles": sorted({u["matchId"] for u in units if u["isTeamGame"] is False and u["split"] == "discovery"}),
        "nNonTeamBundlesValidation": len({u["matchId"] for u in units if u["isTeamGame"] is False and u["split"] == "validation"}),
        "noPlayDiscovery": sorted({u["matchId"] for u in units if u["isTeamGame"] is not False and u["outcome"] == "NO_PLAY"
                                   and u["isMainRoomOfBundle"] and u["split"] == "discovery"}),
        "nNoPlayValidation": len({u["matchId"] for u in units if u["isTeamGame"] is not False and u["outcome"] == "NO_PLAY"
                                  and u["isMainRoomOfBundle"] and u["split"] == "validation"}),
        "multiRoomDiscovery": sorted({r["matchId"] for r in J["reconcile"]["rows"] if "多房间" in r["flags"] and r["split"] == "discovery"}),
        "nMultiRoomValidation": len({r["matchId"] for r in J["reconcile"]["rows"] if "多房间" in r["flags"] and r["split"] == "validation"}),
        "clanConflictDiscovery": sorted({u["matchId"] for u in units if u["clanTeamConflict"] and u["split"] == "discovery"}),
        "usedPeerRowsDiscovery": sorted({u["matchId"] for u in units if u["usedPeerRows"] and u["split"] == "discovery"}),
        "outcomeFlipDiscovery": sorted({r["matchId"] for r in J["reconcile"]["rows"] if "主队胜负不同" in r["flags"] and r["split"] == "discovery"}),
        "likelyOutcomeDiscovery": sorted({r["matchId"] for r in J["reconcile"]["rows"] if "结局为推定" in r["flags"] and r["split"] == "discovery"}),
        "outcomeUnknownDiscovery": sorted({r["matchId"] for r in J["reconcile"]["rows"] if "结局未观察到" in r["flags"] and r["split"] == "discovery"}),
        "primaryUncertainDiscovery": sorted({r["matchId"] for r in J["reconcile"]["rows"] if "主队不确定" in r["flags"] and r["split"] == "discovery"}),
        "tDiffDiscovery": sorted({r["matchId"] for r in J["reconcile"]["rows"] if "队伍数不同" in r["flags"] and r["split"] == "discovery"}),
        "nTDiffValidation": len({r["matchId"] for r in J["reconcile"]["rows"] if "队伍数不同" in r["flags"] and r["split"] == "validation"}),
        "resetsDiscovery": [f"{x['matchId']}（第 {'、'.join(str(t) for t in x['ticks'])} 拍）" for x in J["quality"]["resets"] if x["split"] == "discovery"],
        "nOutcomeFlipValidation": len({r["matchId"] for r in J["reconcile"]["rows"] if "主队胜负不同" in r["flags"] and r["split"] == "validation"}),
    }
    disc_units = [u for u in units if u["split"] == "discovery"]
    by_unit = {(u["matchId"], u["roomIdx"]): u for u in units}
    np_main = [u for u in disc_units if u["isTeamGame"] is not False and u["outcome"] == "NO_PLAY" and u["isMainRoomOfBundle"]]
    J["derived"]["noPlayDetailDiscovery"] = [
        f"{u['matchId']}（{'最后一个号在第 ' + str(u['lastTick']) + ' 拍离场' if u['lastTick'] else '所有号都没有结算行'}）" for u in np_main]
    sg = J["quality"]["startGaps"]
    J["derived"]["nStartGapLt05"] = sg["<0.5"]
    J["derived"]["nStartGapGe16"] = sg["1.6-3.0"] + sg["3.0-12"] + sg[">=12"]
    J["derived"]["nStartGapBetween"] = sg["0.5-1.0"] + sg["1.0-1.6"]
    ll = J["room"]["calibration"]["likelyRules"]["LOSS_LIKELY(rank>1,share<0.2)"]
    J["derived"]["lossLikelyErr"] = ll
    J["derived"]["expWinsAmongLossLikelySq10"] = J["room"]["tagged"]["squad10"]["all"]["counts"]["LOSS_LIKELY"] * ll["rate"]
    J["derived"]["winLikelyAcc"] = J["room"]["calibration"]["likelyRules"]["WIN_LIKELY(rank1,share>=0.5)"]
    cc = [u for u in disc_units if u["clanTeamConflict"]]
    J["derived"]["clanConflictDetail"] = [
        f"{u['matchId']}（{u['seeded']} 人房，" + "、".join(f"队 {t} 有 {n} 个号" for t, n in sorted(u["teams"].items())) + "）" for u in cc]
    s20 = [u for u in units if u["cohort"] == "squad10" and u["seeded"] == 20 and u["kind"] == "main"
           and u["isTeamGame"] is not False and u["outcome"] != "NO_PLAY"]
    J["derived"]["seeded20Sq10Main"] = {"n": len(s20), "minBots": min(u["nBots"] for u in s20), "maxBots": max(u["nBots"] for u in s20),
                                        "nT2": sum(1 for u in s20 if u["T"] == 2)}
    phys = R.analyze_all.phys
    co_of = {a["matchId"]: a["cohort"] for a in allb}
    J["quality"]["seeded20"]["nSharedAB"] = sum(
        1 for p in phys if p["seeded"] == 20 and len({co_of[m["matchId"]] for m in p["members"]}) > 1)
    a002 = by_unit[("A002", 0)]
    J["derived"]["a002"] = {"nLeftEarly": a002["nLeftEarly"], "nBots": a002["nBots"], "outcome": a002["outcome"]}
    a057 = by_unit[("A057", 0)]
    J["derived"]["a057"] = {"ownOutcome": a057["ownOutcome"], "outcome": a057["outcome"], "nEndRowsOwn": a057["events"].get("end", 0),
                            "team": a057["primaryTeam"], "winner": a057["winner"]}
    t10 = J["room"]["tagged"]["squad10"]
    n_np10 = sum(1 for u in units if u["cohort"] == "squad10" and u["isTeamGame"] is not False and u["outcome"] == "NO_PLAY"
                 and u["kind"] == "main")
    J["derived"]["sq10NoPlayAsLoss"] = rate(t10["all"]["main"]["rate"]["k"], t10["all"]["main"]["rate"]["n"] + n_np10)
    J["derived"]["nSq10NoPlayMain"] = n_np10
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(REP, exist_ok=True)
    # 内部文件：含验证集逐局
    internal = {"_notice": "含验证集逐局明细：仅 R10 与 c136 使用，R01~R09 不得读取。",
                "roomUnits": units, "reconcileRows": J["reconcile"]["rows"],
                "squad20TeamUnits": J["squad20"]["team"]["all"]["_teamUnits"],
                "sharedRoomsAll": J["sharedRooms"]["_rowsAll"]}
    pub = strip_private(J)
    # 公开文件里：对账明细只留发现集；房间单位只留发现集
    pub["reconcile"]["rows"] = [r for r in pub["reconcile"]["rows"] if r["split"] == "discovery"]
    # 哪些发现集的局和验证集的包是同一个物理房间，属于验证集细节：公开文件只给个数，名单放内部文件
    pub["roomUnitsDiscovery"] = [{k: v for k, v in u.items() if k not in ("peerSplits", "usedPeerRows", "hasPeer", "peerCohorts", "physRoom")}
                                 for u in units if u["split"] == "discovery"]
    val_linked = set(pub["quality"]["physical"].pop("discoveryBundlesSharingWithValidation"))
    internal["discoveryBundlesSharingWithValidation"] = sorted(val_linked)
    pub["derived"]["nUsedPeerRowsDiscovery"] = len(pub["derived"]["usedPeerRowsDiscovery"])
    pub["derived"]["usedPeerRowsDiscovery"] = [m for m in pub["derived"]["usedPeerRowsDiscovery"] if m not in val_linked]
    with open(os.path.join(OUT, "baseline-full-internal.json"), "w", encoding="utf-8") as f:
        json.dump(internal, f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT, "baseline-full.json"), "w", encoding="utf-8") as f:
        json.dump(pub, f, ensure_ascii=False, indent=1)
    print("wrote", os.path.join(OUT, "baseline-full.json"))
    if "--no-report" not in argv and os.path.exists(TEMPLATE):
        T = build_tables(pub)
        with open(TEMPLATE, encoding="utf-8") as f:
            tpl = f.read()
        with open(os.path.join(REP, "BASELINE-FULL.md"), "w", encoding="utf-8") as f:
            f.write(render(tpl, pub, T))
        print("wrote", os.path.join(REP, "BASELINE-FULL.md"))
    if "--tables" in argv:
        T = build_tables(pub)
        for k, v in T.items():
            print(f"\n### {k}\n{v}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
