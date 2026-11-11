#!/usr/bin/env python3
"""flow.py — 只看日志的『兵去哪了』流水账：把每个号每个 90 拍快照窗的余额变化拆成 利息 / 捐款 / 其余。

    python3 flow.py <matchId> [--room N] [--t0 3000] [--t1 99999] [--bots 名字,名字]

为什么要它：logstats [QE] 的『纯船窗少掉的兵』只数出去的那一窗，船上的兵靠岸、打完以后回到余额是在后面的窗。
要说一个号的船到底亏了多少，得把整段时间的进出合起来看；要说兵是不是并到了队友身上（船靠在同队的地上、
没定案的捐款其实成交了），得把同一窗里全队的『其余』加起来看守不守恒。

口径：
  · 残差 = 窗末余额 − 只滚利息的公式余额（facts.interest_gain；领土取窗首，窗内领土变化大时利息有 1~2% 的误差）。
  · 捐款取 donfit 定案（out/<局>/donfit[_room<N>].json）：EXEC 的按 到账+税 记捐出方流出、按 到账 记收款方流入，
    记在发令拍所在的窗（时延跨窗时会错开一窗）。没定案（AMB）的另列一栏：发令时按足额算的 到账+税 / 到账。
  · 其余 = 残差 + 成交捐出 − 成交收入。负数 = 陆攻 / 船 / 戳刺派出去还没回来的兵、挨打被打掉的兵；正数 = 回流、没定案的捐款到账、
    同队的船并进来的兵、空壳赠兵。
节：
  [VA] 逐号合计：窗数 | 利息（公式增量）| 成交捐出（到账+税）| 成交收入 | 没定案 捐出 / 收入（足额口径）| 其余 负的合计 / 正的合计 / 净 |
       领土 首→末 | 陆攻+戳刺 / 船 条数（cmds 增量 − 捐款日志条数 − 船，船）
  [VB] 逐窗全队：窗 | 各号『其余』（千兵；* = 这一窗有船，+ = 有陆攻或戳刺）| 全队合计 | 这一窗没定案的捐款（捐出→收款 足额到账，千兵）
  [VC] 被围（窗首 nb=0 且 neut=0）且窗内有船的窗，逐号合计：窗数 / 船数 | 这些窗的『其余』合计 | 之后一窗的『其余』合计（回流）| 两者之和 |
       这些窗 + 之后一窗的领土净变化
"""
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import facts  # noqa: E402


def main():
    args = sys.argv[1:]
    mid = args[0]
    room = int(args[args.index("--room") + 1]) if "--room" in args else None
    t0 = int(args[args.index("--t0") + 1]) if "--t0" in args else 0
    t1 = int(args[args.index("--t1") + 1]) if "--t1" in args else 10 ** 9
    only = set(args[args.index("--bots") + 1].split(",")) if "--bots" in args else None
    F = facts.build(mid, room=room) if room is not None else facts.build(mid)
    land = F["land"]
    sfx = f"_room{room}" if room is not None else ""
    dpath = os.path.join(HERE, "..", "out", mid, f"donfit{sfx}.json")
    if not os.path.exists(dpath) and room is not None:
        dpath = os.path.join(HERE, "..", "out", mid, "donfit.json")   # 主房间的产物不带后缀
    rows = json.load(open(dpath))["rows"] if os.path.exists(dpath) else []
    if rows and not all(r["donor"] in F["bots"] or str(r["donor"]) in F["bots"] for r in rows):
        rows = []   # 那份定案是别的房间的
    if not rows:
        print(f"（没有找到 donfit 定案 {os.path.basename(dpath)}：捐款栏全是 0，『其余』里混着捐款）")
    name_to_me = {}
    for me, b in F["bots"].items():
        name_to_me[b["name"]] = str(me)
    bots = {str(me): b for me, b in F["bots"].items()}

    def full_amt(r):
        return int((r["myBal"] * (r["pct"] + 1) + 0.5) // 1024)

    def full_fee(r):
        return int((64 * r["myBal"] + 0.5) // 1024)

    wins = defaultdict(dict)   # me -> t0 -> rec
    for me, b in bots.items():
        tk = b["ticks"]
        for i in range(1, len(tk)):
            a, c = tk[i - 1], tk[i]
            if c["t"] <= t0 or a["t"] >= t1 or a["terr"] < 50:
                continue
            exp = facts.interest_gain(a["terr"], land, a["bal"], a["t"], c["t"])
            rec = dict(t0=a["t"], t1=c["t"], resid=c["bal"] - exp, interest=exp - a["bal"], terr0=a["terr"], terr1=c["terr"],
                       dc=c["cmds"] - a["cmds"], db=c["boats"] - a["boats"], boxed=(a["nb"] == 0 and a["neut"] == 0),
                       outE=0, inE=0, outA=0, inA=0, nDonLog=0, amb=[])
            wins[me][a["t"]] = rec
    for r in rows:
        dn, al = str(r["donor"]), str(r["ally"])
        for me, key_out in ((dn, True), (al, False)):
            if me not in wins:
                continue
            for w in wins[me].values():
                if w["t0"] <= r["t"] < w["t1"]:
                    if key_out:
                        w["nDonLog"] += 1
                        if r["status"] == "EXEC":
                            w["outE"] += r["amt"] + r["fee"]
                        elif r["status"] == "AMB":
                            w["outA"] += full_amt(r) + full_fee(r)
                            w["amb"].append(f"{r['donorName']}→{r['allyName']} {full_amt(r) // 1000}")
                    else:
                        if r["status"] == "EXEC":
                            w["inE"] += r["amt"]
                        elif r["status"] == "AMB":
                            w["inA"] += full_amt(r)
                    break
    order = sorted(wins, key=lambda m: int(m))
    if only:
        order = [m for m in order if bots[m]["name"] in only]
    print(f"[VA] {mid} 兵的流水（只看日志；窗 = 相邻两条 HL-TICK，t={t0}~{min(t1, F['card']['outcome']['endTick'])}）：号 队 | 窗数 | 利息 | 成交捐出（到账+税）| 成交收入 | "
          f"没定案 捐出 / 收入（足额口径）| 其余：负的合计 / 正的合计 / 净 | 领土 首→末 | 陆攻+戳刺 / 船")
    for me in order:
        ws = sorted(wins[me].values(), key=lambda w: w["t0"])
        if not ws:
            continue
        oth = [w["resid"] + w["outE"] - w["inE"] for w in ws]
        b = bots[me]
        print(f"     {b['name']}({me}) T{b.get('team')} | {len(ws)} | {sum(w['interest'] for w in ws)} | {sum(w['outE'] for w in ws)} | {sum(w['inE'] for w in ws)} | "
              f"{sum(w['outA'] for w in ws)} / {sum(w['inA'] for w in ws)} | {sum(x for x in oth if x < 0)} / {sum(x for x in oth if x > 0)} / {sum(oth)} | "
              f"{ws[0]['terr0']}→{ws[-1]['terr1']} | {sum(w['dc'] - w['db'] - w['nDonLog'] for w in ws)} / {sum(w['db'] for w in ws)}")
    print("[VB] 逐窗全队『其余』（千兵；* = 这一窗有船，+ = 有陆攻或戳刺，# = 窗首被围）：窗 | " + " | ".join(bots[m]["name"] for m in order) + " | 全队合计 | 没定案的捐款（足额到账，千兵）")
    tset = sorted({t for m in order for t in wins[m]})
    for t in tset:
        cells, tot, amb = [], 0, []
        for m in order:
            w = wins[m].get(t)
            if not w:
                cells.append("-")
                continue
            o = w["resid"] + w["outE"] - w["inE"]
            tot += o
            amb += w["amb"]
            flag = ("*" if w["db"] > 0 else "") + ("+" if w["dc"] - w["db"] - w["nDonLog"] > 0 else "") + ("#" if w["boxed"] else "")
            cells.append(f"{round(o / 1000)}{flag}")
        print(f"     {t:>5} | " + " | ".join(f"{c:>8}" for c in cells) + f" | {round(tot / 1000):>7} | " + "；".join(amb))
    print("[VC] 被围（窗首 nb=0 且 neut=0）且窗内有船的窗：号 | 窗数 / 船数 | 这些窗的『其余』合计 | 紧接着一窗的『其余』合计 | 两者之和 | 领土净变化（这些窗 + 紧接着一窗）")
    for me in order:
        ws = sorted(wins[me].values(), key=lambda w: w["t0"])
        n = nb = a = bsum = dterr = 0
        used = set()
        for i, w in enumerate(ws):
            if w["boxed"] and w["db"] > 0:
                n += 1
                nb += w["db"]
                if i not in used:
                    a += w["resid"] + w["outE"] - w["inE"]
                    dterr += w["terr1"] - w["terr0"]
                    used.add(i)
                if i + 1 < len(ws) and i + 1 not in used and not (ws[i + 1]["boxed"] and ws[i + 1]["db"] > 0):
                    x = ws[i + 1]
                    bsum += x["resid"] + x["outE"] - x["inE"]
                    dterr += x["terr1"] - x["terr0"]
                    used.add(i + 1)
        if n:
            print(f"     {bots[me]['name']} | {n} / {nb} | {a} | {bsum} | {a + bsum} | {dterr:+d}")

    # [VD] 出手段的价钱：连续的『有陆攻或戳刺、没有船』的窗连成一段，再带上紧接着的一窗（兵回流 / 地继续涨）。
    #      花掉的兵 = −（这几窗『其余』之和）；只在领土净涨的段里算每格的价。挨打的损失也混在『其余』里，所以是上限。
    print("[VD] 出手段的价钱（只看日志；一段 = 连续的『有陆攻 / 戳刺、没有船』的窗 + 紧接着的一窗）：号 | 段数 | 领土净涨的段：段数 / 花掉的兵 / 涨的格 / 每格 | "
          "其中段首密度 ≥100 的：段数 / 花掉的兵 / 涨的格 / 每格 | 段首密度 <100 的：段数 / 花掉的兵 / 涨的格 / 每格 | 领土没涨的段：段数 / 花掉的兵 / 领土变化")
    tot = dict(hi=[0, 0, 0], lo=[0, 0, 0], bad=[0, 0, 0])
    epis_all = []
    for me in order:
        ws = sorted(wins[me].values(), key=lambda w: w["t0"])
        epis = []
        i = 0
        while i < len(ws):
            w = ws[i]
            atk = (w["dc"] - w["db"] - w["nDonLog"] > 0) and w["db"] == 0
            if not atk:
                i += 1
                continue
            j = i
            while j + 1 < len(ws) and (ws[j + 1]["dc"] - ws[j + 1]["db"] - ws[j + 1]["nDonLog"] > 0) and ws[j + 1]["db"] == 0 and ws[j + 1]["t0"] == ws[j]["t1"]:
                j += 1
            seg = ws[i:j + 1]
            if j + 1 < len(ws) and ws[j + 1]["t0"] == ws[j]["t1"] and ws[j + 1]["db"] == 0:
                seg = seg + [ws[j + 1]]
                j += 1
            spent = -sum(x["resid"] + x["outE"] - x["inE"] for x in seg)
            gain = seg[-1]["terr1"] - seg[0]["terr0"]
            b0 = None
            for s in bots[me]["ticks"]:
                if s["t"] == seg[0]["t0"]:
                    b0 = s
                    break
            dens0 = (b0["bal"] / max(1, b0["terr"])) if b0 else 0
            epis.append(dict(t0=seg[0]["t0"], t1=seg[-1]["t1"], spent=spent, gain=gain, dens0=dens0, terr0=seg[0]["terr0"], name=bots[me]["name"]))
            i = j + 1
        if not epis:
            continue
        good = [e for e in epis if e["gain"] > 0 and e["spent"] > 0]
        hi = [e for e in good if e["dens0"] >= 100]
        lo = [e for e in good if e["dens0"] < 100]
        bad = [e for e in epis if not (e["gain"] > 0 and e["spent"] > 0)]

        def fmt(es):
            sp, gn = sum(e["spent"] for e in es), sum(e["gain"] for e in es)
            return f"{len(es)} / {sp} / {gn} / {sp / gn:.0f}" if gn > 0 else f"{len(es)} / {sp} / {gn} / –"

        for k, es in (("hi", hi), ("lo", lo)):
            tot[k][0] += len(es)
            tot[k][1] += sum(e["spent"] for e in es)
            tot[k][2] += sum(e["gain"] for e in es)
        tot["bad"][0] += len(bad)
        tot["bad"][1] += sum(e["spent"] for e in bad)
        tot["bad"][2] += sum(e["gain"] for e in bad)
        epis_all += epis
        print(f"     {bots[me]['name']} | {len(epis)} | {fmt(good)} | {fmt(hi)} | {fmt(lo)} | {len(bad)} / {sum(e['spent'] for e in bad)} / {sum(e['gain'] for e in bad):+d}")
    if epis_all:
        h, lw, bd = tot["hi"], tot["lo"], tot["bad"]
        print(f"     合计 | {len(epis_all)} | 段首密度 ≥100：{h[0]} 段 / {h[1]} 兵 / {h[2]} 格 / 每格 {h[1] / max(1, h[2]):.0f} | <100：{lw[0]} 段 / {lw[1]} 兵 / {lw[2]} 格 / 每格 {lw[1] / max(1, lw[2]):.0f} | "
              f"领土没涨的 {bd[0]} 段 / {bd[1]} 兵 / {bd[2]:+d} 格")
        big = sorted([e for e in epis_all if e["spent"] > 0], key=lambda e: -e["spent"])[:14]
        print("     花得最多的 14 段：号 起~止 | 段首 领土 / 密度 | 花掉的兵 | 领土变化 | 每格")
        for e in big:
            per = f"{e['spent'] / e['gain']:.0f}" if e["gain"] > 0 else "–"
            print(f"       {e['name']} {e['t0']}~{e['t1']} | {e['terr0']} / {e['dens0']:.0f} | {e['spent']} | {e['gain']:+d} | {per}")

    # [VE] 挨打窗：窗内没有自己的指令（cmds 不变）、领土掉了、『其余』为负。
    print("[VE] 挨打窗（窗内 cmds 不变、领土净掉、『其余』为负）：号 | 窗数 | 掉的格 | 少掉的兵 | 每掉一格少掉的兵 | 掉得最多的一窗（起拍 / 格 / 兵）")
    for me in order:
        ws = sorted(wins[me].values(), key=lambda w: w["t0"])
        hit = [w for w in ws if w["dc"] == 0 and w["terr1"] < w["terr0"] and (w["resid"] + w["outE"] - w["inE"]) < 0]
        if not hit:
            continue
        lost = sum(w["terr0"] - w["terr1"] for w in hit)
        burn = -sum(w["resid"] + w["outE"] - w["inE"] for w in hit)
        worst = max(hit, key=lambda w: w["terr0"] - w["terr1"])
        print(f"     {bots[me]['name']} | {len(hit)} | {lost} | {burn} | {burn / max(1, lost):.0f} | {worst['t0']} / {worst['terr0'] - worst['terr1']} / {-(worst['resid'] + worst['outE'] - worst['inE'])}")


if __name__ == "__main__":
    main()
