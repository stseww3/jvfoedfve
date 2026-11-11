#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rooms.py — R10（裁判）的对局包取证脚本：把每个对局包还原成「号 → 房间 → 队伍 → 结局」。

为什么需要它（详见 reports/BASELINE-FULL.md §1、§6、§7）：
  1. B 组的号在一局之内会改名（日志行首的名字按墙钟轮换），按名字拼出来的轨迹是断的；
  2. 一个对局包里可能混了两到三个房间（大厅拆房，或前后两场）；
  3. 卡片的 actualTeams / primaryTeamWon 在没有 team.totals、或者我方号先死/先离场时不可靠；
  4. 同一个物理房间可能同时出现在两个包里（一个 squad10 包、一个 squad20 包）。

做法（全部只读 /agent/repos/c136-data/）：
  A. 名字链：把 traj.csv 里的每个名字看成一段，按「上一段最后一拍 → 下一段第一拍」的指纹接续
     （maxMs 单调不减、cmds/boats 单调不减、拍号相邻、领土接近）串成同一个号；只有 INIT、没有 TICK 的名字也各成一条链。
     结算行挂到链上的顺序：① 按名字；② 按 meId == INIT 的 me 且 seededPlayers 相同、候选唯一
     （left 行的拍号是陈旧的，只能这样挂）；③ 按「结算拍紧跟某条链的末尾 + sent>=cmds + peak>=链内最大领土」；
     ④ 都挂不上的记为 orphan。
     校验：用 ① 或 ③ 挂上的结算行，其 meId 必须等于链首 INIT 的 me（两者都有时）。
  B. 房间：结算行按 (land, seededPlayers) 分组，组内按开局墙钟（at − seconds）做单链聚类，
     相邻间隔超过 START_LINK_S 秒就切开；落单的结算行如果和相邻簇间隔不到 3 秒、座位号不冲突、
     且拍钟 T0（at − 0.056×tick）与该簇中位数相差不超过 T0_RESCUE_S 秒，则并回该簇。
     没有结算行的号按 INIT 的 (mode, map, mapSeed, seeded) 归房；仍分不开的按日志行号上的拍号相位归房。
  C. 队伍：结算行的 team.mine；带标签的编队（squad8 / squad10）同一房间的号取房间里观察到的那个队；
     squad20 没有结算队号的号，用捐款关系（HL-DONATE / HL-DISPATCH，引擎只允许捐给队友）并入已知队伍。
     HL-ASSIST 的 ally 关系不用于推断队伍（c110 会替不同引擎队的同编队号出手，见报告 §7.1）。
  D. 结局：有 end 行 → 以最后一条带 team.totals 的 end 行的 team.best 为胜方；没有 → 按最后一次看到的各队份额
     给出 推定胜 / 推定负 / 未知。队伍数优先用 team.totals 里见过的队号数，不足时用引擎规则。
  E. 物理房间：跨包把 (land, seeded) 相同、开局墙钟相差不超过 START_LINK_S 秒、座位号不冲突的房间并成一个物理房间，
     用所有成员包的结算行重新判定队伍数和结局。

用法：
  python3 rooms.py build            # 生成 out/rooms/ 下的 4 个文件
  python3 rooms.py show B009        # 打印某一个包的还原结果
  python3 rooms.py selfcheck        # 打印名字链的校验统计
"""

from __future__ import annotations

import datetime
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from c136lib import (DATA, bundle_dir, load_cards, load_events, load_results,  # noqa: E402
                     load_traj)

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out", "rooms")

RE_INIT = re.compile(r"^(\d+)\t\[([^\]]+)\] \[HL-GAME-INIT\] mode=(-?\d+) map=(-?\d+) mapSeed=(-?\d+) seeded=(\d+) me=(-?\d+)")
RE_RESULT = re.compile(r"^(\d+)\t\[RESULT (?:\[(?:Nope|APEX)\]\s*)?([^\]]+)\] result=(\w+) event=(\w+) place=(\d+).*?\bpeak=(\d+) team=")
RE_ASSIST_FOR = re.compile(r"^(\d+)\t\[([^\]]+)\] \[HL-ASSIST\] t=(\d+) .*?-> (?:enemy|target)=(\d+)\((.*?)\)(?: for ally=(\d+)\((.*?)\))?")

START_LINK_S = 1.6        # 同一房间里相邻两条结算行的开局墙钟最多相差这么多秒
T0_RESCUE_S = 0.6         # 落单的结算行并回相邻房间时，拍钟 T0 与该房间中位数最多相差这么多秒
PHASE_GAP_TICKS = 120     # 没有结算行时：同一房间的拍号相位最多相差这么多拍


def _at_s(at: str) -> float:
    return datetime.datetime.strptime(at, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=datetime.timezone.utc).timestamp()


# ----------------------------------------------------------------------------
# 读一个包
# ----------------------------------------------------------------------------

def read_bundle(card: dict) -> dict:
    d = bundle_dir(card)
    inits, result_lines, assists = [], [], []
    with open(os.path.join(d, "in_game.log"), encoding="utf-8") as f:
        for line in f:
            m = RE_INIT.match(line)
            if m:
                inits.append({"line": int(m.group(1)), "name": m.group(2), "mode": int(m.group(3)),
                              "map": int(m.group(4)), "seed": int(m.group(5)), "seeded": int(m.group(6)),
                              "me": int(m.group(7))})
                continue
            m = RE_RESULT.match(line)
            if m:
                result_lines.append({"line": int(m.group(1)), "name": m.group(2).strip(), "result": m.group(3),
                                     "event": m.group(4), "place": int(m.group(5)), "peak": int(m.group(6))})
                continue
            m = RE_ASSIST_FOR.match(line)
            if m:
                assists.append({"line": int(m.group(1)), "name": m.group(2), "t": int(m.group(3)),
                                "enemy": int(m.group(4)), "enemyName": m.group(5),
                                "ally": int(m.group(6)) if m.group(6) else None, "allyName": m.group(7)})
    ticks = defaultdict(list)
    for r in load_traj(card):
        ticks[r["bot"]].append(r)
    for b in ticks:
        ticks[b].sort(key=lambda x: (x["line"]))
    results = load_results(card)
    # 给结算行配上日志行号（按 名字+place+peak+result 匹配；匹配不到则 None）
    used = set()
    for r in results:
        r["_line"] = None
        for i, rl in enumerate(result_lines):
            if i in used:
                continue
            if rl["name"] == r["bot"] and rl["place"] == r["place"] and rl["peak"] == r["peak"] and rl["result"] == r["result"]:
                r["_line"] = rl["line"]
                used.add(i)
                break
        r["_start"] = _at_s(r["at"]) - (r["seconds"] or 0)
    return {"card": card, "inits": inits, "ticks": dict(ticks), "results": results,
            "events": load_events(card), "assists": assists}


# ----------------------------------------------------------------------------
# A. 名字链
# ----------------------------------------------------------------------------

def _link_cost(L: dict, F: dict):
    """上一段最后一行 L → 下一段第一行 F 的接续代价；不可能接续时返回 None。"""
    dt = F["t"] - L["t"]
    if dt <= 0 or dt > 450:
        return None
    if F["line"] <= L["line"]:
        return None
    dc = F["cmds"] - L["cmds"]
    db = F["boats"] - L["boats"]
    if dc < 0 or db < 0 or dc > 80 or db > 25:
        return None
    cost = 1.0 * dc + 3.0 * db + 0.02 * (dt - 90)
    if L.get("maxMs") is not None and F.get("maxMs") is not None:
        dm = F["maxMs"] - L["maxMs"]
        if dm < -1e-6:
            return None
        cost += 10.0 * dm
    if L.get("avgMs") is not None and F.get("avgMs") is not None:
        cost += 100.0 * abs(F["avgMs"] - L["avgMs"])
    cost += 30.0 * abs(math.log((F["terr"] + 100.0) / (L["terr"] + 100.0)))
    return cost


def build_chains(b: dict) -> list[dict]:
    """
    返回链的列表。每条链：
      names        依次用过的名字
      rows         合并后的 TICK 行（按日志行号排序）
      init         链首名字的 INIT 行（没有则 None）
      result       结算行（没有则 None）
      resultHow    'name'（结算名就是链里的名字）| 'tail'（结算名没有 TICK 行，按指纹挂到链尾）| None
      linkCosts    每次接续的代价（越小越确定）
      ambiguous    接续时次优候选与最优候选代价接近的次数
    """
    ticks = b["ticks"]
    names = list(ticks)
    first = {n: ticks[n][0] for n in names}
    last = {n: ticks[n][-1] for n in names}
    starters = [n for n in names if first[n]["t"] <= 180]
    conts = [n for n in names if first[n]["t"] > 180]
    # 所有可能的接续对
    pairs = []
    for n2 in conts:
        for n1 in names:
            if n1 == n2:
                continue
            c = _link_cost(last[n1], first[n2])
            if c is not None:
                pairs.append((c, n1, n2))
    pairs.sort()
    succ, pred, link_cost, amb = {}, {}, {}, Counter()
    best_for = defaultdict(list)
    for c, n1, n2 in pairs:
        best_for[n2].append((c, n1))
    for c, n1, n2 in pairs:
        if n1 in succ or n2 in pred:
            continue
        succ[n1] = n2
        pred[n2] = n1
        link_cost[n2] = c
        alts = [x for x in best_for[n2] if x[1] != n1 and x[1] not in succ]
        if alts and alts[0][0] - c < 8.0:
            amb[n2] += 1
    chains = []
    heads = [n for n in names if n not in pred]
    for h in sorted(heads, key=lambda n: (first[n]["t"], first[n]["line"])):
        seq = [h]
        while seq[-1] in succ:
            seq.append(succ[seq[-1]])
        rows = []
        for n in seq:
            rows.extend(ticks[n])
        rows.sort(key=lambda x: x["line"])
        chains.append({"names": seq, "rows": rows, "init": None, "result": None, "resultHow": None,
                       "linkCosts": [round(link_cost[n], 2) for n in seq[1:]],
                       "ambiguous": sum(amb[n] for n in seq[1:]),
                       "headIsStarter": h in starters})
    # INIT：按名字挂到链（INIT 名字是开局名）
    init_by_name = {}
    for i in b["inits"]:
        init_by_name.setdefault(i["name"], i)
    name_to_chain = {}
    for ch in chains:
        for n in ch["names"]:
            name_to_chain[n] = ch
        if ch["names"][0] in init_by_name:
            ch["init"] = init_by_name[ch["names"][0]]
    # INIT 里有、但没有任何 TICK 行的名字：也算一个号（开局就卡住或很快离场的号）
    for n, i in init_by_name.items():
        if n not in name_to_chain:
            ch = {"names": [n], "rows": [], "init": i, "result": None, "resultHow": None,
                  "linkCosts": [], "ambiguous": 0, "headIsStarter": True}
            chains.append(ch)
            name_to_chain[n] = ch
    # 结算行：先按名字
    pending = []
    for r in b["results"]:
        ch = name_to_chain.get(r["bot"])
        if ch is not None and ch["result"] is None:
            ch["result"] = r
            ch["resultHow"] = "name"
        else:
            pending.append(r)
    # 再按局内号挂：INIT 的 me == 结算行的 meId，且 INIT 的 seeded == 结算行的 seededPlayers，候选唯一。
    # （left 行的 tick 不可靠：它取自页面最后一次刷新的状态，可能比最后一条 TICK 行还早，甚至是 0，
    #   所以这里不用拍号，只用局内号 + 日志行号先后。）
    still = []
    for r in pending:
        cs = []
        for ch in chains:
            if ch["result"] is not None or ch["init"] is None or r["meId"] is None:
                continue
            if ch["init"]["me"] != r["meId"] or ch["init"]["seeded"] != r["seededPlayers"]:
                continue
            if ch["rows"] and r["_line"] is not None and r["_line"] < ch["rows"][-1]["line"]:
                continue
            cs.append(ch)
        if len(cs) == 1:
            cs[0]["result"] = r
            cs[0]["resultHow"] = "meid"
            cs[0]["names"].append(r["bot"])
        else:
            still.append(r)
    pending = still
    # 最后按指纹挂到链尾（结算名没有 TICK 行：改名之后、下一次快照之前就死了/走了）
    cands = []
    for r in pending:
        for ci, ch in enumerate(chains):
            if ch["result"] is not None:
                continue
            if not ch["rows"]:
                continue
            L = ch["rows"][-1]
            dt = (r["tick"] or 0) - L["t"]
            if r["event"] == "left":
                # left 行的 tick 可能是旧值：只要求不比链尾晚太多
                if dt > 450:
                    continue
                dt = max(dt, 0)
            elif dt < 0 or dt > 450:
                continue
            if r["_line"] is not None and r["_line"] < L["line"]:
                continue
            if r["sent"] is not None and r["sent"] < L["cmds"]:
                continue
            mx = max(x["terr"] for x in ch["rows"])
            if r["peak"] is not None and r["peak"] < mx:
                continue
            if ch["init"] is not None and r["meId"] is not None and ch["init"]["me"] != r["meId"]:
                continue
            cost = 0.02 * dt + 0.5 * ((r["sent"] or L["cmds"]) - L["cmds"])
            ref = r["lastTerritory"] if r["event"] == "died" else r["territory"]
            if r["event"] != "died" and ref is not None:
                cost += 30.0 * abs(math.log((ref + 100.0) / (L["terr"] + 100.0)))
            if r["peak"] is not None:
                cost += 5.0 * abs(math.log((r["peak"] + 100.0) / (mx + 100.0)))
            if ch["init"] is not None and r["meId"] is not None:
                cost -= 50.0          # INIT me 与结算 meId 相等：强证据
            cands.append((cost, id(r), ci, r))
    cands.sort(key=lambda x: x[0])
    done_r = set()
    for cost, rid, ci, r in cands:
        ch = chains[ci]
        if rid in done_r or ch["result"] is not None:
            continue
        ch["result"] = r
        ch["resultHow"] = "tail"
        ch["names"].append(r["bot"])
        done_r.add(rid)
    orphans = [r for r in pending if id(r) not in done_r]
    # 没有任何 TICK 行、也挂不到链上的结算行：各自成一条「只有结算」的链
    for r in orphans:
        init = init_by_name.get(r["bot"])
        chains.append({"names": [r["bot"]], "rows": [], "init": init, "result": r, "resultHow": "orphan",
                       "linkCosts": [], "ambiguous": 0, "headIsStarter": init is not None})
    for k, ch in enumerate(chains):
        ch["idx"] = k
        ch["me"] = (ch["init"] or {}).get("me")
        if ch["me"] is None and ch["result"] is not None:
            ch["me"] = ch["result"]["meId"]
        ch["idCheck"] = None
        if ch["init"] is not None and ch["result"] is not None and ch["result"]["meId"] is not None:
            ch["idCheck"] = (ch["init"]["me"] == ch["result"]["meId"])
    return chains


# ----------------------------------------------------------------------------
# B. 房间
# ----------------------------------------------------------------------------

def _phase(ch: dict, ref_rows: list[dict]):
    """
    链 ch 相对参考行集合 ref_rows（同一房间的全部 TICK 行，按行号排序）的拍号相位：
    对 ch 的每一行，在参考集合里按行号线性插值得到「同一时刻参考房间的拍号」，取差的中位数。
    """
    if not ch["rows"] or len(ref_rows) < 2:
        return None
    ls = [r["line"] for r in ref_rows]
    ts = [r["t"] for r in ref_rows]
    import bisect
    diffs = []
    for r in ch["rows"]:
        i = bisect.bisect_left(ls, r["line"])
        if i <= 0 or i >= len(ls):
            continue
        l0, l1 = ls[i - 1], ls[i]
        t0, t1 = ts[i - 1], ts[i]
        tt = t0 if l1 == l0 else t0 + (t1 - t0) * (r["line"] - l0) / (l1 - l0)
        diffs.append(r["t"] - tt)
    if not diffs:
        return None
    diffs.sort()
    return diffs[len(diffs) // 2]


def _tick_clock(r: dict):
    """结算行的「拍钟零点」= 上报墙钟 − 0.056 s × 拍号。只对 died 行可靠（end 行在终局后才报，left 行的拍号可能是旧值）。"""
    if r["event"] != "died" or not r["tick"]:
        return None
    return r["_start"] + r["seconds"] - 0.056 * r["tick"]


def _split_by_start(chs: list[dict]) -> list[list[dict]]:
    """
    同一 (land, seeded) 组里按开局墙钟（at − seconds）分簇：相邻间隔 > START_LINK_S 就另起一簇。
    依据（全部 160 包的相邻间隔分布，见 BASELINE-FULL 的附表）：同房间的间隔几乎都 < 1 s；
    不同房间（大厅被拆成几个 20 人房）的间隔 ≥ 1.9 s。
    补救：只有一个号的簇，如果和相邻簇的开局间隔 < 3 s、号不冲突、且它的拍钟零点与相邻簇 died 行的
    拍钟零点中位数相差 ≤ T0_RESCUE_S，就并回相邻簇（那个号只是页面起得晚，例：B007 的 Cheese）。
    """
    chs = sorted(chs, key=lambda c: c["result"]["_start"])
    clusters = [[chs[0]]]
    for c in chs[1:]:
        if c["result"]["_start"] - clusters[-1][-1]["result"]["_start"] > START_LINK_S:
            clusters.append([c])
        else:
            clusters[-1].append(c)
    changed = True
    while changed and len(clusters) > 1:
        changed = False
        for k, cl in enumerate(clusters):
            if len(cl) != 1:
                continue
            c = cl[0]
            t0 = _tick_clock(c["result"])
            if t0 is None:
                continue
            best = None
            for j in (k - 1, k + 1):
                if j < 0 or j >= len(clusters):
                    continue
                other = clusters[j]
                gap = min(abs(c["result"]["_start"] - o["result"]["_start"]) for o in other)
                if gap >= 3.0:
                    continue
                if any(o["me"] is not None and o["me"] == c["me"] for o in other):
                    continue
                t0s = sorted(x for x in (_tick_clock(o["result"]) for o in other) if x is not None)
                if not t0s:
                    continue
                d = abs(t0 - t0s[len(t0s) // 2])
                if d <= T0_RESCUE_S and (best is None or d < best[0]):
                    best = (d, j)
            if best is not None:
                clusters[best[1]].extend(cl)
                c["roomHow"] = "result-t0rescue"
                del clusters[k]
                changed = True
                break
    return clusters


def assign_rooms(b: dict, chains: list[dict]) -> list[dict]:
    """
    给每条链一个 room 编号（包内从 0 起）。返回房间列表（每个房间含 key 与成员链下标）。
    第一步：有结算行的链按 (land, seeded) 分组，再按开局墙钟分簇（_split_by_start）；
    第二步：没有结算行的链按 INIT 的 (mode, map, seed, seeded) 找同键房间，多于一个候选时按拍号相位挑最近的；
            找不到同键房间则与同键、相位接近的其他无结算链合成「无结算房间」。
    """
    rooms: list[dict] = []
    with_res = [ch for ch in chains if ch["result"] is not None]
    groups = defaultdict(list)
    for ch in with_res:
        r = ch["result"]
        groups[(r["land"], r["seededPlayers"])].append(ch)
    for (land, seeded), chs in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        for cl in _split_by_start(chs):
            starts = sorted(c["result"]["_start"] for c in cl)
            rooms.append({"land": land, "seeded": seeded, "start": starts[len(starts) // 2],
                          "startSpread": round(starts[-1] - starts[0], 2),
                          "chains": [c["idx"] for c in cl], "initKey": None})
    # 每个房间的 INIT 键（取成员里出现最多的）
    by_idx = {c["idx"]: c for c in chains}
    for rm in rooms:
        keys = Counter()
        for ci in rm["chains"]:
            i = by_idx[ci]["init"]
            if i is not None:
                keys[(i["mode"], i["map"], i["seed"], i["seeded"])] += 1
        # INIT 的 seeded 必须和结算的 seededPlayers 一致才算这个房间的 INIT
        keys = Counter({k: v for k, v in keys.items() if k[3] == rm["seeded"]})
        rm["initKey"] = keys.most_common(1)[0][0] if keys else None
    # 同一 (land, seeded) 的几个房间如果只有一个拿到了 INIT 键，其余的继承它（同一大厅拆出来的房间地图相同）
    by_ls = defaultdict(list)
    for rm in rooms:
        by_ls[(rm["land"], rm["seeded"])].append(rm)
    for rs in by_ls.values():
        ks = {rm["initKey"] for rm in rs if rm["initKey"] is not None}
        if len(ks) == 1:
            k = next(iter(ks))
            for rm in rs:
                if rm["initKey"] is None:
                    rm["initKey"] = k
                    rm["initKeyInherited"] = True
    ref_cache = {}

    def ref_rows(k):
        if k not in ref_cache:
            ref_cache[k] = sorted((r for ci in rooms[k]["chains"] for r in by_idx[ci]["rows"]), key=lambda x: x["line"])
        return ref_cache[k]

    assigned = {ci for rm in rooms for ci in rm["chains"]}
    rest = [ch for ch in chains if ch["idx"] not in assigned]
    n_result_rooms = len(rooms)
    leftovers = []
    for ch in rest:
        i = ch["init"]
        cand = []
        for k in range(n_result_rooms):
            rm = rooms[k]
            if i is not None and rm["initKey"] is not None and (i["mode"], i["map"], i["seed"], i["seeded"]) != rm["initKey"]:
                continue
            if i is not None and rm["initKey"] is None and i["seeded"] != rm["seeded"]:
                continue
            ph = _phase(ch, ref_rows(k))
            clash = ch["me"] is not None and any(by_idx[ci]["me"] == ch["me"] for ci in rm["chains"])
            cand.append((k, ph, clash))
        ok = sorted(((abs(ph), k) for k, ph, clash in cand if not clash and ph is not None and abs(ph) <= PHASE_GAP_TICKS))
        if ok:
            k = ok[0][1]
            rooms[k]["chains"].append(ch["idx"])
            ch["roomHow"] = "phase"
            ch["roomPhase"] = round(ok[0][0], 1)
            ch["roomPhaseNext"] = round(ok[1][0], 1) if len(ok) > 1 else None
            continue
        nokey = [k for k, ph, clash in cand if not clash]
        if not ch["rows"] and len(nokey) == 1:
            rooms[nokey[0]]["chains"].append(ch["idx"])
            ch["roomHow"] = "initkey-only"
            continue
        leftovers.append(ch)
    # 剩下的：按 INIT 键 + 相位合成「无结算房间」
    for ch in leftovers:
        i = ch["init"]
        key = (i["mode"], i["map"], i["seed"], i["seeded"]) if i else None
        placed = False
        for rm in rooms[n_result_rooms:]:
            if rm["initKey"] != key:
                continue
            ref = sorted((r for ci in rm["chains"] for r in by_idx[ci]["rows"]), key=lambda x: x["line"])
            ph = _phase(ch, ref)
            clash = ch["me"] is not None and any(by_idx[ci]["me"] == ch["me"] for ci in rm["chains"])
            if not clash and (ph is None or abs(ph) <= PHASE_GAP_TICKS):
                rm["chains"].append(ch["idx"])
                placed = True
                break
        if not placed:
            rooms.append({"land": None, "seeded": i["seeded"] if i else None, "start": None, "startSpread": None,
                          "chains": [ch["idx"]], "noResult": True, "initKey": key})
        ch["roomHow"] = "no-result"
    for k, rm in enumerate(rooms):
        rm["idx"] = k
        for ci in rm["chains"]:
            by_idx[ci]["room"] = k
            by_idx[ci].setdefault("roomHow", "result")
    return rooms


# ----------------------------------------------------------------------------
# C. 队伍
# ----------------------------------------------------------------------------

def infer_teams(b: dict, chains: list[dict], rooms: list[dict]) -> None:
    """
    每个号的队伍（teamHow）：
      result  结算行的 team.mine（died / end 行才有；left 行没有）
      clan    带战队标签的编组（squad8 的 [Nope]、squad10 的 [APEX]）：引擎把同标签的人整体放进一个队，
              所以同一房间里只要有一个号报过队号，其余没有队号的号（left / 没有结算行）取同一个队号。
              房间里报出的队号多于一个时不推断，记 clanTeamConflict。
      donate  没有战队标签的编组（squad20）：捐款（DONATE）的发起号和目标号在同一个队。
              依据：两端队号都由结算行给出的捐款边，全部 160 包里没有一条是跨队的（见 allyEdges.donate*）。
              把同一房间里的捐款边连成连通块，块里所有已知队号一致时，块内未知的号取这个队号；
              不一致时不推断，记 donateTeamConflict。
    协防（ASSIST：squad-rescue poke -> enemy=X for ally=Y）的 ally **不能**用来推队伍：
    squad20 里两端队号已知的协防边大部分是跨队的（见 allyEdges.assist*）——那里的 ally 是「同编组的号」，
    不是「引擎里的队友」。
    """
    by_idx = {c["idx"]: c for c in chains}
    tagged = b["card"]["cohort"] in ("squad8", "squad10")
    name_to_chain = {}
    for ch in chains:
        for n in ch["names"]:
            name_to_chain.setdefault(n, ch)
    for ch in chains:
        r = ch["result"]
        ch["team"] = r["teamMine"] if (r is not None and r["teamMine"] is not None) else None
        ch["teamHow"] = "result" if ch["team"] is not None else None
    me_to_chain = {}
    for ch in chains:
        if ch.get("room") is not None and ch["me"] is not None:
            me_to_chain.setdefault((ch["room"], ch["me"]), ch)

    # 边：按类型去重
    edge_sets = {"donate": set(), "assist": set()}
    for e in b["events"]:
        if e["type"] in ("DONATE", "DISPATCH"):
            ch = name_to_chain.get(e["bot"])
            if ch is not None and e["target"] is not None and ch.get("room") is not None:
                edge_sets["donate"].add((ch["idx"], e["target"]))
    for a in b["assists"]:
        ch = name_to_chain.get(a["name"])
        if ch is not None and a["ally"] is not None and ch.get("room") is not None:
            edge_sets["assist"].add((ch["idx"], a["ally"]))

    # 诊断：两端队号都来自结算行的边，同队 / 跨队各多少（在任何推断之前算）
    for rm in rooms:
        rm["allyEdges"] = {f"{k}{x}": 0 for k in ("donate", "assist") for x in ("Same", "Cross", "Unknown", "NotOurs")}
    for kind, es in edge_sets.items():
        for ci, ally in es:
            ch = by_idx[ci]
            rm = rooms[ch["room"]]
            other = me_to_chain.get((ch["room"], ally))
            if other is None:
                rm["allyEdges"][kind + "NotOurs"] += 1
            elif ch["teamHow"] != "result" or other["teamHow"] != "result":
                rm["allyEdges"][kind + "Unknown"] += 1
            elif ch["team"] == other["team"]:
                rm["allyEdges"][kind + "Same"] += 1
            else:
                rm["allyEdges"][kind + "Cross"] += 1

    for rm in rooms:
        chs = [by_idx[ci] for ci in rm["chains"]]
        rm["clanTeamConflict"] = False
        rm["donateTeamConflict"] = 0
        if tagged:
            seen = Counter(c["team"] for c in chs if c["team"] is not None)
            rm["clanTeamConflict"] = len(seen) > 1
            if len(seen) == 1:
                t = next(iter(seen))
                for c in chs:
                    if c["team"] is None:
                        c["team"] = t
                        c["teamHow"] = "clan"
            continue
        # 没有标签：捐款边并查集。节点 = ('c', 链下标) 或 ('p', 局内号)（不是我方号的队友）
        parent = {}

        def find(x):
            parent.setdefault(x, x)
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x, y):
            rx, ry = find(x), find(y)
            if rx != ry:
                parent[rx] = ry

        in_room = set(rm["chains"])
        for ci, ally in edge_sets["donate"]:
            if ci not in in_room:
                continue
            other = me_to_chain.get((rm["idx"], ally))
            union(("c", ci), ("c", other["idx"]) if other is not None else ("p", ally))
        comp_team = defaultdict(Counter)
        for c in chs:
            if c["team"] is not None:
                comp_team[find(("c", c["idx"]))][c["team"]] += 1
        rm["donateTeamConflict"] = sum(1 for v in comp_team.values() if len(v) > 1)
        for c in chs:
            if c["team"] is None:
                v = comp_team.get(find(("c", c["idx"])))
                if v and len(v) == 1:
                    c["team"] = next(iter(v))
                    c["teamHow"] = "donate"
        # 没有队号、但彼此有捐款关系的号：记下连通块编号（同块同队，队号未知）
        for c in chs:
            c["teamGroup"] = None
        groups = defaultdict(list)
        for c in chs:
            if c["team"] is None and ("c", c["idx"]) in parent:
                groups[find(("c", c["idx"]))].append(c)
        for gi, (_, members) in enumerate(sorted(groups.items(), key=lambda kv: min(m["idx"] for m in kv[1]))):
            for m in members:
                m["teamGroup"] = gi


# ----------------------------------------------------------------------------
# D. 房间小结（只依赖本包的事实）
# ----------------------------------------------------------------------------

def engine_team_count(nominal: int, humans: int, clan: int) -> int:
    """引擎分队函数的队伍数下调规则：while (T>2 && clan > floor(humans/T)) T--。clan=最大战队人数。"""
    t = nominal
    while t > 2 and clan > humans // t:
        t -= 1
    return t


def _terr_at(rows: list[dict], t: int):
    """链在第 t 拍的领土：有这一拍的快照就取它；缺拍时在前后 180 拍内的两个快照之间线性插值；否则 None。"""
    prev = nxt = None
    for r in rows:
        if r["t"] == t:
            return r["terr"], "exact"
        if r["t"] < t:
            prev = r
        elif nxt is None:
            nxt = r
    if prev is not None and nxt is not None and nxt["t"] - prev["t"] <= 360 and t - prev["t"] <= 180 and nxt["t"] - t <= 180:
        w = (t - prev["t"]) / (nxt["t"] - prev["t"])
        return int(round(prev["terr"] + w * (nxt["terr"] - prev["terr"]))), "interp"
    return None, None


def chain_public(c: dict) -> dict:
    r = c["result"]
    rows = c["rows"]
    n_gap = sum(1 for x, y in zip(rows, rows[1:]) if y["t"] - x["t"] > 90)
    n_missing = sum((y["t"] - x["t"]) // 90 - 1 for x, y in zip(rows, rows[1:]) if y["t"] - x["t"] > 90)
    resets = [y["t"] for x, y in zip(rows, rows[1:]) if y["cmds"] < x["cmds"]]
    t630, how630 = _terr_at(rows, 630)
    t1530, how1530 = _terr_at(rows, 1530)
    last = rows[-1] if rows else None
    return {
        "names": c["names"], "me": c["me"], "team": c["team"], "teamHow": c["teamHow"],
        "teamGroup": c.get("teamGroup"),
        "roomHow": c.get("roomHow"), "roomPhase": c.get("roomPhase"), "roomPhaseNext": c.get("roomPhaseNext"),
        "resultHow": c["resultHow"], "idCheck": c["idCheck"],
        "linkCosts": c["linkCosts"], "ambiguous": c["ambiguous"],
        "firstT": rows[0]["t"] if rows else None, "lastT": rows[-1]["t"] if rows else None,
        "nSnap": len(rows), "nSnapGaps": n_gap, "nSnapMissing": n_missing, "counterResetsAt": resets,
        "peakTerrSnap": max((x["terr"] for x in rows), default=None),
        "terr630": t630, "terr630How": how630, "terr1530": t1530, "terr1530How": how1530,
        "skipFinal": last["skip"] if last else None, "maxMsFinal": last["maxMs"] if last else None,
        "avgMsFinal": last["avgMs"] if last else None, "cmdsFinal": last["cmds"] if last else None,
        "event": r["event"] if r else None, "result": r["result"] if r else None,
        "tick": r["tick"] if r else None, "peak": r["peak"] if r else None,
        "place": r["place"] if r else None,
        "lastTerritory": r["lastTerritory"] if r else None,
        "territoryAtResult": r["territory"] if r else None,
        "balanceAtResult": r["balance"] if r else None,
        "startOffsetS": None,
    }


def room_facts(b: dict, chains: list[dict], rm: dict) -> dict:
    by_idx = {c["idx"]: c for c in chains}
    chs = [by_idx[ci] for ci in rm["chains"]]
    card = b["card"]
    res = [c["result"] for c in chs if c["result"] is not None]
    land = rm["land"]
    init = rm["initKey"]
    mode = init[0] if init else None
    tagged = card["cohort"] in ("squad8", "squad10")
    events = Counter((c["result"]["event"] if c["result"] else "none") for c in chs)
    teams = Counter(c["team"] for c in chs if c["team"] is not None)
    teams_by_result = Counter(c["team"] for c in chs if c["teamHow"] == "result")
    n_unknown = sum(1 for c in chs if c["team"] is None)
    # 我方的「主队」：号数最多的队；并列时取队号小的并标记；
    # 「主队不确定」= 没有队号的号足够多，可能改变哪个队是主队
    primary, primary_tie, primary_uncertain = None, False, False
    if teams:
        top = teams.most_common()
        primary = sorted([t for t, n in top if n == top[0][1]])[0]
        primary_tie = sum(1 for t, n in top if n == top[0][1]) > 1
        second = max([n for t, n in top if t != primary], default=0)
        primary_uncertain = (not tagged) and n_unknown > 0 and (top[0][1] - second) <= n_unknown
    last_tick = max((r["tick"] or 0 for r in res), default=None)
    last_snap = max((c["rows"][-1]["t"] for c in chs if c["rows"]), default=None)
    left_rows = [r for r in res if r["event"] == "left"]
    n_left_early = sum(1 for r in left_rows if 0 < (r["tick"] or 0) < 2000)
    n_left_t0 = sum(1 for r in left_rows if (r["tick"] or 0) == 0)
    n_left_end = sum(1 for r in left_rows if last_tick is not None and (r["tick"] or 0) >= 2000 and last_tick - r["tick"] <= 150)
    n_left_mid = len(left_rows) - n_left_early - n_left_t0 - n_left_end
    totals_rows = [{"tick": r["tick"], "line": r["_line"], "event": r["event"], "result": r["result"],
                    "mine": r["teamMine"], "best": r["teamBest"], "totals": r["teamTotals"],
                    "alive": r["alivePlayers"]}
                   for r in sorted(res, key=lambda r: (r["tick"] or 0, r["_line"] or 0)) if r["teamTotals"]]
    end_rows = [{"tick": r["tick"], "result": r["result"], "mine": r["teamMine"], "best": r["teamBest"],
                 "hasTotals": bool(r["teamTotals"])}
                for r in sorted(res, key=lambda r: (r["tick"] or 0, r["_line"] or 0)) if r["event"] == "end"]
    bots = []
    for c in chs:
        pb = chain_public(c)
        if c["result"] is not None and rm.get("start") is not None:
            pb["startOffsetS"] = round(c["result"]["_start"] - rm["start"], 2)
        bots.append(pb)
    return {
        "roomIdx": rm["idx"], "land": land, "seeded": rm["seeded"],
        "startUtc": (datetime.datetime.fromtimestamp(rm["start"], datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                     if rm.get("start") else None),
        "startS": rm.get("start"), "startSpreadS": rm.get("startSpread"),
        "initKey": {"mode": init[0], "map": init[1], "mapSeed": init[2], "seeded": init[3]} if init else None,
        "mode": mode, "tagged": tagged,
        "nBots": len(chs), "events": dict(events),
        "nLeftEarly": n_left_early, "nLeftT0": n_left_t0, "nLeftMid": n_left_mid, "nLeftAtEnd": n_left_end,
        "teams": {str(k): v for k, v in sorted(teams.items())},
        "teamsFromResult": {str(k): v for k, v in sorted(teams_by_result.items())},
        "nTeamUnknown": n_unknown,
        "primaryTeam": primary, "primaryTie": primary_tie, "primaryUncertain": primary_uncertain,
        "lastTick": last_tick, "lastSnapshotTick": last_snap,
        "clanTeamConflict": rm.get("clanTeamConflict", False),
        "donateTeamConflict": rm.get("donateTeamConflict", 0),
        "allyEdges": rm.get("allyEdges"),
        "totalsRows": totals_rows, "endRows": end_rows,
        "bots": bots,
    }


# ----------------------------------------------------------------------------
# E. 判定（可以只用本包的结算行，也可以用同一物理房间里所有包的结算行）
# ----------------------------------------------------------------------------

def judge(room: dict, totals_rows: list[dict], end_rows: list[dict], clan_max: int, mode) -> dict:
    """
    totals_rows / end_rows：这个房间里（本包，或同一物理房间的所有包）带 team.totals 的结算行 / end 行。
    clan_max：这个房间里我方最大的带标签编组人数（没有带标签的编组时为 1）。
    """
    land = room["land"]
    nominal = (mode + 2) if (mode is not None and mode < 7) else None
    rows = sorted(totals_rows, key=lambda r: (r["tick"] or 0, r["line"] or 0))
    is_team_game = None
    if mode is not None:
        is_team_game = mode < 7 or mode == 9
    elif rows:
        is_team_game = True
    team_keys = set()
    for r in rows:
        team_keys |= {int(k) for k in r["totals"] if k != "0"}
    t_obs = len(team_keys)
    t_rule = engine_team_count(nominal, room["seeded"], clan_max) if (nominal is not None and room["seeded"]) else None
    # 队伍数取值：totals 里见过的队号数 ≥ 规则值 → 用观察值；观察值少于规则值（首条 totals 之前已有队伍被灭，
    # 或者根本没有 totals）→ 用规则值，并把观察值记为下界
    if t_obs >= 2 and (t_rule is None or t_obs >= t_rule):
        t_best, t_how = t_obs, ("totals" if (t_rule is None or t_obs == t_rule) else "totals>rule")
    elif t_rule is not None:
        t_best, t_how = t_rule, ("rule" if t_obs == 0 else "rule>totals")
    elif t_obs >= 1:
        t_best, t_how = None, "unknown(one-key-no-rule)"
    else:
        t_best, t_how = None, "unknown"
    ends = sorted(end_rows, key=lambda r: (r["tick"] or 0))
    ends_tot = [r for r in ends if r["hasTotals"]]
    winner = ends_tot[-1]["best"] if ends_tot else None
    last = rows[-1] if rows else None
    last_shares = {k: round(v / land, 4) for k, v in last["totals"].items()} if (last is not None and land) else None
    real_last = {int(k): v for k, v in last["totals"].items() if k != "0"} if last is not None else {}
    leader_last = max(real_last, key=lambda k: real_last[k]) if real_last else None
    team_out = {}
    for t_str, n in room["teams"].items():
        t = int(t_str)
        o = {"nBots": n, "lastShare": None, "lastRank": None, "peakShareSeen": None, "outcome": "NO_INFO"}
        if land and rows:
            o["peakShareSeen"] = round(max(r["totals"].get(t_str, 0) / land for r in rows), 4)
        if last is not None and land:
            v = real_last.get(t, 0)
            o["lastShare"] = round(v / land, 4)
            o["lastRank"] = 1 + sum(1 for x in real_last.values() if x > v)
        if winner is not None:
            o["outcome"] = "WIN" if winner == t else "LOSS"
        elif last is not None:
            o["outcome"] = "LOSS" if real_last.get(t, 0) <= 0 else "OPEN"
        team_out[t_str] = o
    primary = room["primaryTeam"]
    p = team_out.get(str(primary)) if primary is not None else None
    if is_team_game is False:
        outcome = "NON_TEAM"
    elif primary is None:
        all_left = all(e in ("left", "none") for e in room["events"])
        outcome = "NO_PLAY" if all_left else "UNKNOWN"
    elif p["outcome"] in ("WIN", "LOSS"):
        outcome = p["outcome"]
    elif p["outcome"] == "NO_INFO":
        outcome = "UNKNOWN"
    elif p["lastRank"] == 1 and p["lastShare"] >= 0.5:
        outcome = "WIN_LIKELY"
    elif p["lastRank"] != 1 and p["lastShare"] < 0.20:
        outcome = "LOSS_LIKELY"
    else:
        outcome = "UNKNOWN"
    return {
        "isTeamGame": is_team_game, "nominalTeams": nominal,
        "teamKeysSeen": sorted(team_keys), "tObs": t_obs, "tRule": t_rule, "tBest": t_best, "tHow": t_how,
        "clanMax": clan_max,
        "hasAiKey": any("0" in r["totals"] for r in rows),
        "firstTotalsTick": rows[0]["tick"] if rows else None,
        "winner": winner, "endObserved": bool(ends), "endTick": ends[-1]["tick"] if ends else None,
        "lastTotalsTick": last["tick"] if last else None, "lastShares": last_shares,
        "leaderAtLastTotals": leader_last,
        "teamOutcomes": team_out,
        "primaryLastShare": p["lastShare"] if p else None, "primaryLastRank": p["lastRank"] if p else None,
        "primaryPeakShareSeen": p["peakShareSeen"] if p else None,
        "outcome": outcome,
        "ourTeamsIncludeWinner": (str(winner) in room["teams"]) if winner is not None else None,
    }


def analyze_bundle(card: dict) -> dict:
    """只用本包的数据。物理房间（跨包）的合并在 analyze_all 里做。"""
    b = read_bundle(card)
    chains = build_chains(b)
    rooms = assign_rooms(b, chains)
    infer_teams(b, chains, rooms)
    out_rooms = []
    facts = [room_facts(b, chains, rm) for rm in rooms]
    # 没有 INIT 的房间：同一个包里、地图面积相同、开局相差不到 60 秒的另一个房间有 INIT 时，继承它的模式
    # （同一个大厅拆出来的两个房间）。继承来的名义队伍数如果小于本房间 totals 里见过的队号数，则不继承。
    for f in facts:
        f["modeInherited"] = False
        if f["mode"] is not None or f["startS"] is None:
            continue
        seen = set()
        for r in f["totalsRows"]:
            seen |= {k for k in r["totals"] if k != "0"}
        for g in facts:
            if g is f or g["mode"] is None or g["startS"] is None or g["land"] != f["land"]:
                continue
            if abs(g["startS"] - f["startS"]) > 60:
                continue
            if g["mode"] < 7 and g["mode"] + 2 < len(seen):
                continue
            f["mode"] = g["mode"]
            f["modeInherited"] = True
            break
    for f in facts:
        clan = f["nBots"] if f["tagged"] else 1
        f.update(judge(f, f["totalsRows"], f["endRows"], clan, f["mode"]))
        f["anyBotWonRow"] = any(r["result"] == "won" for r in f["endRows"]) if f["endRows"] else None
        f["physRoom"] = None
        f["physPeers"] = []
        f["own"] = {k: f[k] for k in ("tObs", "tRule", "tBest", "tHow", "winner", "outcome", "isTeamGame")}
        out_rooms.append(f)
    main = max(out_rooms, key=lambda r: (r["nBots"], r["lastTick"] or 0)) if out_rooms else None
    by_how = Counter()
    for c in chains:
        if c["idCheck"] is not None:
            by_how[(c["resultHow"], bool(c["idCheck"]))] += 1
    id_checks = [c["idCheck"] for c in chains if c["idCheck"] is not None]
    return {
        "matchId": card["matchId"], "cohort": card["cohort"], "split": card["split"],
        "nNames": len(b["ticks"]), "nInitNames": len({i["name"] for i in b["inits"]}),
        "nResultRows": len(b["results"]), "nBots": len(chains),
        "nRooms": len(out_rooms), "mainRoom": main["roomIdx"] if main else None,
        "idCheckOk": sum(1 for x in id_checks if x), "idCheckBad": sum(1 for x in id_checks if not x),
        "idCheckIndependentOk": by_how[("name", True)] + by_how[("tail", True)],
        "idCheckIndependentBad": by_how[("name", False)] + by_how[("tail", False)],
        "nRenamedBots": sum(1 for c in chains if len(c["names"]) > 1),
        "nAmbiguousLinks": sum(c["ambiguous"] for c in chains),
        "nBotsNoResult": sum(1 for c in chains if c["result"] is None),
        "nOrphanResults": sum(1 for c in chains if c["resultHow"] == "orphan"),
        "rooms": out_rooms,
    }


def link_physical(bundles: list[dict]) -> list[dict]:
    """
    跨包合并物理房间：land、seeded 相同，开局墙钟相差 ≤ START_LINK_S，且不把同一个包的两个房间并到一起、
    局内号不冲突。合并后用物理房间里所有包的结算行重新判定队伍数 / 胜方 / 结局。
    返回物理房间列表；并就地改写每个房间的判定字段（本包自己的判定保留在 room["own"]）。
    """
    items = []
    for a in bundles:
        for r in a["rooms"]:
            if r["startS"] is not None and r["land"] is not None:
                items.append((a, r))
    parent = list(range(len(items)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    members = {i: [i] for i in range(len(items))}
    pairs = []
    by_key = defaultdict(list)
    for i, (a, r) in enumerate(items):
        by_key[(r["land"], r["seeded"])].append(i)
    for idxs in by_key.values():
        idxs.sort(key=lambda i: items[i][1]["startS"])
        for x in range(len(idxs)):
            for y in range(x + 1, len(idxs)):
                gap = items[idxs[y]][1]["startS"] - items[idxs[x]][1]["startS"]
                if gap > START_LINK_S:
                    break
                pairs.append((gap, idxs[x], idxs[y]))
    pairs.sort()
    clashes = []
    for gap, i, j in pairs:
        ri, rj = find(i), find(j)
        if ri == rj:
            continue
        mi, mj = members[ri], members[rj]
        if {items[k][0]["matchId"] for k in mi} & {items[k][0]["matchId"] for k in mj}:
            continue
        ids_i = {bt["me"] for k in mi for bt in items[k][1]["bots"] if bt["me"] is not None}
        ids_j = {bt["me"] for k in mj for bt in items[k][1]["bots"] if bt["me"] is not None}
        if ids_i & ids_j:
            clashes.append((items[i][0]["matchId"], items[j][0]["matchId"], round(gap, 2), sorted(ids_i & ids_j)))
            continue
        parent[ri] = rj
        members[rj] = mi + mj
        del members[ri]
    phys = []
    for pid, (root, ms) in enumerate(sorted(members.items(), key=lambda kv: min(items[k][1]["startS"] for k in kv[1]))):
        rooms_ = [items[k] for k in ms]
        rows = [x for a, r in rooms_ for x in r["totalsRows"]]
        ends = [x for a, r in rooms_ for x in r["endRows"]]
        clan = max((r["nBots"] if r["tagged"] else 1) for a, r in rooms_)
        modes = Counter(r["mode"] for a, r in rooms_ if r["mode"] is not None)
        mode = modes.most_common(1)[0][0] if modes else None
        for a, r in rooms_:
            r["physRoom"] = pid
            r["physPeers"] = [{"matchId": a2["matchId"], "roomIdx": r2["roomIdx"], "cohort": a2["cohort"],
                               "split": a2["split"], "nBots": r2["nBots"]}
                              for a2, r2 in rooms_ if a2 is not a]
            if len(rooms_) > 1:
                r.update(judge(r, rows, ends, clan, mode))
                r["mode"] = mode if r["mode"] is None else r["mode"]
        phys.append({
            "physRoom": pid, "land": rooms_[0][1]["land"], "seeded": rooms_[0][1]["seeded"],
            "startUtc": min(r["startUtc"] for a, r in rooms_),
            "members": [{"matchId": a["matchId"], "roomIdx": r["roomIdx"], "cohort": a["cohort"], "split": a["split"],
                         "nBots": r["nBots"], "teams": r["teams"], "nTeamUnknown": r["nTeamUnknown"]} for a, r in rooms_],
            "nOurBots": sum(r["nBots"] for a, r in rooms_),
            "modeConflict": len(modes) > 1,
            "tBest": rooms_[0][1]["tBest"], "tHow": rooms_[0][1]["tHow"], "winner": rooms_[0][1]["winner"],
            "isTeamGame": rooms_[0][1]["isTeamGame"],
        })
    for a in bundles:
        for r in a["rooms"]:
            r["usedPeerRows"] = any(r[k] != r["own"][k] for k in r["own"])
    return phys, clashes


def analyze_all(which: str = "all") -> list[dict]:
    """全部 160 包一起分析（物理房间的合并需要看到所有包），再按 which 过滤返回。"""
    allb = [analyze_bundle(c) for c in load_cards("all")]
    phys, clashes = link_physical(allb)
    analyze_all.phys = phys
    analyze_all.clashes = clashes
    if which == "all":
        return allb
    return [a for a in allb if a["split"] == which]


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def _fmt_room(r: dict) -> str:
    peers = ",".join(f"{p['matchId']}#{p['roomIdx']}({p['nBots']})" for p in r["physPeers"]) or "-"
    return (f"  room{r['roomIdx']}: bots={r['nBots']} seeded={r['seeded']} land={r['land']} start={r['startUtc']} "
            f"spread={r['startSpreadS']} mode={r['mode']} nominalT={r['nominalTeams']} tObs={r['tObs']} tRule={r['tRule']} "
            f"tBest={r['tBest']}({r['tHow']}) keys={r['teamKeysSeen']} "
            f"events={r['events']} teams={r['teams']} (fromResult={r['teamsFromResult']}, unknown={r['nTeamUnknown']}) "
            f"primary={r['primaryTeam']}{'(tie)' if r['primaryTie'] else ''}{'(uncertain)' if r['primaryUncertain'] else ''} "
            f"winner={r['winner']} outcome={r['outcome']} own={r['own']['outcome']} "
            f"lastTick={r['lastTick']} endObserved={r['endObserved']} primaryLastShare={r['primaryLastShare']} "
            f"rank={r['primaryLastRank']} lastShares={r['lastShares']} phys={r['physRoom']} peers={peers}\n"
            f"         teamOutcomes={r['teamOutcomes']}")


def cmd_show(mid: str, allb: list[dict]) -> None:
    a = next(x for x in allb if x["matchId"] == mid)
    print(json.dumps({k: v for k, v in a.items() if k != "rooms"}, ensure_ascii=False))
    for r in a["rooms"]:
        print(_fmt_room(r))
        for bt in r["bots"]:
            print(f"     me={bt['me']} team={bt['team']}({bt['teamHow']}) {bt['event']}@{bt['tick']} "
                  f"snap={bt['firstT']}..{bt['lastT']}({bt['nSnap']},miss{bt['nSnapMissing']}) names={'→'.join(bt['names'])} "
                  f"resultHow={bt['resultHow']} idCheck={bt['idCheck']} linkCosts={bt['linkCosts']} amb={bt['ambiguous']} "
                  f"roomHow={bt['roomHow']} skip={bt['skipFinal']} resets={bt['counterResetsAt']}")


def cmd_selfcheck(allb: list[dict]) -> None:
    tot = Counter()
    for a in allb:
        k = a["cohort"]
        tot[(k, "bundles")] += 1
        tot[(k, "bots")] += a["nBots"]
        tot[(k, "idOk")] += a["idCheckOk"]
        tot[(k, "idBad")] += a["idCheckBad"]
        tot[(k, "idIndependentOk")] += a["idCheckIndependentOk"]
        tot[(k, "idIndependentBad")] += a["idCheckIndependentBad"]
        tot[(k, "renamed")] += a["nRenamedBots"]
        tot[(k, "ambiguousLinks")] += a["nAmbiguousLinks"]
        tot[(k, "noResult")] += a["nBotsNoResult"]
        tot[(k, "orphanResults")] += a["nOrphanResults"]
        tot[(k, "multiRoomBundles")] += 1 if a["nRooms"] > 1 else 0
        tot[(k, "rooms")] += a["nRooms"]
        tot[(k, "roomsWithPeer")] += sum(1 for r in a["rooms"] if r["physPeers"])
        tot[(k, "roomsUsedPeerRows")] += sum(1 for r in a["rooms"] if r["usedPeerRows"])
        if a["idCheckBad"]:
            print("idCheckBad:", a["matchId"], a["idCheckBad"])
    for k in sorted(tot):
        print(k, tot[k])
    print("physical rooms:", len(analyze_all.phys), "with >1 bundle:", sum(1 for p in analyze_all.phys if len(p["members"]) > 1))
    print("me clashes that blocked a merge:", analyze_all.clashes)


def _mask_validation(a: dict) -> dict:
    """发现集文件里，把验证集同房包的编号遮掉（只留「有验证集同房包」这个事实）。"""
    a = json.loads(json.dumps(a))
    for r in a["rooms"]:
        for p in r["physPeers"]:
            if p["split"] == "validation":
                p["matchId"] = "(validation)"
                p["roomIdx"] = None
    return a


def cmd_build(allb: list[dict]) -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    disc = [_mask_validation(a) for a in allb if a["split"] == "discovery"]
    val = [a for a in allb if a["split"] == "validation"]
    with open(os.path.join(OUT_DIR, "rooms-discovery.json"), "w", encoding="utf-8") as f:
        json.dump(disc, f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT_DIR, "rooms-validation-internal.json"), "w", encoding="utf-8") as f:
        json.dump({"_notice": "验证集内部文件：仅 R10 与 c136 使用，R01~R09 不得读取。", "bundles": val}, f,
                  ensure_ascii=False, indent=1)
    with open(os.path.join(OUT_DIR, "physical-rooms-internal.json"), "w", encoding="utf-8") as f:
        json.dump({"_notice": "含验证集包编号：仅 R10 与 c136 使用，R01~R09 不得读取。",
                   "physicalRooms": analyze_all.phys, "meClashes": analyze_all.clashes}, f, ensure_ascii=False, indent=1)
    # 发现集的「名字链 → 号」对照表
    with open(os.path.join(OUT_DIR, "identity-map-discovery.csv"), "w", encoding="utf-8") as f:
        f.write("matchId,cohort,roomIdx,me,team,teamHow,event,resultTick,firstSnap,lastSnap,nSnap,nSnapMissing,nNames,nameChain\n")
        for a in allb:
            if a["split"] != "discovery":
                continue
            for r in a["rooms"]:
                for bt in r["bots"]:
                    f.write(",".join(str(x) if x is not None else "" for x in (
                        a["matchId"], a["cohort"], r["roomIdx"], bt["me"], bt["team"], bt["teamHow"], bt["event"],
                        bt["tick"], bt["firstT"], bt["lastT"], bt["nSnap"], bt["nSnapMissing"], len(bt["names"]),
                        "→".join(bt["names"]))) + "\n")
    print(f"built: discovery={len(disc)} validation={len(val)} physicalRooms={len(analyze_all.phys)} -> {os.path.normpath(OUT_DIR)}")


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[1] in ("show", "selfcheck", "build"):
        allb = analyze_all("all")
        if argv[1] == "show":
            for mid in argv[2:]:
                cmd_show(mid, allb)
        elif argv[1] == "selfcheck":
            cmd_selfcheck(allb)
        else:
            cmd_build(allb)
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
