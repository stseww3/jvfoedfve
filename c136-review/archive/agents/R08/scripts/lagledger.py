#!/usr/bin/env python3
"""lagledger.py — 「延迟 / 执行延迟」硬账：选点落地、指令时延分位、漏斗、迟到落空、派出去的兵的去向、重复下单与同拍成批。

    python3 lagledger.py <matchId> [--side peer] [--quiet]
需要 out/<局>/resim.json、shadow.json（--side peer 时用 shadow_peer.json）；有 atkfate.json 时出 [GF]。
输出 out/<局>/lagledger[_peer].txt 和 lagledger_sum[_peer].json（跨局汇总用）。

时段固定四段（按执行拍；漏斗里影子那一列按决策拍）：0~600、600~1500、1500~3000、3000+。
节：
  [GA] 选点执行：每个号在出生阶段真正落地了几条选点指令、最后一条落在出生阶段的第几步、日志里最后一条指派有没有落地、
       落点和最后一条指派差多远、同像素 / <40 像素的号对；其他真人落地条数作对照。
  [GB] 指令时延（执行拍 − 影子决策拍）：各时段 P50 / P90 / 最大、≥35 拍的占比、没生效的占比；按类型（陆攻 / 船 / 捐款）。
  [GC] 逐号：各时段时延中位（= 这个客户端比服务器落后多少拍）。
  [GD] 漏斗：影子过闸想发 → 真机本地受理（HL-TICK 的 cmds 计数）→ 录像落地 → 生效。
  [GE] 迟到落空 / 打错目标：陆攻落地时目标已经没了（录像里目标记成 512）——改打无主地的、作废的；目标还在但没生效的。
  [GF] 派出去的兵的去向（全房真值，编队对其他真人）：对内置 AI 的进攻烧掉多少、目标出局时还压着没用上的有多少；
       对无主地的进攻（含转过来的）烧掉多少、原数退回余额多少。
  [GG] 重复下单与同拍成批：同号同目标相邻 ≤14 拍的连发串；同一服务器拍落地 ≥3 条的批、抽走余额的比例；其他真人作对照。
口径见各节表头。影子 = 不落后的客户端在全场真值上逐拍跑同一份策略源码，只记不发。
"""
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from truth import Truth  # noqa: E402
import shadowcmp as SC  # noqa: E402
import r08lib as L  # noqa: E402

OUT = os.path.join(HERE, "..", "out")
NEUTRAL = 512
PER = [(0, 600, "0~600"), (600, 1500, "600~1500"), (1500, 3000, "1500~3000"), (3000, 10 ** 9, "3000+")]


def per_of(t):
    for i, (a, b, _) in enumerate(PER):
        if a <= t < b:
            return i
    return len(PER) - 1


def q(v, f):
    v = sorted(v)
    return v[min(len(v) - 1, int(len(v) * f))] if v else None


def pct(a, b):
    return f"{100.0 * a / b:.0f}%" if b else "–"


def fmt(x):
    return "–" if x is None else str(x)


def wan(x):
    return f"{x / 10000:.1f} 万" if abs(x) >= 100000 else str(int(x))


def main():
    args = sys.argv[1:]
    mid = args[0]
    side = "peer" if "--side" in args and args[args.index("--side") + 1] == "peer" else "own"
    suffix = "_peer" if side == "peer" else ""
    T = Truth(mid)
    R = T.R
    H = T.H
    S = json.load(open(os.path.join(OUT, mid, f"shadow{suffix}.json"), encoding="utf-8"))
    ids = {sb["id"]: name for name, sb in S["bots"].items()}
    sqid = set(ids)
    allsq = set(T.sqIds) | set(T.peerIds)
    lines = []
    w = lines.append
    SUM = {"matchId": mid, "side": side, "bots": len(sqid), "endTick": R["endTick"], "periods": [p[2] for p in PER]}
    end = R["endTick"]

    # ---------- [GA]
    seq = R.get("spawnSeq")
    turns = R.get("spawnTurns", 0)
    w(f"[GA] {mid} 选点执行（录像取自 {R.get('replayFrom', mid)}；出生阶段共 {turns} 步，一步约 7 拍；{'本编队' if side == 'own' else '同房另一支编队'} {len(sqid)} 个号）")
    if seq and side == "own":
        import spawncheck
        try:
            _, rows, pairs, same_last, (n_lines, n_backend, n_other) = spawncheck.analyse(mid)
        except Exception as e:  # noqa: BLE001
            rows, pairs, same_last, n_lines, n_backend = [], [], [], 0, 0
            w(f"  （日志指派读不出来：{e}）")
        byp = {r["p"]: r for r in rows}
        n_land = [len(seq[p]) for p in sqid]
        oth = [len(seq[p]) for p in range(H) if p not in allsq and R["spawnXY"][p]]
        last_step = [seq[p][-1][0] for p in sqid if seq[p]]
        late = sum(1 for s in last_step if s >= turns - 1)
        w(f"  日志里的出生指派 {n_lines} 行（后端协调器 {n_backend} 行）。每号指派 中位 {q([r['n'] for r in rows], 0.5)} 条、最多 {max([r['n'] for r in rows], default=0)} 条"
          f"｜录像里真正落地的选点指令：每号 中位 {q(n_land, 0.5)} 条、最多 {max(n_land, default=0)} 条、0 条的 {sum(1 for n in n_land if n == 0)} 个"
          f"（其他真人 中位 {fmt(q(oth, 0.5))} 条、最多 {max(oth, default=0)} 条）")
        n_last_ok = sum(1 for r in rows if r["lastExecuted"])
        n_notlog = sum(1 for r in rows if not r["inLog"])
        w(f"  日志里最后一条指派落地了的 {n_last_ok}/{len(rows)} 个；没落地、停在更早一版坐标上的 {len(rows) - n_last_ok - n_notlog} 个；落点不在日志指派里（0 条落地或被引擎另放）{n_notlog} 个"
          f"｜最后一条落地指令在出生阶段最后两步（第 {turns - 1}、{turns} 步）才到的 {late}/{len(last_step)} 个"
          f"｜同像素号对 {sum(1 for d, a, b in pairs if d == 0)}、<40 像素号对 {len(pairs)}、最后一条指派相同的号对 {len(same_last)}")
        w("  逐号：号 | 队 | 日志指派条数 | 落地条数 | 最后一条落地在第几步 | 引擎落点 | 落点是日志的第几条 | 日志最后一条 | 落点离日志最后一条（像素）| 最后两次落地之间跳了多远")
        hop_all = []
        for p in sorted(sqid):
            r = byp.get(p)
            sq_ = seq[p]
            hop = round(((sq_[-1][1] - sq_[-2][1]) ** 2 + (sq_[-1][2] - sq_[-2][2]) ** 2) ** 0.5) if len(sq_) >= 2 else 0
            hop_all.append(hop)
            if not r:
                continue
            dist = round(((r["engine"][0] - r["last"][0]) ** 2 + (r["engine"][1] - r["last"][1]) ** 2) ** 0.5) if r["engine"] and r["last"] else -1
            w(f"    {r['name']:<16} | T{r['team']} | {r['n']} | {len(sq_)} | {sq_[-1][0] if sq_ else '–'} | {r['engine']} | {r['hit'] or '不在日志里'} | {r['last']} | {dist} | {hop}")
        SUM["spawn"] = {"bots": len(rows), "logAssignMed": q([r["n"] for r in rows], 0.5), "logAssignMax": max([r["n"] for r in rows], default=0),
                        "landedMed": q(n_land, 0.5), "landedMax": max(n_land, default=0), "otherLandedMed": q(oth, 0.5),
                        "lastExecuted": n_last_ok, "stale": len(rows) - n_last_ok - n_notlog, "notInLog": n_notlog, "lastTwoSteps": late,
                        "samePixelPairs": sum(1 for d, a, b in pairs if d == 0), "near40Pairs": len(pairs), "sameLastPairs": len(same_last), "turns": turns,
                        "hopMed": q(hop_all, 0.5)}
    elif not seq:
        w("  （resim.json 里没有 spawnSeq：重跑 resim_r08.mjs）")

    # ---------- 配对
    pairs_all = []   # (name, real cmd, shadow cmd or None, lag)
    shadow_all = []  # (name, shadow cmd, matched?)
    for name, sb in S["bots"].items():
        real, sh, used, pairs = SC.match_bot(T, name, sb)
        for c, i, lag in pairs:
            pairs_all.append((name, c, sh[i] if i is not None else None, lag))
        for i, s in enumerate(sh):
            shadow_all.append((name, s, used[i]))

    # ---------- [GB]
    w("")
    w("[GB] 指令时延 = 录像里的执行拍 − 影子做出同一决策的拍（陆攻 / 船 / 捐款；配对规则同 shadowcmp.py，上限 1500 拍）")
    w("  时段（执行拍）| 已执行 | 配上影子 | P50 | P90 | 最大 | 时延 ≥35 拍的占比 | 没生效的占比 | 陆攻 P50/P90 | 船 P50/P90 | 捐款 P50/P90")
    SUM["lag"] = []
    for i, (a, b, lab) in enumerate(PER):
        if a >= end:
            continue
        rows = [x for x in pairs_all if a <= x[1][0] < b]
        lags = [x[3] for x in rows if x[3] is not None]
        bad = sum(1 for x in rows if x[1][5] == 0)
        kk = []
        for kind in (1, 3, 2):
            lk = [x[3] for x in rows if x[3] is not None and x[1][2] == kind]
            kk.append(f"{fmt(q(lk, 0.5))}/{fmt(q(lk, 0.9))}")
        w(f"  {lab} | {len(rows)} | {len(lags)} | {fmt(q(lags, 0.5))} | {fmt(q(lags, 0.9))} | {max(lags) if lags else '–'} | {pct(sum(1 for x in lags if x >= 35), len(lags))} | {pct(bad, len(rows))} | " + " | ".join(kk))
        SUM["lag"].append({"period": lab, "executed": len(rows), "matched": len(lags), "p50": q(lags, 0.5), "p90": q(lags, 0.9), "max": max(lags) if lags else None,
                           "ge35": sum(1 for x in lags if x >= 35), "noEffect": bad})

    # ---------- [GC]
    w("")
    w("[GC] 逐号时延中位（条数）：号 | " + " | ".join(p[2] for p in PER) + " | 全程最大@执行拍")
    for name in sorted(S["bots"], key=lambda n: S["bots"][n]["id"]):
        cells = []
        mx = (None, None)
        for a, b, lab in PER:
            lags = [x[3] for x in pairs_all if x[0] == name and a <= x[1][0] < b and x[3] is not None]
            cells.append(f"{fmt(q(lags, 0.5))}（{len(lags)}）")
        allx = [(x[3], x[1][0]) for x in pairs_all if x[0] == name and x[3] is not None]
        if allx:
            mx = max(allx)
        w(f"    {name:<16} | " + " | ".join(cells) + f" | {fmt(mx[0])}@{fmt(mx[1])}")
    slow = defaultdict(int)
    for i, (a, b, lab) in enumerate(PER):
        for name in S["bots"]:
            lags = [x[3] for x in pairs_all if x[0] == name and a <= x[1][0] < b and x[3] is not None]
            if len(lags) >= 3 and q(lags, 0.5) >= 35:
                slow[lab] += 1
    w("  时延中位 ≥35 拍（至少 3 条）的号数：" + "、".join(f"{lab} {slow[lab]}" for _, _, lab in PER))
    SUM["slowBots"] = dict(slow)

    # ---------- [GD]
    w("")
    w("[GD] 漏斗：影子过闸想发的（陆攻 / 船 / 捐款，本地校验通过）→ 其中在录像里配上的 → 真机本地受理（HL-TICK 的 cmds 计数增量，含协防戳刺）→ 录像落地 → 生效")
    w("  时段 | 影子想发 | 配上录像的（落地率）| 真机 cmds 增量 | 录像落地（陆攻/船/捐款）| 生效 | 录像落地 ÷ 影子想发")
    F = None
    fp = os.path.join(OUT, mid, "facts.json")
    if os.path.exists(fp) and side == "own":
        F = json.load(open(fp, encoding="utf-8"))
    SUM["funnel"] = []
    for a, b, lab in PER:
        if a >= end:
            continue
        sh = [x for x in shadow_all if a <= x[1][0] < b and x[1][4] == 1]
        mt = sum(1 for x in sh if x[2])
        real = [c for c in R["cmdLog"] if c[1] in sqid and c[2] in (1, 2, 3) and a <= c[0] < b]
        eff = sum(1 for c in real if c[5] == 1)
        cm = None
        if F:
            cm = 0
            for me, bot in F["bots"].items():
                if int(me) not in sqid:
                    continue
                tk = bot.get("ticks") or []
                ca = max([x["cmds"] for x in tk if x["t"] <= a], default=0)
                cb = max([x["cmds"] for x in tk if x["t"] <= min(b, 10 ** 8)], default=0)
                cm += max(0, cb - ca)
        w(f"  {lab} | {len(sh)} | {mt}（{pct(mt, len(sh))}）| {fmt(cm)} | {len(real)} | {eff} | {pct(len(real), len(sh))}")
        SUM["funnel"].append({"period": lab, "shadow": len(sh), "shadowMatched": mt, "clientCmds": cm, "replay": len(real), "effective": eff})
    if F:
        res = [(b.get("name"), b.get("sent"), b.get("accepted")) for b in F["bots"].values()]
    # ---------- [GE]
    w("")
    w("[GE] 迟到落空 / 打错目标（陆攻）。「目标已经没了」= 影子瞄的是内置 AI 或真人，录像里这条的目标记成 512（引擎在目标出局后把它改成无主地）")
    w("  时段 | 陆攻落地 | 没生效 | 目标已经没了：条数（原本瞄 AI / 真人）| 其中改打了无主地：条数、派出的兵 | 其中作废（身边没有无主地，一兵不扣）：条数、本意的兵 | 目标还在但没生效 | 没配上影子、目标 512、没生效")
    SUM["late"] = []
    for a, b, lab in PER:
        if a >= end:
            continue
        rows = [x for x in pairs_all if a <= x[1][0] < b and x[1][2] == 1]
        n = len(rows)
        noeff = sum(1 for x in rows if x[1][5] == 0)
        gone = [x for x in rows if x[2] is not None and min(x[1][4], NEUTRAL) == NEUTRAL and x[2][3] != NEUTRAL]
        g_ai = sum(1 for x in gone if x[2][3] >= H)
        red = [x for x in gone if x[1][5] == 1]
        void = [x for x in gone if x[1][5] == 0]
        void_troops = sum(L.attack_quote(x[1][8], x[1][3])[0] for x in void)
        alive_noeff = sum(1 for x in rows if x[2] is not None and x[1][5] == 0 and min(x[1][4], NEUTRAL) != NEUTRAL)
        un512 = sum(1 for x in rows if x[2] is None and x[1][5] == 0 and min(x[1][4], NEUTRAL) == NEUTRAL)
        sent = sum(x[1][6] for x in rows if x[1][5] == 1)
        w(f"  {lab} | {n} | {noeff}（{pct(noeff, n)}）| {len(gone)}（{g_ai} / {len(gone) - g_ai}）| {len(red)} 条 {sum(x[1][6] for x in red)} 兵 | {len(void)} 条 {void_troops} 兵 | {alive_noeff} | {un512}")
        SUM["late"].append({"period": lab, "attacks": n, "noEffect": noeff, "targetGone": len(gone), "goneAI": g_ai, "redirected": len(red), "redirectedTroops": sum(x[1][6] for x in red),
                            "void": len(void), "voidTroops": void_troops, "aliveNoEffect": alive_noeff, "unmatched512NoEffect": un512, "sentTroops": sent})
    # 时延 ≥35 拍的陆攻单列（600~1500）
    rows = [x for x in pairs_all if 600 <= x[1][0] < 1500 and x[1][2] == 1 and x[3] is not None]
    late = [x for x in rows if x[3] >= 35]
    ontime = [x for x in rows if x[3] < 35]
    def bad_share(v):
        return pct(sum(1 for x in v if x[1][5] == 0 or (min(x[1][4], NEUTRAL) == NEUTRAL and x[2][3] != NEUTRAL)), len(v))
    w(f"  600~1500 配上影子的陆攻 {len(rows)} 条：时延 <35 拍的 {len(ontime)} 条，其中落空或目标已没了的占 {bad_share(ontime)}；时延 ≥35 拍的 {len(late)} 条，占 {bad_share(late)}")

    # ---------- [GF]
    ap = os.path.join(OUT, mid, "atkfate.json")
    if os.path.exists(ap):
        A = json.load(open(ap, encoding="utf-8"))
        w("")
        w("[GF] 派出去的兵的去向（全房真值；一路进攻 = 同一进攻方对同一目标从第一次推进到结束 / 转向）")
        w("  时段 | 谁 | 对内置 AI：路数、烧掉的兵、拿到的格（兵/格）、目标出局时还压着没用上的兵（占 烧掉+没用上 的）| 对无主地（含目标出局后转过来的）：路数、烧掉的兵、拿到的格、原数退回余额的兵（占 烧掉+退回 的）| 这一段陆攻指令派出的兵 | 回到余额的兵 ÷ 派出的兵")
        SUM["fate"] = []
        groups = [("编队" if side == "own" else "另一支编队", lambda p: p in sqid), ("其他真人", lambda p: p not in allsq)]
        for a, b, lab in PER:
            if a >= end:
                continue
            for gname, gf in groups:
                E = [e for e in A["ends"] if a <= e[0] < b and gf(e[1])]
                ai = [e for e in E if H <= e[2] < NEUTRAL]
                ne = [e for e in E if e[2] == NEUTRAL]
                ai_burn = sum(e[8] for e in ai); ai_tiles = sum(e[7] for e in ai)
                ai_left = sum(e[3] for e in ai if e[9] == 1)
                ai_ret = sum(e[3] for e in ai if e[9] == 0)
                ne_burn = sum(e[8] for e in ne); ne_tiles = sum(e[7] for e in ne); ne_ret = sum(e[3] for e in ne if e[9] == 0)
                hu_ret = sum(e[3] for e in E if e[2] < H and e[9] == 0)
                sent = sum(c[6] for c in R["cmdLog"] if c[2] == 1 and c[5] == 1 and a <= c[0] < b and gf(c[1]) and c[1] < H)
                back = ai_ret + ne_ret + hu_ret
                w(f"  {lab} | {gname} | {len(ai)} 路、{wan(ai_burn)}、{ai_tiles} 格（{ai_burn / ai_tiles:.1f}）" if ai_tiles else f"  {lab} | {gname} | {len(ai)} 路、{wan(ai_burn)}、0 格")
                lines[-1] += (f"、没用上 {wan(ai_left)}（{pct(ai_left, ai_burn + ai_left)}）| {len(ne)} 路、{wan(ne_burn)}、{ne_tiles} 格、退回 {wan(ne_ret)}（{pct(ne_ret, ne_burn + ne_ret)}）"
                              f" | {wan(sent)} | {pct(back, sent)}")
                SUM["fate"].append({"period": lab, "group": gname, "aiEpisodes": len(ai), "aiBurn": ai_burn, "aiTiles": ai_tiles, "aiLeftover": ai_left,
                                    "neutEpisodes": len(ne), "neutBurn": ne_burn, "neutTiles": ne_tiles, "neutReturned": ne_ret, "sent": sent, "returnedAll": back})

    # ---------- [GG]
    w("")
    w("[GG] 重复下单与同拍成批（录像真值）。连发串 = 同号、同类、同目标的指令，相邻两条执行拍相差 ≤14 拍；批 = 同一个号在同一服务器拍落地 ≥3 条（陆攻 / 船 / 捐款）")
    w("  时段 | 谁 | 指令数 | 连发串：串数（2 条 / 3 条 / ≥4 条）、串里第 2 条起的指令数、它们派出的兵 | 批：批数、批里的指令数、抽走余额 ≥50% 的批数、≥90% 的批数、批里第 2 条起派出的兵")
    SUM["dup"] = []
    groups = [("编队" if side == "own" else "另一支编队", lambda p: p in sqid), ("其他真人", lambda p: p not in allsq)]
    for a, b, lab in PER:
        if a >= end:
            continue
        for gname, gf in groups:
            cm = [c for c in R["cmdLog"] if c[2] in (1, 2, 3) and a <= c[0] < b and c[1] < H and gf(c[1])]
            byk = defaultdict(list)
            for c in cm:
                tgt = min(c[4], NEUTRAL) if c[2] in (1, 2) else -1
                byk[(c[1], c[2], tgt)].append(c)
            chains = []
            for k, v in byk.items():
                v.sort(key=lambda c: c[0])
                cur = [v[0]]
                for c in v[1:]:
                    if c[0] - cur[-1][0] <= 14:
                        cur.append(c)
                    else:
                        if len(cur) >= 2:
                            chains.append(cur)
                        cur = [c]
                if len(cur) >= 2:
                    chains.append(cur)
            n2 = sum(1 for ch in chains if len(ch) == 2); n3 = sum(1 for ch in chains if len(ch) == 3); n4 = sum(1 for ch in chains if len(ch) >= 4)
            extra_n = sum(len(ch) - 1 for ch in chains)
            extra_troops = sum(c[6] for ch in chains for c in ch[1:] if c[5] == 1)
            byt = defaultdict(list)
            for c in cm:
                byt[(c[1], c[0])].append(c)
            batches = [v for v in byt.values() if len(v) >= 3]
            d50 = d90 = 0
            b_extra = 0
            for v in batches:
                b0 = v[0][8]
                spent = sum((c[6] + c[7]) if c[2] != 2 else (c[6] + c[7]) for c in v if c[5] == 1)
                if b0 > 0 and spent >= 0.5 * b0:
                    d50 += 1
                if b0 > 0 and spent >= 0.9 * b0:
                    d90 += 1
                b_extra += sum(c[6] for c in v[1:] if c[5] == 1)
            w(f"  {lab} | {gname} | {len(cm)} | {len(chains)}（{n2} / {n3} / {n4}）、{extra_n} 条、{wan(extra_troops)} | {len(batches)} 批、{sum(len(v) for v in batches)} 条、{d50}、{d90}、{wan(b_extra)}")
            SUM["dup"].append({"period": lab, "group": gname, "cmds": len(cm), "chains": len(chains), "chain2": n2, "chain3": n3, "chain4": n4, "chainExtraCmds": extra_n,
                               "chainExtraTroops": extra_troops, "batches": len(batches), "batchCmds": sum(len(v) for v in batches), "drain50": d50, "drain90": d90, "batchExtraTroops": b_extra})
    # 过期放大：时延 ≥35 拍、已生效的陆攻 / 船，本意兵力（决策拍余额 × 比例）对实发兵力
    w("  过期放大（时延 ≥35 拍、已生效的陆攻 / 船）：时段 | 条数 | 本意的兵（影子决策拍的余额 × 比例）| 实发的兵 | 实发 ÷ 本意")
    SUM["stale"] = []
    for a, b, lab in PER:
        if a >= end:
            continue
        rows = [x for x in pairs_all if a <= x[1][0] < b and x[1][2] in (1, 3) and x[3] is not None and x[3] >= 35 and x[1][5] == 1]
        intent = sum(L.attack_quote(x[2][6], x[2][2], 12 if x[1][2] == 1 else 32)[0] for x in rows)
        actual = sum(x[1][6] for x in rows)
        w(f"    {lab} | {len(rows)} | {wan(intent)} | {wan(actual)} | {actual / intent:.2f}" if intent else f"    {lab} | {len(rows)} | 0 | {wan(actual)} | –")
        SUM["stale"].append({"period": lab, "n": len(rows), "intent": intent, "actual": actual})

    text = "\n".join(lines) + "\n"
    with open(os.path.join(OUT, mid, f"lagledger{suffix}.txt"), "w", encoding="utf-8") as f:
        f.write(text)
    with open(os.path.join(OUT, mid, f"lagledger_sum{suffix}.json"), "w", encoding="utf-8") as f:
        json.dump(SUM, f, ensure_ascii=False)
    if "--quiet" in args:
        print(f"{mid}: lagledger{suffix}.txt {len(lines)} 行")
    else:
        print(text)


if __name__ == "__main__":
    main()
