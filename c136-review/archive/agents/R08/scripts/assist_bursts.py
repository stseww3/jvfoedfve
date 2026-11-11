#!/usr/bin/env python3
"""协防戳刺分串 + 超上限放兵的「连扣」拟合（只用 in_game.log，不需要录像）。

用法：python3 assist_bursts.py <matchId> [--gap 4]

依赖 out/<matchId>/facts.json（先跑 facts.py <matchId>）。

1) 协防戳刺串：同一个号的 HL-ASSIST 行，目标敌人相同、相邻两条相差 ≤gap 拍，记为一串（n 条）。
   每条戳刺是 g.attack(102, …)：按执行时余额抽 103/1024，再付 12/1024 手续费，
   n 条连扣后余额剩 (1-115/1024)^n = 0.8877^n。脚本把「只算这 n 条戳刺」的预测余额
   和该串之后第一条快照的实测余额放在一起；同一段里有捐款的，再扣 (pct+1+64)/1024。
2) 超上限放兵：段首 bal>95×terr、段内非发船指令 ≥4、余额跌 ≥60% 的快照段。
   按策略 buyLand 的规则，密度过 114.17 时单笔 = B - 手续费 - 90×领土（约 20% 余额）；
   脚本给出这笔单连扣 n-2、n-1、n 次后的预测余额，与实测对比。

输出同时写到 out/<matchId>/assist_bursts.json。
"""
import json
import os
import re
import sys

import facts

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out")
DATA = "/agent/repos/c136-data/bundles"

POKE = 103 / 1024
FEE = 12 / 1024
RELEASE_DENS = 90 / (1 - 0.2 - 12 / 1024)   # 114.17


def roll(terr, land, bal, t0, t1):
    return facts.interest_gain(terr, land, int(bal), t0, t1) if t1 > t0 else int(bal)


def main():
    mid = sys.argv[1]
    gap = int(sys.argv[sys.argv.index("--gap") + 1]) if "--gap" in sys.argv else 4
    F = json.load(open(os.path.join(OUT, mid, "facts.json"), encoding="utf-8"))
    land = F["card"]["mapLand"]
    bots = F["bots"]
    name2bot = {b["name"]: b for b in bots.values()}

    assists, dons = [], []
    for ln in open(os.path.join(DATA, mid, "in_game.log"), encoding="utf-8"):
        m = re.match(r"(\d+)\t\[(\w+)\] \[HL-ASSIST\] t=(\d+) .*?(?:enemy|target)=(\d+)\((.*?)\)(?: for ally=(\d+))?", ln)
        if m and m.group(2) in name2bot:
            assists.append(dict(line=int(m.group(1)), bot=m.group(2), t=int(m.group(3)), enemy=int(m.group(4)),
                                enemyName=m.group(5), ally=int(m.group(6)) if m.group(6) else None))
        m = re.match(r"(\d+)\t\[(\w+)\] \[HL-DONATE\] t=(\d+) .*?pct=(\d+)", ln)
        if m and m.group(2) in name2bot:
            dons.append(dict(line=int(m.group(1)), bot=m.group(2), t=int(m.group(3)), pct=int(m.group(4))))

    bursts = []
    for a in assists:
        if bursts and bursts[-1]["bot"] == a["bot"] and bursts[-1]["enemy"] == a["enemy"] and a["t"] - bursts[-1]["t1"] <= gap:
            b = bursts[-1]
            b["t1"], b["n"], b["line1"] = a["t"], b["n"] + 1, a["line"]
        else:
            bursts.append(dict(bot=a["bot"], enemy=a["enemy"], enemyName=a["enemyName"], ally=a["ally"],
                               t0=a["t"], t1=a["t"], n=1, line0=a["line"], line1=a["line"]))

    print(f"== {mid} 协防戳刺：{len(assists)} 条，{len(bursts)} 串（相邻 ≤{gap} 拍、同一敌人）==")
    for b in bursts:
        tk = name2bot[b["bot"]]["ticks"]
        before = [i for i, x in enumerate(tk) if x["t"] <= b["t0"]]
        after = [i for i, x in enumerate(tk) if x["t"] >= b["t1"] + 14]
        if not before or not after:
            b["note"] = "串前或串后没有快照"
            print(f"  {b['bot']:8s} t={b['t0']}~{b['t1']} n={b['n']} （{b['note']}）")
            continue
        i0, i1 = before[-1], after[0]
        p0, p1 = tk[i0], tk[i1]
        idle = p0["bal"]
        for j in range(i0, i1):
            idle = roll(tk[j]["terr"], land, idle, tk[j]["t"], tk[j + 1]["t"])
        # 只算戳刺：滚利息到第一条戳刺生效（约 +12 拍），连扣 n 次，再滚到快照
        t_exec = min(b["t0"] + 12, p1["t"])
        pred = roll(p0["terr"], land, p0["bal"], p0["t"], t_exec)
        for _ in range(b["n"]):
            pred = pred - pred * POKE - pred * FEE
        seg_dons = [d for d in dons if d["bot"] == b["bot"] and p0["t"] <= d["t"] < p1["t"]]
        pred_don = pred
        for d in seg_dons:
            pred_don = pred_don - pred_don * (d["pct"] + 1 + 64) / 1024
        pred = roll(p0["terr"], land, pred, t_exec, p1["t"])
        pred_don = roll(p0["terr"], land, pred_don, t_exec, p1["t"])
        b.update(snap0=p0["t"], snap1=p1["t"], bal0=p0["bal"], bal1=p1["bal"], dens0=p0["dens"], terr0=p0["terr"], terr1=p1["terr"],
                 idleBal=idle, netOut=idle - p1["bal"], predPokesOnly=pred, predWithDonations=pred_don if seg_dons else None,
                 donationsInSeg=len(seg_dons), fracByPokes=round(1 - (1 - POKE - FEE) ** b["n"], 4),
                 dcmds=p1["cmds"] - p0["cmds"])
        extra = f" 含同段 {len(seg_dons)} 笔捐款后应剩 {pred_don}" if seg_dons else ""
        print(f"  {b['bot']:8s} t={b['t0']}~{b['t1']} n={b['n']} 敌={b['enemy']}({b['enemyName'][:16]}) 友={b['ally']} | "
              f"快照 {p0['t']}→{p1['t']} 余额 {p0['bal']}→{p1['bal']} 领土 {p0['terr']}→{p1['terr']} Δcmds={b['dcmds']} | "
              f"不动应有 {idle}，净流出 {idle - p1['bal']} | 只算 {b['n']} 条戳刺（合计抽 {b['fracByPokes']:.0%}）应剩 {pred}{extra} | L{b['line0']}~L{b['line1']}")

    print(f"== {mid} 超上限放兵（段首 bal>95×terr、非发船指令 ≥4、余额跌 ≥60%）==")
    releases = []
    for b in bots.values():
        tk = b["ticks"]
        for i in range(len(tk) - 1):
            p0, p1 = tk[i], tk[i + 1]
            n = (p1["cmds"] - p0["cmds"]) - (p1["boats"] - p0["boats"])
            if p0["terr"] <= 0 or p0["bal"] <= 95 * p0["terr"] or n < 4 or p1["bal"] > 0.4 * p0["bal"]:
                continue
            if any(x["bot"] == b["name"] and p0["t"] <= x["t0"] < p1["t"] for x in bursts):
                continue        # 这一段的指令是协防戳刺，已在上面算过
            L, bal, t = p0["terr"], p0["bal"], p0["t"]
            while bal < RELEASE_DENS * L and t < p1["t"]:
                step = min(10, p1["t"] - t)
                bal = roll(L, land, bal, t, t + step)
                t += step
            fee = 12 * bal // 1024
            x = bal - fee - 90 * L
            frac = x / bal
            idle = roll(L, land, p0["bal"], p0["t"], p1["t"])
            preds = {}
            for k in (n - 2, n - 1, n):
                if k < 1:
                    continue
                r = bal
                for _ in range(k):
                    r = r - r * frac - r * FEE
                preds[k] = roll(L, land, r, min(t + 12, p1["t"]), p1["t"])
            best = min(preds, key=lambda k: abs(preds[k] - p1["bal"]))
            rec = dict(bot=b["name"], t0=p0["t"], t1=p1["t"], dens0=p0["dens"], bal0=p0["bal"], bal1=p1["bal"], terr0=p0["terr"], terr1=p1["terr"],
                       attackCmds=n, boats=p1["boats"] - p0["boats"], fireTickEst=t, firstOrder=int(x), firstOrderFrac=round(frac, 4),
                       predByN=preds, bestN=best, bestErr=round(preds[best] / p1["bal"] - 1, 4), idleBal=idle,
                       excessOverSingle=idle - p1["bal"] - int(x))
            releases.append(rec)
            print(f"  {b['name']:8s} {p0['t']}-{p1['t']} dens0={p0['dens']} 余额 {p0['bal']}→{p1['bal']} 领土 {p0['terr']}→{p1['terr']} 进攻指令 {n} 条 | "
                  f"过线拍≈{t}，单笔 {int(x)}（{frac:.1%}）| 连扣预测 " + "、".join(f"{k} 次 {v}" for k, v in preds.items()) +
                  f" | 最接近 {best} 次（{rec['bestErr']:+.1%}）| 比只执行第一条多派 {rec['excessOverSingle']}")

    json.dump(dict(match=mid, gap=gap, bursts=bursts, releases=releases),
              open(os.path.join(OUT, mid, "assist_bursts.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
