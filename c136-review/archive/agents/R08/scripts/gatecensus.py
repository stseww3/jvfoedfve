#!/usr/bin/env python3
"""gatecensus.py — 全程买地门槛普查：1500 拍以后，号对真人邻居（尤其是正在打它的那个）为什么不出手。

    # 先跑（重计算，套 run-heavy）：node shadow.mjs <局> --walk-every 30 --census-until 0 --core-census-until 0 --tag walk --quiet
    python3 gatecensus.py <matchId> [--side peer] [--quiet]     # 读 out/<局>/shadow_walk.json + resim.json，写 gatecensus.txt + gatecensus_sum.json

口径：影子（归档策略原样，喂录像真值盘面）每 30 拍对每个在线号把 Policy.buyLand 的报价循环重走一遍（shadow.mjs walkBuyLand，不发指令）。
报价按每格成本从低到高排；遇到第一个『价 ≥ worth 且没过软上限』的报价整轮截断（c110 L5267 break），后面更贵的报价不再看。
  一个采样点的『整轮结论』= 最后一行的结论：SEND（会发）/ break（价格截断）/ 全部 skip。
  『对进攻者的结论』= 报价表里进攻者那一行的结论；截断发生在它前面时记成 break（它的价更高）。
注意：这是策略逻辑在真值盘面上的结论，不含指令时延；真实的号看到的盘面还要晚几十到几百拍（lagledger.py）。

[WA] 采样点的构成  [WB] 有真人敌邻时的整轮结论（分时段）  [WC] 正在挨真人打时，对进攻者的结论（分时段）
[WD] 同 [WC]，按自己的密度分档  [WE] 价格门的细节（报价 ÷ worth）  [WF] 留底门的细节（safe ÷ 余额）
[WG] 丢给真人的格数，按丢地那 30 拍开头对这个进攻者的结论分摊（真值逐对战损账）  [WH] 逐号  [WI] 自检
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from truth import Truth, OUT  # noqa: E402

PERIODS = [(1500, 3000), (3000, 4284), (4284, 6300), (6300, 8100), (8100, 10 ** 9)]
BANDS = [(0, 60), (60, 100), (100, 126), (126, 10 ** 9)]


def plabel(p):
    return f"{p[0]}~{'终' if p[1] > 10 ** 8 else p[1]}"


def blabel(b):
    return f"<{b[1]}" if b[0] == 0 else (f"≥{b[0]}" if b[1] > 10 ** 8 else f"{b[0]}~{b[1]}")


def norm(v):
    if v is None:
        return "?"
    v = re.sub(r"\(<[\d.]+x100xL\)", "", v)
    v = re.sub(r"\((\d+)\)", "", v)
    v = v.replace("(没照抄)", "")
    return v


def med(v):
    s = sorted(v)
    return s[len(s) // 2] if s else 0


def qt(v, f):
    s = sorted(v)
    return s[min(len(s) - 1, int(f * len(s)))] if s else 0


def fmt_counter(c, total=None, top=8):
    total = total if total is not None else sum(c.values())
    return "；".join(f"{k} {v}（{100 * v / max(total, 1):.0f}%）" for k, v in c.most_common(top))


def main():
    argv = sys.argv[1:]
    quiet = "--quiet" in argv
    side = argv[argv.index("--side") + 1] if "--side" in argv else "own"
    mid = [a for a in argv if not a.startswith("--") and a != side][0]
    T = Truth(mid)
    R = T.R
    H = T.H
    fn = "shadow_walk_peer.json" if side == "peer" else "shadow_walk.json"
    D = json.load(open(os.path.join(OUT, mid, fn), encoding="utf-8"))
    every = D.get("walkEvery") or 30
    bots = D["bots"]
    out = []
    summ = dict(matchId=mid, side=side, walkEvery=every)

    # 真值：逐对战损（30 拍窗）里丢给真人的格数
    lost = defaultdict(lambda: defaultdict(int))   # lost[(bot id, tEnd)][attacker] = tiles
    for r in R["pairLog"]:
        t, a, d, tiles = r[0], r[1], r[2], r[3]
        if d < H and a < H and tiles > 0:
            lost[(d, t)][a] += tiles
    pl_t = sorted({r[0] for r in R["pairLog"]})
    pl_step = min((b - a for a, b in zip(pl_t, pl_t[1:])), default=30)

    samples = []
    for name, b in bots.items():
        me = b["id"]
        for w in b.get("walks", []):
            t, B, L, worth, over, nH, nHumNb, inH, top, neut, active, rows = w
            last = rows[-1] if rows else None
            fin = norm(last[4]) if last else "noOffers"
            if fin.startswith("SEND"):
                final = "SEND→真人" if last[1] else "SEND→人机"
            elif fin.startswith("break"):
                final = "break:price>=worth"
            elif last is None:
                final = "没有报价"
            else:
                final = "全部跳过"
            byq = {r[0]: r for r in rows}
            atk_v = None
            atk_row = None
            if inH > 0 and top >= 0:
                if top in byq:
                    atk_row = byq[top]
                    atk_v = norm(atk_row[4])
                elif fin.startswith("break"):
                    atk_v = "break:price>=worth（更便宜的报价已截断）"
                elif fin.startswith("SEND"):
                    atk_v = "先发给了更便宜的目标"
                else:
                    atk_v = "不在报价表里（不接壤 / 受保护）"
            samples.append(dict(bot=name, me=me, t=t, B=B, L=L, dens=B / max(L, 1), worth=worth, over=over, nHumNb=nHumNb, inH=inH, top=top, neut=neut, active=active,
                                rows=rows, final=final, fin=fin, atk_v=atk_v, atk_row=atk_row, last=last))

    def per(s):
        for p in PERIODS:
            if p[0] <= s["t"] < p[1]:
                return p
        return None

    samples = [s for s in samples if per(s)]
    hn = [s for s in samples if s["nHumNb"] >= 1]
    ua = [s for s in samples if s["inH"] > 0 and s["top"] >= 0]
    out.append(f"[WA] {mid} 全程买地门槛普查（影子每 {every} 拍重走一遍 buyLand）：采样点 {len(samples)} 个（号·拍），其中有真人敌邻的 {len(hn)} 个（{100 * len(hn) / max(len(samples), 1):.0f}%），"
               f"正被真人压着兵的 {len(ua)} 个（{100 * len(ua) / max(len(samples), 1):.0f}%）；没有真人敌邻的 {len(samples) - len(hn)} 个")
    out.append("  时段 | 采样点 | 有真人敌邻 | 正在挨真人打 | 过软上限（余额 > 100×领土）的点")
    for p in PERIODS:
        ss = [s for s in samples if per(s) == p]
        if not ss:
            continue
        out.append(f"    {plabel(p)} | {len(ss)} | {sum(1 for s in ss if s['nHumNb'] >= 1)} | {sum(1 for s in ss if s['inH'] > 0 and s['top'] >= 0)} | {sum(1 for s in ss if s['over'])}")

    out.append("")
    out.append("[WB] 有真人敌邻时的整轮结论：时段 | 点数 | SEND→真人 | SEND→人机 | 价格截断 break:price>=worth | 全部跳过（其中最便宜的真人报价的结论）")
    wb = []
    for p in PERIODS + [None]:
        ss = [s for s in hn if (p is None or per(s) == p)]
        if not ss:
            continue
        c = Counter(s["final"] for s in ss)
        sub = Counter()
        for s in ss:
            if s["final"] == "全部跳过":
                hr = next((r for r in s["rows"] if r[1]), None)
                sub[norm(hr[4]) if hr else "没有真人报价"] += 1
        n = len(ss)
        out.append(f"    {plabel(p) if p else '合计'} | {n} | {c['SEND→真人']}（{100 * c['SEND→真人'] / n:.1f}%）| {c['SEND→人机']}（{100 * c['SEND→人机'] / n:.1f}%）| {c['break:price>=worth']}（{100 * c['break:price>=worth'] / n:.1f}%）| "
                   f"{c['全部跳过']}（{100 * c['全部跳过'] / n:.1f}%：{fmt_counter(sub, c['全部跳过'], 5)}）")
        wb.append(dict(period=plabel(p) if p else "all", n=n, sendHuman=c["SEND→真人"], sendAi=c["SEND→人机"], priceBreak=c["break:price>=worth"], allSkip=c["全部跳过"], allSkipWhy=dict(sub)))
    summ["withHumanNb"] = wb

    out.append("")
    out.append("[WC] 正在挨真人打时，对压兵最多的那个进攻者的结论：时段 | 点数 | 会打它（SEND）| 各门槛")
    wc = []
    for p in PERIODS + [None]:
        ss = [s for s in ua if (p is None or per(s) == p)]
        if not ss:
            continue
        c = Counter("SEND" if (s["atk_v"] or "").startswith("SEND") else s["atk_v"] for s in ss)
        n = len(ss)
        rest = Counter({k: v for k, v in c.items() if k != "SEND"})
        out.append(f"    {plabel(p) if p else '合计'} | {n} | {c['SEND']}（{100 * c['SEND'] / n:.1f}%）| {fmt_counter(rest, n, 7)}")
        wc.append(dict(period=plabel(p) if p else "all", n=n, send=c["SEND"], why=dict(rest)))
    summ["underAttack"] = wc

    out.append("")
    out.append("[WD] 同上，按自己当拍的密度分档：密度 | 点数 | 会打它 | 各门槛 | 余额合计（千）")
    wd = []
    for bd in BANDS:
        ss = [s for s in ua if bd[0] <= s["dens"] < bd[1]]
        if not ss:
            continue
        c = Counter("SEND" if (s["atk_v"] or "").startswith("SEND") else s["atk_v"] for s in ss)
        n = len(ss)
        rest = Counter({k: v for k, v in c.items() if k != "SEND"})
        out.append(f"    {blabel(bd)} | {n} | {c['SEND']}（{100 * c['SEND'] / n:.1f}%）| {fmt_counter(rest, n, 6)} | {sum(s['B'] for s in ss) // 1000}")
        wd.append(dict(band=blabel(bd), n=n, send=c["SEND"], why=dict(rest)))
    summ["underAttackByDensity"] = wd

    out.append("")
    pb = [s for s in ua if (s["atk_v"] or "").startswith("break") and s["atk_row"] is not None]
    pb2 = [s for s in ua if (s["atk_v"] or "").startswith("break")]
    out.append(f"[WE] 价格门的细节（正在挨打、对进攻者的结论是 break:price>=worth 的 {len(pb2)} 个点；其中进攻者自己就是截断那一行的 {len(pb)} 个）")
    if pb:
        ratio = [s["atk_row"][2] / max(s["worth"], 1e-9) for s in pb]
        out.append(f"  进攻者的每格报价 ÷ worth：中位 {med(ratio):.2f}、下四分位 {qt(ratio, 0.25):.2f}、上四分位 {qt(ratio, 0.75):.2f}；≤1.25 的 {sum(1 for x in ratio if x <= 1.25)} 个、≤1.5 的 {sum(1 for x in ratio if x <= 1.5)} 个、≤2 的 {sum(1 for x in ratio if x <= 2)} 个、>3 的 {sum(1 for x in ratio if x > 3)} 个")
        out.append(f"  每格报价 中位 {med([s['atk_row'][2] for s in pb]):.0f}｜worth 中位 {med([s['worth'] for s in pb]):.0f}｜自己的密度 中位 {med([s['dens'] for s in pb]):.0f}｜进攻者的密度 中位 {med([s['atk_row'][7] / max(s['atk_row'][8], 1) for s in pb]):.0f}"
                   f"｜worth ÷ 自己的密度 中位 {med([s['worth'] / max(s['dens'], 1e-9) for s in pb]):.2f}｜进攻者余额 ÷ 自己余额 中位 {med([s['atk_row'][7] / max(s['B'], 1) for s in pb]):.2f}")
        for bd in BANDS:
            ss = [s for s in pb if bd[0] <= s["dens"] < bd[1]]
            if ss:
                rr = [s["atk_row"][2] / max(s["worth"], 1e-9) for s in ss]
                out.append(f"    密度 {blabel(bd)}：{len(ss)} 个点，报价 ÷ worth 中位 {med(rr):.2f}，报价 中位 {med([s['atk_row'][2] for s in ss]):.0f}，worth 中位 {med([s['worth'] for s in ss]):.0f}")
        summ["priceGate"] = dict(n=len(pb2), nRow=len(pb), ratioMed=round(med(ratio), 2), ratioQ1=round(qt(ratio, 0.25), 2), ratioQ3=round(qt(ratio, 0.75), 2),
                                 le125=sum(1 for x in ratio if x <= 1.25), le150=sum(1 for x in ratio if x <= 1.5), le200=sum(1 for x in ratio if x <= 2),
                                 priceMed=med([s["atk_row"][2] for s in pb]), worthMed=med([s["worth"] for s in pb]), densMed=round(med([s["dens"] for s in pb]), 1))

    out.append("")
    sf = [s for s in ua if s["atk_v"] == "skip:avail<=0(safe)" and s["atk_row"] is not None and s["atk_row"][5] is not None]
    out.append(f"[WF] 留底门的细节（正在挨打、对进攻者的结论是 skip:avail<=0(safe) 的 {len(sf)} 个点）")
    if sf:
        r1 = [s["atk_row"][5] / max(s["B"], 1) for s in sf]
        out.append(f"  safe 原值 ÷ 自己的余额：中位 {med(r1):.2f}、下四分位 {qt(r1, 0.25):.2f}、上四分位 {qt(r1, 0.75):.2f}；≥2 的 {sum(1 for x in r1 if x >= 2)} 个、≥5 的 {sum(1 for x in r1 if x >= 5)} 个"
                   f"｜进攻者余额 ÷ 自己余额 中位 {med([s['atk_row'][7] / max(s['B'], 1) for s in sf]):.2f}｜自己的密度 中位 {med([s['dens'] for s in sf]):.0f}")
        summ["safeGate"] = dict(n=len(sf), safeOverBalMed=round(med(r1), 2), ge2=sum(1 for x in r1 if x >= 2), ge5=sum(1 for x in r1 if x >= 5))

    # [WG] 丢地分摊
    out.append("")
    out.append(f"[WG] 丢给真人的格数，按丢地那 {pl_step} 拍开头时对这个进攻者的结论分摊（真值逐对战损账；窗口对不上采样点的记『没有采样点』）")
    by_bt = {(s["me"], s["t"]): s for s in samples}
    wg_tot = Counter()
    wg_per = defaultdict(Counter)
    sq_ids = {b["id"] for b in bots.values()}
    for (d, tend), atks in lost.items():
        if d not in sq_ids:
            continue
        for a, tiles in atks.items():
            if a in T.sqIds and T.team(a) != T.team(d):
                key = "进攻者是异队编队友（受保护，不在报价表里）"
            elif T.team(a) == T.team(d):
                key = "进攻者是同队"
            else:
                t0 = tend - pl_step
                t0 -= t0 % every
                s = by_bt.get((d, t0))
                if s is None:
                    key = "没有采样点（1500 拍前 / 已不在线）"
                else:
                    r = next((x for x in s["rows"] if x[0] == a), None)
                    if r is not None:
                        v = norm(r[4])
                        key = "SEND（会打它）" if v.startswith("SEND") else v
                    elif s["fin"].startswith("break"):
                        key = "break:price>=worth"
                    elif s["fin"].startswith("SEND"):
                        key = "先发给了更便宜的目标"
                    else:
                        key = "不在报价表里（当拍不接壤）"
            wg_tot[key] += tiles
            pp = next((p for p in PERIODS if p[0] <= tend - pl_step < p[1]), None)
            wg_per[plabel(pp) if pp else "<1500"][key] += tiles
    tot = sum(wg_tot.values())
    out.append(f"  全场丢给真人 {tot} 格：{fmt_counter(wg_tot, tot, 10)}")
    for p in ["<1500"] + [plabel(p) for p in PERIODS]:
        c = wg_per.get(p)
        if c:
            out.append(f"    {p}：{sum(c.values())} 格｜{fmt_counter(c, None, 6)}")
    summ["lostTilesByVerdict"] = dict(total=tot, by=dict(wg_tot), byPeriod={k: dict(v) for k, v in wg_per.items()})

    out.append("")
    out.append("[WH] 逐号：号 | 采样点 | 有真人敌邻 | 正在挨打 | 挨打时会打进攻者（SEND）| 挨打时最多的两个门槛 | 挨打的点里过软上限的")
    wh = []
    for name in bots:
        ss = [s for s in samples if s["bot"] == name]
        u = [s for s in ss if s["inH"] > 0 and s["top"] >= 0]
        c = Counter("SEND" if (s["atk_v"] or "").startswith("SEND") else s["atk_v"] for s in u)
        rest = Counter({k: v for k, v in c.items() if k != "SEND"})
        out.append(f"    {name:<16} | {len(ss)} | {sum(1 for s in ss if s['nHumNb'] >= 1)} | {len(u)} | {c['SEND']}（{100 * c['SEND'] / max(len(u), 1):.0f}%）| {fmt_counter(rest, len(u), 2)} | {sum(1 for s in u if s['over'])}")
        wh.append(dict(bot=name, n=len(ss), humanNb=sum(1 for s in ss if s["nHumNb"] >= 1), underAttack=len(u), send=c["SEND"], why=dict(rest.most_common(3))))
    summ["perBot"] = wh

    # [WI] 自检：整轮结论是 SEND 的点，影子在这一拍到下一个采样点之间有没有发陆攻
    out.append("")
    ok = n = 0
    for name, b in bots.items():
        atk_t = sorted(c[0] for c in b["cmds"] if c[1] == 1)
        for s in (x for x in samples if x["bot"] == name and x["final"].startswith("SEND")):
            n += 1
            if any(s["t"] <= t < s["t"] + every for t in atk_t):
                ok += 1
    out.append(f"[WI] 自检：整轮结论是 SEND 的 {n} 个点里，影子在这一拍到下一个采样点之前真的发了陆攻的 {ok} 个（{100 * ok / max(n, 1):.0f}%）；"
               "其余是 buyLand 之外的关（驱动层 8 拍静默、进攻槽占满、先做了捐款 / 发船等）或采样拍在策略出手之后（余额已经变了）")
    summ["selfCheck"] = dict(sendSamples=n, shadowSentWithin=ok)

    txt = "\n".join(out) + "\n"
    sfx = "_peer" if side == "peer" else ""
    with open(os.path.join(OUT, mid, f"gatecensus{sfx}.txt"), "w", encoding="utf-8") as f:
        f.write(txt)
    with open(os.path.join(OUT, mid, f"gatecensus_sum{sfx}.json"), "w", encoding="utf-8") as f:
        json.dump(summ, f, ensure_ascii=False, indent=1)
    if quiet:
        print(f"{mid}: gatecensus{sfx}.txt {len(out)} 行")
    else:
        print(txt)


if __name__ == "__main__":
    main()
