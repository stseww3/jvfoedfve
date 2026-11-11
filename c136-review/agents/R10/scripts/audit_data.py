#!/usr/bin/env python3
"""audit_data.py — M2/M4 共用的数据装配层：把对局包、房间重建结果、录像拼成「号 × 快照 × 事件 × 真实捐款账」。

只读 /agent/repos/c136-data；房间与队伍来自本目录 rooms.py 的产物（out/rooms/）。

对外：
  load_games(which)      which = 'discovery' | 'validation'；返回 Game 列表（见下）
  quota_cap(t)           引擎配额上限 aOY 在第 t 拍的值
  donation_cost(...)     一笔到账 v 的捐款消耗的配额点
  interest_rate(...)     每 10 拍利息率（万分之一），与模拟器 interestRate 同式

Game（dict）：
  mid, cohort, ver, split, card, land(主房间地图陆地格数)
  rooms: [room]            room = rooms.py 的房间 dict，另加 "botRecs"
  bots:  [bot]             bot = {mid, cohort, ver, roomIdx, names, me, team, event, tick, outcome, T, land,
                                  snaps[快照行], inReplay, replayOk(该号在录像覆盖内)}
  events: [ev]             ev = events.csv 的一行，另加 "botRec"（发起号）、"recRec"（对象号，可能 None）
  replay: 录像（replay.load 的返回）或 None；replayRoom: 录像对应的房间号或 None；replayTicks
  ledger: 真实捐款账（只有带录像的包有），见 build_ledger
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import c136lib as L  # noqa: E402
import replay as RP  # noqa: E402
import baseline_full as BF  # noqa: E402

OUT = os.path.normpath(os.path.join(HERE, "..", "out"))

MAXLAG = 400          # 下单到执行最多允许的拍数（统筹工具 donation_ledger.mjs 用的是同一个上限）
COVER_MARGIN = 30     # 录像覆盖判定：下单拍 ≤ 录像总拍数 − 30 才算在覆盖内
LAG_DEFAULT = 12      # 没有可用样本时的典型延迟


def norm_name(n: str) -> str:
    return re.sub(r"\[[^\]]*\]", "", n or "").strip().lower()


# ----------------------------------------------------------------------------
# 引擎公式（原文位置见 reports/HYPOTHESIS-AUDIT.md 附录）
# ----------------------------------------------------------------------------

def iv(a: int, b: int) -> int:
    """引擎的整数除法 bO.g0(a,b) = floor((a+0.5)/b)；对非负整数等于 a // b。"""
    return a // b


def quota_cap(t: int) -> int:
    """配额上限 aOY：开局 15；每逢 tick%100==99 增加 4（t<1071）/ 6（<2142）/ 8（<3213）/ 10。
    返回第 t 拍处理命令时的上限（第 t 拍的命令在当拍 ao.ee 之前处理，所以只计入 ≤ t−1 的增量）。"""
    cap = 15
    k = 99
    while k <= t - 1:
        cap += 4 if k < 1071 else 6 if k < 2142 else 8 if k < 3213 else 10
        k += 100
    return cap


def quota_denominator(t: int, land: int, rec_terr: int):
    """返回 (底数, 分母)。t>=3213 时分母是收款方软上限 min(100×领土, 1e9)。"""
    if t >= 3213:
        return 4, max(1, min(100 * rec_terr, 10 ** 9))
    uv = 1 + iv(land, 300)
    if t < 357:
        return 2, uv
    if t < 714:
        return 2, 4 * uv
    if t < 1071:
        return 2, 10 * uv
    if t < 2142:
        return 2, 30 * uv
    return 2, 100 * uv


def donation_cost(t: int, land: int, rec_terr: int, v: int) -> int:
    base, den = quota_denominator(t, land, rec_terr)
    return base + iv(100 * v, den)


def quota_free(t: int) -> bool:
    return t >= 4284


def donate_amounts(bal: int, pct: int, rec_terr, rec_bal):
    """返回 (到账 v, 手续费)。对方余额/领土未知时不做 150×领土 的截断。"""
    fee = iv(64 * bal, 1024)
    v = min(iv(bal * (pct + 1), 1024), bal - fee)
    if rec_terr is not None and rec_bal is not None:
        v = min(v, 150 * rec_terr - rec_bal, 1_500_000_000 - rec_bal)
    return max(v, 0), fee


def _isqrt_engine(h: int, cs: int = 9) -> int:
    if h < 1:
        return 0
    a = iv(h + 1, 2)
    for _ in range(cs):
        a = iv(a + iv(h, a), 2)
    return a


_INTEREST_TABLE = [100 + _isqrt_engine(iv(25600 * i, 508)) for i in range(512)]


def interest_rate(t: int, terr: int, land: int, bal: int):
    """返回 (实际利息率, 不受软上限影响时的利息率)，单位万分之一 / 每 10 拍。"""
    n1 = _INTEREST_TABLE[min(511, iv(511 * terr, max(1, land)))]
    if t < 1920:
        n1 = max(iv(100 * (13440 - 6 * t), 1920), n1)
    base = min(max(n1, 0), 700)
    cap = min(100 * terr, 10 ** 9)
    if cap > 0 and bal > cap:
        n1 -= iv(2 * n1 * (bal - cap), cap)
    return min(max(n1, 0), 700), base


# ----------------------------------------------------------------------------
# 装配
# ----------------------------------------------------------------------------

def _rooms_file(which: str) -> str:
    return os.path.join(OUT, "rooms", "rooms-discovery.json" if which == "discovery" else "rooms-validation-internal.json")


def version_of(card: dict) -> str:
    v = BF.strategy_version(card)
    return v


def load_games(which: str = "discovery") -> list[dict]:
    cards = {c["matchId"]: c for c in L.load_cards(which)}
    with open(_rooms_file(which), encoding="utf-8") as f:
        rb = {b["matchId"]: b for b in json.load(f)}
    games = []
    for mid in sorted(cards):
        card = cards[mid]
        b = rb[mid]
        traj = L.traj_by_bot(card)
        g = {"mid": mid, "cohort": card["cohort"], "ver": version_of(card), "split": card["split"], "card": card,
             "rooms": b["rooms"], "bots": [], "mainRoom": b["mainRoom"]}
        name2bot = {}
        for room in b["rooms"]:
            room["botRecs"] = []
            for bot in room["bots"]:
                rows = []
                for nm in bot["names"]:
                    rows.extend(traj.get(nm, []))
                rows.sort(key=lambda x: x["line"])
                rec = {"mid": mid, "cohort": g["cohort"], "ver": g["ver"], "roomIdx": room["roomIdx"],
                       "names": bot["names"], "name": bot["names"][0], "me": bot["me"], "team": bot["team"],
                       "event": bot["event"], "tick": bot["tick"], "result": bot["result"],
                       "outcome": room["outcome"], "T": room.get("tBest"), "land": room["land"],
                       "seeded": room["seeded"], "nBotsRoom": room["nBots"], "tagged": room["tagged"],
                       "snaps": rows, "inReplay": False, "peak": bot.get("peak"),
                       "lastT": bot.get("lastT"), "firstT": bot.get("firstT")}
                g["bots"].append(rec)
                room["botRecs"].append(rec)
                for nm in bot["names"]:
                    name2bot[nm] = rec
        g["name2bot"] = name2bot
        room_by_idx = {room["roomIdx"]: room for room in b["rooms"]}
        g["roomByIdx"] = room_by_idx
        # 录像：看每个房间有几个号能在录像名单里按座位号对上名字，对上最多的房间就是录像对应的房间
        r = RP.load(mid)
        g["replay"] = r
        g["replayRoom"] = None
        g["replayTicks"] = r["totalTicks"] if r else None
        if r:
            best = (0, None)
            for room in b["rooms"]:
                ok = 0
                for rec in room["botRecs"]:
                    me = rec["me"]
                    if me is not None and me < len(r["names"]) and norm_name(r["names"][me]) in [norm_name(x) for x in rec["names"]]:
                        ok += 1
                if ok > best[0]:
                    best = (ok, room["roomIdx"])
            g["replayRoom"] = best[1]
            for room in b["rooms"]:
                if room["roomIdx"] != best[1]:
                    continue
                for rec in room["botRecs"]:
                    me = rec["me"]
                    if me is not None and me < len(r["names"]) and norm_name(r["names"][me]) in [norm_name(x) for x in rec["names"]]:
                        rec["inReplay"] = True
        # 事件
        evs = []
        for e in L.load_events(card):
            rec = name2bot.get(e["bot"])
            e["botRec"] = rec
            e["recRec"] = None
            if rec is not None and e.get("target") is not None:
                for o in room_by_idx[rec["roomIdx"]]["botRecs"]:
                    if o["me"] == e["target"]:
                        e["recRec"] = o
                        break
            evs.append(e)
        g["events"] = evs
        g["land"] = next((rm["land"] for rm in b["rooms"] if rm["roomIdx"] == b["mainRoom"]), None)
        games.append(g)
    return games


def snap_at(rec: dict, t: int, tol: int = 90):
    """离 t 最近的一张快照（差距超过 tol 返回 None）。"""
    best = None
    for s in rec["snaps"]:
        if best is None or abs(s["t"] - t) < abs(best["t"] - t):
            best = s
    if best is None or abs(best["t"] - t) > tol:
        return None
    return best


def snap_before(rec: dict, t: int):
    """t 拍之前（含）最近的一张快照。"""
    best = None
    for s in rec["snaps"]:
        if s["t"] <= t and (best is None or s["t"] > best["t"]):
            best = s
    return best


def interp_state(rec: dict, t: int):
    """按前后两张快照线性插值 t 拍时的 (领土, 余额)；只有一侧时取那一侧；都没有返回 (None, None)。"""
    lo = hi = None
    for s in rec["snaps"]:
        if s["t"] <= t and (lo is None or s["t"] > lo["t"]):
            lo = s
        if s["t"] >= t and (hi is None or s["t"] < hi["t"]):
            hi = s
    if lo is None and hi is None:
        return None, None
    if lo is None or (hi is not None and hi["t"] - t > 180 and t - lo["t"] > 180):
        s = hi if lo is None else None
        if s is None:
            return None, None
        return s["terr"], s["bal"]
    if hi is None or hi["t"] == lo["t"]:
        if t - lo["t"] > 180:
            return None, None
        return lo["terr"], lo["bal"]
    w = (t - lo["t"]) / (hi["t"] - lo["t"])
    return int(round(lo["terr"] + w * (hi["terr"] - lo["terr"]))), int(round(lo["bal"] + w * (hi["bal"] - lo["bal"])))


# ----------------------------------------------------------------------------
# 真实捐款账
# ----------------------------------------------------------------------------

def build_ledger(g: dict) -> dict | None:
    """
    把日志里的捐款/调度下单（HL-DISPATCH / HL-DONATE）和录像里真实成交的捐款命令（id=2）一一对上。

    口径：
      - 只算「在录像里」的号（座位号上的名字对得上）且下单拍 ≤ 录像总拍数 − COVER_MARGIN 的下单；
      - 一条成交命令匹配同一个号、同一 pct、同一对象、下单拍 ≤ 成交拍 ≤ 下单拍 + MAXLAG 的下单；
        候选不止一条时，取「延迟最接近本局典型延迟」的那条（典型延迟 = 本局只有唯一候选的成交的延迟中位数）；
      - 每条下单至多匹配一条成交。没匹配上的下单 = 被引擎拒绝（没有进录像）。
    返回 {"attempts": [...], "executed": n, "unmatchedExec": n, "lagMedian": x, "othersDonations": [...]}。
    attempt = 事件行 + {"exec": bool, "execTick": int|None, "lag": int|None, "covered": True}
    """
    r = g["replay"]
    if not r:
        return None
    T = g["replayTicks"]
    by_me = defaultdict(list)
    atts = []
    for e in g["events"]:
        if e["type"] not in ("DISPATCH", "DONATE"):
            continue
        rec = e["botRec"]
        if rec is None or not rec["inReplay"]:
            continue
        if e["t"] > T - COVER_MARGIN:
            continue
        a = dict(e)
        a["exec"] = False
        a["execTick"] = None
        a["lag"] = None
        atts.append(a)
        by_me[rec["me"]].append(a)
    our_me = {rec["me"] for rec in g["bots"] if rec["inReplay"]}
    execs = defaultdict(list)
    others = []
    for (tick, cid, player, a, c) in r["cmds"]:
        if cid != 2:
            continue
        if player in our_me:
            execs[player].append((tick, a, c))
        else:
            others.append((tick, player, a, c))
    # 第一遍：唯一候选的延迟
    uniq = []
    for me, lst in execs.items():
        A = by_me.get(me, [])
        for (tick, pct, to) in lst:
            c = [x for x in A if x["pct"] == pct and x["target"] == to and 0 <= tick - x["t"] <= 60]
            if len(c) == 1:
                uniq.append(tick - c[0]["t"])
    uniq.sort()
    lag0 = uniq[len(uniq) // 2] if uniq else LAG_DEFAULT
    unmatched = 0
    n_exec = 0
    for me, lst in execs.items():
        A = by_me.get(me, [])
        for (tick, pct, to) in sorted(lst):
            n_exec += 1
            c = [x for x in A if not x["exec"] and x["pct"] == pct and x["target"] == to and 0 <= tick - x["t"] <= MAXLAG]
            if not c:
                unmatched += 1
                continue
            best = min(c, key=lambda x: (abs((tick - x["t"]) - lag0), x["t"]))
            best["exec"] = True
            best["execTick"] = tick
            best["lag"] = tick - best["t"]
    return {"attempts": atts, "executed": n_exec, "unmatchedExec": unmatched, "lagMedian": lag0,
            "othersDonations": others, "nExecAll": n_exec + len(others)}


# ----------------------------------------------------------------------------
# 真引擎探针（engine_probe.cjs）的作业单与结果
# ----------------------------------------------------------------------------

def engine_dir(which: str = "discovery") -> str:
    return os.path.join(OUT, "engine", which)


def write_engine_jobs(which: str = "discovery", games=None) -> str:
    """给 engine_probe.cjs 写作业单：每个带录像的包一条（我方在录像里的座位号 + 录像覆盖内的全部捐款下单）。"""
    games = games if games is not None else load_games(which)
    jobs = []
    for g in games:
        if not g["replay"]:
            continue
        ours = sorted(rec["me"] for rec in g["bots"] if rec["inReplay"])
        if not ours:
            continue
        led = build_ledger(g)
        atts = [[i, a["t"], a["botRec"]["me"], a["pct"], a["target"]] for i, a in enumerate(led["attempts"])
                if a["pct"] is not None and a["target"] is not None]
        jobs.append({"mid": g["mid"], "replay": RP.replay_path(g["mid"]), "ours": ours, "attempts": atts})
    d = os.path.join(OUT, "engine")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, f"jobs-{which}.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(jobs, f)
    return p


def load_engine(mid: str, which: str = "discovery"):
    """读探针结果；没有（没录像或还没跑）返回 None。"""
    p = os.path.join(engine_dir(which), mid + ".json")
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        e = json.load(f)
    if e.get("error"):
        return None
    return e


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "discovery"
    p = write_engine_jobs(which)
    with open(p, encoding="utf-8") as f:
        n = len(json.load(f))
    print(f"jobs: {n} -> {os.path.relpath(p, os.path.join(HERE, '..'))}")
