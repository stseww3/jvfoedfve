#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build-clean-dataset.py — Builds the complete, sanitized in-match dataset and
clean in-game source mirror in /agent/repos/c136-data for c136 R01..R10.
"""

from __future__ import annotations
import csv
import datetime
import gzip
import hashlib
import json
import os
import re
import shutil
from collections import Counter, defaultdict

OUT_ROOT = "/agent/repos/c136-data"
BUNDLES_DISC = os.path.join(OUT_ROOT, "bundles")
BUNDLES_VAL = os.path.join(OUT_ROOT, "validation_bundles")
SRC_DIR = os.path.join(OUT_ROOT, "src")

RE_BOT_PREFIX = re.compile(r"^\[(?:\[(?:Nope|APEX)\]\s*)?([^\]]+)\]\s*(.*)$")
RE_INIT = re.compile(r"^\[HL-GAME-INIT\] mode=(-?\d+) map=(-?\d+) mapSeed=(-?\d+) players=(\d+) me=(-?\d+)")
RE_COORD = re.compile(r"^\[(?:BACKEND-)?SPAWN-COORD\] Solved (\d+) bots in ([\d.]+)ms \(map=(\d+)x(\d+), minSep=(\d+)px, boss=([^)]*)\): (.*)$")
RE_SPAWN_B = re.compile(r"^\[HL-SPAWN-BACKEND\] me=(-?\d+) slot=(-?\d+) role=([A-Z0-9_]+) -> \((-?\d+),(-?\d+)\) bossDist=(-?\d+) minAllyDist=(-?\d+) voronoi=(-?\d+)")
RE_SPAWN_L = re.compile(r"^\[HL-SPAWN\] me=(-?\d+) slot=(-?\d+) \(squad=(\d+),rankIdx=(\d+)\) -> \((-?\d+),(-?\d+)\) chosenSlots=(\d+)/(\d+) minSep=(-?\d+)")
RE_OPENING = re.compile(r"^\[HL-OPENING\] t=(\d+) cyc=(\d+) DP expand rings=(\d+) spend=(\d+)/(\d+) terr=(\d+)")
RE_OPENCHECK = re.compile(r"^\[OPENING-CHECK (\d+) bots @ tick (\d+)\] (.*)$")
RE_TICK = re.compile(r"^\[HL-TICK\] t=(\d+) terr=(\d+)\(([\d.]+)%\) bal=(-?\d+) dens=([\d.]+) nb=(\d+) neut=(\d+) cmds=(\d+) boats=(\d+)(?: avgMs=([\d.]+) maxMs=([\d.]+) skip=(\d+))?")
RE_SLOW = re.compile(r"^\[HL-SLOW-TICK\] t=(\d+) took ([\d.]+)ms \(max=([\d.]+)ms\)")
RE_DONATE = re.compile(r"^\[HL-DONATE\] t=(\d+) (.*?) pct=(\d+)/1024(?: \(~5%\))? -> (?:ally|boss)=(\d+)\((.*?)\)(?: boxedIn=(true|false))? myBal=(-?\d+) dMe=(-?\d+)(?: dAlly=(-?\d+))?(?: dBoss=(-?\d+))?")
RE_DISPATCH = re.compile(r"^\[HL-DISPATCH\] t=(\d+) (\w+) pct=(\d+)/1024 -> ally=(\d+)\((.*?)\) boxedIn=(true|false) myBal=(-?\d+) dMe=(-?\d+) dAlly=(-?\d+)")
RE_ASSIST = re.compile(r"^\[HL-ASSIST\] t=(\d+) 10% (squad-rescue|boss-assist) poke -> (?:enemy|target)=(\d+)\((.*?)\)(?: for ally=(\d+)\((.*?)\))?(?: myBal=(-?\d+) dMe=(-?\d+))?$")
RE_INTERCEPT = re.compile(r"^\[HL-INTERCEPT\] t=(\d+) unified sea intercept pct=(\d+)/1024 -> boatId=(\d+) owner=(\d+)\((.*?)\) boatTroops=(\d+)")
RE_PEACE = re.compile(r"^\[HL-PEACE\] t=(\d+) initiated peace vote \(teamLand=([\d.]+)%\)")
RE_RESULT = re.compile(r"^\[RESULT (?:\[(?:Nope|APEX)\]\s*)?([^\]]+)\] result=(\w+) event=(\w+) place=(\d+).*?\bpeak=(\d+) team=(.*)$")
RE_REPLAY_RAW = re.compile(r"\[HL-(?:LIVE-)?REPLAY-(?:RAW|URL)\]\s+(\S+)")
RE_REPLAY_SAVED = re.compile(r"\[REPLAY-SAVED\] game=([a-z0-9-]+) len=(\d+) -> .*?[\\/](replay-[^\s\\/]+\.txt)")


def t0_ms(game_id: str) -> int:
    try:
        return int(game_id.split("-")[0], 36)
    except Exception:
        return 0


def iso_utc(ms: int) -> str:
    if not ms:
        return ""
    return datetime.datetime.fromtimestamp(ms / 1000.0, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def clean_bot_name(name: str) -> str:
    return re.sub(r"^\[[^\]]+\]\s*", "", name or "").strip()


def sanitize_log_line(line: str) -> str:
    line = re.sub(r"\bhumans=(\d+)", r"seeded=\1", line)
    line = re.sub(r"\b\[(?:Nope|APEX)\]\s*", "", line)
    return line


def parse_in_game_line(line_no: int, raw_line: str) -> dict | None:
    text = raw_line.strip()
    if not text:
        return None
    m_Saved = RE_REPLAY_SAVED.search(text)
    if m_Saved:
        return {"type": "REPLAY_REF", "line": line_no, "game": m_Saved.group(1), "file": m_Saved.group(3)}
    m_Raw = RE_REPLAY_RAW.search(text)
    if m_Raw:
        url = m_Raw.group(1)
        rep = url.split("replay=", 1)[-1] if "replay=" in url else url
        return {"type": "REPLAY_STR", "line": line_no, "replay": rep}

    m_res = RE_RESULT.match(text)
    if m_res:
        t_str = m_res.group(6).strip()
        team = None if t_str == "null" else json.loads(t_str)
        return {
            "type": "RESULT", "line": line_no, "bot": clean_bot_name(m_res.group(1)),
            "result": m_res.group(2), "event": m_res.group(3),
            "place": int(m_res.group(4)), "peak": int(m_res.group(5)), "team": team,
            "clean_line": sanitize_log_line(text),
        }

    m_coord = RE_COORD.match(text)
    if m_coord:
        return {
            "type": "COORD", "line": line_no, "bot": None, "t": 0,
            "n": int(m_coord.group(1)), "ms": float(m_coord.group(2)),
            "W": int(m_coord.group(3)), "H": int(m_coord.group(4)),
            "minSep": int(m_coord.group(5)), "boss": m_coord.group(6),
            "clean_line": sanitize_log_line(text),
        }

    m_oc = RE_OPENCHECK.match(text)
    if m_oc:
        return {
            "type": "OPENCHECK", "line": line_no, "bot": None,
            "n": int(m_oc.group(1)), "t": int(m_oc.group(2)),
            "body": m_oc.group(3), "clean_line": sanitize_log_line(text),
        }

    m_pfx = RE_BOT_PREFIX.match(text)
    if not m_pfx:
        return None
    bot = clean_bot_name(m_pfx.group(1))
    body = m_pfx.group(2)

    m = RE_TICK.match(body)
    if m:
        return {
            "type": "TICK", "line": line_no, "bot": bot,
            "t": int(m.group(1)), "terr": int(m.group(2)), "pct": float(m.group(3)),
            "bal": int(m.group(4)), "dens": float(m.group(5)),
            "nb": int(m.group(6)), "neut": int(m.group(7)),
            "cmds": int(m.group(8)), "boats": int(m.group(9)),
            "avgMs": float(m.group(10)) if m.group(10) else 0.0,
            "maxMs": float(m.group(11)) if m.group(11) else 0.0,
            "skip": int(m.group(12)) if m.group(12) else 0,
            "clean_line": f"[{bot}] {sanitize_log_line(body)}",
        }

    m = RE_INIT.match(body)
    if m:
        return {
            "type": "INIT", "line": line_no, "bot": bot, "t": 0,
            "mode": int(m.group(1)), "map": int(m.group(2)),
            "mapSeed": int(m.group(3)), "seededPlayers": int(m.group(4)), "me": int(m.group(5)),
            "clean_line": f"[{bot}] [HL-GAME-INIT] mode={m.group(1)} map={m.group(2)} mapSeed={m.group(3)} seeded={m.group(4)} me={m.group(5)}",
        }

    m = RE_SPAWN_B.match(body)
    if m:
        return {
            "type": "SPAWN", "line": line_no, "bot": bot, "t": 0,
            "me": int(m.group(1)), "slot": int(m.group(2)), "role": m.group(3),
            "x": int(m.group(4)), "y": int(m.group(5)),
            "bossDist": int(m.group(6)), "minAllyDist": int(m.group(7)), "voronoi": int(m.group(8)),
            "clean_line": f"[{bot}] {sanitize_log_line(body)}",
        }

    m = RE_SPAWN_L.match(body)
    if m:
        return {
            "type": "SPAWN", "line": line_no, "bot": bot, "t": 0,
            "me": int(m.group(1)), "slot": int(m.group(2)), "role": f"RANK_{m.group(4)}",
            "x": int(m.group(5)), "y": int(m.group(6)),
            "bossDist": -1, "minAllyDist": int(m.group(9)), "voronoi": -1,
            "clean_line": f"[{bot}] {sanitize_log_line(body)}",
        }

    m = RE_OPENING.match(body)
    if m:
        return {
            "type": "OPENING", "line": line_no, "bot": bot,
            "t": int(m.group(1)), "cyc": int(m.group(2)), "rings": int(m.group(3)),
            "spend": int(m.group(4)), "bal": int(m.group(5)), "terr": int(m.group(6)),
            "clean_line": f"[{bot}] {sanitize_log_line(body)}",
        }

    m = RE_DISPATCH.match(body)
    if m:
        return {
            "type": "DISPATCH", "line": line_no, "bot": bot,
            "t": int(m.group(1)), "kind": m.group(2), "pct": int(m.group(3)),
            "target": int(m.group(4)), "targetName": clean_bot_name(m.group(5)),
            "boxedIn": m.group(6) == "true", "myBal": int(m.group(7)),
            "dMe": int(m.group(8)), "dAlly": int(m.group(9)),
            "clean_line": f"[{bot}] {sanitize_log_line(body)}",
        }

    m = RE_DONATE.match(body)
    if m:
        d_ally = m.group(9) or m.group(10)
        return {
            "type": "DONATE", "line": line_no, "bot": bot,
            "t": int(m.group(1)), "kind": m.group(2).strip(), "pct": int(m.group(3)),
            "target": int(m.group(4)), "targetName": clean_bot_name(m.group(5)),
            "boxedIn": None if m.group(6) is None else (m.group(6) == "true"),
            "myBal": int(m.group(7)), "dMe": int(m.group(8)),
            "dAlly": int(d_ally) if d_ally else None,
            "clean_line": f"[{bot}] {sanitize_log_line(body)}",
        }

    m = RE_ASSIST.match(body)
    if m:
        return {
            "type": "ASSIST", "line": line_no, "bot": bot,
            "t": int(m.group(1)), "kind": m.group(2),
            "target": int(m.group(3)), "targetName": clean_bot_name(m.group(4)),
            "ally": int(m.group(5)) if m.group(5) else None,
            "allyName": clean_bot_name(m.group(6)) if m.group(6) else None,
            "myBal": int(m.group(7)) if m.group(7) else None,
            "dMe": int(m.group(8)) if m.group(8) else None,
            "clean_line": f"[{bot}] {sanitize_log_line(body)}",
        }

    m = RE_INTERCEPT.match(body)
    if m:
        return {
            "type": "INTERCEPT", "line": line_no, "bot": bot,
            "t": int(m.group(1)), "kind": "sea_intercept", "pct": int(m.group(2)),
            "boatId": int(m.group(3)), "target": int(m.group(4)),
            "targetName": clean_bot_name(m.group(5)), "boatTroops": int(m.group(6)),
            "clean_line": f"[{bot}] {sanitize_log_line(body)}",
        }

    m = RE_PEACE.match(body)
    if m:
        return {
            "type": "PEACE", "line": line_no, "bot": bot,
            "t": int(m.group(1)), "kind": "peace_vote", "teamLandPct": float(m.group(2)),
            "clean_line": f"[{bot}] {sanitize_log_line(body)}",
        }

    m = RE_SLOW.match(body)
    if m:
        return {
            "type": "SLOW", "line": line_no, "bot": bot,
            "t": int(m.group(1)), "ms": float(m.group(2)), "maxMs": float(m.group(3)),
            "clean_line": f"[{bot}] {sanitize_log_line(body)}",
        }

    if body.startswith("ERROR: Strategy"):
        return {
            "type": "ERROR", "line": line_no, "bot": bot, "t": None, "msg": body,
            "clean_line": f"[{bot}] {body}",
        }

    return None


def extract_cohort_segments(cohort_prefix: str, squad_label: str, log_paths: list[str], res_path: str, replay_dir: str | None):
    res_rows = []
    with open(res_path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if not line.strip():
                continue
            r = json.loads(line)
            r["_idx"] = i
            r["_bot_clean"] = clean_bot_name(r.get("bot", ""))
            r["_t0"] = t0_ms(r.get("game", ""))
            r["_seeded"] = len(r.get("humans") or [])
            res_rows.append(r)

    by_key = defaultdict(list)
    for r in res_rows:
        by_key[(r["_bot_clean"], r.get("place"), r.get("peak"), r.get("result"))].append(r)

    segs = []
    cur = None
    line_no = 0
    for p in log_paths:
        if not os.path.exists(p):
            continue
        op = gzip.open if p.endswith(".gz") else open
        with op(p, "rt", encoding="utf-8", errors="replace") as f:
            for raw_line in f:
                line_no += 1
                ev = parse_in_game_line(line_no, raw_line)
                if ev is None:
                    continue
                if ev["type"] == "INIT":
                    if (
                        cur is None
                        or cur["seed"] != ev["mapSeed"]
                        or cur["seededPlayers"] != ev["seededPlayers"]
                        or (cur["results_count"] > 0 and cur["ticks_count"] > 0)
                    ):
                        if cur is None or cur["seed"] != ev["mapSeed"] or cur["seededPlayers"] != ev["seededPlayers"]:
                            cur = {
                                "mode": ev["mode"],
                                "map": ev["map"],
                                "seed": ev["mapSeed"],
                                "seededPlayers": ev["seededPlayers"],
                                "events": [],
                                "ticks_count": 0,
                                "results_count": 0,
                                "matched_rows": [],
                                "replay_strs": [],
                                "replay_files": [],
                            }
                            segs.append(cur)
                if cur is None:
                    continue
                if ev["type"] == "REPLAY_STR":
                    cur["replay_strs"].append(ev["replay"])
                    continue
                if ev["type"] == "REPLAY_REF":
                    cur["replay_files"].append(ev["file"])
                    continue
                cur["events"].append(ev)
                if ev["type"] == "TICK":
                    cur["ticks_count"] += 1
                elif ev["type"] == "RESULT":
                    cur["results_count"] += 1
                    cands = by_key.get((ev["bot"], ev["place"], ev["peak"], ev["result"]), [])
                    for c in cands:
                        if not c.get("_used"):
                            c["_used"] = True
                            cur["matched_rows"].append(c)
                            break

    valid_segs = [s for s in segs if s["ticks_count"] > 0 and len(s["matched_rows"]) >= 3]
    return valid_segs, res_rows


def write_csv(path: str, header: list[str], rows: list[list]):
    with open(path, "w", newline="", encoding="utf-8") as f:
        cw = csv.writer(f)
        cw.writerow(header)
        for r in rows:
            cw.writerow(["" if v is None else v for v in r])


def build_bundle(match_id: str, cohort: str, seg: dict, replay_dir: str | None, split_name: str, out_dir: str) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    stories_dir = os.path.join(out_dir, "stories")
    os.makedirs(stories_dir, exist_ok=True)

    evs = seg["events"]
    rows = sorted(seg["matched_rows"], key=lambda r: r["_idx"])

    # Deduplicate matched rows by bot name (keep latest tick)
    by_bot_row = {}
    for r in rows:
        b = r["_bot_clean"]
        if b not in by_bot_row or r.get("tick", 0) >= by_bot_row[b].get("tick", 0):
            by_bot_row[b] = r
    rows = list(by_bot_row.values())

    bots_set = sorted({e["bot"] for e in evs if e.get("bot")} | {r["_bot_clean"] for r in rows})
    ids_map = {}
    for e in evs:
        if e["type"] == "INIT" and e.get("bot"):
            ids_map[e["bot"]] = e["me"]
    for r in rows:
        b = r["_bot_clean"]
        if b not in ids_map and r.get("me") and r["me"].get("id") is not None:
            ids_map[b] = r["me"]["id"]
    id2bot = {v: k for k, v in ids_map.items() if v is not None}

    # 1. Write in_game.log
    with open(os.path.join(out_dir, "in_game.log"), "w", encoding="utf-8") as f:
        for e in evs:
            if e.get("clean_line"):
                f.write(f"{e['line']}\t{e['clean_line']}\n")

    # 2. Write traj.csv
    ticks = [e for e in evs if e["type"] == "TICK"]
    write_csv(
        os.path.join(out_dir, "traj.csv"),
        ["bot", "t", "terr", "pct", "bal", "dens", "nb", "neut", "cmds", "boats", "avgMs", "maxMs", "skip", "line"],
        [[e["bot"], e["t"], e["terr"], e["pct"], e["bal"], e["dens"], e["nb"], e["neut"], e["cmds"], e["boats"], e["avgMs"], e["maxMs"], e["skip"], e["line"]] for e in ticks],
    )

    # 3. Write opening.csv
    openings = [e for e in evs if e["type"] == "OPENING"]
    write_csv(
        os.path.join(out_dir, "opening.csv"),
        ["bot", "t", "cyc", "rings", "spend", "bal", "terr", "line"],
        [[e["bot"], e["t"], e["cyc"], e["rings"], e["spend"], e["bal"], e["terr"], e["line"]] for e in openings],
    )

    # 4. Write spawn.csv
    spawns = [e for e in evs if e["type"] == "SPAWN"]
    write_csv(
        os.path.join(out_dir, "spawn.csv"),
        ["bot", "me", "slot", "role", "x", "y", "bossDist", "minAllyDist", "voronoi", "line"],
        [[e["bot"], e["me"], e["slot"], e["role"], e["x"], e["y"], e["bossDist"], e["minAllyDist"], e["voronoi"], e["line"]] for e in spawns],
    )

    # 5. Write events.csv & audit whether DONATE/DISPATCH actually reduced donor balance
    # For each bot, index its DONATE/DISPATCH events in chronological order to check if consecutive myBal increased (indicating quota/cap rejection!)
    act_evs = [e for e in evs if e["type"] in ("DONATE", "DISPATCH", "ASSIST", "INTERCEPT", "PEACE")]
    bot_transfers = defaultdict(list)
    for e in act_evs:
        if e["type"] in ("DONATE", "DISPATCH"):
            bot_transfers[e["bot"]].append(e)

    rejected_transfer_count = 0
    total_transfer_count = 0
    for b, tlist in bot_transfers.items():
        for i, cur_e in enumerate(tlist):
            total_transfer_count += 1
            cur_e["likelyRejected"] = False
            if i + 1 < len(tlist):
                nxt_e = tlist[i + 1]
                dt = nxt_e["t"] - cur_e["t"]
                # If another transfer happens within 35 ticks and myBal did not decrease by at least 4% (even after ~2-3 interest ticks), the transfer was rejected by quota/cap!
                if 0 < dt <= 35 and nxt_e["myBal"] >= cur_e["myBal"] * 0.98:
                    cur_e["likelyRejected"] = True
                    rejected_transfer_count += 1

    ev_rows = []
    for e in act_evs:
        ev_rows.append([
            e["type"], e["t"], e["bot"], e.get("kind"), e.get("pct"),
            e.get("target"), e.get("targetName"), e.get("boxedIn"),
            e.get("myBal"), e.get("dMe"), e.get("dAlly"),
            e.get("ally"), e.get("boatId"), e.get("boatTroops"),
            e.get("likelyRejected"), e["line"],
        ])
    write_csv(
        os.path.join(out_dir, "events.csv"),
        ["type", "t", "bot", "kind", "pct", "target", "targetName", "boxedIn", "myBal", "dMe", "dAlly", "ally", "boatId", "boatTroops", "likelyRejected", "line"],
        ev_rows,
    )

    # 6. Write sanitized results.csv & results.json
    land = rows[0]["land"] if rows else 0
    seeded_count = rows[0]["_seeded"] if rows else seg["seededPlayers"]
    t0 = min((r["_t0"] for r in rows if r["_t0"] > 0), default=0)

    clean_res_list = []
    res_csv_rows = []
    for r in sorted(rows, key=lambda x: x.get("tick", 0)):
        team = r.get("team") or {}
        item = {
            "bot": r["_bot_clean"],
            "meId": (r.get("me") or {}).get("id"),
            "event": r.get("event"),
            "result": r.get("result"),
            "tick": r.get("tick"),
            "seconds": r.get("seconds"),
            "place": r.get("place"),
            "alivePlayers": r.get("alivePlayers"),
            "territory": r.get("territory"),
            "lastTerritory": r.get("lastTerritory"),
            "lastRank": r.get("lastRank"),
            "peak": r.get("peak"),
            "land": r.get("land"),
            "balance": r.get("balance"),
            "sent": r.get("sent"),
            "accepted": r.get("accepted"),
            "teamMine": team.get("mine"),
            "teamBest": team.get("best"),
            "teamTotals": team.get("totals"),
            "seededPlayers": r["_seeded"],
            "at": r.get("at"),
        }
        clean_res_list.append(item)
        res_csv_rows.append([
            item["bot"], item["meId"], item["event"], item["result"], item["tick"], item["seconds"],
            item["place"], item["alivePlayers"], item["territory"], item["lastTerritory"], item["lastRank"],
            item["peak"], item["land"], item["balance"], item["sent"], item["accepted"],
            item["teamMine"], item["teamBest"],
            json.dumps(item["teamTotals"], separators=(",", ":")) if item["teamTotals"] else "",
            item["seededPlayers"], item["at"],
        ])

    with open(os.path.join(out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(clean_res_list, f, indent=2)
    write_csv(
        os.path.join(out_dir, "results.csv"),
        ["bot", "meId", "event", "result", "tick", "seconds", "place", "alivePlayers", "territory", "lastTerritory", "lastRank", "peak", "land", "balance", "sent", "accepted", "teamMine", "teamBest", "teamTotals", "seededPlayers", "at"],
        res_csv_rows,
    )

    # 7. Build timeline.csv & timeline.txt
    by_t = defaultdict(dict)
    for e in ticks:
        by_t[e["t"]][e["bot"]] = e

    tl_rows = []
    boxed_high_dens_ticks = 0
    for t in sorted(by_t):
        snap = by_t[t]
        terr_sum = bal_sum = 0
        alive_cnt = 0
        cells = []
        for b in bots_set:
            r = snap.get(b)
            if r:
                tr, bl = r["terr"], r["bal"]
                terr_sum += tr
                bal_sum += bl
                if tr > 0:
                    alive_cnt += 1
                if r["nb"] == 0 and r["neut"] == 0 and r["dens"] >= 95 and t >= 1500:
                    boxed_high_dens_ticks += 1
                cells += [tr, bl, r["dens"], r["nb"], r["neut"]]
            else:
                cells += ["", "", "", "", ""]
        share = round(terr_sum / max(1, land), 5) if land else 0.0
        sq_dens = round(bal_sum / max(1, terr_sum), 2)
        tl_rows.append([t, alive_cnt, terr_sum, share, bal_sum, sq_dens] + cells)

    tl_hdr = ["t", "alive", "squadTerr", "squadShare", "squadBal", "squadDens"] + [f"{b}_{c}" for b in bots_set for c in ("terr", "bal", "dens", "nb", "neut")]
    write_csv(os.path.join(out_dir, "timeline.csv"), tl_hdr, tl_rows)

    L = []
    L.append(f"matchId={match_id} cohort={cohort} land={land} seededPlayers={seeded_count}")
    L.append("deaths/exit ticks: " + ", ".join(f"{r['bot']}@{r['tick']}({r['event']}:{r['result']})" for r in clean_res_list))
    L.append("")
    L.append("== snapshots (HL-TICK every 90 ticks) ==")
    L.append("t\talive\tsqTerr\tsqShare%\tsqBal\tsqDens\t| " + "\t".join(f"{b}(terr/bal/dens/nb/neut)" for b in bots_set))
    for row in tl_rows:
        t, alive_cnt, terr_sum, share, bal_sum, sq_dens = row[:6]
        cells = []
        for i in range(len(bots_set)):
            c = row[6 + 5 * i : 11 + 5 * i]
            cells.append("-" if c[0] == "" else f"{c[0]}/{c[1]}/{c[2]}/{c[3]}/{c[4]}")
        L.append(f"{t}\t{alive_cnt}\t{terr_sum}\t{100 * share:.2f}\t{bal_sum}\t{sq_dens}\t| " + "\t".join(cells))
    L.append("")
    L.append("== whole-team land at each result tick (team.totals; key 0 = unaligned AI) ==")
    L.append("tick\tbot\tevent\tmine\tbest\ttotals(share% of land)\tsumAll%\tourTeamRank")
    for r in clean_res_list:
        tot = r["teamTotals"]
        if not tot:
            L.append(f"{r['tick']}\t{r['bot']}\t{r['event']}\t-\t-\t(team=null)")
            continue
        mine = str(r["teamMine"])
        real = {k: v for k, v in tot.items() if k != "0"}
        rank = 1 + sum(1 for k, v in real.items() if v > real.get(mine, 0))
        s = " ".join(f"T{k}={v}({100 * v / max(1, land):.1f}%)" for k, v in sorted(tot.items(), key=lambda kv: int(kv[0])))
        L.append(f"{r['tick']}\t{r['bot']}\t{r['event']}\t{mine}\t{r['teamBest']}\t{s}\t{100 * sum(tot.values()) / max(1, land):.1f}\t{rank}/{len(real)}")
    with open(os.path.join(out_dir, "timeline.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")

    # 8. Build per-bot stories/story_<bot>.txt and count DROP30 events
    drop30_events = []
    for bot in bots_set:
        b_ticks = [e for e in ticks if e["bot"] == bot]
        my_id = ids_map.get(bot)
        b_evs = []
        for e in openings:
            if e["bot"] == bot:
                b_evs.append((e["t"], f"OPEN({e['t']},{e['spend']}/{e['bal']})"))
        for e in act_evs:
            et = e["t"]
            if e["type"] in ("DONATE", "DISPATCH"):
                amt = round(e["pct"] / 1024.0 * e["myBal"])
                rej_tag = "[REJ?]" if e.get("likelyRejected") else ""
                if e["bot"] == bot:
                    to_name = id2bot.get(e["target"], e.get("targetName") or str(e["target"]))
                    b_evs.append((et, f"{e['type'][:3]}>{to_name}({et},{e['kind'][:7]},pct={e['pct']},~{amt}){rej_tag}"))
                if my_id is not None and e.get("target") == my_id:
                    b_evs.append((et, f"RCV<{e['bot']}({et},~{amt}){rej_tag}"))
            elif e["type"] == "ASSIST":
                if e["bot"] == bot:
                    b_evs.append((et, f"AST({et},e={e['target']},for={e.get('allyName') or e.get('ally')})"))
                if my_id is not None and e.get("ally") == my_id:
                    b_evs.append((et, f"AST<{e['bot']}({et},e={e['target']})"))
            elif e["type"] == "INTERCEPT" and e["bot"] == bot:
                b_evs.append((et, f"INT({et},pct={e['pct']},boat={e['boatId']},tr={e['boatTroops']})"))
            elif e["type"] == "PEACE" and e["bot"] == bot:
                b_evs.append((et, f"PEACE({et},{e['teamLandPct']}%)"))
        b_evs.sort(key=lambda x: x[0])

        SL = []
        r0 = next((r for r in clean_res_list if r["bot"] == bot), None)
        if r0:
            SL.append(
                f"# {bot} id={my_id} result={r0['result']} event={r0['event']} tick={r0['tick']} "
                f"place={r0['place']} peak={r0['peak']} lastTerr={r0['lastTerritory']} bal={r0['balance']} "
                f"sent={r0['sent']} accepted={r0['accepted']} teamMine={r0['teamMine']}"
            )
        SL.append("t\tterr\tdTerr\tbal\tdBal\tdBal%\tdens\tnb\tneut\tdCmds\tdBoats\tflags\t| events in (prev,t]")
        prev = None
        for r in b_ticks:
            t, terr, bal = r["t"], r["terr"], r["bal"]
            flags = []
            if prev is None:
                SL.append(f"{t}\t{terr}\t\t{bal}\t\t\t{r['dens']}\t{r['nb']}\t{r['neut']}\t\t\t\t| (first snapshot; cmds={r['cmds']} boats={r['boats']})")
            else:
                pt, pterr, pbal = prev["t"], prev["terr"], prev["bal"]
                dbal = bal - pbal
                pctb = 100.0 * dbal / pbal if pbal > 0 else 0.0
                if t - pt != 90:
                    flags.append("GAP")
                if pbal > 0 and dbal <= -0.30 * pbal:
                    flags.append("DROP30")
                    drop30_events.append({"bot": bot, "t0": pt, "t1": t, "bal0": pbal, "bal1": bal, "dropPct": round(-pctb, 1), "terr0": pterr, "terr1": terr})
                seg_s = [x[1] for x in b_evs if pt < x[0] <= t]
                SL.append(
                    f"{t}\t{terr}\t{terr - pterr:+d}\t{bal}\t{dbal:+d}\t{pctb:+.0f}%\t{r['dens']}\t{r['nb']}\t{r['neut']}\t"
                    f"{r['cmds'] - prev['cmds']}\t{r['boats'] - prev['boats']}\t{','.join(flags)}\t| {' '.join(seg_s)}"
                )
            prev = r
        with open(os.path.join(stories_dir, f"story_{bot}.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(SL) + "\n")

    # 9. Check replay availability
    has_replay = False
    replay_out_path = os.path.join(out_dir, "replay.txt")
    if seg["replay_strs"]:
        longest = max(seg["replay_strs"], key=len)
        if len(longest) > 100:
            with open(replay_out_path, "w", encoding="utf-8") as f:
                f.write(longest + "\n")
            has_replay = True
    elif seg["replay_files"] and replay_dir:
        for rf in seg["replay_files"]:
            cand = os.path.join(replay_dir, rf)
            if os.path.exists(cand):
                shutil.copyfile(cand, replay_out_path)
                has_replay = True
                break

    # 10. Compute team metrics and card.json
    mines = Counter(r["teamMine"] for r in clean_res_list if r["teamMine"] is not None)
    primary_team = mines.most_common(1)[0][0] if mines else None
    distinct_teams = len(mines)
    t_nominal = (seg["mode"] + 2) if seg["mode"] < 7 else 2
    t_obs = max((len([k for k in (r["teamTotals"] or {}).keys() if k != "0"]) for r in clean_res_list), default=t_nominal)
    actual_teams = max(2, t_obs)

    primary_team_won = any(r["result"] == "won" and r["teamMine"] == primary_team for r in clean_res_list)
    any_bot_won = any(r["result"] == "won" for r in clean_res_list)
    end_tick = max((r["tick"] or 0 for r in clean_res_list), default=0)

    # Peak squad share from timeline
    peak_squad_share = max((row[3] for row in tl_rows), default=0.0)
    # Final team share at latest result with teamTotals
    with_tot = [r for r in clean_res_list if r["teamTotals"]]
    our_final_share = 0.0
    winner_team = None
    max_team_share_seen = 0.0
    for r in with_tot:
        tot = r["teamTotals"]
        if primary_team is not None and str(primary_team) in tot and land > 0:
            sh = tot[str(primary_team)] / land
            if sh > max_team_share_seen:
                max_team_share_seen = sh
    if with_tot and land > 0:
        last_r = max(with_tot, key=lambda x: x["tick"] or 0)
        tot = last_r["teamTotals"]
        winner_team = last_r["teamBest"]
        if primary_team is not None and str(primary_team) in tot:
            our_final_share = round(tot[str(primary_team)] / land, 4)

    anomalies = {
        "drop30Count": len(drop30_events),
        "drop30Events": drop30_events[:30],
        "totalTransfers": total_transfer_count,
        "likelyRejectedTransfers": rejected_transfer_count,
        "boxedHighDensSnapshots": boxed_high_dens_ticks,
        "strategyErrors": sum(1 for e in evs if e["type"] == "ERROR"),
        "slowTicks": sum(1 for e in evs if e["type"] == "SLOW"),
        "teamSplit": distinct_teams > 1,
    }
    with open(os.path.join(out_dir, "anomalies.json"), "w", encoding="utf-8") as f:
        json.dump(anomalies, f, indent=2)

    card = {
        "matchId": match_id,
        "cohort": cohort,
        "split": split_name,
        "timeUtc": iso_utc(t0),
        "timestampMs": t0,
        "squadBots": len(clean_res_list),
        "mapId": seg["map"],
        "mapSeed": seg["seed"],
        "mapLand": land,
        "mode": seg["mode"],
        "nominalTeams": t_nominal,
        "actualTeams": actual_teams,
        "baseWinExpectation": round(1.0 / actual_teams, 4),
        "seededPlayers": seeded_count,
        "ourPrimaryTeam": primary_team,
        "distinctSquadTeams": distinct_teams,
        "teamSplitCounts": {str(k): v for k, v in sorted(mines.items())},
        "outcome": {
            "primaryTeamWon": primary_team_won,
            "anyBotWon": any_bot_won,
            "resultLabel": "won" if primary_team_won else ("split_straggler_won" if any_bot_won else "lost"),
            "winnerTeam": winner_team,
            "endTick": end_tick,
            "peakSquadLandShare": round(peak_squad_share, 4),
            "peakPrimaryTeamShareSeen": round(max_team_share_seen, 4),
            "ourFinalTeamShare": our_final_share,
        },
        "dataCompleteness": {
            "results": True,
            "inGameLog": True,
            "replay": has_replay,
            "tickSnapshots": len(tl_rows),
        },
        "anomaliesSummary": {
            "drop30Count": len(drop30_events),
            "totalTransfers": total_transfer_count,
            "likelyRejectedTransfers": rejected_transfer_count,
            "boxedHighDensSnapshots": boxed_high_dens_ticks,
            "strategyErrors": anomalies["strategyErrors"],
            "teamSplit": distinct_teams > 1,
        },
    }
    with open(os.path.join(out_dir, "card.json"), "w", encoding="utf-8") as f:
        json.dump(card, f, indent=2)

    return card


def main():
    if os.path.exists(OUT_ROOT):
        shutil.rmtree(OUT_ROOT)
    os.makedirs(BUNDLES_DISC, exist_ok=True)
    os.makedirs(BUNDLES_VAL, exist_ok=True)
    os.makedirs(SRC_DIR, exist_ok=True)

    manifest = []

    # 1. Cohort G (8-bot batch from c116-winrate/data)
    g_segs, _ = extract_cohort_segments(
        "G", "squad8",
        ["/tmp/c116-jvfoedfve/c116-winrate/data/G01-G09-squad.log"],
        "/tmp/c116-jvfoedfve/c116-winrate/data/tsb-team-results.jsonl",
        "/tmp/c116-jvfoedfve/c116-winrate/replays",
    )
    for i, s in enumerate(g_segs):
        mid = f"G{i:02d}"
        card = build_bundle(mid, "squad8", s, "/tmp/c116-jvfoedfve/c116-winrate/replays", "discovery", os.path.join(BUNDLES_DISC, mid))
        manifest.append(card)

    # 2. Cohort A (10-bot squad from d3-raw-export/c116)
    a_segs, _ = extract_cohort_segments(
        "A", "squad10",
        [
            "/tmp/c116-jvfoedfve/d3-raw-export/c116/tsb-apex-squad.log.part1.gz",
            "/tmp/c116-jvfoedfve/d3-raw-export/c116/tsb-apex-squad.log.part2.gz",
        ],
        "/tmp/c116-jvfoedfve/d3-raw-export/c116/tsb-team-results.jsonl",
        "/tmp/c116-jvfoedfve/d3-raw-export/c116/replays",
    )
    for i, s in enumerate(a_segs, 1):
        mid = f"A{i:03d}"
        # Deterministic stratified holdout: every 4th match (i % 4 == 0) is validation
        split_name = "validation" if (i % 4 == 0) else "discovery"
        target_root = BUNDLES_VAL if split_name == "validation" else BUNDLES_DISC
        card = build_bundle(mid, "squad10", s, "/tmp/c116-jvfoedfve/d3-raw-export/c116/replays", split_name, os.path.join(target_root, mid))
        manifest.append(card)

    # 3. Cohort B (20-bot squad from d3-raw-export/c110)
    b_segs, _ = extract_cohort_segments(
        "B", "squad20",
        [
            "/tmp/c116-jvfoedfve/d3-raw-export/c110/tsb-team-squad.pre-reboot.log",
            "/tmp/c116-jvfoedfve/d3-raw-export/c110/tsb-team-squad.log.gz",
        ],
        "/tmp/c116-jvfoedfve/d3-raw-export/c110/tsb-team-results.jsonl",
        "/tmp/c116-jvfoedfve/d3-raw-export/c110/replays",
    )
    for i, s in enumerate(b_segs, 1):
        mid = f"B{i:03d}"
        split_name = "validation" if (i % 4 == 0) else "discovery"
        target_root = BUNDLES_VAL if split_name == "validation" else BUNDLES_DISC
        card = build_bundle(mid, "squad20", s, "/tmp/c116-jvfoedfve/d3-raw-export/c110/replays", split_name, os.path.join(target_root, mid))
        manifest.append(card)

    # Mark cross-matches (same timestampMs within 15s and same mapLand)
    for c1 in manifest:
        for c2 in manifest:
            if c1["matchId"] != c2["matchId"] and c1["cohort"] != c2["cohort"]:
                if c1["mapLand"] == c2["mapLand"] and abs(c1["timestampMs"] - c2["timestampMs"]) <= 15000:
                    c1["sameMatchPeer"] = {
                        "peerMatchId": c2["matchId"],
                        "peerCohort": c2["cohort"],
                        "peerPrimaryTeam": c2["ourPrimaryTeam"],
                        "samePrimaryTeam": c1["ourPrimaryTeam"] == c2["ourPrimaryTeam"],
                    }
                    # Update card.json on disk
                    root_d = BUNDLES_VAL if c1["split"] == "validation" else BUNDLES_DISC
                    cp = os.path.join(root_d, c1["matchId"], "card.json")
                    with open(cp, "w", encoding="utf-8") as f:
                        json.dump(c1, f, indent=2)

    disc_manifest = [c for c in manifest if c["split"] == "discovery"]
    val_manifest = [c for c in manifest if c["split"] == "validation"]

    with open(os.path.join(OUT_ROOT, "manifest.jsonl"), "w", encoding="utf-8") as f:
        for c in disc_manifest:
            f.write(json.dumps(c) + "\n")

    with open(os.path.join(OUT_ROOT, "manifest_all_internal.jsonl"), "w", encoding="utf-8") as f:
        for c in manifest:
            f.write(json.dumps(c) + "\n")

    print(f"Built {len(manifest)} full bundles: discovery={len(disc_manifest)}, validation={len(val_manifest)}")
    print(f"  G (squad8):  {sum(1 for c in manifest if c['cohort']=='squad8')}")
    print(f"  A (squad10): {sum(1 for c in manifest if c['cohort']=='squad10')} (disc={sum(1 for c in disc_manifest if c['cohort']=='squad10')}, val={sum(1 for c in val_manifest if c['cohort']=='squad10')})")
    print(f"  B (squad20): {sum(1 for c in manifest if c['cohort']=='squad20')} (disc={sum(1 for c in disc_manifest if c['cohort']=='squad20')}, val={sum(1 for c in val_manifest if c['cohort']=='squad20')})")
    print(f"  With replay: {sum(1 for c in manifest if c['dataCompleteness']['replay'])}")


if __name__ == "__main__":
    main()
