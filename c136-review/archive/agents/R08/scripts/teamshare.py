#!/usr/bin/env python3
"""teamshare.py — 结果行那一拍的「各队占地」和编队在队里的分量（只看日志的局也能用）。

    python3 teamshare.py <matchId> [--room N]      # 写 out/<matchId>/teamshare[_roomN].txt 并打印

数据：每条结果行（results.csv）带当拍的 team.totals（各队领土）和 alivePlayers（当拍还活着的真人数）。
编队各号的领土取结果行当拍之前最近的一条 HL-TICK（最多早 89 拍）；已经阵亡的号算 0。
节：
  [TA] 逐条结果行：拍 | 触发的号 事件 | 各队占陆地 % | 编队合计 格 / 占陆地 % | 各队里编队的格数、占该队的 % | 活着的真人数 / 其中编队号
       | 人均：编队活号 / 其它活着的真人 / 比值
  [TB] 汇总：编队在各队的人数；首末两条结果行之间各队总格数的变化里编队号贡献了多少
  [TC] 每 450 拍各队编队号的活号数、领土、余额、密度、被围数、超软上限数
口径：
  · 「其它活着的真人」= alivePlayers − 当拍活着的编队号；他们的地 = 各队合计（不含 0 队）− 编队的地。
    0 队是没有归队的地（内置 AI 的残余），不算进任何一边。
  · 结果行的 alivePlayers 是引擎在那一拍报的数；编队号是否活着按它自己的阵亡拍判断。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import facts  # noqa: E402

OUT = os.path.join(HERE, "..", "out")


def terr_at(b, t):
    if b.get("event") in ("died", "left") and b.get("deathTick") is not None and t >= b["deathTick"]:
        return 0
    prior = [s for s in b["ticks"] if s["t"] <= t]
    if not prior:
        return 0
    return prior[-1]["terr"]


def main():
    a = sys.argv[1:]
    mid = a[0]
    room = int(a[a.index("--room") + 1]) if "--room" in a else None
    suf = "" if room is None else f"_room{room}"
    F = facts.build(mid, room=room) if room is not None else facts.build(mid)
    land = F["land"]
    bots = F["bots"]
    res = sorted([r for r in F["results"] if r.get("teamTotals")], key=lambda r: r["tick"])
    seen = set()
    P = [f"[TA] {mid}{suf} 结果行当拍的各队占地与编队的分量（陆地 {land}）：拍 | 号 事件 | 各队占陆地 % | 编队 格 / % | 各队里编队 格（占该队 %）| 活着的真人 / 其中编队 | 人均 编队 / 其它 / 比值"]
    rows = []
    for r in res:
        t = r["tick"]
        if t in seen:
            continue
        seen.add(t)
        tot = {int(k): v for k, v in r["teamTotals"].items()}
        by_team = {}
        alive_sq = 0
        for b in bots.values():
            v = terr_at(b, t)
            if v > 0:
                alive_sq += 1
            by_team[b["team"]] = by_team.get(b["team"], 0) + v
        sq = sum(by_team.values())
        teams = sorted(k for k in tot if k != 0)
        own = sum(tot[k] for k in teams)
        alive = r.get("alivePlayers") or 0
        others = alive - alive_sq
        pc_sq = sq / alive_sq if alive_sq else 0
        pc_ot = (own - sq) / others if others > 0 else 0
        rows.append(dict(t=t, tot=tot, by_team=by_team, sq=sq, alive=alive, alive_sq=alive_sq, pc_sq=pc_sq, pc_ot=pc_ot))
        P.append(f"     {t} | {r['bot']} {r['event']} | " + " / ".join(f"T{k} {100 * tot[k] / land:.1f}" for k in teams) + (f" / 0 队 {tot[0]} 格" if tot.get(0) else "")
                 + f" | {sq} / {100 * sq / land:.2f} | " + "；".join(f"T{k} {by_team.get(k, 0)}（{100 * by_team.get(k, 0) / max(1, tot[k]):.1f}%）" for k in teams)
                 + f" | {alive} / {alive_sq} | {pc_sq:.0f} / {pc_ot:.0f} / {pc_sq / pc_ot if pc_ot else 0:.2f}")
    P.append("[TB] 汇总")
    cnt = {}
    for b in bots.values():
        cnt[b["team"]] = cnt.get(b["team"], 0) + 1
    P.append("     编队人数：" + "，".join(f"T{k}×{v}" for k, v in sorted(cnt.items(), key=lambda kv: str(kv[0]))) + f"；真人 {F['card'].get('seededPlayers')} 个")
    if len(rows) >= 2:
        r0, r1 = rows[0], rows[-1]
        for k in sorted(x for x in r0["tot"] if x != 0):
            d_team = r1["tot"].get(k, 0) - r0["tot"][k]
            d_sq = r1["by_team"].get(k, 0) - r0["by_team"].get(k, 0)
            P.append(f"     T{k}：t={r0['t']}→{r1['t']} 全队 {r0['tot'][k]}→{r1['tot'].get(k, 0)}（{d_team:+d}），其中编队号 {r0['by_team'].get(k, 0)}→{r1['by_team'].get(k, 0)}（{d_sq:+d}），"
                     f"队里其他人 {r0['tot'][k] - r0['by_team'].get(k, 0)}→{r1['tot'].get(k, 0) - r1['by_team'].get(k, 0)}（{d_team - d_sq:+d}）")
    P.append("[TC] 每 450 拍：各队编队号的 活号数 | 领土合计 | 余额合计 | 密度 | 被围(nb=0&neut=0)的号数（它们的余额合计）| 余额 ≥100×领土 的号数")
    all_t = sorted({s["t"] for b in bots.values() for s in b["ticks"]})
    for t in [x for x in all_t if x % 450 == 0 or x == all_t[-1]]:
        cells = []
        for k in sorted(cnt, key=str):
            g = []
            for b in bots.values():
                if b["team"] != k or (b.get("event") in ("died", "left") and b.get("deathTick") is not None and t >= b["deathTick"]):
                    continue
                prior = [s for s in b["ticks"] if s["t"] <= t]
                if prior and t - prior[-1]["t"] <= 90:
                    g.append(prior[-1])
            terr = sum(s["terr"] for s in g)
            bal = sum(s["bal"] for s in g)
            boxed = [s for s in g if s["nb"] == 0 and s["neut"] == 0]
            cells.append(f"T{k} {len(g)} | {terr} | {bal} | {bal / max(1, terr):.1f} | {len(boxed)}（{sum(s['bal'] for s in boxed)} 兵）| {sum(1 for s in g if s['bal'] >= 100 * s['terr'])}")
        P.append(f"     {t} || " + " || ".join(cells))
    with open(os.path.join(OUT, mid, f"teamshare{suf}.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(P) + "\n")
    print("\n".join(P))


if __name__ == "__main__":
    main()
