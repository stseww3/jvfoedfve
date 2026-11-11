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
TICK_RE = re.compile(r"\[(\w+)\] \[HL-TICK\] t=(\d+) .*?cmds=(\d+)")


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
    return ("协调器" if coord else "无协调器") + (f"·{tag}" if tag else ""), last_tick, resets


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
        ver, log_last, resets = log_facts(mid, allow)
        r = {"matchId": mid, "cohort": c.get("cohort", ""), "result": c.get("_result", ""), "ver": ver, "humans": int(b["humans"]), "logBots": int(b["logBots"]),
             "bots": int(b["squadBots"]), "lastTick": int(b["lastTick"]), "logLastTick": log_last, "cmdsResets": resets}
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
                  "spawnAfterPhase": int(b["spawnCmdsAfterPhase"])})
        rows.append(r)

    cols = ["matchId", "cohort", "ver", "result", "humans", "logBots", "bots", "partial", "lastTick", "logLastTick", "replayShort", "cmdsResets", "leftAll", "leftBefore3000", "leftTicks", "solves", "changes", "asg", "hostSpawn", "spawnLanded", "firstMiss", "firstBots", "endLast",
            "endOver", "endStale", "endNone", "grpRev", "grpFwd", "grpBoth", "myFirstStep", "othFirstStep", "issued", "landed", "dispatch", "donLanded", "atkIssued",
            "atkLanded", "atkMiss", "late90", "late90_600_1500", "late90_1500_3000", "late90_3000", "late180", "squadCmds", "sqBatches", "sqBatchCmds", "sqBatch9", "sqBatchGt9",
            "sqBatchMax", "sqBatchesByPeriod", "otherCmds", "otBatches", "otBatchCmds", "otBatchMax", "notMod7", "spawnAfterPhase"]
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
    P(f"其他真人：{sum(1 for r in rows if r['otBatches'])} 局有批，合计 {sum(r['otBatches'] for r in rows):,} 个批 {sum(r['otBatchCmds'] for r in rows):,} 条（其他真人全部指令 {sum(r['otherCmds'] for r in rows):,} 条）；最大一批 {max(r['otBatchMax'] for r in rows)} 条。")
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

    # 每个号每一帧（7 拍）落了几条：直接数缓存里的 humans_cmd.tsv
    sizes = {"1": Counter(), "0": Counter()}
    nine = {"1": [0, 0, 0], "0": [0, 0, 0]}   # 正好 9 条的帧数、其中下一帧（+7 拍）同一个号还有指令的、上一帧（−7 拍）有指令的
    for mid in mids:
        per = defaultdict(Counter)
        sq = {}
        with open(os.path.join(ROOT, mid, "humans_cmd.tsv"), newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f, delimiter="\t"):
                per[row["p"]][int(row["t"])] += 1
                sq[row["p"]] = row["squad"]
        for pl, cnt in per.items():
            for t, k in cnt.items():
                sizes[sq[pl]][k] += 1
                if k == 9:
                    nine[sq[pl]][0] += 1
                    nine[sq[pl]][1] += 1 if cnt.get(t + 7) else 0
                    nine[sq[pl]][2] += 1 if cnt.get(t - 7) else 0
    P("")
    P("## B2. 一个号在同一帧（7 拍）里落了几条（全部带录像的局；进攻 / 捐款 / 船 / 追击）")
    for key, lab in (("1", "我方"), ("0", "其他真人")):
        c = sizes[key]
        P(f"{lab}：" + "、".join(f"{k} 条 {c[k]:,} 帧" for k in sorted(c)) + f"；最多 {max(c)} 条")
        P(f"{lab}正好 9 条的 {nine[key][0]:,} 帧里，下一帧同一个号还有指令的 {nine[key][1]} 帧、上一帧有指令的 {nine[key][2]} 帧")

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
