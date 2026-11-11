#!/usr/bin/env python3
"""ledger-table.py — 把已做完延迟账/抢地账的各局拼成两张跨局表（markdown），供 CROSS-MATCH-SUMMARY 和留言引用。

    python3 scripts/ledger-table.py [<mid> ...]      # 不给局号 = out/dossier 下所有带 delay-facts 或 land-facts 的局
    写 out/dossier/ledger-table.md
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DOS = os.path.join(ROOT, "out", "dossier")


def _load(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _wan(x):
    if x is None:
        return "—"
    if abs(x) >= 1e5:
        return f"{x / 1e4:.0f}万"
    if abs(x) >= 1e4:
        return f"{x / 1e4:.1f}万"
    return f"{x:,.0f}"


def _p(a, b, nd=0):
    return f"{100 * a / b:.{nd}f}%" if b else "—"


def main():
    mids = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not mids:
        s = set()
        for p in glob.glob(os.path.join(DOS, "*-delay-facts.json")) + glob.glob(os.path.join(DOS, "*-land-facts.json")):
            s.add(os.path.basename(p).split("-")[0])
        mids = sorted(s)
    out = []
    w = out.append
    w("# 延迟账与抢地账跨局表（ledger-table.py；每格数字取自对应局的 out/dossier/<局>-delay-facts.json / <局>-land-facts.json / out/cache/<局>-freeze.json）")
    w("")
    w("## 表 1　延迟与执行")
    w("")
    w("| 局 | 选点：重解轮数 / 没落到终解的号 / 叠点对 | 延迟 P50/P90/最大：0~600 | 600~1500 | 1500~3000 | 3000+ | 陆攻+船：想发→受理→落地→生效 | 捐款：受理→落地 | 600~1500 落地率 | 600~1500 目标已死改道（条 / 兵 / 占打 AI+真人兵） | 作废 | 落地前重发：后续÷首条 | 同拍 ≥3 条的批 / 抽走余额 ≥50% 的批（兵） | 延迟>45 拍后的补发串（发/落/花） |")
    w("| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |")
    for mid in mids:
        d = _load(os.path.join(DOS, f"{mid}-delay-facts.json"))
        if not d:
            continue
        sp = d["spawn"]
        lg = {r["period"]: r for r in d["lag"]["byPeriod"]}
        fn = d["funnel"]
        fp = {r["period"]: r for r in fn["byPeriod"]}
        lt = {r["period"]: r for r in d["late"]["byPeriod"]}
        ri = d["reissue"]["total"]
        sb = d["sameTickBatches"]["byPeriod"]

        def lag(per):
            r = lg.get(per)
            return f"{r['p50']}/{r['p90']}/{r['max']}（{r['n']}）" if r and r["n"] else "—"
        m = lt.get("600~1500") or {}
        tp = (m.get("troopsAI", 0) + m.get("troopsHuman", 0))
        f6 = fp.get("600~1500")
        w(f"| {mid} | {sp.get('rounds', 0)} / {sp.get('notOnFinal', 0)} / {len(sp.get('stackPairs', []))} | {lag('0~600')} | {lag('600~1500')} | {lag('1500~3000')} | {lag('3000+')} | "
          + "→".join(str(sum(r[k]["attack"] + r[k]["boat"] for r in fn["byPeriod"])) for k in ("want", "acc", "land", "eff")) + " | "
          + "→".join(str(sum(r[k]["donate"] for r in fn["byPeriod"])) for k in ("acc", "land")) + " | "
          + (f"{_p(f6['land']['total'], f6['acc']['total'])}（{f6['acc']['total']}→{f6['land']['total']}）" if f6 and f6["acc"]["total"] else "—") + " | "
          f"{m.get('deadTarget', 0)} / {_wan(m.get('deadTargetTroops', 0))} / {_p(m.get('deadTargetTroops', 0), tp, 1)} | {m.get('deadTargetNoop', 0)} | "
          + (f"{ri['syncExtra'] / ri['syncFirst']:.2f}（{ri['syncStrings']} 串）" if ri["syncFirst"] else "—") + " | "
          f"{sum(r['batches'] for r in sb)} / {sum(r['drain50'] for r in sb)}（{_wan(sum(r['drain50Spent'] for r in sb))}） | "
          f"{ri['lagStrings']}（{ri['lagIssued']}/{ri['lagExecuted']}/{_wan(ri['lagSpent'])}） |")
    w("")
    w("延迟 = 服务器处理拍 − 页面发令拍，括号里是条数；漏斗四级 = 策略想发 / 页面受理 / 录像落地 / 落地且非空令；捐款「受理→落地」之间掉的主要是撞额度（页面受理后游戏客户端不发出，录像里没有这条）；「目标已死改道」= 瞄准 AI 或真人、落地时目标已不存在、被引擎改成打无主地（没有相邻无主地就作废）。")
    w("")
    w("## 表 2　出生份额与实际抢到")
    w("")
    w("| 局 | 真人 / 编队号 | 编队名下占全图 / 人头占比 → 份额÷人头 | 每号名下中位 对 其他真人中位 | 630 拍 地÷名下：编队 对 其他真人 | 1500 拍 地÷名下：编队 对 其他真人 | 1500 拍 人均地：编队÷其他真人 = 出生份额 × 转化 | 接壤 AI 的地（600 拍定格 → 1800 拍）：格数 → 编队 / 同队路人 / 敌方真人 | 我方名下范围里的 AI 地 → 编队 / 敌方真人 | 开局买 AI 地的决策拍：被 safeFinite 冻结 / 总数（卡在编队友） |")
    w("| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |")
    for mid in mids:
        g = _load(os.path.join(DOS, f"{mid}-land-facts.json"))
        if not g:
            continue
        v = g["voronoi"]
        cap = {r["t"]: r for r in g.get("capture", [])}
        fz = _load(os.path.join(ROOT, "out", "cache", f"{mid}-freeze.json"))

        def cp(t):
            r = cap.get(t)
            return f"{r['squadRatio']:.2f} 对 {r['othersRatio']:.2f}" if r else "—"
        r = cap.get(1500)
        ident = "—"
        if r and r["squadAlive"] and r["humansAlive"] > r["squadAlive"] and r["othersRatio"]:
            on = r["humansAlive"] - r["squadAlive"]
            a = (r["squadTerr"] / r["squadAlive"]) / (r["othersTerr"] / on)
            b = (r["squadCells"] / r["squadAlive"]) / (r["othersCells"] / on)
            ident = f"{a:.2f} = {b:.2f} × {r['squadRatio'] / r['othersRatio']:.2f}" + (f"（在场 {r['squadAlive']}/{v['squadBots']} 个号）" if r["squadAlive"] < v["squadBots"] else "")
        af = g.get("aiFate")
        if af and af["B"]["rows"]:
            x = af["B"]["rows"][-1]
            y = af["A"]["rows"][-1]
            ai_b = f"{af['B']['cells']:,} → {_p(x['squad'], x['n'])} / {_p(x['mate'], x['n'])} / {_p(x['enemy'], x['n'])}" + (f"（{x['t']} 拍）" if x["t"] != 1800 else "")
            ai_a = f"{af['A']['cells']:,} → {_p(y['squad'], y['n'])} / {_p(y['enemy'], y['n'])}"
        else:
            ai_b = ai_a = "—"
        fzs = "—"
        if fz:
            t = fz["team"]
            fzs = f"{t['frozen']} / {t['ticks']}（{_p(t['frozen'], t['ticks'])}；{t.get('frozenBy', {}).get('squad', 0)}）"
        w(f"| {mid} | {v['humans']} / {v['squadBots']} | {v['squadCellsPct']}% / {v['headPct']}% → {v['shareOverHead']:.2f} | {v['squadMedian']:,.0f} 对 {v['othersMedian']:,.0f} | {cp(630)} | {cp(1500)} | {ident} | {ai_b} | {ai_a} | {fzs} |")
    w("")
    w("「名下」= 把每格陆地分给直线最近的真人出生点后落到该号头上的格数（不看地形、不看内置 AI）；「地÷名下」= 该拍实际领土 ÷ 名下格数；恒等式里「出生份额」= 编队人均名下 ÷ 其他真人人均名下，「转化」= 编队 地÷名下 ÷ 其他真人 地÷名下，两项相乘就是人均地之比（只算该拍还在场的号）。")
    txt = "\n".join(out) + "\n"
    with open(os.path.join(DOS, "ledger-table.md"), "w", encoding="utf-8") as f:
        f.write(txt)
    print(txt)


if __name__ == "__main__":
    main()
