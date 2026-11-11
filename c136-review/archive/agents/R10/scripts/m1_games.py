#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
m1_games.py — 把数据 A 的单号结算记录归并成「房间」，并和小队日志对上号。（R10，M1）

输入（数据 A，联络广播里公布的路径；取法见本文件末尾的说明）：
  <data>/tsb-team-results.jsonl     单号结算记录，119 条
  <data>/G01-G09-squad.log          小队日志（只用前 MAX_LOG_LINE 行，后面是连接层的重复输出）

输出：
  out/m1/rooms.json    每个房间一条记录（见 README 字段说明）
  out/m1/rooms.md      人读的表

做的事（全部是机械规则，没有人工判断）：
  1. 结算记录 → 房间。同一个房间的判据：地图陆地像素数 land 相同、真人数 H（humans 列表长度）相同、
     由 game 字段前缀解出的开局时刻相差不超过 ROOM_TOL_MS。
     （game 字段是每个号自己生成的「开局毫秒时间戳的 36 进制 + 随机数」，各号不同，不能直接当房间号。
       出处：page.js track()：id = `${now.toString(36)}-${rand}`。）
  2. 小队日志 → 对局。按 [HL-GAME-INIT] 的 (mapSeed, players) 变化切分；每局收集各号的 me 编号、
     快照、报错、热更新、结算行。
  3. 两边对号：同一个号、同一个 me 编号、同一个 H。
  4. 队伍数：三个来源并列给出，互相核对。
       T_nominal = mode + 2                         （引擎：vz<7 时 numberTeams = vz+2）
       T_rule    = 把 T_nominal 往下减，直到「最大战队人数 <= floor(H / T)」，最小 2
                   （引擎的分队函数：while(T>2 && 最大战队人数 > floor(H/T)) T--）
                   这里的「最大战队人数」只知道我方带 [Nope] 标签进场的号数，所以 T_rule 是上界。
       T_obs     = 各号结算记录里 team.totals 的非 0 键数的最大值（下界：之前已被消灭的队看不到）
     team.totals 的 "0" 键不是队伍：引擎里 team=0 表示「不属于任何队」，内置 AI 在少于 8 队的局里都是 0。

用法：
  python3 m1_games.py [数据目录] [输出目录]
  默认数据目录 /tmp/c136-r10/c116-winrate/data ，默认输出目录 <脚本目录>/../out/m1
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict

ROOM_TOL_MS = 5000       # 同一房间各号开局时刻的最大差
MAX_LOG_LINE = 7992      # 日志只有前 7992 行有对局内容（c136 广播 0002；本脚本会自检最后一条对局行的行号）
SNAP_TICKS = [630, 1530, 3060, 4500]   # 团队领土份额取样拍（HL-TICK 每 90 拍一条，从 630 起）
SNAP_TOL = 90            # 取样时允许的拍差

RE_PREFIX = re.compile(r"^\[(\[Nope\] \w+)\] (.*)$")
RE_INIT = re.compile(r"\[HL-GAME-INIT\] mode=(-?\d+) map=(-?\d+) mapSeed=(-?\d+) players=(\d+) me=(-?\d+)")
RE_TICK = re.compile(r"\[HL-TICK\] t=(\d+) terr=(\d+)\(([\d.]+)%\) bal=(-?\d+) dens=([\d.]+) nb=(\d+) neut=(\d+) "
                     r"cmds=(\d+) boats=(\d+) avgMs=([\d.]+) maxMs=([\d.]+) skip=(\d+)")
RE_RESULT = re.compile(r"^\[RESULT (\[Nope\] \w+)\] result=(\w+) event=(\w+) place=(\d+)")
RE_SELF = re.compile(r"^\[SELF-CHECK OK\] (\[Nope\] \w+) verified in Room 0 as \"([^\"]*)\" \(acc=\w+, room0NopeCount=(\d+)\)")
RE_HOT = re.compile(r"^\[HOT-IMPORT\] Injected updated (\S+) \((\d+) bytes\) into (\[Nope\] \w+)")
RE_ERR = re.compile(r"ERROR: Strategy bot stopped: (.*)$")
RE_ANYT = re.compile(r"\bt=(\d+)\b")


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def t0_ms(game_id: str) -> int:
    return int(game_id.split("-")[0], 36)


def iso_utc(ms: int) -> str:
    import datetime
    return datetime.datetime.fromtimestamp(ms / 1000.0, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + f"{ms % 1000:03d}Z"


# ----------------------------------------------------------------------------
# 结算记录 → 房间
# ----------------------------------------------------------------------------

def load_results(path: str) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            r["_row"] = i
            r["_t0"] = t0_ms(r["game"])
            r["_H"] = len(r["humans"])
            rows.append(r)
    return rows


def cluster_rooms(rows: list[dict]) -> list[list[dict]]:
    rooms: list[list[dict]] = []
    for r in sorted(rows, key=lambda x: (x["_t0"], x["_row"])):
        placed = False
        for room in reversed(rooms):
            first = room[0]
            if r["_t0"] - first["_t0"] > ROOM_TOL_MS:
                break
            if first["land"] == r["land"] and first["_H"] == r["_H"]:
                room.append(r)
                placed = True
                break
        if not placed:
            rooms.append([r])
    return rooms


def nonzero_team_keys(team: dict | None) -> list[str]:
    if not team or not team.get("totals"):
        return []
    return sorted(k for k in team["totals"].keys() if k != "0")


def summarize_room(room: list[dict]) -> dict:
    room = sorted(room, key=lambda x: x["_row"])
    bots = [r["bot"] for r in room]
    assert len(set(bots)) == len(bots), f"同一房间里同一个号出现两次：{bots}"
    played = [r for r in room if r["tick"] > 0]
    recs = []
    for r in room:
        team = r.get("team")
        recs.append({
            "row": r["_row"], "bot": r["bot"], "me": r["me"]["id"], "event": r["event"], "result": r["result"],
            "why": r.get("why"), "tick": r["tick"], "seconds": r["seconds"], "place": r["place"],
            "alivePlayers": r["alivePlayers"], "territory": r["territory"], "peak": r["peak"],
            "balance": r["balance"], "sent": r["sent"], "accepted": r["accepted"],
            "mine": team.get("mine") if team else None, "best": team.get("best") if team else None,
            "totals": team.get("totals") if team else None, "at": r["at"],
        })
    mines = sorted({x["mine"] for x in recs if x["mine"] is not None})
    t_obs = max((len(nonzero_team_keys(r.get("team"))) for r in room), default=0)
    results = Counter(r["result"] for r in room)
    events = Counter(r["event"] for r in room)
    won = results.get("won", 0) > 0
    saw_end = events.get("end", 0) > 0
    # 最后一条带 team 的记录（按拍）：用来描述「我们最后看到的局面」
    with_team = [r for r in room if r.get("team")]
    last = max(with_team, key=lambda r: r["tick"]) if with_team else None
    last_view = None
    if last:
        tot = last["team"]["totals"]
        land = last["land"]
        mine = str(last["team"]["mine"])
        best = str(last["team"]["best"])
        last_view = {
            "tick": last["tick"], "bot": last["bot"], "mine": last["team"]["mine"], "best": last["team"]["best"],
            "mine_share_of_land": (tot.get(mine, 0) / land) if land else None,
            "best_share_of_land": (tot.get(best, 0) / land) if land else None,
            "teams_alive": len(nonzero_team_keys(last["team"])),
        }
    if not played:
        kind = "aborted"          # 所有号都在 tick=0 离开：没开打
    else:
        kind = "played"
    if kind == "played":
        if won:
            squad_outcome = "won"
        elif saw_end:
            squad_outcome = "lost_observed"      # 有号活到终局，终局时我方队伍不是领土第一
        else:
            squad_outcome = "lost_inferred"      # 我方的号在终局前全部死亡或离开，终局没有被记录
    else:
        squad_outcome = None
    return {
        "t0_ms": min(r["_t0"] for r in room), "t0_utc": iso_utc(min(r["_t0"] for r in room)),
        "t0_spread_ms": max(r["_t0"] for r in room) - min(r["_t0"] for r in room),
        "land": room[0]["land"], "H": room[0]["_H"], "players": room[0]["players"],
        "strategy": sorted({r.get("strategy") for r in room}), "ext": sorted({r.get("ext") for r in room}),
        "n_records": len(room), "n_played_records": len(played), "kind": kind,
        "max_tick": max(r["tick"] for r in room),
        "results": dict(results), "events": dict(events),
        "why": dict(Counter(r.get("why") for r in room if r.get("why"))),
        "mine_values": mines, "split": len(mines) > 1,
        "T_obs": t_obs, "squad_outcome": squad_outcome, "saw_end": saw_end,
        "last_view": last_view,
        "records": recs,
    }


# ----------------------------------------------------------------------------
# 小队日志 → 对局
# ----------------------------------------------------------------------------

def parse_log(path: str) -> tuple[list[dict], dict]:
    games: list[dict] = []
    cur: dict | None = None
    pending_self: list[dict] = []
    last_game_line = 0
    last_tick_by_bot: dict[str, int] = {}
    n_lines = 0
    with open(path, encoding="utf-8", errors="replace") as f:
        for ln, raw in enumerate(f, 1):
            n_lines = ln
            line = raw.rstrip("\r\n")
            if ln > MAX_LOG_LINE:
                # 只做一件事：确认后面没有对局内容（自检用）
                if "[HL-TICK]" in line or "[HL-GAME-INIT]" in line or line.startswith("[RESULT "):
                    last_game_line = ln
                continue
            m = RE_SELF.match(line)
            if m:
                pending_self.append({"line": ln, "bot": m.group(1), "as": m.group(2), "nope": int(m.group(3))})
                continue
            m = RE_HOT.match(line)
            if m:
                if cur is not None:
                    cur["hot_imports"].append({"line": ln, "file": m.group(1), "bytes": int(m.group(2)), "bot": m.group(3),
                                               "max_tick_so_far": max(last_tick_by_bot.values(), default=None)})
                    last_game_line = ln
                continue
            m = RE_RESULT.match(line)
            if m:
                if cur is not None:
                    cur["result_lines"].append({"line": ln, "bot": m.group(1), "result": m.group(2), "event": m.group(3),
                                                "place": int(m.group(4))})
                    cur["last_line"] = ln
                    last_game_line = ln
                continue
            if line.startswith("[BACKEND-SPAWN-COORD] Solved"):
                if cur is not None:
                    cur["n_spawn_solved"] += 1
                continue
            if line.startswith("[OPENING-CHECK"):
                if cur is not None:
                    cur["opening_check"].append({"line": ln, "text": line})
                continue
            m = RE_PREFIX.match(line)
            if not m:
                continue
            bot, rest = m.group(1), m.group(2)
            mi = RE_INIT.search(rest)
            if mi:
                mode, mp, seed, players, me = (int(x) for x in mi.groups())
                key = (seed, players, mp, mode)
                if cur is None or cur["_key"] != key:
                    cur = {
                        "_key": key, "mode": mode, "map": mp, "mapSeed": seed, "H": players,
                        "first_line": ln, "last_line": ln, "me": {}, "init_lines": 0,
                        "selfcheck": pending_self, "ticks": defaultdict(list), "errors": defaultdict(list),
                        "hot_imports": [], "result_lines": [], "n_spawn_solved": 0, "opening_check": [],
                        "counts": Counter(),
                    }
                    pending_self = []
                    last_tick_by_bot = {}
                    games.append(cur)
                cur["me"].setdefault(bot, me)
                assert cur["me"][bot] == me, f"第 {ln} 行：{bot} 的 me 在同一局里变了"
                cur["init_lines"] += 1
                last_game_line = ln
                continue
            if cur is None:
                continue
            mt = RE_TICK.search(rest)
            if mt:
                t, terr = int(mt.group(1)), int(mt.group(2))
                cur["ticks"][bot].append({
                    "line": ln, "t": t, "terr": terr, "pct": float(mt.group(3)), "bal": int(mt.group(4)),
                    "dens": float(mt.group(5)), "nb": int(mt.group(6)), "neut": int(mt.group(7)),
                    "cmds": int(mt.group(8)), "boats": int(mt.group(9)),
                })
                last_tick_by_bot[bot] = t
                cur["last_line"] = ln
                cur["counts"]["HL-TICK"] += 1
                last_game_line = ln
                continue
            me_ = RE_ERR.search(rest)
            if me_:
                cur["errors"][bot].append({"line": ln, "msg": me_.group(1), "last_tick_seen": last_tick_by_bot.get(bot)})
                cur["counts"]["ERROR"] += 1
                continue
            for tag in ("HL-SPAWN-BACKEND", "HL-OPENING", "HL-DONATE", "HL-ASSIST", "HL-INTERCEPT", "HL-SLOW-TICK"):
                if "[" + tag + "]" in rest:
                    cur["counts"][tag] += 1
                    if tag != "HL-SPAWN-BACKEND":
                        ma = RE_ANYT.search(rest)
                        if ma:
                            last_tick_by_bot[bot] = max(last_tick_by_bot.get(bot, 0), int(ma.group(1)))
                    break
    meta = {"n_lines": n_lines, "last_game_content_line_after_cut": last_game_line if last_game_line > MAX_LOG_LINE else None}
    return games, meta


def snapshot(ticks: list[dict], t: int) -> dict | None:
    best = None
    for s in ticks:
        d = abs(s["t"] - t)
        if d <= SNAP_TOL and (best is None or d < abs(best["t"] - t)):
            best = s
    return best


def summarize_log_game(g: dict, idx: int) -> dict:
    bots = sorted(g["me"].keys())
    err = {}
    for b, lst in g["errors"].items():
        ticks_seen = [e["last_tick_seen"] for e in lst if e["last_tick_seen"] is not None]
        err[b] = {
            "n": len(lst), "first_line": lst[0]["line"], "last_line": lst[-1]["line"],
            "msgs": dict(Counter(e["msg"] for e in lst)),
            "last_tick_seen_at_first_error": lst[0]["last_tick_seen"],
            "last_tick_seen_at_last_error": lst[-1]["last_tick_seen"],
            "min_tick_seen": min(ticks_seen) if ticks_seen else None,
        }
    tick_summary = {}
    for b in bots:
        tl = g["ticks"].get(b, [])
        ts = [s["t"] for s in tl]
        gaps = [(a, c) for a, c in zip(ts, ts[1:]) if c - a > 90]
        tick_summary[b] = {
            "n": len(tl), "first_t": ts[0] if ts else None, "last_t": ts[-1] if ts else None,
            "peak_terr_in_snapshots": max((s["terr"] for s in tl), default=None),
            "gaps": gaps,
        }
    self_names = sorted({s["bot"] for s in g["selfcheck"]})
    self_mismatch = [s for s in g["selfcheck"] if s["bot"] != s["as"]]
    return {
        "log_index": idx, "mode": g["mode"], "map": g["map"], "mapSeed": g["mapSeed"], "H": g["H"],
        "first_line": g["first_line"], "last_line": g["last_line"],
        "bots_in_game": bots, "n_bots_in_game": len(bots), "me": {b: g["me"][b] for b in bots},
        "init_lines": g["init_lines"], "n_spawn_solved": g["n_spawn_solved"],
        "selfcheck_bots": self_names, "selfcheck_lines": len(g["selfcheck"]),
        "selfcheck_max_nope": max((s["nope"] for s in g["selfcheck"]), default=None),
        "selfcheck_name_mismatch": len(self_mismatch),
        "bots_in_game_not_selfchecked": sorted(set(bots) - set(self_names)),
        "counts": dict(g["counts"]),
        "errors": err, "n_error_lines": sum(v["n"] for v in err.values()),
        "hot_imports": g["hot_imports"],
        "max_tick_in_snapshots": max((s["t"] for tl in g["ticks"].values() for s in tl), default=None),
        "tick_summary": tick_summary,
        "result_lines": g["result_lines"],
        "_ticks": {b: g["ticks"].get(b, []) for b in bots},
    }


def t_rule(t_nominal: int, H: int, clan: int) -> int:
    """引擎分队函数里的队伍数下调规则（只考虑一个战队的人数 clan）。"""
    T = t_nominal
    while T > 2 and clan > H // T:
        T -= 1
    return T


# ----------------------------------------------------------------------------
# 主流程
# ----------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    data_dir = argv[1] if len(argv) > 1 else "/tmp/c136-r10/c116-winrate/data"
    out_dir = argv[2] if len(argv) > 2 else os.path.join(here, "..", "out", "m1")
    os.makedirs(out_dir, exist_ok=True)
    res_path = os.path.join(data_dir, "tsb-team-results.jsonl")
    log_path = os.path.join(data_dir, "G01-G09-squad.log")

    rows = load_results(res_path)
    rooms = [summarize_room(r) for r in cluster_rooms(rows)]
    rooms.sort(key=lambda r: r["t0_ms"])
    log_games_raw, log_meta = parse_log(log_path)
    log_games = [summarize_log_game(g, i) for i, g in enumerate(log_games_raw)]

    # 对号：同一个号 + 同一个 me + 同一个 H
    used = set()
    for room in rooms:
        room["log"] = None
        if room["kind"] != "played":
            continue
        cand = []
        for lg in log_games:
            if lg["H"] != room["H"]:
                continue
            hit = sum(1 for rec in room["records"] if lg["me"].get(rec["bot"]) == rec["me"])
            if hit:
                cand.append((hit, lg))
        if cand:
            hit, lg = max(cand, key=lambda x: x[0])
            assert lg["log_index"] not in used, "一个日志对局对上了两个房间"
            used.add(lg["log_index"])
            assert hit == room["n_records"], f"房间 {room['t0_utc']} 只有 {hit}/{room['n_records']} 条记录对上日志"
            room["log"] = lg
    assert len(used) == len(log_games), f"有日志对局没对上房间：{len(used)}/{len(log_games)}"

    # 编号：有日志的房间按时间顺序叫 G00..；没日志但打过的叫 P1..；没开打的叫 A1..
    gi = pi = ai = 0
    for room in rooms:
        if room["log"] is not None:
            room["id"] = f"G{gi:02d}"
            gi += 1
        elif room["kind"] == "played":
            pi += 1
            room["id"] = f"P{pi}"
        else:
            ai += 1
            room["id"] = f"A{ai:02d}"

    # 队伍数与衍生量
    for room in rooms:
        lg = room["log"]
        room["n_bots_results"] = room["n_records"]
        if lg:
            room["T_nominal"] = lg["mode"] + 2 if 0 <= lg["mode"] < 7 else None
            clan = lg["selfcheck_max_nope"] if lg["selfcheck_max_nope"] is not None else lg["n_bots_in_game"]
            room["clan_for_rule"] = clan
            room["T_rule"] = t_rule(room["T_nominal"], room["H"], clan) if room["T_nominal"] else None
            room["T_rule_if_all_bots_tagged"] = (t_rule(room["T_nominal"], room["H"], lg["n_bots_in_game"])
                                                 if room["T_nominal"] else None)
        else:
            room["T_nominal"] = room["T_rule"] = room["T_rule_if_all_bots_tagged"] = room["clan_for_rule"] = None
        if room["kind"] == "played":
            # 采用的队伍数：有日志用 T_rule，并要求 T_obs <= T_rule；没有日志只能用 T_obs（下界）
            if room["T_rule"] is not None:
                assert room["T_obs"] <= room["T_rule"], f"{room['id']}: T_obs {room['T_obs']} > T_rule {room['T_rule']}"
                room["T"] = room["T_rule"]
                room["T_source"] = "rule(mode,H,clan)" + ("=obs" if room["T_obs"] == room["T_rule"] else ">obs")
            else:
                room["T"] = room["T_obs"]
                room["T_source"] = "obs(lower bound)"
        else:
            room["T"] = None
            room["T_source"] = None
        # 团队（我方各号之和）领土份额取样
        if lg:
            snaps = {}
            death_tick = {rec["bot"]: rec["tick"] for rec in room["records"]}
            for t in SNAP_TICKS:
                terr_sum = 0
                n_alive = 0
                n_missing = 0
                per_bot = {}
                for b in lg["bots_in_game"]:
                    s = snapshot(lg["_ticks"][b], t)
                    if s is not None:
                        terr_sum += s["terr"]
                        n_alive += 1
                        per_bot[b] = s["terr"]
                    elif b in death_tick and death_tick[b] < t - SNAP_TOL:
                        per_bot[b] = 0          # 已经有结算记录（死亡或离开）
                    else:
                        per_bot[b] = None       # 该拍附近没有快照，也没有更早的结算：缺测
                        n_missing += 1
                snaps[str(t)] = {
                    "squad_terr": terr_sum, "squad_share": terr_sum / room["land"],
                    "n_with_snapshot": n_alive, "n_missing": n_missing, "per_bot": per_bot,
                }
            room["snapshots"] = snaps
        else:
            room["snapshots"] = None

    # 自检
    checks = []
    n_rec = sum(r["n_records"] for r in rooms)
    checks.append(("结算记录数 = 119", n_rec == 119 == len(rows), n_rec))
    checks.append(("日志对局数 = 10", len(log_games) == 10, len(log_games)))
    checks.append(("日志 7992 行之后没有对局内容", log_meta["last_game_content_line_after_cut"] is None,
                   log_meta["last_game_content_line_after_cut"]))
    g_rooms = [r for r in rooms if r["log"] is not None]
    n_log_results = sum(len(r["log"]["result_lines"]) for r in g_rooms)
    checks.append(("日志里的 [RESULT] 行数 = 有日志房间的结算记录数",
                   n_log_results == sum(r["n_records"] for r in g_rooms), n_log_results))
    for r in g_rooms:
        a = sorted((x["bot"], x["result"], x["event"], x["place"]) for x in r["log"]["result_lines"])
        b = sorted((x["bot"], x["result"], x["event"], x["place"]) for x in r["records"])
        checks.append((f"{r['id']} 日志 [RESULT] 行与结算记录逐条一致", a == b, len(a)))
    max_spread = max(r["t0_spread_ms"] for r in rooms)
    checks.append((f"房间内开局时刻最大差 <= {ROOM_TOL_MS} ms", max_spread <= ROOM_TOL_MS, max_spread))
    ts = sorted(r["t0_ms"] for r in rooms)
    min_gap = min(b - a for a, b in zip(ts, ts[1:]))
    checks.append(("相邻房间开局时刻最小间隔 > 4 倍容差", min_gap > 4 * ROOM_TOL_MS, min_gap))

    # 输出
    def strip(room: dict) -> dict:
        out = {k: v for k, v in room.items()}
        if out.get("log"):
            lg = {k: v for k, v in out["log"].items() if k != "_ticks"}
            out["log"] = lg
        return out

    payload = {
        "source": {
            "results": {"path": "c116-winrate/data/tsb-team-results.jsonl", "sha256": sha256(res_path), "rows": len(rows)},
            "log": {"path": "c116-winrate/data/G01-G09-squad.log", "sha256": sha256(log_path),
                    "lines": log_meta["n_lines"], "lines_used": MAX_LOG_LINE},
            "branch": "cursor/c116-winrate-liaison-b3bc",
        },
        "params": {"ROOM_TOL_MS": ROOM_TOL_MS, "MAX_LOG_LINE": MAX_LOG_LINE, "SNAP_TICKS": SNAP_TICKS, "SNAP_TOL": SNAP_TOL},
        "checks": [{"name": n, "ok": bool(ok), "value": v} for n, ok, v in checks],
        "rooms": [strip(r) for r in rooms],
    }
    with open(os.path.join(out_dir, "rooms.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1, sort_keys=True)

    lines = []
    lines.append("# 数据 A：房间表（由 scripts/m1_games.py 生成，勿手改）\n")
    lines.append("## 自检\n")
    for n, ok, v in checks:
        lines.append(f"- {'PASS' if ok else 'FAIL'} {n}（{v}）")
    lines.append("\n## 打过的房间（至少一个号 tick>0）\n")
    lines.append("| 编号 | 开局 UTC | H | land | 记录数 | 结果分布 | 小队结局 | 终局是否被记录 | mode | T_nominal | T_rule | T_obs | 采用 T | 我方队伍号 | 拆队 | 日志号数 / 自检 [Nope] 数 | 报错行 | 热更新 | 最大拍 |")
    lines.append("| :-: | :-- | --: | --: | --: | :-- | :-- | :-: | --: | --: | --: | --: | --: | :-- | :-: | :-- | --: | --: | --: |")
    for r in rooms:
        if r["kind"] != "played":
            continue
        lg = r["log"]
        res = " ".join(f"{k}{v}" for k, v in sorted(r["results"].items()))
        lines.append(
            f"| {r['id']} | {r['t0_utc'][11:19]} | {r['H']} | {r['land']} | {r['n_records']} | {res} | {r['squad_outcome']} | "
            f"{'是' if r['saw_end'] else '否'} | {lg['mode'] if lg else '—'} | {r['T_nominal'] or '—'} | {r['T_rule'] or '—'} | "
            f"{r['T_obs']} | {r['T']} | {','.join(str(x) for x in r['mine_values'])} | {'是' if r['split'] else '否'} | "
            f"{(str(lg['n_bots_in_game']) + ' / ' + str(lg['selfcheck_max_nope'])) if lg else '—'} | "
            f"{lg['n_error_lines'] if lg else '—'} | {len(lg['hot_imports']) if lg else '—'} | {r['max_tick']} |")
    lines.append("\n## 没开打的房间（所有号都在 tick=0 离开）\n")
    lines.append("| 编号 | 开局 UTC | H | land | 记录数 | 号 |")
    lines.append("| :-: | :-- | --: | --: | --: | :-- |")
    for r in rooms:
        if r["kind"] == "played":
            continue
        lines.append(f"| {r['id']} | {r['t0_utc'][11:19]} | {r['H']} | {r['land']} | {r['n_records']} | "
                     f"{', '.join(x['bot'].replace('[Nope] ', '') for x in r['records'])} |")
    lines.append("\n## 我们最后看到的局面（最后一条带 team 字段的记录）\n")
    lines.append("| 编号 | 拍 | 存活队伍数 | 我方队伍份额 | 第一名份额 | 第一名是不是我方 |")
    lines.append("| :-: | --: | --: | --: | --: | :-: |")
    for r in rooms:
        lv = r.get("last_view")
        if r["kind"] != "played" or not lv:
            continue
        lines.append(f"| {r['id']} | {lv['tick']} | {lv['teams_alive']} | {100*lv['mine_share_of_land']:.1f}% | "
                     f"{100*lv['best_share_of_land']:.1f}% | {'是' if lv['mine'] == lv['best'] else '否'} |")
    lines.append("\n## 我方各号领土之和占全图陆地的份额（只有我方的号，不含同队的其他真人）\n")
    lines.append("| 编号 | " + " | ".join(f"t≈{t}（有快照/缺测）" for t in SNAP_TICKS) + " |")
    lines.append("| :-: | " + " | ".join("--:" for _ in SNAP_TICKS) + " |")
    for r in rooms:
        if not r.get("snapshots"):
            continue
        cells = []
        for t in SNAP_TICKS:
            s = r["snapshots"][str(t)]
            cells.append(f"{100*s['squad_share']:.1f}%（{s['n_with_snapshot']}/{s['n_missing']}）")
        lines.append(f"| {r['id']} | " + " | ".join(cells) + " |")
    lines.append("")
    with open(os.path.join(out_dir, "rooms.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    bad = [c for c in checks if not c[1]]
    print(f"rooms={len(rooms)} played={sum(1 for r in rooms if r['kind']=='played')} "
          f"with_log={len(g_rooms)} checks={len(checks)-len(bad)}/{len(checks)}")
    for n, ok, v in checks:
        if not ok:
            print("FAIL", n, v)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

# 数据的取法（在自己的 c136 工作区里）：
#   bash c136-review/tools/bus-get.sh cursor/c116-winrate-liaison-b3bc c116-winrate /tmp/c136-r10/c116-winrate
# 本脚本写成时该分支的提交号是 d9a56dcde66f；输出里记录了两个输入文件的 sha256。
