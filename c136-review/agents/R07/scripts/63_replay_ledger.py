#!/usr/bin/env python3
"""63_replay_ledger.py — R07：有录像的局（A 组）的「执行层」精确账本。

用法：python3 63_replay_ledger.py <matchId> [--detail]
输入：
  /agent/repos/c136-data/bundles/<matchId>/in_game.log（策略日志；行号 = 文件内第几行，记作 L<n>）
  out/<matchId>/cmds.tsv       （统筹的 replay_cmds.mjs 解出的「引擎已接受」指令流）
  out/<matchId>/truth_cmd.tsv  （60_truth.cjs：每条我方指令前后的真实余额）
  out/<matchId>/truth_bots.tsv （60_truth.cjs：我方每号每 10 拍的 领土/余额/状态）
输出（stdout + out/<matchId>/replay_ledger.txt / .json）：
  A. 每个号被引擎接受的指令数（按种类）、首末拍、离开拍、最后一条日志拍
  B. 捐款/调度：日志条数 vs 引擎执行条数；逐笔执行（真实到账、手续费、延迟、受捐方配额点数/累计/上限）
  C. 没被执行的日志捐款：按「即使受捐方从没收过钱也超上限」/「超剩余额度」/「免检期仍没执行」分类
  D. 顶格：每号余额 >= 150×领土（硬上限）与 >= 100×领土（软上限）的时长（10 拍采样）
  E. 同拍多条指令（清仓批）：同一号同一拍被接受 >=3 条指令，列出前后余额
口径：
  到账 = min(g0(B*(pct+1),1024), B-费)，费 = g0(64*B,1024)，B = 指令执行前一拍的真实余额（truth_cmd 的 bal_0）；
  配额点数/上限按引擎原文 [B3][B4][B5]（r07lib.quota_points / quota_cap / quota_exempt），累计只算录像里出现的捐款
  （含非我方队友捐给我方号的；友军登陆占用的额度录像命令流里看不出来，所以累计是下限）。
"""
import csv
import json
import os
import re
import sys
from collections import defaultdict

from r07lib import attack_quote, DATA, OUT, g0, load_card, quota_cap, quota_exempt, quota_points

RE_DIS = re.compile(r"\[HL-DISPATCH\] t=(\d+) (\w+) pct=(\d+)/1024 -> ally=(\d+)\(([^)]*)\) boxedIn=(true|false) myBal=(\d+) dMe=(-?\d+) dAlly=(-?\d+)")
RE_DON = re.compile(r"\[HL-DONATE\] t=(\d+) ([a-z ]+?) pct=(\d+)/1024 -> (?:boss|ally)=(\d+)\(([^)]*)\)(?: boxedIn=(true|false))? myBal=(\d+) dMe=(-?\d+)")
RE_TICK = re.compile(r"\[HL-TICK\] t=(\d+)")
RE_BOT = re.compile(r"^\d+\t\[([A-Za-z0-9_]+)\] (.*)$", re.S)


def load_tsv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def main():
    mid = sys.argv[1]
    detail = "--detail" in sys.argv
    out = os.path.join(OUT, mid)
    card = load_card(mid)
    land = card["mapLand"]
    cmds = load_tsv(os.path.join(out, "cmds.tsv"))
    tcmd = load_tsv(os.path.join(out, "truth_cmd.tsv"))
    bots = load_tsv(os.path.join(out, "truth_bots.tsv"))
    players = load_tsv(os.path.join(out, "truth_players.tsv"))
    squad = {int(r["p"]): r["squad"] for r in players if r["squad"]}
    pname = {int(r["p"]): r["name"] for r in players}
    lines = []
    P = lines.append
    J = {"matchId": mid}

    # ---- 日志
    logs = []  # dict(line, bot, t, kind, pct, to, toName, boxed, myBal, dMe, dAlly)
    last_log = {}
    with open(os.path.join(DATA, "bundles", mid, "in_game.log"), encoding="utf-8") as f:
        for n, ln in enumerate(f, 1):
            m = RE_BOT.match(ln.rstrip("\n"))
            if not m:
                continue
            bot, text = m.group(1), m.group(2)
            mt = RE_TICK.search(text)
            if mt:
                last_log[bot] = max(last_log.get(bot, 0), int(mt.group(1)))
            md = RE_DIS.search(text)
            if md:
                logs.append(dict(line=n, bot=bot, t=int(md.group(1)), kind=md.group(2), pct=int(md.group(3)), to=int(md.group(4)),
                                 toName=md.group(5), boxed=md.group(6) == "true", myBal=int(md.group(7)), dMe=int(md.group(8)), dAlly=int(md.group(9))))
                continue
            md = RE_DON.search(text)
            if md:
                logs.append(dict(line=n, bot=bot, t=int(md.group(1)), kind=md.group(2).strip().replace(" ", "_"), pct=int(md.group(3)), to=int(md.group(4)),
                                 toName=md.group(5), boxed=md.group(6) == "true", myBal=int(md.group(7)), dMe=int(md.group(8)), dAlly=None))

    # ---- A. 指令种类
    P(f"=== {mid} 执行层账本（录像命令流 + 真引擎余额）===")
    P("A. 引擎接受的指令（每号）：种类×条数 | 首拍~末拍 | 离开拍 | 最后一条 HL-TICK 日志拍")
    per = defaultdict(lambda: defaultdict(int))
    first, last, leave = {}, {}, {}
    for c in cmds:
        p = int(c["player"])
        if p not in squad:
            continue
        t = int(c["tick"])
        k = c["kind"]
        if k.startswith("leave"):
            leave[p] = t
            continue
        per[p][k] += 1
        if t >= 0:
            first.setdefault(p, t)
            last[p] = t
    J["cmdKinds"] = {}
    for p in sorted(squad, key=lambda x: squad[x]):
        b = squad[p]
        kinds = " ".join(f"{k}×{v}" for k, v in sorted(per[p].items()))
        ingame = sum(v for k, v in per[p].items() if k != "spawn")
        P(f"  {b}#{p}: {kinds} | 局内 {ingame} 条 {first.get(p)}~{last.get(p)} | 离开 {leave.get(p, '-')} | 末条日志 {last_log.get(b, '-')}")
        J["cmdKinds"][b] = {"kinds": dict(per[p]), "inGame": ingame, "first": first.get(p), "last": last.get(p), "leave": leave.get(p), "lastLog": last_log.get(b)}

    # ---- B. 捐款执行
    don = [r for r in tcmd if r["kind"] == "donate"]
    cum = defaultdict(int)
    execs = []
    for r in don:
        T = int(r["tick"])
        p, to, pct = int(r["p"]), int(r["b"]), int(r["a"])
        b0 = int(float(r["bal_0"])) if r["bal_0"] != "" else None
        b1 = int(float(r["bal_p1"])) if r["bal_p1"] != "" else None
        fee = g0(64 * b0, 1024)
        amt = max(0, min(g0(b0 * (pct + 1), 1024), b0 - fee))
        tterr = int(float(r["tterr"])) if r["tterr"] != "" else 0
        tb0 = int(float(r["tbal_m1"])) if r["tbal_m1"] != "" else None
        tb1 = int(float(r["tbal_p1"])) if r["tbal_p1"] != "" else None
        exempt = quota_exempt(T)
        need = quota_points(T, amt, land, tterr)
        cap = quota_cap(T + 1)
        before = cum[to]
        if not exempt:
            cum[to] += need
        execs.append(dict(T=T, p=p, donor=squad.get(p, pname.get(p, str(p))), to=to, toName=squad.get(to, pname.get(to, str(to))), pct=pct, bal0=b0, bal1=b1,
                          amt=amt, fee=fee, tterr=tterr, tbal0=tb0, tbal1=tb1, need=need, cumBefore=before, cap=cap, exempt=exempt, mine=p in squad))
    # 配对：每条执行记录 ← 同号、同 pct、同对象、t<=T 的「最近一条还没配上的日志」
    used = set()
    for e in execs:
        if not e["mine"]:
            continue
        cand = [l for l in logs if l["bot"] == e["donor"] and l["pct"] == e["pct"] and l["to"] == e["to"] and l["t"] <= e["T"] and l["line"] not in used]
        if cand:
            l = max(cand, key=lambda x: x["t"])
            used.add(l["line"])
            e["logT"], e["logLine"], e["lag"], e["kind"] = l["t"], l["line"], e["T"] - l["t"], l["kind"]
    mine_exec = [e for e in execs if e["mine"]]
    P("")
    P(f"B. 捐款/调度：日志 {len(logs)} 条，引擎执行 {len(mine_exec)} 条（{100 * len(mine_exec) / max(1, len(logs)):.1f}%）；另有非我方号捐给我方号 {len(execs) - len(mine_exec)} 条")
    tot_amt = sum(e["amt"] for e in mine_exec)
    tot_fee = sum(e["fee"] for e in mine_exec)
    P(f"   我方执行合计：到账 {tot_amt}，手续费 {tot_fee}（费/到账 = {tot_fee / max(1, tot_amt):.3f}）")
    J_split = {}
    for nm, sel in (("有配额期（t<4284）", [e for e in mine_exec if not e["exempt"]]), ("免检期（t>=4284）", [e for e in mine_exec if e["exempt"]])):
        if not sel:
            continue
        a, f = sum(e["amt"] for e in sel), sum(e["fee"] for e in sel)
        pcts = sorted(e["pct"] for e in sel)
        P(f"     其中{nm}：{len(sel)} 笔，pct {pcts[0]}~{pcts[-1]}，到账 {a}，手续费 {f}（费/到账 = {f / max(1, a):.3f}）；单笔到账 {min(e['amt'] for e in sel)}~{max(e['amt'] for e in sel)}，单笔费 {min(e['fee'] for e in sel)}~{max(e['fee'] for e in sel)}")
        J_split[nm] = {"n": len(sel), "amt": a, "fee": f}
    P("   逐笔：执行拍 捐出方→受捐方 pct | 执行前余额→后 | 到账 费 | 受捐方领土 余额前→后 | 配额 需点/累计前/上限 | 对应日志 t(延迟) L行 种类")
    for e in execs:
        q = "免检" if e["exempt"] else f"{e['need']}/{e['cumBefore']}/{e['cap']}"
        lg = f"t={e.get('logT')}(+{e.get('lag')}) L{e.get('logLine')} {e.get('kind')}" if e.get("logLine") else "(无日志)"
        P(f"   {e['T']} {e['donor']}→{e['toName']} pct={e['pct']} | {e['bal0']}→{e['bal1']} | {e['amt']} {e['fee']} | {e['tterr']} {e['tbal0']}→{e['tbal1']} | {q} | {lg}")
    J["donations"] = {"logged": len(logs), "executed": len(mine_exec), "execAmt": tot_amt, "execFee": tot_fee, "split": J_split, "execs": execs}
    by_donor = defaultdict(lambda: [0, 0, 0, 0])
    for l in logs:
        by_donor[l["bot"]][0] += 1
    for e in mine_exec:
        x = by_donor[e["donor"]]
        x[1] += 1
        x[2] += e["amt"]
        x[3] += e["fee"]
    P("   每号：" + "；".join(f"{b} 日志 {v[0]} 执行 {v[1]} 到账 {v[2]} 费 {v[3]}" for b, v in sorted(by_donor.items())))
    J["donations"]["byDonor"] = {b: {"logged": v[0], "executed": v[1], "amt": v[2], "fee": v[3]} for b, v in by_donor.items()}

    # ---- C. 没执行的日志捐款分类
    P("")
    lags = [e["lag"] for e in mine_exec if e.get("lag") is not None]
    lag0, lag1 = (min(lags), max(lags)) if lags else (7, 17)
    lag0, lag1 = min(lag0, 7), max(lag1, 12)
    P(f"C. 没被执行的日志捐款（落地拍未知：对「发令拍 + {lag0}~{lag1} 拍」里的每一拍都算一遍需点 / 上限 / 累计——这个范围取自本局已执行捐款的实测延迟；表里的需点、上限取 +12 拍那一档）")
    cls = defaultdict(list)
    exec_sorted = sorted(execs, key=lambda e: e["T"])
    bots_by = defaultdict(dict)
    for r in bots:
        bots_by[r["bot"]][int(r["t"])] = r
    for l in logs:
        if l["line"] in used:
            continue
        fee = g0(64 * l["myBal"], 1024)
        amt = max(0, min(g0(l["myBal"] * (l["pct"] + 1), 1024), l["myBal"] - fee))
        recv = squad.get(l["to"])

        def at(T):
            rr = bots_by.get(recv, {}).get((T // 10) * 10) if recv else None
            rterr = int(rr["terr"]) if rr else 0
            need = quota_points(T, amt, land, rterr)
            cap = quota_cap(T + 1)
            c_lt = sum(e["need"] for e in exec_sorted if e["to"] == l["to"] and e["T"] < T and not e["exempt"])
            c_le = sum(e["need"] for e in exec_sorted if e["to"] == l["to"] and e["T"] <= T and not e["exempt"])
            return need, cap, c_lt, c_le, rterr, (rr["alive"] == "1" if rr else None)

        win = [at(T) for T in range(l["t"] + lag0, l["t"] + lag1 + 1)]
        need, cap, c0, _c1, rterr, ralive = at(l["t"] + 12)
        if all(quota_exempt(T) for T in range(l["t"] + lag0, l["t"] + lag1 + 1)):
            k = "免检期仍未执行"
        elif all(w[0] > w[1] for w in win):
            k = "单笔需点 > 全场上限（受捐方即使从没收过也过不了）"
        elif all(w[2] + w[0] > w[1] for w in win):
            k = "需点 > 剩余额度（累计已用）"
        elif all(w[3] + w[0] > w[1] for w in win):
            k = "需点 > 剩余额度（要么撞上换档前的贵价，要么额度被同拍先到的另一笔用掉）"
        else:
            k = "按下限账算得过却没执行（延迟/余额变化/友军登陆占额/其他）"
        cls[k].append(dict(l, amt=amt, fee=fee, need=need, cap=cap, cum=c0, recvTerr=rterr, recvAlive=ralive))
    J["notExecuted"] = {}
    for k, v in sorted(cls.items(), key=lambda kv: -len(kv[1])):
        ts = [x["t"] for x in v]
        P(f"   {k}: {len(v)} 条，t={min(ts)}~{max(ts)}，名义到账合计 {sum(x['amt'] for x in v)}；需点 {min(x['need'] for x in v)}~{max(x['need'] for x in v)}，上限 {min(x['cap'] for x in v)}~{max(x['cap'] for x in v)}")
        J["notExecuted"][k] = {"n": len(v), "t0": min(ts), "t1": max(ts), "amt": sum(x["amt"] for x in v), "needMin": min(x["need"] for x in v), "needMax": max(x["need"] for x in v)}
        if detail:
            for x in v:
                P(f"      L{x['line']} t={x['t']} {x['bot']}→{x['toName']} {x['kind']} pct={x['pct']} myBal={x['myBal']} 到账 {x['amt']} 需点 {x['need']} 累计 {x['cum']} 上限 {x['cap']} dMe={x['dMe']} dAlly={x['dAlly']}")

    # ---- D. 顶格时长
    P("")
    P("D. 顶格时长（10 拍采样；在场且没离开的拍）：硬上限 = 余额 >= 150×领土-1；软上限以上 = 余额 >= 100×领土")
    J["caps"] = {}
    for b in sorted(bots_by):
        rows = [r for r in bots_by[b].values() if r["alive"] == "1" and r["state"] != "2" and int(r["terr"]) > 0]
        hard = [int(r["t"]) for r in rows if int(r["bal"]) >= 150 * int(r["terr"]) - 1]
        soft = [int(r["t"]) for r in rows if int(r["bal"]) >= 100 * int(r["terr"])]
        if not soft:
            continue
        P(f"  {b}: 硬上限 {len(hard) * 10} 拍" + (f"（{min(hard)}~{max(hard)}）" if hard else "") + f"；软上限以上 {len(soft) * 10} 拍（{min(soft)}~{max(soft)}）")
        J["caps"][b] = {"hardTicks": len(hard) * 10, "hard0": min(hard) if hard else None, "hard1": max(hard) if hard else None,
                        "softTicks": len(soft) * 10, "soft0": min(soft), "soft1": max(soft)}

    # ---- E. 同拍多条指令
    P("")
    P("E. 同一号同一拍被接受 >=3 条指令（清仓批）：拍 号 条数 | 指令(种类 pct→目标) | 批前余额 → 批后余额")
    grp = defaultdict(list)
    for r in tcmd:
        if int(r["p"]) in squad:
            grp[(int(r["tick"]), int(r["p"]))].append(r)
    batches = []
    for (T, p), rs in sorted(grp.items()):
        if len(rs) < 3:
            continue
        b0 = int(float(rs[0]["bal_0"])) if rs[0]["bal_0"] != "" else None
        b1 = int(float(rs[0]["bal_p1"])) if rs[0]["bal_p1"] != "" else None
        desc = " ".join(f"{r['kind']} {r['a']}→{r['target'] or r['b']}" for r in rs)
        # 整数对账：批里哪几条真的扣了款？按录像顺序和反序各试一遍，枚举「扣款的子集」，找批后余额一格不差的组合
        fit = None
        if b0 is not None and b1 is not None and len(rs) <= 12 and all(r["kind"] in ("attack", "donate") for r in rs):
            best = None
            for order_name, seq in (("反序", list(reversed(rs))), ("正序", list(rs))):
                n = len(seq)
                for mask in range(1 << n):
                    B = b0
                    fee_sum = tr_sum = 0
                    for i in range(n):
                        if not (mask >> i) & 1:
                            continue
                        r = seq[i]
                        if r["kind"] == "attack":
                            tr, fee = attack_quote(B, int(r["a"]))
                        else:
                            tr, fee = donate_quote(B, int(r["a"]))
                        B -= tr + fee
                        fee_sum += fee
                        tr_sum += tr
                    if B == b1:
                        k = bin(mask).count("1")
                        cand = (k, order_name, fee_sum, tr_sum)
                        if best is None or k > best[0]:
                            best = cand
                if best:
                    break
            fit = best
        fit_txt = f" | 整数对账：{fit[0]} 条扣了款（{fit[1]}），手续费合计 {fit[2]}，发出的兵合计 {fit[3]}" if fit else (" | 整数对账：无精确解（批内另有利息/挨打）" if b0 != b1 else " | 余额没变：全部未生效")
        P(f"  {T} {squad[p]} ×{len(rs)} | {desc[:200]} | {b0} → {b1}{fit_txt}")
        batches.append(dict(T=T, bot=squad[p], n=len(rs), bal0=b0, bal1=b1, paidN=fit[0] if fit else None, feeSum=fit[2] if fit else None, troopSum=fit[3] if fit else None))
    if not batches:
        P("  （无）")
    J["batches"] = batches

    txt = "\n".join(lines) + "\n"
    with open(os.path.join(out, "replay_ledger.txt"), "w") as f:
        f.write(txt)
    with open(os.path.join(out, "replay_ledger.json"), "w") as f:
        json.dump(J, f, ensure_ascii=False, indent=1)
    sys.stdout.write(txt)


if __name__ == "__main__":
    main()
