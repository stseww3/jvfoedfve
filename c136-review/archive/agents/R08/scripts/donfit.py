#!/usr/bin/env python3
"""donfit.py — 没有录像的房间里，用「余额观测序列」给每笔捐款定案：成交 / 没成交 / 定不了，并给出指令时延的区间。

    python3 donfit.py <matchId> [--room N] [--quiet] [--donor 名字]

为什么要它：facts.py 的 [G] 只看发令 20 拍后的下一条余额，时延超过 20 拍时会把「晚到」的捐款判成「被拒」。
这里把每个捐出方的全部余额观测（HL-TICK 快照 + 每条 HL-DONATE 自带的 myBal）按时间排好，逐段枚举
「这段里哪几笔在途捐款落地了」，用引擎公式（利息 E3..E7、捐款 B1：到账 floor((B*(pct+1)+0.5)/1024)、税 floor((64B+0.5)/1024)）
算期末余额，挑误差最小的组合。

口径：
  · 段 = 相邻两条观测。段内领土取两端快照的领土（两端不同就各算一遍取误差小的）。
  · 足额成交：某个组合按足额到账算，相对误差 < 4.5%（一笔捐款最少也要扣 6.25% 的税，笔数不同的组合互相差 6% 以上）。
    同一个客户端的指令按发出顺序执行，所以优先取「在途队列的队首连续 k 笔」。
  · 夹小成交：足额对不上，但队首 k≥1 笔落在「只扣税 … 足额」之间 —— 收款方快到 150 倍领土上限，到账被引擎夹小，税照扣；取最小的 k。
  · 对不上或分不清的段（段内有陆攻、发船、挨打、收款）里的在途捐款记「定不了」。
  · 归属（2026-11 改）：余额只认得出「落地了几笔、pct 多少」，认不出是哪一笔。默认先取过得了引擎受捐额度（B3/B4/B5：
    受捐方累计点数 ≤ 全场额度，t≥4284 不查）的，再取发令最晚的；--fifo 换回旧口径（在途队列队首优先，会把时延估大、把归属推给旧单）。
  · 段所在的快照窗（或前一个窗）里有陆攻 / 发船 / 协防戳刺时（cmds 增量 > 日志里的捐款条数），只留「足额对到 1.5% 以内且过得了额度」的，其余记「定不了」。
  · 一笔捐款发令后 150 拍内每一段都对得上、且都明确不含它 → 记「没成交」。
  · 收款方是本房间的编队号、结果行是 died：出局拍之后才开始的段不再把这笔捐款当候选，直接记「没成交（收款方已出局）」
    ——引擎不给已出局的玩家转兵（game.js donate L404-416），拍号是锁步模拟的服务器拍，不受客户端卡顿影响。
  · 时延区间：(最后一次确认还没落地的观测拍 − 发令拍, 第一次确认已落地的观测拍 − 发令拍]。
产物：out/<局>/donfit[_room<N>].txt 与 donfit[_room<N>].json
"""
import itertools
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import facts  # noqa: E402
import r08lib as L  # noqa: E402

TOL_FIT = 0.045     # 足额组合允许的相对误差（捐出方挨打、领土微变带来的噪声 ≈3%）
TOL_CLIP = 0.01     # 「只扣税」上界的容差
TOL_MIXED = 0.015   # 同窗有陆攻 / 发船 / 戳刺时，足额组合要对到这个精度才收（一条 10% 戳刺 ≈ 余额的 11%，和一笔捐款的 15%~33% 差得不远）
HORIZON = 150


def sim_segment(bal, t0, t1, terr, land, events, full=True):
    """从 t0 的余额 bal 滚到 t1；events = [(执行拍, pct)]，按时间执行捐款（full=False 时只扣税、到账记 0）。
    返回 (期末余额, [(到账, 税)])."""
    out = []
    t = t0
    for te, pct in sorted(events):
        te = max(t, min(te, t1))
        bal = facts.interest_gain(terr, land, bal, t, te)
        t = te
        amt, fee = L.donate_quote(bal, pct)
        if not full:
            amt = 0
        bal -= amt + fee
        out.append((amt, fee))
    return facts.interest_gain(terr, land, bal, t, t1), out


def fit_segment(bal0, t0, bal1, t1, terr_opts, land, cand, quota_ok=None):
    """枚举在途捐款 cand（按发令先后排）的子集，返回 dict(kind, sub, parts, err)。
    先定「落地了几笔」（余额只认笔数和 pct，认不出是哪一笔），再定「是哪几笔」：
      · quota_ok 给了（默认）：同样笔数、误差同档的组合里，先取过得了引擎受捐额度的，再取发令最晚的（新单先到）。
        依据：指令不落后时一笔捐款 20 拍内不是成交就是被拒；落后时成批到的单子也是新的先执行（bursts.py，有录像的局）。
      · quota_ok=None（--fifo，旧口径）：取「在途队列的队首连续 k 笔」。
    kind: 'full'  = 某个组合按足额到账算，相对误差 < TOL_FIT
          'none'  = 一笔都没落地（误差 < TOL_FIT）
          'clip'  = 足额对不上，但 k≥1 笔落在「只扣税 … 足额」之间（收款方快到 150 倍上限，到账被夹小）；取最小的 k
          'dirty' = 对不上或分不清"""
    n = len(cand)
    ev_all = {}
    for k in range(n + 1):
        for sub in itertools.combinations(range(n), k):
            rec = None
            for terr in terr_opts:
                for lag in (8, 30):
                    ev = [(max(cand[j]["t"] + lag, t0), cand[j]["pct"]) for j in sub]
                    pred, parts = sim_segment(bal0, t0, t1, terr, land, ev)
                    err = abs(pred - bal1) / max(bal1, 1)
                    feas, parts_fee, tot_v = False, None, 0
                    if k >= 1:
                        pred_fee, parts_fee = sim_segment(bal0, t0, t1, terr, land, ev, full=False)
                        feas = pred * (1 - TOL_FIT) <= bal1 <= pred_fee * (1 + TOL_CLIP)
                        tot_v = max(0, int(pred_fee - bal1))
                    if rec is None or err < rec["err"]:
                        rec = dict(err=err, sub=sub, parts=parts, feas=feas or (rec or {}).get("feas", False), parts_fee=parts_fee, tot_v=tot_v)
                    elif feas and not rec["feas"]:
                        rec["feas"], rec["parts_fee"], rec["tot_v"] = True, parts_fee, tot_v
            ev_all[sub] = rec
    is_prefix = lambda sub: sub == tuple(range(len(sub)))
    newest = lambda sub: tuple(-j for j in reversed(sub))
    exact = [r for r in ev_all.values() if r["err"] < TOL_FIT]
    if exact:
        pref = [r for r in exact if is_prefix(r["sub"])]
        pick = min(pref or exact, key=lambda r: r["err"])
        rivals = [r for r in exact if len(r["sub"]) != len(pick["sub"]) and r["err"] - pick["err"] < 0.02]
        if rivals:
            return dict(kind="dirty", sub=(), parts=[], err=pick["err"])
        if quota_ok is not None and pick["sub"]:
            alts = [r for r in exact if len(r["sub"]) == len(pick["sub"])]
            pick = min(alts, key=lambda r: (not quota_ok(r["sub"], r["parts"]), int(r["err"] / 0.02), newest(r["sub"])))
        return dict(kind="full" if pick["sub"] else "none", sub=pick["sub"], parts=pick["parts"], err=pick["err"])
    for k in range(1, n + 1):
        if quota_ok is None:
            r = ev_all[tuple(range(k))]
            if r["feas"]:
                return dict(kind="clip", sub=r["sub"], parts=[(r["tot_v"] // k, f) for _, f in r["parts_fee"]], err=r["err"])
            continue
        alts = [r for r in ev_all.values() if len(r["sub"]) == k and r["feas"]]
        if alts:
            parts_of = lambda r: [(r["tot_v"] // k, f) for _, f in r["parts_fee"]]
            r = min(alts, key=lambda r: (not quota_ok(r["sub"], parts_of(r)), newest(r["sub"])))
            return dict(kind="clip", sub=r["sub"], parts=parts_of(r), err=r["err"])
    return dict(kind="dirty", sub=(), parts=[], err=min(r["err"] for r in ev_all.values()))


class Quota:
    """引擎受捐额度（证据 B3/B4/B5）：每个受捐方累计点数 ≤ 全场额度；t≥4284 不查。只看得到编队号自己捐的，所以「已用」是下限。"""

    def __init__(self, F):
        self.F = F
        self.land = F["land"]
        self.used = defaultdict(int)
        self.conflicts = []

    def terr_at(self, ally, t):
        b = self.F["bots"].get(ally)
        if not b or not b["ticks"]:
            return None
        prior = [x for x in b["ticks"] if x["t"] <= t]
        return (prior[-1] if prior else b["ticks"][0])["terr"]

    def points(self, d, amt, t0, t1):
        """这一笔在 (t0, t1] 里成交要花的点数与当时的额度；指令时延取 14 拍（有录像的局中位 12~16 拍）。"""
        te = min(t1, max(d["t"], t0) + 14)
        if te >= 4284:
            return 0, 10 ** 9, te
        rt = self.terr_at(d["ally"], te)
        if rt is None and te >= 3213:
            return 0, 10 ** 9, te
        return L.quota_points(te, amt, self.land, rt or 1), L.quota_cap(t1), te

    def ok(self, cand, t0, t1):
        def f(sub, parts):
            tmp = defaultdict(int)
            for j, (amt, _fee) in sorted(zip(sub, parts), key=lambda x: -x[0]):
                d = cand[j]
                pts, cap, _ = self.points(d, amt, t0, t1)
                if self.used[d["ally"]] + tmp[d["ally"]] + pts > cap:
                    return False
                tmp[d["ally"]] += pts
            return True
        return f

    def book(self, d, amt, t0, t1):
        pts, cap, te = self.points(d, amt, t0, t1)
        over = self.used[d["ally"]] + pts > cap
        self.used[d["ally"]] += pts
        if over:
            self.conflicts.append((d["t"], d["donor"], d["ally"], amt, pts, self.used[d["ally"]], cap))
        return pts, over


class Donor:
    def __init__(self, me, b, dead_at=None):
        self.me = me
        self.b = b
        self.dead_at = dead_at or {}
        self.dons = sorted(b["donations"], key=lambda d: (d["t"], d["line"]))
        obs = [(s["t"], 1, s["bal"], s["terr"], None) for s in b["ticks"]]
        obs += [(d["t"], 0, d["myBal"], None, d) for d in self.dons]
        obs.sort(key=lambda o: (o[0], o[1]))
        self.obs = obs
        self.res = {id(d): dict(status="AMB", notSeenAt=d["t"], seenAt=None, amt=None, fee=None, dirty=0, clean_without=0, clip=False, pts=None, over=False, mixed=False) for d in self.dons}
        self.pending = []
        self.last_terr = None
        self.segs = []
        # 每个快照窗 (a.t, c.t] 里「不是捐款」的指令数（陆攻 / 发船 / 协防戳刺——戳刺也是一条陆攻，要花兵）：cmds 的增量 − 日志里的捐款条数
        self.win = []
        tk = b["ticks"]
        for a_, c_ in zip(tk, tk[1:]):
            nd = sum(1 for d in self.dons if a_["t"] <= d["t"] < c_["t"])
            self.win.append((a_["t"], c_["t"], (c_["cmds"] - a_["cmds"]) - nd))

    def mixed(self, t0, t1):
        """(t0, t1] 碰到的快照窗、以及它前面那个窗（指令可能晚到）里有没有别的指令。"""
        prev = 0
        for a_, c_, other in self.win:
            if a_ < t1 and c_ > t0 and (other > 0 or prev > 0):
                return True
            prev = other
        return False

    def step(self, i, land, quota):
        obs, res, pending = self.obs, self.res, self.pending
        o = obs[i]
        t1, bal1 = o[0], o[2]
        if i > 0:
            p = obs[i - 1]
            t0, bal0 = p[0], p[2]
            if t1 > t0:
                terr_opts = {x for x in (p[3], o[3]) if x}
                nxt_terr = next((x[3] for x in obs[i:] if x[3]), None)
                if not terr_opts:
                    terr_opts = {x for x in (self.last_terr, nxt_terr) if x}
                for d in list(pending):
                    dt = self.dead_at.get(d["ally"])
                    if dt is not None and t0 >= dt:
                        res[id(d)].update(status="NOEXEC", deadReceiver=True)
                        pending.remove(d)
                cand = [d for d in pending if d["t"] < t1]
                qok = quota.ok(cand, t0, t1) if quota else None
                f = fit_segment(bal0, t0, bal1, t1, terr_opts, land, cand, qok)
                # 段里（或前一个快照窗）有陆攻 / 发船：余额的落差可能是它们的，不是捐款的。
                # 只留「足额对上、且过得了额度」的；夹小的、过不了额度的一律算分不清。
                if qok is not None and f["sub"] and self.mixed(t0, t1) and (f["kind"] == "clip" or f["err"] > TOL_MIXED or not qok(f["sub"], f["parts"])):
                    f = dict(kind="dirty", sub=(), parts=[], err=f["err"])
                    for d in cand:
                        res[id(d)]["mixed"] = True
                self.segs.append(dict(t0=t0, t1=t1, bal0=bal0, bal1=bal1, nCand=len(cand), kind=f["kind"], nExec=len(f["sub"]) if f["kind"] != "dirty" else None, err=round(f["err"], 5)))
                if f["kind"] != "dirty":
                    for j, d in enumerate(cand):
                        r = res[id(d)]
                        if j in f["sub"]:
                            r["status"] = "EXEC"
                            r["clip"] = f["kind"] == "clip"
                            r["seenAt"] = t1
                            r["amt"], r["fee"] = f["parts"][f["sub"].index(j)]
                            if quota:
                                r["pts"], r["over"] = quota.book(d, r["amt"], t0, t1)
                            pending.remove(d)
                        else:
                            r["notSeenAt"] = t1
                            r["clean_without"] += 1
                else:
                    for d in cand:
                        res[id(d)]["dirty"] += 1
                for d in list(pending):
                    if t1 - d["t"] >= HORIZON:
                        r = res[id(d)]
                        r["status"] = "NOEXEC" if r["clean_without"] > 0 and r["dirty"] == 0 else "AMB"
                        pending.remove(d)
        if o[3]:
            self.last_terr = o[3]
        if o[4] is not None:
            pending.append(o[4])

    def finish(self):
        for d in self.pending:
            r = self.res[id(d)]
            dt = self.dead_at.get(d["ally"])
            if dt is not None and r["notSeenAt"] >= dt:
                r.update(status="NOEXEC", deadReceiver=True)
                continue
            r["status"] = "NOEXEC" if r["clean_without"] > 0 and r["dirty"] == 0 else "AMB"
        out = []
        for d in self.dons:
            r = self.res[id(d)]
            out.append(dict(t=d["t"], donor=d["donor"], ally=d["ally"], allyName=d["allyName"], kind=d["kind"], pct=d["pct"], myBal=d["myBal"], line=d["line"],
                            status=r["status"], clip=r["clip"], lagLo=r["notSeenAt"] - d["t"], lagHi=(r["seenAt"] - d["t"]) if r["seenAt"] is not None else None,
                            amt=r["amt"], fee=r["fee"], oldVerdict=d.get("obsVerdict"), pts=r["pts"], quotaOver=r["over"], mixed=r["mixed"], donorName=self.b["name"],
                            deadReceiver=bool(r.get("deadReceiver"))))
        return out


def analyse(mid, room=None, fifo=False):
    F = facts.full(mid, room=room)
    land = F["land"]
    quota = None if fifo else Quota(F)
    dead_at = {me: int(b["deathTick"]) for me, b in F["bots"].items() if b.get("event") == "died" and b.get("deathTick") is not None}
    donors = [Donor(me, b, dead_at) for me, b in F["bots"].items() if b["donations"]]
    # 全房间按观测拍排：额度是受捐方的累计量，要跨捐出方按时间记账
    ev = sorted((o[0], o[1], k, i) for k, dn in enumerate(donors) for i, o in enumerate(dn.obs))
    for _t, _o, k, i in ev:
        donors[k].step(i, land, quota)
    rows = []
    segs_all = {}
    for dn in donors:
        rows += dn.finish()
        segs_all[dn.b["name"]] = dn.segs
    F["_quota"] = quota
    rows.sort(key=lambda x: (x["t"], x["line"]))
    # 连发：同一个号相隔 ≤25 拍的两笔，前一笔在后一笔发令时还没落地（lagLo ≥ 间隔），且两笔都成交
    by_donor = defaultdict(list)
    for x in rows:
        by_donor[x["donor"]].append(x)
    for lst in by_donor.values():
        for a, c in zip(lst, lst[1:]):
            gap = c["t"] - a["t"]
            if gap <= 25 and a["status"] == "EXEC" and c["status"] == "EXEC" and a["lagLo"] >= gap:
                c["dupOf"] = a["t"]
    return F, rows, segs_all


def main():
    args = sys.argv[1:]
    mid = args[0]
    room = int(args[args.index("--room") + 1]) if "--room" in args else None
    donor = args[args.index("--donor") + 1] if "--donor" in args else None
    fifo = "--fifo" in args
    F, rows, segs = analyse(mid, room, fifo)
    P = []
    n = len(rows)
    ex = [x for x in rows if x["status"] == "EXEC"]
    no = [x for x in rows if x["status"] == "NOEXEC"]
    amb = [x for x in rows if x["status"] == "AMB"]
    P.append(f"[FA] {mid}{'' if room is None else ' 房间' + str(room)} 捐款定案（余额序列拟合）：日志 {n} 笔；成交 {len(ex)}，没成交 {len(no)}，定不了 {len(amb)}")
    cl = [x for x in ex if x.get("clip")]
    P.append(f"     成交的到账合计 {sum(x['amt'] for x in ex)}，税合计 {sum(x['fee'] for x in ex)}（税占捐出方付出的 {100 * sum(x['fee'] for x in ex) / max(1, sum(x['amt'] + x['fee'] for x in ex)):.1f}%）")
    P.append(f"     其中到账被收款方 150 倍上限夹小的 {len(cl)} 笔：到账 {sum(x['amt'] for x in cl)}，税 {sum(x['fee'] for x in cl)}（税占 {100 * sum(x['fee'] for x in cl) / max(1, sum(x['amt'] + x['fee'] for x in cl)):.0f}%）")
    old = defaultdict(int)
    for x in rows:
        old[(x["oldVerdict"], x["status"])] += 1
    P.append("     与 facts.py [G]「只看发令 20 拍后那条余额」的判定对照（旧判定→新定案：笔数）：" + "；".join(f"{k[0]}→{k[1]}:{v}" for k, v in sorted(old.items(), key=lambda kv: -kv[1])))
    lag_hi = sorted(x["lagHi"] for x in ex if x["lagHi"] is not None)
    lo20 = sum(1 for x in ex if x["lagLo"] >= 20)
    P.append(f"     成交的 {len(ex)} 笔里，发令 20 拍后的观测仍未扣款（时延 ≥20 拍）的 {lo20} 笔（{100 * lo20 / max(1, len(ex)):.0f}%）；时延上界 中位 {lag_hi[len(lag_hi) // 2] if lag_hi else '-'} 拍")
    dup = [x for x in rows if x.get("dupOf") is not None]
    P.append(f"     连发（同号 ≤25 拍内第二笔，发令时前一笔还没落地，两笔都成交）：{len(dup)} 笔，多付出 到账 {sum(x['amt'] for x in dup)} + 税 {sum(x['fee'] for x in dup)}")
    dead = [x for x in no if x.get("deadReceiver")]
    if dead:
        P.append(f"     没成交的 {len(no)} 笔里，收款方在这笔捐款落地前已经出局的 {len(dead)} 笔：" + "；".join(f"t={x['t']} {x['donorName']}→{x['allyName']}" for x in dead[:8]))
    P.append("[FB] 按捐出方：号 | 日志笔数 | 成交 / 没成交 / 定不了 | 到账合计 | 税合计 | 连发笔数 | 时延≥20 的成交笔数")
    by = defaultdict(list)
    for x in rows:
        by[x["donorName"]].append(x)
    for name, lst in sorted(by.items(), key=lambda kv: -len(kv[1])):
        e = [x for x in lst if x["status"] == "EXEC"]
        P.append(f"     {name:14} | {len(lst):>3} | {len(e)} / {sum(1 for x in lst if x['status'] == 'NOEXEC')} / {sum(1 for x in lst if x['status'] == 'AMB')} | {sum(x['amt'] for x in e):>9} | {sum(x['fee'] for x in e):>8} | {sum(1 for x in lst if x.get('dupOf') is not None)} | {sum(1 for x in e if x['lagLo'] >= 20)}")
    P.append("[FC] 按收款方：号 | 成交笔数 | 到账合计 | 捐出方付的税 | 首末拍")
    byr = defaultdict(list)
    for x in ex:
        byr[f"{x['allyName']}({x['ally']})"].append(x)
    for name, lst in sorted(byr.items(), key=lambda kv: -sum(x["amt"] for x in kv[1])):
        P.append(f"     {name:18} | {len(lst):>3} | {sum(x['amt'] for x in lst):>9} | {sum(x['fee'] for x in lst):>8} | {lst[0]['t']}~{lst[-1]['t']}")
    # [FE] 盈余捐款（surplus）成交后捐出方的密度：c110 L4488 的 pct 固定取 153/185/280，不受 L4386-4388 的 maxSafePct 限制
    q = F.get("_quota")
    if q is not None:
        P.append(f"[FQ] 引擎受捐额度对账（归属口径：先取过得了额度的，再取发令最晚的；--fifo 可换回旧的队首口径）：成交的 {len(ex)} 笔里记账后超出额度的 {len(q.conflicts)} 笔"
                 "（编队外队友的捐款看不到，已用点数是下限；超出 = 余额拟合和额度模型对不上，这几笔的到账额或归属存疑）")
        for c in q.conflicts[:12]:
            P.append(f"     存疑：t={c[0]} {F['bots'][c[1]]['name']}→{F['bots'][c[2]]['name'] if c[2] in F['bots'] else c[2]} 到账 {c[3]}，折 {c[4]} 点，累计 {c[5]} > 额度 {c[6]}")
        P.append("     受捐方 | t<2142 成交 笔数 / 到账 / 点数 | 2142~3212 | 3213~4283 | t≥4284 笔数 / 到账（不查额度）| t=4283 累计点数（额度 " + str(L.quota_cap(4283)) + "）")
        byq = defaultdict(list)
        for x in ex:
            byq[x["allyName"]].append(x)
        for name, lst in sorted(byq.items(), key=lambda kv: -sum(x["amt"] for x in kv[1])):
            def cell(lo, hi):
                g = [x for x in lst if lo <= x["t"] + (x["lagHi"] or 0) < hi]
                return g
            a1, a2, a3, a4 = cell(0, 2142), cell(2142, 3213), cell(3213, 4284), cell(4284, 10 ** 9)
            P.append(f"     {name:14} | {len(a1)} / {sum(x['amt'] for x in a1)} / {sum(x['pts'] or 0 for x in a1)} | {len(a2)} / {sum(x['amt'] for x in a2)} / {sum(x['pts'] or 0 for x in a2)} | "
                     f"{len(a3)} / {sum(x['amt'] for x in a3)} / {sum(x['pts'] or 0 for x in a3)} | {len(a4)} / {sum(x['amt'] for x in a4)} | {sum(x['pts'] or 0 for x in a1 + a2 + a3)}")
    P.append("[FE] 盈余捐款成交后的密度（捐后余额 = 发令时余额 − 到账 − 税；连发的第二笔再减去第一笔）：号 | 成交笔数 | 发令时密度 中位 | 捐后密度 中位 / 最低 | 捐后 <68 的笔数 | 捐后 <55 的笔数")
    bots_by_name = {b["name"]: b for b in F["bots"].values()}
    fe = defaultdict(list)
    prev_out = {}
    for x in rows:
        if x["status"] != "EXEC" or not x["kind"].startswith("surplus"):
            continue
        b = bots_by_name.get(x["donorName"])
        s0 = None
        for sn in (b["ticks"] if b else []):
            if sn["t"] <= x["t"]:
                s0 = sn
        if not s0 or s0["terr"] <= 0:
            continue
        extra = prev_out.get((x["donorName"], x.get("dupOf")), 0) if x.get("dupOf") is not None else 0
        after = (x["myBal"] - x["amt"] - x["fee"] - extra) / s0["terr"]
        x["densBefore"] = round(x["myBal"] / s0["terr"], 1)
        x["densAfter"] = round(after, 1)
        prev_out[(x["donorName"], x["t"])] = x["amt"] + x["fee"]
        fe[x["donorName"]].append(x)
    for name, lst in sorted(fe.items(), key=lambda kv: -len(kv[1])):
        db = sorted(v["densBefore"] for v in lst)
        da = sorted(v["densAfter"] for v in lst)
        P.append(f"     {name:14} | {len(lst):>3} | {db[len(db) // 2]} | {da[len(da) // 2]} / {da[0]} | {sum(1 for v in da if v < 68)} | {sum(1 for v in da if v < 55)}")
    P.append("[FD] 逐笔：拍 捐出→收款 类型 pct | 发令时余额 | 定案 | 时延区间(拍) | 到账 / 税 | 旧判定 | 连发")
    for x in rows:
        if donor and x["donorName"] != donor:
            continue
        lag = f"({x['lagLo']},{x['lagHi']}]" if x["lagHi"] is not None else f"(>{x['lagLo']})"
        P.append(f"     {x['t']:>5} {x['donorName']}→{x['allyName']}({x['ally']}) {x['kind'].replace(' donate', '')} {x['pct']} | {x['myBal']} | {x['status']}{'(夹小)' if x.get('clip') else ''}{'(收款方已出局)' if x.get('deadReceiver') else ''} | {lag} | {x['amt']} / {x['fee']} | {x['oldVerdict']} | {'连发@' + str(x['dupOf']) if x.get('dupOf') is not None else ''} L{x['line']}")
    txt = "\n".join(P)
    suffix = "" if room is None else f"_room{room}"
    od = os.path.join(HERE, "..", "out", mid)
    os.makedirs(od, exist_ok=True)
    if not donor:
        open(os.path.join(od, f"donfit{suffix}.txt"), "w", encoding="utf-8").write(txt + "\n")
        json.dump(dict(rows=rows, segs=segs), open(os.path.join(od, f"donfit{suffix}.json"), "w", encoding="utf-8"), ensure_ascii=False)
    if "--quiet" not in args:
        print(txt)
    else:
        print("\n".join(P[:6]))


if __name__ == "__main__":
    main()
