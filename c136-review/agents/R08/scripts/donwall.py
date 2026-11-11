#!/usr/bin/env python3
"""donwall.py — 捐款撞「受捐额度」的墙：把 donfit.py 的成交判定和引擎额度模型按行号拼起来。

    python3 donwall.py <matchId> [--room N]       # 要先跑过 donfit.py；写 out/<matchId>/donwall[_roomN].txt 并打印

口径：
  · 成交判定来自 donfit.py（EXEC / NOEXEC / AMB），不是日志里旧的 +20 拍规则。
  · 额度模型（引擎证据 B3/B4/B5，r08lib.quota_cap / quota_points）：每笔捐款按到账额折成点数，
    受捐方累计点数不得超过全场额度（初值 15，每 100 拍加 4/6/8/10）；t≥4284 不查。点数的分段：
      t<2142   2 + 到账×100 ÷ (30×(1+陆地÷300))        —— 本局陆地 40 万格时约「每 402 兵 1 点」
      t<3213   2 + 到账×100 ÷ (100×(1+陆地÷300))       —— 约「每 1341 兵 1 点」
      t≥3213   4 + 到账 ÷ 受捐方领土                   —— 受捐方越小越贵
  · 「单笔就超」= 这一笔自己的点数 > 额度（按发令拍、发令 +20 拍两种分段都超才算），不用管受捐方之前用了多少，引擎必拒。
  · 「累计超」= 受捐方已成交的点数（donfit 逐笔记的）+ 这一笔的点数 > 额度。
  · 「其它」= 两样都不超却没成交：已用点数只算得到编队号自己捐的（队里别人的捐款日志看不到，是下限），或另有原因。
  · 受捐方的领土取捐款当拍之前最近一条 HL-TICK。
节：
  [WA] 按时段：笔数 | 成交 / 没成交 / 判不了 | 没成交里 单笔就超 / 累计超 / 其它 | 到账 | 税
  [WB] 按捐出方：没成交笔数 | 其中单笔就超 | 这些单笔的点数中位数 ÷ 额度中位数 | 最长连续没成交串（笔数、起止拍）
  [WC] 按受捐方：对它的笔数 | 成交 | 没成交 | 单笔就超 / 累计超 | 第一笔成交拍 | t<4284 已用点数 | 领土范围
  [WD] 捐出方发捐款时的状态与 pct
  [WE] 额度本身给每个受捐方留的上限（纯引擎公式，不依赖拟合）
  [WF] 阵亡的编队号整局和阵亡前 600 拍收到的捐款
  [WG] 成交的捐款按受捐方当时的密度分档（≥100 = 受捐方自己已经超软上限）
"""
import collections
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import facts  # noqa: E402
import r08lib as L  # noqa: E402

OUT = os.path.join(HERE, "..", "out")
PERIODS = ((0, 2142), (2142, 3213), (3213, 4284), (4284, 10 ** 9))


def main():
    a = sys.argv[1:]
    mid = a[0]
    room = int(a[a.index("--room") + 1]) if "--room" in a else None
    suf = "" if room is None else f"_room{room}"
    F = facts.build(mid, room=room) if room is not None else facts.build(mid)
    land = F["land"]
    led = {d["line"]: d for d in facts.donation_ledger(F)}
    fit = json.load(open(os.path.join(OUT, mid, f"donfit{suf}.json"), encoding="utf-8"))["rows"]
    rows = []
    for r in fit:
        d = led.get(r["line"])
        if not d:
            continue
        rt = d.get("recvTerr") or 1
        amt_eff = d["amountEff"]
        c0 = L.quota_points(r["t"], amt_eff, land, rt)
        c1 = L.quota_points(r["t"] + 20, amt_eff, land, rt)
        cap = L.quota_cap(r["t"] + 20)
        free = r["t"] + 20 >= 4284
        rows.append(dict(t=r["t"], donor=r["donorName"], recv=r["allyName"], kind=r["kind"], pct=r["pct"], status=r["status"], amt=r.get("amt") or 0, fee=r.get("fee") or 0,
                         cost=min(c0, c1), cap=cap, free=free, solo=(not free) and min(c0, c1) > cap, pts=r.get("pts") or 0, te=r["t"] + (r.get("lagHi") or 0),
                         dMe=d.get("dMe"), boxed=bool(d.get("boxedIn")), myBal=r["myBal"], recvTerr=rt, cum=False))
    used = collections.defaultdict(int)
    evs = sorted([(r["te"], 0, i) for i, r in enumerate(rows) if r["status"] == "EXEC"] + [(r["t"] + 20, 1, i) for i, r in enumerate(rows) if r["status"] != "EXEC"])
    for _te, kind, i in evs:
        r = rows[i]
        if kind == 0:
            if r["te"] < 4284:
                used[r["recv"]] += r["pts"]
        elif r["status"] == "NOEXEC" and not r["free"] and not r["solo"]:
            r["cum"] = used[r["recv"]] + r["cost"] > r["cap"]
    P = [f"[WA] {mid}{suf} 捐款撞额度墙（{len(rows)} 笔）：时段（按发令拍；分段点 2142 / 3213 / 4284 是引擎的）| 笔数 | 成交 / 没成交 / 判不了 | 没成交里：单笔就超额度 / 累计超 / 其它 | 到账 | 税"]
    for lo, hi in PERIODS:
        g = [r for r in rows if lo <= r["t"] < hi]
        if not g:
            continue
        c = collections.Counter(r["status"] for r in g)
        solo = sum(1 for r in g if r["status"] == "NOEXEC" and r["solo"])
        cum = sum(1 for r in g if r["status"] == "NOEXEC" and r["cum"])
        P.append(f"     {lo}~{hi if hi < 10 ** 9 else '末'} | {len(g)} | {c['EXEC']} / {c['NOEXEC']} / {c['AMB']} | {solo} / {cum} / {c['NOEXEC'] - solo - cum} | "
                 f"{sum(r['amt'] for r in g if r['status'] == 'EXEC')} | {sum(r['fee'] for r in g if r['status'] == 'EXEC')}")
    ne = [r for r in rows if r["status"] == "NOEXEC"]
    pre = [r for r in rows if r["t"] < 4284]
    post = [r for r in rows if r["t"] >= 4284]
    P.append(f"     t<4284：{len(pre)} 笔，成交 {sum(1 for r in pre if r['status'] == 'EXEC')}（{100 * sum(1 for r in pre if r['status'] == 'EXEC') / max(1, len(pre)):.0f}%），"
             f"没成交 {sum(1 for r in pre if r['status'] == 'NOEXEC')}（单笔就超 {sum(1 for r in pre if r['status'] == 'NOEXEC' and r['solo'])}，累计超 {sum(1 for r in pre if r['status'] == 'NOEXEC' and r['cum'])}，"
             f"其它 {sum(1 for r in pre if r['status'] == 'NOEXEC' and not r['solo'] and not r['cum'])}），判不了 {sum(1 for r in pre if r['status'] == 'AMB')}")
    P.append(f"     t≥4284（不查额度）：{len(post)} 笔，成交 {sum(1 for r in post if r['status'] == 'EXEC')}（{100 * sum(1 for r in post if r['status'] == 'EXEC') / max(1, len(post)):.0f}%），"
             f"没成交 {sum(1 for r in post if r['status'] == 'NOEXEC')}，判不了 {sum(1 for r in post if r['status'] == 'AMB')}")
    P.append("[WB] 捐出方 | 没成交 | 其中 单笔就超 / 累计超 | 单笔就超的点数中位数 / 额度中位数 | 最长连续没成交串：笔数 起止拍")
    by = collections.defaultdict(list)
    for r in rows:
        by[r["donor"]].append(r)
    for n, g in sorted(by.items(), key=lambda kv: -sum(1 for r in kv[1] if r["status"] == "NOEXEC")):
        x = [r for r in g if r["status"] == "NOEXEC"]
        if not x:
            continue
        s = [r for r in x if r["solo"]]
        best, cur = [], []
        for r in sorted(g, key=lambda r: r["t"]):
            if r["status"] == "NOEXEC":
                cur.append(r)
                if len(cur) > len(best):
                    best = list(cur)
            elif r["status"] == "EXEC":
                cur = []
        P.append(f"     {n} | {len(x)} | {len(s)} / {sum(1 for r in x if r['cum'])} | {int(statistics.median([r['cost'] for r in s])) if s else '-'} / {int(statistics.median([r['cap'] for r in s])) if s else '-'} | "
                 f"{len(best)} 笔 {best[0]['t']}~{best[-1]['t']}")
    P.append("[WC] 受捐方 | 对它的笔数 | 成交 | 没成交 | 没成交里 单笔就超 / 累计超 | 第一笔成交拍 | t<4284 已用点数（donfit 记账）| 捐款当拍领土 最小~最大")
    by = collections.defaultdict(list)
    for r in rows:
        by[r["recv"]].append(r)
    for n, g in sorted(by.items(), key=lambda kv: -len(kv[1])):
        ex = [r for r in g if r["status"] == "EXEC"]
        x = [r for r in g if r["status"] == "NOEXEC"]
        P.append(f"     {n} | {len(g)} | {len(ex)} | {len(x)} | {sum(1 for r in x if r['solo'])} / {sum(1 for r in x if r['cum'])} | {min([r['t'] for r in ex]) if ex else '-'} | {used.get(n, 0)} | "
                 f"{min(r['recvTerr'] for r in g)}~{max(r['recvTerr'] for r in g)}")
    P.append("[WD] 捐出方发捐款时的状态")
    dm = [r["dMe"] for r in rows if r["dMe"]]
    P.append(f"     带 boxedIn 标记的 {sum(1 for r in rows if r['boxed'])} 笔；捐出方密度中位数 {statistics.median(dm) if dm else '-'}；没成交的笔里捐出方密度 >100 的 {sum(1 for r in ne if (r['dMe'] or 0) > 100)} 笔、"
             f"≥95 的 {sum(1 for r in ne if (r['dMe'] or 0) >= 95)} 笔")
    k = collections.Counter((r["kind"], r["pct"]) for r in rows)
    P.append("     种类×pct：" + "；".join(f"{a_} {b_}/1024 ×{n}" for (a_, b_), n in k.most_common(8)))
    k2 = collections.Counter((r["kind"], r["pct"]) for r in ne if r["solo"])
    P.append("     单笔就超的种类×pct：" + "；".join(f"{a_} {b_}/1024 ×{n}" for (a_, b_), n in k2.most_common(8)))
    # 没成交的笔想捐多少（发令时余额×pct，不含税）
    want = sum(L.donate_quote(r["myBal"], r["pct"])[0] for r in ne if not r["free"])
    P.append(f"     t<4284 没成交的 {sum(1 for r in ne if not r['free'])} 笔合计想捐 {want} 兵（同一笔钱每 20 拍重试一次，会重复计）；这些发令都记进了 cmds")
    uv = 1 + land // 300
    P.append(f"[WE] 额度给每个受捐方的上限（纯引擎公式；陆地 {land}，uv={uv}）")
    for t in (1500, 1700, 1900, 2100, 2141):
        cap = L.quota_cap(t)
        P.append(f"     t={t}：额度 {cap} 点 → 一个受捐方开局以来累计最多收 {(cap - 2) * 30 * uv // 100} 兵（一笔收完的话）")
    for t in (2142, 2500, 3000, 3212):
        cap = L.quota_cap(t)
        P.append(f"     t={t}：额度 {cap} 点 → 累计最多 {(cap - 2) * 100 * uv // 100} 兵")
    P.append(f"     t=3213~4283：额度每 100 拍只涨 10 点，一笔的点数 = 4 + 到账÷受捐方领土 → 已经顶着额度的受捐方每 100 拍最多再收 6×领土 兵（一笔）；"
             f"例：领土 4000 → 24000 兵，领土 15000 → 90000 兵")
    P.append(f"     t=4283 的额度 {L.quota_cap(4283)} 点；t≥4284 不查")
    P.append("[WF] 阵亡的编队号在阵亡前收到的捐款：号 | 阵亡拍 | 整局 日志笔数 → 成交 笔数 / 到账 | 阵亡前 600 拍：日志笔数 → 成交 笔数 / 到账；没成交 单笔超 / 累计超 / 其它；判不了")
    for b in sorted(F["bots"].values(), key=lambda b: b.get("deathTick") or 10 ** 9):
        if b.get("event") != "died":
            continue
        dt = b["deathTick"]
        g = [r for r in rows if r["recv"] == b["name"]]
        w = [r for r in g if dt - 600 <= r["t"] <= dt]
        ex = [r for r in g if r["status"] == "EXEC"]
        wex = [r for r in w if r["status"] == "EXEC"]
        wne = [r for r in w if r["status"] == "NOEXEC"]
        P.append(f"     {b['name']} | {dt} | {len(g)} → {len(ex)} / {sum(r['amt'] for r in ex)} | {len(w)} → {len(wex)} / {sum(r['amt'] for r in wex)}；"
                 f"{sum(1 for r in wne if r['solo'])} / {sum(1 for r in wne if r['cum'])} / {sum(1 for r in wne if not r['solo'] and not r['cum'])}；{sum(1 for r in w if r['status'] == 'AMB')}")
    P.append("[WG] 成交的捐款按受捐方当时的密度（之前最近一条快照的 余额÷领土）：档 | 笔数 | 到账 | 税")
    bn = {b["name"]: b for b in F["bots"].values()}

    def dens_at(name, t):
        b = bn.get(name)
        prior = [x for x in (b["ticks"] if b else []) if x["t"] <= t]
        return prior[-1]["bal"] / max(1, prior[-1]["terr"]) if prior else None

    band = collections.defaultdict(lambda: [0, 0, 0])
    per = collections.defaultdict(lambda: [0, 0, 0, None, None])
    for r in rows:
        if r["status"] != "EXEC":
            continue
        d = dens_at(r["recv"], r["t"])
        if d is None:
            k = "受捐方没有快照"
        else:
            k = "≥100（超软上限）" if d >= 100 else ("80~100" if d >= 80 else "<80")
        band[k][0] += 1
        band[k][1] += r["amt"]
        band[k][2] += r["fee"]
        if d is not None and d >= 100:
            x = per[r["recv"]]
            x[0] += 1
            x[1] += r["amt"]
            x[2] += r["fee"]
            x[3] = r["t"] if x[3] is None else min(x[3], r["t"])
            x[4] = r["t"] if x[4] is None else max(x[4], r["t"])
    for k in ("<80", "80~100", "≥100（超软上限）", "受捐方没有快照"):
        if k in band:
            P.append(f"     {k} | {band[k][0]} | {band[k][1]} | {band[k][2]}")
    P.append("     密度 ≥100 时收款的受捐方：号 | 笔数 | 到账 | 税 | 首末拍 | 首末拍之间的领土 前→后")
    for n, x in sorted(per.items(), key=lambda kv: -kv[1][1]):
        b = bn[n]
        t0 = [s for s in b["ticks"] if s["t"] <= x[3]]
        t1 = [s for s in b["ticks"] if s["t"] <= x[4] + 90]
        P.append(f"     {n} | {x[0]} | {x[1]} | {x[2]} | {x[3]}~{x[4]} | {t0[-1]['terr'] if t0 else '-'}→{t1[-1]['terr'] if t1 else '-'}")
    with open(os.path.join(OUT, mid, f"donwall{suf}.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(P) + "\n")
    print("\n".join(P))


if __name__ == "__main__":
    main()
