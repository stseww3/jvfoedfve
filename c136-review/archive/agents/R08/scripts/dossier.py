#!/usr/bin/env python3
"""dossier.py — 阵亡号的死因卷宗（真值）：写死因之前逐号核对用。

    python3 dossier.py <matchId> [名字 ...] [--span 1500] [--quiet]     # 不给名字 = 全部阵亡的编队号；写 out/<matchId>/dossier.txt

每个号一段：
  [1] 峰值、阵亡拍、阵亡前 span 拍里每 150 拍：地、兵、密度、身上的兵（来源）、在外的兵、接壤（前 4）
  [2] 整局逐个进攻者的账（按拿走的格数）：首末拍、窗数、拿走的格、对方耗兵（每格）、这个号被打掉的余额；这个号对它的陆攻 / 船：条数、派出的兵、拿回的格
  [3] 阵亡前 span 拍里的已执行指令：按类型计数、最后一条的拍、同拍 ≥3 条的批；最长的『没有任何陆攻 / 船』空窗
  [4] 阵亡前 span 拍里收到的捐款（真值）：笔数、到账；捐出的：笔数、到账、税
  [5] 一拍掉 ≥40% 余额的时刻（阵亡前 span 拍）：拍、余额 前→后、同拍指令
"""
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from truth import Truth, NEUTRAL, OUT  # noqa: E402


def top_nb(T, o, t):
    best = None
    for tt, lst in o["nb"]:
        if tt <= t:
            best = lst
        else:
            break
    return best or []


def main():
    argv = sys.argv[1:]
    quiet = "--quiet" in argv
    span = 1500
    if "--span" in argv:
        span = int(argv[argv.index("--span") + 1])
    args = [a for i, a in enumerate(argv) if not a.startswith("--") and (i == 0 or argv[i - 1] != "--span")]
    mid = args[0]
    T = Truth(mid)
    R = T.R
    names = args[1:] or [n for n, p in sorted(T.squad.items(), key=lambda kv: T.deathT[kv[1]]) if T.deathT[p] >= 0]
    out = []
    summ = []
    for name in names:
        me = T.squad[name]
        o = T.sq_of(name)
        dt = T.deathT[me] if T.deathT[me] >= 0 else T.end
        t0 = max(0, dt - span)
        peak, peakT = 0, 0
        for i, t in enumerate(T.snapT):
            v = R["snapTerr"][i][me]
            if v > peak:
                peak, peakT = v, t
        out.append(f"== {name}({me}) T{T.team(me)}：峰值 {peak} 格 @{peakT}；阵亡 {T.deathT[me]}；离开 {T.leftT[me]}")
        out.append("  [1] 拍 | 地 | 兵 | 密度 | 身上的兵（来源）| 在外的兵（目标）| 接壤（前 4）")
        ts = o["t"]
        for i, t in enumerate(ts):
            if t < t0 or t > dt or (t % 150 and t + 10 <= dt):
                continue
            if t % 150 and t + 10 <= dt:
                continue
            terr, bal = T.terr(me, t), T.bal(me, t)
            inn = " ".join(f"{T.nm(q, t)}:{v}" for q, v in sorted(o["inn"][i], key=lambda x: -x[1])[:3])
            outs = " ".join(f"{T.nm(q, t)}:{v}" for q, v in sorted(o["out"][i], key=lambda x: -x[1])[:3])
            nb = " ".join(f"{T.nm(q, t)}:{c}" for q, c in top_nb(T, o, t)[:4])
            out.append(f"      {t:>5} | {terr} | {bal} | {bal / max(terr, 1):.1f} | {inn} | {outs} | {nb}")

        # [2] 进攻者账
        take = defaultdict(lambda: dict(t0=None, t1=None, w=0, tiles=0, burnt=0, hit=0))
        mine = defaultdict(lambda: dict(tiles=0, burnt=0))
        for r in R["pairLog"]:
            if r[2] == me and r[1] != me:
                e = take[r[1]]
                e["t0"] = r[0] if e["t0"] is None else e["t0"]
                e["t1"] = r[0]
                e["w"] += 1
                e["tiles"] += r[3]
                e["burnt"] += r[4]
                e["hit"] += r[5] + r[6]
            elif r[1] == me:
                e = mine[r[2]]
                e["tiles"] += r[3]
                e["burnt"] += r[4]
        cm = defaultdict(lambda: [0, 0, 0, 0])   # 目标 -> 陆攻条数, 派出兵, 船条数, 船上兵
        for r in R["cmdLog"]:
            if r[1] != me:
                continue
            if r[2] == 1 and r[5]:
                cm[r[4]][0] += 1
                cm[r[4]][1] += r[6]
            elif r[2] == 3:
                cm[r[10] if len(r) > 10 else NEUTRAL][2] += 1
                cm[r[10] if len(r) > 10 else NEUTRAL][3] += r[6]
        out.append("  [2] 进攻者（拿走 ≥100 格的）：谁 | 首末拍（窗数）| 拿走的格 | 对方耗兵（每格）| 这个号被打掉的余额 | 这个号对它：生效陆攻 条数 / 派出的兵、船 条数 / 船上兵、拿回的格 / 烧掉的兵")
        for q, e in sorted(take.items(), key=lambda kv: -kv[1]["tiles"]):
            if e["tiles"] < 100:
                continue
            c = cm[q]
            m = mine[q]
            out.append(f"      {T.nm(q)} | {e['t0']}~{e['t1']}（{e['w']}）| {e['tiles']} | {e['burnt']}（{e['burnt'] / max(e['tiles'], 1):.0f}）| {e['hit']} | {c[0]} / {c[1]}、{c[2]} / {c[3]}、{m['tiles']} / {m['burnt']}")

        # [3] 指令
        cl = [r for r in R["cmdLog"] if r[1] == me and r[2] in (1, 2, 3)]
        last = [r for r in cl if t0 <= r[0] <= dt]
        nat = sum(1 for r in last if r[2] == 1)
        nok = sum(1 for r in last if r[2] == 1 and r[5])
        nbo = sum(1 for r in last if r[2] == 3)
        ndo = sum(1 for r in last if r[2] == 2 and r[5])
        lastAct = max([r[0] for r in cl if r[2] in (1, 3)], default=-1)
        lastAny = max([r[0] for r in cl], default=-1)
        byT = defaultdict(list)
        for r in last:
            byT[r[0]].append(r)
        batches = [(t, len(v)) for t, v in sorted(byT.items()) if len(v) >= 3]
        acts = sorted(set(r[0] for r in cl if r[2] in (1, 3) and r[0] >= t0)) + [dt]
        prev = t0
        gap, gapAt = 0, (t0, t0)
        for t in acts:
            if t - prev > gap:
                gap, gapAt = t - prev, (prev, t)
            prev = t
        out.append(f"  [3] 阵亡前 {span} 拍（{t0}~{dt}）已执行：陆攻 {nat} 条（生效 {nok}）、船 {nbo} 条、捐款 {ndo} 笔｜整局最后一条陆攻 / 船在 t={lastAct}（离阵亡 {dt - lastAct} 拍），最后一条任何指令在 t={lastAny}｜"
                   f"最长的没有陆攻 / 船的空窗 {gapAt[0]}~{gapAt[1]}（{gap} 拍）｜同拍 ≥3 条的批：" + (" ".join(f"{t}×{n}" for t, n in batches) or "无"))
        tg = defaultdict(lambda: [0, 0, 0])
        for r in last:
            if r[2] == 1:
                e = tg[T.nm(r[4])]
                e[0] += 1
                e[1] += 1 if r[5] else 0
                e[2] += r[6] if r[5] else 0
        out.append("      陆攻按目标（条数 / 生效 / 派出的兵）：" + ("；".join(f"{k} {v[0]} / {v[1]} / {v[2]}" for k, v in sorted(tg.items(), key=lambda kv: -kv[1][2])) or "无"))

        # [4] 捐款
        din = [r for r in R["cmdLog"] if r[2] == 2 and r[5] and r[4] == me and t0 <= r[0] <= dt]
        dout = [r for r in R["cmdLog"] if r[2] == 2 and r[5] and r[1] == me and t0 <= r[0] <= dt]
        by = defaultdict(lambda: [0, 0])
        for r in din:
            by[T.nm(r[1])][0] += 1
            by[T.nm(r[1])][1] += r[6]
        out.append(f"  [4] 阵亡前 {span} 拍收到捐款 {len(din)} 笔、到账 {sum(r[6] for r in din)}（" + "；".join(f"{k} {v[0]} 笔 {v[1]}" for k, v in sorted(by.items(), key=lambda kv: -kv[1][1]))
                   + f"）｜捐出 {len(dout)} 笔、到账 {sum(r[6] for r in dout)}、税 {sum(r[7] for r in dout)}"
                   + (f"｜最后一笔捐出 t={max(r[0] for r in dout)} → {T.nm(max(dout, key=lambda r: r[0])[4])}" if dout else ""))

        # [5] 掉余额
        drops = []
        for i in range(1, len(ts)):
            t = ts[i]
            if t < t0 or t > dt:
                continue
            b0, b1 = T.bal(me, ts[i - 1]), T.bal(me, t)
            if b0 >= 2000 and b1 <= 0.6 * b0:
                cc = [r for r in cl if ts[i - 1] <= r[0] < t]
                kinds = defaultdict(int)
                for r in cc:
                    kinds["陆攻" if r[2] == 1 else "船" if r[2] == 3 else "捐款"] += 1
                drops.append(f"{ts[i - 1]}→{t} {b0}→{b1}（" + (" ".join(f"{k}×{v}" for k, v in kinds.items()) or "没有指令：挨打 / 船靠岸") + "）")
        out.append("  [5] 10 拍内余额掉 ≥40%：" + ("；".join(drops[:12]) or "无"))

        # [6] 最后一轮下坡：阵亡前 span 拍里领土最后一次 ≥ 该窗峰值 90% 的拍 → 阵亡
        win = [(t, T.terr(me, t)) for t in ts if t0 <= t <= dt]
        if win:
            mx = max(v for _, v in win)
            tS = max(t for t, v in win if v >= 0.9 * mx)
            b0, l0 = T.bal(me, tS), T.terr(me, tS)
            lost = defaultdict(lambda: [0, 0, 0])
            for r in R["pairLog"]:
                if r[2] == me and r[1] != me and tS < r[0] <= dt + 30:
                    e = lost[T.nm(r[1], r[0])]
                    e[0] += r[3]
                    e[1] += r[4]
                    e[2] += r[5] + r[6]
            cc = [r for r in cl if tS <= r[0] <= dt]
            la = [r for r in cc if r[2] == 1 and r[5]]
            bo = [r for r in cc if r[2] == 3]
            do = [r for r in cc if r[2] == 2 and r[5]]
            toAtk = sum(r[6] for r in la if T.nm(r[4], r[0]) in lost)
            inc = ret = 0
            i0 = min(range(len(T.snapT)), key=lambda i: abs(T.snapT[i] - tS))
            i1 = min(range(len(T.snapT)), key=lambda i: abs(T.snapT[i] - dt))
            if "snapInc" in R:
                inc = R["snapInc"][i1][me] - R["snapInc"][i0][me]
            if "snapRet" in R:
                ret = R["snapRet"][i1][me] - R["snapRet"][i0][me]
            got = sum(r[6] for r in R["cmdLog"] if r[2] == 2 and r[5] and r[4] == me and tS <= r[0] <= dt)
            pool = b0 + inc + ret + got
            out.append(f"  [6] 最后一轮下坡 t={tS}→{dt}（{dt - tS} 拍）：起点 {l0} 格 / {b0} 兵（密度 {b0 / max(l0, 1):.0f}）、期间产兵 {inc}、收到捐款 {got}、进攻退回 {ret}｜丢给："
                       + "；".join(f"{k} {v[0]} 格（对方耗兵 {v[1]}、打掉余额 {v[2]}）" for k, v in sorted(lost.items(), key=lambda kv: -kv[1][0])[:4])
                       + f"｜这段自己的指令：生效陆攻 {len(la)} 条 {sum(r[6] for r in la)} 兵（其中打向进攻者 {toAtk}）、船 {len(bo)} 条 {sum(r[6] for r in bo)} 兵 + {sum(r[7] for r in bo)} 费、捐出 {len(do)} 笔 到账 {sum(r[6] for r in do)} + 税 {sum(r[7] for r in do)}"
                       + f"｜被打掉的余额合计 {sum(v[2] for v in lost.values())}（占 起点余额 + 产兵 + 收到 + 退回 的 {100 * sum(v[2] for v in lost.values()) / max(pool, 1):.0f}%）")
            summ.append(dict(bot=name, team=T.team(me), peak=peak, peakT=peakT, deathT=T.deathT[me], declineFrom=tS, declineTicks=dt - tS, terr0=l0, bal0=b0, dens0=round(b0 / max(l0, 1), 1),
                             income=inc, donIn=got, refund=ret, lostTo=[[k, v[0], v[1], v[2]] for k, v in sorted(lost.items(), key=lambda kv: -kv[1][0])[:4]],
                             landAtk=len(la), landAtkTroops=sum(r[6] for r in la), atAttackers=toAtk, boats=len(bo), boatTroops=sum(r[6] for r in bo), boatFees=sum(r[7] for r in bo),
                             donOut=len(do), donOutGot=sum(r[6] for r in do), donOutTax=sum(r[7] for r in do), destroyed=sum(v[2] for v in lost.values()),
                             destroyedPct=round(100 * sum(v[2] for v in lost.values()) / max(pool, 1), 1), lastActT=lastAct, idleBeforeDeath=dt - lastAct))
        out.append("")
    txt = "\n".join(out) + "\n"
    with open(os.path.join(OUT, mid, "dossier.txt"), "w", encoding="utf-8") as f:
        f.write(txt)
    if len(args) == 1:
        tot = dict(deaths=len(summ), destroyed=sum(e["destroyed"] for e in summ), atAttackers=sum(e["atAttackers"] for e in summ),
                   zeroReply=sum(1 for e in summ if e["atAttackers"] == 0), bal0=sum(e["bal0"] for e in summ))
        with open(os.path.join(OUT, mid, "dossier_sum.json"), "w", encoding="utf-8") as f:
            json.dump(dict(matchId=mid, span=span, perBot=summ, total=tot), f, ensure_ascii=False, indent=1)
        out.append(f"[合计] 阵亡 {tot['deaths']} 个号：最后一轮下坡里被打掉的余额 {tot['destroyed']}，打向进攻者的兵 {tot['atAttackers']}（{100 * tot['atAttackers'] / max(tot['destroyed'], 1):.1f}%），一兵没还手的 {tot['zeroReply']} 个")
        with open(os.path.join(OUT, mid, "dossier.txt"), "a", encoding="utf-8") as f:
            f.write(out[-1] + "\n")
    if quiet:
        print(f"{mid}: dossier.txt {len(out)} 行")
    else:
        print(txt)


if __name__ == "__main__":
    main()
