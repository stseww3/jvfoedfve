#!/usr/bin/env python3
"""flowcheck.py — 把已交复盘稿里引用过的『兵/格』（只看日志的口径）用净值口径重算一遍，列出差异（outbox 0008 里答应的事）。

    python3 flowcheck.py [--quiet]      → out/_cross/flowcheck.txt、flowcheck.json

三个口径（都只看日志，同一条 DROP30 出手窗）：
  单窗   digest [F] 的『每格花费』= 这一窗比『只滚利息』少掉的兵 ÷ 这一窗涨的格。没扣同窗的捐款，也没抵掉后面退回余额的兵。
  两段   digest [F] 的『两段合计』= 出手窗 + 下一窗的净流出 ÷ 两窗净增的格。抵掉了下一窗的回流，没扣捐款。
  净值   flow.py 的口径：『其余』= 余额变化 − 利息 − 成交捐款收支（donfit 定案；没有 donfit 的局捐款栏是 0）。
         净值两窗 = 出手窗 + 下一窗的『其余』之和取负 ÷ 两窗净增的格（= 两段口径再扣掉捐款）；
         净值三窗 = 再多带一窗（看回流 / 被吃回去有没有改变结论）。挨打掉的兵也混在里面，所以都是上限；合起来领土没涨就算不出每格。
         （flow.py [VD] 的『出手段』会把连着出手的窗全并成一段，开局一路打到中期的号一段就是一两千拍，不能拿来对单次引用，这里不用。）
节：
  [FK-A] 逐局：出手窗（DROP30 且归因 ATTACK-GAIN、领土净涨）条数，三个口径的中位，单窗 / 两段比净值高出一半以上的条数
  [FK-B] 复盘稿 decisions 里引用过的数字逐条对上出手窗（按 号 + 数值 配，±0.6 以内算同一个）：引用值 | 它是哪个口径 | 净值口径 | 差多少
  [FK-C] 小结：引用值按净值口径重算后，『高价』（≥90 兵/格）的结论还站不站得住
"""
import json
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import facts  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")
REV = os.path.join(os.path.dirname(HERE), "reviews")
MINE = ["G02", "G05", "G08", "B043", "B033", "B034", "B031", "B049", "B006", "B030", "B019", "B009", "B015", "B029", "B035", "B027"]
NUM = re.compile(r"(?:（|\(|每格(?:连手续费)?\s*|均价\s*|约\s*|折合\s*|按\s*)?(\d+(?:\.\d+)?)\s*兵/格|每格\s*(\d+(?:\.\d+)?)(?:\s*兵)?")


def windows(F, rows):
    land = F["land"]
    out = {}
    for me, b in F["bots"].items():
        tk = b["ticks"]
        ws = []
        for i in range(1, len(tk)):
            a, c = tk[i - 1], tk[i]
            exp = facts.interest_gain(a["terr"], land, a["bal"], a["t"], c["t"])
            nd = sum(1 for x in F.get("dons", []) if str(x.get("donor")) == str(me) and a["t"] <= x["t"] < c["t"])
            ws.append(dict(t0=a["t"], t1=c["t"], resid=c["bal"] - exp, terr0=a["terr"], terr1=c["terr"], outE=0, inE=0, amb=0,
                           dc=c["cmds"] - a["cmds"], db=c["boats"] - a["boats"], nDon=nd))
        out[str(me)] = ws
    for r in rows:
        for me, is_out in ((str(r["donor"]), True), (str(r["ally"]), False)):
            for w in out.get(me, []):
                if w["t0"] <= r["t"] < w["t1"]:
                    if r["status"] == "EXEC":
                        if is_out:
                            w["outE"] += r["amt"] + r["fee"]
                        else:
                            w["inE"] += r["amt"]
                    elif r["status"] == "AMB":
                        w["amb"] += 1
                    break
    return out


def flow_net(ws, t0, nwin):
    seg = [w for w in ws if w["t0"] >= t0][:nwin]
    seg2 = []
    for w in seg:            # 只取相连的窗
        if seg2 and w["t0"] != seg2[-1]["t1"]:
            break
        seg2.append(w)
    if not seg2 or seg2[0]["t0"] != t0:
        return None
    spent = -sum(w["resid"] + w["outE"] - w["inE"] for w in seg2)
    gain = seg2[-1]["terr1"] - seg2[0]["terr0"]
    don = sum(w["outE"] + w["inE"] for w in seg2)
    return dict(spent=round(spent), gain=gain, per=(spent / gain if gain > 0 else None), don=round(don), amb=sum(w["amb"] for w in seg2), t1=seg2[-1]["t1"], n=len(seg2))


def main():
    quiet = "--quiet" in sys.argv
    out = ["[FK-A] 逐局出手窗（DROP30、归因 ATTACK-GAIN、当窗领土净涨）：局 | 条数 | 有 donfit 定案 | 中位『每格』：单窗 / 两段 / 净值两窗 / 净值三窗 | 单窗比净值两窗高出一半以上的 | "
           "两窗合起来领土没涨的 | 两窗里有成交捐款的 | 有捐款的窗：两段 ÷ 净值两窗 的中位"]
    J = dict(matches={}, cited=[])
    cited_rows = []
    f = lambda x: "–" if x is None else f"{x:.1f}"  # noqa: E731
    allrows = []
    for mid in MINE:
        F = facts.full(mid)
        dp = os.path.join(OUT, mid, "donfit.json")
        rows = json.load(open(dp, encoding="utf-8"))["rows"] if os.path.exists(dp) else []
        if rows and not all(str(r["donor"]) in {str(k) for k in F["bots"]} for r in rows):
            rows = []
        W = windows(F, rows)
        eps = []
        for d in F["drop30"]:
            if d.get("cls") != "ATTACK-GAIN" or (d.get("dterr") or 0) <= 0:
                continue
            fn2 = flow_net(W.get(str(d["me"]), []), d["t0"], 2) or {}
            fn3 = flow_net(W.get(str(d["me"]), []), d["t0"], 3) or {}
            eps.append(dict(match=mid, bot=d["name"], t0=d["t0"], t1=d["t1"], dens0=d.get("dens0"), single=d.get("perPx"), two=d.get("perPx2"), epi=d.get("epiPerPx"),
                            net2=fn2.get("per"), net3=fn3.get("per"), spent2=fn2.get("spent"), gain2=fn2.get("gain"), spent3=fn3.get("spent"), gain3=fn3.get("gain"),
                            don=fn2.get("don"), amb=fn2.get("amb")))
        allrows += eps
        ok = [e for e in eps if e["net2"] is not None and e["net2"] > 0]

        def med(key, es):
            xs = [e[key] for e in es if e.get(key) is not None]
            return statistics.median(xs) if xs else None
        hi1 = sum(1 for e in ok if e["single"] is not None and e["single"] > 1.5 * e["net2"])
        wd = [e for e in ok if e["don"] and e["two"]]
        rd = statistics.median([e["two"] / e["net2"] for e in wd]) if wd else None
        J["matches"][mid] = dict(n=len(eps), donfit=bool(rows), medSingle=med("single", ok), medTwo=med("two", ok), medNet2=med("net2", ok), medNet3=med("net3", ok),
                                 singleHigh=hi1, noNet=len(eps) - len(ok), withDon=sum(1 for e in eps if e["don"]), twoOverNetWithDon=rd)
        out.append(f"    {mid} | {len(eps)} | {'有' if rows else '无'} | {f(med('single', ok))} / {f(med('two', ok))} / {f(med('net2', ok))} / {f(med('net3', ok))} | {hi1} | {len(eps) - len(ok)} | "
                   f"{sum(1 for e in eps if e['don'])} | {('%.2f' % rd) if rd else '–'}")
        rp = os.path.join(REV, f"{mid}.json")
        R = json.load(open(rp, encoding="utf-8"))
        for dec in R.get("decisions", []):
            txt = json.dumps({k: dec.get(k) for k in ("decision", "evidence")}, ensure_ascii=False)
            tnums = [int(x) for x in re.findall(r"\d+", str(dec.get("t") or ""))]
            lo, hi = (min(tnums) - 180, max(tnums) + 180) if tnums else (None, None)
            vals = []
            for m in NUM.finditer(txt):
                v = float(m.group(1) or m.group(2))
                if v not in vals:
                    vals.append(v)
            seen = set()
            for v in vals:
                hit = None
                for e in eps:
                    if lo is not None and not (lo <= e["t0"] <= hi):
                        continue
                    for basis in ("single", "two", "epi"):
                        x = e.get(basis)
                        if x is not None and abs(x - v) <= 0.6 and (str(e["bot"]) in txt):
                            hit = (e, basis)
                            break
                    if hit:
                        break
                if hit and (hit[0]["bot"], hit[0]["t0"], hit[1]) not in seen:
                    e, basis = hit
                    seen.add((e["bot"], e["t0"], basis))
                    cited_rows.append(dict(decision=dec["id"], pattern=dec.get("patternId"), cited=v, basis={"single": "单窗", "two": "两段", "epi": "续攻"}[basis], **e))
    n_all = len(allrows)
    ok_all = [e for e in allrows if e["net2"] is not None and e["net2"] > 0 and e["single"] is not None]
    out.append(f"    合计 | {n_all} | – | {f(statistics.median([e['single'] for e in ok_all]))} / {f(statistics.median([e['two'] for e in ok_all if e['two'] is not None]))} / "
               f"{f(statistics.median([e['net2'] for e in ok_all]))} / {f(statistics.median([e['net3'] for e in ok_all if e['net3'] is not None]))} | "
               f"{sum(1 for e in ok_all if e['single'] > 1.5 * e['net2'])}（{100 * sum(1 for e in ok_all if e['single'] > 1.5 * e['net2']) / max(1, len(ok_all)):.0f}%）| {n_all - len(ok_all)} | "
               f"{sum(1 for e in allrows if e['don'])} | –")
    out.append(f"    单窗 ÷ 净值两窗 的分布（{len(ok_all)} 条）：中位 {statistics.median([e['single'] / e['net2'] for e in ok_all]):.2f}，"
               f"四分位 {statistics.quantiles([e['single'] / e['net2'] for e in ok_all], n=4)[0]:.2f}~{statistics.quantiles([e['single'] / e['net2'] for e in ok_all], n=4)[2]:.2f}；"
               f"段首密度 ≥100 的 {sum(1 for e in ok_all if (e['dens0'] or 0) >= 100)} 条里中位 "
               f"{statistics.median([e['single'] / e['net2'] for e in ok_all if (e['dens0'] or 0) >= 100] or [0]):.2f}")
    hi_d = [e for e in ok_all if (e["dens0"] or 0) >= 100]
    lo_d = [e for e in ok_all if (e["dens0"] or 0) < 100]
    out.append(f"    净值两窗的每格（中位）：段首密度 ≥100 的 {len(hi_d)} 条 {f(statistics.median([e['net2'] for e in hi_d]) if hi_d else None)} 兵/格；"
               f"<100 的 {len(lo_d)} 条 {f(statistics.median([e['net2'] for e in lo_d]) if lo_d else None)} 兵/格"
               f"（<30 的 {sum(1 for e in lo_d if (e['dens0'] or 0) < 30)} 条 {f(statistics.median([e['net2'] for e in lo_d if (e['dens0'] or 0) < 30] or [0]))}）")
    J["all"] = dict(n=n_all, withNet=len(ok_all), singleOverNetMedian=statistics.median([e["single"] / e["net2"] for e in ok_all]),
                    net2MedianHiDens=(statistics.median([e["net2"] for e in hi_d]) if hi_d else None), net2MedianLoDens=(statistics.median([e["net2"] for e in lo_d]) if lo_d else None),
                    nHi=len(hi_d), nLo=len(lo_d))
    out.append("[FK-B] 复盘稿里引用过、能对上出手窗的数字：局 决策 模式 | 号 窗 | 引用值（口径）| 单窗 / 两段 | 净值两窗：花掉的兵 ÷ 涨的格 = 每格 | 净值三窗 | 净值两窗 ÷ 引用值 | 两窗里成交捐款的兵 / 没定案的条数 | 段首密度")
    for c in cited_rows:
        ratio = (c["net2"] / c["cited"]) if c["net2"] else None
        c["ratio"] = ratio
        out.append(f"    {c['match']} {c['decision']} {c['pattern']} | {c['bot']} {c['t0']}~{c['t1']} | {c['cited']}（{c['basis']}）| {f(c['single'])} / {f(c['two'])} | "
                   f"{c['spent2']} ÷ {c['gain2']} = {f(c['net2'])} | {f(c['net3'])} | {('%.2f' % ratio) if ratio else '–（两窗合起来没涨地）'} | {c['don']} / {c['amb']} | {c['dens0']}")
    J["cited"] = cited_rows
    n = len(cited_rows)
    with_net = [c for c in cited_rows if c.get("ratio")]
    lower = [c for c in with_net if c["ratio"] < 0.75]
    higher = [c for c in with_net if c["ratio"] > 1.25]
    sing = [c for c in cited_rows if c["basis"] == "单窗"]
    exp = [c for c in cited_rows if c["cited"] >= 90]
    exp_still = [c for c in exp if c.get("net2") is not None and c["net2"] >= 90]
    exp_lost = [c for c in exp if c.get("net2") is not None and c["net2"] < 90]
    exp_none = [c for c in exp if c.get("net2") is None]
    out.append(f"[FK-C] 小结：对上的引用 {n} 条（单窗口径 {len(sing)} 条，两段 / 续攻口径 {n - len(sing)} 条）；净值两窗算得出来的 {len(with_net)} 条里，"
               f"比引用值低 25% 以上的 {len(lower)} 条、高 25% 以上的 {len(higher)} 条、差在 ±25% 以内的 {len(with_net) - len(lower) - len(higher)} 条。")
    out.append(f"    引用值 ≥90 兵/格（当『高价』用的）{len(exp)} 条：净值两窗仍 ≥90 的 {len(exp_still)} 条；掉到 90 以下的 {len(exp_lost)} 条"
               + ("（" + "；".join(f"{c['match']} {c['decision']} {c['bot']} {c['cited']} → {c['net2']:.1f}" for c in exp_lost) + "）" if exp_lost else "")
               + f"；两窗合起来没涨地、算不出每格的 {len(exp_none)} 条"
               + ("（" + "；".join(f"{c['match']} {c['decision']} {c['bot']} {c['cited']}：花 {c['spent2']} 兵、领土 {c['gain2']:+d}" for c in exp_none) + "）" if exp_none else "") + "。")
    J["summary"] = dict(cited=n, citedSingle=len(sing), withNet=len(with_net), lower=len(lower), higher=len(higher), expensive=len(exp), expensiveStill=len(exp_still),
                        expensiveLost=len(exp_lost), expensiveNoNet=len(exp_none))
    od = os.path.join(OUT, "_cross")
    os.makedirs(od, exist_ok=True)
    open(os.path.join(od, "flowcheck.txt"), "w", encoding="utf-8").write("\n".join(out) + "\n")
    json.dump(J, open(os.path.join(od, "flowcheck.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"flowcheck: {len(out)} 行" if quiet else "\n".join(out))


if __name__ == "__main__":
    main()
