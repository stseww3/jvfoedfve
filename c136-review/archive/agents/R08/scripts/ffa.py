#!/usr/bin/env python3
"""ffa.py — 只用日志（facts.json 的 HL-TICK 快照 + 结果行）的几张表，给没有队伍账的局（自由混战）和录像很短的局用。

[FD] 被围的账：每个号 nb=0 且 neut=0 的快照数、最长一段的领土 / 余额 / 指令 / 船；连同对局卡的队数和整局日志捐款条数（NEW-MT-11）。
[FE] 看不见的失地：相邻两条快照都是 nb=0、neut=0、cmds 没变，领土却在掉（NEW-MT-06）。
[FG] 有录像重演产物（resim.json）时：录像末拍编队号在活着的真人里的名次、两边的领土中位、过万格的个数、前 10 名、离开的真人。

[FA] 生存梯：每个编队号出结果的那一拍，全房还活着的真人数（结果行的 alivePlayers）、其中编队号数、
     编队占活人的比例、编队占全图陆地的比例（各号 ≤ 该拍的最后一条 HL-TICK 快照相加）、
     人均比的下限 =（编队占地 ÷ 编队号数）÷（(1 − 编队占地) ÷ 其他活人数）——把编队以外的陆地全算给其他真人，所以是下限。
[FB] 出局时账上的兵：结果行的 peak / lastTerritory / balance。引擎规则：领土 ≤ 历史峰值的 1/4 就出局，余额清零。
[FC] 分段指令（HL-TICK 的 cmds / boats 计数增量）：时段 | 号·拍 | 非船指令 | 船 | 每 1000 号·拍的非船指令 | 编队占地 起→止 | 编队密度 起→止。

用法：python3 ffa.py <局> [--quiet]    产物 out/<局>/ffa.txt、ffa_sum.json
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")
PERIODS = [(0, 630), (630, 1440), (1440, 1980), (1980, 3600), (3600, 4590), (4590, 6570), (6570, 99999)]


def snap_at(b, t):
    best = None
    for s in b["ticks"]:
        if s["t"] <= t:
            best = s
        else:
            break
    return best


def gone_tick(b):
    """这个号不再算『在场』的拍：阵亡拍 / 离开拍；没有结果行的按最后一条快照 + 90 拍。"""
    if b.get("deathTick") is not None:
        return b["deathTick"]
    if b.get("leftTick") is not None:
        return b["leftTick"]
    return (b["ticks"][-1]["t"] + 90) if b.get("ticks") else 0


def analyse(mid):
    F = json.load(open(os.path.join(OUT, mid, "facts.json"), encoding="utf-8"))
    land = F["card"]["mapLand"]
    bots = [b for b in F["bots"].values() if b.get("ticks")]
    ladder = []
    for b in sorted(bots, key=lambda x: (x.get("deathTick") or x.get("leftTick") or 10 ** 9)):
        t = b.get("deathTick") or b.get("leftTick")
        if t is None or b.get("alivePlayers") is None:
            continue
        alive = b["alivePlayers"]
        if b.get("event") == "left":
            alive -= 1  # 离开的那一行里 alivePlayers 还算着它自己
        sq_alive = [x for x in bots if x is not b and gone_tick(x) > t]
        terr = 0
        bal = 0
        for x in sq_alive:
            s = snap_at(x, t)
            if s:
                terr += s["terr"]
                bal += s["bal"]
        share = terr / land
        others = alive - len(sq_alive)
        ratio = None
        if sq_alive and others > 0 and share < 1:
            ratio = (share / len(sq_alive)) / ((1 - share) / others)
        ladder.append(dict(t=t, bot=b["name"], event=b.get("event"), place=b.get("place"), alive=alive, squadAlive=len(sq_alive), squadOfAlive=(len(sq_alive) / alive if alive else None),
                           squadLandShare=share, squadTerr=terr, squadBal=bal, perHeadRatioLowerBound=ratio, line=b.get("resLine")))
    bank = []
    for b in sorted(bots, key=lambda x: (x.get("deathTick") or 10 ** 9)):
        if b.get("event") != "died":
            continue
        pk = b.get("resPeak") or 0
        lt = b.get("lastTerritory") or 0
        bank.append(dict(bot=b["name"], t=b["deathTick"], place=b.get("place"), peak=pk, lastTerr=lt, lastOverPeak=(lt / pk if pk else None), balance=b.get("resBalance") or 0,
                         dens=((b.get("resBalance") or 0) / lt if lt else None), line=b.get("resLine")))
    periods = []
    for a, z in PERIODS:
        bt = cm = bo = 0
        t0s = t1s = None
        for b in bots:
            tk = [s for s in b["ticks"] if a <= s["t"] <= z]
            if len(tk) < 2:
                continue
            bt += tk[-1]["t"] - tk[0]["t"]
            cm += tk[-1]["cmds"] - tk[0]["cmds"]
            bo += tk[-1]["boats"] - tk[0]["boats"]
        ts = sorted({s["t"] for b in bots for s in b["ticks"] if a <= s["t"] <= z})
        if not ts or bt == 0:
            continue

        def tot(t):
            te = ba = n = 0
            for b in bots:
                if gone_tick(b) <= t:
                    continue
                s = snap_at(b, t)
                if s and t - s["t"] <= 180:
                    te += s["terr"]
                    ba += s["bal"]
                    n += 1
            return te, ba, n
        te0, ba0, n0 = tot(ts[0])
        te1, ba1, n1 = tot(ts[-1])
        periods.append(dict(t0=ts[0], t1=ts[-1], botTicks=bt, nonBoat=cm - bo, boats=bo, per1000=(1000 * (cm - bo) / bt), n0=n0, n1=n1,
                            share0=te0 / land, share1=te1 / land, dens0=(ba0 / te0 if te0 else None), dens1=(ba1 / te1 if te1 else None),
                            terr0=te0, terr1=te1, bal0=ba0, bal1=ba1))
    boxed, unseen = [], []
    for b in bots:
        tk = b["ticks"]
        runs, cur = [], []
        for s in tk:
            if s["terr"] > 0 and s["nb"] == 0 and s["neut"] == 0:
                cur.append(s)
            elif cur:
                runs.append(cur)
                cur = []
        if cur:
            runs.append(cur)
        n = sum(len(r) for r in runs)
        if n:
            run = max(runs, key=lambda r: r[-1]["t"] - r[0]["t"])
            a, z = run[0], run[-1]
            boxed.append(dict(bot=b["name"], snapshots=n, runs=len(runs), t0=a["t"], t1=z["t"], terr0=a["terr"], terr1=z["terr"], bal0=a["bal"], bal1=z["bal"],
                              densMax=max(s["dens"] for s in run), cmds=z["cmds"] - a["cmds"], boats=z["boats"] - a["boats"], line0=a["line"], line1=z["line"],
                              boatsAllGame=tk[-1]["boats"]))
        wins = []
        for p, s in zip(tk, tk[1:]):
            if (s["t"] - p["t"] == 90 and p["terr"] > 0 and p["nb"] == 0 and p["neut"] == 0 and s["nb"] == 0 and s["neut"] == 0
                    and s["cmds"] == p["cmds"] and s["terr"] < p["terr"]):
                wins.append([p["t"], s["t"], p["terr"] - s["terr"]])
        if wins:
            unseen.append(dict(bot=b["name"], windows=len(wins), cells=sum(w[2] for w in wins), list=wins))
    boxed.sort(key=lambda r: -r["snapshots"])
    unseen.sort(key=lambda r: -r["cells"])
    return dict(matchId=mid, land=land, ladder=ladder, bank=bank, periods=periods,
                bankTotal=sum(r["balance"] for r in bank), bankBots=len(bank), boxed=boxed, unseen=unseen,
                donationsLogged=len(F.get("dons") or []), teamsOnCard=len(F["card"].get("teamSplitCounts") or {}), truthEnd=truth_end(mid))


def truth_end(mid):
    """有录像重演产物时：录像末拍编队号在活着的真人里的名次（按领土）、两边的中位、过万格的个数、离开的真人。"""
    p = os.path.join(OUT, mid, "resim.json")
    if not os.path.exists(p):
        return None
    R = json.load(open(p, encoding="utf-8"))
    H, names = R["H"], R["names"]
    sq = {v["id"] for k, v in R["squad"].items() if k in R["sq"]}
    terr, bal = R["snapTerr"][-1], R["snapBal"][-1]
    alive = sorted((p for p in range(H) if terr[p] > 0), key=lambda p: -terr[p])

    def med(xs):
        xs = sorted(xs)
        return None if not xs else (xs[len(xs) // 2] if len(xs) % 2 else (xs[len(xs) // 2 - 1] + xs[len(xs) // 2]) / 2)
    others = [p for p in alive if p not in sq]
    mine = [p for p in alive if p in sq]
    return dict(t=R["snapT"][-1], gameMode=R.get("gameMode"), nTeams=R.get("nTeams"), recorder=R.get("selectedPlayer"), recorderName=names[R["selectedPlayer"]] if R.get("selectedPlayer") is not None else None,
                aliveHumans=len(alive), squadAlive=len(mine), squadRanks=[alive.index(p) + 1 for p in mine],
                squadMedian=med([terr[p] for p in mine]), othersMedian=med([terr[p] for p in others]),
                squadGe10k=sum(1 for p in mine if terr[p] >= 10000), othersGe10k=sum(1 for p in others if terr[p] >= 10000),
                squadBalPerHead=(sum(bal[p] for p in mine) / len(mine) if mine else None), othersBalPerHead=(sum(bal[p] for p in others) / len(others) if others else None),
                top=[dict(p=p, name=names[p], terr=terr[p], bal=bal[p], squad=p in sq) for p in alive[:10]],
                leavers=[dict(p=p, name=names[p], t=t, squad=p in sq) for p, t in enumerate(R["leftT"][:H]) if t is not None and t >= 0],
                neverSpawned=[dict(p=p, name=names[p]) for p in range(H) if (R["deathT"][p] == 0 or R["leftT"][p] == 0)])


def main():
    mid = sys.argv[1]
    quiet = "--quiet" in sys.argv
    R = analyse(mid)
    out = [f"[FA] {mid} 生存梯（只看日志）：出结果的拍 | 号 | 结果 / 名次 | 之后全房活着的真人 | 其中编队号 | 编队占活人 % | 编队占全图陆地 %（地 / 兵）| 人均比下限 | 结果行"]
    for r in R["ladder"]:
        ratio = "–" if r["perHeadRatioLowerBound"] is None else f"{r['perHeadRatioLowerBound']:.2f}"
        soa = "–" if r["squadOfAlive"] is None else f"{100 * r['squadOfAlive']:.1f}"
        out.append(f"    {r['t']:>5} | {r['bot']:<12} | {r['event']} / {r['place']} | {r['alive']} | {r['squadAlive']} | {soa} | "
                   f"{100 * r['squadLandShare']:.2f}（{r['squadTerr']} / {r['squadBal']}）| {ratio} | L{r['line']}")
    out.append(f"[FB] 出局时账上的兵（结果行）：号 | 阵亡拍 / 名次 | 历史峰值 | 出局前最后的领土（÷ 峰值）| 出局时余额（密度）| 余额累计 | 结果行")
    cum = 0
    for r in R["bank"]:
        lop = "–" if r["lastOverPeak"] is None else f"{r['lastOverPeak']:.2f}"
        dens = "–" if r["dens"] is None else f"{r['dens']:.1f}"
        cum += r["balance"]
        out.append(f"    {r['bot']:<12} | {r['t']} / {r['place']} | {r['peak']} | {r['lastTerr']}（{lop}）| {r['balance']}（{dens}）| {cum} | L{r['line']}")
    big = [r for r in R["bank"] if r["balance"] >= 100000]
    out.append(f"    合计：阵亡 {R['bankBots']} 个号，出局时余额合计 {R['bankTotal']}；其中余额 ≥10 万的 {len(big)} 个、合计 {sum(r['balance'] for r in big)}")
    out.append("[FC] 分段指令（HL-TICK 的 cmds / boats 增量）：时段 | 号·拍 | 非船指令 | 船 | 每 1000 号·拍的非船指令 | 号数 起→止 | 编队占全图陆地 % 起→止 | 编队密度 起→止 | 编队领土 起→止 | 编队余额 起→止")
    for p in R["periods"]:
        d0 = "–" if p["dens0"] is None else f"{p['dens0']:.1f}"
        d1 = "–" if p["dens1"] is None else f"{p['dens1']:.1f}"
        out.append(f"    {p['t0']}~{p['t1']} | {p['botTicks']} | {p['nonBoat']} | {p['boats']} | {p['per1000']:.1f} | {p['n0']}→{p['n1']} | "
                   f"{100 * p['share0']:.2f}→{100 * p['share1']:.2f} | {d0}→{d1} | {p['terr0']}→{p['terr1']} | {p['bal0']}→{p['bal1']}")
    out.append(f"[FD] 被围的账（快照里 nb=0 且 neut=0；对局卡的队数 {R['teamsOnCard']}，整局日志捐款 {R['donationsLogged']} 条）："
               "号 | 被围快照数 / 段数 | 最长一段 起~止（拍数）| 领土 起→止 | 余额 起→止 | 段内最高密度 | 段内指令 / 其中船 | 整局船数 | 日志行")
    for r in R["boxed"]:
        out.append(f"    {r['bot']:<12} | {r['snapshots']} / {r['runs']} | {r['t0']}~{r['t1']}（{r['t1'] - r['t0']}）| {r['terr0']}→{r['terr1']} | {r['bal0']}→{r['bal1']} | "
                   f"{r['densMax']} | {r['cmds']} / {r['boats']} | {r['boatsAllGame']} | L{r['line0']}~L{r['line1']}")
    out.append(f"    合计：{len(R['boxed'])} 个号有过被围快照，共 {sum(r['snapshots'] for r in R['boxed'])} 个")
    out.append("[FE] 看不见的失地（相邻两条快照都是 nb=0、neut=0，cmds 没变，领土在掉）：号 | 窗数 | 掉的格 | 各窗 起~止:格")
    for r in R["unseen"]:
        out.append(f"    {r['bot']:<12} | {r['windows']} | {r['cells']} | " + "、".join(f"{a}~{z}:{c}" for a, z, c in r["list"]))
    out.append(f"    合计：{sum(r['windows'] for r in R['unseen'])} 窗 / {sum(r['cells'] for r in R['unseen'])} 格")
    te = R.get("truthEnd")
    if te:
        out.append(f"[FG] 录像末拍 t={te['t']}（真值；录像头 gameMode={te['gameMode']}、队数 {te['nTeams']}；录制号 {te['recorderName']}({te['recorder']})）："
                   f"有地的真人 {te['aliveHumans']}（含离开后留下的空壳），其中编队号 {te['squadAlive']}")
        out.append(f"    编队号按领土的名次：{te['squadRanks']}（后一半 = 名次 > {te['aliveHumans'] // 2} 的有 {sum(1 for r in te['squadRanks'] if r > te['aliveHumans'] // 2)} 个）")
        out.append(f"    领土中位：编队 {te['squadMedian']}，其他真人 {te['othersMedian']}；过 1 万格的：编队 {te['squadGe10k']} 个，其他真人 {te['othersGe10k']} 个；"
                   f"人均兵：编队 {te['squadBalPerHead']:.0f}，其他真人 {te['othersBalPerHead']:.0f}")
        out.append("    前 10 名：" + "、".join(f"{'*' if x['squad'] else ''}{x['name']} {x['terr']} 格 / {x['bal']} 兵" for x in te["top"]))
        out.append("    录像里记了『离开』的真人：" + ("、".join(f"{'*' if x['squad'] else ''}{x['name']}({x['p']}) t={x['t']}" for x in te["leavers"]) or "无"))
        out.append("    t=0 就不在的席位：" + ("、".join(f"{x['name']}({x['p']})" for x in te["neverSpawned"]) or "无"))
    os.makedirs(os.path.join(OUT, mid), exist_ok=True)
    open(os.path.join(OUT, mid, "ffa.txt"), "w", encoding="utf-8").write("\n".join(out) + "\n")
    json.dump(R, open(os.path.join(OUT, mid, "ffa_sum.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if not quiet:
        print("\n".join(out))


if __name__ == "__main__":
    main()
