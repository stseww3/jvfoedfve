#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""82_outlet_gap.py — R07：我方号全部没有前沿之后，兵去了哪、同队的前线是谁在打。

用法（在 scripts/ 目录下）：
    python3 82_outlet_gap.py <matchId> [--from T]

输入（都在 out/<matchId>/，由 60_truth.cjs / 67_troop_flow.mjs / 74_side_flow.mjs 生成）：
    truth_border.tsv   每 90 拍每个我方号的邻居（玩家号:接壤格数）、贴无主地格数
    truth_all.tsv      每 90 拍每个席位的领土 / 余额 / 是否在场 / state（2 = 离开、由内置 AI 接管）
    truth_players.tsv  席位名、队伍、是否真人席位、是否我方号
    humans_cmd.tsv     全场真人席位逐条生效的指令（进攻 / 发船 / 捐款：扣款、手续费、目标类型、到账）
    tick_net.tsv       我方号每 10 拍的利息地租（eco）
输出：out/<matchId>/outlet_gap.txt / .json
    A. 每个采样拍我方有几个号贴着敌队在位真人 / 内置 AI 或离开席位 / 无主地；最后一个还有前沿的采样拍
    B. 「全队没有敌队真人邻居」这一段里各组的账（发兵去向、发船、捐款）
    C. 同队其他真人在这一段：领土、余额、密度、离 150×领土硬上限的空间、打出去和挨的兵、收到的捐款
    D. 我方每个号在这一段：利息地租、捐出 / 收到、发船、余额
    E. 抽样对照：我方密度 / 同队其他真人密度 / 同队领土最大的三个人
    F. 全场本队内部的捐款按「捐方组 → 收方组」分；我方号最后一条打真人的进攻
    G. 窗口内 in_game.log 的调度日志：类别、boxedIn、捐方 / 收方密度的范围（读 /agent/repos/c136-data/bundles/<matchId>/in_game.log）
--from T：不用自动找到的起点，改用指定拍号（取不早于它的第一个采样拍）。
"""
import csv
import json
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = "/agent/repos/c136-data"


def fmt(x):
    return f"{int(round(x)):,}"


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(2)
    mid = args[0]
    out = os.path.join(HERE, "..", "out", mid)

    def rd(name):
        return list(csv.DictReader(open(os.path.join(out, name), encoding="utf-8"), delimiter="\t"))

    players = {int(r["p"]): r for r in rd("truth_players.tsv")}
    squad = {p for p, r in players.items() if r.get("squad") not in ("", None, "0")}
    if not squad:
        print("truth_players.tsv 里没有我方号")
        sys.exit(1)
    my_team = players[next(iter(squad))]["team"]
    human = {p for p, r in players.items() if r.get("human") == "1"}

    snap = defaultdict(dict)  # t -> p -> (terr, bal, alive, state)
    for r in rd("truth_all.tsv"):
        snap[int(r["t"])][int(r["p"])] = (int(r["terr"]), int(float(r["bal"])), int(r["alive"]), int(r["state"]))
    ticks = sorted(snap)
    end_t = ticks[-1]

    def at(p, t):
        return snap[t].get(p, (0, 0, 0, 0))

    # ---------- A. 前沿 ----------
    border = defaultdict(list)
    for r in rd("truth_border.tsv"):
        border[int(r["t"])].append(r)
    bt = sorted(border)
    front = []  # (t, 在场, 贴敌队在位真人, 贴 AI/离开席位, 贴无主地, 三样都没有)
    for t in bt:
        st = snap.get(t, {})
        n = e = a = nt = boxed = 0
        for r in border[t]:
            me = int(r["p"])
            if st and at(me, t)[2] == 0:
                continue
            n += 1
            he = ha = False
            for tok in (r["nbs"] or "").split():
                if ":" not in tok:
                    continue
                q = int(tok.split(":")[0])
                pl = players.get(q)
                if pl is None or q not in human:
                    # 实际队数 ≥8 的局内置 AI 也分队：和我方同队的 AI 打不了，不算出口
                    if not (pl is not None and pl["team"] not in ("", "0") and pl["team"] == my_team):
                        ha = True
                elif pl["team"] != my_team:
                    if st and at(q, t)[3] == 2:
                        ha = True
                    else:
                        he = True
            hn = int(r["neutralAdj"]) > 0
            e += he
            a += ha
            nt += hn
            boxed += (not he and not ha and not hn)
        front.append((t, n, e, a, nt, boxed))
    last_front = max([f[0] for f in front if f[2] > 0], default=None)
    auto_from = min([f[0] for f in front if last_front is None or f[0] > last_front], default=None)
    t_from = auto_from
    if "--from" in args:
        want = int(args[args.index("--from") + 1])
        t_from = min([t for t in ticks if t >= want], default=None)
    L = [f"# {mid} 全队没有前沿之后（82_outlet_gap.py；邻居 / 领土 / 余额每 90 拍采样，指令与利息逐条；终局采样拍 {end_t}）",
         "# 「贴敌队真人」= 接壤的席位属于别的队、是真人席位且没有离开；「AI / 离开席位」= 内置 AI，或别的队已离开、由 AI 接管的席位。",
         "",
         "A. 我方号的前沿（每个采样拍：在场号数 / 贴敌队真人的号数 / 贴 AI 或离开席位的号数 / 贴无主地的号数 / 三样都没有的号数）"]
    prev = None
    for i, f in enumerate(front):
        key = f[1:]
        if key != prev or i == len(front) - 1:
            L.append(f"  t={f[0]}: 在场 {f[1]} | 贴敌队真人 {f[2]} | 贴 AI / 离开席位 {f[3]} | 贴无主地 {f[4]} | 三样都没有 {f[5]}")
        prev = key
    L.append("  （只在数字变化的采样拍换行）")
    if last_front is None:
        L.append("  全程没有一个采样拍有我方号贴着敌队真人。")
    else:
        L.append(f"  最后一个还有我方号贴着敌队真人的采样拍：t={last_front}；之后第一个采样拍 t={auto_from if auto_from is not None else '（没有）'}。")
    J = {"matchId": mid, "lastFrontTick": last_front, "autoFrom": auto_from, "from": t_from, "endTick": end_t, "front": front}
    if t_from is None:
        L.append("  我方号到终局都还有敌队真人邻居，没有「全队没有前沿」的窗口。")
        txt = "\n".join(L) + "\n"
        open(os.path.join(out, "outlet_gap.txt"), "w", encoding="utf-8").write(txt)
        json.dump(J, open(os.path.join(out, "outlet_gap.json"), "w", encoding="utf-8"), ensure_ascii=False)
        print(txt)
        return
    span = end_t - t_from
    L.append(f"  本文窗口：t={t_from}~{end_t}（{span} 拍，占全场 {100 * span / max(1, end_t):.1f}%）。")

    # ---------- 指令 ----------
    all_cmds = rd("humans_cmd.tsv")
    for r in all_cmds:
        for k in ("t", "p", "pct", "target", "b0", "b1", "spent", "fee", "troops", "terr", "tTerr", "tBal", "recv", "left"):
            r[k] = int(float(r[k]))
    cmds = [r for r in all_cmds if r["t"] >= t_from]

    def group(p):
        if p in squad:
            return "我方号"
        pl = players.get(p)
        if pl is None or p not in human:
            return "AI"
        return "同队其他真人" if pl["team"] == my_team else f"T{pl['team']} 真人"

    groups = ["我方号", "同队其他真人"] + sorted({group(p) for p in human if group(p).startswith("T")})
    G = {g: defaultdict(float) for g in groups}
    for r in cmds:
        g = group(r["p"])
        if g not in G:
            continue
        S = G[g]
        if r["kind"] == "attack":
            k = {"H": "H", "N": "N"}.get(r["tt"], "A")
            S["atk" + k] += 1
            S["t" + k] += r["troops"]
            S["atkFee"] += r["fee"]
        elif r["kind"] == "boat":
            S["boatN"] += 1
            S["boatTroops"] += r["troops"]
            S["boatFee"] += r["fee"]
        elif r["kind"] == "donate":
            S["donN"] += 1
            S["donAmt"] += r["recv"]
            S["donFee"] += r["fee"]
            tg = group(r["target"])
            S["donIn" if tg == g else "donOut"] += r["recv"]
            S["donInN" if tg == g else "donOutN"] += 1
    L += ["", f"B. 窗口 t={t_from}~{end_t} 各组的账（离开后被 AI 接管的席位仍算在原来的组里）",
          "组\t在场 期初→期末\t领土 期初→期末\t余额 期初→期末\t密度 期初→期末\t打真人 条/兵\t打 AI 或离开席位 条/兵\t打无主地 条/兵\t进攻费\t发船 条/带兵/费\t捐款 笔/到账/费\t其中给组内 笔/到账\t给组外 笔/到账"]
    J["groups"] = {}
    for g in groups:
        ps = [p for p in human if group(p) == g]
        n0 = sum(1 for p in ps if at(p, t_from)[2] and at(p, t_from)[3] != 2)
        n1 = sum(1 for p in ps if at(p, end_t)[2] and at(p, end_t)[3] != 2)
        l0 = sum(at(p, t_from)[0] for p in ps if at(p, t_from)[2])
        l1 = sum(at(p, end_t)[0] for p in ps if at(p, end_t)[2])
        b0 = sum(at(p, t_from)[1] for p in ps if at(p, t_from)[2])
        b1 = sum(at(p, end_t)[1] for p in ps if at(p, end_t)[2])
        S = G[g]
        L.append(f"{g}\t{n0}→{n1}\t{fmt(l0)}→{fmt(l1)}\t{fmt(b0)}→{fmt(b1)}\t{b0 / max(1, l0):.0f}→{b1 / max(1, l1):.0f}\t{int(S['atkH'])}/{fmt(S['tH'])}\t{int(S['atkA'])}/{fmt(S['tA'])}\t{int(S['atkN'])}/{fmt(S['tN'])}\t"
                 f"{fmt(S['atkFee'])}\t{int(S['boatN'])}/{fmt(S['boatTroops'])}/{fmt(S['boatFee'])}\t{int(S['donN'])}/{fmt(S['donAmt'])}/{fmt(S['donFee'])}\t{int(S['donInN'])}/{fmt(S['donIn'])}\t{int(S['donOutN'])}/{fmt(S['donOut'])}")
        J["groups"][g] = {"n0": n0, "n1": n1, "terr0": l0, "terr1": l1, "bal0": b0, "bal1": b1, **{k: v for k, v in S.items()}}

    # ---------- C. 同队其他真人 ----------
    mates = [p for p in human if group(p) == "同队其他真人" and (at(p, t_from)[2] or at(p, end_t)[2])]
    win_ticks = [t for t in ticks if t >= t_from]
    L += ["", f"C. 同队其他真人在窗口内（按期末领土排；空间 = 150×领土 − 余额，即引擎还肯让他收多少兵；t≥4284 捐款不再查配额）",
          "玩家\t领土 期初→期末\t余额 期初→期末\t密度 期初→期末（窗口内最低）\t空间 期初 / 窗口内最小\t打真人 条/兵\t打 AI 或离开席位 条/兵\t挨敌队真人 条/兵\t收捐 笔/到账（来自）"]
    J["mates"] = []
    for p in sorted(mates, key=lambda p: -at(p, end_t)[0]):
        s0, s1 = at(p, t_from), at(p, end_t)
        dens = [at(p, t)[1] / max(1, at(p, t)[0]) for t in win_ticks if at(p, t)[2] and at(p, t)[0] > 0]
        rooms = [150 * at(p, t)[0] - at(p, t)[1] for t in win_ticks if at(p, t)[2] and at(p, t)[0] > 0]
        aH = [r for r in cmds if r["p"] == p and r["kind"] == "attack" and r["tt"] == "H"]
        aA = [r for r in cmds if r["p"] == p and r["kind"] == "attack" and r["tt"] in ("A", "L")]
        hit = [r for r in cmds if r["kind"] == "attack" and r["tt"] == "H" and r["target"] == p and players.get(r["p"], {}).get("team") != my_team]
        rc = [r for r in cmds if r["kind"] == "donate" and r["target"] == p and r["recv"] > 0]
        frm = defaultdict(int)
        for r in rc:
            frm[players[r["p"]]["name"][:14] + ("*" if r["p"] in squad else "")] += r["recv"]
        tail = "" if s1[2] else "（期末已出局）"
        if s1[3] == 2:
            tail = "（期末已离开）"
        L.append(f"{players[p]['name'][:18]}#{p}{tail}\t{fmt(s0[0])}→{fmt(s1[0])}\t{fmt(s0[1])}→{fmt(s1[1])}\t{s0[1] / max(1, s0[0]):.0f}→{s1[1] / max(1, s1[0]):.0f}（{min(dens) if dens else 0:.0f}）\t"
                 f"{fmt(150 * s0[0] - s0[1])} / {fmt(min(rooms)) if rooms else '-'}\t{len(aH)}/{fmt(sum(r['troops'] for r in aH))}\t{len(aA)}/{fmt(sum(r['troops'] for r in aA))}\t"
                 f"{len(hit)}/{fmt(sum(r['troops'] for r in hit))}\t{len(rc)}/{fmt(sum(r['recv'] for r in rc))}" + ("（" + "、".join(f"{k} {fmt(v)}" for k, v in sorted(frm.items(), key=lambda kv: -kv[1])) + "）" if frm else ""))
        J["mates"].append({"p": p, "name": players[p]["name"], "terr0": s0[0], "terr1": s1[0], "bal0": s0[1], "bal1": s1[1], "minDens": min(dens) if dens else None,
                           "room0": 150 * s0[0] - s0[1], "minRoom": min(rooms) if rooms else None, "atkH": len(aH), "tH": sum(r["troops"] for r in aH),
                           "hitN": len(hit), "hit": sum(r["troops"] for r in hit), "recvN": len(rc), "recv": sum(r["recv"] for r in rc), "recvFrom": dict(frm)})
    sq_to_mates = [r for r in cmds if r["kind"] == "donate" and r["p"] in squad and group(r["target"]) == "同队其他真人"]
    L.append(f"  我方号在窗口内捐给同队其他真人：{len(sq_to_mates)} 笔，到账 {fmt(sum(r['recv'] for r in sq_to_mates))}。")

    # ---------- D. 我方每个号 ----------
    eco = defaultdict(int)
    names = {}
    for r in rd("tick_net.tsv"):
        if int(r["t0"]) >= t_from:
            eco[r["bot"]] += int(float(r["eco"]))
    bot_p = {}
    for t in bt:
        for r in border[t]:
            bot_p[r["bot"]] = int(r["p"])
    L += ["", f"D. 我方每个号在窗口内（利息地租取 tick_net.tsv 的 eco；捐出 / 收到取 humans_cmd.tsv 的引擎实收）",
          "号\t领土\t余额 期初→期末\t密度 期初→期末\t利息地租\t进攻 条\t发船 条/带兵/费\t捐出 笔/到账/费\t收到 笔/到账\t手续费合计÷利息地租"]
    tot = defaultdict(float)
    J["bots"] = {}
    for b, p in sorted(bot_p.items(), key=lambda kv: -at(kv[1], end_t)[0]):
        s0, s1 = at(p, t_from), at(p, end_t)
        mine = [r for r in cmds if r["p"] == p]
        atk = [r for r in mine if r["kind"] == "attack"]
        boat = [r for r in mine if r["kind"] == "boat"]
        don = [r for r in mine if r["kind"] == "donate"]
        rc = [r for r in cmds if r["kind"] == "donate" and r["target"] == p and r["recv"] > 0]
        fee = sum(r["fee"] for r in mine)
        e = eco.get(b, 0)
        L.append(f"{b}\t{fmt(s1[0])}\t{fmt(s0[1])}→{fmt(s1[1])}\t{s0[1] / max(1, s0[0]):.0f}→{s1[1] / max(1, s1[0]):.0f}\t{fmt(e)}\t{len(atk)}\t{len(boat)}/{fmt(sum(r['troops'] for r in boat))}/{fmt(sum(r['fee'] for r in boat))}\t"
                 f"{len(don)}/{fmt(sum(r['recv'] for r in don))}/{fmt(sum(r['fee'] for r in don))}\t{len(rc)}/{fmt(sum(r['recv'] for r in rc))}\t{100 * fee / max(1, e):.1f}%")
        for k, v in (("eco", e), ("fee", fee), ("donN", len(don)), ("donAmt", sum(r["recv"] for r in don)), ("donFee", sum(r["fee"] for r in don)), ("boatN", len(boat)),
                     ("boatTroops", sum(r["troops"] for r in boat)), ("boatFee", sum(r["fee"] for r in boat)), ("atkN", len(atk)), ("bal0", s0[1]), ("bal1", s1[1]), ("terr1", s1[0])):
            tot[k] += v
        J["bots"][b] = {"terr": s1[0], "bal0": s0[1], "bal1": s1[1], "eco": e, "fee": fee, "donN": len(don), "donAmt": sum(r["recv"] for r in don), "recvN": len(rc), "recv": sum(r["recv"] for r in rc)}
    L.append(f"合计\t{fmt(tot['terr1'])}\t{fmt(tot['bal0'])}→{fmt(tot['bal1'])}\t\t{fmt(tot['eco'])}\t{int(tot['atkN'])}\t{int(tot['boatN'])}/{fmt(tot['boatTroops'])}/{fmt(tot['boatFee'])}\t"
             f"{int(tot['donN'])}/{fmt(tot['donAmt'])}/{fmt(tot['donFee'])}\t\t{100 * tot['fee'] / max(1, tot['eco']):.1f}%")
    L.append(f"  窗口内我方：利息地租 {fmt(tot['eco'])}；手续费 {fmt(tot['fee'])}（捐款费 {fmt(tot['donFee'])}、发船费 {fmt(tot['boatFee'])}）；期末还压在手里 {fmt(tot['bal1'])}；"
             f"两项合计 {fmt(tot['fee'] + tot['bal1'])}。进攻指令 {int(tot['atkN'])} 条。")
    J["squadTotals"] = dict(tot)

    # ---------- E. 抽样对照 ----------
    L += ["", "E. 抽样对照（在场、没有离开的席位）：我方号 / 同队其他真人 的领土、余额、密度；同队领土最大的三个人（领土 / 密度）；我方占本队领土、余额的比例"]
    step = max(1, len(win_ticks) // 9)
    pick = win_ticks[::step]
    if pick[-1] != end_t:
        pick.append(end_t)
    J["samples"] = []
    for t in pick:
        sq = [at(p, t) for p in squad if at(p, t)[2] and at(p, t)[3] != 2]
        mt = [(p, at(p, t)) for p in human if group(p) == "同队其他真人" and at(p, t)[2] and at(p, t)[3] != 2]
        sl, sb = sum(x[0] for x in sq), sum(x[1] for x in sq)
        ml, mb = sum(x[1][0] for x in mt), sum(x[1][1] for x in mt)
        top = sorted(mt, key=lambda x: -x[1][0])[:3]
        L.append(f"  t={t}: 我方 {len(sq)} 号 {fmt(sl)} 格 / {fmt(sb)} 兵（密度 {sb / max(1, sl):.0f}）| 同队其他 {len(mt)} 人 {fmt(ml)} 格 / {fmt(mb)} 兵（密度 {mb / max(1, ml):.0f}）| "
                 + "、".join(f"{players[p]['name'][:12]} {fmt(s[0])} 格 / 密度 {s[1] / max(1, s[0]):.0f}" for p, s in top)
                 + f" | 我方占本队领土 {100 * sl / max(1, sl + ml):.1f}%、余额 {100 * sb / max(1, sb + mb):.1f}%")
        J["samples"].append({"t": t, "squadTerr": sl, "squadBal": sb, "matesTerr": ml, "matesBal": mb})
    # ---------- F. 全场捐款按组 ----------
    L += ["", "F. 全场（t=0 起）本队内部的捐款按「捐方组 → 收方组」分（引擎实收；到账为 0 的不计笔数）"]
    M = defaultdict(lambda: [0, 0, 0])
    for r in all_cmds:
        if r["kind"] != "donate" or r["recv"] <= 0:
            continue
        ga, gb = group(r["p"]), group(r["target"])
        if ga in ("我方号", "同队其他真人") and gb in ("我方号", "同队其他真人"):
            m = M[(ga, gb)]
            m[0] += 1
            m[1] += r["recv"]
            m[2] += r["fee"]
    J["donationMatrix"] = {}
    for ga in ("我方号", "同队其他真人"):
        for gb in ("我方号", "同队其他真人"):
            m = M[(ga, gb)]
            L.append(f"  {ga} → {gb}：{m[0]} 笔，到账 {fmt(m[1])}，手续费 {fmt(m[2])}")
            J["donationMatrix"][f"{ga}→{gb}"] = m
    sq_h = [r for r in all_cmds if r["p"] in squad and r["kind"] == "attack" and r["tt"] == "H"]
    last_h = max((r["t"] for r in sq_h), default=None)
    L.append(f"  我方号全场对真人的进攻 {len(sq_h)} 条 {fmt(sum(r['troops'] for r in sq_h))} 兵，最后一条在 t={last_h}；"
             f"之后到终局 {end_t - last_h if last_h is not None else '-'} 拍。")
    J["lastSquadAttackOnHuman"] = last_h
    # ---------- G. 窗口内的调度日志 ----------
    logp = os.path.join(DATA, "bundles", mid, "in_game.log")
    if os.path.exists(logp):
        pat = re.compile(r"\[(\w+)\] \[HL-DISPATCH\] t=(\d+) (\w+) pct=(\d+)/1024 -> ally=(\d+)\((.*?)\) boxedIn=(\w+) myBal=(\d+) dMe=(\d+) dAlly=(\d+)")
        rows = []
        for line in open(logp, encoding="utf-8", errors="replace"):
            if "HL-DISPATCH" not in line:
                continue
            m = pat.search(line)
            if m and int(m.group(2)) >= t_from - 10:
                rows.append({"bot": m.group(1), "t": int(m.group(2)), "kind": m.group(3), "pct": int(m.group(4)), "boxed": m.group(7), "dMe": int(m.group(9)), "dAlly": int(m.group(10))})
        L += ["", f"G. 窗口内的调度日志（in_game.log 的 [HL-DISPATCH]，决策拍 ≥ {t_from - 10}；日志在发令拍写，落地晚 7~20 拍）"]
        if rows:
            kc, bc, dc = defaultdict(int), defaultdict(int), defaultdict(int)
            for r in rows:
                kc[r["kind"]] += 1
                bc[r["boxed"]] += 1
                dc[r["bot"]] += 1
            dme = sorted(r["dMe"] for r in rows)
            dal = sorted(r["dAlly"] for r in rows)
            L.append(f"  共 {len(rows)} 条；类别：" + "、".join(f"{k} {v}" for k, v in sorted(kc.items(), key=lambda kv: -kv[1])) + "；boxedIn：" + "、".join(f"{k} {v}" for k, v in bc.items()))
            L.append(f"  捐方密度 dMe 最小 {dme[0]} / 中位 {dme[len(dme) // 2]} / 最大 {dme[-1]}（≥105 的 {sum(1 for x in dme if x >= 105)} 条）；"
                     f"收方密度 dAlly 最小 {dal[0]} / 中位 {dal[len(dal) // 2]} / 最大 {dal[-1]}（≤112 的 {sum(1 for x in dal if x <= 112)} 条）；捐方密度低于收方的 {sum(1 for r in rows if r['dMe'] < r['dAlly'])} 条")
            L.append("  按捐方：" + "、".join(f"{k} {v}" for k, v in sorted(dc.items(), key=lambda kv: -kv[1])))
            J["windowDispatchLogs"] = {"n": len(rows), "kinds": dict(kc), "boxedIn": dict(bc), "dMeMin": dme[0], "dMeMed": dme[len(dme) // 2], "dAllyMax": dal[-1], "dAllyMed": dal[len(dal) // 2]}
        else:
            L.append("  没有。")
    txt = "\n".join(L) + "\n"
    open(os.path.join(out, "outlet_gap.txt"), "w", encoding="utf-8").write(txt)
    json.dump(J, open(os.path.join(out, "outlet_gap.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(txt)


if __name__ == "__main__":
    main()
