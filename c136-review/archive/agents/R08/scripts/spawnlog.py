#!/usr/bin/env python3
"""spawnlog.py — 只有日志（没有录像）时的出生点核对：只用 spawn.csv（HL-SPAWN 行）和 HL-TICK 快照。

    python3 spawnlog.py <matchId> [--room N] [--sep 145]

没有录像就看不到引擎里真正落在哪，这里看的是「每个号最后一条指派」；B049 房间 1 的录像显示最后一条不一定被执行，
所以 [SB] 的撞点只说明指派撞了，是否真的出生在一起要靠 [SA] 的早期快照（邻居数、被围的时刻）旁证。

节：
  [SA] 逐号：队 | 指派条数 / 不同的点数 | 最后一条指派 (x,y) | t≈450 / 630 / 900 的领土 | t≈630 的真人邻居数 nb / 中立边 neut |
       第一次被围（nb=0 且 neut=0）的拍 | 第一次没有中立地（neut=0）的拍 | 日志峰值领土
  [SB] 最后一条指派相距 < sep 的号对：距离 | 同队 / 异队 | 是否同一个点
  [SC] 汇总：指派条数合计、人均、撞点的号数；同一个点上的号按队列出；t=900 时领土的四分位；t≤900 就被围的号数
"""
import os
import sys
from statistics import median

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import facts  # noqa: E402
import r08lib as L  # noqa: E402


def snap_near(b, t, tol=45):
    best = None
    for s in b["ticks"]:
        if abs(s["t"] - t) <= tol and (best is None or abs(s["t"] - t) < abs(best["t"] - t)):
            best = s
    return best


def analyse(mid, room=None, sep=145.0):
    F = facts.build(mid, room=room)
    bots = F["bots"]
    rows = L.read_csv(os.path.join(L.bundle_dir(mid), "spawn.csv"))
    by_me = {}
    for r in rows:
        try:
            me = int(float(r["me"]))
            x, y = int(float(r["x"])), int(float(r["y"]))
        except (ValueError, KeyError, TypeError):
            continue
        by_me.setdefault(me, []).append(dict(x=x, y=y, line=int(float(r.get("line") or 0)), role=r.get("role"), slot=r.get("slot")))
    out = []
    for me, b in bots.items():
        sp = sorted(by_me.get(int(me), []), key=lambda d: d["line"])
        tk = b["ticks"]
        boxed = next((s["t"] for s in tk if s["nb"] == 0 and s["neut"] == 0), None)
        noneut = next((s["t"] for s in tk if s["neut"] == 0), None)
        s630 = snap_near(b, 630)
        out.append(dict(me=int(me), name=b["name"], team=b["team"], n=len(sp), distinct=len({(d["x"], d["y"]) for d in sp}),
                        last=(sp[-1]["x"], sp[-1]["y"]) if sp else None, lastLine=sp[-1]["line"] if sp else None, slot=sp[-1]["slot"] if sp else None,
                        t450=(snap_near(b, 450) or {}).get("terr"), t630=(s630 or {}).get("terr"), t900=(snap_near(b, 900) or {}).get("terr"),
                        nb630=(s630 or {}).get("nb"), neut630=(s630 or {}).get("neut"), boxedAt=boxed, noNeutAt=noneut,
                        peak=max((s["terr"] for s in tk), default=None)))
    pairs = []
    for i, a in enumerate(out):
        for c in out[i + 1:]:
            if not a["last"] or not c["last"]:
                continue
            d = ((a["last"][0] - c["last"][0]) ** 2 + (a["last"][1] - c["last"][1]) ** 2) ** 0.5
            if d < sep:
                pairs.append(dict(a=a["name"], b=c["name"], ta=a["team"], tb=c["team"], d=round(d, 1), same=a["last"] == c["last"]))
    pairs.sort(key=lambda p: p["d"])
    return F, out, pairs


def main():
    args = sys.argv[1:]
    mid = args[0]
    room = int(args[args.index("--room") + 1]) if "--room" in args else None
    sep = float(args[args.index("--sep") + 1]) if "--sep" in args else 145.0
    F, out, pairs = analyse(mid, room, sep)
    P = [f"[SA] {mid}{'' if room is None else ' 房间' + str(room)} 出生指派（只看日志）：号 队 | 指派条数 / 不同点数 | 最后一条指派 | 领土 t≈450 / 630 / 900 | t≈630 nb / neut | 第一次被围的拍 | 第一次 neut=0 的拍 | 日志峰值领土"]
    for r in sorted(out, key=lambda r: (r["team"] or 0, r["me"])):
        P.append(f"     {r['name']}({r['me']}) T{r['team']} | {r['n']} / {r['distinct']} | {r['last']} | {r['t450']} / {r['t630']} / {r['t900']} | {r['nb630']} / {r['neut630']} | "
                 f"{r['boxedAt']} | {r['noNeutAt']} | {r['peak']}")
    P.append(f"[SB] 最后一条指派相距 < {sep:.0f} 像素的号对（{len(pairs)} 对）：号 A(队) – 号 B(队) | 距离 | 同队? | 同一个点?")
    for p in pairs:
        P.append(f"     {p['a']}(T{p['ta']}) – {p['b']}(T{p['tb']}) | {p['d']} | {'同队' if p['ta'] == p['tb'] else '异队'} | {'是' if p['same'] else '否'}")
    pts = {}
    for r in out:
        if r["last"]:
            pts.setdefault(r["last"], []).append(r)
    dup = {k: v for k, v in pts.items() if len(v) > 1}
    n_tot = sum(r["n"] for r in out)
    t900 = sorted(r["t900"] for r in out if r["t900"] is not None)
    P.append(f"[SC] 汇总：指派 {n_tot} 条，人均 {n_tot / max(1, len(out)):.1f} 条；最后一条指派落在同一个点上的号 {sum(len(v) for v in dup.values())} 个（{len(dup)} 个点）")
    for k, v in dup.items():
        P.append(f"     点 {k}：" + "、".join(f"{r['name']}(T{r['team']}，t≈900 {r['t900']} 格，第一次被围 {r['boxedAt']})" for r in v))
    if t900:
        q = lambda f: t900[min(len(t900) - 1, int(f * len(t900)))]
        P.append(f"     t≈900 的领土：最小 {t900[0]}、下四分位 {q(0.25)}、中位 {median(t900):.0f}、上四分位 {q(0.75)}、最大 {t900[-1]}；合计 {sum(t900)}（占陆地 {100 * sum(t900) / F['land']:.2f}%）")
    early = [r for r in out if r["boxedAt"] is not None and r["boxedAt"] <= 900]
    P.append(f"     t≤900 就被围（nb=0 且 neut=0）的号 {len(early)} 个：" + "、".join(f"{r['name']}(T{r['team']}) t={r['boxedAt']} 当时 {r['t900']} 格" for r in early))
    e1500 = [r for r in out if r["boxedAt"] is not None and r["boxedAt"] <= 1800]
    P.append(f"     t≤1800 被围过的号 {len(e1500)} 个：" + "、".join(f"{r['name']}(T{r['team']}) t={r['boxedAt']}" for r in e1500))
    txt = "\n".join(P)
    od = os.path.join(HERE, "..", "out", mid)
    os.makedirs(od, exist_ok=True)
    suffix = "" if room is None else f"_room{room}"
    open(os.path.join(od, f"spawnlog{suffix}.txt"), "w", encoding="utf-8").write(txt + "\n")
    if "--quiet" not in args:
        print(txt)


if __name__ == "__main__":
    main()
