#!/usr/bin/env python3
# 编队内捐款的「来回倒」核算：只读 out/cache/<mid>-resim.json（真值重演里每条已执行的捐款）。
# 用法：python3 scripts/pingpong.py <mid> [--win 100] [--from 0] [--bucket 1000] [--json 文件]
# 输出：
#   [1] 每一对（捐→收）：笔数、到账、税（捐出方整笔余额的 64/1024，game.js transfer L388-399）、pct 中位、
#       捐出方/接收方在这一笔前后的密度中位、接收方落地后高于软上限（>100×领土）/顶到硬上限（≥149.5×领土）的笔数。
#   [2] 来回倒（NEW-R01-DN07 的口径）：甲→乙 之后 win 拍内 乙→甲 的次数；每对的总流量、净流量、税。
#   [3] 利息核算（NEW-R01-DN10 的口径）：每笔落地当拍，按引擎利率公式（game.js interestRate L739-746 + economyTick L778-784）
#       算捐出方+接收方「每 10 拍利息」在这笔前后的合计变化；变化 ≤0 的笔数；变化 >0 的那些要多少拍才把税挣回来，
#       以及在挣回来之前接收方就把兵又捐出去（任何去向）的笔数。
#   [4] 按 bucket 拍分段的流量与税。
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MAXP = 512


def iV(a, b):
    return int((a + 0.5) // b)


def _mn(h, cs):
    a = iV(h + 1, 2)
    for _ in range(cs):
        a = iV(a + iV(h, a), 2)
    return a


TABLE = [100 + (0 if iV(25600 * i, MAXP - 4) < 1 else _mn(iV(25600 * i, MAXP - 4), 9)) for i in range(MAXP)]


def rate(terr, bal, t, land):
    n1 = TABLE[min(MAXP - 1, iV((MAXP - 1) * terr, land))]
    if t < 1920:
        n1 = max(iV(100 * (13440 - 6 * t), 1920), n1)
    cap = min(100 * terr, 1e9)
    if cap > 0 and bal > cap:
        n1 -= iV(2 * n1 * (bal - cap), cap)
    return min(max(n1, 0), 700)


def interest(terr, bal, t, land):
    return max(iV(rate(terr, bal, t, land) * bal, 1e4), 1)


def k(x):
    ax = abs(x)
    if ax >= 1e6:
        return f"{x / 1e6:.2f}M"
    if ax >= 1e4:
        return f"{x / 1e3:.0f}k"
    if ax >= 1e3:
        return f"{x / 1e3:.1f}k"
    return str(int(round(x)))


def med(a):
    if not a:
        return float("nan")
    s = sorted(a)
    return s[len(s) // 2]


def main():
    args = sys.argv[1:]
    mid = args[0]

    def opt(name, dflt):
        return type(dflt)(args[args.index(name) + 1]) if name in args else dflt

    win = opt("--win", 100)
    t_from = opt("--from", 0)
    bucket = opt("--bucket", 1000)
    jout = opt("--json", "")
    R = json.load(open(os.path.join(ROOT, "out", "cache", f"{mid}-resim.json")))
    land = R["land"]
    names = [n.replace("[APEX] ", "") for n in R["names"]]
    squad = {v["id"] for v in R["squad"].values() if v.get("id", -1) >= 0}
    dons = [c for c in R["cmdLog"] if c[2] == 2 and c[5] == 1 and c[0] >= t_from]
    rows = []
    for c in dons:
        t, p, _, pct, q, ok, got, tax, B0, L0, q0, cap, cost, Tq, bq0 = c[:15]
        dA0, dA1 = B0 / max(1, L0), (B0 - got - tax) / max(1, L0)
        dB0, dB1 = bq0 / max(1, Tq), (bq0 + got) / max(1, Tq)
        i0 = interest(L0, B0, t, land) + interest(Tq, bq0, t, land)
        i1 = interest(L0, B0 - got - tax, t, land) + interest(Tq, bq0 + got, t, land)
        want = min(iV((pct + 1) * B0, 1024), B0 - tax)
        rows.append(dict(t=t, p=p, q=q, pct=pct, got=got, tax=tax, dA0=dA0, dA1=dA1, dB0=dB0, dB1=dB1, dI=i1 - i0, i0=i0,
                         capped=got < want - 1, inSquad=(p in squad and q in squad)))
    out = {"mid": mid, "win": win, "from": t_from, "n": len(rows), "got": sum(r["got"] for r in rows), "tax": sum(r["tax"] for r in rows)}
    print(f"{mid} 编队内捐款来回倒核算（t≥{t_from}，已执行 {len(rows)} 笔，到账 {k(out['got'])}，税 {k(out['tax'])}）")

    # [1]
    by = defaultdict(list)
    for r in rows:
        by[(r["p"], r["q"])].append(r)
    print("[1] 每一对（捐→收）")
    out["pairs"] = []
    for (p, q), L in sorted(by.items(), key=lambda kv: -sum(r["got"] for r in kv[1])):
        o = dict(donor=names[p], recv=names[q], n=len(L), got=sum(r["got"] for r in L), tax=sum(r["tax"] for r in L), pctMed=med([r["pct"] for r in L]),
                 dA0=round(med([r["dA0"] for r in L]), 1), dA1=round(med([r["dA1"] for r in L]), 1), dB0=round(med([r["dB0"] for r in L]), 1), dB1=round(med([r["dB1"] for r in L]), 1),
                 recvOverSoft=sum(1 for r in L if r["dB1"] > 100), recvAtHard=sum(1 for r in L if r["dB1"] >= 149.5), capped=sum(1 for r in L if r["capped"]),
                 t0=L[0]["t"], t1=L[-1]["t"])
        out["pairs"].append(o)
        print(f"  {o['donor']}→{o['recv']}：{o['n']} 笔（{o['t0']}~{o['t1']}）到账 {k(o['got'])} 税 {k(o['tax'])}（税/到账 {o['tax'] / max(1, o['got']):.2f}）pct 中位 {o['pctMed']}；"
              f"捐出方密度中位 {o['dA0']}→{o['dA1']}，接收方 {o['dB0']}→{o['dB1']}；接收方落地后 >100 的 {o['recvOverSoft']} 笔、顶到硬上限 {o['recvAtHard']} 笔、被硬上限截短 {o['capped']} 笔")

    # [2]
    print(f"[2] 来回倒：甲→乙 之后 {win} 拍内 乙→甲")
    out["bounce"] = []
    und = defaultdict(lambda: dict(n=0, gross=0, tax=0, ab=0, ba=0, bounces=0, gaps=[]))
    for i, r in enumerate(rows):
        a, b = sorted((r["p"], r["q"]))
        u = und[(a, b)]
        u["n"] += 1
        u["gross"] += r["got"]
        u["tax"] += r["tax"]
        if r["p"] == a:
            u["ab"] += r["got"]
        else:
            u["ba"] += r["got"]
        for s in rows[i + 1:]:
            if s["t"] - r["t"] > win:
                break
            if s["p"] == r["q"] and s["q"] == r["p"]:
                u["bounces"] += 1
                u["gaps"].append(s["t"] - r["t"])
                break
    for (a, b), u in sorted(und.items(), key=lambda kv: -kv[1]["gross"]):
        net = abs(u["ab"] - u["ba"])
        o = dict(a=names[a], b=names[b], n=u["n"], gross=u["gross"], net=net, tax=u["tax"], ab=u["ab"], ba=u["ba"], bounces=u["bounces"], gapMed=med(u["gaps"]) if u["gaps"] else None)
        out["bounce"].append(o)
        print(f"  {o['a']}⇄{o['b']}：{o['n']} 笔，{o['a']}→{o['b']} {k(u['ab'])}、反向 {k(u['ba'])}；总流量 {k(u['gross'])}，净流量 {k(net)}（净/总 {net / max(1, u['gross']):.2f}），税 {k(u['tax'])}"
              f"（税/净流量 {u['tax'] / max(1, net):.1f}）；{win} 拍内掉头 {u['bounces']} 次" + (f"，间隔中位 {o['gapMed']} 拍" if u["gaps"] else ""))

    # [3]
    print("[3] 每笔落地当拍：捐出方+接收方「每 10 拍利息」合计的变化（引擎利率公式）")
    neg = [r for r in rows if r["dI"] <= 0]
    pos = [r for r in rows if r["dI"] > 0]
    early = 0
    pay = []
    for i, r in enumerate(pos):
        need = r["tax"] / (r["dI"] / 10.0)
        pay.append(need)
        idx = rows.index(r)
        for s in rows[idx + 1:]:
            if s["t"] - r["t"] > need:
                break
            if s["p"] == r["q"]:
                early += 1
                break
    out["interest"] = dict(n=len(rows), nonPositive=len(neg), nonPositiveTax=sum(r["tax"] for r in neg), positive=len(pos), positiveTax=sum(r["tax"] for r in pos),
                           sumDeltaPer10=sum(r["dI"] for r in rows), paybackMed=round(med(pay)) if pay else None, redonatedBeforePayback=early)
    oi = out["interest"]
    print(f"  合计变化 ≤0 的 {oi['nonPositive']} 笔（税 {k(oi['nonPositiveTax'])}）；>0 的 {oi['positive']} 笔（税 {k(oi['positiveTax'])}），"
          f"其中靠多出来的利息挣回税要的拍数中位 {oi['paybackMed']}，在挣回之前接收方又捐出去的 {oi['redonatedBeforePayback']} 笔；全部笔的「每 10 拍利息变化」加总 {k(oi['sumDeltaPer10'])}")
    # 分对
    for (p, q), L in sorted(by.items(), key=lambda kv: -sum(r["got"] for r in kv[1]))[:6]:
        n0 = sum(1 for r in L if r["dI"] <= 0)
        print(f"    {names[p]}→{names[q]}：≤0 的 {n0}/{len(L)} 笔，每 10 拍利息变化中位 {k(med([r['dI'] for r in L]))}（税中位 {k(med([r['tax'] for r in L]))}）")

    # [4]
    print(f"[4] 每 {bucket} 拍")
    bk = defaultdict(lambda: dict(n=0, got=0, tax=0))
    for r in rows:
        b = bk[r["t"] // bucket * bucket]
        b["n"] += 1
        b["got"] += r["got"]
        b["tax"] += r["tax"]
    out["buckets"] = []
    for b0 in sorted(bk):
        b = bk[b0]
        out["buckets"].append(dict(t0=b0, **b))
        print(f"  {b0}~{b0 + bucket - 1}：{b['n']} 笔 到账 {k(b['got'])} 税 {k(b['tax'])}")
    if jout:
        json.dump(out, open(jout, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
