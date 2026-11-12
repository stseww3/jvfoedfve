#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""57_exec_census.py — R07：全部带录像的对局包的「执行层」普查（选点指令进没进录像、指令成批晚到、发出 vs 落地）。

第一步先跑 57_exec_census.mjs（只解码录像），它把每局的 spawn_cmds.tsv / 精简 humans_cmd.tsv 写到 out/_cache/census/<局>/。
这里对每一局复用 53_issue_vs_land.py 和 54_spawn_seq.py 的逻辑（R07_OUT_ROOT 指到 out/_cache/census），
再并上 census_batches.tsv（同一号同一拍 ≥3 条的批）和 card.json（编队、结果）。

用法：python3 57_exec_census.py
输出：out/_cross/exec_census.tsv（每局一行）、out/_cross/exec_census.txt（分布和小结）
"""
import csv
import importlib.util
import json
import os
import re
import statistics
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = "/agent/repos/c136-data"
ROOT = os.path.join(HERE, "..", "out", "_cache", "census")
os.environ["R07_OUT_ROOT"] = ROOT
CROSS = os.path.join(HERE, "..", "out", "_cross")
TICK_RE = re.compile(r"\[([^\]\[]+)\] \[HL-TICK\] t=(\d+) .*?cmds=(\d+)")
MS_RE = re.compile(r"avgMs=([\d.]+) maxMs=([\d.]+) skip=(\d+)")


def load_mod(fn, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fn))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def card(mid):
    try:
        d = json.load(open(os.path.join(DATA, "bundles", mid, "card.json"), encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    oc = d.get("outcome")
    if isinstance(oc, str):
        try:
            oc = json.loads(oc.replace("'", '"').replace("False", "false").replace("True", "true").replace("None", "null"))
        except ValueError:
            oc = {}
    d["_result"] = (oc or {}).get("resultLabel", "")
    return d


def log_facts(mid, allow):
    """日志头里有 [BACKEND-SPAWN-COORD] 的是 c116（Va / Vb）一代，没有的是更早的一代；名牌取 [RESULT [..] 里的。
    另记：在场的号最后一条 HL-TICK 的拍号、cmds 计数回绕（变小）的次数。"""
    coord = False
    tag = ""
    last_tick = 0
    resets = 0
    prev = {}
    ms = {"tickLines": 0, "skipLines": 0, "avgMsMax": 0.0, "maxMsMax": 0.0, "maxMsGe56": 0, "maxMsGe392": 0}
    with open(os.path.join(DATA, "bundles", mid, "in_game.log"), encoding="utf-8", errors="replace") as f:
        for ln in f:
            if not coord and "[BACKEND-SPAWN-COORD]" in ln:
                coord = True
            if not tag and "[RESULT [" in ln:
                tag = ln.split("[RESULT [", 1)[1].split("]", 1)[0]
            m = TICK_RE.search(ln)
            if m and m.group(1) in allow:
                t, c = int(m.group(2)), int(m.group(3))
                last_tick = max(last_tick, t)
                if m.group(1) in prev and c < prev[m.group(1)]:
                    resets += 1
                prev[m.group(1)] = c
                mm = MS_RE.search(ln)
                if mm:
                    a_ms, x_ms, sk = float(mm.group(1)), float(mm.group(2)), int(mm.group(3))
                    ms["tickLines"] += 1
                    ms["skipLines"] += 1 if sk else 0
                    ms["avgMsMax"] = max(ms["avgMsMax"], a_ms)
                    ms["maxMsMax"] = max(ms["maxMsMax"], x_ms)
                    ms["maxMsGe56"] += 1 if x_ms >= 56 else 0
                    ms["maxMsGe392"] += 1 if x_ms >= 392 else 0
    return ("协调器" if coord else "无协调器") + (f"·{tag}" if tag else ""), last_tick, resets, ms


def main():
    os.makedirs(CROSS, exist_ok=True)
    m53 = load_mod("53_issue_vs_land.py", "m53")
    m54 = load_mod("54_spawn_seq.py", "m54")
    batches = {r["matchId"]: r for r in csv.DictReader(open(os.path.join(ROOT, "census_batches.tsv"), encoding="utf-8"), delimiter="\t")}
    mids = sorted(batches)
    rows = []
    for mid in mids:
        b = batches[mid]
        c = card(mid)
        allow = m53.allowed_bots(mid) or set()
        ver, log_last, resets, ms = log_facts(mid, allow)
        r = {"matchId": mid, "cohort": c.get("cohort", ""), "result": c.get("_result", ""), "ver": ver, "humans": int(b["humans"]), "logBots": int(b["logBots"]),
             "bots": int(b["squadBots"]), "lastTick": int(b["lastTick"]), "logLastTick": log_last, "cmdsResets": resets}
        r.update(ms)
        r["peer"] = (c.get("sameMatchPeer") or {}).get("peerMatchId", "") if isinstance(c.get("sameMatchPeer"), dict) else ""
        r["famSeats"] = int(b["peerSeats"]) + int(b["familyNameSeats"])
        r["mixed"] = 1 if (r["peer"] or r["famSeats"] >= 3) else 0
        # 结算表里 event=left 的号（被判离开；席位交给内置 AI）。只是下限：有的号被判离开时结算表没有记（A062 六个里只记了一个）
        left = []
        rp = os.path.join(DATA, "bundles", mid, "results.csv")
        if os.path.exists(rp):
            with open(rp, newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    if row.get("event") == "left" and row.get("bot") in allow:
                        try:
                            left.append(int(row["tick"]))
                        except (ValueError, KeyError):
                            pass
        r["leftAll"] = len(left)
        r["leftBefore3000"] = sum(1 for t in left if 0 < t < 3000)
        r["leftTicks"] = ",".join(str(t) for t in sorted(left))
        # 录像只到一半（最后一拍比在场的号最后一条 HL-TICK 早 180 拍以上）的局，发出 vs 落地不能对账
        r["replayShort"] = 1 if r["lastTick"] + 180 < log_last else 0
        r["partial"] = 1 if r["bots"] < r["logBots"] else 0
        s = m54.run(mid)
        if s:
            r.update({"solves": s["solves"], "changes": s["changes"], "asg": s["asg"], "spawnLanded": s["cmd"], "hostSpawn": s.get("hostSpawn"),
                      "firstMiss": s["fbMiss"], "firstBots": s["fbBots"], "endLast": s["endLast"], "endOver": s["endOverwritten"], "endStale": s["endStale"],
                      "endNone": s["endNone"], "grpRev": s["grpRev"], "grpFwd": s["grpFwd"], "grpBoth": s["grpBoth"], "myFirstStep": s["myFirst"], "othFirstStep": s["othFirst"]})
        v = m53.one(mid) if (allow and not r["replayShort"] and not resets) else None
        if v:
            a = v["agg"]
            ks = list(a)
            oi, ol = v["issued"] - v["dispatch"], v["landed"] - v["donLand"]
            r.update({"issued": v["issued"], "landed": v["landed"], "dispatch": v["dispatch"], "donLanded": v["donLand"], "atkIssued": oi, "atkLanded": ol,
                      "atkMiss": oi - ol, "late90": sum(a[k][1] for k in ks), "late90_600_1500": a[ks[1]][1], "late90_1500_3000": a[ks[2]][1], "late90_3000": a[ks[3]][1],
                      "late180": sum(a[k][2] for k in ks)})
        r.update({"sqBatches": int(b["sqBatches"]), "sqBatchCmds": int(b["sqBatchCmds"]), "sqBatch9": int(b["sqBatch9"]), "sqBatchGt9": int(b["sqBatchGt9"]),
                  "sqBatchMax": int(b["sqBatchMax"]), "sqBatchesByPeriod": b["sqBatchesByPeriod"], "otBatches": int(b["otBatches"]), "otBatchCmds": int(b["otBatchCmds"]),
                  "otBatchMax": int(b["otBatchMax"]), "squadCmds": int(b["squadCmds"]), "otherCmds": int(b["otherCmds"]), "notMod7": int(b["squadCmdsNotMod7"]),
                  "spawnAfterPhase": int(b["spawnCmdsAfterPhase"]), "otBatch9": int(b["otBatch9"]), "famCmds": int(b["famCmds"]), "famBatches": int(b["famBatches"]),
                  "famBatchCmds": int(b["famBatchCmds"]), "famBatch9": int(b["famBatch9"]), "famBatchMax": int(b["famBatchMax"])})
        rows.append(r)

    cols = ["matchId", "cohort", "ver", "result", "humans", "logBots", "bots", "partial", "lastTick", "logLastTick", "replayShort", "cmdsResets", "leftAll", "leftBefore3000", "leftTicks", "solves", "changes", "asg", "hostSpawn", "spawnLanded", "firstMiss", "firstBots", "endLast",
            "endOver", "endStale", "endNone", "grpRev", "grpFwd", "grpBoth", "myFirstStep", "othFirstStep", "issued", "landed", "dispatch", "donLanded", "atkIssued",
            "atkLanded", "atkMiss", "late90", "late90_600_1500", "late90_1500_3000", "late90_3000", "late180", "squadCmds", "sqBatches", "sqBatchCmds", "sqBatch9", "sqBatchGt9",
            "sqBatchMax", "sqBatchesByPeriod", "otherCmds", "otBatches", "otBatchCmds", "otBatchMax", "notMod7", "spawnAfterPhase",
            "otBatch9", "peer", "famSeats", "mixed", "famCmds", "famBatches", "famBatchCmds", "famBatch9", "famBatchMax",
            "tickLines", "skipLines", "avgMsMax", "maxMsMax", "maxMsGe56", "maxMsGe392"]
    with open(os.path.join(CROSS, "exec_census.tsv"), "w", encoding="utf-8") as f:
        f.write("\t".join(cols) + "\n")
        for r in rows:
            f.write("\t".join("" if r.get(c) is None else str(r.get(c)) for c in cols) + "\n")

    L = []
    P = L.append
    n = len(rows)
    P(f"# 执行层普查（57_exec_census.mjs + 57_exec_census.py）：{n} 局带录像的对局包；逐局数字在 exec_census.tsv")
    P("")
    part = [r for r in rows if r["partial"]]
    short = [r for r in rows if r["replayShort"]]
    P(f"日志里的号不全在这份录像里的局（别的号在别的房间）：{len(part)} 局（" + "、".join(f"{r['matchId']} {r['bots']}/{r['logBots']}" for r in part) + "）；下面只算在场的号。")
    P(f"录像比日志短 180 拍以上的局（发出 vs 落地不对账）：{len(short)} 局（" + "、".join(f"{r['matchId']} 录像到 {r['lastTick']}、日志到 {r['logLastTick']}" for r in short) + "）")
    P(f"cmds 计数回绕过的局（同样不对账）：{sum(1 for r in rows if r['cmdsResets'])} 局")
    P("")
    P("## A. 选点指令")
    co = [r for r in rows if r.get("solves")]
    P(f"有出生协调器日志的 {len(co)} 局，{sum(r['firstBots'] for r in co)} 个号次：协调器第一次给的点没进录像的 {sum(r['firstMiss'] for r in co)} 个号次。")
    P(f"日志里的指派合计 {sum(r['asg'] for r in co):,}、宿主发出的选点指令合计 {sum(r['hostSpawn'] or 0 for r in co):,}、进了录像 {sum(r['spawnLanded'] for r in co):,}。")
    exc = [r for r in co if r["firstMiss"] < r["firstBots"]]
    P("协调器第一次给的点进了录像的例外：" + ("、".join(f"{r['matchId']} {r['firstBots'] - r['firstMiss']} 个号" for r in exc) if exc else "无"))
    ch = Counter(("0 次" if r["changes"] == 0 else "1~9 次" if r["changes"] < 10 else "10~29 次" if r["changes"] < 30 else "≥30 次") for r in co)
    P("协调器求解结果变过几次（局数）：" + "、".join(f"{k} {ch[k]}" for k in ("0 次", "1~9 次", "10~29 次", "≥30 次")))
    z = [r for r in co if r["endNone"]]
    P(f"有号一条选点指令都没进录像的局：{len(z)} 局" + ("（" + "、".join(f"{r['matchId']} {r['endNone']}/{r['bots']} 个号、求解 {r['solves']} 次变 {r['changes']} 次" for r in z) + "）" if z else ""))
    P(f"出生阶段结束时停在最后一次指派上的号 {sum(r['endLast'] for r in co)}；最后一次进了录像但被同一步里更早的那条盖掉 {sum(r['endOver'] for r in co)}；"
      f"最后一次没进录像、停在更早的指派上 {sum(r['endStale'] for r in co)}；一条都没进 {sum(r['endNone'] for r in co)}。")
    st = [r for r in co if r["endStale"] or r["endOver"]]
    P(f"至少一个号没停在最后一次指派上的局（不算一条都没进的）：{len(st)} 局：" + "、".join(f"{r['matchId']}（{r['endStale'] + r['endOver']}）" for r in st))
    P(f"同一步里同一个号落了 ≥2 条（指向不同点）的组：录像先后和发令先后相反 {sum(r['grpRev'] for r in co)} 组、相同 {sum(r['grpFwd'] for r in co)} 组、两种都说得通 {sum(r['grpBoth'] for r in co)} 组。")
    fs = [r["myFirstStep"] for r in co if r.get("myFirstStep") is not None]
    os_ = [r["othFirstStep"] for r in co if r.get("othFirstStep") is not None]
    if fs and os_:
        P(f"我方第一条进录像的选点指令在第几步：最小 {min(fs)}、中位 {statistics.median(fs):.0f}、最大 {max(fs)}；其他真人：最小 {min(os_)}、中位 {statistics.median(os_):.0f}、最大 {max(os_)}。")
    P(f"出生阶段结束之后才出现在录像里的选点指令：{sum(r['spawnAfterPhase'] for r in rows)} 条（全部 {n} 局）。")

    P("")
    P("## B. 指令成批落地（同一号同一拍 ≥3 条；进攻 / 捐款 / 船 / 追击）")
    P(f"我方：{sum(1 for r in rows if r['sqBatches'])} 局有批，合计 {sum(r['sqBatches'] for r in rows):,} 个批 {sum(r['sqBatchCmds'] for r in rows):,} 条（我方全部指令 {sum(r['squadCmds'] for r in rows):,} 条）；"
      f"正好 9 条的 {sum(r['sqBatch9'] for r in rows)} 批，超过 9 条的 {sum(r['sqBatchGt9'] for r in rows)} 批。")
    P(f"同场的同一批号（不在这个对局包里；另一个对局包的号、名字带 [APEX]、或名字在别的对局包的号名单里）：{sum(1 for r in rows if r['famSeats'])} 局有这样的席位、合计 {sum(r['famSeats'] for r in rows)} 个；"
      f"{sum(r['famBatches'] for r in rows):,} 个批 {sum(r['famBatchCmds'] for r in rows):,} 条（它们的全部指令 {sum(r['famCmds'] for r in rows):,} 条）；正好 9 条的 {sum(r['famBatch9'] for r in rows)} 批；最大一批 {max(r['famBatchMax'] for r in rows)} 条。")
    P(f"其他真人：{sum(1 for r in rows if r['otBatches'])} 局有批，合计 {sum(r['otBatches'] for r in rows):,} 个批 {sum(r['otBatchCmds'] for r in rows):,} 条（其他真人全部指令 {sum(r['otherCmds'] for r in rows):,} 条）；"
      f"正好 9 条的 {sum(r['otBatch9'] for r in rows)} 批；最大一批 {max(r['otBatchMax'] for r in rows)} 条。")
    cl = [r for r in rows if not r["mixed"]]
    P(f"其他真人，只算没有第二队同一批号的 {len(cl)} 局：{sum(r['otBatches'] for r in cl):,} 个批 {sum(r['otBatchCmds'] for r in cl):,} 条（全部指令 {sum(r['otherCmds'] for r in cl):,} 条）；正好 9 条的 {sum(r['otBatch9'] for r in cl)} 批。")
    P(f"我方落地拍不是 7 的倍数的指令：{sum(r['notMod7'] for r in rows)} 条。")
    bk = Counter(("0" if r["sqBatches"] == 0 else "1~9" if r["sqBatches"] < 10 else "10~29" if r["sqBatches"] < 30 else "30~59" if r["sqBatches"] < 60 else "≥60") for r in rows)
    P("每局我方的批数（局数）：" + "、".join(f"{k} 个批 {bk[k]} 局" for k in ("0", "1~9", "10~29", "30~59", "≥60")))
    per = [0, 0, 0, 0]
    for r in rows:
        for i, x in enumerate(r["sqBatchesByPeriod"].split("/")):
            per[i] += int(x)
    P(f"我方的批按落地拍：0~600 {per[0]}、600~1500 {per[1]}、1500~3000 {per[2]}、3000+ {per[3]}。")
    top = sorted(rows, key=lambda r: -r["sqBatches"])[:12]
    P("批最多的 12 局：" + "、".join(f"{r['matchId']}（{r['sqBatches']} 批 / {r['sqBatchCmds']} 条，{r['result']}）" for r in top))

    # 每个号每一帧（7 拍）落了几条：直接数缓存里的 humans_cmd.tsv。
    # 三类席位：1 = 这个对局包的号（我方）；F = 同场的同一批号（另一个对局包的号、名字带 [APEX]、或名字在别的对局包的号名单里）；0 = 其他真人。
    # 「没有第二队的局」= card.json 没有 sameMatchPeer、F 类席位不到 3 个：只有这些局里的「其他真人」能保证不混进同一批号。
    KEYS = (("1", "我方"), ("F", "同场的同一批号（不在这个对局包里）"), ("0", "其他真人（全部局）"), ("0c", "其他真人（没有第二队的局）"), ("0t", "其他真人里名字带战队标签或默认名 Player N 的"))
    sizes = {k: Counter() for k, _ in KEYS}
    nine = {k: [0, 0, 0] for k, _ in KEYS}    # 正好 9 条的帧数、其中下一帧（+1 回合）同一个号还有指令的、上一帧（−1 回合）有指令的
    gaps = {}                                 # (类, 帧里几条) -> [下一条指令隔 1 / 2 / 3 / ≥4 个回合的帧数, 上一条指令隔 1 / 2 / 3 / ≥4 个回合的帧数]
    # 大批（一个号一帧 ≥6 条）是不是几个号同时到：帧数、按「同一拍有几个号」分、同拍成对数（实际 / 各号互不相干时的期望）、前后 2 个回合内有别的号的大批
    sync = {k: {"frames": 0, "byK": Counter(), "obs": 0, "exp": 0.0, "near": 0, "games": 0} for k in ("1", "F", "0")}
    WS = (1, 2, 3, 4, 5, 6, 9, 12, 30)
    wmax = {k: {"players": 0, "cmds": 0, "max": {w: (0, "", "") for w in WS}, "hit9": 0, "over9": 0, "hit9names": []} for k, _ in KEYS}
    stalls = []                               # (局, 号, 落地拍, 静默回合数, 这段里队友落地条数, 队友按平时该落的条数, 其他真人落地条数, 其他真人按平时该落的条数, 这段里有没有队友的大批)
    bgaps = defaultdict(list)                 # 时段 -> [同一个号相邻两个 ≥8 条的批隔几个回合]
    TB = ((600, 900), (900, 1200), (1200, 1500), (1500, 1800), (1800, 2100), (2100, 2400), (2400, 3000), (3000, 10 ** 9))
    rr_cycles, rr_shift, rr_pairs, rr_games, rr_text = [], [], [0, 0], set(), []
    RR_EXAMPLES = {"A070": (1050, 2100), "A026": (1300, 2300), "A089": (900, 1600)}

    def win_max(cnt, w):
        rs = sorted(cnt)
        j = s = mx = 0
        for rr in rs:
            s += cnt[rr]
            while rs[j] <= rr - w:
                s -= cnt[rs[j]]
                j += 1
            mx = max(mx, s)
        return mx

    def tagged(name):
        nm = name.strip()
        return bool(re.search(r"\[[^\]]+\]", nm)) or bool(re.fullmatch(r"Player( \d+)?", nm))

    mixed = {r["matchId"]: r["mixed"] for r in rows}
    for mid in mids:
        per = defaultdict(Counter)            # 席位 -> {回合: 条数}
        sq, nm = {}, {}
        with open(os.path.join(ROOT, mid, "humans_cmd.tsv"), newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f, delimiter="\t"):
                per[row["p"]][int(row["t"]) // 7] += 1
                sq[row["p"]] = "1" if row["squad"] == "1" else ("0" if row["squad"] == "0" else "F")
                nm[row["p"]] = row["name"]

        def keys_of(pl):
            ks = [sq[pl]]
            if sq[pl] == "0":
                if not mixed[mid]:
                    ks.append("0c")
                if tagged(nm[pl]):
                    ks.append("0t")
            return ks

        for key in ("1", "F", "0"):
            big = defaultdict(set)
            nbig = Counter()
            for pl, cnt in per.items():
                if sq[pl] != key:
                    continue
                for t, k in cnt.items():
                    if k >= 6:
                        big[t].add(pl)
                        nbig[pl] += 1
            if not big:
                continue
            bt = sorted(big)
            rounds = bt[-1] - bt[0] + 1
            tot = sum(nbig.values())
            S = sync[key]
            S["games"] += 1
            S["frames"] += tot
            S["obs"] += sum(len(s) * (len(s) - 1) // 2 for s in big.values())
            S["exp"] += (tot * tot - sum(v * v for v in nbig.values())) / 2 / rounds
            for t, s in big.items():
                S["byK"][min(len(s), 5)] += len(s)
                for pl in s:
                    if any(o != pl for d in (-2, -1, 0, 1, 2) for o in big.get(t + d, ())):
                        S["near"] += 1
        for pl, cnt in per.items():
            ks = keys_of(pl)
            ts = sorted(cnt)
            for i, t in enumerate(ts):
                gk = gaps.setdefault((sq[pl], cnt[t]), [[0, 0, 0, 0], [0, 0, 0, 0]])
                if i + 1 < len(ts):
                    gk[0][min(ts[i + 1] - t, 4) - 1] += 1
                if i > 0:
                    gk[1][min(t - ts[i - 1], 4) - 1] += 1
            for t, k in cnt.items():
                for kk in ks:
                    sizes[kk][k] += 1
                    if k == 9:
                        nine[kk][0] += 1
                        nine[kk][1] += 1 if cnt.get(t + 1) else 0
                        nine[kk][2] += 1 if cnt.get(t - 1) else 0
            wm = {w: win_max(cnt, w) for w in WS}
            for kk in ks:
                W = wmax[kk]
                W["players"] += 1
                W["cmds"] += sum(cnt.values())
                for w in WS:
                    if wm[w] > W["max"][w][0]:
                        W["max"][w] = (wm[w], mid, nm[pl].strip())
                if wm[3] == 9:
                    W["hit9"] += 1
                    W["hit9names"].append(f"{mid} {nm[pl].strip()}")
                elif wm[3] > 9:
                    W["over9"] += 1

        # 一个号静默 ≥5 个回合之后落了一个 ≥6 条的批（落地拍 600~3000）：静默的这段里，队友和其他真人的指令照常落地吗
        mine = [pl for pl in per if sq[pl] == "1"]
        if len(mine) >= 5:
            r0, r1 = 600 // 7, min(3000, int(batches[mid]["lastTick"])) // 7
            n_r = max(1, r1 - r0)
            tm_round, ot_round, tm_big = Counter(), Counter(), Counter()
            for pl, cnt in per.items():
                if sq[pl] == "F":
                    continue
                tgt = tm_round if sq[pl] == "1" else ot_round
                for t, k in cnt.items():
                    tgt[t] += k
                    if sq[pl] == "1" and k >= 6:
                        tm_big[t] += 1
            tm_all = sum(v for t, v in tm_round.items() if r0 <= t < r1)
            ot_all = sum(v for t, v in ot_round.items() if r0 <= t < r1)
            for pl in mine:
                cnt = per[pl]
                ts = sorted(cnt)
                own = sum(cnt[t] for t in ts if r0 <= t < r1)
                for i in range(1, len(ts)):
                    t = ts[i]
                    if cnt[t] < 6 or not (r0 <= t < r1):
                        continue
                    sil = t - ts[i - 1] - 1
                    if sil < 5:
                        continue
                    span = range(ts[i - 1] + 1, t)
                    stalls.append((mid, nm[pl].strip(), t * 7, sil, sum(tm_round.get(x, 0) for x in span), (tm_all - own) / n_r * sil,
                                   sum(ot_round.get(x, 0) for x in span), ot_all / n_r * sil, 1 if any(tm_big.get(x) for x in span) else 0))
        # 各号的大批是不是按固定的先后顺序轮流落地：取这一局 600~3000 拍里 ≥8 条的批最多的号当参照，
        # 它相邻两批之间算一轮（≤120 个回合的才算）；别的号在这一轮里正好落一批的，记它在这一轮里的位置（0~1）。
        seqs = {}
        for pl in mine:
            v = sorted(t for t, k in per[pl].items() if k >= 8 and 600 // 7 <= t < 3000 // 7)
            if len(v) >= 4:
                seqs[pl] = v
        if len(seqs) >= 3:
            ref = max(seqs, key=lambda q: (len(seqs[q]), q))
            cyc = []
            for a0, a1 in zip(seqs[ref], seqs[ref][1:]):
                g = a1 - a0
                if g > 120:
                    cyc.append(None)
                    continue
                ph = {}
                for pl, v in seqs.items():
                    if pl == ref:
                        continue
                    inside = [t for t in v if a0 <= t < a1]
                    if len(inside) == 1:
                        ph[pl] = (inside[0] - a0) / g
                cyc.append(ph)
                rr_cycles.append((mid, g, len(ph), len(seqs) - 1))
            for c0, c1 in zip(cyc, cyc[1:]):
                if not c0 or not c1:
                    continue
                both = sorted(set(c0) & set(c1))
                for pl in both:
                    d = abs(c1[pl] - c0[pl])
                    rr_shift.append(min(d, 1 - d))
                for i in range(len(both)):
                    for j in range(i + 1, len(both)):
                        d0, d1 = c0[both[i]] - c0[both[j]], c1[both[i]] - c1[both[j]]
                        if d0 == 0 or d1 == 0:
                            continue
                        rr_pairs[0] += 1
                        rr_pairs[1] += 1 if (d0 > 0) == (d1 > 0) else 0
                        rr_games.add(mid)
        if mid in RR_EXAMPLES:
            lo, hi = RR_EXAMPLES[mid]
            ev = sorted((t, nm[pl].strip().split("] ")[-1], per[pl][t]) for pl in mine for t in per[pl] if per[pl][t] >= 6 and lo // 7 <= t < hi // 7)
            rr_text.append(f"  {mid}（落地拍 {lo}~{hi}；回合号:号名 条数）：" + " ".join(f"{t}:{b}×{k}" for t, b, k in ev))

        # 同一个号相邻两个 ≥8 条的批隔几个回合（中间零星落地 ≤2 条的才算）
        for pl, cnt in per.items():
            if sq[pl] != "1":
                continue
            ts = sorted(cnt)
            last = None
            between = 0
            for t in ts:
                if cnt[t] >= 8:
                    if last is not None and between <= 2:
                        for lo, hi in TB:
                            if lo <= t * 7 < hi:
                                bgaps[(lo, hi)].append(t - last)
                    last, between = t, 0
                else:
                    between += cnt[t]

    P("")
    P("## B2. 一个号在同一帧（7 拍）里落了几条（全部带录像的局；进攻 / 捐款 / 船 / 追击）")
    nmix = sum(1 for r in rows if r["mixed"])
    P(f"   席位分三类：我方 = 这个对局包的号；同场的同一批号 = 同一场里另一个对局包的号（card.json 的 sameMatchPeer）、名字带 [APEX] 的、名字在别的对局包号名单里的；其余算其他真人。")
    P(f"   同场有第二队同一批号的局（card.json 有 sameMatchPeer，或这类席位 ≥3 个）：{nmix} 局；这些局里第二队的号如果不在任何对局包的日志里，名字对不上，会混在「其他真人」里。")
    for key, lab in KEYS:
        c = sizes[key]
        if not c:
            continue
        P(f"{lab}：" + "、".join(f"{k} 条 {c[k]:,} 帧" for k in sorted(c)) + f"；最多 {max(c)} 条")
        P(f"  正好 9 条的 {nine[key][0]:,} 帧里，下一帧同一个号还有指令的 {nine[key][1]} 帧、上一帧有指令的 {nine[key][2]} 帧")

    P("")
    P("## B3. 一帧落了 k 条之后，同一个号的下一条指令隔几个回合（1 回合 = 7 拍）；之前的上一条隔几个回合")
    P("   谁 | 帧里几条 | 下一条隔 1 / 2 / 3 / ≥4 个回合的帧数 | 上一条隔 1 / 2 / 3 / ≥4 个回合的帧数")
    for key, lab in (("1", "我方"), ("F", "同一批号"), ("0", "其他真人")):
        for k in (9, 8, 7, 6, 5, 4, 3, 2, 1):
            gk = gaps.get((key, k))
            if gk:
                P(f"  {lab}\t{k}\t" + " / ".join(f"{x:,}" for x in gk[0]) + "\t" + " / ".join(f"{x:,}" for x in gk[1]))

    P("")
    P("## B4. 大批（一个号一帧落了 ≥6 条）是不是几个号同时到")
    P("   谁 | 有大批的局 | 大批的帧数（号 × 帧）| 其中同一拍只有它一个号 / 另有 1 个号 / 另有 2 个 / 另有 3 个 / 另有 ≥4 个号也落了大批 | 同一拍或前后 2 个回合内有别的号的大批 | 同拍成对数：实际 / 各号互不相干时的期望")
    for key, lab in (("1", "我方"), ("F", "同一批号"), ("0", "其他真人")):
        S = sync[key]
        if not S["frames"]:
            continue
        P(f"  {lab}\t{S['games']} 局\t{S['frames']:,}\t" + " / ".join(f"{S['byK'][k]:,}" for k in (1, 2, 3, 4, 5))
          + f"\t{S['near']:,}（{S['near'] / S['frames']:.0%}）\t{S['obs']:,} / {S['exp']:.1f}")
    P("  （期望 = 每局里把各号的大批帧随机撒在这一局第一个到最后一个大批之间的回合上，两个号撞在同一拍的对数；只是量级）")

    P("")
    P("## B5. 任何连续 W 个回合里，一个号最多落了几条（每个席位取自己全局的最大值，再在同一类里取最大）")
    P("   谁 | 席位数（号次）| 指令条数 | W = " + " / ".join(str(w) for w in WS) + " | 连续 3 个回合的最大值正好 9 条的席位 | 超过 9 条的席位")
    for key, lab in KEYS:
        W = wmax[key]
        if not W["players"]:
            continue
        P(f"  {lab}\t{W['players']:,}\t{W['cmds']:,}\t" + " / ".join(str(W["max"][w][0]) for w in WS) + f"\t{W['hit9']:,}\t{W['over9']}")
    for key, lab in (("0c", "其他真人（没有第二队的局）"), ("0t", "名字带战队标签或默认名的")):
        W = wmax[key]
        P(f"  {lab}里连续 3 个回合落满 9 条的席位：" + ("、".join(W["hit9names"]) if W["hit9names"] else "无"))
    W = wmax["0"]
    P("  其他真人里各个 W 的最大值出在：" + "、".join(f"W={w} {W['max'][w][1]} {W['max'][w][2]}（{W['max'][w][0]} 条）" for w in (3, 4, 6, 12, 30)))
    W = wmax["1"]
    P("  我方各个 W 的最大值出在：" + "、".join(f"W={w} {W['max'][w][1]} {W['max'][w][2]}（{W['max'][w][0]} 条）" for w in (3, 4, 6, 12, 30)))

    P("")
    P("## B6. 一个号静默 ≥5 个回合之后落了一个 ≥6 条的批（落地拍 600~3000；在场 ≥5 个号的局）：静默的这段里别人的指令照常落地吗")
    if stalls:
        sl = sorted(x[3] for x in stalls)
        tot_r = sum(x[3] for x in stalls)
        tm_in, tm_exp = sum(x[4] for x in stalls), sum(x[5] for x in stalls)
        ot_in, ot_exp = sum(x[6] for x in stalls), sum(x[7] for x in stalls)
        P(f"  这样的静默 {len(stalls):,} 段，分布在 {len({x[0] for x in stalls})} 局、{len({(x[0], x[1]) for x in stalls})} 个号次；静默长度（回合）中位 {statistics.median(sl):.0f}、P90 {sl[int(0.9 * (len(sl) - 1))]}、最大 {sl[-1]}；合计 {tot_r:,} 个回合")
        P(f"  这些回合里队友（同一个对局包的其他号）落地 {tm_in:,} 条 = 每回合 {tm_in / tot_r:.2f} 条；按各局 600~3000 拍队友的平均速度该落 {tm_exp:,.0f} 条 = 每回合 {tm_exp / tot_r:.2f} 条；实际 ÷ 平时 = {tm_in / tm_exp:.2f}")
        P(f"  这些回合里其他真人落地 {ot_in:,} 条 = 每回合 {ot_in / tot_r:.2f} 条；按各局 600~3000 拍的平均速度该落 {ot_exp:,.0f} 条 = 每回合 {ot_exp / tot_r:.2f} 条；实际 ÷ 平时 = {ot_in / ot_exp:.2f}")
        P(f"  静默的这段里队友至少落了 1 条的：{sum(1 for x in stalls if x[4] > 0):,} 段（{sum(1 for x in stalls if x[4] > 0) / len(stalls):.1%}）；其他真人至少落了 1 条的：{sum(1 for x in stalls if x[6] > 0):,} 段（{sum(1 for x in stalls if x[6] > 0) / len(stalls):.1%}）；"
          f"队友在这段里落过大批（≥6 条）的：{sum(x[8] for x in stalls):,} 段（{sum(x[8] for x in stalls) / len(stalls):.1%}）")
        lg = sorted(stalls, key=lambda x: -x[3])[:6]
        P("  最长的 6 段：" + "、".join(f"{x[0]} {x[1]} 落地拍 {x[2]}（静默 {x[3]} 个回合，其间队友落地 {x[4]} 条、其他真人 {x[6]} 条）" for x in lg))

    P("")
    P("## B7. 同一个号相邻两个 ≥8 条的批隔几个回合（中间零星落地 ≤2 条的才算；按后一个批的落地拍分段）")
    P("   时段 | 对数 | 间隔（回合）中位 / P90 / 最大")
    for lo, hi in TB:
        v = sorted(bgaps.get((lo, hi), []))
        if v:
            P(f"  {lo}~{hi if hi < 10 ** 9 else ''}\t{len(v):,}\t{statistics.median(v):.1f} / {v[int(0.9 * (len(v) - 1))]} / {v[-1]}")
    allg = sorted(x for v in bgaps.values() for x in v)
    if allg:
        P(f"  合计\t{len(allg):,}\t{statistics.median(allg):.1f} / {allg[int(0.9 * (len(allg) - 1))]} / {allg[-1]}；间隔正好 3 个回合的 {sum(1 for x in allg if x == 3)} 对、不到 3 个回合的 {sum(1 for x in allg if x < 3)} 对")

    P("")
    P("## B9. 同一局里各号的大批是不是按固定的先后顺序轮流落地（600~3000 拍；≥8 条的批；一局里至少 3 个号各有 ≥4 个这样的批）")
    if rr_cycles:
        gs = sorted(c[1] for c in rr_cycles)
        P(f"  参照号（这一局里批最多的号）相邻两批之间算一轮：{len(rr_cycles):,} 轮，分布在 {len({c[0] for c in rr_cycles})} 局；一轮的长度（回合）中位 {statistics.median(gs):.0f}、P90 {gs[int(0.9 * (len(gs) - 1))]}")
        P(f"  一轮里别的号正好落一批的：{sum(c[2] for c in rr_cycles):,} 个号次（这些轮里别的有批的号合计 {sum(c[3] for c in rr_cycles):,} 个号次）")
        if rr_pairs[0]:
            P(f"  相邻两轮里都正好落一批的两个号，谁先谁后保持不变的：{rr_pairs[1]:,} / {rr_pairs[0]:,} 对（{rr_pairs[1] / rr_pairs[0]:.0%}；各号互不相干时是 50%）；涉及 {len(rr_games)} 局")
        if rr_shift:
            sh = sorted(rr_shift)
            P(f"  同一个号在相邻两轮里的位置（0~1）差多少：中位 {statistics.median(sh):.2f}、P90 {sh[int(0.9 * (len(sh) - 1))]:.2f}（{len(sh):,} 个号次；互不相干时中位 0.25）")
    P("  例子（一个号一帧 ≥6 条的批，按落地的回合排）：")
    for t in rr_text:
        P(t)

    P("")
    P("## B8. 策略自己的耗时（[HL-TICK] 行尾的 avgMs / maxMs / skip；在场的号）")
    ms = [r for r in rows if r.get("tickLines")]
    P(f"  {len(ms)} 局、{sum(r['tickLines'] for r in ms):,} 行 [HL-TICK] 带这三项：skip 不是 0 的 {sum(r['skipLines'] for r in ms):,} 行；avgMs 最大 {max(r['avgMsMax'] for r in ms):.2f}；"
      f"maxMs ≥56（一拍）的 {sum(r['maxMsGe56'] for r in ms):,} 行、≥392（一个回合）的 {sum(r['maxMsGe392'] for r in ms):,} 行；maxMs 最大 {max(r['maxMsMax'] for r in ms):.1f}")
    big_ms = sorted((r for r in ms if r["maxMsGe392"]), key=lambda r: -r["maxMsMax"])[:8]
    if big_ms:
        P("  maxMs ≥392 的局：" + "、".join(f"{r['matchId']}（最大 {r['maxMsMax']:.0f}，{r['maxMsGe392']} 行）" for r in big_ms))

    P("")
    P("## C. 发出 vs 落地（进攻和船；真号 cmds 计数减捐款 vs 录像）")
    fv = [r for r in rows if r.get("atkIssued")]
    P(f"能对账的 {len(fv)} 局：发出 {sum(r['atkIssued'] for r in fv):,}、落地 {sum(r['atkLanded'] for r in fv):,}、没落地 {sum(r['atkMiss'] for r in fv):,}。")
    mk = Counter(("<2%" if r["atkMiss"] / r["atkIssued"] < 0.02 else "2%~10%" if r["atkMiss"] / r["atkIssued"] < 0.10 else "10%~25%" if r["atkMiss"] / r["atkIssued"] < 0.25 else "≥25%") for r in fv)
    P("没落地占发出的比例（局数）：" + "、".join(f"{k} {mk[k]} 局" for k in ("<2%", "2%~10%", "10%~25%", "≥25%")))
    P(f"一定晚 >90 拍的条数（不靠影子的下限）：合计 {sum(r['late90'] for r in fv):,}（600~1500 {sum(r['late90_600_1500'] for r in fv):,}、1500~3000 {sum(r['late90_1500_3000'] for r in fv):,}、3000+ {sum(r['late90_3000'] for r in fv):,}）；"
      f"有这种指令的局 {sum(1 for r in fv if r['late90'])} 局；一定晚 >180 拍的 {sum(r['late180'] for r in fv):,} 条。")
    top = sorted(fv, key=lambda r: -r["atkMiss"] / r["atkIssued"])[:12]
    P("没落地比例最高的 12 局：" + "、".join(f"{r['matchId']}（{r['atkMiss']}/{r['atkIssued']} = {r['atkMiss'] / r['atkIssued']:.0%}，批 {r['sqBatches']}，{r['result']}）" for r in top))
    P(f"捐款：日志 [HL-DISPATCH] 合计 {sum(r['dispatch'] for r in fv):,} 条、录像里我方捐款指令 {sum(r['donLanded'] for r in fv):,} 条。")

    P("")
    P("## C2. 被判离开的席位（results.csv 里 event=left；只是下限）")
    lf = [r for r in rows if r["leftBefore3000"]]
    P(f"t<3000 就有号被判离开的局：{len(lf)} 局、{sum(r['leftBefore3000'] for r in lf)} 个号（全部 {n} 局里在场的号合计 {sum(r['bots'] for r in rows)} 个）；"
      f"其中 ≥5 个号的：" + "、".join(f"{r['matchId']}（{r['leftBefore3000']}/{r['bots']}，拍 {r['leftTicks']}，{r['result']}）" for r in lf if r["leftBefore3000"] >= 5))
    P("其余：" + "、".join(f"{r['matchId']}（{r['leftBefore3000']}）" for r in lf if r["leftBefore3000"] < 5))
    lf_ids = {r["matchId"] for r in lf}
    a = [r for r in fv if r["matchId"] in lf_ids]
    b = [r for r in fv if r["matchId"] not in lf_ids]
    for lab, rs in (("有号在 t<3000 被判离开的局", a), ("没有的局", b)):
        if rs:
            miss = [r["atkMiss"] / r["atkIssued"] for r in rs]
            P(f"{lab}（能对账的 {len(rs)} 局）：没落地比例中位 {statistics.median(miss):.1%}、≥25% 的 {sum(1 for x in miss if x >= 0.25)} 局；批数中位 {statistics.median([r['sqBatches'] for r in rs]):.0f}；"
              + "、".join(f"{k or '?'} {v}" for k, v in Counter(r["result"] for r in rs).most_common()))

    P("")
    P("## D. 和结果的对照（只是并排放，不是因果）")
    for key, lab in (("result", "结果"), ("cohort", "编队"), ("ver", "一代")):
        g = defaultdict(list)
        for r in fv:
            g[r.get(key) or "?"].append(r)
        for k, rs in sorted(g.items(), key=lambda kv: -len(kv[1])):
            miss = [r["atkMiss"] / r["atkIssued"] for r in rs]
            P(f"{lab} {k}：{len(rs)} 局；没落地比例中位 {statistics.median(miss):.1%}、≥10% 的 {sum(1 for x in miss if x >= 0.10)} 局；批数中位 {statistics.median([r['sqBatches'] for r in rs]):.0f}、"
              f"≥30 个批的 {sum(1 for r in rs if r['sqBatches'] >= 30)} 局；有一定晚 >90 拍指令的 {sum(1 for r in rs if r['late90'])} 局")
    hv = [r for r in fv if r["atkMiss"] / r["atkIssued"] >= 0.10 or r["sqBatches"] >= 30]
    wc = Counter(r["result"] for r in hv)
    wa = Counter(r["result"] for r in fv)
    P(f"没落地 ≥10% 或批 ≥30 的 {len(hv)} 局里：" + "、".join(f"{k or '?'} {v}" for k, v in wc.most_common()) + f"；全部 {len(fv)} 局里：" + "、".join(f"{k or '?'} {v}" for k, v in wa.most_common()))

    open(os.path.join(CROSS, "exec_census.txt"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
