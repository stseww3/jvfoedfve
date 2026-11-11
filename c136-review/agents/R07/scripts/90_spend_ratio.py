#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""90_spend_ratio.py — 各组在一段时间里把收入花到了哪里（进攻 / 手续费 / 挨打）。R07

用法（在 scripts/ 目录下）：
    python3 90_spend_ratio.py <matchId> --span t0:t1 [--span t0:t1]... [--tag tp]

输入：out/<matchId>/side_flow[_<tag>].json（74_side_flow.mjs 的分组 × 阶段流水；--tag 默认 tp）。
      span 的两端必须正好落在 74_side_flow 的切点上（否则报错，不做插值）。
口径（都是 74_side_flow.mjs 的原始栏目按阶段相加）：
  收入 = 利息地租（eco：每拍结算里的正项）
  进攻净消耗 = 发出的兵（无主地 + 内置 AI + 真人）− 进攻结束退回的兵
  手续费 = 陆攻费 + 发船费 + 捐款费
  挨打掉 = 每拍结算的余额差里扣掉利息地租、退兵、收到的兵之后的缺口
  各项 ÷ 收入 给出占比；余额、领土取 span 两端。
  每人 = 除以 span 第一个阶段期初的在场人数（n0）；退回 = 进攻结束（目标被吃光 / 边界断开）退回余额的兵。
输出：out/<matchId>/spend_ratio[_<tag>].txt
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def fmt(n):
    return f"{int(round(n)):,}"


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    mid = args[0]
    tag = args[args.index("--tag") + 1] if "--tag" in args else "tp"
    spans = []
    for i, a in enumerate(args):
        if a == "--span":
            t0, t1 = args[i + 1].split(":")
            spans.append((int(t0), int(t1)))
    out = os.path.join(HERE, "..", "out", mid)
    src = os.path.join(out, f"side_flow_{tag}.json" if tag else "side_flow.json")
    d = json.load(open(src, encoding="utf-8"))
    phases = d["phases"]
    cuts = sorted({p["t0"] for p in phases} | {p["t1"] for p in phases})
    if not spans:
        spans = [(cuts[0], cuts[-1])]
    L = [f"# {mid} 各组把收入花到了哪里（{os.path.basename(src)} 的阶段相加；切点 {','.join(str(c) for c in cuts)}）",
         "# 栏目：收入（利息地租）| 进攻净消耗（占收入）| 手续费 攻 / 船 / 捐（合计占收入）| 挨打掉（占收入）| 捐款 笔 / 到账 | 进攻 条 / 发兵 | 领土 期初→期末 | 余额 期初→期末 | 密度 期初→期末"]
    for t0, t1 in spans:
        if t0 not in cuts or t1 not in cuts:
            print(f"span {t0}:{t1} 不在切点上：{cuts}")
            sys.exit(2)
        ph = [p for p in phases if p["t0"] >= t0 and p["t1"] <= t1]
        L.append("")
        L.append(f"## t={t0}~{t1}（{len(ph)} 个阶段）")
        groups = list(ph[0]["row"].keys())
        for g in groups:
            rows = [p["row"][g] for p in ph if g in p["row"]]
            if not rows:
                continue
            eco = sum(r["eco"] for r in rows)
            burn = sum(r["burn"] for r in rows)
            af = sum(r["atkFee"] for r in rows)
            bf = sum(r["boatFee"] for r in rows)
            df = sum(r["donFee"] for r in rows)
            hit = sum(r["hit"] for r in rows)
            don_n = sum(r["donN"] for r in rows)
            don_amt = sum(r["donAmt"] for r in rows)
            atk_n = sum(r["atkN"] for r in rows)
            sent = sum(r["tN"] + r["tA"] + r["tH"] for r in rows)
            terr0, terr1 = rows[0]["terr0"], rows[-1]["terr1"]
            bal0, bal1 = rows[0]["bal0"], rows[-1]["bal1"]
            pc = (lambda x: f"{100 * x / eco:.0f}%") if eco > 0 else (lambda x: "-")
            n0 = max(1, rows[0].get("n0") or 1)
            t_ai = sum(r["tA"] for r in rows)
            refund = sum(r["refund"] for r in rows)
            L.append(f"  {g}：收入 {fmt(eco)} | 进攻净消耗 {fmt(burn)}（{pc(burn)}）| 手续费 {fmt(af)} / {fmt(bf)} / {fmt(df)}（{pc(af + bf + df)}）| 挨打掉 {fmt(hit)}（{pc(hit)}）| "
                     f"捐款 {don_n} 笔 / {fmt(don_amt)} | 进攻 {atk_n} 条 / {fmt(sent)} | 领土 {fmt(terr0)}→{fmt(terr1)} | 余额 {fmt(bal0)}→{fmt(bal1)} | "
                     f"密度 {bal0 / max(1, terr0):.0f}→{bal1 / max(1, terr1):.0f} | "
                     f"期初 {n0} 人：每人净消耗 {fmt(burn / n0)}、每人打 AI {fmt(t_ai / n0)}、每人领土 {terr1 / n0 - terr0 / n0:+,.0f}；退回 {fmt(refund)}（占发兵 {100 * refund / max(1, sent):.0f}%）")
    txt = "\n".join(L) + "\n"
    dst = os.path.join(out, f"spend_ratio_{tag}.txt" if tag else "spend_ratio.txt")
    open(dst, "w", encoding="utf-8").write(txt)
    print(txt)


if __name__ == "__main__":
    main()
