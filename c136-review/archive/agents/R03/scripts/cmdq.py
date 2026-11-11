#!/usr/bin/env python3
"""cmdq.py — 从重放缓存里按号、按拍段打出服务器实际处理的指令（不重跑重放）。

out/cache/<mid>-resim.json 的 cmdLog 每条：
  陆攻 [t, 号, 1, pct, 目标, ok, 送出的兵, 手续费, 处理前余额, 处理前领土, 处理前对该目标是否已有在途兵]
  捐款 [t, 号, 2, pct, 对象, ok, 到账, 税, 处理前余额, 处理前领土, 对象已用额度, 额度上限, 本笔点数, 对象领土, 对象处理前余额]
  发船 [t, 号, 3, pct, 落点格, ok, 上船的兵, 船费, 处理前余额, 处理前领土, 落点归属]

用法：
  python3 scripts/cmdq.py <mid> <号[,号…]|squad|all> <t0> <t1> [--kind 1,2,3] [--target 名字片段] [--batch]
  --batch  按（号、处理拍）合并成批：条数、pct 列表、批前余额、批内送出合计、批后剩余比例
号可以写名字（kaito9）或席位号（15）；squad = 编队 10 个号；all = 全部真人。
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
NEUTRAL = 512


def k(v):
    v = float(v)
    a = abs(v)
    if a >= 1e6:
        return "%.2fM" % (v / 1e6)
    if a >= 1e4:
        return "%.0fk" % (v / 1e3)
    if a >= 1e3:
        return "%.1fk" % (v / 1e3)
    return "%d" % v


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 4:
        print(__doc__)
        sys.exit(2)
    mid, who, t0, t1 = args[0], args[1], int(args[2]), int(args[3])

    def opt(name, d=None):
        return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else d

    kinds = set(int(x) for x in opt("--kind", "1,2,3").split(","))
    tgt = opt("--target")
    d = json.load(open(os.path.join(ROOT, "out", "cache", f"{mid}-resim.json")))
    H, names = d["H"], d["names"]
    sq = {v["id"]: n for n, v in d["squad"].items()}

    def nm(p):
        if p == NEUTRAL:
            return "无主地"
        if p in sq:
            return sq[p]
        if p < H:
            return f"{names[p][:14]}#{p}T{d['teams'][p]}"
        return f"AI{p}"

    if who == "squad":
        ids = set(sq)
    elif who == "all":
        ids = set(range(H))
    else:
        ids = set()
        for w in who.split(","):
            if w.isdigit():
                ids.add(int(w))
            else:
                ids.add(d["squad"][w]["id"])
    rows = [r for r in d["cmdLog"] if t0 <= r[0] <= t1 and r[1] in ids and r[2] in kinds]
    if tgt:
        rows = [r for r in rows if tgt in nm(r[4]) or (r[2] == 3 and tgt in nm(r[10]))]
    print(f"# {mid} cmdLog {who} {t0}~{t1} kinds={sorted(kinds)}" + (f" target~{tgt}" if tgt else "") + f"：{len(rows)} 条")
    if "--batch" in sys.argv:
        by = {}
        for r in rows:
            by.setdefault((r[1], r[0]), []).append(r)
        print("# 号 处理拍 | 条数（生效） | 目标 | pct | 批前余额 领土 | 送出+手续费 合计 | 批后剩余/批前")
        for (p, t), lst in sorted(by.items(), key=lambda kv: (kv[0][1], kv[0][0])):
            B0, L0 = lst[0][8], lst[0][9]
            spent = sum((r[6] + r[7]) for r in lst if r[5])
            tg = {}
            for r in lst:
                key = nm(r[10]) + "(船)" if r[2] == 3 else (("捐→" if r[2] == 2 else "") + nm(r[4]))
                tg[key] = tg.get(key, 0) + 1
            print(f"{nm(p):8s} {t:5d} | {len(lst)}（{sum(1 for r in lst if r[5])}） | {' '.join(f'{a}×{b}' for a, b in tg.items())} | "
                  f"{[r[3] for r in lst]} | {k(B0)} {L0} | {k(spent)} | {(B0 - spent) / max(1, B0):.3f}")
        return
    print("# 处理拍 号 种类 pct 目标 ok | 送出/到账 手续费/税 | 处理前余额 领土 | 备注")
    for r in rows:
        t, p, kind, pct, q, ok = r[:6]
        if kind == 1:
            note = "已有在途" if r[10] else ""
            print(f"{t:5d} {nm(p):8s} 攻 pct={pct:4d} → {nm(q):22s} ok={ok} | {k(r[6]):>7s} {k(r[7]):>6s} | {k(r[8]):>7s} {r[9]:6d} | {note}")
        elif kind == 2:
            print(f"{t:5d} {nm(p):8s} 捐 pct={pct:4d} → {nm(q):22s} ok={ok} | {k(r[6]):>7s} {k(r[7]):>6s} | {k(r[8]):>7s} {r[9]:6d} | 对象额度 {r[10]}+{r[12]}/{r[11]} 对象 地 {r[13]} 兵 {k(r[14])}")
        elif kind == 3:
            print(f"{t:5d} {nm(p):8s} 船 pct={pct:4d} → 落点归属 {nm(r[10]):14s} ok={ok} | {k(r[6]):>7s} {k(r[7]):>6s} | {k(r[8]):>7s} {r[9]:6d} |")


if __name__ == "__main__":
    main()
