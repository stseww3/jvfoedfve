#!/usr/bin/env python3
"""ledger-brief.py — 把一局的延迟账（delay-ledger.py）、抢地账（land-ledger.mjs）和开局冻结账（freeze-scan.mjs）
压成十来行的摘要，供叙述版引用；同时给 mkreview.py 提供 latencyAndLand 字段。只做读取和四则运算，不含判断。

    python3 scripts/ledger-brief.py <mid> [<mid> ...] [--quiet]
    写 out/dossier/<mid>-ledger-brief.txt

三层对账的恒等式（[B9]）：
    编队人均地 ÷ 其他真人人均地 = (编队人均名下格数 ÷ 其他真人人均名下格数) × (编队 地÷名下 ÷ 其他真人 地÷名下)
    左边是结果，右边第一项只由出生点决定（第①层），第二项是「同样的出生份额下谁转化得多」（第②③层和其余一切都在里面）。
    第②层另给被 safeFinite 冻结的决策拍数，第③层另给目标已死改打无主地/作废/退回余额的兵数——单位不同，不强行折成格数。
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def _load(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _wan(x):
    if x is None:
        return "—"
    if abs(x) >= 1e8:
        return f"{x / 1e8:.2f} 亿"
    if abs(x) >= 1e5:
        return f"{x / 1e4:.1f} 万"
    if abs(x) >= 1e4:
        return f"{x / 1e4:.2f} 万"
    return f"{x:,.0f}"


def _pct(a, b, nd=1):
    return f"{100 * a / b:.{nd}f}%" if b else "—"


def _names(x):
    return "、".join(x) if isinstance(x, (list, tuple)) else str(x)


def brief(mid):
    d = _load(os.path.join(ROOT, "out", "dossier", f"{mid}-delay-facts.json"))
    g = _load(os.path.join(ROOT, "out", "dossier", f"{mid}-land-facts.json"))
    fz = _load(os.path.join(ROOT, "out", "cache", f"{mid}-freeze.json"))
    out = []
    w = out.append
    doc = {"matchId": mid}
    w(f"# {mid} 延迟账与抢地账摘要（ledger-brief.py；数字取自 out/dossier/{mid}-delay-facts.json、{mid}-land-facts.json、out/cache/{mid}-freeze.json）")
    if d:
        sp = d["spawn"]
        bots = sp["bots"]
        off = [(b, v) for b, v in bots.items() if v.get("executed", 0) > 0 and v.get("distToFinal") is not None and v["distToFinal"] > 6]
        zero = [b for b, v in bots.items() if v.get("executed", 0) == 0]
        trail = [b for b, v in bots.items() if v.get("trailingUnexecuted", 0) > 0]
        off_txt = "；".join(
            f"{b} 差 {v['distToFinal']:.0f} 像素" + (f"（停在第 {v['staleRound']} 轮的坐标" + (f"，最后一轮把这个点给了 {_names(v['finalOwnerOfMySpot'])}" if v.get("finalOwnerOfMySpot") else "") + "）" if v.get("staleRound") is not None else "")
            + {"same-step-inversion": "，原因：终解那条和上一条在同一步落地、旧的后处理", "trailing-unexecuted": "，原因：终解那条没落地",
               "trailing-unexecuted+same-step-inversion": "，原因：终解那条没落地，且最后落地的两条在同一步、旧的后处理"}.get(v.get("reason"), "")
            for b, v in off)
        tail = ((f"；最后一步落地 ≥2 条、先发的旧坐标生效的 {len(sp.get('sameStepInversionBots') or [])} 个" + (f"（{'、'.join(sp['sameStepInversionBots'])}）" if sp.get("sameStepInversionBots") else ""))
                + f"；叠点 {len(sp['stackPairs'])} 对" + (f"（{'；'.join('+'.join(p) for p in sp['stackPairs'])}）" if sp["stackPairs"] else ""))
        if sp.get("comparable", True) and sp.get("rounds"):
            w(f"[B1] 选点落地：重解 {sp['rounds']} 轮（{sp['distinctSolutions']} 套不同的解），最小间距 {sp['minSepFirst']}→{sp['minSepLast']} 像素，boss={sp['boss']}；"
              f"{len(bots)} 个号里 {sp['onFinal']} 个落在最后一轮的坐标上，{sp['notOnFinal']} 个没落到" + (f"（{off_txt}）" if off_txt else "")
              + f"，{len(zero)} 个一条选点指令都没落地" + (f"（{'、'.join(zero)}）" if zero else "")
              + f"；{len(trail)} 个号最后的指派没落地" + (f"（{'、'.join(trail)}）" if trail else "") + tail)
        else:
            # 本包日志里没有这个房间的选点求解行（A071：日志从不在本房间的号进另一局那一行起切），只能报录像里落地的选点指令
            fr = sp.get("foreignRounds")
            ex = sorted(v.get("executed", 0) for v in bots.values())
            w("[B1] 选点落地：本包日志里没有本房间的选点求解行，无法和终解对账"
              + (f"（日志里的 {fr['rounds']} 轮求解是在 {fr['map'][0]}x{fr['map'][1]} 的地图上做的，本房间是 {fr['roomMap'][0]}x{fr['roomMap'][1]}，属于另一个房间）" if fr else "")
              + f"；录像里 {len(bots)} 个号各落地 {ex[0]}~{ex[-1]} 条选点指令，{len(zero)} 个一条都没落地" + (f"（{'、'.join(zero)}）" if zero else "") + tail)
        lg = d["lag"]
        w("[B2] 指令延迟（发令拍→服务器处理拍，按发令拍分段，n 条 P50/P90/最大）：" + "｜".join(
            f"{r['period']} {r['n']} 条 {r['p50']}/{r['p90']}/{r['max']}" + (f"（>30 拍 {r['gt30']} 条、>90 拍 {r['gt90']} 条）" if r["gt30"] else "") if r["n"] else f"{r['period']} 0 条"
            for r in lg["byPeriod"]) + f"｜全局 {lg['total']['n']} 条 {lg['total']['p50']}/{lg['total']['p90']}/{lg['total']['max']}，>30 拍 {lg['total']['gt30']} 条")
        rc = lg.get("relativeClock") or {}
        beh = [(b, v) for b, v in rc.items() if v.get("ge90")]
        dl = lg.get("localMinusServerAtDeath") or {}
        dv = [v for v in dl.values() if isinstance(v, (int, float))]
        w("     各号相对队友的时钟：" + ("没有一个号落后队友 ≥90 拍" if not beh else "；".join(f"{b} 最多落后 {v['max']} 拍（{v['at']} 拍前后），落后 ≥90 拍的日志行 {v['ge90']} 行" for b, v in beh))
          + (f"；出局时页面拍号 − 服务器拍号 {min(dv):+d}~{max(dv):+d}" if dv else ""))
        fn = d["funnel"]
        w("[B3] 漏斗（策略想发 → 页面受理 → 录像落地 → 生效）：全局 "
          + " → ".join(str(fn["total"][k]) for k in ("want", "acc", "land", "eff")) + "；"
          + "｜".join(f"{r['period']} " + "→".join(str(r[k]["total"]) for k in ("want", "acc", "land", "eff")) for r in fn["byPeriod"])
          + "；其中陆攻+船 " + "→".join(str(sum(r[k]["attack"] + r[k]["boat"] for r in fn["byPeriod"])) for k in ("want", "acc", "land", "eff"))
          + "，捐款 受理 " + str(sum(r["acc"]["donate"] for r in fn["byPeriod"])) + " → 落地 " + str(sum(r["land"]["donate"] for r in fn["byPeriod"])) + "（没落地的主要是撞额度）")
        lt = {r["period"]: r for r in d["late"]["byPeriod"]}
        seg = []
        for per in ("0~600", "600~1500", "1500~3000", "3000+"):
            r = lt.get(per)
            if not r or not r["attacks"]:
                continue
            tp = r["troopsAI"] + r["troopsHuman"]
            sent = r["neutralSentTroops"] + r.get("neutralBoatTroops", 0)
            seg.append(f"{per} 打 AI/真人 {r['toAI'] + r['toHuman']} 条 {_wan(tp)}兵，目标已死改打无主地 {r['deadTarget']} 条 {_wan(r['deadTargetTroops'])}兵（{_pct(r['deadTargetTroops'], tp)}），其中作废 {r['deadTargetNoop']} 条，延迟 >30 拍 {r['late30']} 条；"
                       f"打无主地发出 {_wan(sent)}" + (f"（含船 {_wan(r['neutralBoatTroops'])}）" if r.get("neutralBoatTroops") else "") + f"、烧掉 {_wan(r['neutralBurnt'])}（拿 {r['neutralTiles']} 格"
                       + (f"，至少 {_pct(sent - r['neutralBurnt'], sent, 0)} 回到余额）" if sent > r["neutralBurnt"] else "，烧掉的不少于发出的、算不出退回）"))
        w("[B4] 晚到与落空：" + "｜".join(seg))
        ri = d["reissue"]
        w("[B5] 落地前对同一目标重发：全局 " + f"{ri['total']['syncStrings']} 串 {ri['total']['syncCmds']} 条，首条 {_wan(ri['total']['syncFirst'])}、后续 {ri['total']['syncExtraCmds']} 条 {_wan(ri['total']['syncExtra'])}"
          + (f"（后续÷首条 {ri['total']['syncExtra'] / ri['total']['syncFirst']:.2f}）" if ri["total"]["syncFirst"] else "") + "；"
          + "｜".join(f"{r['period']} {r['syncStrings']} 串 {r['syncCmds']} 条 首 {_wan(r['syncFirst'])} 后 {_wan(r['syncExtra'])}" for r in ri["byPeriod"] if r["syncStrings"])
          + (f"；延迟 >45 拍后的补发串 {ri['total']['lagStrings']} 串（发 {ri['total']['lagIssued']} 落 {ri['total']['lagExecuted']}，花 {_wan(ri['total']['lagSpent'])}）" if ri["total"]["lagStrings"] else "；延迟 >45 拍后的补发串 0 串"))
        sb = d["sameTickBatches"]
        tb = sum(r["batches"] for r in sb["byPeriod"])
        w("     同一拍落地：两条的 " + str(sum(r["pairs"] for r in sb["byPeriod"])) + f" 次，≥3 条的批 {tb} 批"
          + (f"（最多 {max(r['maxN'] for r in sb['byPeriod'])} 条；一批花掉余额 ≥50% 的 {sum(r['drain50'] for r in sb['byPeriod'])} 批 {_wan(sum(r['drain50Spent'] for r in sb['byPeriod']))}兵，≥80% 的 {sum(r['drain80'] for r in sb['byPeriod'])} 批）" if tb else "")
          + ("；最重的：" + "、".join(f"{x['bot']} {x['t']} 拍 {x['n']} 条花掉余额 {100 * x['frac']:.0f}%（{_wan(x['spent'])}/{_wan(x['B0'])}）" for x in sb["worst"][:6]) if sb.get("worst") else ""))
        doc["delay"] = d
    else:
        w("[B1]~[B5] 没有延迟账（缺 delay-facts.json）")
    three = None
    if g:
        v = g["voronoi"]
        w(f"[B6] 出生份额：{v['humans']} 个真人、编队 {v['squadBots']} 个号；编队名下 {v['squadCells']:,} 格 = 全图 {v['squadCellsPct']}%，人头占 {v['headPct']}% → 份额÷人头 {v['shareOverHead']:.2f}；"
          f"每号名下中位 {v['squadMedian']:,.0f}（{v['squadMin']:,}~{v['squadMax']:,}）对其他真人中位 {v['othersMedian']:,.0f}；名下比编队中位还小的其他真人 {v['othersSmallerThanSquadMedian']}/{v['others']} 个")
        cap = {r["t"]: r for r in g.get("capture", [])}
        seg = []
        for t in sorted(cap):
            r = cap[t]
            seg.append(f"{t} 拍 编队 {r['squadRatio']:.2f}（{r['squadAlive']} 个号，单号地中位 {r['squadMedianTerr']:,.0f}）对其他真人 {r['othersRatio']:.2f}（中位 {r['othersMedianRatio']:.2f}，单人地中位 {r['othersMedianTerr']:,.0f}），人头口径 {r['vsFair']:.2f}")
        w("[B7] 实际领土 ÷ 出生份额：" + "｜".join(seg))
        reg = {r["t"]: r for r in g.get("region", [])}
        if reg:
            w("     我方名下范围归谁：" + "｜".join(
                f"{t} 拍 编队 {_pct(r['squad'], r['n'])}、同队路人 {_pct(r['mate'], r['n'])}、敌方真人 {_pct(r['enemy'], r['n'])}、AI {_pct(r['ai'], r['n'])}、无主 {_pct(r['neutral'], r['n'])}，编队范围外的地 {r['squadOutside']:,}"
                for t, r in sorted(reg.items()) if t in (630, 1500, 1800) or t == max(reg)))
        af = g.get("aiFate")
        if af:
            def last(rows):
                r = rows[-1]
                return f"{r['t']} 拍 编队 {_pct(r['squad'], r['n'])}、同队路人 {_pct(r['mate'], r['n'])}、敌方真人 {_pct(r['enemy'], r['n'])}、仍属 AI {_pct(r['ai'], r['n'])}"
            w(f"[B8] 身边 AI 的地去向（{af['freezeTick']} 拍定格）：与编队接壤的 {af['B']['ais']} 个 AI 共 {af['B']['cells']:,} 格 → {last(af['B']['rows'])}；"
              f"我方名下范围内的 AI 地 {af['A']['cells']:,} 格 → {last(af['A']['rows'])}；出生在我方名下范围内的 {af['C']['ais']} 个 AI 共 {af['C']['cells']:,} 格 → {last(af['C']['rows'])}")
            tk = af.get("takersB") or []
            if tk:
                w("     接壤 AI 的地被谁拿走（前 6）：" + "、".join(f"{'*' if x['squad'] else ''}{x['name']}" + (f"(队{x['team']})" if x.get("team") is not None else "") + f" {x['cells']:,}" for x in tk[:6]) + "（* = 编队的号）")
        else:
            w("[B8] 重放没到定格拍，身边 AI 的地去向空缺")
        # 三层对账
        r = cap.get(1500) or (cap[max(cap)] if cap else None)
        if r and r["squadAlive"] and r["humansAlive"] > r["squadAlive"]:
            on = r["humansAlive"] - r["squadAlive"]
            sq_land, ot_land = r["squadTerr"] / r["squadAlive"], r["othersTerr"] / on
            sq_cell, ot_cell = r["squadCells"] / r["squadAlive"], r["othersCells"] / on
            three = {
                "t": r["t"], "squadAlive": r["squadAlive"], "othersAlive": on,
                "landPerHeadSquad": round(sq_land), "landPerHeadOthers": round(ot_land), "landRatio": round(sq_land / ot_land, 3),
                "cellsPerHeadSquad": round(sq_cell), "cellsPerHeadOthers": round(ot_cell), "layer1SpawnFactor": round(sq_cell / ot_cell, 3),
                "convSquad": r["squadRatio"], "convOthers": r["othersRatio"], "layer23ConversionFactor": round(r["squadRatio"] / r["othersRatio"], 3) if r["othersRatio"] else None,
                "squadBotsAtStart": v["squadBots"], "squadTerrOverAllCells": round(r["squadTerr"] / max(1, v["squadCells"]), 3),
            }
            w(f"[B9] 600~1500 三层对账（{r['t']} 拍，在场的号）：人均地 编队 {sq_land:,.0f} 对其他真人 {ot_land:,.0f} = {sq_land / ot_land:.2f} 倍"
              f" = 出生份额（人均名下 {sq_cell:,.0f} 对 {ot_cell:,.0f} = {sq_cell / ot_cell:.2f} 倍）× 转化（地÷名下 {r['squadRatio']:.2f} 对 {r['othersRatio']:.2f} = {three['layer23ConversionFactor']:.2f} 倍）"
              + (f"；把已出局的号也算上，编队地 ÷ 全部 {v['squadBots']} 个号的名下 = {three['squadTerrOverAllCells']:.2f}" if r["squadAlive"] < v["squadBots"] else ""))
            if r.get("squadCtl") is None and r.get("perBot"):
                # 旧版 land-facts 没有「在控」字段：用卷宗里的离线拍补算
                df = _load(os.path.join(ROOT, "out", "dossier", f"{mid}-facts.json")) or {}
                left = {x["bot"]: x.get("leftServerTick") for x in df.get("deaths", []) if x.get("leftServerTick")}
                live = {b: e for b, e in r["perBot"].items() if e["terr"] > 0}
                hk = [b for b in live if left.get(b) is not None and left[b] <= r["t"]]
                ctl = {b: e for b, e in live.items() if b not in hk}
                r = dict(r, squadCtl=len(ctl), squadCtlTerr=sum(e["terr"] for e in ctl.values()), squadCtlCells=sum(e["cells"] for e in ctl.values()), husks=hk)
                r["squadCtlRatio"] = r["squadCtlTerr"] / max(1, r["squadCtlCells"])
            if r.get("squadCtl") is not None and r["squadCtl"] < r["squadAlive"]:
                three["squadCtl"] = {"bots": r["squadCtl"], "terr": r["squadCtlTerr"], "cells": r["squadCtlCells"], "ratio": r["squadCtlRatio"], "husks": r.get("husks")}
                w(f"     去掉已离线的空壳（{'、'.join(r.get('husks') or [])}）：在控 {r['squadCtl']} 个号 地 {r['squadCtlTerr']:,} ÷ 名下 {r['squadCtlCells']:,} = {r['squadCtlRatio']:.2f}"
                  f"（人均地 {r['squadCtlTerr'] / r['squadCtl']:,.0f}，人均名下 {r['squadCtlCells'] / r['squadCtl']:,.0f}）")
            conv_o = r["othersTerr"] / max(1, r["othersCells"])
            exp = r["squadCells"] * conv_o
            three["squadTerr"] = r["squadTerr"]
            three["expectedAtOthersConversion"] = round(exp)
            three["gapAtOthersConversion"] = round(exp - r["squadTerr"])
            w(f"     按其他真人的 地÷名下（{conv_o:.4f}）算，编队这些号该有 {exp:,.0f} 格，实际 {r['squadTerr']:,} 格，" + (f"少 {exp - r['squadTerr']:,.0f} 格" if exp >= r["squadTerr"] else f"多 {r['squadTerr'] - exp:,.0f} 格") + "（算术，不是反事实重放）")
        doc["land"] = g
    else:
        w("[B6]~[B8] 没有抢地账（缺 land-facts.json）")
    if fz:
        t = fz["team"]
        fb = t.get("frozenBy", {})
        w(f"     ② 留底冻结（{fz['from']}~{fz['to']} 拍买 AI 地的决策拍）：共 {t['ticks']} 拍 → 选到目标 {t['target']}、扩无主地 {t['neutral']}、没有 AI 邻居 {t['noai']}、被 safeFinite 冻结 {t['frozen']}（{_pct(t['frozen'], t['ticks'])}；"
          f"卡在编队友 {fb.get('squad', 0)}、同队路人 {fb.get('mate', 0)}、敌方真人 {fb.get('enemy', 0)}；去掉这一项当拍就能出手的 {t.get('frozenWould', 0)}）、其它 {t['other']}")
        if three is not None:
            three["layer2"] = {"window": [fz["from"], fz["to"]], "decisionTicks": t["ticks"], "target": t["target"], "neutral": t["neutral"], "noAi": t["noai"],
                               "frozenBySafeFinite": t["frozen"], "frozenBy": fb, "frozenWouldSend": t.get("frozenWould", 0), "other": t["other"]}
    if d and three is not None:
        r = {x["period"]: x for x in d["late"]["byPeriod"]}.get("600~1500")
        if r:
            tp = r["troopsAI"] + r["troopsHuman"]
            three["layer3"] = {"attacksAtAIorHuman": r["toAI"] + r["toHuman"], "troops": tp, "deadTargetCmds": r["deadTarget"], "deadTargetTroops": r["deadTargetTroops"],
                               "deadTargetTroopsPct": round(100 * r["deadTargetTroops"] / tp, 1) if tp else None, "void": r["deadTargetNoop"], "late30": r["late30"],
                               "neutralSent": r["neutralSentTroops"], "neutralBurnt": r["neutralBurnt"]}
            w(f"     ③ 晚到（600~1500 拍）：打 AI/真人 {_wan(tp)}兵里 {_wan(r['deadTargetTroops'])}（{_pct(r['deadTargetTroops'], tp)}）落地时目标已死、改打无主地；作废 {r['deadTargetNoop']} 条；延迟 >30 拍的 {r['late30']} 条")
    doc["threeLayer"] = three
    return "\n".join(out) + "\n", doc


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    quiet = "--quiet" in sys.argv
    for mid in args:
        txt, _ = brief(mid)
        p = os.path.join(ROOT, "out", "dossier", f"{mid}-ledger-brief.txt")
        txt = txt.encode("utf-16", "surrogatepass").decode("utf-16", "replace")
        with open(p, "w", encoding="utf-8") as f:
            f.write(txt)
        if quiet:
            print(f"{mid}: 已写 {p}")
        else:
            print(txt)


if __name__ == "__main__":
    main()
