#!/usr/bin/env python3
"""crosstab.py — R03 复盘的 11 局跨局表（给 reports/CROSS-MATCH-SUMMARY.md 和 cards/ 用）。

只读：reviews/<局>.json、out/dossier/<局>-{delay,land}-facts.json、out/cache/<局>-{resim,shadow,freeze}.json、
      /agent/repos/c136-data/manifest.jsonl（只取这 11 局的行）。不重跑重放。
写：out/cross/X0-roster.txt … X10-rank.txt，每张表头写清口径。

    python3 scripts/crosstab.py            # 全部表
    python3 scripts/crosstab.py X3 X4      # 只重算指定的表

表：
  X0  对局表（结构、结局、编队地盘份额走势）
  X1  延迟账补充（分时段：迟到 >30 拍、落地时目标已死；发令漏斗；重发串）
  X2  好地抢到率三层恒等式（名下、转化的时间序列、AI 地去向）
  X3  整局兵力去向总账（编队 对 同队路人 对 敌方真人；口径同卷宗 [L]）
  X4  分段对照账（0~630 / 630~1500 / 1500~4284 / 4284~结束；口径同 winledger.py）
  X5  利息效率（编队 对 其他真人；口径同卷宗 [P]）
  X6  捐款与调度（日志→成交→额度拒；按额度分段的到账与税；闸门计数）
  X7  决策拍分类（600~1500 的 pickTarget；1500 拍起的 buyLand）
  X8  报价对 worth（belowworth.py 的分类，1500~2399 与 2400~结束）
  X9  模式普查（11 份复盘 JSON 里的 decisions / deaths / newPatterns / turningPoints）
  X10 秩相关（n=11，Spearman；随机置换给双侧 p）
"""
import json
import math
import os
import random
import re
import sys
from collections import Counter, defaultdict

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from dossier import Dossier  # noqa: E402
import belowworth as BW  # noqa: E402

MIDS = ["A051", "A087", "A066", "A025", "A045", "A067", "A071", "A090", "A042", "A046", "A041"]
OUT = os.path.join(ROOT, "out", "cross")
DOS = os.path.join(ROOT, "out", "dossier")
CACHE = os.path.join(ROOT, "out", "cache")
CUTS = (0, 630, 1500, 4284)

_J, _D = {}, {}


def J(mid):
    if mid not in _J:
        _J[mid] = json.load(open(os.path.join(ROOT, "reviews", f"{mid}.json"), encoding="utf-8"))
    return _J[mid]


def D(mid):
    if mid not in _D:
        _D[mid] = Dossier(mid)
    return _D[mid]


def facts(mid, kind):
    return json.load(open(os.path.join(DOS, f"{mid}-{kind}-facts.json"), encoding="utf-8"))


def wan(x):
    """兵数：≥100 万写整数万，≥1 万写一位小数的万，其余写整数。"""
    if x is None:
        return "—"
    a = abs(x)
    if a >= 1e6:
        return f"{x / 1e4:.0f}万"
    if a >= 1e4:
        return f"{x / 1e4:.1f}万"
    return f"{x:,.0f}"


def pc(a, b, nd=1):
    return f"{100 * a / b:.{nd}f}%" if b else "—"


def per(a, b, nd=1):
    return f"{a / b:.{nd}f}" if b else "—"


def write(name, lines):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, name)
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"写 {os.path.relpath(p, ROOT)}（{len(lines)} 行）")


# ---------- 分组 ----------
def groups(mid):
    """返回 [(组名, 席位列表)]：编队、同队路人、敌方真人（自由混战局是「其他真人」）。"""
    d = D(mid)
    R = d.R
    sq = set(d.sqids)
    others = [p for p in range(d.H) if p not in sq]
    if not d.team_game:
        return [("编队", sorted(sq)), ("其他真人", others)]
    mates = [p for p in others if R["teams"][p] == d.my_team]
    enemy = [p for p in others if R["teams"][p] != d.my_team and R["teams"][p] > 0]
    out = [("编队", sorted(sq))]
    if mates:
        out.append(("同队路人", mates))
    out.append(("敌方真人", enemy))
    return out


def had_land(d, pl):
    return any(row[pl] > 0 for row in d.R["snapTerr"])


def stop_tick(d, pl):
    return d.left[pl] if d.left[pl] >= 0 else d.alive_until(pl)


def group_total(d, ids):
    """ids 里每个席位从开局到 离线/灭亡 的总账；口径同 dossier.sec_total（卷宗 [L]）。"""
    keys = ("inc", "burnN", "burnAI", "burnH", "netH", "atkFee", "defBal", "defSlot", "donOut", "donTax", "donIn",
            "boatOut", "boatFee", "balEnd", "outEnd", "lostTiles", "lostBurn", "tilesN", "tilesAI", "tilesH", "ret")
    tot = dict.fromkeys(keys, 0)
    heads = 0
    for pl in ids:
        if not had_land(d, pl):
            continue
        heads += 1
        end = stop_tick(d, pl)
        g = d.ledger(pl, 0, end)
        tot["inc"] += g["inc"]
        tot["ret"] += g["ret"]
        for t, att, de, tiles, burnt, dB, dS, n in d.pair_att.get(pl, ()):
            if t > end + 30:
                continue
            cl = d.cls(de, t)
            if cl == "N":
                tot["burnN"] += burnt; tot["tilesN"] += tiles
            elif cl == "AI":
                tot["burnAI"] += burnt; tot["tilesAI"] += tiles
            else:
                tot["burnH"] += burnt - dS; tot["netH"] += dS; tot["tilesH"] += tiles
        tot["atkFee"] += sum(s[1] for s in g["sent"].values())
        tot["defBal"] += g["def_bal"]
        tot["defSlot"] += sum(x[2] for x in g["lost"].values())
        tot["donOut"] += g["don_out"][0]; tot["donTax"] += g["don_out"][1]
        tot["donIn"] += g["don_in"]
        tot["boatOut"] += g["boat"][0]; tot["boatFee"] += g["boat"][1]
        tot["balEnd"] += g["bal1"]; tot["outEnd"] += g["out1"]
        for t, att, de, tiles, burnt, dB, dS, n in d.pair_def.get(pl, ()):
            if t > end + 30 or att >= d.H:
                continue
            tot["lostTiles"] += tiles; tot["lostBurn"] += burnt
    tot["heads"] = heads
    return tot


def window_row(d, ids, a, b):
    """同 winledger.py：一个组在 [a, b) 的账。"""
    R = d.R
    ia, ib = d.ix(a), d.ix(b)
    r = {
        "n0": sum(1 for p in ids if R["snapTerr"][ia][p] > 0), "n1": sum(1 for p in ids if R["snapTerr"][ib][p] > 0),
        "L0": sum(R["snapTerr"][ia][p] for p in ids), "L1": sum(R["snapTerr"][ib][p] for p in ids),
        "B0": sum(R["snapBal"][ia][p] for p in ids), "B1": sum(R["snapBal"][ib][p] for p in ids),
    }
    acc = Counter()
    for p in ids:
        g = d.ledger(p, a, b)
        acc["inc"] += g["inc"]; acc["ret"] += g["ret"]
        for cl, s in g["sent"].items():
            acc["fee"] += s[1]
            if cl == "H":
                acc["sentH"] += s[0]; acc["feeH"] += s[1]; acc["nH"] += s[2]
        for cl, x in g["gain"].items():
            if cl == "H":
                acc["tilesH"] += x[0]; acc["burnH"] += x[1]
            else:
                acc["tilesO"] += x[0]; acc["burnO"] += x[1]
        for x in g["lost"].values():
            acc["defTiles"] += x[0]; acc["defBal"] += x[1]
        acc["donOut"] += g["don_out"][0]; acc["donTax"] += g["don_out"][1]; acc["donN"] += g["don_out"][2]
        acc["donIn"] += g["don_in"]
        acc["boat"] += g["boat"][0]; acc["boatFee"] += g["boat"][1]; acc["boatN"] += g["boat"][2]
    r.update(acc)
    for k_ in ("inc", "ret", "fee", "sentH", "feeH", "nH", "tilesH", "burnH", "tilesO", "burnO", "defTiles", "defBal",
               "donOut", "donTax", "donN", "donIn", "boat", "boatFee", "boatN"):
        r.setdefault(k_, 0)
    r["fees3"] = r["fee"] + r["donTax"] + r["boatFee"]
    return r


def interest_eff(d, ids, phases):
    """同 dossier.sec_interest（卷宗 [P]）：实得利息 对 「同样的地、余额一直等于软上限」口径。"""
    import c136lib as L
    R, T = d.R, d.T
    tot = [[0, 0, 0, 0, 0, 0] for _ in phases]
    for pl in ids:
        stop = stop_tick(d, pl)
        for k_, (a, b) in enumerate(phases):
            x = tot[k_]
            for i in range(len(T) - 1):
                t = T[i]
                if t < a or t >= b or t >= stop:
                    continue
                terr, bal = R["snapTerr"][i][pl], R["snapBal"][i][pl]
                if terr <= 0:
                    continue
                cap = L.soft_cap(terr)
                step = T[i + 1] - t
                inc = R["snapInc"][i + 1][pl] - R["snapInc"][i][pl]
                tt = t + 9
                full = L.g0(L.interest_rate(tt, terr, cap, d.land) * cap, 10000) + (terr if tt % 100 == 99 else 0)
                if step != 10:
                    full = full * step // 10
                x[0] += step; x[3] += inc; x[4] += full
                if bal > cap:
                    x[1] += step
                    x[5] += max(0, full - inc)
                if bal >= 149 * terr:
                    x[2] += step
    return tot


# ---------- X0 ----------
def x0():
    man = {}
    with open("/agent/repos/c136-data/manifest.jsonl", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r.get("matchId") in MIDS:
                man[r["matchId"]] = r
    L_ = ["# X0 对局表（crosstab.py；结构取自复盘 JSON 的 context/outcome 与 manifest.jsonl；份额取自重放快照：编队在控的号的地合计 ÷ 全图陆地）",
          "# 人头占比 = 编队号数 ÷ 开局有地的真人数（land-facts 的 voronoi.humans）；峰值÷人头 = 份额峰值 ÷ 人头占比",
          "# 结束拍两个数：卡片 = card.json 的 outcome.endTick（编队最后一个号的页面结算拍）；录像 = 重放到的最后一拍",
          "局 | 分型 | 结果 | 图/陆地 | 真人 队数 各队人数 | 编队号数 人头占比 | 结束拍 卡片/录像 | 编队地份额：630 / 1500 / 3000 / 4284 拍 | 份额峰值（拍） 峰值÷人头 | 出局"]
    for m in MIDS:
        j, d = J(m), D(m)
        c, o = j["context"], j["outcome"]
        vor = facts(m, "land")["voronoi"]
        head = 100.0 * vor["squadBots"] / vor["humans"]
        end = d.R["endTick"]
        sh = {}
        for t in (630, 1500, 3000, 4284):
            if t <= end:
                row = d.team_rows([t])[0]
                sh[t] = 100.0 * row[6] / d.land
        peak, peak_t = 0.0, 0
        for i, t in enumerate(d.T):
            ctl = [q for q in d.sqids if not (0 <= d.left[q] <= t)]
            v = sum(d.R["snapTerr"][i][q] for q in ctl)
            if v > peak:
                peak, peak_t = v, t
        peak_pct = 100.0 * peak / d.land
        sizes = c.get("teamSizes") or []
        team_txt = "/".join(str(x) for x in sizes[1:]) if sizes else "无队伍"
        pres = c.get("presence") or {}
        pres_txt = " ".join(f"{ {'died': '死', 'left': '离线', 'end': '活到结束'}.get(k_, k_)} {v}" for k_, v in pres.items())
        L_.append(f"{m} | {j['lossArchetype']} | {o.get('result')} | 图 {c.get('map')}/{c.get('mapLand'):,} | {vor['humans']} 人 {c.get('teams')} 队 {team_txt} | "
                  f"{vor['squadBots']} 号 {head:.1f}% | {o.get('endTick')}/{end} | " + " / ".join(f"{sh[t]:.2f}%" if t in sh else "—" for t in (630, 1500, 3000, 4284))
                  + f" | {peak_pct:.2f}%（{peak_t}） {peak_pct / head:.2f} | {pres_txt}")
    L_.append("")
    L_.append("# manifest.jsonl 里这 11 局的行（cohort / split / mode / nominalTeams→actualTeams / baseWinExpectation / anomaliesSummary）")
    for m in MIDS:
        r = man.get(m, {})
        a = r.get("anomaliesSummary") or {}
        L_.append(f"{m} | {r.get('cohort')} {r.get('split')} mode={r.get('mode')} 队 {r.get('nominalTeams')}→{r.get('actualTeams')} 期望 {r.get('baseWinExpectation')} | "
                  f"drop30 {a.get('drop30Count')} 调度/捐款 {a.get('totalTransfers')} 疑似被拒 {a.get('likelyRejectedTransfers')} 被围高密快照 {a.get('boxedHighDensSnapshots')} 策略报错 {a.get('strategyErrors')}")
    write("X0-roster.txt", L_)


# ---------- X1 ----------
def x1():
    L_ = ["# X1 延迟账补充（crosstab.py；取自 out/dossier/<局>-delay-facts.json；延迟 = 服务器处理拍 − 页面发令拍，只算成交的陆攻+船+捐款）",
          "# 迟到 = 延迟 >30 拍的成交指令；目标已死 = 陆攻落地时目标（AI/真人）已经没地，指令改打无主地或作废；占比 = 目标已死的兵 ÷ 同段打 AI+真人落地的兵",
          "",
          "[X1a] 分时段：成交条数、延迟分位、迟到条数",
          "局 | 0~600：条 P50/P90/最大 >30拍 >90拍 | 600~1500 | 1500~3000 | 3000+ | 整局：条 >30拍（占比） >90拍"]
    for m in MIDS:
        f = facts(m, "delay")
        cells = []
        for r in f["lag"]["byPeriod"]:
            cells.append(f"{r['n']} 条 {r['p50']}/{r['p90']}/{r['max']} >30:{r['gt30']} >90:{r['gt90']}")
        tt = f["lag"]["total"]
        L_.append(f"{m} | " + " | ".join(cells) + f" | {tt['n']} 条 >30:{tt['gt30']}（{pc(tt['gt30'], tt['n'])}） >90:{tt['gt90']}")
    L_ += ["", "[X1b] 分时段：落地的陆攻里迟到的兵、目标已死的条数与兵",
           "局 | 时段 | 落地陆攻 条（打AI/真人/中立） | 打AI+真人的兵 | 迟到>30拍 条/兵 | 目标已死 条（AI/真人）/兵/占比 | 其中作废"]
    for m in MIDS:
        f = facts(m, "delay")
        for r in f["late"]["byPeriod"]:
            tr = r["troopsAI"] + r["troopsHuman"]
            L_.append(f"{m} | {r['period']} | {r['attacks']}（{r['toAI']}/{r['toHuman']}/{r['toNeutral']}） | {wan(tr)} | {r['late30']}/{wan(r['late30Troops'])} | "
                      f"{r['deadTarget']}（{r['deadTargetAI']}/{r['deadTargetHuman']}）/{wan(r['deadTargetTroops'])}/{pc(r['deadTargetTroops'], tr)} | {r['deadTargetNoop']}")
    L_ += ["", "[X1c] 发令漏斗（陆攻+船：想发→本地受理→落地→生效；捐款：受理→落地），整局",
           "局 | 陆攻+船 想发→受理→落地→生效 | 落地÷受理 | 生效÷受理 | 捐款 受理→落地 | 落地÷受理"]
    for m in MIDS:
        f = facts(m, "delay")
        bp = f["funnel"]["byPeriod"]
        w = sum(r["want"]["attack"] + r["want"]["boat"] for r in bp)
        a = sum(r["acc"]["attack"] + r["acc"]["boat"] for r in bp)
        l_ = sum(r["land"]["attack"] + r["land"]["boat"] for r in bp)
        e = sum(r["eff"]["attack"] + r["eff"]["boat"] for r in bp)
        da, dl = sum(r["acc"]["donate"] for r in bp), sum(r["land"]["donate"] for r in bp)
        L_.append(f"{m} | {w}→{a}→{l_}→{e} | {pc(l_, a, 0)} | {pc(e, a, 0)} | {da}→{dl} | {pc(dl, da, 0)}")
    L_ += ["", "[X1d] 重发串（同一个号对同一目标、同一源码行，相邻发令 ≤10 拍并成一串；同步串 = 首条 ≤45 拍成交；落后串 = 首条 >45 拍才成交）",
           "局 | 串/条 | 同步串：串/条 首条送出 首条成交前多发 多发÷首条 | 落后串：串 发/落 花掉 | 目标已死的串/条"]
    for m in MIDS:
        f = facts(m, "delay")
        t = f["reissue"]["total"]
        L_.append(f"{m} | {t['strings']}/{t['cmds']} | {t['syncStrings']}/{t['syncCmds']} {wan(t['syncFirst'])} {wan(t['syncExtra'])} {per(t['syncExtra'], t['syncFirst'], 2)} | "
                  f"{t['lagStrings']} {t['lagIssued']}/{t['lagExecuted']} {wan(t['lagSpent'])} | {t['deadStrings']}/{t['deadCmds']}")
    L_ += ["", "[X1e] 选点落地（协调器重解轮数、不同解的套数、最小间距首→末、没落到终解的号、叠点对、选点期步数）",
           "局 | 重解轮数 不同解 | 最小间距 首→末 像素 | 落在终解/没落到 | 叠点对 | 选点期步数 | boss"]
    for m in MIDS:
        sp = facts(m, "delay")["spawn"]
        L_.append(f"{m} | {sp.get('rounds')} {sp.get('distinctSolutions')} | {sp.get('minSepFirst')}→{sp.get('minSepLast')} | {sp.get('onFinal')}/{sp.get('notOnFinal')} | "
                  f"{len(sp.get('stackPairs') or [])} | {sp.get('spawnSteps')} | {sp.get('boss')}")
    write("X1-delay.txt", L_)


# ---------- X2 ----------
def x2():
    L_ = ["# X2 好地抢到率三层恒等式（crosstab.py；取自 out/dossier/<局>-land-facts.json 与复盘 JSON 的 latencyAndLand.threeLayer）",
          "# 名下 = 每格陆地归直线最近的真人出生点（Voronoi）后落到该号头上的格数；转化 = 该组的地 ÷ 该组的名下",
          "# 恒等式（1500 拍）：编队人均地 ÷ 其他真人人均地 = 出生份额（人均名下之比）× 转化（地÷名下 之比）；ln 列是两项各自的自然对数（相加 = ln 人均地比）",
          "",
          "[X2a] 1500 拍三层对账",
          "局 | 在场 编队/其他 | 人均地 编队 对 其他 | 人均地比 | 出生份额 | 转化 | ln 出生份额 + ln 转化 = ln 人均地比 | 按其他真人的转化该有 / 实际 / 差"]
    for m in MIDS:
        t = J(m)["latencyAndLand"]["threeLayer"]
        l1, l2, lr = t["layer1SpawnFactor"], t["layer23ConversionFactor"], t["landRatio"]
        L_.append(f"{m} | {t['squadAlive']}/{t['othersAlive']} | {t['landPerHeadSquad']:,} 对 {t['landPerHeadOthers']:,} | {lr:.2f} | {l1:.2f} | {l2:.2f} | "
                  f"{math.log(l1):+.2f} + {math.log(l2):+.2f} = {math.log(lr):+.2f} | {t['expectedAtOthersConversion']:,} / {t['squadTerr']:,} / {t['squadTerr'] - t['expectedAtOthersConversion']:+,}")
    for label, ms in (("11 局", MIDS), ("10 个输局", [m for m in MIDS if m != "A025"])):
        ts = [J(m)["latencyAndLand"]["threeLayer"] for m in ms]
        g1 = math.exp(sum(math.log(t["layer1SpawnFactor"]) for t in ts) / len(ts))
        g2 = math.exp(sum(math.log(t["layer23ConversionFactor"]) for t in ts) / len(ts))
        g3 = math.exp(sum(math.log(t["landRatio"]) for t in ts) / len(ts))
        n_lt1 = sum(1 for t in ts if t["layer1SpawnFactor"] < 1)
        n_c_lt1 = sum(1 for t in ts if t["layer23ConversionFactor"] < 1)
        L_.append(f"{label}的几何平均：出生份额 {g1:.2f} × 转化 {g2:.2f} → 人均地比 {g3:.2f}；出生份额 <1 的局 {n_lt1}/{len(ts)}，转化 <1 的局 {n_c_lt1}/{len(ts)}")
    L_ += ["", "[X2b] 出生份额（Voronoi 名下）",
           "局 | 开局有地真人/编队号 | 编队名下格数 占全图 | 人头占比 | 份额÷人头 | 每号名下 中位（最小~最大） | 其他真人名下 中位（下四分位） | 其他真人里名下比编队中位还小的人数"]
    for m in MIDS:
        v = facts(m, "land")["voronoi"]
        L_.append(f"{m} | {v['humans']}/{v['squadBots']} | {v['squadCells']:,} {v['squadCellsPct']}% | {v['headPct']}% | {v['shareOverHead']:.2f} | "
                  f"{v['squadMedian']:,.0f}（{v['squadMin']:,}~{v['squadMax']:,}） | {v['othersMedian']:,.0f}（{v['othersQ1']:,.0f}） | {v.get('othersSmallerThanSquadMedian')}")
    L_ += ["", "[X2c] 转化的时间序列：地÷名下 编队 对 其他真人（括号里是两者之比）",
           "局 | " + " | ".join(f"{t} 拍" for t in (630, 900, 1200, 1500, 1800))]
    for m in MIDS:
        cap = {c["t"]: c for c in facts(m, "land")["capture"]}
        cells = []
        for t in (630, 900, 1200, 1500, 1800):
            c = cap.get(t)
            if not c:
                cells.append("—")
                continue
            cells.append(f"{c['squadRatio']:.2f} 对 {c['othersRatio']:.2f}（{c['squadRatio'] / c['othersRatio']:.2f}）")
        L_.append(f"{m} | " + " | ".join(cells))
    L_ += ["", "[X2d] 600 拍时接壤编队的 AI 的地（B 集）与编队名下范围里的 AI 地（A 集），到 1800 拍（不足则到最后一个采样拍）归了谁",
           "局 | B 集 格数（AI 个数）→ 编队/同队路人/敌方真人/仍是AI | A 集 格数 → 编队/同队路人/敌方真人/仍是AI"]
    for m in MIDS:
        af = facts(m, "land")["aiFate"]
        cells = []
        for key in ("B", "A"):
            s = af[key]
            r = s["rows"][-1]
            n = max(1, s["cells"])
            ais = f"（{s['ais']} 个）" if "ais" in s else ""
            cells.append(f"{s['cells']:,}{ais} → {pc(r['squad'], n, 0)}/{pc(r['mate'], n, 0)}/{pc(r['enemy'], n, 0)}/{pc(r['ai'], n, 0)}（{r['t']} 拍）")
        L_.append(f"{m} | " + " | ".join(cells))
    L_ += ["", "[X2e] 600~1500 拍 pickTarget 的决策拍去向（freeze-scan；冻结 = 有 AI 邻居、没在扩中立、pickTarget 返回空且 safeFinite ≥ (1−0.2141)×余额）",
           "局 | 决策拍 | 有目标 | 扩中立 | 没有 AI 邻居 | 冻结（占比） 其中卡在 编队友/路人队友/敌方真人/AI | 冻结拍上余额·拍"]
    for m in MIDS:
        fz = J(m)["openingFreeze"]["team"]
        fb = fz.get("frozenBy") or {}
        L_.append(f"{m} | {fz['ticks']} | {fz['target']}（{pc(fz['target'], fz['ticks'], 0)}） | {fz['neutral']}（{pc(fz['neutral'], fz['ticks'], 0)}） | {fz['noai']}（{pc(fz['noai'], fz['ticks'], 0)}） | "
                  f"{fz['frozen']}（{pc(fz['frozen'], fz['ticks'], 0)}） {fb.get('squad', 0)}/{fb.get('mate', 0)}/{fb.get('enemy', 0)}/{fb.get('ai', 0)} | {wan(fz.get('frozenBalTicks'))}")
    write("X2-land.txt", L_)


# ---------- X3 ----------
def x3():
    L_ = ["# X3 整局兵力去向总账（crosstab.py；重放精确值；口径同卷宗 [L]：每个席位只算 开局→离线/灭亡）",
          "# 利息 = 整局利息收入合计；各项写成占该组利息的百分比。打真人 = 烧 + 槽内对消；三项费 = 陆攻手续费 + 捐款税 + 船费；",
          "# 挨打掉兵 = 别人打它时从余额里扣掉的兵；末余额 = 离线/灭亡/终局那一拍的余额 + 在途兵。组内互捐的到账不是去向（只有税是）。",
          "# 「以上合计」不到或超过 100% 的部分：组外来的捐款（净收捐列）、空壳/AI 送的兵（X3c 表外进项）、船上的兵（海上损耗、移交、登陆）、撞硬上限没入账的兵、开局本金。",
          "",
          "[X3a] 各组利息的去向（%）",
          "局 | 组 | 有地人数 | 利息 人均利息 | 打中立 | 打AI | 打真人（其中对消） | 三项费（攻击费/捐款税/船费） | 挨打掉兵 | 反击槽被消 | 末余额+在途 | 以上合计 | 净收捐（收捐 − 捐出到账）"]
    rows = {}
    for m in MIDS:
        d = D(m)
        for name, ids in groups(m):
            t = group_total(d, ids)
            rows[(m, name)] = t
            inc = max(1, t["inc"])
            fees = t["atkFee"] + t["donTax"] + t["boatFee"]
            hum = t["burnH"] + t["netH"]
            parts = t["burnN"] + t["burnAI"] + hum + fees + t["defBal"] + t["defSlot"] + t["balEnd"] + t["outEnd"]
            L_.append(f"{m} | {name} | {t['heads']} | {wan(t['inc'])} {wan(t['inc'] / max(1, t['heads']))} | {pc(t['burnN'], inc)} | {pc(t['burnAI'], inc)} | {pc(hum, inc)}（{pc(t['netH'], inc)}） | "
                      f"{pc(fees, inc)}（{pc(t['atkFee'], inc)}/{pc(t['donTax'], inc)}/{pc(t['boatFee'], inc)}） | {pc(t['defBal'], inc)} | {pc(t['defSlot'], inc)} | {pc(t['balEnd'] + t['outEnd'], inc)} | {pc(parts, inc)} | {pc(t['donIn'] - t['donOut'], inc)}")
    L_ += ["", "[X3b] 得地与失地的单价（兵/格；打真人的单价不含对消）",
           "局 | 组 | 中立 格（兵/格） | AI 格（兵/格） | 真人 格（兵/格） | 被真人吃 格（对方烧的兵/格） | 得真人地÷被真人吃"]
    for m in MIDS:
        for name, ids in groups(m):
            t = rows[(m, name)]
            L_.append(f"{m} | {name} | {t['tilesN']:,}（{per(t['burnN'], t['tilesN'])}） | {t['tilesAI']:,}（{per(t['burnAI'], t['tilesAI'])}） | {t['tilesH']:,}（{per(t['burnH'], t['tilesH'])}） | "
                      f"{t['lostTiles']:,}（{per(t['lostBurn'], t['lostTiles'])}） | {per(t['tilesH'], t['lostTiles'], 2)}")
    L_ += ["", "[X3c] 编队：捐款、船、表外进项（卷宗 [L] 的 squadLedger.total）",
           "局 | 互捐到账 税 税÷到账 | 捐给编队外 | 收捐（含路人给的） | 表外进项（空壳/AI 送的） | 船 出兵/船费 | 船靠队友岸（其中编队外） | 船登陆敌方真人"]
    for m in MIDS:
        d = D(m)
        d.sec_total()
        s = d.squad_ledger["total"]
        L_.append(f"{m} | {wan(s['donOut'])} {wan(s['donTax'])} {pc(s['donTax'], s['donOut'], 0)} | {wan(s['donOutNonSquad'])} | {wan(s['donIn'])} | {wan(d.squad_ledger['giftIn'])} | "
                  f"{wan(s['boatOut'])}/{wan(s['boatFee'])} | {wan(s['boatToMate'])}（{wan(s['boatToOutside'])}） | {wan(s['boatOnEnemy'])}")
        j = (J(m).get("squadLedger") or {}).get("total")
        if j:
            for k_ in ("inc", "burnH", "netH", "atkFee", "defBal", "donTax", "lostTiles"):
                if j[k_] != s[k_] or rows[(m, "编队")][k_] != s[k_]:
                    L_.append(f"  !! {m} {k_}: 复盘 JSON {j[k_]}，卷宗重算 {s[k_]}，本脚本 {rows[(m, '编队')][k_]}")
    write("X3-ledger.txt", L_)


# ---------- X4 ----------
def x4():
    L_ = ["# X4 分段对照账（crosstab.py；口径同 winledger.py / 卷宗 [E]；断面 0 / 630 / 1500 / 4284 / 结束）",
          "# 每组一行：窗口两端 有地人数、地（占全图 %）、兵；窗口里 利息（人均 = 利息 ÷ 窗口起点有地人数）；对真人 条/出/烧/得地（兵/格）；对 AI+中立 烧/得地（兵/格）；",
          "#           挨打 掉兵/失地（兵/格）；捐出 笔/到账/税；船 条/兵/费；三项费 = 陆攻手续费 + 捐款税 + 船费，及其占利息的百分比",
          "局 | 窗口 | 组 | 人数 | 地 %→% | 兵 | 利息（人均） | 对真人 条 出 烧 得地（兵/格） | 对AI+中立 烧 得地（兵/格） | 挨打 掉兵 失地（兵/格） | 捐出 笔 到账 税 | 船 条 兵 费 | 三项费（占利息）"]
    for m in MIDS:
        d = D(m)
        end = d.R["endTick"]
        cuts = [c for c in CUTS if c < end] + [end]
        for a, b in zip(cuts, cuts[1:]):
            for name, ids in groups(m):
                r = window_row(d, ids, a, b)
                L_.append(f"{m} | {a}~{b} | {name} | {r['n0']}→{r['n1']} | {100 * r['L0'] / d.land:.2f}%→{100 * r['L1'] / d.land:.2f}% | {wan(r['B0'])}→{wan(r['B1'])} | "
                          f"{wan(r['inc'])}（{wan(r['inc'] / max(1, r['n0']))}） | {r['nH']} 条 {wan(r['sentH'])} {wan(r['burnH'])} {r['tilesH']:,}（{per(r['burnH'], r['tilesH'])}） | "
                          f"{wan(r['burnO'])} {r['tilesO']:,}（{per(r['burnO'], r['tilesO'])}） | {wan(r['defBal'])} {r['defTiles']:,}（{per(r['defBal'], r['defTiles'])}） | "
                          f"{r['donN']} 笔 {wan(r['donOut'])} {wan(r['donTax'])} | {r['boatN']} 条 {wan(r['boat'])} {wan(r['boatFee'])} | {wan(r['fees3'])}（{pc(r['fees3'], r['inc'])}）")
    write("X4-windows.txt", L_)

    # X4b：人均口径的对照（编队 对 其他真人 = 全部不是编队号的真人席位，含同队路人与离线空壳；人数 = 该拍有地的席位数）
    B = ["# X4b 断面与窗口的人均对照（crosstab.py；编队 对 其他真人；其他真人 = 全部不是编队号的真人席位，含同队路人和离线后由 AI 托管的空壳）",
         "# 人数 = 该拍有地的席位数；人均 = 合计 ÷ 人数（窗口量按窗口起点的人数）；比 = 编队人均 ÷ 其他真人人均",
         "",
         "[X4b-1] 断面状态：人均地、人均兵、密度（兵÷地）",
         "局 | 断面 | 人数 编队/其他 | 人均地 编队 对 其他（比） | 人均兵 编队 对 其他（比） | 密度 编队 对 其他"]
    W = ["", "[X4b-2] 窗口流量：人均利息、人均花在 AI+中立上的兵、人均得 AI+中立地、对真人 得地−失地（合计）",
         "局 | 窗口 | 人均利息 编队 对 其他（比） | 人均烧在 AI+中立 编队 对 其他（比） | 人均得 AI+中立地 编队 对 其他（比） | 对真人 得地/失地 编队 | 对真人 得地/失地 其他 | 三项费占利息 编队 对 其他"]
    for m in MIDS:
        d = D(m)
        R = d.R
        end = R["endTick"]
        sq = sorted(d.sqids)
        ot = [p for p in range(d.H) if p not in d.bot_of]
        for t in (630, 1500, 4284):
            if t > end:
                continue
            i = d.ix(t)
            row = []
            for ids in (sq, ot):
                n = sum(1 for p in ids if R["snapTerr"][i][p] > 0)
                L1 = sum(R["snapTerr"][i][p] for p in ids)
                B1 = sum(R["snapBal"][i][p] for p in ids)
                row.append((n, L1, B1))
            (n1, l1, b1), (n2, l2, b2) = row
            if not n1 or not n2:
                B.append(f"{m} | {t} | {n1}/{n2} | —")
                continue
            B.append(f"{m} | {t} | {n1}/{n2} | {l1 / n1:,.0f} 对 {l2 / n2:,.0f}（{(l1 / n1) / (l2 / n2):.2f}） | {wan(b1 / n1)} 对 {wan(b2 / n2)}（{(b1 / n1) / max(1e-9, b2 / n2):.2f}） | "
                     f"{b1 / max(1, l1):.1f} 对 {b2 / max(1, l2):.1f}")
        cuts = [c for c in CUTS if c < end] + [end]
        for a, b in zip(cuts, cuts[1:]):
            r1, r2 = window_row(d, sq, a, b), window_row(d, ot, a, b)
            n1, n2 = max(1, r1["n0"]), max(1, r2["n0"])

            def ratio(x, y):
                return f"{x / y:.2f}" if y else "—"
            W.append(f"{m} | {a}~{b} | {wan(r1['inc'] / n1)} 对 {wan(r2['inc'] / n2)}（{ratio(r1['inc'] / n1, r2['inc'] / n2)}） | "
                     f"{wan(r1['burnO'] / n1)} 对 {wan(r2['burnO'] / n2)}（{ratio(r1['burnO'] / n1, r2['burnO'] / n2)}） | "
                     f"{r1['tilesO'] / n1:,.0f} 对 {r2['tilesO'] / n2:,.0f}（{ratio(r1['tilesO'] / n1, r2['tilesO'] / n2)}） | "
                     f"{r1['tilesH']:,}/{r1['defTiles']:,} | {r2['tilesH']:,}/{r2['defTiles']:,} | {pc(r1['fees3'], r1['inc'])} 对 {pc(r2['fees3'], r2['inc'])}")
    write("X4b-percap.txt", B + W)


# ---------- X5 ----------
def x5():
    L_ = ["# X5 利息效率（crosstab.py；口径同卷宗 [P]；只算每个席位在线且有地的拍）",
          "# 满额 = 同样的地、余额一直等于软上限（100×地）时的利息；超软 = 余额 > 软上限的 席位·拍；贴硬 = 余额 ≥ 149×地 的 席位·拍；少拿 = 超软那些拍上 满额 − 实得",
          "局 | 时段 | 组 | 席位·拍 | 超软（占比） | 贴硬（占比） | 实得 | 满额 | 实得÷满额 | 超软拍上少拿"]
    for m in MIDS:
        d = D(m)
        end = d.R["endTick"]
        phases = [(a, min(b, end)) for a, b in ((600, 1500), (1500, 4284), (4284, end)) if a < end]
        res = {}
        for name, ids in groups(m):
            res[name] = interest_eff(d, ids, phases)
        for k_, (a, b) in enumerate(phases):
            for name, _ in groups(m):
                x = res[name][k_]
                L_.append(f"{m} | {a}~{b} | {name} | {x[0]:,} | {x[1]:,}（{pc(x[1], x[0], 0)}） | {x[2]:,}（{pc(x[2], x[0], 0)}） | {wan(x[3])} | {wan(x[4])} | {pc(x[3], x[4], 0)} | {wan(x[5])}")
        je = (J(m).get("interestEfficiency") or {}).get("phases")
        if je:
            for k_, p in enumerate(je):
                x = res["编队"][k_]
                if p["income"] != x[3] or p["incomeAtSoftCap"] != x[4]:
                    L_.append(f"  !! {m} {p['from']}~{p['to']}：复盘 JSON 实得 {p['income']} 满额 {p['incomeAtSoftCap']}，本脚本 {x[3]} / {x[4]}")
    write("X5-interest.txt", L_)


# ---------- X6 ----------
def x6():
    L_ = ["# X6 捐款与调度（crosstab.py；日志条数/成交/额度拒 取自复盘 JSON 的 donationAudit（卷宗 [H] 的逐笔配对）；全场捐款网络取自重放 cmdLog（卷宗 [N]））",
          "# 额度拒 = 日志有 HL-DISPATCH/HL-DONATE、重放里没有成交，且按引擎额度公式复算 已用点数 + 本笔点数 > 当拍上限",
          "",
          "[X6a] 编队的调度/捐款：日志 → 成交 → 额度拒",
          "局 | 日志条数 | 成交（占比） | 额度拒（占比） | 其它没成交 | 成交到账 | 税 | 税÷到账 | 税÷编队整局利息"]
    for m in MIDS:
        da = J(m)["donationAudit"]
        d = D(m)
        if not hasattr(d, "squad_ledger"):
            d.sec_total()
        inc = d.squad_ledger["total"]["inc"]
        L_.append(f"{m} | {da['logged']} | {da['exec']}（{pc(da['exec'], da['logged'], 0)}） | {da['quota']}（{pc(da['quota'], da['logged'], 0)}） | {da['other']} | {wan(da['amount'])} | {wan(da['fee'])} | "
                  f"{pc(da['fee'], da['amount'], 0)} | {pc(da['fee'], inc)}")
    L_ += ["", "[X6b] 全场成交捐款按组、按额度分段的到账（<2142 / 2142~3212 / 3213~4283 / ≥4284 拍）",
           "局 | 组 | 笔 | 到账 | 税 | 税÷到账 | 分段到账"]
    for m in MIDS:
        d = D(m)
        if not d.team_game:
            L_.append(f"{m} | （没有队伍，全场没有捐款）")
            continue
        d.sec_donnet()
        for name, v in sorted((d.donnet or {}).get("byClass", {}).items(), key=lambda kv: -kv[1]["delivered"]):
            bands = " ".join(f"{b}:{wan(x)}" for b, x in v["bands"].items())
            L_.append(f"{m} | {name} | {v['n']} | {wan(v['delivered'])} | {wan(v['tax'])} | {pc(v['tax'], v['delivered'], 0)} | {bands}")
    L_ += ["", "[X6c] tryDonateToTeammate 每次调用停在哪一道闸（donate-why；A051 的复盘 JSON 没有这一节）",
           "局 | 调用次数 | 发出 | slotPhase（没轮到） | cooldown12 | busy | A:dMe | B:dMe | pct<180 | 其它闸"]
    for m in MIDS:
        g = J(m).get("donateGates")
        if not g:
            L_.append(f"{m} | —")
            continue
        t = dict(g["total"])
        named = ("sent", "slotPhase", "cooldown12", "busy", "A:dMe", "B:dMe", "pct<180")
        rest = " ".join(f"{k_}:{v}" for k_, v in sorted(t.items(), key=lambda kv: -kv[1]) if k_ not in named)
        L_.append(f"{m} | {g['calls']} | {t.get('sent', 0)} | {t.get('slotPhase', 0)} | {t.get('cooldown12', 0)} | {t.get('busy', 0)} | {t.get('A:dMe', 0)} | {t.get('B:dMe', 0)} | {t.get('pct<180', 0)} | {rest}")
    L_ += ["", "[X6d] DROP30（90 拍内余额跌 ≥30% 的区间）按主因",
           "局 | 区间数 | " + " | ".join(("捐款", "挨打", "攻真人", "攻AI", "攻中立", "船", "其它"))]
    for m in MIDS:
        dr = J(m)["drop30"]
        bc = dict(dr.get("byMainCause") or {})
        known = ("捐款", "挨打", "攻真人", "攻AI", "攻中立", "船")
        other = sum(v for k_, v in bc.items() if k_ not in known)
        L_.append(f"{m} | {dr['count']} | " + " | ".join(str(bc.get(k_, 0)) for k_ in known) + f" | {other}")
    import c136lib as L
    bands = ((0, 2142, "<2142"), (2142, 3213, "2142~3212"), (3213, 4284, "3213~4283"), (4284, 10 ** 9, "≥4284"))
    L_ += ["", "[X6e] 按额度分段：日志里的调度条数（页面发令拍；进攻档/防守档/产出档）→ 重放里编队号成交的捐款笔数与到账（服务器处理拍）",
           "# 进攻档 = offense_dispatch，防守档 = defense_dispatch，产出档 = yield_opt_dispatch（events.csv 的 kind 列；只数本房间的编队号）",
           "局 | " + " | ".join(f"{nm}：日志（进/防/产）→成交 笔 到账" for _, _, nm in bands) + " | 2142 拍前日志条数占整局"]
    tot_log, tot_ex, tot_amt = [0] * len(bands), [0] * len(bands), [0] * len(bands)
    for m in MIDS:
        d = D(m)
        ev = [e for e in L.load_events(m) if e.get("type") in ("DISPATCH", "DONATE") and e.get("bot") in d.sq]
        cells = []
        for a, b, nm in bands:
            kinds = Counter(str(e.get("kind")) for e in ev if a <= int(e["t"]) < b)
            n_log = sum(kinds.values())
            ex = [c for pl in d.sqids for c in d.cmds.get(pl, ()) if c[2] == 2 and c[5] and a <= c[0] < b]
            cells.append(f"{n_log}（{kinds.get('offense_dispatch', 0)}/{kinds.get('defense_dispatch', 0)}/{kinds.get('yield_opt_dispatch', 0)}）→{len(ex)} 笔 {wan(sum(c[6] for c in ex))}")
        early = sum(1 for e in ev if int(e["t"]) < 2142)
        L_.append(f"{m} | " + " | ".join(cells) + f" | {early}/{len(ev)}（{pc(early, len(ev), 0)}）")
        for k_, (a, b, nm) in enumerate(bands):
            tot_log[k_] += sum(1 for e in ev if a <= int(e["t"]) < b)
            ex = [c for pl in d.sqids for c in d.cmds.get(pl, ()) if c[2] == 2 and c[5] and a <= c[0] < b]
            tot_ex[k_] += len(ex)
            tot_amt[k_] += sum(c[6] for c in ex)
    L_.append("11 局合计 | " + " | ".join(f"{tot_log[k_]}→{tot_ex[k_]} 笔 {wan(tot_amt[k_])}（成交÷日志 {pc(tot_ex[k_], tot_log[k_], 0)}）" for k_ in range(len(bands))))
    write("X6-donation.txt", L_)


# ---------- X7 ----------
def x7():
    L_ = ["# X7 1500 拍起 buyLand 的决策拍分类（crosstab.py；取自复盘 JSON 的 coreDecisionTicks.team，即 freeze-scan 第二段）",
          "# 发令=buyLand 发了令；同拍被占=同一拍前面已有指令被受理；被围=没有任何陆上邻居；被挡=走到 send 被守卫或适配层拒掉；",
          "# 卡编队友底=只把 safeFinite 当 0 就会出手；卡真人留底=把整个 safeAt 当 0 才会出手；报价高=最便宜的报价 ≥ worth 且没过软上限；等在途=对它已有在途兵；其余=其余不出手",
          "局 | 决策拍 | 发令 | 同拍被占 | 被围 | 被挡 | 卡编队友底 | 卡真人留底 | 报价高 | 等在途 | 其余"]
    keys = ("sent", "slotTaken", "noOffer", "blocked", "frozenSF", "frozenKeep", "pricedHigh", "pulseWait", "pricedOther")
    for m in MIDS:
        c = J(m)["coreDecisionTicks"]["team"]
        n = c["ticks"]
        L_.append(f"{m} | {n} | " + " | ".join(f"{c.get(k_, 0)}（{pc(c.get(k_, 0), n, 0)}）" for k_ in keys))
    L_ += ["", "# 逐号：1500 拍起「被围」占该号决策拍 ≥50% 的号数、≥90% 的号数（coreDecisionTicks.perBot）",
           "局 | 号数 | 被围≥50% | 被围≥90% | 整局一条 buyLand 都没发过的号"]
    for m in MIDS:
        pb = J(m)["coreDecisionTicks"]["perBot"]
        a = sum(1 for v in pb.values() if v["ticks"] and v["noOffer"] >= 0.5 * v["ticks"])
        b = sum(1 for v in pb.values() if v["ticks"] and v["noOffer"] >= 0.9 * v["ticks"])
        z = sum(1 for v in pb.values() if v["ticks"] and v["sent"] == 0)
        L_.append(f"{m} | {len(pb)} | {a} | {b} | {z}")
    write("X7-decision.txt", L_)


# ---------- X8 ----------
def x8():
    L_ = ["# X8 报价对 worth（crosstab.py 调 belowworth.py 的 count；读影子缓存的 acts；每个决策拍只进一类，口径见 belowworth.py 文件头）",
          "# 不给脉冲档 = 「低于worth」里排第一的报价 pulseMode=0 且 nearCollapse=0 的拍（只剩整吃档可走）",
          "局 | 窗口 | 决策拍 | 发令 | 没报价 | 过软上限 | 低于worth（其中不给脉冲档） | 高于worth | 其它 | 低于worth÷(低于+高于)"]
    for m in MIDS:
        end = D(m).R["endTick"]
        for a, b in ((1500, 2399), (2400, end)):
            if a > end:
                continue
            _, tot, n, _ = BW.count(m, a, b)
            lo, hi = tot["低于worth"], tot["高于worth"]
            L_.append(f"{m} | {a}~{b} | {n} | {tot['发令']}（{pc(tot['发令'], n, 0)}） | {tot['没报价']}（{pc(tot['没报价'], n, 0)}） | {tot['过软上限']} | "
                      f"{lo}（{tot['不给脉冲档']}） | {hi} | {tot['其它']} | {pc(lo, lo + hi, 0)}")
    L_ += ["", "# 逐号：1500 拍~结束 「低于worth」≥100 个决策拍的号（号：低于worth 拍数 / 其中不给脉冲档 / 该号决策拍）"]
    for m in MIDS:
        end = D(m).R["endTick"]
        per_, _, _, _ = BW.count(m, 1500, end)
        big = [(b, c) for b, c in per_.items() if c["低于worth"] >= 100]
        big.sort(key=lambda x: -x[1]["低于worth"])
        L_.append(f"{m} | " + ("；".join(f"{b} {c['低于worth']}/{c['不给脉冲档']}/{c['决策拍']}" for b, c in big) if big else "没有"))
    write("X8-belowworth.txt", L_)


# ---------- X9 ----------
def split_ids(s):
    out = []
    for part in str(s or "").split("/"):
        part = part.strip()
        if part:
            out.append(part.split("（")[0].strip())
    return out


def x9():
    dec = defaultdict(lambda: defaultdict(Counter))  # 模式 -> 局 -> 判定
    dth = defaultdict(Counter)
    L_ = ["# X9 模式普查（crosstab.py；数的是 11 份复盘 JSON 里手工打的标：decisions[].patternId（一条决策打了几个编号就各记一次）、deaths[].patternIds、newPatterns、turningPoints）",
          "# 这是复盘员打标的次数，不是检测脚本的全量计数；每局只挑了 20 条上下的决策实例",
          "",
          "[X9a] 决策实例按模式编号：实例数、出现的局数、判定（错/对/不明）、局名单"]
    verdicts = Counter()
    for m in MIDS:
        j = J(m)
        for x in j["decisions"]:
            verdicts[(m, x.get("verdict"))] += 1
            for pid in split_ids(x.get("patternId")):
                dec[pid][m][x.get("verdict")] += 1
        for x in j["deaths"]:
            for pid in (x.get("patternIds") or []):
                for q in split_ids(pid):
                    dth[q][m] += 1
    rows = []
    for pid, bym in dec.items():
        n = sum(sum(c.values()) for c in bym.values())
        v = Counter()
        for c in bym.values():
            v.update(c)
        rows.append((len(bym), n, pid, v, bym))
    rows.sort(key=lambda r: (-r[0], -r[1], r[2]))
    for nm_, n, pid, v, bym in rows:
        L_.append(f"{pid} | {n} 条 | {nm_} 局 | 错 {v.get('error', 0)} 对 {v.get('good', 0)} 不明 {v.get('unclear', 0)} | " + " ".join(m for m in MIDS if m in bym))
    L_ += ["", "[X9b] 每局决策实例的判定", "局 | 条数 | 错 | 对 | 不明"]
    for m in MIDS:
        e, g, u = verdicts[(m, "error")], verdicts[(m, "good")], verdicts[(m, "unclear")]
        L_.append(f"{m} | {e + g + u} | {e} | {g} | {u}")
    L_ += ["", "[X9c] 死因链上的模式编号：号次、局数、局名单"]
    for pid, bym in sorted(dth.items(), key=lambda kv: (-len(kv[1]), -sum(kv[1].values()), kv[0])):
        L_.append(f"{pid} | {sum(bym.values())} 号次 | {len(bym)} 局 | " + " ".join(m for m in MIDS if m in bym))
    L_ += ["", "[X9d] 各局提出的 NEW 模式（proposedId：出现在哪些局的 newPatterns 里）"]
    npm = defaultdict(list)
    names = {}
    for m in MIDS:
        for p in J(m).get("newPatterns") or []:
            npm[p["proposedId"]].append(m)
            names.setdefault(p["proposedId"], p.get("name", ""))
    for pid, ms in sorted(npm.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        L_.append(f"{pid} | {len(ms)} 局 | {' '.join(ms)} | {names[pid][:60]}")
    L_ += ["", "[X9e] 转折窗口：每局条数、陈述类型（observed/inferred）、把握（high/medium/low）、窗口起止拍",
           "局 | 条数 | observed | inferred | high | medium | low | 窗口"]
    for m in MIDS:
        tps = J(m)["turningPoints"]
        st = Counter(t.get("statementType") for t in tps)
        cf = Counter(t.get("confidence") for t in tps)
        L_.append(f"{m} | {len(tps)} | {st.get('observed', 0)} | {st.get('inferred', 0)} | {cf.get('high', 0)} | {cf.get('medium', 0)} | {cf.get('low', 0)} | "
                  + " ".join(f"{t.get('t0')}~{t.get('t1')}" for t in tps))
    L_ += ["", "[X9f] 出局方式与死因（deaths[]）：每局 死/离线/活到结束 的号数，出局拍的最早、中位、最晚",
           "局 | 号数 | died | left | 其它 | 出局拍 最早/中位/最晚"]
    for m in MIDS:
        ds = J(m)["deaths"]
        ev = Counter(x.get("event") for x in ds)
        ts = sorted(x.get("t") for x in ds if isinstance(x.get("t"), (int, float)))
        med = ts[len(ts) // 2] if ts else "—"
        L_.append(f"{m} | {len(ds)} | {ev.get('died', 0)} | {ev.get('left', 0)} | {sum(v for k_, v in ev.items() if k_ not in ('died', 'left'))} | "
                  + (f"{ts[0]}/{med}/{ts[-1]}" if ts else "—"))
    write("X9-patterns.txt", L_)


# ---------- X10 ----------
def ranks(v):
    idx = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(idx):
        j = i
        while j + 1 < len(idx) and v[idx[j + 1]] == v[idx[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1
        for k_ in range(i, j + 1):
            r[idx[k_]] = avg
        i = j + 1
    return r


def pearson(a, b):
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    sa = math.sqrt(sum((x - ma) ** 2 for x in a))
    sb = math.sqrt(sum((x - mb) ** 2 for x in b))
    if sa == 0 or sb == 0:
        return 0.0
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (sa * sb)


def spearman(x, y, iters=20000, seed=136):
    rx, ry = ranks(x), ranks(y)
    rho = pearson(rx, ry)
    rng = random.Random(seed)
    hit = 0
    p = list(ry)
    for _ in range(iters):
        rng.shuffle(p)
        if abs(pearson(rx, p)) >= abs(rho) - 1e-12:
            hit += 1
    return rho, (hit + 1) / (iters + 1)


def pfmt(p):
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def x10():
    V = {}

    def put(name, fn, note):
        V[name] = ([fn(m) for m in MIDS], note)

    def delay_p50(m):
        return next(r for r in facts(m, "delay")["lag"]["byPeriod"] if r["period"] == "600~1500")["p50"]

    def dead_share(m):
        r = next(r for r in facts(m, "delay")["late"]["byPeriod"] if r["period"] == "600~1500")
        tr = r["troopsAI"] + r["troopsHuman"]
        return 100.0 * r["deadTargetTroops"] / tr if tr else 0.0

    def gt30_share(m):
        t = facts(m, "delay")["lag"]["total"]
        return 100.0 * t["gt30"] / t["n"]

    def peak_over_head(m):
        d = D(m)
        vor = facts(m, "land")["voronoi"]
        peak = 0
        for i, t in enumerate(d.T):
            ctl = [q for q in d.sqids if not (0 <= d.left[q] <= t)]
            peak = max(peak, sum(d.R["snapTerr"][i][q] for q in ctl))
        return (peak / d.land) / (vor["squadBots"] / vor["humans"])

    def fee_share(m):
        t = group_total(D(m), D(m).sqids)
        return 100.0 * (t["atkFee"] + t["donTax"] + t["boatFee"]) / max(1, t["inc"])

    def def_share(m):
        t = group_total(D(m), D(m).sqids)
        return 100.0 * t["defBal"] / max(1, t["inc"])

    def percap(m, t):
        """t 拍 编队人均地 ÷ 其他真人人均地（人数 = 该拍有地的席位）；编队或其他真人没人了返回 None。"""
        d = D(m)
        if t > d.R["endTick"]:
            return None
        i = d.ix(t)
        sq = [p for p in d.sqids if d.R["snapTerr"][i][p] > 0]
        ot = [p for p in range(d.H) if p not in d.bot_of and d.R["snapTerr"][i][p] > 0]
        if not sq or not ot:
            return None
        return (sum(d.R["snapTerr"][i][p] for p in sq) / len(sq)) / (sum(d.R["snapTerr"][i][p] for p in ot) / len(ot))

    def win_ratio(m, a, b, key):
        d = D(m)
        ot = [p for p in range(d.H) if p not in d.bot_of]
        r1, r2 = window_row(d, sorted(d.sqids), a, b), window_row(d, ot, a, b)
        return (r1[key] / max(1, r1["n0"])) / max(1e-9, r2[key] / max(1, r2["n0"]))

    def inc_ratio_all(m):
        d = D(m)
        ot = [p for p in range(d.H) if p not in d.bot_of]
        a, b = group_total(d, d.sqids), group_total(d, ot)
        return (a["inc"] / max(1, a["heads"])) / max(1e-9, b["inc"] / max(1, b["heads"]))

    tl = lambda m: J(m)["latencyAndLand"]["threeLayer"]  # noqa: E731
    put("人均地比630", lambda m: percap(m, 630), "630 拍 编队人均地 ÷ 其他真人人均地")
    put("人均地比4284", lambda m: percap(m, 4284), "4284 拍 同上")
    put("得AI地比", lambda m: win_ratio(m, 630, 1500, "tilesO"), "630~1500 拍 人均得 AI+中立地 编队 ÷ 其他真人")
    put("烧AI兵比", lambda m: win_ratio(m, 630, 1500, "burnO"), "630~1500 拍 人均烧在 AI+中立上的兵 编队 ÷ 其他真人")
    put("人均利息比", inc_ratio_all, "整局 人均利息 编队 ÷ 其他真人")
    put("人均地比", lambda m: tl(m)["landRatio"], "1500 拍 编队人均地 ÷ 其他真人人均地")
    put("出生份额", lambda m: tl(m)["layer1SpawnFactor"], "人均名下之比")
    put("转化", lambda m: tl(m)["layer23ConversionFactor"], "1500 拍 地÷名下 之比")
    put("峰值÷人头", peak_over_head, "编队地份额峰值 ÷ 人头占比")
    put("结束拍", lambda m: D(m).R["endTick"], "")
    put("真人数", lambda m: facts(m, "land")["voronoi"]["humans"], "开局有地的真人")
    put("延迟P50", delay_p50, "600~1500 拍 发令→落地 延迟中位")
    put("迟到占比", gt30_share, "整局成交指令里延迟 >30 拍的占比")
    put("目标已死占比", dead_share, "600~1500 拍 打 AI+真人的兵里落地时目标已死的占比")
    put("冻结占比", lambda m: 100.0 * J(m)["openingFreeze"]["team"]["frozen"] / J(m)["openingFreeze"]["team"]["ticks"], "600~1500 拍 决策拍里 safeFinite 冻结的占比")
    put("没AI邻居占比", lambda m: 100.0 * J(m)["openingFreeze"]["team"]["noai"] / J(m)["openingFreeze"]["team"]["ticks"], "600~1500 拍 决策拍里没有 AI 邻居的占比")
    put("被围占比", lambda m: 100.0 * J(m)["coreDecisionTicks"]["team"]["noOffer"] / J(m)["coreDecisionTicks"]["team"]["ticks"], "1500 拍起 决策拍里没有陆上邻居的占比")
    put("三项费占利息", fee_share, "编队整局")
    put("挨打掉兵占利息", def_share, "编队整局")
    L_ = ["# X10 秩相关（crosstab.py；n=11 局，Spearman ρ；p = 把其中一列随机打乱 20,000 次、|ρ| 不小于实测值的比例（双侧，随机种子固定 136））",
          "# 只有 11 局、同一版策略、不是随机抽的；这里的 ρ 只说明这 11 局里两列的排序是否同向，不是因果，也不能外推",
          "",
          "[X10a] 各列的取值（局的顺序：" + " ".join(MIDS) + "）"]
    for name, (vals, note) in V.items():
        L_.append(f"{name}（{note}）: " + " ".join("—" if v is None else (f"{v:.2f}" if isinstance(v, float) else str(v)) for v in vals))
    pairs = [("出生份额", "人均地比"), ("转化", "人均地比"), ("出生份额", "转化"), ("延迟P50", "转化"), ("目标已死占比", "转化"), ("迟到占比", "转化"),
             ("冻结占比", "转化"), ("没AI邻居占比", "转化"), ("真人数", "出生份额"), ("真人数", "延迟P50"), ("延迟P50", "人均地比"),
             ("延迟P50", "得AI地比"), ("目标已死占比", "得AI地比"), ("冻结占比", "得AI地比"), ("没AI邻居占比", "得AI地比"), ("出生份额", "得AI地比"),
             ("烧AI兵比", "得AI地比"), ("得AI地比", "人均地比"), ("人均地比630", "人均地比"), ("人均地比", "人均地比4284"), ("人均地比", "人均利息比"),
             ("人均地比", "峰值÷人头"), ("出生份额", "峰值÷人头"), ("转化", "峰值÷人头"), ("延迟P50", "峰值÷人头"), ("被围占比", "峰值÷人头"),
             ("真人数", "峰值÷人头"), ("三项费占利息", "峰值÷人头"), ("挨打掉兵占利息", "峰值÷人头"), ("人均利息比", "峰值÷人头"),
             ("延迟P50", "三项费占利息"), ("人均地比", "结束拍")]
    L_ += ["", f"[X10b] 成对的秩相关（共 {len(pairs)} 对；同时看这么多对，单看 p<0.05 会有假阳性：按 Bonferroni 折算的门槛是 {0.05 / len(pairs):.4f}）",
           "列 A × 列 B | n | ρ | p（置换）"]
    for a, b in pairs:
        xs, ys = V[a][0], V[b][0]
        keep = [i for i in range(len(MIDS)) if xs[i] is not None and ys[i] is not None]
        rho, p = spearman([xs[i] for i in keep], [ys[i] for i in keep])
        L_.append(f"{a} × {b} | {len(keep)} | {rho:+.2f} | {pfmt(p)}")
    L_ += ["", "[X10c] 去掉胜局 A025 之后（n=10 输局）同样的几对", "列 A × 列 B | n | ρ | p（置换）"]
    drop = MIDS.index("A025")
    for a, b in [("延迟P50", "转化"), ("目标已死占比", "转化"), ("出生份额", "转化"), ("延迟P50", "得AI地比"), ("目标已死占比", "得AI地比"),
                 ("烧AI兵比", "得AI地比"), ("人均地比", "人均地比4284"), ("人均地比", "峰值÷人头"), ("人均地比", "人均利息比"), ("挨打掉兵占利息", "峰值÷人头")]:
        xs, ys = V[a][0], V[b][0]
        keep = [i for i in range(len(MIDS)) if i != drop and xs[i] is not None and ys[i] is not None]
        rho, p = spearman([xs[i] for i in keep], [ys[i] for i in keep])
        L_.append(f"{a} × {b} | {len(keep)} | {rho:+.2f} | {pfmt(p)}")
    write("X10-rank.txt", L_)


# ---------- X11 ----------
def run_tool(script, *args):
    import subprocess
    r = subprocess.run([sys.executable, os.path.join(HERE, script), *args], capture_output=True, text=True, timeout=110)
    return r.stdout.split("\n")


def x11():
    import pingpong as PP
    L_ = ["# X11 几条模式的跨局机械计数（crosstab.py；[X11a] 调 dispatch-follow.py，[X11b] 调 retq.py，[X11c] 读重放 cmdLog 的成交捐款、利息公式用 pingpong.py 的）",
          "",
          "[X11a] 进攻档调度（offense_dispatch）前后 150 拍受捐方有没有对在线真人落过陆攻（dispatch-follow.py 的合计行与分段行）"]
    fol, fol_early = [0, 0, 0], [0, 0, 0]
    for m in MIDS:
        if not D(m).team_game:
            L_.append(f"{m} | 没有队伍，没有调度")
            continue
        out = run_tool("dispatch-follow.py", m)
        tot = next((x.strip() for x in out if x.strip().startswith("合计")), "—")
        seg = next((x.strip() for x in out if x.strip().startswith("按 1000 拍")), "")
        L_.append(f"{m} | {tot} | {seg}")
        nums = [int(x) for x in re.findall(r"(\d+) 条", tot)]
        if len(nums) == 3:
            for k_ in range(3):
                fol[k_] += nums[k_]
        early = re.search(r"1000~1999 调度 (\d+)、之后打了 (\d+)、前后都没打 (\d+)", seg)
        if early:
            for k_ in range(3):
                fol_early[k_] += int(early.group(k_ + 1))
    L_.append(f"10 个有队伍的局合计 | 进攻档调度 {fol[0]} 条；之后 150 拍内受捐方打过真人的 {fol[1]} 条（{pc(fol[1], fol[0], 0)}）；前后 150 拍都没打过真人的 {fol[2]} 条（{pc(fol[2], fol[0], 0)}） | "
              f"其中 1000~1999 拍：调度 {fol_early[0]}、之后打了 {fol_early[1]}、前后都没打 {fol_early[2]}（{pc(fol_early[2], fol_early[0], 0)}）")
    L_ += ["", "[X11b] 编队对真人的陆攻：出/费/烧/对消/得地/退（retq.py 的合计行；窗口 1500~4284 与 4284~结束；退 = 这一段全部退回余额的兵，含打中立/AI 的）"]
    for m in MIDS:
        out = run_tool("retq.py", m, "1500,4284")
        i = next((k_ for k_, x in enumerate(out) if x.strip().startswith("合计")), None)
        rows = [x.strip() for x in out[i + 1:] if x.strip()] if i is not None else []
        for x in rows:
            L_.append(f"{m} | {x}")
    L_ += ["", "[X11c] 编队号 → 编队号 的成交捐款（重放 cmdLog；密度 = 余额 ÷ 地；利息 = 引擎利率公式算的「每 10 拍利息」，捐出方 + 接收方合计，落地当拍前后比）",
           "# 被截短 = 到账比指令兵数少 1 个兵以上（接收方硬上限的余量不够）；接收方更密 = 落地前接收方密度 > 捐出方密度",
           "局 | 窗口 | 笔 到账 税（税÷到账） | 捐出方落地前密度 ≥100 / 40~100 / <40 的笔数 | 捐出方落地后密度 <40 的笔数 | 接收方更密 | 接收方落地后 >100 / ≥149.5 | 被截短 | 利息合计变化 ≤0 的笔数（税）"]
    agg = {"<4284": Counter(), "≥4284": Counter()}
    for m in MIDS:
        d = D(m)
        sq = set(d.sqids)
        land = d.land
        for a, b, nm in ((0, 4284, "<4284"), (4284, 10 ** 9, "≥4284")):
            rows = [c for c in d.R["cmdLog"] if c[2] == 2 and c[5] == 1 and c[1] in sq and c[4] in sq and a <= c[0] < b]
            if not rows:
                L_.append(f"{m} | {nm} | 0 笔")
                continue
            got = tax = hi = midn = lo = after_lo = denser = over = hard = capped = neg = neg_tax = 0
            for c in rows:
                t, p, _, pct, q, ok, g, tx, B0, L0, q0, cap, cost, Tq, bq0 = c[:15]
                dA0, dA1 = B0 / max(1, L0), (B0 - g - tx) / max(1, L0)
                dB0, dB1 = bq0 / max(1, Tq), (bq0 + g) / max(1, Tq)
                i0 = PP.interest(L0, B0, t, land) + PP.interest(Tq, bq0, t, land)
                i1 = PP.interest(L0, B0 - g - tx, t, land) + PP.interest(Tq, bq0 + g, t, land)
                want = min(PP.iV((pct + 1) * B0, 1024), B0 - tx)
                got += g; tax += tx
                if dA0 >= 100:
                    hi += 1
                elif dA0 >= 40:
                    midn += 1
                else:
                    lo += 1
                after_lo += dA1 < 40
                denser += dB0 > dA0
                over += dB1 > 100
                hard += dB1 >= 149.5
                capped += g < want - 1
                if i1 - i0 <= 0:
                    neg += 1; neg_tax += tx
            L_.append(f"{m} | {nm} | {len(rows)} 笔 {wan(got)} {wan(tax)}（{pc(tax, got, 0)}） | {hi} / {midn} / {lo} | {after_lo} | {denser} | {over} / {hard} | {capped} | {neg}（{wan(neg_tax)}）")
            if m != "A025":
                tt = agg[nm]
                for k_, v in zip(("n", "got", "tax", "hi", "mid", "lo", "after_lo", "denser", "over", "hard", "capped", "neg", "neg_tax"),
                                 (len(rows), got, tax, hi, midn, lo, after_lo, denser, over, hard, capped, neg, neg_tax)):
                    tt[k_] += v
    for nm in ("<4284", "≥4284"):
        tt = agg[nm]
        L_.append(f"9 个有队伍的输局合计 | {nm} | {tt['n']} 笔 {wan(tt['got'])} {wan(tt['tax'])}（{pc(tt['tax'], tt['got'], 0)}） | {tt['hi']} / {tt['mid']} / {tt['lo']} | {tt['after_lo']} | {tt['denser']}（{pc(tt['denser'], tt['n'], 0)}） | "
                  f"{tt['over']} / {tt['hard']} | {tt['capped']} | {tt['neg']}（{wan(tt['neg_tax'])}；占笔数 {pc(tt['neg'], tt['n'], 0)}）")
    write("X11-patterns-mech.txt", L_)


# ---------- X12 ----------
def x12():
    """跨局小结：把报告里要引用的「几局里有几局」「最小~最大」统一在这里算出来。"""
    WIN = "A025"
    S = {}

    def put(name, note, fn):
        S[name] = (note, {m: fn(m) for m in MIDS})

    _cut, _win, _tot, _eff = {}, {}, {}, {}

    def cut(m, t):
        if (m, t) not in _cut:
            d = D(m)
            R = d.R
            res = None
            if t <= R["endTick"]:
                i = d.ix(t)
                sq = sorted(d.sqids)
                ot = [p for p in range(d.H) if p not in d.bot_of]
                row = []
                for ids in (sq, ot):
                    row.append((sum(1 for p in ids if R["snapTerr"][i][p] > 0), sum(R["snapTerr"][i][p] for p in ids), sum(R["snapBal"][i][p] for p in ids)))
                (n1, l1, b1), (n2, l2, b2) = row
                if n1 and n2 and l1 and l2:
                    res = {"land": (l1 / n1) / (l2 / n2), "bal": (b1 / n1) / (b2 / n2), "dens": (b1 / l1) / (b2 / l2), "n1": n1}
            _cut[(m, t)] = res
        return _cut[(m, t)]

    def cutv(m, t, k_):
        c = cut(m, t)
        return c[k_] if c else None

    def win(m, a, b):
        if (m, a, b) not in _win:
            d = D(m)
            end = d.R["endTick"]
            b2 = end if b is None else b
            ot = [p for p in range(d.H) if p not in d.bot_of]
            _win[(m, a, b)] = (window_row(d, sorted(d.sqids), a, b2), window_row(d, ot, a, b2))
        return _win[(m, a, b)]

    def wratio(m, a, b, key):
        r1, r2 = win(m, a, b)
        y = r2[key] / max(1, r2["n0"])
        return (r1[key] / max(1, r1["n0"])) / y if y else None

    def tot(m, which):
        if (m, which) not in _tot:
            g = groups(m)
            ids = g[0][1] if which == "sq" else g[-1][1]
            _tot[(m, which)] = group_total(D(m), ids)
        return _tot[(m, which)]

    def share(m, which, *keys):
        t = tot(m, which)
        return 100.0 * sum(t[k_] for k_ in keys) / max(1, t["inc"])

    def eff(m, which):
        if (m, which) not in _eff:
            g = groups(m)
            ids = g[0][1] if which == "sq" else g[-1][1]
            _eff[(m, which)] = interest_eff(D(m), ids, [(1500, 4284)])[0]
        return _eff[(m, which)]

    def lagrow(m):
        return next(r for r in facts(m, "delay")["lag"]["byPeriod"] if r["period"] == "600~1500")

    def laterow(m):
        return next(r for r in facts(m, "delay")["late"]["byPeriod"] if r["period"] == "600~1500")

    def dead_share(m):
        r = laterow(m)
        tr = r["troopsAI"] + r["troopsHuman"]
        return 100.0 * r["deadTargetTroops"] / tr if tr else 0.0

    def funnel(m, num, den):
        bp = facts(m, "delay")["funnel"]["byPeriod"]
        x = sum(r[num]["attack"] + r[num]["boat"] for r in bp)
        y = sum(r[den]["attack"] + r[den]["boat"] for r in bp)
        return 100.0 * x / y if y else None

    def capr(m, t):
        c = {c["t"]: c for c in facts(m, "land")["capture"]}.get(t)
        return c["squadRatio"] / c["othersRatio"] if c else None

    def fate(m, key):
        s = facts(m, "land")["aiFate"][key]
        return 100.0 * s["rows"][-1]["squad"] / max(1, s["cells"])

    def fz(m, k_):
        f = J(m)["openingFreeze"]["team"]
        return 100.0 * f[k_] / f["ticks"]

    def fz_by_squad(m):
        f = J(m)["openingFreeze"]["team"]
        return 100.0 * (f.get("frozenBy") or {}).get("squad", 0) / f["frozen"] if f["frozen"] else None

    def core(m, k_):
        c = J(m)["coreDecisionTicks"]["team"]
        return 100.0 * c.get(k_, 0) / c["ticks"]

    def da(m, k_):
        x = J(m)["donationAudit"]
        return 100.0 * x[k_] / x["logged"] if x["logged"] else None

    _bw = {}

    def bw(m):
        if m not in _bw:
            _, t, n, _ = BW.count(m, 1500, 2399)
            _bw[m] = (t, n)
        return _bw[m]

    def bw_low(m):
        t, n = bw(m)
        return 100.0 * t["低于worth"] / (t["低于worth"] + t["高于worth"]) if (t["低于worth"] + t["高于worth"]) else None

    def bw_nopulse(m):
        t, n = bw(m)
        return 100.0 * t["不给脉冲档"] / t["低于worth"] if t["低于worth"] else None

    tl = lambda m: J(m)["latencyAndLand"]["threeLayer"]  # noqa: E731
    vor = lambda m: facts(m, "land")["voronoi"]  # noqa: E731

    put("A1 人均地比 630", "630 拍 编队人均地 ÷ 其他真人人均地", lambda m: cutv(m, 630, "land"))
    put("A2 人均地比 1500", "1500 拍", lambda m: cutv(m, 1500, "land"))
    put("A3 人均地比 4284", "4284 拍", lambda m: cutv(m, 4284, "land"))
    put("A4 人均兵比 630", "630 拍 编队人均余额 ÷ 其他真人人均余额", lambda m: cutv(m, 630, "bal"))
    put("A5 人均兵比 1500", "1500 拍", lambda m: cutv(m, 1500, "bal"))
    put("A6 人均兵比 4284", "4284 拍", lambda m: cutv(m, 4284, "bal"))
    put("A7 密度比 1500", "1500 拍 编队（兵÷地）÷ 其他真人（兵÷地）", lambda m: cutv(m, 1500, "dens"))
    put("A8 在场号数 4284", "4284 拍编队还有地的号数", lambda m: (cut(m, 4284) or {}).get("n1"))
    put("B1 人均利息比 0~630", "窗口里 编队人均利息 ÷ 其他真人人均利息", lambda m: wratio(m, 0, 630, "inc"))
    put("B2 人均利息比 630~1500", "", lambda m: wratio(m, 630, 1500, "inc"))
    put("B3 人均利息比 1500~4284", "", lambda m: wratio(m, 1500, 4284, "inc"))
    put("B4 人均利息比 4284~结束", "", lambda m: wratio(m, 4284, None, "inc"))
    put("B5 人均烧AI+中立比 0~630", "窗口里 编队人均烧在 AI+中立上的兵 ÷ 其他真人的", lambda m: wratio(m, 0, 630, "burnO"))
    put("B6 人均烧AI+中立比 630~1500", "", lambda m: wratio(m, 630, 1500, "burnO"))
    put("B7 人均得AI+中立地比 0~630", "窗口里 编队人均得 AI+中立地 ÷ 其他真人的", lambda m: wratio(m, 0, 630, "tilesO"))
    put("B8 人均得AI+中立地比 630~1500", "", lambda m: wratio(m, 630, 1500, "tilesO"))
    put("B9 人均得AI+中立地比 1500~4284", "", lambda m: wratio(m, 1500, 4284, "tilesO"))
    put("B10 对真人净得地 630~1500", "编队 得真人地 − 被吃的地（格）", lambda m: win(m, 630, 1500)[0]["tilesH"] - win(m, 630, 1500)[0]["defTiles"])
    put("B11 对真人净得地 1500~4284", "", lambda m: win(m, 1500, 4284)[0]["tilesH"] - win(m, 1500, 4284)[0]["defTiles"])
    put("B12 对真人净得地 4284~结束", "", lambda m: win(m, 4284, None)[0]["tilesH"] - win(m, 4284, None)[0]["defTiles"])
    put("B13 三项费占利息 1500~4284 编队", "%", lambda m: 100.0 * win(m, 1500, 4284)[0]["fees3"] / max(1, win(m, 1500, 4284)[0]["inc"]))
    put("B14 三项费占利息 1500~4284 其他真人", "%", lambda m: 100.0 * win(m, 1500, 4284)[1]["fees3"] / max(1, win(m, 1500, 4284)[1]["inc"]))
    put("C1 挨打掉兵占利息 编队", "整局 %", lambda m: share(m, "sq", "defBal"))
    put("C2 挨打掉兵占利息 对手", "整局 %；对手 = 敌方真人（自由混战局 = 其他真人）", lambda m: share(m, "op", "defBal"))
    put("C3 攻击费占利息 编队", "%", lambda m: share(m, "sq", "atkFee"))
    put("C4 攻击费占利息 对手", "%", lambda m: share(m, "op", "atkFee"))
    put("C5 捐款税占利息 编队", "%", lambda m: share(m, "sq", "donTax"))
    put("C6 捐款税占利息 对手", "%", lambda m: share(m, "op", "donTax"))
    put("C7 船费占利息 编队", "%", lambda m: share(m, "sq", "boatFee"))
    put("C8 船费占利息 对手", "%", lambda m: share(m, "op", "boatFee"))
    put("C9 末余额+在途占利息 编队", "%", lambda m: share(m, "sq", "balEnd", "outEnd"))
    put("C10 末余额+在途占利息 对手", "%", lambda m: share(m, "op", "balEnd", "outEnd"))
    put("C11 打AI占利息 编队", "%", lambda m: share(m, "sq", "burnAI"))
    put("C12 打AI占利息 对手", "%", lambda m: share(m, "op", "burnAI"))
    put("C13 打真人占利息 编队", "%（烧 + 对消）", lambda m: share(m, "sq", "burnH", "netH"))
    put("C14 打真人占利息 对手", "%", lambda m: share(m, "op", "burnH", "netH"))
    put("C15 人均利息 编队÷对手", "整局人均利息之比", lambda m: (tot(m, "sq")["inc"] / max(1, tot(m, "sq")["heads"])) / max(1e-9, tot(m, "op")["inc"] / max(1, tot(m, "op")["heads"])))
    put("C16 得真人地÷被真人吃 编队", "整局格数之比", lambda m: tot(m, "sq")["tilesH"] / max(1, tot(m, "sq")["lostTiles"]))
    put("C17 得真人地÷被真人吃 对手", "", lambda m: tot(m, "op")["tilesH"] / max(1, tot(m, "op")["lostTiles"]))
    put("C18 编队吃真人地的单价", "兵/格，不含对消", lambda m: tot(m, "sq")["burnH"] / max(1, tot(m, "sq")["tilesH"]))
    put("C19 别人吃编队地的单价", "兵/格（对方烧的兵 ÷ 编队失地）", lambda m: tot(m, "sq")["lostBurn"] / max(1, tot(m, "sq")["lostTiles"]))
    put("C20 税÷互捐到账 编队", "%", lambda m: (100.0 * tot(m, "sq")["donTax"] / tot(m, "sq")["donOut"]) if tot(m, "sq")["donOut"] else None)
    put("D1 延迟P50 600~1500", "拍", lambda m: lagrow(m)["p50"])
    put("D2 延迟P90 600~1500", "拍", lambda m: lagrow(m)["p90"])
    put("D3 迟到占比 整局", "% 成交指令里延迟 >30 拍", lambda m: 100.0 * facts(m, "delay")["lag"]["total"]["gt30"] / facts(m, "delay")["lag"]["total"]["n"])
    put("D4 目标已死占比 600~1500", "% 打 AI+真人的兵里落地时目标已死", dead_share)
    put("D5 陆攻+船 落地÷受理", "% 整局", lambda m: funnel(m, "land", "acc"))
    put("D6 陆攻+船 生效÷受理", "% 整局", lambda m: funnel(m, "eff", "acc"))
    put("D7 同步串 多发÷首条", "首条成交前多发的兵 ÷ 首条送出的兵", lambda m: facts(m, "delay")["reissue"]["total"]["syncExtra"] / max(1, facts(m, "delay")["reissue"]["total"]["syncFirst"]))
    put("D8 落后串数", "首条 >45 拍才成交的重发串", lambda m: facts(m, "delay")["reissue"]["total"]["lagStrings"])
    put("E1 出生份额", "人均名下之比（三层恒等式第一层）", lambda m: tl(m)["layer1SpawnFactor"])
    put("E2 转化 1500", "地÷名下 之比（第二、三层合并）", lambda m: tl(m)["layer23ConversionFactor"])
    put("E3 转化之比 630", "地÷名下 编队 ÷ 其他真人", lambda m: capr(m, 630))
    put("E4 转化之比 1500", "", lambda m: capr(m, 1500))
    put("E5 转化之比 1500÷630", "<1 = 630 到 1500 拍编队的转化优势在缩小", lambda m: capr(m, 1500) / capr(m, 630))
    put("E6 份额÷人头", "编队名下占全图 ÷ 人头占比", lambda m: vor(m)["shareOverHead"])
    put("E7 每号名下中位 ÷ 其他真人名下中位", "", lambda m: vor(m)["squadMedian"] / vor(m)["othersMedian"])
    put("E8 B集归编队", "% 600 拍接壤编队的 AI 的地到 1800 拍归编队", lambda m: fate(m, "B"))
    put("E9 A集归编队", "% 编队名下范围里的 AI 地到 1800 拍归编队", lambda m: fate(m, "A"))
    put("E10 冻结占比 600~1500", "% pickTarget 决策拍", lambda m: fz(m, "frozen"))
    put("E11 冻结里卡在编队友", "% 冻结拍", fz_by_squad)
    put("E12 没AI邻居占比 600~1500", "% 决策拍", lambda m: fz(m, "noai"))
    put("E13 有目标占比 600~1500", "% 决策拍", lambda m: fz(m, "target"))
    put("F1 利息效率 1500~4284 编队", "% 实得 ÷ 满额", lambda m: 100.0 * eff(m, "sq")[3] / max(1, eff(m, "sq")[4]))
    put("F2 利息效率 1500~4284 对手", "%", lambda m: 100.0 * eff(m, "op")[3] / max(1, eff(m, "op")[4]))
    put("F3 超软占比 1500~4284 编队", "% 席位·拍", lambda m: 100.0 * eff(m, "sq")[1] / max(1, eff(m, "sq")[0]))
    put("F4 超软占比 1500~4284 对手", "%", lambda m: 100.0 * eff(m, "op")[1] / max(1, eff(m, "op")[0]))
    put("G1 调度/捐款 成交÷日志", "%", lambda m: da(m, "exec"))
    put("G2 调度/捐款 额度拒÷日志", "%", lambda m: da(m, "quota"))
    put("H1 被围占比 1500起", "% buyLand 决策拍", lambda m: core(m, "noOffer"))
    put("H2 报价高占比 1500起", "%", lambda m: core(m, "pricedHigh"))
    put("H3 卡编队友底占比 1500起", "%", lambda m: core(m, "frozenSF"))
    put("H4 卡真人留底占比 1500起", "%", lambda m: core(m, "frozenKeep"))
    put("H5 发令占比 1500起", "%", lambda m: core(m, "sent"))
    put("I1 低于worth÷(低于+高于) 1500~2399", "%", bw_low)
    put("I2 低于worth里不给脉冲档 1500~2399", "%", bw_nopulse)

    def fv(v, nd):
        return "—" if v is None else f"{v:.{nd}f}"

    def stat(name, nd=2):
        note, vals = S[name]
        ls = sorted((v, m) for m, v in vals.items() if m != WIN and v is not None)
        if not ls:
            return f"{name}（{note}） | 无"
        k_ = len(ls)
        med = ls[k_ // 2][0] if k_ % 2 else (ls[k_ // 2 - 1][0] + ls[k_ // 2][0]) / 2.0
        return (f"{name}（{note}） | " + " ".join(fv(vals[m], nd) for m in MIDS)
                + f" | 输局 {k_} 局：最小 {fv(ls[0][0], nd)}（{ls[0][1]}） 中位 {fv(med, nd)} 最大 {fv(ls[-1][0], nd)}（{ls[-1][1]}） | 胜局 {fv(vals[WIN], nd)}")

    def count(name, label, pred):
        vals = S[name][1]
        ls = [(m, v) for m, v in vals.items() if m != WIN and v is not None]
        hit = [m for m, v in ls if pred(v)]
        w = vals[WIN]
        miss = [m for m, v in ls if not pred(v)]
        return (f"  计数 | {name} {label}：输局 {len(hit)}/{len(ls)}" + (f"（不满足的：{' '.join(miss)}）" if miss and len(miss) <= 4 else "")
                + f"；胜局 {'—' if w is None else ('是' if pred(w) else '否')}")

    def versus(a, b, label=">"):
        va, vb = S[a][1], S[b][1]
        ls = [m for m in MIDS if m != WIN and va[m] is not None and vb[m] is not None]
        hit = [m for m in ls if (va[m] > vb[m] if label == ">" else va[m] < vb[m])]
        miss = [m for m in ls if m not in hit]
        w = None if va[WIN] is None or vb[WIN] is None else (va[WIN] > vb[WIN] if label == ">" else va[WIN] < vb[WIN])
        return (f"  对比 | 「{a}」{label}「{b}」：输局 {len(hit)}/{len(ls)}" + (f"（不满足的：{' '.join(miss)}）" if miss and len(miss) <= 4 else "")
                + f"；胜局 {'—' if w is None else ('是' if w else '否')}")

    L_ = ["# X12 跨局小结（crosstab.py；把 X1~X8 里要跨局引用的量各取一列，统一给出 10 个输局的最小/中位/最大、胜局 A025 的值、以及「几局里有几局」的计数）",
          "# 各局取值的顺序：" + " ".join(MIDS) + "；— = 该局没有这个量（没有队伍、没有捐款、已经没有在场的号等）",
          "# 口径与 X1~X8 各表相同；「其他真人」= 全部不是编队号的真人席位，「对手」= 敌方真人（自由混战局 A046 = 其他真人）",
          "",
          "[A] 断面状态"]
    for nm in ("A1 人均地比 630", "A2 人均地比 1500", "A3 人均地比 4284", "A4 人均兵比 630", "A5 人均兵比 1500", "A6 人均兵比 4284", "A7 密度比 1500"):
        L_.append(stat(nm))
    L_.append(stat("A8 在场号数 4284", 0))
    L_ += [count("A1 人均地比 630", "≥0.95", lambda v: v >= 0.95), count("A2 人均地比 1500", "<0.80", lambda v: v < 0.80), count("A3 人均地比 4284", "<0.80", lambda v: v < 0.80),
           count("A5 人均兵比 1500", ">1", lambda v: v > 1), count("A6 人均兵比 4284", "<1", lambda v: v < 1), count("A7 密度比 1500", ">1", lambda v: v > 1)]
    L_ += ["", "[B] 窗口流量"]
    for nm in ("B1 人均利息比 0~630", "B2 人均利息比 630~1500", "B3 人均利息比 1500~4284", "B4 人均利息比 4284~结束", "B5 人均烧AI+中立比 0~630", "B6 人均烧AI+中立比 630~1500",
               "B7 人均得AI+中立地比 0~630", "B8 人均得AI+中立地比 630~1500", "B9 人均得AI+中立地比 1500~4284"):
        L_.append(stat(nm))
    for nm in ("B10 对真人净得地 630~1500", "B11 对真人净得地 1500~4284", "B12 对真人净得地 4284~结束"):
        L_.append(stat(nm, 0))
    for nm in ("B13 三项费占利息 1500~4284 编队", "B14 三项费占利息 1500~4284 其他真人"):
        L_.append(stat(nm, 1))
    L_ += [count("B2 人均利息比 630~1500", "≥1", lambda v: v >= 1), count("B6 人均烧AI+中立比 630~1500", "<1", lambda v: v < 1), count("B8 人均得AI+中立地比 630~1500", "<1", lambda v: v < 1),
           count("B5 人均烧AI+中立比 0~630", "≥1", lambda v: v >= 1), count("B7 人均得AI+中立地比 0~630", "≥0.95", lambda v: v >= 0.95),
           count("B3 人均利息比 1500~4284", "<1", lambda v: v < 1), count("B4 人均利息比 4284~结束", "<1", lambda v: v < 1),
           count("B10 对真人净得地 630~1500", "<0", lambda v: v < 0), count("B11 对真人净得地 1500~4284", ">0", lambda v: v > 0), count("B12 对真人净得地 4284~结束", "<0", lambda v: v < 0),
           versus("B13 三项费占利息 1500~4284 编队", "B14 三项费占利息 1500~4284 其他真人")]
    L_ += ["", "[C] 整局总账（占利息 %）"]
    for i in range(1, 15):
        nm = next(k_ for k_ in S if k_.startswith(f"C{i} "))
        L_.append(stat(nm, 1))
    for i in range(15, 18):
        nm = next(k_ for k_ in S if k_.startswith(f"C{i} "))
        L_.append(stat(nm))
    for i in range(18, 21):
        nm = next(k_ for k_ in S if k_.startswith(f"C{i} "))
        L_.append(stat(nm, 1))
    L_ += [versus("C1 挨打掉兵占利息 编队", "C2 挨打掉兵占利息 对手"), versus("C3 攻击费占利息 编队", "C4 攻击费占利息 对手"), versus("C5 捐款税占利息 编队", "C6 捐款税占利息 对手"),
           versus("C7 船费占利息 编队", "C8 船费占利息 对手", "<"), versus("C9 末余额+在途占利息 编队", "C10 末余额+在途占利息 对手", "<"), versus("C11 打AI占利息 编队", "C12 打AI占利息 对手", "<"),
           versus("C13 打真人占利息 编队", "C14 打真人占利息 对手"),
           count("C15 人均利息 编队÷对手", "<1", lambda v: v < 1), count("C16 得真人地÷被真人吃 编队", "<1", lambda v: v < 1), count("C17 得真人地÷被真人吃 对手", ">1", lambda v: v > 1),
           versus("C19 别人吃编队地的单价", "C18 编队吃真人地的单价")]
    L_ += ["", "[D] 延迟"]
    for nm in ("D1 延迟P50 600~1500", "D2 延迟P90 600~1500"):
        L_.append(stat(nm, 0))
    for nm in ("D3 迟到占比 整局", "D4 目标已死占比 600~1500", "D5 陆攻+船 落地÷受理", "D6 陆攻+船 生效÷受理"):
        L_.append(stat(nm, 1))
    L_.append(stat("D7 同步串 多发÷首条"))
    L_.append(stat("D8 落后串数", 0))
    L_ += [count("D1 延迟P50 600~1500", ">30 拍", lambda v: v > 30), count("D1 延迟P50 600~1500", "≤14 拍", lambda v: v <= 14), count("D4 目标已死占比 600~1500", "≥10%", lambda v: v >= 10),
           count("D5 陆攻+船 落地÷受理", "<90%", lambda v: v < 90), count("D7 同步串 多发÷首条", ">1", lambda v: v > 1), count("D8 落后串数", "≥18", lambda v: v >= 18)]
    L_ += ["", "[E] 出生份额与转化"]
    for nm in ("E1 出生份额", "E2 转化 1500", "E3 转化之比 630", "E4 转化之比 1500", "E5 转化之比 1500÷630", "E6 份额÷人头", "E7 每号名下中位 ÷ 其他真人名下中位"):
        L_.append(stat(nm))
    for nm in ("E8 B集归编队", "E9 A集归编队", "E10 冻结占比 600~1500", "E11 冻结里卡在编队友", "E12 没AI邻居占比 600~1500", "E13 有目标占比 600~1500"):
        L_.append(stat(nm, 0))
    L_ += [count("E1 出生份额", "<1", lambda v: v < 1), count("E2 转化 1500", ">1", lambda v: v > 1), count("E3 转化之比 630", ">1", lambda v: v > 1), count("E5 转化之比 1500÷630", "<1", lambda v: v < 1),
           count("E6 份额÷人头", "<1", lambda v: v < 1), count("E7 每号名下中位 ÷ 其他真人名下中位", "<1", lambda v: v < 1), count("E8 B集归编队", "≥80%", lambda v: v >= 80),
           count("E10 冻结占比 600~1500", "≥14%", lambda v: v >= 14), count("E11 冻结里卡在编队友", "≥50%", lambda v: v >= 50), count("E12 没AI邻居占比 600~1500", "≥18%", lambda v: v >= 18)]
    L_ += ["", "[F] 利息效率 1500~4284"]
    for nm in ("F1 利息效率 1500~4284 编队", "F2 利息效率 1500~4284 对手", "F3 超软占比 1500~4284 编队", "F4 超软占比 1500~4284 对手"):
        L_.append(stat(nm, 0))
    L_ += [versus("F1 利息效率 1500~4284 编队", "F2 利息效率 1500~4284 对手"), versus("F3 超软占比 1500~4284 编队", "F4 超软占比 1500~4284 对手")]
    L_ += ["", "[G] 调度/捐款日志的去向"]
    for nm in ("G1 调度/捐款 成交÷日志", "G2 调度/捐款 额度拒÷日志"):
        L_.append(stat(nm, 0))
    L_ += [count("G1 调度/捐款 成交÷日志", "<50%", lambda v: v < 50), count("G2 调度/捐款 额度拒÷日志", "≥50%", lambda v: v >= 50)]
    L_ += ["", "[H] 1500 拍起 buyLand 决策拍"]
    for nm in ("H1 被围占比 1500起", "H2 报价高占比 1500起", "H3 卡编队友底占比 1500起", "H4 卡真人留底占比 1500起", "H5 发令占比 1500起"):
        L_.append(stat(nm, 0))
    L_ += [count("H1 被围占比 1500起", "≥40%", lambda v: v >= 40), count("H5 发令占比 1500起", "<10%", lambda v: v < 10)]
    L_ += ["", "[I] 报价对 worth（1500~2399 拍）"]
    for nm in ("I1 低于worth÷(低于+高于) 1500~2399", "I2 低于worth里不给脉冲档 1500~2399"):
        L_.append(stat(nm, 0))
    L_ += [count("I1 低于worth÷(低于+高于) 1500~2399", "≥30%", lambda v: v >= 30), count("I2 低于worth里不给脉冲档 1500~2399", "≥50%", lambda v: v >= 50)]
    write("X12-summary.txt", L_)


TABLES = {"X0": x0, "X1": x1, "X2": x2, "X3": x3, "X4": x4, "X5": x5, "X6": x6, "X7": x7, "X8": x8, "X9": x9, "X10": x10, "X11": x11, "X12": x12}


def main():
    want = [a.upper() for a in sys.argv[1:]] or list(TABLES)
    for name in want:
        TABLES[name]()


if __name__ == "__main__":
    main()
