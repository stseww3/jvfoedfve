#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
c136lib.py — R10（裁判）读取 /agent/repos/c136-data 对局包的公共函数。只依赖标准库。

约定：
  - 只读 /agent/repos/c136-data/；任何脚本都不写这个目录。
  - 发现集 123 局在 bundles/，验证集 37 局在 validation_bundles/。
    load_cards('discovery') 只给发现集；load_cards('all') 给 160 局（仅 R10 与 c136 可用）。
  - 「局」是独立单位。同一个房间里同时有 10 号编队和 20 号编队时（card.sameMatchPeer），
    两张卡描述的是同一局，统计时要去重或显式处理（见 room_key）。
"""

from __future__ import annotations

import csv
import json
import os

DATA = "/agent/repos/c136-data"


def load_cards(which: str = "all") -> list[dict]:
    """which: 'all'（160 局）| 'discovery'（123 局）| 'validation'（37 局）"""
    path = os.path.join(DATA, "manifest_all_internal.jsonl")
    cards = [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]
    if which == "all":
        return cards
    if which in ("discovery", "validation"):
        return [c for c in cards if c["split"] == which]
    raise ValueError(which)


def bundle_dir(card_or_id) -> str:
    if isinstance(card_or_id, dict):
        mid, split = card_or_id["matchId"], card_or_id.get("split")
        if split == "validation":
            return os.path.join(DATA, "validation_bundles", mid)
        if split == "discovery":
            return os.path.join(DATA, "bundles", mid)
    else:
        mid = card_or_id
    for sub in ("bundles", "validation_bundles"):
        p = os.path.join(DATA, sub, mid)
        if os.path.isdir(p):
            return p
    raise FileNotFoundError(mid)


def load_json(card, name: str):
    with open(os.path.join(bundle_dir(card), name), encoding="utf-8") as f:
        return json.load(f)


def load_csv(card, name: str) -> list[dict]:
    with open(os.path.join(bundle_dir(card), name), encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_results(card) -> list[dict]:
    """results.json：每个号一行结算（event=died/end/left；teamTotals 可能为 None）。"""
    return load_json(card, "results.json")


def _num(x, typ=float):
    if x is None or x == "":
        return None
    try:
        return typ(x)
    except ValueError:
        return typ(float(x))


def load_traj(card) -> list[dict]:
    """traj.csv 的每一行转成数值：bot,t,terr,pct,bal,dens,nb,neut,cmds,boats,avgMs,maxMs,skip,line"""
    out = []
    for r in load_csv(card, "traj.csv"):
        out.append({
            "bot": r["bot"], "t": int(r["t"]), "terr": int(r["terr"]), "pct": float(r["pct"]),
            "bal": int(r["bal"]), "dens": float(r["dens"]), "nb": int(r["nb"]), "neut": int(r["neut"]),
            "cmds": int(r["cmds"]), "boats": int(r["boats"]),
            "avgMs": _num(r.get("avgMs")), "maxMs": _num(r.get("maxMs")),
            "skip": _num(r.get("skip"), int), "line": int(r["line"]),
        })
    return out


def traj_by_bot(card) -> dict[str, list[dict]]:
    by = {}
    for r in load_traj(card):
        by.setdefault(r["bot"], []).append(r)
    for b in by:
        by[b].sort(key=lambda x: (x["t"], x["line"]))
    return by


def traj_by_t(card) -> dict[int, dict[str, dict]]:
    """{t: {bot: 行}}。同一号同一拍有重复行时保留日志里靠后的一行。"""
    by = {}
    for r in load_traj(card):
        by.setdefault(r["t"], {})[r["bot"]] = r
    return by


def load_events(card) -> list[dict]:
    """events.csv：DONATE / DISPATCH / ASSIST / INTERCEPT / PEACE。数值列转 int，likelyRejected 转 bool/None。"""
    out = []
    for r in load_csv(card, "events.csv"):
        e = dict(r)
        for k in ("t", "pct", "target", "myBal", "dMe", "dAlly", "ally", "boatId", "boatTroops", "line"):
            e[k] = _num(r.get(k), int)
        lr = r.get("likelyRejected")
        e["likelyRejected"] = True if lr == "True" else (False if lr == "False" else None)
        bi = r.get("boxedIn")
        e["boxedIn"] = True if bi == "True" else (False if bi == "False" else None)
        out.append(e)
    return out


def load_opening(card) -> list[dict]:
    out = []
    for r in load_csv(card, "opening.csv"):
        out.append({"bot": r["bot"], **{k: int(r[k]) for k in ("t", "cyc", "rings", "spend", "bal", "terr", "line")}})
    return out


def load_spawn(card) -> list[dict]:
    out = []
    for r in load_csv(card, "spawn.csv"):
        out.append({"bot": r["bot"], "role": r["role"],
                    **{k: int(r[k]) for k in ("me", "slot", "x", "y", "bossDist", "minAllyDist", "voronoi", "line")}})
    return out


def team_bucket(t: int) -> str:
    """任务卡规定的队伍数分层：T=2、T=3~4、T>=5。"""
    if t <= 2:
        return "T=2"
    if t <= 4:
        return "T=3-4"
    return "T>=5"


def room_key(card) -> str:
    """
    同一个房间的键。两张卡互为 sameMatchPeer 时返回相同的键（两个 matchId 排序后用 '+' 连接），
    否则就是自己的 matchId。
    """
    peer = card.get("sameMatchPeer")
    if peer:
        return "+".join(sorted([card["matchId"], peer["peerMatchId"]]))
    return card["matchId"]


def nearest_snapshot(ts: list[int], target: int, tol: int = 45):
    """在快照拍号列表里找离 target 最近的一个；差距超过 tol 返回 None。"""
    best = None
    for t in ts:
        if best is None or abs(t - target) < abs(best - target):
            best = t
    if best is None or abs(best - target) > tol:
        return None
    return best
