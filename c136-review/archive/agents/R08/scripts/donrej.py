#!/usr/bin/env python3
"""donrej.py — 日志里打印了、录像里却没有的捐款，逐笔查「到了引擎为什么没成交」。

    python3 donrej.py <matchId> [--replay-from X] [--peer X]      # 两步都做：先配对，再调 donquote.mjs 进真引擎问价

依据：统筹分发的 donation_ledger.mjs 头注——录像的捐款记录点在全部校验（队友、存活、金额≥1、受捐额度）之后，
所以「录像里没有的捐款」=发到引擎时被拒，或者根本没发出去。
做法：(1) 日志 HL-DONATE / HL-DISPATCH（号、本地拍 t、pct、受捐方）与真值重演里已执行的捐款逐笔配对（同号、同 pct、同受捐方、
执行拍 ≥ t−2，最早优先）；(2) 没配上的每一笔，在真引擎重演里从 t 起逐拍调用 donateQuote 的各个环节
（受捐方是否活着 / 是否队友 / 150×领土的硬上限余量 / 受捐额度），记下每一拍「如果这一拍执行会不会成交、卡在哪」；
(3) 用该号同期其它指令的实测时延（shadowcmp 的逐条配对）估出这笔捐款的大致执行拍，在 ±8 拍内找拒因。
输出：out/<mid>/donrej.txt
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import facts  # noqa: E402
from truth import Truth, OUT  # noqa: E402

WHY = {0: "可成交", 1: "受捐方已死", 2: "不是队友", 3: "受捐方到硬上限(150×领土)", 4: "超受捐额度", 5: "捐出方已死/已离开", 6: "金额<1"}


def pair(mid):
    T = Truth(mid)
    F = facts.build(mid)
    dons = facts.donation_ledger(F)
    ex = [c for c in T.R["cmdLog"] if c[2] == 2 and c[1] in T.sqIds]
    used = set()
    rows = []
    for d in dons:
        p = d["donor"]
        best = None
        for i, c in enumerate(ex):
            if i in used or c[1] != p or c[3] != d["pct"] or c[4] != d["ally"]:
                continue
            if c[0] < d["t"] - 2 or c[0] > d["t"] + 700:
                continue
            if best is None or c[0] < ex[best][0]:
                best = i
        if best is not None:
            used.add(best)
        rows.append(dict(t=d["t"], donor=p, to=d["ally"], pct=d["pct"], kind=d["kind"], line=d["line"], myBal=d["myBal"],
                         exec=None if best is None else ex[best][0]))
    return T, rows, len(ex) - len(used)


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1
    mid = args[0]
    T, rows, spare = pair(mid)
    un = [r for r in rows if r["exec"] is None]
    odir = os.path.join(OUT, mid)
    with open(os.path.join(odir, "don_unexec.json"), "w", encoding="utf-8") as f:
        json.dump(un, f)
    ev = {}
    if un:
        cmd = ["bash", os.path.join(HERE, "..", "..", "..", "tools", "run-heavy.sh"), "node", os.path.join(HERE, "donquote.mjs"), mid] + args[1:]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=115)
        if r.returncode != 0:
            print(r.stdout[-400:], r.stderr[-400:])
            return 1
        ev = {(e["t"], e["donor"], e["to"], e["pct"]): e for e in json.load(open(os.path.join(odir, "don_unexec_eval.json"), encoding="utf-8"))}
    out = []
    # 各号「决策拍 → 实测时延」：来自影子决策与录像的逐条配对（shadowcmp.match_bot）；没有 shadow.json 时退回捐款自身的配对
    lag_tab = {}
    sp = os.path.join(odir, "shadow.json")
    if os.path.exists(sp):
        import shadowcmp as SC
        S = json.load(open(sp, encoding="utf-8"))
        for name, sb in S["bots"].items():
            try:
                real, sh, used, pairs = SC.match_bot(T, name, sb)
            except Exception:
                continue
            lag_tab[sb["id"]] = sorted((sh[i][0], lag) for c, i, lag in pairs if i is not None)
    lags = sorted(r["exec"] - r["t"] for r in rows if r["exec"] is not None)
    out.append(f"[DR] {mid} 日志捐款 {len(rows)} 笔：配上已执行 {len(rows) - len(un)}，录像里没有 {len(un)}；已执行但没配上日志 {spare}")
    if lags:
        out.append(f"     已执行的：本地拍→执行拍 时延 中位 {lags[len(lags) // 2]}，最大 {lags[-1]}，≥35 拍的 {sum(1 for x in lags if x >= 35)} 笔")
    out.append("     没执行的逐笔：本地拍 捐出→受捐 pct 种类 | 估计执行拍（依据）| 那一拍的结果 | 之后 400 拍内第一拍可成交 | 各拒因占的拍数")
    cnt = {}
    for r in un:
        e = ev.get((r["t"], r["donor"], r["to"], r["pct"]))
        # 估计执行拍：同一个号、本地拍相差 ≤60 的已执行捐款的时延中位；没有就用全局中位
        near = sorted(x["exec"] - x["t"] for x in rows if x["exec"] is not None and x["donor"] == r["donor"] and abs(x["t"] - r["t"]) <= 60)
        tab = lag_tab.get(r["donor"], [])
        near2 = sorted(l for (td, l) in tab if abs(td - r["t"]) <= 90)
        if near:
            lag, src = near[len(near) // 2], "同号邻近已执行捐款"
        elif near2:
            lag, src = near2[len(near2) // 2], "同号 ±90 拍内其它指令的实测时延"
        elif tab:
            td, lag = min(tab, key=lambda x: abs(x[0] - r["t"]))
            src = f"同号最近一条配上的指令（决策拍 {td}）"
        else:
            lag, src = (lags[len(lags) // 2] if lags else 12), "全局中位"
        te = r["t"] + lag
        if e and not e.get("seq"):
            out.append(f"     {r['t']} {T.nm(r['donor'], r['t'])}→{T.nm(r['to'], r['t'])} pct={r['pct']} {r['kind']} | {te} | （决策拍在录像结束之后，问不了价）")
            cnt["录像结束之后"] = cnt.get("录像结束之后", 0) + 1
        elif e:
            seq = e["seq"]  # [[t0, code], ...] 游程
            def code_at(t):
                c = None
                for t0, cc in seq:
                    if t0 <= t:
                        c = cc
                    else:
                        break
                return c
            # 执行拍只能估到 ±1 个服务器回合（7 拍），同一回合里几条指令谁先谁后也不知道：
            # 在 [te-8, te+8] 里只要有一拍会被拒，就按那个拒因记（优先级：已死 > 硬上限 > 额度 > 金额 > 捐出方）
            cs = {code_at(x) for x in range(max(r["t"], te - 8), te + 9)}
            c = next((k for k in (1, 3, 4, 6, 5) if k in cs), 0)
            first_ok = next((t0 for t0, cc in seq if cc == 0 and t0 >= r["t"]), None)
            span = {}
            for (t0, cc), nxt in zip(seq, seq[1:] + [[e.get("tEnd", (seq[-1][0] + 1) if seq else r["t"]), None]]):
                span[cc] = span.get(cc, 0) + (nxt[0] - t0)
            why = WHY.get(c, "?")
            if c == 0:
                why = "估计拍前后都可成交（没发到引擎：补拍时一个回合最多落地 8~9 条，多出来的被丢；或执行拍估错）" if lag >= 35 else "估计拍前后都可成交（原因不明）"
            cnt[why] = cnt.get(why, 0) + 1
            out.append(f"     {r['t']} {T.nm(r['donor'], r['t'])}→{T.nm(r['to'], r['t'])} pct={r['pct']} {r['kind']} | {te}（{src} {lag} 拍）| {why}"
                       f"{'；额度 ' + next((e['qAt'][str(x)] for x in range(max(r['t'], te - 8), te + 9) if str(x) in e['qAt']), '') if c == 4 else ''} | {first_ok if first_ok is not None else '无'} | "
                       + "，".join(f"{WHY.get(k, k)} {v}" for k, v in sorted(span.items(), key=lambda kv: -kv[1])))
        else:
            out.append(f"     {r['t']} {T.nm(r['donor'], r['t'])}→{T.nm(r['to'], r['t'])} pct={r['pct']} {r['kind']} | {te} | （没有引擎问价结果）")
    out.append("     估计拒因合计：" + "，".join(f"{k} {v}" for k, v in sorted(cnt.items(), key=lambda kv: -kv[1])))
    txt = "\n".join(out)
    with open(os.path.join(odir, "donrej.txt"), "w", encoding="utf-8") as f:
        f.write(txt + "\n")
    print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
