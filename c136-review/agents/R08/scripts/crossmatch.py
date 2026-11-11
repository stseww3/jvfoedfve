#!/usr/bin/env python3
"""crossmatch.py — R08 复盘过的 16 局的跨局对照表（M7）。只汇总，不重算：每个数都来自各局已有的脚本产物。

    python3 crossmatch.py [--quiet]      → out/_cross/crossmatch.txt、crossmatch.json

输入（都在 agents/R08/ 下）：
  reviews/<局>.json                         复盘稿（对局卡、结局、归类、决策审计、转折窗口）
  out/<局>/facts.json                       日志事实表（facts.py）
  out/<局>/lagledger_sum.json               延迟硬账（lagledger.py）——只有主房间有录像的 10 局
  out/<局>/landcap_sum.json                 好地硬账（landcap.mjs + landcap.py）
  out/<局>/spawnlast.json、spawngeo_sum.json  出生点执行 / 几何（spawncheck.py、spawngeo.py）
  out/<局>/enclose_sum.json、econ_sum.json    被围 / 兵的总账（enclose.py、econ.py）
  out/<局>/lagload_sum.json                 时延和房间活动量（lagload.py）
  out/_cross/xscan.json、xbatch.json        发现集全量的模式计数 / 录像成批统计（xscan.py、xbatch.py）

节：
  [XM-A] 花名册：对局卡、结局、归类、真值覆盖
  [XM-B] 份额轨迹（日志口径）：编队占全图的份额、÷ 人头份额
  [XM-C] 延迟硬账①：各时段时延 P50 / P90 / 最大、≥35 拍占比、没生效占比
  [XM-C2] 延迟硬账②：指令漏斗、迟到落空、成批落地（编队 vs 同房其他真人）
  [XM-C4] 派出去的兵的去向（编队 vs 同房其他真人）
  [XM-C3] 时延和房间活动量的秩相关、时延波段
  [XM-D] 好地硬账①：自然地盘（Voronoi）、人均比、相对自然地盘的兑现
  [XM-D2] 好地硬账②：人机地的去向、三层归因（①站位 ②门槛 ③迟到）
  [XM-E] 出生点：最后一解的执行、同像素、贴边、最近邻
  [XM-F] 被围、兵的总账（录像段）
  [XM-G] 捐款（日志口径）
  [XM-H] 出局：阵亡 / 离开、出局时账上的兵、四分之一线、满仓速死
  [XM-I] 决策审计：模式 × 判定（16 份复盘稿）
  [XM-J] 归类和第一个转折窗口
"""
import json
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "out")
REV = os.path.join(ROOT, "reviews")
MINE = ["G02", "G05", "G08", "B043", "B033", "B034", "B031", "B049", "B006", "B030", "B019", "B009", "B015", "B029", "B035", "B027"]
# 包里带的录像不是主房间的两局（复盘稿里逐条核过）：没有主房间真值
OTHER_ROOM = {"B049": "录像是另一个房间的（2 个编队号）", "B009": "录像是另一个房间的（1 个编队号）"}
CHECK = [630, 1530, 3060, 4500]
# B030 是 6 个真人的自由混战小房间（3 个编队号吃下整张图，打了 37561 拍）：单列，不进『合计』，免得它一局盖过其他九局
OUTLIER = {"B030"}


def load(*p):
    path = os.path.join(*p)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def pc(a, b, d=0):
    return "–" if not b else f"{100 * a / b:.{d}f}%"


def plain(x):
    return "–" if x is None else str(int(round(x)))


def num(x, d=2):
    if x is None:
        return "–"
    if isinstance(x, (int, float)) and abs(x) > 1e6 and d <= 3:
        return "∞"       # 分母（其他真人）已经没有地 / 没有兵了
    return f"{x:.{d}f}" if isinstance(x, float) else str(x)


def main():
    quiet = "--quiet" in sys.argv
    xs = load(OUT, "_cross", "xscan.json") or {}
    xb = load(OUT, "_cross", "xbatch.json") or {}
    xrow = {r["matchId"]: r for r in xs.get("rows", [])}
    brow = {r["matchId"]: r for r in xb.get("rows", [])}
    R = {m: load(REV, f"{m}.json") for m in MINE}
    F = {m: load(OUT, m, "facts.json") for m in MINE}
    LAG = {m: load(OUT, m, "lagledger_sum.json") for m in MINE}
    LAND = {m: load(OUT, m, "landcap_sum.json") for m in MINE}
    truth = [m for m in MINE if LAG[m] and LAND[m]]
    core = [m for m in truth if m not in OUTLIER]
    J = dict(matches=MINE, truth=truth)
    out = []

    # ------------------------------------------------------------------ [XM-A]
    out.append(f"[XM-A] 花名册（{len(MINE)} 局；主房间有录像真值的 {len(truth)} 局：{'、'.join(truth)}）。局 | 编队档 | 模式 | 名义队数 / 实际队数 | 开局真人 | 编队号数 | 编队分在几个队 | "
               "均分胜率 | 对局卡结果 | 归类 | 日志末拍 | 编队峰值份额 | 真值到第几拍 | 阵亡 / 离开 / 号数 | 第一个阵亡")
    J["roster"] = {}
    for m in MINE:
        r, x = R[m], xrow.get(m, {})
        c, o = r["context"], r["outcome"]
        b = x.get("basics", {})
        tr = f"{LAG[m]['endTick']}" if m in truth else OTHER_ROOM.get(m, "无录像")
        J["roster"][m] = dict(cohort=c.get("cohort"), mode=c.get("mode"), nominalTeams=c.get("nominalTeams"), actualTeams=c.get("actualTeams"), seeded=c.get("seededPlayers"),
                              squadBots=c.get("squadBots"), squadTeams=len(c.get("teamSplitCounts") or {}), base=c.get("baseWinExpectation"), cardLabel=x.get("resultLabel"),
                              reviewLabel=o.get("resultLabel"), archetype=r.get("lossArchetype"), endTick=o.get("endTick"), peakShare=o.get("peakSquadLandShare"),
                              truthEnd=(LAG[m]["endTick"] if m in truth else None), died=b.get("died"), left=b.get("left"), bots=b.get("bots"), firstDeath=b.get("firstDeath"))
        out.append(f"    {m} | {c.get('cohort')} | {c.get('mode')} | {c.get('nominalTeams')} / {c.get('actualTeams')} | {c.get('seededPlayers')} | {c.get('squadBots')} | "
                   f"{len(c.get('teamSplitCounts') or {})} | {num(c.get('baseWinExpectation'))} | {x.get('resultLabel')}{'' if x.get('resultLabel') == o.get('resultLabel') else '（复盘：' + str(o.get('resultLabel')) + '）'} | "
                   f"{r.get('lossArchetype')} | {o.get('endTick')} | {pc(o.get('peakSquadLandShare') or 0, 1, 1)} | {tr} | {b.get('died')} / {b.get('left')} / {b.get('bots')} | {b.get('firstDeath')}")
    arch = Counter(R[m].get("lossArchetype") for m in MINE)
    out.append("    归类合计：" + "、".join(f"{k} {v}" for k, v in arch.most_common()))
    J["archetypes"] = dict(arch)

    # ------------------------------------------------------------------ [XM-B]
    out.append("[XM-B] 份额轨迹（日志口径：各号 HL-TICK 快照的领土合计 ÷ 全图陆地；括号里 = 份额 ÷ 人头份额，人头份额 = 编队号数 ÷ 开局真人数）。"
               "局 | 人头份额 | " + " | ".join(f"t={t}" for t in CHECK) + " | 峰值（拍）")
    J["share"] = {}
    for m in MINE:
        f, c = F[m], R[m]["context"]
        land = f["card"]["mapLand"]
        head = (c.get("squadBots") or len(f["bots"])) / max(1, c.get("seededPlayers") or 1)
        cells, row = [], {}
        by_t = defaultdict(int)
        for b in f["bots"].values():
            for s in b["ticks"]:
                by_t[s["t"]] += s["terr"]
        for t in CHECK:
            v = by_t.get(t)
            if v is None:
                cells.append("–")
                continue
            sh = v / land
            row[t] = dict(share=round(sh, 4), ratio=round(sh / head, 2))
            cells.append(f"{100 * sh:.1f}%（{sh / head:.2f}）")
        pk_t = max(by_t, key=lambda t: by_t[t]) if by_t else None
        row["peak"] = dict(t=pk_t, share=round(by_t[pk_t] / land, 4)) if pk_t is not None else None
        J["share"][m] = dict(head=round(head, 4), **{str(k): v for k, v in row.items()})
        out.append(f"    {m} | {100 * head:.1f}% | " + " | ".join(cells) + f" | {100 * by_t[pk_t] / land:.1f}%（{pk_t}）")

    # ------------------------------------------------------------------ [XM-C]
    PER = ["0~600", "600~1500", "1500~3000", "3000+"]
    out.append("[XM-C] 延迟硬账①（lagledger.py [GB]：时延 = 录像里的执行拍 − 影子做出同一决策的拍）。局 | 真值末拍 | "
               + " | ".join(f"{p}：P50 / P90 / 最大（≥35 拍占比，没生效占比）" for p in PER))
    J["lag"] = {}
    for m in truth:
        lag = {r["period"]: r for r in LAG[m].get("lag", [])}
        cells = []
        for p in PER:
            r = lag.get(p)
            if not r or not r.get("matched"):
                cells.append("–")
                continue
            cells.append(f"{r['p50']} / {r['p90']} / {r['max']}（{pc(r['ge35'], r['matched'])}，{pc(r['noEffect'], r['executed'])}）")
        J["lag"][m] = lag
        out.append(f"    {m} | {LAG[m]['endTick']} | " + " | ".join(cells))
    # 合计（按条数加权）
    tot = {p: Counter() for p in PER}
    for m in core:
        for r in LAG[m].get("lag", []):
            for k in ("executed", "matched", "ge35", "noEffect"):
                tot[r["period"]][k] += r.get(k) or 0
            tot[r["period"]]["matches"] += 1 if r.get("matched") else 0
            tot[r["period"]]["slow"] += 1 if (r.get("matched") and r["p50"] >= 35) else 0
    out.append("    合计（不含 B030，各局条数相加）| – | " + " | ".join(
        f"{tot[p]['matches']} 局 {tot[p]['matched']} 条：≥35 拍 {pc(tot[p]['ge35'], tot[p]['matched'])}，没生效 {pc(tot[p]['noEffect'], tot[p]['executed'])}，P50≥35 的 {tot[p]['slow']} 局" for p in PER))
    J["lagTotal"] = {p: dict(tot[p]) for p in PER}

    # ------------------------------------------------------------------ [XM-C2]
    out.append("[XM-C2] 延迟硬账②（lagledger.py [GD][GE][GG]）。局 | 时段 | 漏斗：影子想发 → 录像里落地 → 生效 | 迟到落空：陆攻落地 / 没生效 / 目标已经没了 / 其中改打了无主地：条数（派出的兵）/ "
               "其中作废、一兵不扣：条数（本意的兵）| 成批（一拍 ≥3 条）编队：批 / 批里的指令 / 一拍抽走 ≥50% 余额的批 / ≥90% | 其他真人：批 / 批里的指令 | 连发串里第 2 条起的指令 编队 / 其他真人")
    J["funnel"], J["late"], J["dup"] = {}, {}, {}
    ftot = {p: Counter() for p in PER}
    for m in truth:
        fun = {r["period"]: r for r in LAG[m].get("funnel", [])}
        late = {r["period"]: r for r in LAG[m].get("late", [])}
        dup = defaultdict(dict)
        for r in LAG[m].get("dup", []):
            dup[r["period"]][r["group"]] = r
        J["funnel"][m], J["late"][m], J["dup"][m] = fun, late, dup
        for p in PER:
            f, l = fun.get(p), late.get(p)
            ds, do = dup.get(p, {}).get("编队"), dup.get(p, {}).get("其他真人")
            if not f or not (f.get("shadow") or f.get("replay")):
                continue
            for k in ("shadow", "replay", "effective") if m in core else ():
                ftot[p][k] += f.get(k) or 0
            for k in ("attacks", "noEffect", "targetGone", "redirected", "redirectedTroops", "void", "voidTroops", "sentTroops") if m in core else ():
                ftot[p][k] += (l or {}).get(k) or 0
            for k in ("cmds", "batches", "batchCmds", "drain50", "drain90", "chainExtraCmds") if m in core else ():
                ftot[p]["s_" + k] += (ds or {}).get(k) or 0
                ftot[p]["o_" + k] += (do or {}).get(k) or 0
            out.append(f"    {m} | {p} | {f.get('shadow')} → {f.get('replay')} → {f.get('effective')} | "
                       + (f"{l['attacks']} / {l['noEffect']} / {l['targetGone']} / {l['redirected']}（{l['redirectedTroops']}）/ {l['void']}（{l['voidTroops']}）" if l else "–")
                       + " | " + (f"{ds['batches']} / {ds['batchCmds']} / {ds['drain50']} / {ds['drain90']}" if ds else "–")
                       + " | " + (f"{do['batches']} / {do['batchCmds']}" if do else "–")
                       + " | " + (f"{ds['chainExtraCmds']}（{pc(ds['chainExtraCmds'], ds['cmds'])}）" if ds else "–") + " / " + (f"{do['chainExtraCmds']}（{pc(do['chainExtraCmds'], do['cmds'])}）" if do else "–"))
    for p in PER:
        t = ftot[p]
        out.append(f"    合计（不含 B030）| {p} | {t['shadow']} → {t['replay']} → {t['effective']}（落地 ÷ 想发 {pc(t['replay'], t['shadow'])}，生效 ÷ 落地 {pc(t['effective'], t['replay'])}）| 陆攻 {t['attacks']}，没生效 {t['noEffect']}（{pc(t['noEffect'], t['attacks'])}），"
                   f"目标已经没了 {t['targetGone']}（{pc(t['targetGone'], t['attacks'])}），改打无主地 {t['redirected']} 条 {t['redirectedTroops']} 兵，作废 {t['void']} 条（本意 {t['voidTroops']} 兵；这一段实际派出 {t['sentTroops']} 兵）| "
                   f"{t['s_batches']} / {t['s_batchCmds']}（占编队指令 {pc(t['s_batchCmds'], t['s_cmds'])}）/ {t['s_drain50']} / {t['s_drain90']} | {t['o_batches']} / {t['o_batchCmds']}（占 {pc(t['o_batchCmds'], t['o_cmds'], 1)}）| "
                   f"{t['s_chainExtraCmds']}（{pc(t['s_chainExtraCmds'], t['s_cmds'])}）/ {t['o_chainExtraCmds']}（{pc(t['o_chainExtraCmds'], t['o_cmds'])}）")
    J["funnelTotal"] = {p: dict(ftot[p]) for p in PER}

    # ------------------------------------------------------------------ [XM-C4]
    out.append("[XM-C4] 派出去的兵的去向（lagledger.py [GF]，全房真值，九局相加，不含 B030）。时段 | 谁 | 对人机：烧掉的兵 / 拿到的格（兵/格）/ 目标出局时还压着没用上的兵（占 烧掉+没用上）| "
               "对无主地：烧掉 / 拿到的格 / 原数退回（占 烧掉+退回）| 陆攻派出的兵 | 回到余额的兵 ÷ 派出的兵")
    fate = {(p, g): Counter() for p in PER for g in ("编队", "其他真人")}
    for m in core:
        for r in LAG[m].get("fate", []):
            for k, v in r.items():
                if isinstance(v, (int, float)) and (r["period"], r["group"]) in fate:
                    fate[(r["period"], r["group"])][k] += v
    for p in PER:
        for g in ("编队", "其他真人"):
            t = fate[(p, g)]
            out.append(f"    {p} | {g} | {t['aiBurn']} / {t['aiTiles']}（{(t['aiBurn'] / t['aiTiles']) if t['aiTiles'] else 0:.1f}）/ {t['aiLeftover']}（{pc(t['aiLeftover'], t['aiBurn'] + t['aiLeftover'])}）| "
                       f"{t['neutBurn']} / {t['neutTiles']} / {t['neutReturned']}（{pc(t['neutReturned'], t['neutBurn'] + t['neutReturned'])}）| {t['sent']} | {pc(t['returnedAll'], t['sent'])}")
    J["fateTotal"] = {f"{p}|{g}": dict(v) for (p, g), v in fate.items()}

    # ------------------------------------------------------------------ [XM-C3]
    out.append("[XM-C3] 时延和房间活动量（lagload.py：每 180 拍一窗的秩相关；时延波段 = 窗内中位 ≥35 拍的连续段）。局 | 开局真人 | 换手格数 | 推进次数 | 交战对数 | 有地真人数 | 时延波段（起~止，峰值中位）")
    J["lagload"] = {}
    for m in truth:
        ll = load(OUT, m, "lagload_sum.json")
        if not ll:
            continue
        sp = ll.get("spearman") or {}
        wv = "；".join(f"{w['t0']}~{w['t1']}（{w.get('peakLag')}）" for w in ll.get("waves", [])) or "无"
        J["lagload"][m] = dict(spearman=sp, waves=ll.get("waves", []))
        out.append(f"    {m} | {R[m]['context'].get('seededPlayers')} | {num(sp.get('tiles'))} | {num(sp.get('expand'))} | {num(sp.get('pairs'))} | {num(sp.get('humans'))} | {wv}")

    # ------------------------------------------------------------------ [XM-D]
    out.append("[XM-D] 好地硬账①（landcap.py：自然地盘 = 出生后按最近出生点切的 Voronoi，E 口径；人均比 = 编队人均领土 ÷ 其他真人人均领土；兑现比 = 人均比 ÷ 自然地盘人均比）。"
               "局 | 人头份额 | 自然地盘份额 | 自然地盘人均比 | 编队号落在最小四分位的 | 人均比 @300 / @630 / @900 / @1260 / @1500 / @1800 | 兑现比 @630 / @1260 或末点")
    J["land"] = {}
    for m in truth:
        L = LAND[m]
        cap = L.get("capture") or {}
        cells = [num(float(cap[k]["perHeadRatio"])) if k in cap else "–" for k in ("300", "630", "900", "1260", "1500", "1800")]
        last = max((int(k) for k in cap), default=None)
        cr630 = cap.get("630", {}).get("captureRatio")
        crl = cap.get("1260", cap.get(str(last), {})).get("captureRatio") if cap else None
        J["land"][m] = dict(headShare=L.get("headShare"), vorEShare=L.get("vorEShare"), vorEPerHead=L.get("vorEPerHead"), lowQuartile=L.get("squadInLowestQuartile"),
                            squad=L.get("squad"), capture=cap)
        out.append(f"    {m} | {pc(L.get('headShare') or 0, 1, 1)} | {pc(L.get('vorEShare') or 0, 1, 1)} | {num(L.get('vorEPerHead'))} | {L.get('squadInLowestQuartile')}/{L.get('squad')} | "
                   + " / ".join(cells) + f" | {num(cr630)} / {num(crl)}")

    # ------------------------------------------------------------------ [XM-D2]
    out.append("[XM-D2] 好地硬账②（landcap.py [KD][KE][KF]：人机地 = 内置 AI 的地；『应得』= 按人头份额该分到的格数）。局 | t=600 贴着编队号的人机地：格 / 到 1500 被吃掉 / 编队吃到（%）| "
               "(600,1500] 属于过人机的地：格 / 编队吃到 / 按人头应得 / 差额 | 接壤口径：别人吃掉之前有编队号贴着的格 = ②门槛挡住 + ③迟到 + 其它（出手了被分走、过闸没发等）| "
               "①站位：按人头应得 − 落在编队号自然地盘里的人机地（正数 = 先天少）")
    J["aiLand"] = {}
    tot2 = Counter()
    for m in truth:
        L = LAND[m]
        af = L.get("aiFate") or {}
        adj = af.get("t=600 时和编队号接壤的 AI 的:1500") or {}
        ev = af.get("ever:全图:1500") or {}
        at, ac = L.get("attr") or {}, L.get("attrContact") or {}
        J["aiLand"][m] = dict(adjacent=adj, ever=ev, attr={k: at.get(k) for k in ("U", "par", "got", "lost", "geomDeficit", "gate", "late", "noContact")},
                              contact={k: ac.get(k) for k in ("short", "inReach", "gate", "late", "rest", "position")})
        for k, v in (("adjCells", adj.get("cells")), ("adjEaten", adj.get("eaten")), ("adjSquad", adj.get("squad")), ("evCells", ev.get("cells")), ("evSquad", ev.get("squad")),
                     ("evPar", ev.get("par")), ("gate", ac.get("gate")), ("late", ac.get("late")), ("inReach", ac.get("inReach")), ("rest", ac.get("rest")),
                     ("geom", at.get("geomDeficit"))) if m in core else ():
            tot2[k] += v or 0
        out.append(f"    {m} | {adj.get('cells')} / {adj.get('eaten')} / {adj.get('squad')}（{pc(adj.get('squad') or 0, adj.get('eaten') or 0)}）| "
                   f"{ev.get('cells')} / {ev.get('squad')} / {ev.get('par')} / {(ev.get('squad') or 0) - (ev.get('par') or 0)} | "
                   f"{ac.get('inReach')} = {ac.get('gate')} + {ac.get('late')} + {(ac.get('inReach') or 0) - (ac.get('gate') or 0) - (ac.get('late') or 0)} | {at.get('geomDeficit')}")
    out.append(f"    合计（不含 B030）| {tot2['adjCells']} / {tot2['adjEaten']} / {tot2['adjSquad']}（{pc(tot2['adjSquad'], tot2['adjEaten'])}）| {tot2['evCells']} / {tot2['evSquad']}（{pc(tot2['evSquad'], tot2['evCells'], 1)}）/ "
               f"{tot2['evPar']}（{pc(tot2['evPar'], tot2['evCells'], 1)}）/ {tot2['evSquad'] - tot2['evPar']} | "
               f"{tot2['inReach']} = {tot2['gate']}（{pc(tot2['gate'], tot2['inReach'])}）+ {tot2['late']}（{pc(tot2['late'], tot2['inReach'])}）+ {tot2['inReach'] - tot2['gate'] - tot2['late']}"
               f"（{pc(tot2['inReach'] - tot2['gate'] - tot2['late'], tot2['inReach'])}）| {tot2['geom']}")
    J["aiLandTotal"] = dict(tot2)

    # ------------------------------------------------------------------ [XM-E]
    out.append("[XM-E] 出生点（spawncheck.py / spawngeo.py）。局 | 最后一条指派被执行的号 / 号数 | 每号指派条数中位 | 引擎落点同像素（<40 像素）的号对 | 离地图边的中位 编队 / 其他真人 | "
               "贴边（≤120 像素）编队 / 其他真人 | 最近邻是编队友的号 | 最近编队友距离中位")
    J["spawn"] = {}
    for m in truth:
        sl = load(OUT, m, "spawnlast.json") or {}
        sg = load(OUT, m, "spawngeo_sum.json") or {}
        n = len(sl)
        ex = sum(1 for v in sl.values() if v.get("lastExecuted"))
        ns = sorted(v.get("n") or 0 for v in sl.values())
        med = ns[len(ns) // 2] if ns else None
        sp = (LAG[m].get("spawn") or {})
        sq, ot = sg.get("squad") or {}, sg.get("others") or {}
        J["spawn"][m] = dict(bots=n, lastExecuted=ex, assignMedian=med, samePixelPairs=sp.get("samePixelPairs"), near40Pairs=sp.get("near40Pairs"),
                             edgeSquad=sq.get("edgeMedian"), edgeOthers=ot.get("edgeMedian"), nearEdgeSquad=sq.get("nearEdge"), nearEdgeOthers=ot.get("nearEdge"),
                             nSquad=sq.get("n"), nOthers=ot.get("n"), nearestIsMate=sq.get("nearestIsMate"), nnMate=sq.get("nnMate"))
        out.append(f"    {m} | {ex}/{n} | {med} | {num(sp.get('near40Pairs'))} | {num(sq.get('edgeMedian'))} / {num(ot.get('edgeMedian'))} | "
                   f"{num(sq.get('nearEdge'))}/{num(sq.get('n'))} / {num(ot.get('nearEdge'))}/{num(ot.get('n'))} | {num(sq.get('nearestIsMate'))}/{num(sq.get('n'))} | "
                   f"{num(round(sq['nnMate'])) if sq.get('nnMate') is not None else '–'}")
    sv = [v for k, v in J["spawn"].items() if k in core]
    ex_all = sum(v["lastExecuted"] for v in sv)
    n_all = sum(v["bots"] for v in sv)
    out.append(f"    合计（不含 B030）| {ex_all}/{n_all}（{pc(ex_all, n_all)}）| – | – | – | "
               f"{sum(v['nearEdgeSquad'] or 0 for v in sv)}/{sum(v['nSquad'] or 0 for v in sv)}（{pc(sum(v['nearEdgeSquad'] or 0 for v in sv), sum(v['nSquad'] or 0 for v in sv))}）/ "
               f"{sum(v['nearEdgeOthers'] or 0 for v in sv)}/{sum(v['nOthers'] or 0 for v in sv)}（{pc(sum(v['nearEdgeOthers'] or 0 for v in sv), sum(v['nOthers'] or 0 for v in sv))}）| "
               f"{sum(v['nearestIsMate'] or 0 for v in sv)}/{sum(v['nSquad'] or 0 for v in sv)}（{pc(sum(v['nearestIsMate'] or 0 for v in sv), sum(v['nSquad'] or 0 for v in sv))}）| –")
    J["spawnTotal"] = dict(lastExecuted=ex_all, bots=n_all)

    # ------------------------------------------------------------------ [XM-F]
    out.append("[XM-F] 被围和兵的总账（只算录像段；enclose.py：A 类 = 陆上边界只有受保护的编队友 / 海；econ.py）。局 | 被围 A 的号·采样 ÷ 全部 | 曾被围 A 的号 | "
               "编队 产兵 / 派出 / 原数退回（占派出）| 其他真人 原数退回占派出 | 编队 烧在进攻里 ÷ 产兵 | 其他真人 同 | 人均产兵比（编队 ÷ 其他真人，逐时段）")
    J["econ"] = {}
    for m in truth:
        en = load(OUT, m, "enclose_sum.json") or {}
        ec = load(OUT, m, "econ_sum.json") or {}
        t = en.get("total") or {}
        sq = (ec.get("total") or {}).get("编队") or {}
        ot = (ec.get("total") or {}).get("其他真人") or {}
        ratios = " / ".join(f"{num(float(p.get('incPerCapRatio')))}@{p.get('t0')}~{p.get('t1')}" for p in ec.get("periods", []) if p.get("incPerCapRatio") is not None)
        J["econ"][m] = dict(enclose=t, squad={k: sq.get(k) for k in ("inc", "ret", "atkTroops", "burnt", "boatFee", "donTax", "tilesGot", "tilesLost", "hitBal")},
                            others={k: ot.get(k) for k in ("inc", "ret", "atkTroops", "burnt", "boatFee", "donTax", "tilesGot", "tilesLost", "hitBal")},
                            incPerCap=[(p.get("t0"), p.get("t1"), p.get("incPerCapRatio")) for p in ec.get("periods", [])])
        out.append(f"    {m} | {t.get('sealedA')}/{t.get('samples')}（{pc(t.get('sealedA') or 0, t.get('samples') or 0)}）| {t.get('botsEverA')} | "
                   f"{sq.get('inc')} / {sq.get('atkTroops')} / {sq.get('ret')}（{pc(sq.get('ret') or 0, sq.get('atkTroops') or 0)}）| {pc(ot.get('ret') or 0, ot.get('atkTroops') or 0)} | "
                   f"{pc(sq.get('burnt') or 0, sq.get('inc') or 0)} | {pc(ot.get('burnt') or 0, ot.get('inc') or 0)} | {ratios or '–'}")

    # ------------------------------------------------------------------ [XM-G]
    out.append("[XM-G] 捐款（日志口径；复盘稿 ledger + xscan 的 NEW-DN-02 / DN-07 / DN-17 检出）。局 | 日志里的捐款行 | 看得到成交的 | 看得到被拒的 | 定不了的 | 到账上限 | 手续费上限 | "
               "小额捐款『税 − 到账』合计（DN-02）| 600 拍内互相倒手的次数（DN-07）| 顶硬上限回弹（DN-17）| 看得到成交的那些：到账 / 手续费（按发令时的余额估）| t<4284 的日志行 / 成交 / 被拒")
    J["donations"] = {}
    for m in MINE:
        lg = R[m].get("ledger") or {}
        p = (xrow.get(m) or {}).get("patterns") or {}
        J["donations"][m] = dict(logged=lg.get("donationsLogged"), accepted=lg.get("donationsObservedAccepted"), rejected=lg.get("donationsObservedRejected"),
                                 undetermined=lg.get("donationsUndetermined"), arrivedUpper=lg.get("donatedArrivedUpperBound"), taxUpper=lg.get("donationTaxUpperBound"),
                                 taxMinusGift=(p.get("NEW-DN-02") or {}).get("taxMinusGift"), pingpong=(p.get("NEW-DN-07") or {}).get("n"), bounce=(p.get("NEW-DN-17") or {}).get("n"))
        d = J["donations"][m]
        dr = ((xrow.get(m) or {}).get("basics") or {}).get("donRows") or []
        acc = [x for x in dr if x[2] == "ACC"]
        d["accArrived"], d["accFee"] = sum(x[4] for x in acc), sum(x[3] for x in acc)
        d["before4284"] = [sum(1 for x in dr if x[0] < 4284), sum(1 for x in dr if x[0] < 4284 and x[2] == "ACC"), sum(1 for x in dr if x[0] < 4284 and x[2] == "REJ")]
        out.append(f"    {m} | {num(d['logged'])} | {num(d['accepted'])} | {num(d['rejected'])} | {num(d['undetermined'])} | {plain(d['arrivedUpper'])} | {plain(d['taxUpper'])} | "
                   f"{plain(d['taxMinusGift'])} | {num(d['pingpong'])} | {num(d['bounce'])} | {d['accArrived']} / {d['accFee']} | {d['before4284'][0]} / {d['before4284'][1]} / {d['before4284'][2]}")
    dd = list(J["donations"].values())
    tot = lambda k: sum(x.get(k) or 0 for x in dd)
    b4 = [sum(x["before4284"][i] for x in dd) for i in range(3)]
    J["donationTotals"] = dict(logged=tot("logged"), accepted=tot("accepted"), rejected=tot("rejected"), undetermined=tot("undetermined"), taxMinusGift=tot("taxMinusGift"),
                               pingpong=tot("pingpong"), bounce=tot("bounce"), accArrived=tot("accArrived"), accFee=tot("accFee"), before4284=b4)
    J["donationTotals"].update(arrivedUpper=tot("arrivedUpper"), taxUpper=tot("taxUpper"))
    out.append(f"    合计 | {tot('logged')} | {tot('accepted')} | {tot('rejected')} | {tot('undetermined')} | {plain(tot('arrivedUpper'))} | {plain(tot('taxUpper'))} | {tot('taxMinusGift')} | {tot('pingpong')} | {tot('bounce')} | "
               f"{tot('accArrived')} / {tot('accFee')}（手续费 ÷ 到账 {pc(tot('accFee'), tot('accArrived'))}）| {b4[0]} / {b4[1]} / {b4[2]}")

    # ------------------------------------------------------------------ [XM-H]
    out.append("[XM-H] 出局（日志口径；xscan.py 的基础量 + NEW-DF-08 / DF-07 / DF-01 检出）。局 | 阵亡 / 离开（离开时还有 ≥100 格的）/ 号数 | 阵亡号结果行里的余额合计 | 其中 ≥10 万的号 | "
               "四分之一线出局且余额 ≥10 万：号数 / 余额（DF-08）| 满仓速死 严口径：号数 / 余额（DF-07）| 挨打不还手的失地段 / 失掉的格（DF-01）")
    J["deaths"] = {}
    th = Counter()
    for m in MINE:
        x = xrow.get(m) or {}
        b, p = x.get("basics") or {}, x.get("patterns") or {}
        d8, d7, d1 = p.get("NEW-DF-08") or {}, p.get("NEW-DF-07") or {}, p.get("NEW-DF-01") or {}
        J["deaths"][m] = dict(died=b.get("died"), left=b.get("left"), leftWithLand=b.get("leftWithLand"), bots=b.get("bots"), bank=b.get("bank"), bankBig=b.get("bankBig"),
                              quarterN=d8.get("n"), quarterBal=d8.get("balance"), fullN=d7.get("n"), fullBal=d7.get("bal"), passiveN=d1.get("n"), passiveCells=d1.get("cellsLost"))
        for k, v in J["deaths"][m].items():
            th[k] += v or 0
        out.append(f"    {m} | {b.get('died')} / {b.get('left')}（{b.get('leftWithLand')}）/ {b.get('bots')} | {b.get('bank')} | {b.get('bankBig')} | {d8.get('n', 0)} / {d8.get('balance', 0)} | "
                   f"{d7.get('n', 0)} / {d7.get('bal', 0)} | {d1.get('n', 0)} / {d1.get('cellsLost', 0)}")
    out.append(f"    合计 | {th['died']} / {th['left']}（{th['leftWithLand']}）/ {th['bots']} | {th['bank']} | {th['bankBig']} | {th['quarterN']} / {th['quarterBal']} | {th['fullN']} / {th['fullBal']} | "
               f"{th['passiveN']} / {th['passiveCells']}")
    J["deathsTotal"] = dict(th)

    # ------------------------------------------------------------------ [XM-I]
    by_pat = defaultdict(lambda: dict(matches=set(), n=0, verdicts=Counter()))
    per_match = {}
    for m in MINE:
        vc = Counter()
        for d in R[m].get("decisions", []):
            pid = d.get("patternId") or "（无）"
            for one in [x.strip() for x in str(pid).replace("、", ",").replace("/", ",").split(",") if x.strip()]:
                e = by_pat[one]
                e["matches"].add(m)
                e["n"] += 1
                e["verdicts"][d.get("verdict")] += 1
            vc[d.get("verdict")] += 1
        per_match[m] = vc
    out.append("[XM-I] 决策审计（16 份复盘稿的 decisions）：逐局判定数。局 | 决策条数 | error | good | unclear | 其它")
    for m in MINE:
        vc = per_match[m]
        oth = sum(v for k, v in vc.items() if k not in ("error", "good", "unclear"))
        out.append(f"    {m} | {sum(vc.values())} | {vc.get('error', 0)} | {vc.get('good', 0)} | {vc.get('unclear', 0)} | {oth}")
    allv = Counter()
    for vc in per_match.values():
        allv.update(vc)
    out.append(f"    合计 | {sum(allv.values())} | {allv.get('error', 0)} | {allv.get('good', 0)} | {allv.get('unclear', 0)} | {sum(v for k, v in allv.items() if k not in ('error', 'good', 'unclear'))}")
    out.append("    模式 × 判定（按出现的局数排；只列 ≥2 局的）：模式 | 局数 | 决策条数 | error / good / unclear | 哪几局")
    rows_i = sorted(by_pat.items(), key=lambda kv: (-len(kv[1]["matches"]), -kv[1]["n"], kv[0]))
    J["decisionPatterns"] = {k: dict(matches=sorted(v["matches"], key=MINE.index), n=v["n"], verdicts=dict(v["verdicts"])) for k, v in rows_i}
    for k, v in rows_i:
        if len(v["matches"]) < 2:
            continue
        out.append(f"      {k} | {len(v['matches'])} | {v['n']} | {v['verdicts'].get('error', 0)} / {v['verdicts'].get('good', 0)} / {v['verdicts'].get('unclear', 0)} | "
                   + "、".join(sorted(v["matches"], key=MINE.index)))
    once = [k for k, v in rows_i if len(v["matches"]) == 1]
    out.append(f"    只在 1 局出现的模式 {len(once)} 个：" + "、".join(once))
    # 前缀
    by_pre = defaultdict(lambda: dict(matches=set(), n=0, verdicts=Counter()))
    for k, v in by_pat.items():
        parts = k.split("-")
        pre = parts[1] if len(parts) >= 3 and parts[0] == "NEW" else (parts[0] if len(parts) >= 2 else k)
        e = by_pre[pre]
        e["matches"] |= v["matches"]
        e["n"] += v["n"]
        e["verdicts"].update(v["verdicts"])
    out.append("    按模式前缀：前缀 | 局数 | 决策条数 | error / good / unclear")
    for k, v in sorted(by_pre.items(), key=lambda kv: -kv[1]["n"]):
        out.append(f"      {k} | {len(v['matches'])} | {v['n']} | {v['verdicts'].get('error', 0)} / {v['verdicts'].get('good', 0)} / {v['verdicts'].get('unclear', 0)}")
    J["decisionPrefixes"] = {k: dict(matches=len(v["matches"]), n=v["n"], verdicts=dict(v["verdicts"])) for k, v in by_pre.items()}

    # ------------------------------------------------------------------ [XM-J]
    out.append("[XM-J] 归类和转折窗口（复盘稿 turningPoints）。局 | 归类 | 转折窗口数 | 第一个：t0~t1 份额前 → 后（口径）| 跌得最多的一个：t0~t1 前 → 后")
    J["turning"] = {}
    for m in MINE:
        tps = R[m].get("turningPoints") or []

        def fmt(tp):
            return f"{tp.get('t0')}~{tp.get('t1')} {tp.get('shareBefore')} → {tp.get('shareAfter')}（{tp.get('shareUnit') or '份额'}）"
        worst = None
        for tp in tps:
            try:
                d = float(tp.get("shareAfter")) - float(tp.get("shareBefore"))
            except (TypeError, ValueError):
                continue
            if worst is None or d < worst[0]:
                worst = (d, tp)
        J["turning"][m] = dict(n=len(tps), first=({k: tps[0].get(k) for k in ("t0", "t1", "shareBefore", "shareAfter", "shareUnit")} if tps else None),
                               worst=({k: worst[1].get(k) for k in ("t0", "t1", "shareBefore", "shareAfter", "shareUnit")} if worst else None))
        out.append(f"    {m} | {R[m].get('lossArchetype')} | {len(tps)} | {fmt(tps[0]) if tps else '–'} | {fmt(worst[1]) if worst else '–'}")

    od = os.path.join(OUT, "_cross")
    os.makedirs(od, exist_ok=True)
    open(os.path.join(od, "crossmatch.txt"), "w", encoding="utf-8").write("\n".join(out) + "\n")
    json.dump(J, open(os.path.join(od, "crossmatch.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=lambda o: sorted(o) if isinstance(o, set) else str(o))
    if quiet:
        print(f"crossmatch: {len(out)} 行")
    else:
        print("\n".join(out))


if __name__ == "__main__":
    main()
