#!/usr/bin/env python3
"""quota-check.py — 受捐额度（防喂养）逐笔对账。

用法：
  python3 quota-check.py A051            # 单局汇总
  python3 quota-check.py A051 --detail   # 逐笔（成交的、没成交的）
  python3 quota-check.py                 # R03 全部对局各一行

做法：
  1. 回放里的捐款 = 真正成交的捐款（引擎在通过额度检查之后才记进回放）。
  2. 捐方是本队号时，用它最近一个快照的余额逐拍推进（利息 + 它自己在回放里的指令）得到成交那一拍的余额，
     到账 = min(floor(B·(pct+1)/1024), B − floor(64·B/1024))，再夹到受捐方硬上限余量。
  3. 每笔成交按引擎公式扣受捐方点数：t<3213 时 2 + floor(100·到账 / (k·uv))，uv = 1 + floor(全图陆地/300)，
     k = 1/4/10/30/100（分界 357/714/1071/2142）；t≥3213 时 4 + floor(100·到账 / min(100·受捐方领土, 1e9))。
     全场上限 aOY 从 15 起，每逢 t%100==99 加 4/6/8/10（分界 1071/2142/3213）。t≥4284 不再限制。
  4. 日志里发了、回放里没有的捐款：按日志里的 myBal 算它需要的点数，和当时受捐方的剩余额度比。
     需要 > 剩余 → “额度拒”；需要 ≤ 剩余 → “额度够但没成交”（丢了，或落地时条件已变）。
局限：别的真人给本队号的捐款金额未知（只知道有这一笔），该受捐方的已用点数是下界，会标 *。
"""
import sys
from collections import defaultdict

import c136lib as L


def analyze(mid, detail=False):
    rep = L.load_replay(mid)
    if rep is None:
        print(f"{mid}: 没有局内指令流，跳过")
        return
    card = L.load_card(mid)
    land = card["mapLand"]
    traj = L.load_traj(mid)
    squad = L.squad_map(mid, rep)
    name2pid = {b: p for p, b in squad.items()}
    events = L.load_events(mid)
    by_tick = L.cmds_by_tick(rep)
    end = rep["totalTicks"]
    snaps = {p: {r["t"]: r for r in traj.get(b, [])} for p, b in squad.items()}
    H = rep["humans"]

    def nm(p):
        if p in squad:
            return squad[p]
        if p < H:
            return "真人:" + str(rep["names"][p])[:14]
        return f"AI#{p}"

    state = {}
    used = defaultdict(int)
    unknown_in = defaultdict(int)
    deals = []       # (S, donor, recv, pct, amount, fee, pts, used_after, cap, donor_known)
    used_hist = defaultdict(list)  # recv -> [(S, used_after)]
    for t in range(end):
        if t % 90 == 0:
            for p in squad:
                r = snaps[p].get(t)
                if r is not None and r["terr"] > 0:
                    state[p] = [r["bal"], r["terr"]]
                elif r is None and p in state and t > max(snaps[p], default=0):
                    del state[p]
        for cid, p, a, b in by_tick.get(t, ()):
            if cid == L.CMD_DONATE:
                if p in state:
                    bal = state[p][0]
                    amount, fee = L.quote_donate(bal, a)
                    if b in state:
                        room = max(0, min(state[b][1] * L.HARD_MULT - state[b][0], L.HARD_TOP - state[b][0]))
                        amount = min(amount, room)
                    state[p][0] = bal - amount - fee
                    pts = None
                    if b in state:
                        state[b][0] += amount
                        if t < L.QUOTA_FREE_FROM:
                            pts = L.quota_points(t, amount, land, state[b][1])
                            used[b] += pts
                            used_hist[b].append((t, used[b]))
                    deals.append((t, p, b, a, amount, fee, pts, used[b] if b in squad else None, L.quota_cap(t), True))
                elif b in squad:
                    unknown_in[b] += 1
                    deals.append((t, p, b, a, None, None, None, None, L.quota_cap(t), False))
                continue
            if p not in state:
                continue
            bal = state[p][0]
            if cid == L.CMD_ATTACK:
                r0 = snaps[p].get(t - t % 90)
                if b >= L.NEUTRAL and r0 is not None and r0["neut"] == 0:
                    continue
                troops, fee = L.quote_attack(bal, a, 12)
                state[p][0] = bal - troops - fee
            elif cid == L.CMD_BOAT or (cid == L.CMD_CHASE and a != 849):
                troops, fee = L.quote_attack(bal, a, 32)
                state[p][0] = bal - troops - fee
        for p, st in state.items():
            st[0] = L.econ_tick(t, st[1], st[0], land)

    def used_at(recv, t):
        u = 0
        for s, v in used_hist[recv]:
            if s <= t:
                u = v
            else:
                break
        return u

    # 没成交的日志捐款
    rows = []
    tot = defaultdict(int)
    for p, bot in squad.items():
        logged = sorted((e["t"], e["pct"], e["target"], e["myBal"], e["kind"]) for e in events
                        if e["bot"] == bot and e["type"] in ("DISPATCH", "DONATE") and e["pct"] is not None)
        key = [(x[0], x[1], x[2]) for x in logged]
        pairs, _ = L.match_donations(key, L.batches_of(rep, p))
        matched_T = defaultdict(int)
        for S, tmin, tmax, pct, tgt in pairs:
            if tmax is not None:
                matched_T[(tmax, pct, tgt)] += 1
        tot["logged"] += len(logged)
        tot["exec"] += sum(1 for S, pp, *_ in deals if pp == p)
        for T, pct, tgt, mybal, kind in logged:
            if matched_T[(T, pct, tgt)] > 0:
                matched_T[(T, pct, tgt)] -= 1
                continue
            if mybal is None or tgt not in squad:
                tot["miss_other"] += 1
                continue
            amount, fee = L.quote_donate(mybal, pct)
            te = T + 12
            if te >= L.QUOTA_FREE_FROM:
                verdict, need, room = "额度已不限", 0, 0
                tot["miss_fit"] += 1
            else:
                r = snaps[tgt].get(te - te % 90) or {}
                terr_r = r.get("terr") or 1
                need = L.quota_points(te, amount, land, terr_r)
                room = L.quota_cap(te) - used_at(tgt, te)
                if need > room:
                    verdict = "额度拒"
                    tot["miss_quota"] += 1
                else:
                    verdict = "额度够但没成交"
                    tot["miss_fit"] += 1
            rows.append((T, bot, squad[tgt], pct, kind, mybal, amount, need, room, verdict))
    n_model = sum(1 for d in deals if d[6] is not None)
    n_viol = sum(1 for d in deals if d[6] is not None and d[7] > d[8])
    tot["model"], tot["viol"] = n_model, n_viol
    print(f"{mid} 陆地={land} uv={1 + L.g0(land, 300)} | 日志捐款 {tot['logged']} 成交 {tot['exec']}"
          f" | 未成交：额度拒 {tot['miss_quota']}，额度够但没成交 {tot['miss_fit']}，对象非本队/缺数据 {tot['miss_other']}"
          f" | 模型自检：成交且可算点数 {n_model} 笔，其中模型算出超上限的 {n_viol} 笔")
    recv_tot = defaultdict(lambda: [0, 0])
    for S, p, b, a, amount, fee, pts, ua, cap, known in deals:
        if b in squad and amount is not None:
            recv_tot[b][0] += 1
            recv_tot[b][1] += amount
    if detail:
        print("  受捐方累计：" + "；".join(
            f"{squad[b]} 收{n}笔共{amt} 已用点数{used[b]}{'*' if unknown_in[b] else ''}" for b, (n, amt) in sorted(recv_tot.items())))
        print("  -- 成交（回放）--")
        for S, p, b, a, amount, fee, pts, ua, cap, known in deals:
            if p not in squad and b not in squad:
                continue
            if known:
                extra = f"到账{amount} 费{fee}"
                if pts is not None:
                    flag = "" if ua <= cap else "  !!超上限(模型与回放不符)"
                    extra += f" 点数{pts} 受捐方累计{ua}/{cap}{flag}"
                print(f"    拍{S:5d} {nm(p)}→{nm(b)} pct={a} {extra}")
            else:
                print(f"    拍{S:5d} {nm(p)}→{nm(b)} pct={a} （捐方不是本队号，金额未知）")
        print("  -- 日志里发了但没成交 --")
        for T, bot, tgt, pct, kind, mybal, amount, need, room, verdict in sorted(rows):
            print(f"    决策拍{T:5d} {bot}→{tgt} {kind} pct={pct} myBal={mybal} 应到账{amount} 需点数{need} 剩余额度{room} → {verdict}")
    return tot


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    detail = "--detail" in sys.argv
    tots = []
    for mid in (args or L.R03_MATCHES):
        t = analyze(mid, detail)
        if t:
            tots.append(t)
    if len(tots) > 1:
        s = lambda k: sum(t[k] for t in tots)  # noqa: E731
        print(f"合计 {len(tots)} 局：日志捐款 {s('logged')}，成交 {s('exec')}，未成交 {s('logged') - s('exec')}"
              f"（额度拒 {s('miss_quota')}，额度够但没成交 {s('miss_fit')}，其他 {s('miss_other')}）；"
              f"模型自检 {s('model')} 笔，超上限 {s('viol')} 笔")


if __name__ == "__main__":
    main()
