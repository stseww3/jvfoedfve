#!/usr/bin/env python3
"""donlogpairs.py — 捐款的对子账（日志口径：out/<局>/donfit.json 里余额拟合定案为成交的捐款）。

    python3 donlogpairs.py <matchId> [--quiet]   # 写 out/<matchId>/donlogpairs.txt 和 donlogpairs_sum.json

录像不够长（或没有录像）的局用它；有录像真值的段落以 donpairs.py 为准。
到账 / 税取 donfit 的拟合值（成交的才算）；状态（领土 / 余额 / 密度）取发令拍之前最近一条 HL-TICK。
节：
  [LA] 合计：成交笔数、到账、税、税 ÷ (到账 + 税)；按收款方是不是编队号拆开
  [LB] 对子：A→B 笔数 / 到账 / 税、B→A 笔数 / 到账 / 税、净额、来回倒掉的（两边到账里较小的一边 ×2）
  [LC] 各队分支：到账、税、净转移（各对子净额的绝对值之和）、来回倒掉的、倒掉的 ÷ 到账
  [LD] 逐号：捐出 笔数 / 到账 / 税，收到 笔数 / 到账，净额；整局利息（flow 口径：相邻 HL-TICK 之间按引擎利率滚的）没有就不列
  [LE] 收款方不在编队日志里的（撞名的陌生人等）：逐笔 拍 / 捐出方 / 种类 / pct / 到账 / 税 / 捐出方余额
  [LF] 收款后多少拍阵亡：≤300 / ≤600 / ≤1200 拍内阵亡的笔数、到账、税
  [LG] 600 拍内来回（A→B 之后 600 拍内 B→A）：次数、两笔里较小的到账合计、这些来回付的税
  [LH] 每 900 拍：成交笔数 / 到账 / 税 / 其中收款方当时密度 ≥100 的到账
"""
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    quiet = "--quiet" in sys.argv
    mid = args[0]
    od = os.path.join(OUT, mid)
    F = json.load(open(os.path.join(od, "facts.json")))
    D = json.load(open(os.path.join(od, "donfit.json")))
    bots = {int(k): v for k, v in F["bots"].items()}
    name = {k: v["name"] for k, v in bots.items()}
    rows = [r for r in D["rows"] if r["status"] == "EXEC"]
    allrows = D["rows"]
    out = []
    summ = dict(matchId=mid, basis="log-fit")

    def nm(p, r=None):
        if p in name:
            return name[p]
        return (r or {}).get("allyName") or f"#{p}"

    def state(p, t):
        b = bots.get(p)
        if not b:
            return None
        best = None
        for s in b["ticks"]:
            if s["t"] <= t:
                best = s
            else:
                break
        return best

    dead = {k: b["deathTick"] for k, b in bots.items() if b.get("event") == "died" and b.get("deathTick")}
    summ["deathTicks"] = {nm(k): v for k, v in dead.items()}

    tot_amt = sum(r["amt"] for r in rows)
    tot_fee = sum(r["fee"] for r in rows)
    sq_rows = [r for r in rows if r["ally"] in bots]
    wild_rows = [r for r in rows if r["ally"] not in bots]
    out.append(f"[LA] {mid} 捐款对子账（日志口径，余额拟合定案为成交的）：日志 {len(allrows)} 笔，成交 {len(rows)} 笔；到账 {tot_amt}，税 {tot_fee}（税 ÷ 付出 {100 * tot_fee / max(1, tot_amt + tot_fee):.1f}%）")
    for lab, rs in (("收款方是编队号", sq_rows), ("收款方不在编队日志里", wild_rows)):
        a = sum(r["amt"] for r in rs)
        f = sum(r["fee"] for r in rs)
        out.append(f"     {lab}：{len(rs)} 笔，到账 {a}，税 {f}（税 ÷ 付出 {100 * f / max(1, a + f):.1f}%）")
    summ["total"] = dict(logged=len(allrows), executed=len(rows), arrival=tot_amt, tax=tot_fee,
                         toSquad=dict(n=len(sq_rows), arrival=sum(r["amt"] for r in sq_rows), tax=sum(r["fee"] for r in sq_rows)),
                         toOutsider=dict(n=len(wild_rows), arrival=sum(r["amt"] for r in wild_rows), tax=sum(r["fee"] for r in wild_rows)))

    pair = defaultdict(lambda: dict(n=0, amt=0, fee=0))
    for r in rows:
        k = (r["donor"], r["ally"])
        pair[k]["n"] += 1
        pair[k]["amt"] += r["amt"]
        pair[k]["fee"] += r["fee"]
    seen = set()
    plist = []
    for (a, b), v in pair.items():
        key = tuple(sorted((a, b)))
        if key in seen:
            continue
        seen.add(key)
        ab = pair.get((key[0], key[1]), dict(n=0, amt=0, fee=0))
        ba = pair.get((key[1], key[0]), dict(n=0, amt=0, fee=0))
        net = ab["amt"] - ba["amt"]
        churn = 2 * min(ab["amt"], ba["amt"])
        plist.append((ab["amt"] + ba["amt"], key, ab, ba, net, churn))
    plist.sort(reverse=True)
    out.append("[LB] 对子（按两边到账合计排序）：A ↔ B | A→B 笔数 / 到账 / 税 | B→A 笔数 / 到账 / 税 | 净额（+ = A 净给 B）| 来回倒掉的（较小一边 ×2）")
    sp = []
    for tot, key, ab, ba, net, churn in plist:
        a, b = key
        an, bn = nm(a), nm(b)
        if b not in name:
            for r in rows:
                if r["ally"] == b:
                    bn = r["allyName"]
                    break
        if a not in name:
            for r in rows:
                if r["ally"] == a:
                    an = r["allyName"]
                    break
        out.append(f"     {an} ↔ {bn} | {ab['n']} / {ab['amt']} / {ab['fee']} | {ba['n']} / {ba['amt']} / {ba['fee']} | {net:+d} | {churn}")
        sp.append(dict(a=an, b=bn, ab=ab, ba=ba, net=net, churn=churn))
    summ["pairs"] = sp

    comp = {}
    for (a, b) in pair:
        ra = comp.setdefault(a, a)
        rb = comp.setdefault(b, b)
        if ra != rb:
            for k2, v2 in list(comp.items()):
                if v2 == rb:
                    comp[k2] = ra
    groups = defaultdict(list)
    for k2, v2 in comp.items():
        groups[v2].append(k2)
    out.append("[LC] 各队分支（按捐款对子连成的组）：成员 | 成交笔数 | 到账 | 税 | 净转移（各对子净额绝对值之和）| 来回倒掉的 | 倒掉的 ÷ 到账 | 税 ÷ 净转移")
    sc = []
    for root, mem in groups.items():
        ms = set(mem)
        rs = [r for r in rows if r["donor"] in ms]
        a = sum(r["amt"] for r in rs)
        f = sum(r["fee"] for r in rs)
        net = sum(abs(p[4]) for p in plist if p[1][0] in ms)
        churn = a - net
        names = []
        for m in sorted(mem):
            n2 = nm(m)
            if m not in name:
                for r in rows:
                    if r["ally"] == m:
                        n2 = r["allyName"] + "（不在编队日志里）"
                        break
            names.append(n2)
        out.append(f"     {' / '.join(names)} | {len(rs)} | {a} | {f} | {net} | {churn} | {100 * churn / max(1, a):.0f}% | {f / max(1, net):.2f}")
        sc.append(dict(members=names, n=len(rs), arrival=a, tax=f, net=net, churn=churn))
    summ["groups"] = sc

    out.append("[LD] 逐号：号 | 捐出 笔数 / 到账 / 税 | 收到 笔数 / 到账 | 净额（收到 − 捐出到账 − 税）")
    sd = []
    ids = sorted(set([r["donor"] for r in rows]) | set([r["ally"] for r in rows]))
    for p in ids:
        o = [r for r in rows if r["donor"] == p]
        i = [r for r in rows if r["ally"] == p]
        oa = sum(r["amt"] for r in o)
        of = sum(r["fee"] for r in o)
        ia = sum(r["amt"] for r in i)
        n2 = nm(p)
        if p not in name and i:
            n2 = i[0]["allyName"] + "（不在编队日志里）"
        out.append(f"     {n2} | {len(o)} / {oa} / {of} | {len(i)} / {ia} | {ia - oa - of:+d}")
        sd.append(dict(name=n2, outN=len(o), outArrival=oa, outTax=of, inN=len(i), inArrival=ia, net=ia - oa - of))
    summ["perBot"] = sd

    out.append("[LE] 收款方不在编队日志里的成交捐款：拍 | 捐出方 → 收款方 | 种类 pct | 到账 | 税 | 捐出方当时 余额 / 领土 / 密度 → 捐后密度")
    se = []
    for r in wild_rows:
        s = state(r["donor"], r["t"])
        terr = s["terr"] if s else None
        out.append(f"     {r['t']} | {nm(r['donor'])} → {r['allyName']} | {r['kind']} {r['pct']} | {r['amt']} | {r['fee']} | {r['myBal']} / {terr} / {r.get('densBefore')} → {r.get('densAfter')}")
        se.append(dict(t=r["t"], donor=nm(r["donor"]), to=r["allyName"], kind=r["kind"], pct=r["pct"], arrival=r["amt"], tax=r["fee"], donorBal=r["myBal"], donorTerr=terr))
    summ["toOutsiderRows"] = se

    out.append("[LF] 收款的编队号在收款后多少拍阵亡：档 | 笔数 | 到账 | 税")
    sf = {}
    for lim in (300, 600, 1200):
        rs = [r for r in sq_rows if r["ally"] in dead and 0 <= dead[r["ally"]] - r["t"] <= lim]
        a = sum(r["amt"] for r in rs)
        f = sum(r["fee"] for r in rs)
        out.append(f"     ≤{lim} 拍 | {len(rs)} | {a} | {f}")
        sf[str(lim)] = dict(n=len(rs), arrival=a, tax=f)
        if lim == 300:
            for r in rs:
                s = state(r["ally"], r["t"])
                out.append(f"        t={r['t']} {nm(r['donor'])} → {nm(r['ally'])} {r['kind']} {r['pct']}：到账 {r['amt']}，税 {r['fee']}；收款方当时 {s['terr'] if s else '?'} 格 / 密度 {s['dens'] if s else '?'}，{dead[r['ally']] - r['t']} 拍后阵亡")
    summ["receiverDiedWithin"] = sf

    out.append("[LG] 600 拍内来回（A→B 成交后 600 拍内 B→A 也成交；每笔回程只配一次）：对子 | 次数 | 两笔里较小的到账合计 | 这些来回两边付的税")
    used = set()
    back = defaultdict(lambda: dict(n=0, churn=0, tax=0))
    srt = sorted(rows, key=lambda r: r["t"])
    for i, r in enumerate(srt):
        for j in range(i + 1, len(srt)):
            q = srt[j]
            if q["t"] - r["t"] > 600:
                break
            if j in used:
                continue
            if q["donor"] == r["ally"] and q["ally"] == r["donor"]:
                used.add(j)
                k = tuple(sorted((r["donor"], r["ally"])))
                back[k]["n"] += 1
                back[k]["churn"] += min(r["amt"], q["amt"])
                back[k]["tax"] += r["fee"] + q["fee"]
                break
    sg = []
    for k, v in sorted(back.items(), key=lambda kv: -kv[1]["churn"]):
        out.append(f"     {nm(k[0])} ↔ {nm(k[1])} | {v['n']} | {v['churn']} | {v['tax']}")
        sg.append(dict(a=nm(k[0]), b=nm(k[1]), **v))
    tn = sum(v["n"] for v in back.values())
    out.append(f"     合计 {tn} 次，来回的兵 {sum(v['churn'] for v in back.values())}，付的税 {sum(v['tax'] for v in back.values())}")
    summ["roundTrips600"] = dict(n=tn, churn=sum(v["churn"] for v in back.values()), tax=sum(v["tax"] for v in back.values()), pairs=sg)

    out.append("[LH] 每 900 拍：窗 | 成交笔数 | 到账 | 税 | 收款方当时密度 ≥100 的 笔数 / 到账 | 捐出方当时密度 中位")
    sh = []
    if rows:
        t0 = (min(r["t"] for r in rows) // 900) * 900
        t1 = max(r["t"] for r in rows)
        w = t0
        while w <= t1:
            rs = [r for r in rows if w <= r["t"] < w + 900]
            if rs:
                hi = []
                for r in rs:
                    s = state(r["ally"], r["t"])
                    if s and s["terr"] > 0 and s["bal"] / s["terr"] >= 100:
                        hi.append(r)
                dd = sorted(r.get("densBefore") or 0 for r in rs)
                md = dd[len(dd) // 2]
                out.append(f"     {w}~{w + 899} | {len(rs)} | {sum(r['amt'] for r in rs)} | {sum(r['fee'] for r in rs)} | {len(hi)} / {sum(r['amt'] for r in hi)} | {md}")
                sh.append(dict(t0=w, n=len(rs), arrival=sum(r["amt"] for r in rs), tax=sum(r["fee"] for r in rs), hiN=len(hi), hiArrival=sum(r["amt"] for r in hi), donorDensMed=md))
            w += 900
    summ["windows900"] = sh

    txt = "\n".join(out) + "\n"
    with open(os.path.join(od, "donlogpairs.txt"), "w") as fh:
        fh.write(txt)
    with open(os.path.join(od, "donlogpairs_sum.json"), "w") as fh:
        json.dump(summ, fh, ensure_ascii=False, indent=1)
    if not quiet:
        sys.stdout.write(txt)


if __name__ == "__main__":
    main()
