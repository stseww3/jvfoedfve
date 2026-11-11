#!/usr/bin/env python3
"""xtruth.py — 发现集全部录像的「开局段真值」跨局计数（到 t=1800）：人均对照的走势、内置 AI 的地谁吃了、
陆攻落地后有没有生效、出生点几何、日志里发出的指令和录像里落地的指令对不对得上。

先出每局的压缩真值表（重计算闸；一局 0.3~4 秒，105 局合计约 2 分钟，分批跑）：
    bash c136-review/tools/run-heavy.sh node c136-review/agents/R08/scripts/xtruth.mjs <局> <局> …
    （指令流另见 xbatch.py 文件头的 replay_cmds.mjs 那一步）
再计数：
    python3 xtruth.py [--quiet]        → out/_cross/xtruth.txt、xtruth.json

只读 /agent/repos/c136-data/bundles/（发现集，局号取自 manifest.jsonl 里 split == "discovery" 的行）；验证集不碰。
out/_run/ 不入库，随时可以按上面两步重建。

席位分组和 xbatch.py 完全一样（own / [APEX] / 名字池 / 野人；机器号 = 前三组）。own 的认法：facts 里这支编队的号，
且录像里这个席位的名字以它的某个日志标签结尾。一局「对得上」= 重演出来的地 / 兵和 traj.csv 的快照逐行相等的 ≥90%
（至少 10 行）——对不上说明包里的录像是别的房间的，这局不进 own 的统计。

口径：
  · 人均对照 = 这一拍还有地的 own 号的人均地 ÷ 还有地的野人的人均地（两边各至少 3 / 5 个号才算）。另给「按出生人数」口径
    （死掉的号按 0 算进分母），防「野人里死掉的不算」把对照抬高。
  · 掉队 = t=630 时人均对照 ≥0.90，且 t=1500 时 ≤ t=630 的 0.75 倍。
  · AI 的地 = (600,1500] 里真人从内置 AI 手里吃下的格（AI 之间互吃、AI 被淘汰后变无主地再被吃的不算）；
    份额对照 = own 吃到的份额 ÷ own 在 t=600 还有地的真人里的人头份额。
  · 无主地 = (0,600] 里真人吃下的无主地格；份额对照同上，人头按出生人数。
  · 陆攻落地后生效 = 录像里落地的陆攻指令，引擎真的派出了兵（没有因为目标没了 / 不接壤 / 兵不够被作废）。
  · 贴边 = 出生点离地图边 ≤ 短边的 12%。
  · 发出 vs 落地 = 日志 HL-TICK 的 cmds 计数增量（策略在自己视角里发出的条数） vs 录像里这个席位落地的陆攻 + 捐款 + 船；
    两边都按日志快照的拍切段（快照 90 拍一条），录像到哪算到哪。卡顿时落地会晚到下一段，分段只看量级。
节：
  [XT-A] 覆盖与核对  [XT-B] 人均对照走势  [XT-C] AI 的地 / 无主地  [XT-D] 陆攻生效率  [XT-E] 出生点  [XT-F] 发出 vs 落地
  [XT-G] 1800 拍前出局 / 离开  [XT-H] 逐局
"""
import json
import math
import os
import re
import statistics
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import facts  # noqa: E402
import r08lib as L  # noqa: E402
from xbatch import name_pool, discovery_ids, MINE  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")
RUN = os.path.join(OUT, "_run", "xtruth")
STREAMS = os.path.join(OUT, "_run", "streams")
CP = [300, 600, 630, 900, 1260, 1500, 1800]
GROUPS = ("own", "apex", "pool", "wild")
GROUP_CN = dict(own="本编队", apex="[APEX]", pool="名字池", wild="野人", bot="机器号")
LOGPER = [("0~600", 0, 600), ("600~1500", 600, 1500), ("1500~3000", 1500, 3000), ("3000+", 3000, 10 ** 9)]
COHORTS = ("squad10", "squad20", "squad8")


def med(v):
    return statistics.median(v) if v else None


def fmt(x, nd=2):
    return "—" if x is None else f"{x:.{nd}f}"


def pct(a, b):
    return "—" if not b else f"{100 * a / b:.0f}%"


def scan(mid, row, pool):
    p = os.path.join(RUN, f"{mid}.json")
    if not os.path.exists(p):
        return None
    X = json.load(open(p, encoding="utf-8"))
    if "error" in X:
        return dict(matchId=mid, error=X["error"])
    H = X["H"]
    names = [str(x).strip() for x in X["names"]] + [""] * H
    low = [x.lower() for x in names]
    F = facts.build(mid)
    own = {}
    for me, b in F["bots"].items():
        mr = b.get("meReal") if b.get("meReal") is not None else me
        if mr is not None and 0 <= mr < H and any(low[mr].endswith(lab.lower()) for lab in b["labels"]):
            own[mr] = b
    v = X["validate"]
    spawn_only = X["endTick"] <= 1
    valid = bool(own) and ((v["rows"] >= 10 and v["bothExact"] >= 0.9 * v["rows"]) or (spawn_only and len(own) >= 5))
    if not valid:
        own = {}
    grp = {}
    for q in range(H):
        if q in own:
            grp[q] = "own"
        elif "[apex]" in low[q]:
            grp[q] = "apex"
        elif low[q] in pool or re.sub(r"^\[[^\]]*\]\s*", "", low[q]) in pool:
            grp[q] = "pool"
        else:
            grp[q] = "wild"
    xy = X["spawnXY"]
    spawned = [q for q in range(H) if xy[q]]
    oc = row.get("outcome") or {}
    rec = dict(matchId=mid, cohort=row.get("cohort"), mode=row.get("mode"), won=bool(oc.get("primaryTeamWon")), label=oc.get("resultLabel"),
               H=H, land=X["land"], endTick=X["endTick"], valid=valid, spawnOnly=spawn_only, rows=v["rows"], exact=v["bothExact"],
               size={g: sum(1 for q in spawned if grp[q] == g) for g in GROUPS}, nTeams=X["nTeams"])

    # ---- 人均对照 ----
    ph = {}
    for t in CP:
        c = X["cp"].get(str(t))
        if not c:
            continue
        cell = {}
        for g in GROUPS + ("bot",):
            sel = [q for q in spawned if (grp[q] == g if g != "bot" else grp[q] != "wild")]
            alive = [q for q in sel if c["terr"][q] > 0]
            cell[g] = dict(n=len(alive), spawned=len(sel), land=sum(c["terr"][q] for q in alive), bal=sum(c["bal"][q] for q in alive))
        ai = X["aiAt"].get(str(t))
        cell["aiLand"] = sum(a[1] for a in ai) if ai is not None else None
        cell["aiN"] = len(ai) if ai is not None else None
        ph[t] = cell
    rec["ph"] = ph

    def ratio(t, g, basis="alive"):
        c = ph.get(t)
        if not c:
            return None
        a, w = c[g], c["wild"]
        if a["n"] < 3 or w["n"] < 5:
            return None
        if basis == "alive":
            return (a["land"] / a["n"]) / (w["land"] / w["n"])
        return (a["land"] / a["spawned"]) / (w["land"] / w["spawned"])

    rec["ratio"] = {g: {t: ratio(t, g) for t in CP} for g in ("own", "apex", "pool", "bot")}
    rec["ratioSpawned"] = {g: {t: ratio(t, g, "spawned") for t in CP} for g in ("own", "bot")}
    rec["densRatio"] = {}
    for t in CP:
        c = ph.get(t)
        if c and c["own"]["n"] >= 3 and c["wild"]["n"] >= 5 and c["own"]["land"] and c["wild"]["land"]:
            rec["densRatio"][t] = (c["own"]["bal"] / c["own"]["land"]) / (c["wild"]["bal"] / c["wild"]["land"])

    # ---- 吃地 ----
    win = X["win"]
    gain = X["gain"]

    def harvest(k_list, col):
        return {g: sum(gain[k][q][col] for k in k_list for q in spawned if (grp[q] == g)) for g in GROUPS}

    rec["neutral0_600"] = harvest([0], 2) if X["endTick"] >= 600 else None
    rec["ai600_1500"] = harvest([1, 2, 3], 0) if X["endTick"] >= 1500 else None
    rec["aiBurn600_1500"] = harvest([1, 2, 3], 1) if X["endTick"] >= 1500 else None
    rec["human600_1500"] = harvest([1, 2, 3], 4) if X["endTick"] >= 1500 else None
    rec["lostToHuman600_1500"] = harvest([1, 2, 3], 6) if X["endTick"] >= 1500 else None
    rec["ai1500_1800"] = harvest([4], 0) if X["endTick"] >= 1800 else None

    # ---- 陆攻生效 ----
    per = X["per"]
    cm = []
    for k in range(len(per) - 1):
        if X["endTick"] < per[k + 1]:
            cm.append(None)
            continue
        cell = {}
        for g in GROUPS:
            sel = [q for q in spawned if grp[q] == g]
            cell[g] = dict(seats=len(sel), land=sum(X["cmds"][k][q][0] for q in sel), ok=sum(X["cmds"][k][q][1] for q in sel),
                           t512=sum(X["cmds"][k][q][2] for q in sel), boats=sum(X["cmds"][k][q][3] for q in sel),
                           don=sum(X["cmds"][k][q][4] for q in sel), donOk=sum(X["cmds"][k][q][5] for q in sel))
        cm.append(cell)
    rec["cmds"] = cm

    # ---- 出生点 ----
    W, Hh = X["W"], X["Hh"]
    lim = round(0.12 * min(W, Hh))
    sp = {g: dict(n=0, nearEdge=0, edge=[], nnBot=0, nnOwn=0, nn=[], picks=[]) for g in GROUPS}
    for q in spawned:
        x, y = xy[q]
        e = min(x, y, W - 1 - x, Hh - 1 - y)
        best, bq = None, None
        for r in spawned:
            if r == q:
                continue
            d = math.hypot(xy[r][0] - x, xy[r][1] - y)
            if best is None or d < best:
                best, bq = d, r
        s = sp[grp[q]]
        s["n"] += 1
        s["edge"].append(e)
        s["picks"].append(X["nPicks"][q])
        if e <= lim:
            s["nearEdge"] += 1
        if bq is not None:
            s["nn"].append(round(best))
            if grp[bq] != "wild":
                s["nnBot"] += 1
            if grp[bq] == "own":
                s["nnOwn"] += 1
    rec["spawn"] = {g: dict(n=s["n"], nearEdge=s["nearEdge"], edgeMed=med(s["edge"]), nnBot=s["nnBot"], nnOwn=s["nnOwn"], nnMed=med(s["nn"]), picksMed=med(s["picks"])) for g, s in sp.items()}
    rec["edgeLimit"] = lim

    # ---- 1800 拍前出局 / 离开 ----
    ex = {}
    for g in GROUPS:
        sel = [q for q in spawned if grp[q] == g]
        ex[g] = dict(n=len(sel), dead=sum(1 for q in sel if 0 < X["deathT"][q] <= X["endTick"]), left=sum(1 for q in sel if 0 < X["leftT"][q] <= X["endTick"]),
                     dead900=sum(1 for q in sel if 0 < X["deathT"][q] <= 900))
    rec["exits"] = ex

    # ---- 发出 vs 落地（日志 vs 录像）----
    sp_path = os.path.join(STREAMS, f"{mid}.json")
    fl = []
    if own and os.path.exists(sp_path) and not spawn_only:
        S = json.load(open(sp_path, encoding="utf-8"))
        last = S["meta"]["lastTick"]
        by = defaultdict(list)
        for t, cid, pl, _dx, _dz in S["cmds"]:
            if cid in (1, 2, 3) and pl in own:
                by[pl].append(t)
        for name, a, z in LOGPER:
            issued = landed = bots = 0
            for q, b in own.items():
                tk = [s for s in b["ticks"] if s["t"] <= min(z, last)]
                if not tk:
                    continue
                s1 = tk[-1]
                s0 = [s for s in tk if s["t"] <= a]
                t0, c0 = (s0[-1]["t"], s0[-1]["cmds"]) if s0 else (0, 0)
                if s1["t"] <= t0:
                    continue
                bots += 1
                issued += s1["cmds"] - c0
                landed += sum(1 for t in by[q] if t0 < t <= s1["t"])
            fl.append(dict(period=name, bots=bots, issued=issued, landed=landed))
    rec["flow"] = fl
    return rec


def main():
    quiet = "--quiet" in sys.argv
    pool = name_pool()
    ids = discovery_ids()
    recs, failed, noreplay = [], [], 0
    for mid, row in ids:
        if not os.path.exists(os.path.join(L.DATA, "bundles", mid, "replay.txt")):
            noreplay += 1
            continue
        r = scan(mid, row, pool)
        if r is None or "error" in r:
            failed.append((mid, (r or {}).get("error", "没有压缩真值表")))
            continue
        recs.append(r)
    out = []
    P = out.append
    val = [r for r in recs if r["valid"]]
    full = [r for r in val if not r["spawnOnly"]]

    P(f"[XT-A] 覆盖与核对：发现集 {len(ids)} 局，其中没有录像 {noreplay} 局；有录像 {len(ids) - noreplay} 局里重演成功 {len(recs)} 局、失败 {len(failed)} 局"
      + ("（" + "；".join(f"{m}：{e[-40:]}" for m, e in failed) + "）" if failed else ""))
    P(f"  对得上（重演的地 / 兵和日志快照逐行相等 ≥90%，至少 10 行；或者录像只有出生期而按名字认出 ≥5 个号）：{len(val)} 局；"
      f"其中录像只有出生期（lastTick ≤1）{sum(1 for r in val if r['spawnOnly'])} 局")
    P(f"  对不上、不进 own 统计的：{'、'.join(r['matchId'] + '（' + str(r['exact']) + '/' + str(r['rows']) + '）' for r in recs if not r['valid']) or '无'}")
    rows_t = sum(r["rows"] for r in full)
    exact_t = sum(r["exact"] for r in full)
    P(f"  对得上且有对局段的 {len(full)} 局：日志快照合计 {rows_t} 行，重演的地和兵都逐位相等 {exact_t} 行（{100 * exact_t / max(1, rows_t):.2f}%）")
    P("  录像覆盖到哪一拍（对得上且有对局段的局数）：" + "；".join(f"≥{t} 拍 {sum(1 for r in full if r['endTick'] >= t)} 局" for t in (600, 900, 1260, 1500, 1800)))
    P("  按编队档：" + "；".join(f"{c} 对得上 {sum(1 for r in val if r['cohort'] == c)} 局（到 1500 拍的 {sum(1 for r in full if r['cohort'] == c and r['endTick'] >= 1500)} 局）" for c in COHORTS))
    P(f"  席位合计（出过生的真人）：" + "；".join(f"{GROUP_CN[g]} {sum(r['size'][g] for r in recs)}" for g in GROUPS))

    # ---- [XT-B] ----
    P("")
    P("[XT-B] 人均对照走势（真值；own 还有地的号的人均地 ÷ 野人的人均地）")
    P("  拍 | 局数 | 中位 | 下四分位 ~ 上四分位 | <0.70 的局 | <1.00 的局 || squad10 中位（局数） | squad20 中位（局数） | squad8 中位（局数） || 主队赢的局 中位（局数） | 没赢的局 中位（局数）")
    agg_b = {}
    for t in CP:
        vals = [(r, r["ratio"]["own"][t]) for r in full if r["ratio"]["own"].get(t) is not None]
        if not vals:
            continue
        xs = sorted(v for _, v in vals)
        q1, q3 = xs[len(xs) // 4], xs[(3 * len(xs)) // 4]
        by_c = []
        for c in COHORTS:
            cv = [v for r, v in vals if r["cohort"] == c]
            by_c.append(f"{fmt(med(cv))}（{len(cv)}）")
        wv = [v for r, v in vals if r["won"]]
        lv = [v for r, v in vals if not r["won"]]
        P(f"  {t:>5} | {len(xs)} | {med(xs):.2f} | {q1:.2f} ~ {q3:.2f} | {sum(1 for v in xs if v < 0.7)} | {sum(1 for v in xs if v < 1.0)} || " + " | ".join(by_c)
          + f" || {fmt(med(wv))}（{len(wv)}） | {fmt(med(lv))}（{len(lv)}）")
        agg_b[t] = dict(n=len(xs), median=med(xs), q1=q1, q3=q3, below07=sum(1 for v in xs if v < 0.7), below1=sum(1 for v in xs if v < 1.0),
                        byCohort={c: dict(n=sum(1 for r, v in vals if r["cohort"] == c), median=med([v for r, v in vals if r["cohort"] == c])) for c in COHORTS},
                        won=dict(n=len(wv), median=med(wv)), lost=dict(n=len(lv), median=med(lv)))
    P("  同一张表，按出生人数口径（死掉的号按 0 算）：" + "；".join(
        f"t={t} 中位 {fmt(med([r['ratioSpawned']['own'][t] for r in full if r['ratioSpawned']['own'].get(t) is not None]))}" for t in CP))
    P("  机器号合计（own + [APEX] + 名字池）÷ 野人，全部重演成功的局：" + "；".join(
        f"t={t} 中位 {fmt(med([r['ratio']['bot'][t] for r in recs if r['ratio']['bot'].get(t) is not None]))}（{sum(1 for r in recs if r['ratio']['bot'].get(t) is not None)} 局）" for t in CP))
    P("  [APEX] 席位（不在 own 里的）÷ 野人：" + "；".join(
        f"t={t} 中位 {fmt(med([r['ratio']['apex'][t] for r in recs if r['ratio']['apex'].get(t) is not None]))}（{sum(1 for r in recs if r['ratio']['apex'].get(t) is not None)} 局）" for t in CP))
    P("  名字池席位（不在 own 里的）÷ 野人：" + "；".join(
        f"t={t} 中位 {fmt(med([r['ratio']['pool'][t] for r in recs if r['ratio']['pool'].get(t) is not None]))}（{sum(1 for r in recs if r['ratio']['pool'].get(t) is not None)} 局）" for t in CP))
    P("  兵密度对照（own 的兵 ÷ 地，再 ÷ 野人的同口径）：" + "；".join(
        f"t={t} 中位 {fmt(med([r['densRatio'][t] for r in full if t in r['densRatio']]))}" for t in CP))
    # 掉队
    both = [r for r in full if r["ratio"]["own"].get(630) is not None and r["ratio"]["own"].get(1500) is not None]
    drop = [r for r in both if r["ratio"]["own"][630] >= 0.9 and r["ratio"]["own"][1500] <= 0.75 * r["ratio"]["own"][630]]
    fall = [r for r in both if r["ratio"]["own"][1500] < r["ratio"]["own"][630]]
    low630 = [r for r in both if r["ratio"]["own"][630] < 0.9]
    P(f"  掉队（t=630 时 ≥0.90 且 t=1500 时 ≤ 630 时的 0.75 倍）：两拍都有数的 {len(both)} 局里 {len(drop)} 局命中；t=1500 比 t=630 低的 {len(fall)} 局；"
      f"t=630 时就 <0.90 的 {len(low630)} 局")
    P("    按编队档：" + "；".join(f"{c} {sum(1 for r in drop if r['cohort'] == c)}/{sum(1 for r in both if r['cohort'] == c)}" for c in COHORTS)
      + f"｜主队赢的局 {sum(1 for r in drop if r['won'])}/{sum(1 for r in both if r['won'])}，没赢的局 {sum(1 for r in drop if not r['won'])}/{sum(1 for r in both if not r['won'])}")
    rr = [r["ratio"]["own"][1500] / r["ratio"]["own"][630] for r in both]
    P(f"    t=1500 ÷ t=630 的比值：中位 {fmt(med(rr))}，下四分位 {fmt(sorted(rr)[len(rr) // 4]) if rr else '—'}，上四分位 {fmt(sorted(rr)[(3 * len(rr)) // 4]) if rr else '—'}；"
      f"没掉的局（比值 ≥1）：{'、'.join(r['matchId'] for r in both if r['ratio']['own'][1500] >= r['ratio']['own'][630]) or '无'}")
    by_h = []
    for lo, hi, nm in ((0, 30, "≤30 席"), (31, 60, "31~60 席"), (61, 90, "61~90 席"), (91, 999, "≥91 席")):
        sel = [r for r in both if lo <= r["H"] <= hi]
        by_h.append(f"{nm} {sum(1 for r in sel if r in drop)}/{len(sel)}（1500 拍中位 {fmt(med([r['ratio']['own'][1500] for r in sel]))}）")
    P("    按房间真人数：" + "；".join(by_h))

    # ---- [XT-C] ----
    P("")
    P("[XT-C] 地是谁吃的（真值）")
    hv = [r for r in full if r["ai600_1500"] is not None and r["ph"].get(600) and r["ph"][600]["own"]["n"] >= 3 and r["ph"][600]["wild"]["n"] >= 5]
    tot = {g: sum(r["ai600_1500"][g] for r in hv) for g in GROUPS}
    heads = {g: sum(r["ph"][600][g]["n"] for r in hv) for g in GROUPS}
    burn = {g: sum(r["aiBurn600_1500"][g] for r in hv) for g in GROUPS}
    allc, allh = sum(tot.values()), sum(heads.values())
    P(f"  (600,1500] 真人从内置 AI 手里吃下的格（{len(hv)} 局合计 {allc} 格；人头 = t=600 还有地的真人 {allh} 个）：")
    for g in GROUPS:
        P(f"    {GROUP_CN[g]}：{tot[g]} 格（{pct(tot[g], allc)}）｜人头 {heads[g]}（{pct(heads[g], allh)}）｜人均 {tot[g] / max(1, heads[g]):.0f} 格｜每格烧 {burn[g] / max(1, tot[g]):.1f} 兵")
    sr = []
    for r in hv:
        a = sum(r["ai600_1500"].values())
        h = sum(r["ph"][600][g]["n"] for g in GROUPS)
        if a > 0:
            sr.append((r, (r["ai600_1500"]["own"] / a) / (r["ph"][600]["own"]["n"] / h)))
    xs = sorted(v for _, v in sr)
    P(f"  逐局的份额对照（own 的份额 ÷ own 的人头份额）：{len(xs)} 局，中位 {fmt(med(xs))}，下四分位 {fmt(xs[len(xs) // 4]) if xs else '—'}，上四分位 {fmt(xs[(3 * len(xs)) // 4]) if xs else '—'}；"
      f"<0.70 的 {sum(1 for v in xs if v < 0.7)} 局，<1.00 的 {sum(1 for v in xs if v < 1.0)} 局")
    P("    按编队档：" + "；".join(f"{c} 中位 {fmt(med([v for r, v in sr if r['cohort'] == c]))}（{sum(1 for r, v in sr if r['cohort'] == c)} 局）" for c in COHORTS)
      + f"｜主队赢的局 中位 {fmt(med([v for r, v in sr if r['won']]))}（{sum(1 for r, v in sr if r['won'])}），没赢的局 {fmt(med([v for r, v in sr if not r['won']]))}（{sum(1 for r, v in sr if not r['won'])}）")
    hu = {g: sum(r["human600_1500"][g] for r in hv) for g in GROUPS}
    lo = {g: sum(r["lostToHuman600_1500"][g] for r in hv) for g in GROUPS}
    P("  同窗真人之间：" + "；".join(f"{GROUP_CN[g]} 从真人手里吃 {hu[g]} 格、被真人吃走 {lo[g]} 格（人均净 {(hu[g] - lo[g]) / max(1, heads[g]):+.0f}）" for g in GROUPS))
    nv = [r for r in full if r["neutral0_600"] is not None and r["size"]["own"] >= 3 and r["size"]["wild"] >= 5]
    ntot = {g: sum(r["neutral0_600"][g] for r in nv) for g in GROUPS}
    nheads = {g: sum(r["size"][g] for r in nv) for g in GROUPS}
    P(f"  (0,600] 真人吃下的无主地（{len(nv)} 局；人头 = 出过生的真人）：" + "；".join(
        f"{GROUP_CN[g]} {ntot[g]} 格（{pct(ntot[g], sum(ntot.values()))}）/ 人头 {nheads[g]}（{pct(nheads[g], sum(nheads.values()))}）/ 人均 {ntot[g] / max(1, nheads[g]):.0f}" for g in GROUPS))
    ai_left = [(r["ph"][t]["aiLand"] / r["land"]) for r in full for t in (600,) if r["ph"].get(t) and r["ph"][t]["aiLand"] is not None]
    ai_left15 = [(r["ph"][1500]["aiLand"] / r["land"]) for r in full if r["ph"].get(1500) and r["ph"][1500]["aiLand"] is not None]
    P(f"  内置 AI 的地占全图陆地：t=600 中位 {100 * med(ai_left):.1f}%（{len(ai_left)} 局），t=1500 中位 {100 * med(ai_left15):.1f}%（{len(ai_left15)} 局）")

    # ---- [XT-D] ----
    P("")
    P("[XT-D] 陆攻落地后有没有生效（真值；录像里落地的陆攻指令）：时段 | 组 | 局数 | 落地 | 生效 | 没生效占比 | 目标 512 占比 | 每席位落地条数")
    agg_d = {}
    for k, nm in enumerate(("0~600", "600~1500", "1500~1800")):
        for g in GROUPS:
            sel = [r for r in (full if g == "own" else recs) if r["cmds"][k] is not None and r["cmds"][k][g]["seats"] > 0]
            land = sum(r["cmds"][k][g]["land"] for r in sel)
            ok = sum(r["cmds"][k][g]["ok"] for r in sel)
            t512 = sum(r["cmds"][k][g]["t512"] for r in sel)
            seats = sum(r["cmds"][k][g]["seats"] for r in sel)
            P(f"  {nm} | {GROUP_CN[g]} | {len(sel)} | {land} | {ok} | {pct(land - ok, land)} | {pct(t512, land)} | {land / max(1, seats):.1f}")
            agg_d[f"{nm}|{g}"] = dict(matches=len(sel), landed=land, effective=ok, t512=t512, seats=seats)
    pm = []
    for r in full:
        c = r["cmds"][1]
        if c and c["own"]["land"] >= 20 and c["wild"]["land"] >= 20:
            pm.append((r, 1 - c["own"]["ok"] / c["own"]["land"], 1 - c["wild"]["ok"] / c["wild"]["land"]))
    P(f"  逐局（600~1500，own 和野人各 ≥20 条陆攻的 {len(pm)} 局）：own 没生效占比 中位 {100 * med([a for _, a, _ in pm]):.0f}%，野人 中位 {100 * med([b for _, _, b in pm]):.0f}%；"
      f"own 比野人高的 {sum(1 for _, a, b in pm if a > b)} 局；own ≥20% 的 {sum(1 for _, a, _ in pm if a >= 0.2)} 局，野人 ≥20% 的 {sum(1 for _, _, b in pm if b >= 0.2)} 局")
    P("    按编队档（own 没生效占比的中位）：" + "；".join(f"{c} {fmt(100 * med([a for r, a, _ in pm if r['cohort'] == c]) if [a for r, a, _ in pm if r['cohort'] == c] else None, 0)}%（{sum(1 for r, _, _ in pm if r['cohort'] == c)} 局）" for c in COHORTS))

    # ---- [XT-E] ----
    P("")
    P("[XT-E] 出生点（真值落点；全部重演成功的局，own 只算对得上的局）：组 | 席位 | 贴边（≤ 短边 12%） | 最近的真人是机器号 | 最近的真人是 own | 离边中位的中位 | 最近真人距离中位的中位 | 选点条数中位的中位")
    agg_e = {}
    for g in GROUPS:
        sel = [r for r in recs if r["spawn"][g]["n"] > 0]
        n = sum(r["spawn"][g]["n"] for r in sel)
        ne = sum(r["spawn"][g]["nearEdge"] for r in sel)
        nb = sum(r["spawn"][g]["nnBot"] for r in sel)
        no = sum(r["spawn"][g]["nnOwn"] for r in sel)
        P(f"  {GROUP_CN[g]} | {n}（{len(sel)} 局） | {ne}（{pct(ne, n)}） | {nb}（{pct(nb, n)}） | {no}（{pct(no, n)}） | {fmt(med([r['spawn'][g]['edgeMed'] for r in sel]), 0)} | "
          f"{fmt(med([r['spawn'][g]['nnMed'] for r in sel if r['spawn'][g]['nnMed'] is not None]), 0)} | {fmt(med([r['spawn'][g]['picksMed'] for r in sel]), 1)}")
        agg_e[g] = dict(seats=n, matches=len(sel), nearEdge=ne, nnBot=nb, nnOwn=no)
    for c in COHORTS:
        sel = [r for r in val if r["cohort"] == c and r["spawn"]["own"]["n"] > 0]
        n = sum(r["spawn"]["own"]["n"] for r in sel)
        ne = sum(r["spawn"]["own"]["nearEdge"] for r in sel)
        no = sum(r["spawn"]["own"]["nnBot"] for r in sel)
        wn = sum(r["spawn"]["wild"]["n"] for r in sel)
        we = sum(r["spawn"]["wild"]["nearEdge"] for r in sel)
        P(f"    {c}：own {n} 席（{len(sel)} 局）贴边 {pct(ne, n)}、最近的真人是机器号 {pct(no, n)}｜同局野人 {wn} 席贴边 {pct(we, wn)}")
    more = [r for r in val if r["spawn"]["own"]["n"] >= 3 and r["spawn"]["wild"]["n"] >= 5]
    P(f"  逐局（own ≥3 席、野人 ≥5 席的 {len(more)} 局）：own 贴边比例高过同局野人的 {sum(1 for r in more if r['spawn']['own']['nearEdge'] / r['spawn']['own']['n'] > r['spawn']['wild']['nearEdge'] / r['spawn']['wild']['n'])} 局；"
      f"own 的最近真人距离中位比野人小的 {sum(1 for r in more if (r['spawn']['own']['nnMed'] or 0) < (r['spawn']['wild']['nnMed'] or 0))} 局")
    # 贴边和 1500 拍人均对照
    e_hi = [r["ratio"]["own"][1500] for r in both if r["spawn"]["own"]["n"] and r["spawn"]["own"]["nearEdge"] / r["spawn"]["own"]["n"] >= 0.5]
    e_lo = [r["ratio"]["own"][1500] for r in both if r["spawn"]["own"]["n"] and r["spawn"]["own"]["nearEdge"] / r["spawn"]["own"]["n"] < 0.5]
    P(f"  own 贴边 ≥50% 的局：t=1500 人均对照中位 {fmt(med(e_hi))}（{len(e_hi)} 局）；<50% 的局：{fmt(med(e_lo))}（{len(e_lo)} 局）")

    # ---- [XT-F] ----
    P("")
    P("[XT-F] 发出 vs 落地（日志 cmds 增量 vs 录像里 own 席位落地的陆攻 + 捐款 + 船）：时段 | 局数 | 号 | 日志发出 | 录像落地 | 落地 ÷ 发出 | 逐局比值的中位 | <0.70 的局 | >1.00 的局")
    agg_f = {}
    for i, (nm, _, _) in enumerate(LOGPER):
        sel = [r for r in full if len(r["flow"]) > i and r["flow"][i]["issued"] >= 20]
        iss = sum(r["flow"][i]["issued"] for r in sel)
        lan = sum(r["flow"][i]["landed"] for r in sel)
        rs = [r["flow"][i]["landed"] / r["flow"][i]["issued"] for r in sel]
        P(f"  {nm} | {len(sel)} | {sum(r['flow'][i]['bots'] for r in sel)} | {iss} | {lan} | {pct(lan, iss)} | {fmt(med(rs))} | {sum(1 for v in rs if v < 0.7)} | {sum(1 for v in rs if v > 1.0)}")
        agg_f[nm] = dict(matches=len(sel), issued=iss, landed=lan, medianRatio=med(rs), below07=sum(1 for v in rs if v < 0.7))
        P("      按编队档：" + "；".join(
            f"{c} {pct(sum(r['flow'][i]['landed'] for r in sel if r['cohort'] == c), sum(r['flow'][i]['issued'] for r in sel if r['cohort'] == c))}（{sum(1 for r in sel if r['cohort'] == c)} 局）" for c in COHORTS))

    # ---- [XT-G] ----
    P("")
    P("[XT-G] 录像前 1800 拍里出局 / 离开（真值；录像不到 1800 拍的算到录像末）：组 | 席位 | 出局 | 其中 900 拍前 | 离开")
    for g in GROUPS:
        sel = [r for r in (full if g == "own" else [x for x in recs if not x["spawnOnly"]])]
        n = sum(r["exits"][g]["n"] for r in sel)
        d = sum(r["exits"][g]["dead"] for r in sel)
        d9 = sum(r["exits"][g]["dead900"] for r in sel)
        lf = sum(r["exits"][g]["left"] for r in sel)
        P(f"  {GROUP_CN[g]} | {n} | {d}（{pct(d, n)}） | {d9}（{pct(d9, n)}） | {lf}（{pct(lf, n)}）")

    # ---- [XT-H] ----
    P("")
    P("[XT-H] 逐局：局 | 档 | 真人 | own/[APEX]/名字池/野人 | 录像到 | 核对 | 人均对照 @300/630/900/1260/1500/1800 | AI 地份额对照 (600,1500] | 600~1500 陆攻没生效 own / 野人 | own 贴边 | 600~1500 落地 ÷ 发出 | 主队赢")
    for r in recs:
        if not r["valid"]:
            P(f"  {r['matchId']} | {r['cohort']} | {r['H']} | —/{r['size']['apex']}/{r['size']['pool']}/{r['size']['wild']} | {r['endTick']} | {r['exact']}/{r['rows']} 对不上 | 不进 own 统计")
            continue
        rt = "/".join(fmt(r["ratio"]["own"].get(t)) for t in (300, 630, 900, 1260, 1500, 1800))
        srv = next((v for x, v in sr if x is r), None)
        c = r["cmds"][1] if len(r["cmds"]) > 1 else None
        ne = (f"{1 - c['own']['ok'] / c['own']['land']:.0%}" if c and c["own"]["land"] else "—") + " / " + (f"{1 - c['wild']['ok'] / c['wild']['land']:.0%}" if c and c["wild"]["land"] else "—")
        fl = r["flow"][1] if len(r["flow"]) > 1 and r["flow"][1]["issued"] else None
        P(f"  {r['matchId']} | {r['cohort']} | {r['H']} | {r['size']['own']}/{r['size']['apex']}/{r['size']['pool']}/{r['size']['wild']} | {r['endTick']} | {r['exact']}/{r['rows']} | {rt} | {fmt(srv)} | {ne} | "
          f"{r['spawn']['own']['nearEdge']}/{r['spawn']['own']['n']} | {(str(fl['landed']) + '/' + str(fl['issued'])) if fl else '—'} | {'赢' if r['won'] else '—'}")

    os.makedirs(os.path.join(OUT, "_cross"), exist_ok=True)
    with open(os.path.join(OUT, "_cross", "xtruth.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    with open(os.path.join(OUT, "_cross", "xtruth.json"), "w", encoding="utf-8") as f:
        json.dump(dict(replays=len(recs), valid=len(val), full=len(full), failed=failed, perHead=agg_b, drop=dict(both=len(both), hit=[r["matchId"] for r in drop]),
                       aiHarvest=dict(matches=len(hv), cells=tot, heads=heads, burnt=burn), cmdEffect=agg_d, spawn=agg_e, flow=agg_f,
                       matches=[{k: v for k, v in r.items()} for r in recs]), f, ensure_ascii=False, separators=(",", ":"))
    if not quiet:
        print("\n".join(out))


if __name__ == "__main__":
    main()
