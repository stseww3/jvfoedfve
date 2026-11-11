#!/usr/bin/env python3
"""42_patterns.py — 机械模式检测（R07 v2.0）。单局或全部对局包。

每个模式都有一个可检测的定义，只用 bundles/<matchId>/ 里的 traj.csv / events.csv / results.csv / in_game.log / card.json。
「窗口」= 同一个号相邻两个 HL-TICK 快照，且间隔恰好 90 拍、cmds 计数没有回绕（热更新会把 cmds 清零）。
窗口内的「进攻类指令数」dAtk = dCmds − 窗口内该号的捐款/调度条数 − 协防条数 − 拦截条数（这三类在策略里也会 cmds++）。

模式定义：
  R07-IO-CRASH        日志里有 `ERROR: Strategy bot stopped`。记：条数、涉及号数、首末拍号区间。
  R07-IO-DUP-ASSIST   同一个号在 ≤12 拍内连发 ≥3 条 [HL-ASSIST]（同一目标）。记：串数、每串条数。
  R07-DN-CHAIN18      同一个号相邻两笔捐款/调度间隔 ≤24 拍（前一笔的余额变化还没回到本地就又捐）。记：相邻对数。
  R07-DN-TAX51        捐款/调度 pct ≤ 60（到账 ≤ 5.96% 余额，手续费恒为 6.25% 余额 → 费 ≥ 到账）。记：笔数、名义到账、手续费。
  R07-EC-BOXED-RICH   快照：nb=0 且 neut=0 且 dens ≥ 60（后排围死，兵闲置）。记：快照数、Σ余额。
  R07-EC-IDLE-RICH    窗口：nb0 ≥ 1、dens0 ≥ 60、dAtk = 0（挨着敌人、兵多、90 拍不出手）。记：窗口数。
  R07-EC-SOFTCAP      快照：dens ≥ 100（超过软上限，利息被扣）。R07-EC-HARDCAP：dens ≥ 145。
  R07-DF-PASSIVE-BLEED 窗口：dTerr ≤ −max(200, 2%·terr0)、dAtk = 0、bal0 ≥ 8·terr0（在丢地、手里有兵、没有任何进攻/反击指令）。记：窗口数、丢地合计。
  R07-DF-RICH-BLEED   PASSIVE-BLEED 的子集：窗口起点 dens0 ≥ 60（兵很多、在丢地、零进攻指令）。记：窗口数、丢地合计、Σ起点余额。
  R07-DN-IDLE-RECV    捐款/调度的收方是我方号，且（a）收方最近快照 ≤90 拍、dens ≥ 60（收方自己兵就多），或（b）收方 >90 拍没有快照（停摆/已死）。
                      记：两类笔数、名义到账、手续费。
  R07-AT-BIG-BURN     窗口：余额跌 ≥30%、bal0 ≥ 100000、捐款解释不了一半、且 (bal0−bal1)/max(1,dTerr) ≥ 100（每多 1 格地花了 ≥100 兵，或领土没涨）。记：窗口数、Σ跌幅。
  R07-SP-CLUSTER      出生：最终出生点里，最近队友距离 < 140 像素的号数（同一队伍挤在一起）。
  R07-SP-SCATTER      出生：最终出生点里，最近队友距离 ≥ 300 像素的号数（孤立出生）。另记：其中在 t<2400 就阵亡或领土掉到 <100 格的号数。
  R07-DN-PINGPONG     A 给 B 捐款后 400 拍内 B 又给 A 捐款（两个号互相倒手，每一手都按捐方全部余额抽 6.25%）。记：回捐笔数、名义到账、手续费。
  R07-DN-DEAD-RECV    收方在捐款之后的 90 拍内没有发出任何指令（cmds 不变）且领土在掉（收方已经不决策，只是在挨打）。记：笔数、名义到账、手续费。
  R07-OP-BOXED-EARLY  t ≤ 1620 时已经 nb=0 且 neut=0 的号（开局就被队友围死）。记：号数、最早拍号、当时领土。
  R07-EC-NO-OUTLET    同一个号（领土 ≥1000）连续 ≥10 个快照 nb=0 且 neut=0、cmds 不变、余额不降（围死且一条指令都发不出去）。记：段数、快照数、段末最大余额。
                      注意：策略停摆（R07-IO-CRASH）的号也会命中，要对照报错条数排除。
  R07-EC-NEUT-LOCK    同一个号（领土 ≥1000）连续 ≥3 个快照 nb=0、贴着 1~5 格中立地、cmds 和领土都不变
                      （零碎中立地不值一条指令，但只要 neutral>0 就不发船：既不吃也不出海）。记：段数、快照数、段末最大余额。
  R07-EG-FRONT-STARVE 快照 t：有接敌号（nb≥1、dens<20、领土≥1000）在下一个窗口丢地 ≥max(200,2%)，而 nb=0 的号加上「dens≥60 且该窗口零进攻」的号握有全队 ≥50% 的兵。记：快照数、薄号丢地合计。
  R07-MT-PRE2400-HOLD 全队贴着的中立地 ≤5（t≥900 第一次）到 t=2400：记份额变化、接敌窗口数（nb≥1）、其中零进攻的窗口数。
  R07-GOOD-SAVED-PUSH （正例）≤3 个连续窗口领土 +≥30% 且 ≥1500 格，起点 dens≥20，期间没有收到捐款（用自己攒的兵换地）。记：次数、涨地合计。
  R07-GOOD-BOXED-BOAT （正例）围死的号（nb=0&neut=0）在 540 拍内领土 +≥max(1000,20%) 且 boats 计数增加（靠船解套）。记：号数、涨地合计。

用法：
  python3 42_patterns.py <matchId> [--print]       # 单局，写 out/<matchId>/patterns.json
  python3 42_patterns.py --all [--print]           # 全部对局包，写 out/common/patterns_all.json / .tsv
"""
import json
import os
import re
import sys
from collections import defaultdict

from r07lib import DATA, OUT, bdir, load_card, load_csv, load_events, load_results, load_traj, donate_quote, ensure_out


def analyze(mid):
    card = load_card(mid)
    land = card["mapLand"]
    traj = load_traj(mid)
    events = load_events(mid)
    res = {"matchId": mid, "cohort": card.get("cohort"), "result": card["outcome"]["resultLabel"], "endTick": card["outcome"]["endTick"],
           "actualTeams": card.get("actualTeams"), "squadBots": card.get("squadBots")}
    pat = {}
    inst = defaultdict(list)

    # ---- crash
    n_err = 0
    err_bots = set()
    hot = 0
    try:
        with open(os.path.join(bdir(mid), "in_game.log"), encoding="utf-8") as f:
            for ln in f:
                if "ERROR: Strategy bot stopped" in ln:
                    n_err += 1
                    m = re.match(r"\d+\t\[([A-Za-z0-9_]+)\]", ln)
                    if m:
                        err_bots.add(m.group(1))
    except FileNotFoundError:
        pass
    # cmds 回绕（热更新 / 策略实例被替换）
    resets = 0
    for b, rows in traj.items():
        for a, c in zip(rows, rows[1:]):
            if c["cmds"] < a["cmds"]:
                resets += 1
                inst["R07-IO-CMDS-RESET"].append({"bot": b, "t0": a["t"], "t1": c["t"]})
    pat["R07-IO-CRASH"] = {"errors": n_err, "bots": len(err_bots), "cmdsResets": resets}

    dons = [e for e in events if e["type"] in ("DONATE", "DISPATCH")]
    asts = [e for e in events if e["type"] == "ASSIST"]
    itcs = [e for e in events if e["type"] == "INTERCEPT"]
    by_bot = defaultdict(lambda: {"don": [], "ast": [], "itc": []})
    for e in dons:
        by_bot[e["bot"]]["don"].append(e)
    for e in asts:
        by_bot[e["bot"]]["ast"].append(e)
    for e in itcs:
        by_bot[e["bot"]]["itc"].append(e)

    # ---- dup assist
    bursts = []
    for b, d in by_bot.items():
        a = sorted(d["ast"], key=lambda e: e["t"])
        cur = []
        for e in a:
            if cur and e["t"] - cur[-1]["t"] <= 6 and e.get("target") == cur[-1].get("target"):
                cur.append(e)
            else:
                if len(cur) >= 3 and cur[-1]["t"] - cur[0]["t"] <= 12 + 6 * (len(cur) - 3):
                    bursts.append((b, cur))
                cur = [e]
        if len(cur) >= 3:
            bursts.append((b, cur))
    pat["R07-IO-DUP-ASSIST"] = {"bursts": len(bursts), "cmds": sum(len(c) for _, c in bursts), "assistTotal": len(asts)}
    for b, c in bursts:
        inst["R07-IO-DUP-ASSIST"].append({"bot": b, "t0": c[0]["t"], "t1": c[-1]["t"], "n": len(c), "target": c[0].get("target")})

    # ---- donation chain + tax
    chain = 0
    for b, d in by_bot.items():
        dd = sorted(d["don"], key=lambda e: e["t"])
        for x, y in zip(dd, dd[1:]):
            if y["t"] - x["t"] <= 24:
                chain += 1
                inst["R07-DN-CHAIN18"].append({"bot": b, "t0": x["t"], "t1": y["t"]})
    tax_n = 0
    tax_amt = 0
    tax_fee = 0
    all_amt = 0
    all_fee = 0
    for e in dons:
        if not isinstance(e.get("myBal"), (int, float)) or not isinstance(e.get("pct"), (int, float)):
            continue
        amt, fee = donate_quote(int(e["myBal"]), int(e["pct"]))
        all_amt += amt
        all_fee += fee
        if e["pct"] <= 60:
            tax_n += 1
            tax_amt += amt
            tax_fee += fee
    pat["R07-DN-CHAIN18"] = {"pairs": chain}
    pat["R07-DN-TAX51"] = {"n": tax_n, "amt": tax_amt, "fee": tax_fee, "allN": len(dons), "allAmt": all_amt, "allFee": all_fee,
                           "rejFlag": sum(1 for e in dons if e["likelyRejected"])}

    # ---- snapshots / windows
    boxed_rich = 0
    boxed_rich_bal = 0
    soft = 0
    hard = 0
    idle_rich = 0
    passive = 0
    passive_px = 0
    rich_bleed = 0
    rich_bleed_px = 0
    rich_bleed_bal = 0
    burn = 0
    burn_sum = 0
    boxed_early = []
    for b, rows in traj.items():
        first_boxed = None
        for r in rows:
            if r["nb"] == 0 and r["neut"] == 0:
                if r["dens"] >= 60:
                    boxed_rich += 1
                    boxed_rich_bal += r["bal"]
                if first_boxed is None:
                    first_boxed = r
            if r["dens"] >= 100:
                soft += 1
            if r["dens"] >= 145:
                hard += 1
        if first_boxed is not None and first_boxed["t"] <= 1620:
            boxed_early.append({"bot": b, "t": first_boxed["t"], "terr": first_boxed["terr"]})
        ev = by_bot.get(b, {"don": [], "ast": [], "itc": []})
        for a, c in zip(rows, rows[1:]):
            if c["t"] - a["t"] != 90 or c["cmds"] < a["cmds"]:
                continue
            nd = sum(1 for e in ev["don"] if a["t"] <= e["t"] < c["t"])
            na = sum(1 for e in ev["ast"] if a["t"] <= e["t"] < c["t"])
            ni = sum(1 for e in ev["itc"] if a["t"] <= e["t"] < c["t"])
            d_atk = (c["cmds"] - a["cmds"]) - nd - na - ni
            d_terr = c["terr"] - a["terr"]
            if a["nb"] >= 1 and a["dens"] >= 60 and d_atk <= 0:
                idle_rich += 1
                inst["R07-EC-IDLE-RICH"].append({"bot": b, "t0": a["t"], "dens": a["dens"], "bal": a["bal"], "dTerr": d_terr})
            if d_terr <= -max(200, 0.02 * a["terr"]) and d_atk <= 0 and a["bal"] >= 8 * a["terr"]:
                passive += 1
                passive_px += -d_terr
                inst["R07-DF-PASSIVE-BLEED"].append({"bot": b, "t0": a["t"], "dTerr": d_terr, "bal0": a["bal"], "dens0": a["dens"]})
                if a["dens"] >= 60:
                    rich_bleed += 1
                    rich_bleed_px += -d_terr
                    rich_bleed_bal += a["bal"]
                    inst["R07-DF-RICH-BLEED"].append({"bot": b, "t0": a["t"], "dTerr": d_terr, "bal0": a["bal"], "dens0": a["dens"], "nb0": a["nb"]})
            drop = a["bal"] - c["bal"]
            if a["bal"] >= 100000 and drop >= 0.3 * a["bal"]:
                don_cost = 0
                for e in ev["don"]:
                    if a["t"] <= e["t"] < c["t"] and isinstance(e.get("myBal"), (int, float)):
                        amt, fee = donate_quote(int(e["myBal"]), int(e["pct"]))
                        don_cost += amt + fee
                if don_cost < 0.5 * drop and drop / max(1, d_terr) >= 100:
                    burn += 1
                    burn_sum += drop
                    inst["R07-AT-BIG-BURN"].append({"bot": b, "t0": a["t"], "bal0": a["bal"], "bal1": c["bal"], "dTerr": d_terr, "dAtk": d_atk, "assist": na})
    pat["R07-EC-BOXED-RICH"] = {"snaps": boxed_rich, "sumBal": boxed_rich_bal}
    pat["R07-EC-SOFTCAP"] = {"snaps": soft}
    pat["R07-EC-HARDCAP"] = {"snaps": hard}
    pat["R07-EC-IDLE-RICH"] = {"windows": idle_rich}
    pat["R07-DF-PASSIVE-BLEED"] = {"windows": passive, "px": passive_px}
    pat["R07-DF-RICH-BLEED"] = {"windows": rich_bleed, "px": rich_bleed_px, "sumBal0": rich_bleed_bal}
    pat["R07-AT-BIG-BURN"] = {"windows": burn, "sumDrop": burn_sum}

    # ---- donations to idle / frozen recipients
    idle_recv = {"denseN": 0, "denseAmt": 0, "denseFee": 0, "staleN": 0, "staleAmt": 0, "staleFee": 0}
    for e in dons:
        if not isinstance(e.get("myBal"), (int, float)) or not isinstance(e.get("pct"), (int, float)):
            continue
        nm = str(e.get("targetName") or "")
        rb = next((b for b in traj if nm.endswith(b)), None)
        if not rb:
            continue
        before = [x for x in traj[rb] if x["t"] <= e["t"]]
        if not before:
            continue
        amt, fee = donate_quote(int(e["myBal"]), int(e["pct"]))
        srow = before[-1]
        if e["t"] - srow["t"] > 90:
            idle_recv["staleN"] += 1
            idle_recv["staleAmt"] += amt
            idle_recv["staleFee"] += fee
            inst["R07-DN-IDLE-RECV"].append({"t": e["t"], "bot": e["bot"], "recv": rb, "why": "stale", "age": e["t"] - srow["t"]})
        elif srow["dens"] >= 60:
            idle_recv["denseN"] += 1
            idle_recv["denseAmt"] += amt
            idle_recv["denseFee"] += fee
            inst["R07-DN-IDLE-RECV"].append({"t": e["t"], "bot": e["bot"], "recv": rb, "why": "dense", "recvDens": srow["dens"]})
    pat["R07-DN-IDLE-RECV"] = idle_recv

    # ---- ping-pong: A→B then B→A within 400 ticks
    def recv_bot(e):
        nm = str(e.get("targetName") or "")
        return next((b for b in traj if nm.endswith(b)), None)
    dq = [(e, recv_bot(e)) for e in sorted(dons, key=lambda e: e["t"]) if isinstance(e.get("myBal"), (int, float)) and isinstance(e.get("pct"), (int, float))]
    pp = {"n": 0, "amt": 0, "fee": 0}
    for i, (e, rb) in enumerate(dq):
        if not rb:
            continue
        prior = [(e2, r2) for e2, r2 in dq[:i] if e2["bot"] == rb and r2 == e["bot"] and 0 <= e["t"] - e2["t"] <= 400]
        if prior:
            amt, fee = donate_quote(int(e["myBal"]), int(e["pct"]))
            pp["n"] += 1
            pp["amt"] += amt
            pp["fee"] += fee
            inst["R07-DN-PINGPONG"].append({"t": e["t"], "bot": e["bot"], "to": rb, "priorT": prior[-1][0]["t"]})
    pat["R07-DN-PINGPONG"] = pp

    # ---- donations to a recipient that issues no command in the next 90 ticks while losing land
    dead = {"n": 0, "amt": 0, "fee": 0}
    for e, rb in dq:
        if not rb:
            continue
        rows_r = traj[rb]
        before = [x for x in rows_r if x["t"] <= e["t"]]
        after = [x for x in rows_r if x["t"] >= e["t"] + 90]
        if not before or not after:
            continue
        a0, a1 = before[-1], after[0]
        if a1["t"] - a0["t"] > 200 or a1["cmds"] < a0["cmds"]:
            continue
        if a1["cmds"] == a0["cmds"] and a1["terr"] < a0["terr"]:
            amt, fee = donate_quote(int(e["myBal"]), int(e["pct"]))
            dead["n"] += 1
            dead["amt"] += amt
            dead["fee"] += fee
            inst["R07-DN-DEAD-RECV"].append({"t": e["t"], "bot": e["bot"], "recv": rb, "recvTerr0": a0["terr"], "recvTerr1": a1["terr"]})
    pat["R07-DN-DEAD-RECV"] = dead
    pat["R07-OP-BOXED-EARLY"] = {"bots": len(boxed_early), "list": boxed_early}

    # ---- spawn cluster
    spawn = load_csv(mid, "spawn.csv")
    final = {}
    for r in spawn:
        final[r["bot"]] = r
    pts = {b: (r["x"], r["y"]) for b, r in final.items() if isinstance(r.get("x"), (int, float))}
    close = 0
    mins = []
    for b in pts:
        ds = [((pts[b][0] - pts[o][0]) ** 2 + (pts[b][1] - pts[o][1]) ** 2) ** 0.5 for o in pts if o != b]
        if ds:
            mins.append(min(ds))
            if min(ds) < 140:
                close += 1
    pat["R07-SP-CLUSTER"] = {"bots": len(pts), "closeLt140": close, "medianNearest": round(sorted(mins)[len(mins) // 2]) if mins else None}
    far = []
    for b in pts:
        ds = [((pts[b][0] - pts[o][0]) ** 2 + (pts[b][1] - pts[o][1]) ** 2) ** 0.5 for o in pts if o != b]
        if ds and min(ds) >= 300:
            far.append(b)
    early_gone = []
    for b in far:
        rows = traj.get(b, [])
        gone = next((r["t"] for r in rows if r["t"] < 2400 and r["t"] >= 900 and r["terr"] < 100), None)
        last = rows[-1]["t"] if rows else 0
        if gone is not None or (rows and last < 2400):
            early_gone.append({"bot": b, "t": gone if gone is not None else last})
    pat["R07-SP-SCATTER"] = {"bots": len(pts), "farGe300": len(far), "farList": far, "earlyGone": len(early_gone), "list": early_gone}

    # ---- helper: received donations per bot (by recipient name suffix)
    recv_by = defaultdict(list)
    for e in dons:
        nm = str(e.get("targetName") or "")
        rb = next((b for b in traj if nm.endswith(b)), None)
        if rb:
            recv_by[rb].append(e["t"])

    # ---- NO-OUTLET: ≥10 consecutive snapshots nb=0&neut=0 with cmds unchanged and balance rising
    no_outlet = []
    for b, rows in traj.items():
        i = 0
        while i < len(rows):
            if rows[i]["nb"] == 0 and rows[i]["neut"] == 0 and rows[i]["terr"] >= 1000:
                j = i
                while (j + 1 < len(rows) and rows[j + 1]["nb"] == 0 and rows[j + 1]["neut"] == 0
                       and rows[j + 1]["cmds"] == rows[i]["cmds"] and rows[j + 1]["bal"] >= rows[j]["bal"]):
                    j += 1
                if j - i + 1 >= 10:
                    no_outlet.append({"bot": b, "t0": rows[i]["t"], "t1": rows[j]["t"], "snaps": j - i + 1, "terr": rows[i]["terr"],
                                      "bal0": rows[i]["bal"], "bal1": rows[j]["bal"], "dens1": rows[j]["dens"]})
                i = j + 1
            else:
                i += 1
    pat["R07-EC-NO-OUTLET"] = {"spans": len(no_outlet), "snaps": sum(x["snaps"] for x in no_outlet), "maxBal1": max((x["bal1"] for x in no_outlet), default=0)}
    inst["R07-EC-NO-OUTLET"] = no_outlet

    # ---- NEUT-LOCK: ≥3 consecutive snapshots nb=0 with 1..5 neutral px touching, cmds and terr unchanged
    neut_lock = []
    for b, rows in traj.items():
        i = 0
        while i < len(rows):
            if rows[i]["nb"] == 0 and 1 <= rows[i]["neut"] <= 5 and rows[i]["terr"] >= 1000:
                j = i
                while (j + 1 < len(rows) and rows[j + 1]["nb"] == 0 and 1 <= rows[j + 1]["neut"] <= 5
                       and rows[j + 1]["cmds"] == rows[i]["cmds"] and rows[j + 1]["terr"] == rows[i]["terr"]):
                    j += 1
                if j - i + 1 >= 3:
                    neut_lock.append({"bot": b, "t0": rows[i]["t"], "t1": rows[j]["t"], "snaps": j - i + 1, "terr": rows[i]["terr"],
                                      "neut": rows[i]["neut"], "bal0": rows[i]["bal"], "bal1": rows[j]["bal"], "dens1": rows[j]["dens"]})
                i = j + 1
            else:
                i += 1
    pat["R07-EC-NEUT-LOCK"] = {"spans": len(neut_lock), "snaps": sum(x["snaps"] for x in neut_lock), "maxBal1": max((x["bal1"] for x in neut_lock), default=0)}
    inst["R07-EC-NEUT-LOCK"] = neut_lock

    # ---- FRONT-STARVE: at snapshot t a thin frontline bot is losing land while idle/boxed bots hold ≥50% of the squad's troops
    by_t = defaultdict(dict)
    for b, rows in traj.items():
        for k, r in enumerate(rows):
            nxt = rows[k + 1] if k + 1 < len(rows) and rows[k + 1]["t"] - r["t"] == 90 and rows[k + 1]["cmds"] >= r["cmds"] else None
            by_t[r["t"]][b] = (r, nxt)
    starve = []
    for t in sorted(by_t):
        d = by_t[t]
        tot = sum(r["bal"] for r, _ in d.values())
        if tot <= 0 or len(d) < 2:
            continue
        thin = [b for b, (r, n) in d.items() if n and r["nb"] >= 1 and r["dens"] < 20 and r["terr"] >= 1000
                and n["terr"] - r["terr"] <= -max(200, 0.02 * r["terr"])]
        if not thin:
            continue
        back = 0
        for b, (r, n) in d.items():
            if b in thin:
                continue
            ev = by_bot.get(b, {"don": [], "ast": [], "itc": []})
            if r["nb"] == 0:
                back += r["bal"]
            elif n and r["dens"] >= 60:
                nd = sum(1 for e in ev["don"] if r["t"] <= e["t"] < n["t"])
                na = sum(1 for e in ev["ast"] if r["t"] <= e["t"] < n["t"])
                ni = sum(1 for e in ev["itc"] if r["t"] <= e["t"] < n["t"])
                if (n["cmds"] - r["cmds"]) - nd - na - ni <= 0:
                    back += r["bal"]
        if back >= 0.5 * tot:
            starve.append({"t": t, "thin": thin, "thinPx": sum(-(d[b][1]["terr"] - d[b][0]["terr"]) for b in thin), "backShare": round(back / tot, 3)})
    pat["R07-EG-FRONT-STARVE"] = {"snaps": len(starve), "px": sum(x["thinPx"] for x in starve)}
    inst["R07-EG-FRONT-STARVE"] = starve

    # ---- PRE2400-HOLD: from the first snapshot (t>=900) where squad neutral contact <=5 until t=2400
    ts_sorted = sorted(by_t)
    t_n0 = next((t for t in ts_sorted if t >= 900 and sum(r["neut"] for r, _ in by_t[t].values()) <= 5), None)
    hold = {"tNeut0": t_n0, "share0": None, "share2400": None, "nbWindows": 0, "idleNbWindows": 0}
    if t_n0 is not None and t_n0 < 2400:
        t_end = max((t for t in ts_sorted if t <= 2400), default=None)
        if t_end is not None and t_end > t_n0:
            hold["share0"] = round(100 * sum(r["terr"] for r, _ in by_t[t_n0].values()) / land, 2)
            hold["share2400"] = round(100 * sum(r["terr"] for r, _ in by_t[t_end].values()) / land, 2)
            for t in ts_sorted:
                if not (t_n0 <= t < t_end):
                    continue
                for b, (r, n) in by_t[t].items():
                    if not n or r["nb"] < 1:
                        continue
                    ev = by_bot.get(b, {"don": [], "ast": [], "itc": []})
                    nd = sum(1 for e in ev["don"] if r["t"] <= e["t"] < n["t"])
                    na = sum(1 for e in ev["ast"] if r["t"] <= e["t"] < n["t"])
                    ni = sum(1 for e in ev["itc"] if r["t"] <= e["t"] < n["t"])
                    hold["nbWindows"] += 1
                    if (n["cmds"] - r["cmds"]) - nd - na - ni <= 0:
                        hold["idleNbWindows"] += 1
    pat["R07-MT-PRE2400-HOLD"] = hold

    # ---- GOOD-SAVED-PUSH: ≤3 consecutive windows, terr +≥30% and ≥1500 px, start dens ≥ 20, no donation received in the span
    pushes = []
    for b, rows in traj.items():
        k = 0
        while k < len(rows):
            a = rows[k]
            hit = None
            if a["dens"] >= 20 and a["terr"] >= 500:
                for m in (1, 2, 3):
                    if k + m >= len(rows) or rows[k + m]["t"] - a["t"] != 90 * m:
                        break
                    c = rows[k + m]
                    gain = c["terr"] - a["terr"]
                    if gain >= max(1500, 0.3 * a["terr"]) and not any(a["t"] <= t < c["t"] for t in recv_by.get(b, [])):
                        hit = (m, c)
                        break
            if hit:
                m, c = hit
                pushes.append({"bot": b, "t0": a["t"], "t1": c["t"], "terr0": a["terr"], "terr1": c["terr"], "bal0": a["bal"], "bal1": c["bal"], "dens0": a["dens"]})
                k += m
            else:
                k += 1
    pat["R07-GOOD-SAVED-PUSH"] = {"n": len(pushes), "px": sum(x["terr1"] - x["terr0"] for x in pushes)}
    inst["R07-GOOD-SAVED-PUSH"] = pushes

    # ---- GOOD-BOXED-BOAT: boxed (nb=0&neut=0) bot gains ≥max(1000, 20%) px within 540 ticks while its boats counter rises
    boxed_boat = []
    for b, rows in traj.items():
        for k, a in enumerate(rows):
            if not (a["nb"] == 0 and a["neut"] == 0):
                continue
            c = next((x for x in rows[k + 1:] if x["t"] - a["t"] <= 540 and x["terr"] - a["terr"] >= max(1000, 0.2 * a["terr"])
                      and x.get("boats", 0) > a.get("boats", 0) and x["cmds"] >= a["cmds"]), None)
            if c:
                boxed_boat.append({"bot": b, "t0": a["t"], "t1": c["t"], "terr0": a["terr"], "terr1": c["terr"], "boats0": a.get("boats"), "boats1": c.get("boats")})
                break
    pat["R07-GOOD-BOXED-BOAT"] = {"bots": len(boxed_boat), "px": sum(x["terr1"] - x["terr0"] for x in boxed_boat)}
    inst["R07-GOOD-BOXED-BOAT"] = boxed_boat

    res["patterns"] = pat
    res["instances"] = {k: v for k, v in inst.items()}
    return res


def fmt(res):
    L = [f"== {res['matchId']} ({res['cohort']}, {res['result']}, end {res['endTick']}, teams {res['actualTeams']}) =="]
    for k, v in res["patterns"].items():
        L.append(f"  {k}: " + json.dumps({a: b for a, b in v.items() if a != 'list'}, ensure_ascii=False))
    for k, v in res["instances"].items():
        L.append(f"  [{k}] {len(v)} 例: " + "; ".join(json.dumps(x, ensure_ascii=False) for x in v[:14]) + (" …" if len(v) > 14 else ""))
    return "\n".join(L)


def main():
    if "--all" in sys.argv:
        mids = sorted(os.listdir(os.path.join(DATA, "bundles")))
        allres = []
        for mid in mids:
            try:
                allres.append(analyze(mid))
            except Exception as e:  # noqa: BLE001
                allres.append({"matchId": mid, "error": str(e)})
        os.makedirs(os.path.join(OUT, "common"), exist_ok=True)
        json.dump([{k: v for k, v in r.items() if k != "instances"} for r in allres],
                  open(os.path.join(OUT, "common", "patterns_all.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        keys = ["R07-IO-CRASH.errors", "R07-IO-CRASH.cmdsResets", "R07-IO-DUP-ASSIST.bursts", "R07-IO-DUP-ASSIST.cmds", "R07-DN-CHAIN18.pairs",
                "R07-DN-TAX51.n", "R07-DN-TAX51.allN", "R07-DN-TAX51.allAmt", "R07-DN-TAX51.allFee", "R07-DN-TAX51.rejFlag",
                "R07-EC-BOXED-RICH.snaps", "R07-EC-SOFTCAP.snaps", "R07-EC-HARDCAP.snaps", "R07-EC-IDLE-RICH.windows",
                "R07-DF-PASSIVE-BLEED.windows", "R07-DF-PASSIVE-BLEED.px", "R07-DF-RICH-BLEED.windows", "R07-DF-RICH-BLEED.px",
                "R07-DN-IDLE-RECV.denseN", "R07-DN-IDLE-RECV.staleN", "R07-AT-BIG-BURN.windows", "R07-AT-BIG-BURN.sumDrop",
                "R07-OP-BOXED-EARLY.bots", "R07-SP-CLUSTER.closeLt140", "R07-SP-CLUSTER.bots", "R07-SP-SCATTER.farGe300", "R07-SP-SCATTER.earlyGone",
                "R07-DN-PINGPONG.n", "R07-DN-PINGPONG.fee", "R07-DN-DEAD-RECV.n", "R07-DN-DEAD-RECV.fee",
                "R07-EC-NO-OUTLET.spans", "R07-EC-NO-OUTLET.snaps", "R07-EC-NO-OUTLET.maxBal1", "R07-EC-NEUT-LOCK.spans", "R07-EC-NEUT-LOCK.snaps", "R07-EC-NEUT-LOCK.maxBal1", "R07-EG-FRONT-STARVE.snaps", "R07-EG-FRONT-STARVE.px",
                "R07-MT-PRE2400-HOLD.tNeut0", "R07-MT-PRE2400-HOLD.share0", "R07-MT-PRE2400-HOLD.share2400", "R07-MT-PRE2400-HOLD.nbWindows", "R07-MT-PRE2400-HOLD.idleNbWindows",
                "R07-GOOD-SAVED-PUSH.n", "R07-GOOD-SAVED-PUSH.px", "R07-GOOD-BOXED-BOAT.bots", "R07-GOOD-BOXED-BOAT.px"]
        rows = ["\t".join(["matchId", "cohort", "result", "endTick", "teams"] + keys)]
        for r in allres:
            if "error" in r:
                rows.append(f"{r['matchId']}\tERROR {r['error']}")
                continue
            vals = []
            for k in keys:
                a, b = k.split(".")
                vals.append(str(r["patterns"].get(a, {}).get(b, "")))
            rows.append("\t".join([r["matchId"], str(r["cohort"]), str(r["result"]), str(r["endTick"]), str(r["actualTeams"])] + vals))
        open(os.path.join(OUT, "common", "patterns_all.tsv"), "w", encoding="utf-8").write("\n".join(rows) + "\n")
        print(f"wrote patterns_all.json/.tsv for {len(allres)} bundles")
        if "--print" in sys.argv:
            print("\n".join(rows))
        return
    mid = sys.argv[1]
    res = analyze(mid)
    out = ensure_out(mid)
    json.dump(res, open(os.path.join(out, "patterns.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(fmt(res))


if __name__ == "__main__":
    main()
