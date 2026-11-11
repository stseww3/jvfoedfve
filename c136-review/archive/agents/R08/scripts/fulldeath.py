#!/usr/bin/env python3
"""fulldeath.py — 「满仓速死」（NEW-DF-07）的机械检出，只用日志（facts.json 的 HL-TICK 快照 + 结果行）。

口径（和 patterns_catalog.py 的 NEW-DF-07 一致）：
  · 最后一轮峰值 P：从最后一条快照往回走，领土一直不升（允许 ≤1% 的回弹）走到头的那个快照的领土；
  · 起点 S：最后一个「领土 ≥ 0.9×P」的快照；
  · 命中：S 的密度 ≥60、余额 ≥100 万，S 到阵亡拍 ≤360 拍，S 之后 cmds 增量 ≤4。
另外给出放宽口径（密度 ≥60、余额 ≥30 万、≤540 拍、cmds ≤6），以及全部阵亡号的下坡一览。

用法：python3 fulldeath.py <局> [--quiet]   产物 out/<局>/fulldeath.txt、fulldeath_sum.json
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")


def analyse(mid):
    F = json.load(open(os.path.join(OUT, mid, "facts.json"), encoding="utf-8"))
    rows = []
    for me, b in sorted(F["bots"].items(), key=lambda kv: (kv[1].get("deathTick") or 10 ** 9)):
        if b.get("event") != "died" or not b.get("ticks"):
            continue
        tk = [s for s in b["ticks"] if s["terr"] > 0]
        if len(tk) < 2:
            continue
        dt = b["deathTick"]
        k = len(tk) - 1
        while k > 0 and tk[k - 1]["terr"] * 1.01 >= tk[k]["terr"]:
            k -= 1
        # k = 最后一轮下坡的第一条；峰值取这一轮里最大的
        peak_i = max(range(k, len(tk)), key=lambda i: (tk[i]["terr"], i))
        P = tk[peak_i]["terr"]
        s_i = max(i for i in range(peak_i, len(tk)) if tk[i]["terr"] >= 0.9 * P)
        S = tk[s_i]
        last = tk[-1]
        dens = S["bal"] / max(S["terr"], 1)
        dc = last["cmds"] - S["cmds"]
        db = last["boats"] - S["boats"]
        ndon = sum(1 for d in F.get("dons", []) if str(d.get("donor")) == str(me) and S["t"] < d.get("t", -1) <= dt)
        strict = dens >= 60 and S["bal"] >= 1_000_000 and dt - S["t"] <= 360 and dc <= 4
        wide = dens >= 60 and S["bal"] >= 300_000 and dt - S["t"] <= 540 and dc <= 6
        rows.append(dict(bot=b["name"], me=b.get("me"), team=b.get("team"), deathTick=dt, peak=P, peakT=tk[peak_i]["t"], startT=S["t"], startTerr=S["terr"],
                         startBal=S["bal"], startDens=round(dens, 1), startNb=S["nb"], startNeut=S["neut"], ticksToDeath=dt - S["t"], cmds=dc, boats=db,
                         donations=ndon, lastT=last["t"], lastTerr=last["terr"], lastBal=last["bal"], strict=strict, wide=wide, line=S.get("line")))
    return rows


def main():
    mid = sys.argv[1]
    quiet = "--quiet" in sys.argv
    rows = analyse(mid)
    out = [f"[FD] {mid} 阵亡号的最后一轮下坡（只看日志）：号 | 阵亡拍 | 最后一轮峰值@拍 | 起点（最后一个领土 ≥ 峰值九成的快照）拍 / 地 / 兵 / 密度 / 敌邻 / 中立 | 起点到阵亡的拍数 | "
           "这期间 cmds 增量（其中船 / 捐款）| 末条快照 拍 / 地 / 兵 | 满仓速死（严 / 宽）| 起点行号"]
    for r in rows:
        out.append(f"    {r['bot']:<16} | {r['deathTick']} | {r['peak']}@{r['peakT']} | {r['startT']} / {r['startTerr']} / {r['startBal']} / {r['startDens']} / {r['startNb']} / {r['startNeut']} | "
                   f"{r['ticksToDeath']} | {r['cmds']}（{r['boats']} / {r['donations']}）| {r['lastT']} / {r['lastTerr']} / {r['lastBal']} | "
                   f"{'是' if r['strict'] else '否'} / {'是' if r['wide'] else '否'} | L{r['line']}")
    st = [r for r in rows if r["strict"]]
    wd = [r for r in rows if r["wide"]]
    out.append(f"  合计：阵亡 {len(rows)} 个号；严口径（密度 ≥60、余额 ≥100 万、≤360 拍、cmds ≤4）命中 {len(st)} 个，起点兵合计 {sum(r['startBal'] for r in st)}、"
               f"地合计 {sum(r['startTerr'] for r in st)}、cmds 合计 {sum(r['cmds'] for r in st)}（其中捐款 {sum(r['donations'] for r in st)}）；"
               f"宽口径（余额 ≥30 万、≤540 拍、cmds ≤6）命中 {len(wd)} 个，起点兵合计 {sum(r['startBal'] for r in wd)}、cmds 合计 {sum(r['cmds'] for r in wd)}")
    slow = [r for r in rows if r["startDens"] >= 60 and not r["wide"]]
    out.append(f"  起点密度 ≥60 但不算速死的 {len(slow)} 个：" + "；".join(f"{r['bot']}（{r['ticksToDeath']} 拍、cmds {r['cmds']}、兵 {r['startBal']}）" for r in slow))
    txt = "\n".join(out)
    od = os.path.join(OUT, mid)
    open(os.path.join(od, "fulldeath.txt"), "w", encoding="utf-8").write(txt + "\n")
    json.dump(dict(matchId=mid, deaths=len(rows), strict=[r["bot"] for r in st], wide=[r["bot"] for r in wd], rows=rows,
                   strictBal=sum(r["startBal"] for r in st), strictCmds=sum(r["cmds"] for r in st), strictDonations=sum(r["donations"] for r in st)),
              open(os.path.join(od, "fulldeath_sum.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if quiet:
        print(f"{mid}: fulldeath.txt {len(out)} 行；严 {len(st)} / 宽 {len(wd)} / 阵亡 {len(rows)}")
    else:
        print(txt)


if __name__ == "__main__":
    main()
