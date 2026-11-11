#!/usr/bin/env python3
"""40_game_digest.py — 单局机械体检（R07 v2.0）。

输入：/agent/repos/c136-data/bundles/<matchId>/ 下的 card.json / traj.csv / opening.csv / spawn.csv /
      events.csv / results.csv / anomalies.json / in_game.log。
输出：c136-review/agents/R07/out/<matchId>/digest.txt 与 digest.json。

内容：
  A 对局卡与异常计数          B 日志标签普查、策略报错区间、慢拍
  C 最终出生点几何            D 开局扩张（HL-OPENING）与 t=630/990/1530 领土
  E 全局时间线（存活=未结算的号数，logging=该拍有 HL-TICK 的号数）+ 结算时刻各队份额
  F 逐号概况（峰值、内陆围死拍数、高密度滞留拍数）
  G DROP30 对账（兵去了哪里：陆攻 / 船 / 捐款 / 被打）
  H 捐款 / 调度汇总（按捐出方、接收方；到账与手续费按引擎公式算）
  I 协防 / 拦截连发
  J 阵亡表（死前 6 个快照、死前 500 拍收支）

用法：python3 40_game_digest.py <matchId> [--print]
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict

from r07lib import (bdir, load_card, load_csv, load_events, load_log, load_results, load_traj,
                    donate_quote, base_rate, ensure_out, snap_at, quota_cap, quota_points, quota_exempt, g0)

T_RE = re.compile(r"\bt=(\d+)\b")


def main():
    mid = sys.argv[1]
    card = load_card(mid)
    land = card["mapLand"]
    traj = load_traj(mid)
    events = load_events(mid)
    results = load_results(mid)
    opening = load_csv(mid, "opening.csv")
    spawn = load_csv(mid, "spawn.csv")
    log = load_log(mid)
    anomalies = json.load(open(os.path.join(bdir(mid), "anomalies.json"), encoding="utf-8"))
    bots = sorted(traj.keys() | {r["bot"] for r in results})
    end_of = {}
    for r in results:
        end_of[r["bot"]] = r
    end_tick = card["outcome"]["endTick"]
    L = []
    J = {"matchId": mid}

    def P(s=""):
        L.append(s)

    # ---------------------------------------------------------------- A
    P(f"=== A. 对局卡 {mid} ===")
    P(json.dumps({k: card[k] for k in card if k not in ("anomaliesSummary",)}, ensure_ascii=False))
    P("anomaliesSummary: " + json.dumps(card.get("anomaliesSummary"), ensure_ascii=False))
    J["card"] = card

    # ---------------------------------------------------------------- B
    P("\n=== B. 日志普查 ===")
    tags = Counter()
    err_by_bot = defaultdict(list)
    slow = []
    last_t = None
    line_t = {}
    # 给没有 t= 的行（报错行）估一个拍号区间：取它前后最近的带 t= 的行
    ts_seq = []
    for i, (ln, bot, text) in enumerate(log):
        m = re.match(r"(\[[A-Z-]+\]|ERROR: Strategy bot stopped|\[RESULT|\[OPENING-CHECK)", text)
        tag = m.group(1) if m else text[:24]
        tags[tag] += 1
        tm = T_RE.search(text) if not text.startswith("[HL-SPAWN") else None
        ts_seq.append(int(tm.group(1)) if tm else None)
    nxt = [None] * len(log)
    cur = None
    for i in range(len(log) - 1, -1, -1):
        if ts_seq[i] is not None:
            cur = ts_seq[i]
        nxt[i] = cur
    cur = None
    for i, (ln, bot, text) in enumerate(log):
        if ts_seq[i] is not None:
            cur = ts_seq[i]
        if text.startswith("ERROR: Strategy bot stopped"):
            err_by_bot[bot].append((ln, cur, nxt[i], text[len("ERROR: Strategy bot stopped: "):][:80]))
        if text.startswith("[HL-SLOW-TICK]"):
            slow.append((ln, bot, text[:140]))
    P("标签计数: " + ", ".join(f"{k}×{v}" for k, v in tags.most_common()))
    J["tags"] = dict(tags)
    J["errors"] = {}
    if err_by_bot:
        P("策略报错（号: 条数, 首条[原始行, 前一带拍号行的 t, 后一带拍号行的 t], 末条, 报错文本）:")
        for b in sorted(err_by_bot):
            e = err_by_bot[b]
            P(f"  {b}: {len(e)} 条, 首 line{e[0][0]} t∈[{e[0][1]},{e[0][2]}], 末 line{e[-1][0]} t∈[{e[-1][1]},{e[-1][2]}], msg={Counter(x[3] for x in e).most_common(2)}")
            J["errors"][b] = {"n": len(e), "firstLine": e[0][0], "firstT": [e[0][1], e[0][2]], "lastLine": e[-1][0], "lastT": [e[-1][1], e[-1][2]],
                              "msgs": Counter(x[3] for x in e).most_common(3)}
    else:
        P("策略报错: 无")
    P(f"慢拍 HL-SLOW-TICK: {len(slow)} 条" + ("；前 6 条: " + " | ".join(f"line{a} {b} {c}" for a, b, c in slow[:6]) if slow else ""))
    J["slowTicks"] = len(slow)
    # HL-TICK 中断：每个号相邻快照间隔 > 90 的区间
    P("HL-TICK 中断（相邻快照间隔>90 拍）:")
    gaps = {}
    for b in bots:
        rows = traj.get(b, [])
        g_ = []
        for a, c in zip(rows, rows[1:]):
            if c["t"] - a["t"] > 90:
                g_.append((a["t"], c["t"]))
        died = end_of.get(b, {}).get("tick")
        lastt = rows[-1]["t"] if rows else None
        tail = None
        if rows and died and died - lastt > 90:
            tail = (lastt, died)
        gaps[b] = {"gaps": g_, "tailGap": tail, "first": rows[0]["t"] if rows else None, "last": lastt}
        if g_ or tail:
            P(f"  {b}: 中断 {g_}" + (f"；最后快照 t={lastt}，结算 t={died}（尾段 {died - lastt} 拍无快照）" if tail else ""))
    J["tickGaps"] = gaps

    # ---------------------------------------------------------------- C
    P("\n=== C. 出生点（每号最后一条 HL-SPAWN-BACKEND）===")
    final_spawn = {}
    nspawn = Counter()
    for r in spawn:
        final_spawn[r["bot"]] = r
        nspawn[r["bot"]] += 1
    pts = {b: (r["x"], r["y"]) for b, r in final_spawn.items() if isinstance(r.get("x"), (int, float))}
    J["spawn"] = {}
    for b in sorted(final_spawn):
        r = final_spawn[b]
        near = None
        if b in pts:
            ds = sorted((round(((pts[b][0] - pts[o][0]) ** 2 + (pts[b][1] - pts[o][1]) ** 2) ** 0.5), o) for o in pts if o != b)
            near = ds[:2]
        P(f"  {b}: me={r['me']} slot={r['slot']} role={r['role']} ({r['x']},{r['y']}) bossDist={r['bossDist']} minAllyDist={r['minAllyDist']} voronoi={r['voronoi']} 重算次数={nspawn[b]} 最近队友={near}")
        J["spawn"][b] = {"me": r["me"], "slot": r["slot"], "role": r["role"], "x": r["x"], "y": r["y"], "bossDist": r["bossDist"],
                         "minAllyDist": r["minAllyDist"], "voronoi": r["voronoi"], "resolves": nspawn[b], "nearest": near}
    oc = [t for (_, _, t) in log if t.startswith("[OPENING-CHECK")]
    J["openingCheck"] = None
    for t in oc[:2]:
        P("  " + t[:900])
    if oc:
        m_ = re.search(r"@ tick (\d+)", oc[0])
        terrs = [int(x) for x in re.findall(r"terr=(\d+)", oc[0])]
        if m_ and terrs:
            J["openingCheck"] = {"t": int(m_.group(1)), "n": len(terrs), "terrSum": sum(terrs), "share": round(sum(terrs) / land, 5),
                                 "terrMin": min(terrs), "terrMax": max(terrs)}
            P(f"  OPENING-CHECK 合计: t={m_.group(1)} n={len(terrs)} terrSum={sum(terrs)} 份额={100 * sum(terrs) / land:.2f}% min={min(terrs)} max={max(terrs)}")

    # ---------------------------------------------------------------- D
    P("\n=== D. 开局扩张（HL-OPENING：t/cyc/rings/spend/bal/terr）===")
    op_by = defaultdict(list)
    for r in opening:
        op_by[r["bot"]].append(r)
    J["opening"] = {}
    for b in bots:
        rows = op_by.get(b, [])
        s = " ".join(f"{r['t']}:c{r['cyc']}r{r['rings']} {r['spend']}/{r['bal']}→{r['terr']}" for r in rows)
        tr = traj.get(b, [])
        t630 = snap_at(tr, 630)
        t990 = snap_at(tr, 990)
        t1530 = snap_at(tr, 1530)
        fx = lambda s_: (s_["terr"] if s_ else None)
        P(f"  {b}: n={len(rows)} | {s}")
        P(f"      terr@630={fx(t630)} @990={fx(t990)} @1530={fx(t1530)}；首拍 t={rows[0]['t'] if rows else None}")
        J["opening"][b] = {"n": len(rows), "first": rows[0]["t"] if rows else None, "terr630": fx(t630), "terr990": fx(t990), "terr1530": fx(t1530),
                           "spendTotal": sum(r["spend"] for r in rows)}

    # ---------------------------------------------------------------- E
    P("\n=== E. 全局时间线 ===")
    all_t = sorted({r["t"] for b in traj for r in traj[b]})
    death_t = {b: end_of[b]["tick"] for b in end_of if end_of[b].get("event") in ("died", "over", "won", "left") or True}
    P("t\talive\tlogging\tsqTerr\tsqShare%\tsqBal\tsqDens\tboxed(nb=0&neut=0)\tdens>=95")
    tl = []
    for t in all_t:
        rows = [(b, r) for b in traj for r in traj[b] if r["t"] == t]
        alive = sum(1 for b in bots if death_t.get(b, 10 ** 9) > t)
        st = sum(r["terr"] for _, r in rows)
        sb = sum(r["bal"] for _, r in rows)
        boxed = sum(1 for _, r in rows if r["nb"] == 0 and r["neut"] == 0)
        hi = sum(1 for _, r in rows if r["dens"] >= 95)
        tl.append({"t": t, "alive": alive, "logging": len(rows), "sqTerr": st, "sqShare": round(st / land, 4), "sqBal": sb,
                   "sqDens": round(sb / max(1, st), 1), "boxed": boxed, "dens95": hi})
        P(f"{t}\t{alive}\t{len(rows)}\t{st}\t{100 * st / land:.2f}\t{sb}\t{sb / max(1, st):.1f}\t{boxed}\t{hi}")
    J["timeline"] = tl
    P("\n结算时刻各队领土（results.teamTotals；份额=占全图陆地）:")
    tt = []
    for r in sorted(results, key=lambda r: r["tick"]):
        tot = r["teamTotals"]
        if not tot:
            continue
        mine = r["teamMine"]
        order = sorted(tot.items(), key=lambda kv: -kv[1])
        rank = [k for k, _ in order].index(mine) + 1 if mine in tot else None
        s = " ".join(f"T{k}={100 * v / land:.1f}%" + ("*" if k == mine else "") for k, v in order)
        P(f"  t={r['tick']} {r['bot']}({r['event']}/{r['result']}) place={r['place']} alivePlayers={r['alivePlayers']} 我队T{mine} 排名{rank}/{len(tot)} | {s} | 合计{100 * sum(tot.values()) / land:.1f}%")
        tt.append({"t": r["tick"], "bot": r["bot"], "event": r["event"], "mine": mine, "rank": rank, "nTeams": len(tot),
                   "shares": {k: round(v / land, 4) for k, v in tot.items()}, "alivePlayers": r["alivePlayers"], "place": r["place"]})
    J["teamTotals"] = tt

    # ---------------------------------------------------------------- F
    P("\n=== F. 逐号概况 ===")
    J["bots"] = {}
    for b in bots:
        rows = traj.get(b, [])
        if not rows:
            continue
        pk = max(rows, key=lambda r: r["terr"])
        md = max(rows, key=lambda r: r["dens"])
        boxed = [r["t"] for r in rows if r["nb"] == 0 and r["neut"] == 0]
        boxed95 = [r["t"] for r in rows if r["nb"] == 0 and r["neut"] == 0 and r["dens"] >= 95]
        d95 = [r["t"] for r in rows if r["dens"] >= 95]
        d100 = [r["t"] for r in rows if r["dens"] >= 100]
        res = end_of.get(b, {})
        P(f"  {b}: 快照{len(rows)} 峰值terr={pk['terr']}@{pk['t']} 最高密度={md['dens']}@{md['t']} 围死快照={len(boxed)}"
          f"({boxed[0] if boxed else '-'}~{boxed[-1] if boxed else '-'}) 围死且dens>=95={len(boxed95)} dens>=95={len(d95)} dens>=100={len(d100)}"
          f" | 结算 {res.get('event')}@{res.get('tick')} place={res.get('place')} peak={res.get('peak')} lastTerr={res.get('lastTerritory')} bal={res.get('balance')} sent={res.get('sent')}/{res.get('accepted')}")
        J["bots"][b] = {"snapshots": len(rows), "peakTerr": pk["terr"], "peakT": pk["t"], "maxDens": md["dens"], "maxDensT": md["t"],
                        "boxedSnaps": len(boxed), "boxedFirst": boxed[0] if boxed else None, "boxedLast": boxed[-1] if boxed else None,
                        "boxed95": len(boxed95), "dens95": len(d95), "dens100": len(d100),
                        "end": {k: res.get(k) for k in ("event", "result", "tick", "place", "peak", "lastTerritory", "balance", "sent", "accepted")}}

    # ---------------------------------------------------------------- H (before G so G can use it)
    dons = [e for e in events if e["type"] in ("DONATE", "DISPATCH")]
    for e in dons:
        if isinstance(e.get("myBal"), (int, float)) and isinstance(e.get("pct"), (int, float)):
            amt, fee = donate_quote(int(e["myBal"]), int(e["pct"]))
            e["_amt"], e["_fee"] = amt, fee
        else:
            e["_amt"], e["_fee"] = 0, 0
        e["_allyBot"] = None
        nm = str(e.get("targetName") or "")
        for b in bots:
            if nm.endswith(b) or nm == b:
                e["_allyBot"] = b

    # ---------------------------------------------------------------- G
    P("\n=== G. DROP30 对账 ===")
    P("号 t0→t1 | bal0→bal1(跌%) | terr0→terr1 | dCmds dBoats | 区间内: 捐出n(到账+费) 收到n(估) 协防n 拦截n 开局n | 利息+地租上限 | 净支出区间=bal0+收到−捐出−费−bal1 ~ 再加收入上限 | 判别")
    J["drop30"] = []
    # anomalies.json 的 drop30Events 只保留了前 30 条（按号名排序后截断），这里直接从轨迹重算：相邻两个快照（间隔 ≤90 拍）余额下跌 ≥30%
    drop_events = []
    for b_ in sorted(traj):
        rows_ = traj[b_]
        for r0_, r1_ in zip(rows_, rows_[1:]):
            if r1_["t"] - r0_["t"] <= 90 and r0_["bal"] > 0 and r1_["bal"] <= 0.7 * r0_["bal"]:
                drop_events.append({"bot": b_, "t0": r0_["t"], "t1": r1_["t"], "dropPct": round(100 * (r0_["bal"] - r1_["bal"]) / r0_["bal"], 1)})
    P(f"（轨迹重算 {len(drop_events)} 条；对局卡 drop30Count={anomalies.get('drop30Count')}；anomalies.drop30Events 列出 {len(anomalies.get('drop30Events', []))} 条）")
    for d in drop_events:
        b, t0, t1 = d["bot"], d["t0"], d["t1"]
        rows = traj.get(b, [])
        r0 = next((r for r in rows if r["t"] == t0), None)
        r1 = next((r for r in rows if r["t"] == t1), None)
        if not r0 or not r1:
            continue
        don_out = [e for e in dons if e["bot"] == b and t0 <= e["t"] < t1]
        don_in = [e for e in dons if e["_allyBot"] == b and t0 <= e["t"] < t1]
        ast = [e for e in events if e["type"] == "ASSIST" and e["bot"] == b and t0 <= e["t"] < t1]
        itc = [e for e in events if e["type"] == "INTERCEPT" and e["bot"] == b and t0 <= e["t"] < t1]
        opn = [r for r in opening if r["bot"] == b and t0 <= r["t"] < t1]
        out_amt = sum(e["_amt"] for e in don_out)
        out_fee = sum(e["_fee"] for e in don_out)
        in_amt = sum(e["_amt"] for e in don_in)
        # 收入粗估：按 t0 的领土与余额，9 次结息 + 可能的 1 次地租（余额在区间内变化，这只是量级）
        rate = base_rate(r0["terr"], land, t0)
        inc = 0
        bal = r0["bal"]
        for k in range(t0, t1):
            if k % 10 == 9:
                i_ = g0(rate * bal, 10000)
                inc += i_
                bal += i_
            if k % 100 == 99:
                inc += r0["terr"]
                bal += r0["terr"]
        unexplained = r0["bal"] + inc + in_amt - out_amt - out_fee - r1["bal"]
        # 进攻/发船净支出的区间：下限 = 完全不计利息地租；上限 = 利息按起点余额滚满整个窗口（余额在窗口内下跌，所以这是上限）
        spend_lo = r0["bal"] + in_amt - out_amt - out_fee - r1["bal"]
        spend_hi = unexplained
        dterr = r1["terr"] - r0["terr"]
        dc = r1["cmds"] - r0["cmds"]
        dbo = r1["boats"] - r0["boats"]
        labels = []
        if out_amt + out_fee > 0.3 * (r0["bal"] - r1["bal"]):
            labels.append("捐款")
        if dbo > 0:
            labels.append("发船")
        if dterr > 0 and dc > 0:
            labels.append("陆攻扩张")
        if dterr < 0:
            labels.append("被打/失地" + ("+反击" if dc > 0 else ""))
        if dterr == 0 and dc > 0 and not labels:
            labels.append("出兵但领土不变(对攻/船/打空)")
        if not labels:
            labels.append("不明")
        P(f"  {b} {t0}→{t1} | {r0['bal']}→{r1['bal']}(-{d['dropPct']}%) | {r0['terr']}→{r1['terr']}({dterr:+d}) | dCmds={dc} dBoats={dbo} | "
          f"捐出{len(don_out)}({out_amt}+{out_fee}) 收到{len(don_in)}({in_amt}) 协防{len(ast)} 拦截{len(itc)} 开局{len(opn)}({sum(r['spend'] for r in opn)}) | 收入≤{inc} | 净支出 {spend_lo}~{spend_hi} | {'/'.join(labels)}"
          f" | nb {r0['nb']}→{r1['nb']} neut {r0['neut']}→{r1['neut']} dens {r0['dens']}→{r1['dens']}")
        J["drop30"].append({"bot": b, "t0": t0, "t1": t1, "bal0": r0["bal"], "bal1": r1["bal"], "dropPct": d["dropPct"], "terr0": r0["terr"], "terr1": r1["terr"],
                            "dCmds": dc, "dBoats": dbo, "donOutN": len(don_out), "donOutAmt": out_amt, "donOutFee": out_fee, "donInN": len(don_in), "donInAmt": in_amt,
                            "assistN": len(ast), "interceptN": len(itc), "openN": len(opn), "incomeEst": inc, "unexplained": unexplained, "spendLo": spend_lo, "spendHi": spend_hi, "labels": labels})

    # ---------------------------------------------------------------- H
    P("\n=== H. 捐款 / 调度（到账=g0(B*(pct+1),1024)，费=g0(64B,1024)，按日志 myBal 算；是否真正到账另见 30_donation_ledger.py）===")
    by_kind = Counter((e["type"], e["kind"]) for e in dons)
    P("  种类计数: " + ", ".join(f"{k[0]}/{k[1]}×{v}" for k, v in by_kind.most_common()))
    pcts = Counter(e["pct"] for e in dons)
    P("  pct 分布: " + ", ".join(f"{k}×{v}" for k, v in sorted(pcts.items(), key=lambda kv: -kv[1])[:10]))
    rej = [e for e in dons if e["likelyRejected"]]
    P(f"  预标 likelyRejected: {len(rej)}/{len(dons)}")
    out_by = defaultdict(lambda: [0, 0, 0])
    in_by = defaultdict(lambda: [0, 0])
    for e in dons:
        o = out_by[e["bot"]]
        o[0] += 1
        o[1] += e["_amt"]
        o[2] += e["_fee"]
        k = e["_allyBot"] or str(e.get("targetName"))
        in_by[k][0] += 1
        in_by[k][1] += e["_amt"]
    P("  捐出方: " + " | ".join(f"{b}: {v[0]} 笔 到账{v[1]} 费{v[2]}（费/到账={v[2] / max(1, v[1]):.2f}）" for b, v in sorted(out_by.items())))
    P("  接收方: " + " | ".join(f"{b}: {v[0]} 笔 ≈{v[1]}" for b, v in sorted(in_by.items(), key=lambda kv: -kv[1][1])))
    tot_amt = sum(e["_amt"] for e in dons)
    tot_fee = sum(e["_fee"] for e in dons)
    P(f"  合计: {len(dons)} 笔，名义到账 {tot_amt}，手续费 {tot_fee}（若全部成交；费/到账={tot_fee / max(1, tot_amt):.3f}）")
    J["donations"] = {"n": len(dons), "amt": tot_amt, "fee": tot_fee, "rejFlag": len(rej),
                      "byKind": {f"{k[0]}/{k[1]}": v for k, v in by_kind.items()},
                      "out": {b: v for b, v in out_by.items()}, "in": {b: v for b, v in in_by.items()}, "pcts": dict(pcts)}
    P("  逐笔: t 捐出方→接收方 kind pct boxedIn myBal dMe dAlly 到账 费 | 配额：上限(t) 需点数(按接收方最近快照领土) | 预标")
    J["donationRows"] = []
    for e in dons:
        rb = e["_allyBot"]
        rterr = None
        if rb and traj.get(rb):
            s_ = snap_at(traj[rb], e["t"]) or traj[rb][0]
            rterr = s_["terr"]
        pts_ = quota_points(e["t"], e["_amt"], land, rterr or 1) if rterr else None
        cap = quota_cap(e["t"])
        P(f"    {e['t']} {e['bot']}→{rb or e.get('targetName')} {e['kind']} pct={e['pct']} boxed={e['boxedIn']} myBal={e['myBal']} dMe={e['dMe']} dAlly={e['dAlly']} "
          f"到账{e['_amt']} 费{e['_fee']} | cap={cap} need={pts_}{' 免检' if quota_exempt(e['t']) else ''} recvTerr={rterr} | {'REJ?' if e['likelyRejected'] else ''} line{e['line']}")
        J["donationRows"].append({"t": e["t"], "from": e["bot"], "to": rb or e.get("targetName"), "kind": e["kind"], "pct": e["pct"], "boxedIn": e["boxedIn"],
                                  "myBal": e["myBal"], "dMe": e["dMe"], "dAlly": e["dAlly"], "amt": e["_amt"], "fee": e["_fee"], "cap": cap, "need": pts_,
                                  "exempt": quota_exempt(e["t"]), "recvTerr": rterr, "rejFlag": e["likelyRejected"], "line": e["line"]})
    # 配额累计（引擎按收方累计点数、所有捐方合计、从不清零；t>=4284 免检）。只统计我方日志里看得到的捐款，非我方队友给同一收方的点数看不到 → 这是下限。
    qcum = defaultdict(int)
    qworst = None
    qn = 0
    for r_ in sorted(J["donationRows"], key=lambda r: r["t"]):
        if r_["exempt"] or r_["need"] is None:
            continue
        qn += 1
        qcum[r_["to"]] += r_["need"]
        ratio = qcum[r_["to"]] / max(1, r_["cap"])
        if qworst is None or ratio > qworst["ratio"]:
            qworst = {"ratio": round(ratio, 3), "to": r_["to"], "t": r_["t"], "cum": qcum[r_["to"]], "cap": r_["cap"]}
    needs_ = [r_["need"] for r_ in J["donationRows"] if not r_["exempt"] and r_["need"] is not None]
    caps_ = [r_["cap"] for r_ in J["donationRows"] if not r_["exempt"]]
    J["quota"] = {"nonExemptN": qn, "exemptN": sum(1 for r_ in J["donationRows"] if r_["exempt"]), "cumByRecipient": dict(qcum), "worst": qworst,
                  "needMin": min(needs_) if needs_ else None, "needMax": max(needs_) if needs_ else None,
                  "capMin": min(caps_) if caps_ else None, "capMax": max(caps_) if caps_ else None}
    P(f"  配额累计（仅我方日志可见的捐款，下限）: 非免检 {qn} 笔、免检 {J['quota']['exemptN']} 笔；单笔需点 {J['quota']['needMin']}~{J['quota']['needMax']}，上限 {J['quota']['capMin']}~{J['quota']['capMax']}；"
      f"按收方累计 {dict(qcum)}；最紧的一刻 {qworst}")

    # ---------------------------------------------------------------- I
    P("\n=== I. 协防 / 拦截 ===")
    for typ in ("ASSIST", "INTERCEPT"):
        evs = [e for e in events if e["type"] == typ]
        P(f"  {typ}: {len(evs)} 条")
        by = defaultdict(list)
        for e in evs:
            by[e["bot"]].append(e)
        for b in sorted(by):
            # 连发：相邻 <= 6 拍
            bursts = []
            cur_ = [by[b][0]]
            for e in by[b][1:]:
                if e["t"] - cur_[-1]["t"] <= 6:
                    cur_.append(e)
                else:
                    bursts.append(cur_)
                    cur_ = [e]
            bursts.append(cur_)
            s = "; ".join(f"t{c[0]['t']}" + (f"~{c[-1]['t']}×{len(c)}" if len(c) > 1 else "") + f"→{c[0].get('target')}({str(c[0].get('targetName'))[:14]})"
                          + (f" pct={c[0].get('pct')}" if c[0].get("pct") not in (None, "") else "")
                          + (f" boat={c[0].get('boatTroops')}" if c[0].get("boatTroops") not in (None, "") else "")
                          + (f" ally={c[0].get('ally')}" if c[0].get("ally") not in (None, "") else "") for c in bursts)
            P(f"    {b}: {len(by[b])} 条, {len(bursts)} 串, 最长 {max(len(c) for c in bursts)} | {s}")
    J["assistN"] = sum(1 for e in events if e["type"] == "ASSIST")
    J["interceptN"] = sum(1 for e in events if e["type"] == "INTERCEPT")

    # ---------------------------------------------------------------- J
    P("\n=== J. 阵亡 / 结算表 ===")
    J["deaths"] = []
    for r in sorted(results, key=lambda r: r["tick"]):
        b = r["bot"]
        rows = traj.get(b, [])
        last = [x for x in rows if x["t"] <= r["tick"]][-7:]
        w0 = r["tick"] - 500
        don_out = [e for e in dons if e["bot"] == b and w0 <= e["t"] <= r["tick"]]
        don_in = [e for e in dons if e["_allyBot"] == b and w0 <= e["t"] <= r["tick"]]
        ast_for = [e for e in events if e["type"] == "ASSIST" and str(e.get("ally")) not in ("", "None") and w0 <= e["t"] <= r["tick"]
                   and (str(e.get("ally")) == str(r.get("meId")))]
        ast_by = [e for e in events if e["type"] == "ASSIST" and e["bot"] == b and w0 <= e["t"] <= r["tick"]]
        pk500 = max((x["terr"] for x in rows if w0 <= x["t"] <= r["tick"]), default=None)
        P(f"  {b} {r['event']}/{r['result']} t={r['tick']} place={r['place']} alivePlayers={r['alivePlayers']} peak={r['peak']} lastTerr={r['lastTerritory']} bal={r['balance']} sent/acc={r['sent']}/{r['accepted']}")
        P("     末段快照: " + " | ".join(f"{x['t']}:{x['terr']}/{x['bal']}/d{x['dens']}/nb{x['nb']}/ne{x['neut']}/c{x['cmds']}/b{x['boats']}" for x in last))
        P(f"     死前500拍: 领土峰值={pk500} 捐出{len(don_out)}笔({sum(e['_amt'] for e in don_out)}+费{sum(e['_fee'] for e in don_out)}) "
          f"收到{len(don_in)}笔(≈{sum(e['_amt'] for e in don_in)}, 其中REJ?{sum(1 for e in don_in if e['likelyRejected'])}) 被协防{len(ast_for)}次 自己协防别人{len(ast_by)}次")
        J["deaths"].append({"bot": b, "event": r["event"], "result": r["result"], "t": r["tick"], "place": r["place"], "peak": r["peak"], "lastTerr": r["lastTerritory"],
                            "bal": r["balance"], "last": [{k: x[k] for k in ("t", "terr", "bal", "dens", "nb", "neut", "cmds", "boats")} for x in last],
                            "peak500": pk500, "donOut500": [len(don_out), sum(e["_amt"] for e in don_out), sum(e["_fee"] for e in don_out)],
                            "donIn500": [len(don_in), sum(e["_amt"] for e in don_in), sum(1 for e in don_in if e["likelyRejected"])],
                            "assistFor500": len(ast_for), "assistBy500": len(ast_by)})

    out = ensure_out(mid)
    open(os.path.join(out, "digest.txt"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    json.dump(J, open(os.path.join(out, "digest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if "--print" in sys.argv:
        print("\n".join(L))
    else:
        print(f"wrote {out}/digest.txt ({len(L)} lines) and digest.json")


if __name__ == "__main__":
    main()
