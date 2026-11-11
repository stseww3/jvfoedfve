#!/usr/bin/env python3
"""xscan.py — 发现集全部对局包（bundles/，123 局）的模式机械计数，只看日志；不落逐局中间文件。

    python3 xscan.py [--mine] [--quiet]     → out/_cross/xscan.txt、xscan.json（--mine 只跑 R08 的 16 局，写 xscan_mine.*）

做法：对每一局在内存里跑 facts.full（身份还原 + 分段 + DROP30 + 捐款账本），再跑 patterns.py 的全部检出函数，
另外数几项基础量（阵亡 / 离开、出局时账上的兵、被围、指令节奏、超软上限）。验证集（validation_bundles/）不碰。
多房间的包只算主房间（facts.build 的默认）；R08 自己的 16 局有录像重演产物时身份还原用了真值，其余各局只靠日志
（标签轮换靠 HL-TICK 的工作进程统计量串联），个别局会有串错的号——所以逐局数字只作筛查，结论看合计。

节：
  [XS-A] 模式 × 发现集：命中局数（按编队档）、次数合计、兑现合计；主队赢的局 / 输的局各自的命中率
  [XS-B] 基础量（按编队档）：号数、阵亡、离开时还有地的、出局时账上的兵、被围 ≥900 拍的号、超软上限 / 顶硬上限的快照占比
  [XS-C] 四分之一线的核对：全部阵亡号『出局前最后的领土 ÷ 历史峰值』的分布
  [XS-D] 指令节奏：每 1000 号·拍的非船指令，按时段；主队赢 / 输对照
  [XS-E] R08 的 16 局逐局（模式命中表）
  [XS-F] 出局的时间：全部阵亡号的出局拍分位、峰值拍 → 出局拍的间隔
  [XS-G] 编队合计领土占全图陆地的份额，t=630 / 1530 / 3060 / 4500 / 6030（日志口径）
  [XS-H] 离开的号：离开拍的分位、分段占比、离开时留下的地和兵
  [XS-I] 捐款日志行按引擎受捐额度的分段：成交 / 被拒 / 定不了、到账上限、手续费
"""
import json
import os
import statistics
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "reviews_src"))
import facts  # noqa: E402
import patterns as P  # noqa: E402
import patterns_catalog as PC  # noqa: E402
import r08lib as L  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")
MINE = ["G02", "G05", "G08", "B043", "B033", "B034", "B031", "B049", "B006", "B030", "B019", "B009", "B015", "B029", "B035", "B027"]
SHARE_T = (630, 1530, 3060, 4500, 6030)
CAD = [("0~630", 0, 630), ("630~1500", 630, 1500), ("1500~3000", 1500, 3000), ("3000~4500", 3000, 4500), ("4500+", 4500, 10 ** 9)]


def discovery_ids():
    with open(os.path.join(L.DATA, "manifest.jsonl"), encoding="utf-8") as f:
        rows = [json.loads(x) for x in f if x.strip()]
    return [(r["matchId"], r) for r in rows if r.get("split") == "discovery"]


def basics(m):
    bots = list(m.bots.values())
    died = [b for b in bots if m.death(b) is not None]
    left = [b for b in bots if b.get("event") == "left"]
    left_land = [b for b in left if (b.get("lastTerritory") or b.get("resTerritory") or 0) >= 100]
    snaps = [s for b in bots for s in b["ticks"] if s["terr"] > 0]
    late = [s for s in snaps if s["t"] >= 1500]
    boxed = [s for s in snaps if s["nb"] == 0 and s["neut"] == 0]
    ratios = []
    for b in died:
        pk, lt = b.get("resPeak") or 0, b.get("lastTerritory")
        if pk >= 500 and lt is not None:
            ratios.append(round(lt / pk, 3))
    cad = []
    for name, a, z in CAD:
        bt = nb = bo = 0
        for b in bots:
            tk = [s for s in b["ticks"] if a <= s["t"] <= z]
            if len(tk) >= 2:
                bt += tk[-1]["t"] - tk[0]["t"]
                nb += (tk[-1]["cmds"] - tk[0]["cmds"]) - (tk[-1]["boats"] - tk[0]["boats"])
                bo += tk[-1]["boats"] - tk[0]["boats"]
        cad.append(dict(period=name, botTicks=bt, nonBoat=nb, boats=bo))
    dons = m.dons
    # 出局拍、峰值拍；编队合计领土占全图陆地的份额（日志口径：每个号取 ≤t 且 ≥t−90 的最后一条快照）
    death_rows = []
    for b in died:
        tk = [s for s in b["ticks"] if s["terr"] > 0]
        pk = max(tk, key=lambda s: s["terr"]) if tk else None
        death_rows.append([m.death(b), pk["t"] if pk else None, pk["terr"] if pk else None, b.get("resBalance") or 0])
    share = {}
    for t in SHARE_T:
        if m.end is None or m.end < t:
            share[t] = None
            continue
        tot = n = 0
        for b in bots:
            tk = [s for s in b["ticks"] if t - 90 <= s["t"] <= t and s["terr"] > 0]
            if tk:
                tot += tk[-1]["terr"]
                n += 1
        share[t] = [tot / m.land if m.land else None, n]
    # 离开的号：[离开拍, 离开时的地, 离开时结果行里的余额, 离开时这个号最后一条快照的兵密度]
    left_rows = []
    for b in left:
        tk = [s for s in b["ticks"] if s["terr"] > 0]
        left_rows.append([b.get("deathTick"), b.get("lastTerritory") or b.get("resTerritory") or 0, b.get("resBalance") or 0, tk[-1]["dens"] if tk else None])
    # 捐款日志行：[发令拍, 种类, 余额观测的判定 ACC / REJ / ?, 手续费, 按受捐方 150 倍上限夹过的到账, pct, 捐出方发令时的余额]
    don_rows = [[d["t"], d.get("kind") or "?", d.get("obsVerdict") or "?", d.get("fee") or 0, d.get("amountEff") or 0, d.get("pct"), d.get("myBal") or 0] for d in dons]
    return dict(bots=len(bots), died=len(died), left=len(left), leftWithLand=len(left_land), deathRows=death_rows, leftRows=left_rows, donRows=don_rows, share=share,
                firstDeath=min((m.death(b) for b in died), default=None),
                bank=sum(b.get("resBalance") or 0 for b in died), bankBig=sum(1 for b in died if (b.get("resBalance") or 0) >= 100_000),
                snaps=len(snaps), boxedSnaps=len(boxed), boxedHighDens=sum(1 for s in boxed if s["dens"] >= 95),
                lateSnaps=len(late), overSoft=sum(1 for s in late if s["bal"] > 100 * s["terr"]), hardCap=sum(1 for s in late if s["bal"] >= 149.5 * s["terr"]),
                quarterRatios=ratios, cadence=cad, donations=len(dons), donationsAccepted=sum(1 for d in dons if d.get("accepted")))


def scan(mid, card0):
    F = facts.full(mid)
    m = P.M(mid, F=F)
    res = {}
    for pid, fn, f in P.DETECTORS:
        try:
            r = f(m)
        except Exception as e:  # noqa: BLE001
            r = dict(hit=False, n=0, items=[], error=repr(e))
        res[pid] = {k: v for k, v in r.items() if k not in ("items", "closePairs")}
    card = F["card"]
    oc = card0.get("outcome") or {}      # 输赢一律用对局卡（manifest）的口径；facts 自己重算的标签另存一栏
    oc2 = card.get("outcome") or {}
    return dict(matchId=mid, cohort=card0.get("cohort"), mode=card0.get("mode"), nominalTeams=card0.get("nominalTeams"), squadTeams=len(card0.get("teamSplitCounts") or {}),
                land=m.land, endTick=m.end, primaryTeamWon=bool(oc.get("primaryTeamWon")), anyBotWon=bool(oc.get("anyBotWon")), resultLabel=oc.get("resultLabel"),
                factsLabel=oc2.get("resultLabel"),
                peakSquadShare=oc.get("peakSquadLandShare"), replay=bool((card0.get("dataCompleteness") or {}).get("replay")),
                rooms=len(F["rooms"]) if F.get("rooms") else 1, unresolved=len(F.get("unresolved") or []), notes=len(F.get("notes") or []),
                cardSquadBots=card0.get("squadBots"), basics=basics(m), patterns=res)


def rate(a, b):
    return "–" if not b else f"{100 * a / b:.0f}%"


def main():
    mine_only = "--mine" in sys.argv
    quiet = "--quiet" in sys.argv
    rows, failed = [], []
    for mid, card in discovery_ids():
        if mine_only and mid not in MINE:
            continue
        try:
            rows.append(scan(mid, card))
        except Exception as e:  # noqa: BLE001
            failed.append((mid, repr(e)[:160]))
    cohorts = sorted({r["cohort"] for r in rows})
    won = [r for r in rows if r["primaryTeamWon"]]
    lost = [r for r in rows if not r["primaryTeamWon"]]
    out = [f"[XS-A] 发现集 {len(rows)} 局（{'、'.join(f'{c} {sum(1 for r in rows if r['cohort'] == c)}' for c in cohorts)}；主队赢 {len(won)}、没赢 {len(lost)}；"
           f"跑失败 {len(failed)} 局{('：' + '；'.join(f'{a} {b}' for a, b in failed)) if failed else ''}）。"
           "模式 | 名称 | 命中局数（" + " / ".join(cohorts) + "）| 次数合计 | 兑现合计 | 主队赢的局命中率 | 没赢的局命中率 | 其它合计"]
    agg = {}
    for pid, fn, _ in P.DETECTORS:
        hits = [r for r in rows if r["patterns"][pid].get("hit")]
        n = sum(r["patterns"][pid].get("n") or 0 for r in hits)
        real = sum(r["patterns"][pid].get("realized") or 0 for r in hits if isinstance(r["patterns"][pid].get("realized"), (int, float)))
        extra = defaultdict(float)
        for r in hits:
            for k, v in r["patterns"][pid].items():
                if k in ("hit", "n", "realized", "error", "note", "minSep", "ffa", "avgTerrAt630", "minAlivePlayers", "deaths", "wide") or isinstance(v, (list, dict, str, bool)) or v is None:
                    continue
                extra[k] += v
        by_c = [sum(1 for r in hits if r["cohort"] == c) for c in cohorts]
        hw, hl = sum(1 for r in hits if r["primaryTeamWon"]), sum(1 for r in hits if not r["primaryTeamWon"])
        nm = PC.BY_ID.get(pid.rstrip("wL"), {}).get("name", "")[:30]
        agg[pid] = dict(fn=fn, matches=len(hits), byCohort=dict(zip(cohorts, by_c)), n=n, realized=real, wonHit=hw, lostHit=hl, won=len(won), lost=len(lost),
                        extra={k: round(v) for k, v in extra.items()}, errors=sum(1 for r in rows if r["patterns"][pid].get("error")))
        out.append(f"  {pid:<11} | {nm} | {len(hits)}（{' / '.join(str(x) for x in by_c)}）| {n} | {real if real else '-'} | {rate(hw, len(won))} | {rate(hl, len(lost))} | "
                   + (" ".join(f"{k}={round(v)}" for k, v in extra.items()) or "-"))
    # [XS-B]
    out.append("[XS-B] 基础量：编队档 | 局数 | 号数 | 阵亡 | 离开（其中离开时还有 ≥100 格）| 出局时账上的兵合计（每个阵亡号平均）| 账上 ≥10 万的阵亡号 | "
               "被围快照占比（其中密度 ≥95）| t≥1500 超软上限的快照占比 | 顶硬上限的占比 | 日志捐款条数（成交）")
    base = {}
    for c in cohorts + ["全部"]:
        rs = rows if c == "全部" else [r for r in rows if r["cohort"] == c]
        b = defaultdict(int)
        for r in rs:
            for k, v in r["basics"].items():
                if isinstance(v, int) and not isinstance(v, bool):
                    b[k] += v
        base[c] = dict(matches=len(rs), **b)
        out.append(f"    {c} | {len(rs)} | {b['bots']} | {b['died']} | {b['left']}（{b['leftWithLand']}）| {b['bank']}（{round(b['bank'] / b['died']) if b['died'] else '–'}）| {b['bankBig']} | "
                   f"{rate(b['boxedSnaps'], b['snaps'])}（{rate(b['boxedHighDens'], b['boxedSnaps'])}）| {rate(b['overSoft'], b['lateSnaps'])} | {rate(b['hardCap'], b['lateSnaps'])} | "
                   f"{b['donations']}（{b['donationsAccepted']}）")
    # [XS-C]
    ratios = sorted(x for r in rows for x in r["basics"]["quarterRatios"])
    if ratios:
        q = statistics.quantiles(ratios, n=20)
        out.append(f"[XS-C] 四分之一线核对：峰值 ≥500 格的阵亡号 {len(ratios)} 个，『出局前最后的领土 ÷ 历史峰值』的 5% / 25% / 50% / 75% / 95% 分位 = "
                   f"{q[0]:.2f} / {q[4]:.2f} / {q[9]:.2f} / {q[14]:.2f} / {q[18]:.2f}；≤0.26 的占 {rate(sum(1 for x in ratios if x <= 0.26), len(ratios))}，"
                   f"≤0.30 的占 {rate(sum(1 for x in ratios if x <= 0.30), len(ratios))}，>0.35 的 {sum(1 for x in ratios if x > 0.35)} 个")
    # [XS-D]
    out.append("[XS-D] 指令节奏（每 1000 号·拍的非船指令；HL-TICK 的 cmds − boats 增量）：时段 | 全部 | " + " | ".join(cohorts) + " | 主队赢的局 | 没赢的局")
    cadence = {}
    for i, (name, _, _) in enumerate(CAD):
        def per(rs):
            bt = sum(r["basics"]["cadence"][i]["botTicks"] for r in rs)
            nb = sum(r["basics"]["cadence"][i]["nonBoat"] for r in rs)
            return (1000 * nb / bt) if bt else None
        vals = [per(rows)] + [per([r for r in rows if r["cohort"] == c]) for c in cohorts] + [per(won), per(lost)]
        cadence[name] = vals
        out.append(f"    {name} | " + " | ".join("–" if v is None else f"{v:.1f}" for v in vals))
    # [XS-F]
    out.append("[XS-F] 出局的时间（日志口径，全部阵亡号）：组 | 阵亡号 | 出局拍的 10% / 25% / 50% / 75% / 90% 分位 | ≤1500 拍 | ≤3000 拍 | ≤4500 拍 | 峰值拍 → 出局拍 的中位间隔 | 峰值拍的中位")
    death_agg = {}
    for nm, rs in [("全部", rows)] + [(c, [r for r in rows if r["cohort"] == c]) for c in cohorts] + [("主队赢的局", won), ("没赢的局", lost)]:
        dr = [d for r in rs for d in r["basics"]["deathRows"] if d[0] is not None]
        if len(dr) < 5:
            continue
        ts = sorted(d[0] for d in dr)
        q = statistics.quantiles(ts, n=20)
        gaps = sorted(d[0] - d[1] for d in dr if d[1] is not None)
        pks = sorted(d[1] for d in dr if d[1] is not None)
        out.append(f"    {nm} | {len(ts)} | {q[1]:.0f} / {q[4]:.0f} / {q[9]:.0f} / {q[14]:.0f} / {q[17]:.0f} | {rate(sum(1 for t in ts if t <= 1500), len(ts))} | {rate(sum(1 for t in ts if t <= 3000), len(ts))} | "
                   f"{rate(sum(1 for t in ts if t <= 4500), len(ts))} | {statistics.median(gaps):.0f} | {statistics.median(pks):.0f}")
        death_agg[nm] = dict(n=len(ts), q10=q[1], q25=q[4], q50=q[9], q75=q[14], q90=q[17], le1500=sum(1 for t in ts if t <= 1500), le3000=sum(1 for t in ts if t <= 3000),
                             peakToDeathMedian=statistics.median(gaps), peakTickMedian=statistics.median(pks))
    # [XS-G]
    out.append("[XS-G] 编队合计领土占全图陆地的份额（日志口径；括号 = 有数的局数）：组 | " + " | ".join(f"t={t}" for t in SHARE_T) + " | 份额最高的那个检查点落在哪（局数）")
    share_agg = {}
    for nm, rs in [("全部", rows)] + [(c, [r for r in rows if r["cohort"] == c]) for c in cohorts] + [("主队赢的局", won), ("没赢的局", lost)]:
        cells = []
        for t in SHARE_T:
            v = [r["basics"]["share"][t][0] for r in rs if r["basics"]["share"].get(t) and r["basics"]["share"][t][0] is not None]
            cells.append(f"{100 * statistics.median(v):.1f}%（{len(v)}）" if v else "–")
            share_agg.setdefault(nm, {})[t] = dict(n=len(v), median=statistics.median(v) if v else None)
        best = {}
        for r in rs:
            sv = [(r["basics"]["share"][t][0], t) for t in SHARE_T if r["basics"]["share"].get(t) and r["basics"]["share"][t][0] is not None]
            if sv:
                bt = max(sv)[1]
                best[bt] = best.get(bt, 0) + 1
        out.append(f"    {nm} | " + " | ".join(cells) + " | " + "，".join(f"t={t}：{best.get(t, 0)}" for t in SHARE_T))
    # [XS-H] 离开
    out.append("[XS-H] 离开的号（日志口径；结果行 event=left）：组 | 离开的号 | 有离开的局 | 一局里 ≥ 一半的号离开的局 | 离开拍的 10% / 25% / 50% / 75% / 90% 分位 | ≤1500 拍 | 1500~3000 | 3000~8500 | >8500 拍 | "
               "离开时还有 ≥100 格的 | 这些号离开时的地合计（每号中位）| 离开时账上的兵合计 | 离开时地 ≥ 全图 1% 的号")
    left_agg = {}
    for nm, rs in [("全部", rows)] + [(c, [r for r in rows if r["cohort"] == c]) for c in cohorts] + [("主队赢的局", won), ("没赢的局", lost)]:
        lr = [(x, r) for r in rs for x in r["basics"].get("leftRows", []) if x[0] is not None]
        if not lr:
            continue
        ts = sorted(x[0] for x, _ in lr)
        q = statistics.quantiles(ts, n=20) if len(ts) >= 2 else [ts[0]] * 19
        withland = [x for x, _ in lr if x[1] >= 100]
        big = sum(1 for x, r in lr if r["land"] and x[1] >= 0.01 * r["land"])
        half = sum(1 for r in rs if r["basics"]["left"] * 2 >= r["basics"]["bots"] and r["basics"]["left"] > 0)
        n = len(ts)
        out.append(f"    {nm} | {n} | {sum(1 for r in rs if r['basics']['left'] > 0)} | {half} | {q[1]:.0f} / {q[4]:.0f} / {q[9]:.0f} / {q[14]:.0f} / {q[17]:.0f} | "
                   f"{rate(sum(1 for t in ts if t <= 1500), n)} | {rate(sum(1 for t in ts if 1500 < t <= 3000), n)} | {rate(sum(1 for t in ts if 3000 < t <= 8500), n)} | {rate(sum(1 for t in ts if t > 8500), n)} | "
                   f"{len(withland)} | {sum(x[1] for x in withland)}（{statistics.median([x[1] for x in withland]) if withland else 0:.0f}）| {sum(x[2] for x, _ in lr)} | {big}")
        left_agg[nm] = dict(n=n, matches=sum(1 for r in rs if r["basics"]["left"] > 0), halfMatches=half, q50=q[9], le1500=sum(1 for t in ts if t <= 1500), gt8500=sum(1 for t in ts if t > 8500),
                            withLand=len(withland), land=sum(x[1] for x in withland), balance=sum(x[2] for x, _ in lr), big=big)
    # [XS-I] 捐款日志行按引擎的受捐额度分段
    DB = [("0~2142", 0, 2142), ("2142~3213", 2142, 3213), ("3213~4284", 3213, 4284), ("4284+", 4284, 10 ** 9)]
    out.append("[XS-I] 捐款日志行按引擎受捐额度的分段（donationCost L348-357 的换算在 t=2142 / 3213 换档；t≥4284 不限额）。判定 = 捐出方下一条余额观测对『成交 / 被拒』两个预期的比对（facts.py）：")
    out.append("    组 | 时段 | 有捐款的局 | 日志行 | 看得到成交 | 看得到被拒 | 定不了 | 成交 ÷（成交 + 被拒）| 成交的那些：到账上限 | 手续费 | 手续费 ÷ 到账 | pct < 63 的行（其中看得到成交的；这种捐款到账比手续费还少）")
    don_agg = {}
    for nm, rs in [("全部", rows)] + [(c, [r for r in rows if r["cohort"] == c]) for c in cohorts]:
        for bn, a, z in DB:
            dr = [x for r in rs for x in r["basics"].get("donRows", []) if a <= x[0] < z]
            if not dr:
                continue
            acc = [x for x in dr if x[2] == "ACC"]
            rej = [x for x in dr if x[2] == "REJ"]
            small = [x for x in dr if x[5] is not None and x[5] < 63]
            got, fee = sum(x[4] for x in acc), sum(x[3] for x in acc)
            out.append(f"    {nm} | {bn} | {sum(1 for r in rs if any(a <= x[0] < z for x in r['basics'].get('donRows', [])))} | {len(dr)} | {len(acc)} | {len(rej)} | {len(dr) - len(acc) - len(rej)} | "
                       f"{rate(len(acc), len(acc) + len(rej))} | {got} | {fee} | {rate(fee, got)} | {len(small)}（{sum(1 for x in small if x[2] == 'ACC')}）")
            don_agg[f"{nm}|{bn}"] = dict(lines=len(dr), acc=len(acc), rej=len(rej), arrived=got, fee=fee, small=len(small))
    kinds = {}
    for r in rows:
        for x in r["basics"].get("donRows", []):
            k = kinds.setdefault(x[1], [0, 0, 0])
            k[0] += 1
            k[1] += x[2] == "ACC"
            k[2] += x[2] == "REJ"
    out.append("    按种类（全部）：" + "；".join(f"{k} {v[0]} 行（成交 {v[1]} / 被拒 {v[2]}）" for k, v in sorted(kinds.items(), key=lambda kv: -kv[1][0])))
    # [XS-E]
    mine = [r for r in rows if r["matchId"] in MINE]
    mine.sort(key=lambda r: MINE.index(r["matchId"]))
    if mine:
        out.append("[XS-E] R08 的 16 局逐局（格子 = 次数，带 * = 兑现的次数，- = 没命中）：模式 | " + " | ".join(r["matchId"] for r in mine) + " | 命中局数")
        for pid, fn, _ in P.DETECTORS:
            cells = []
            for r in mine:
                x = r["patterns"][pid]
                cells.append("-" if not x.get("hit") else (f"{x['n']}" + (f"*{x['realized']}" if x.get("realized") else "")))
            out.append(f"  {pid:<11} | " + " | ".join(f"{c:>5}" for c in cells) + f" | {sum(1 for r in mine if r['patterns'][pid].get('hit'))}")
    od = os.path.join(OUT, "_cross")
    os.makedirs(od, exist_ok=True)
    name = "xscan_mine" if mine_only else "xscan"
    open(os.path.join(od, f"{name}.txt"), "w", encoding="utf-8").write("\n".join(out) + "\n")
    json.dump(dict(matches=len(rows), cohorts=cohorts, won=len(won), lost=len(lost), failed=failed, agg=agg, base=base, cadence=cadence, deathTiming=death_agg, shareTrajectory=share_agg, leaves=left_agg, donationBands=don_agg, donationKinds=kinds,
                   quarter=dict(n=len(ratios), le026=sum(1 for x in ratios if x <= 0.26), le030=sum(1 for x in ratios if x <= 0.30), gt035=sum(1 for x in ratios if x > 0.35)),
                   rows=[{k: v for k, v in r.items()} for r in rows]),
              open(os.path.join(od, f"{name}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    if not quiet:
        print("\n".join(out))
    else:
        print(f"{name}: {len(rows)} 局，{len(out)} 行；失败 {len(failed)}")


if __name__ == "__main__":
    main()
