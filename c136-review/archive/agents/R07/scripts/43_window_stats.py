#!/usr/bin/env python3
"""43_window_stats.py — 任意拍号窗口 [t0,t1] 的逐号收支小结（R07 v2.0）。

用法：python3 43_window_stats.py <matchId> <t0> <t1>
输出：每个号在窗口两端最近快照的 terr/bal/dens/cmds 变化、窗口内捐出/收到（名义到账与手续费）、协防/拦截条数，
      以及全队合计（只统计两端都有快照的号）。数字来自 traj.csv / events.csv，捐款到账与手续费按引擎公式 r07lib.donate_quote。
"""
import sys
from r07lib import load_card, load_events, load_traj, donate_quote, snap_at


def main():
    mid, t0, t1 = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    land = load_card(mid)["mapLand"]
    traj = load_traj(mid)
    ev = load_events(mid)
    dons = [e for e in ev if e["type"] in ("DONATE", "DISPATCH") and t0 <= e["t"] <= t1 and isinstance(e.get("myBal"), (int, float))]
    tot = {"terr0": 0, "terr1": 0, "bal0": 0, "bal1": 0}
    print(f"{mid} 窗口 [{t0},{t1}]")
    for b in sorted(traj):
        a = snap_at(traj[b], t0)
        c = snap_at(traj[b], t1)
        out = [e for e in dons if e["bot"] == b]
        inn = [e for e in dons if str(e.get("targetName") or "").endswith(b)]
        oa = sum(donate_quote(int(e["myBal"]), int(e["pct"]))[0] for e in out)
        of = sum(donate_quote(int(e["myBal"]), int(e["pct"]))[1] for e in out)
        ia = sum(donate_quote(int(e["myBal"]), int(e["pct"]))[0] for e in inn)
        if not a or not c or a["t"] < t0 - 90 or c["t"] < t1 - 90:
            print(f"  {b}: 两端快照不全（{a['t'] if a else None} / {c['t'] if c else None}） | 捐出{len(out)}笔 到账{oa} 费{of} | 收到{len(inn)}笔≈{ia}")
            continue
        na = sum(1 for e in ev if e["type"] == "ASSIST" and e["bot"] == b and t0 <= e["t"] <= t1)
        ni = sum(1 for e in ev if e["type"] == "INTERCEPT" and e["bot"] == b and t0 <= e["t"] <= t1)
        print(f"  {b}: t{a['t']}→t{c['t']} terr {a['terr']}→{c['terr']}({c['terr'] - a['terr']:+d}) bal {a['bal']}→{c['bal']}({c['bal'] - a['bal']:+d}) "
              f"dens {a['dens']}→{c['dens']} nb {a['nb']}→{c['nb']} dCmds={c['cmds'] - a['cmds']} | 捐出{len(out)}笔 到账{oa} 费{of} | 收到{len(inn)}笔≈{ia} | 协防{na} 拦截{ni}")
        tot["terr0"] += a["terr"]
        tot["terr1"] += c["terr"]
        tot["bal0"] += a["bal"]
        tot["bal1"] += c["bal"]
    for label, t in (("t0", t0), ("t1", t1)):
        rows = [(b, snap_at(traj[b], t)) for b in sorted(traj)]
        rows = [(b, r) for b, r in rows if r and r["t"] >= t - 90]
        sb = sum(r["bal"] for _, r in rows)
        if sb > 0:
            print(f"  兵力分布@{label}≈{t}（有快照的 {len(rows)} 个号，合计 {sb}）: " + " ".join(f"{b}={100 * r['bal'] / sb:.1f}%(d{r['dens']},nb{r['nb']})" for b, r in rows))
    amt = sum(donate_quote(int(e["myBal"]), int(e["pct"]))[0] for e in dons)
    fee = sum(donate_quote(int(e["myBal"]), int(e["pct"]))[1] for e in dons)
    print(f"  合计: terr {tot['terr0']}→{tot['terr1']}({tot['terr1'] - tot['terr0']:+d}, 份额 {100 * tot['terr0'] / land:.2f}%→{100 * tot['terr1'] / land:.2f}%) "
          f"bal {tot['bal0']}→{tot['bal1']}({tot['bal1'] - tot['bal0']:+d}) | 窗口内捐款 {len(dons)} 笔 名义到账 {amt} 手续费 {fee}")


if __name__ == "__main__":
    main()
