#!/usr/bin/env python3
"""donburst.py — 「协防/调度一拥而上」：同一个受捐方在很短的时间里收到几个号的捐款。

数据：out/cache/<mid>-resim.json 的 cmdLog 捐款行（服务器实际处理的，ok=1 才算成交）
  [t, 号, 2, pct, 对象, ok, 到账, 税, 处理前余额, 处理前领土, 对象已用额度, 额度上限, 本笔点数, 对象领土, 对象处理前余额]

口径：同一个受捐方的成交捐款按处理拍排序，相邻两笔间隔 ≤ --gap（默认 30 拍）并成一串；
      只打「不同捐方 ≥ --min（默认 3）个」的串。
每串打：处理拍范围、受捐方、笔数与捐方个数、到账合计、税合计、
        受捐方第一笔前的 地/兵/密度、最后一笔后的 兵/密度（= 最后一笔前余额 + 最后一笔到账）、
        串里被硬上限截短的笔数（到账 < 按 pct 应送出的 95%，且对象处理前余额 + 到账 ≥ 149×对象领土）。
最后一行打全局合计。--squad-only 只看受捐方是本房间编队号的串（默认全部真人都看，便于和对手对照）。

用法：python3 scripts/donburst.py <mid> [--gap 30] [--min 3] [--squad-only]
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


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
    if not args:
        print(__doc__)
        sys.exit(2)
    mid = args[0]

    def opt(name, d=None):
        return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else d

    gap = int(opt("--gap", "30"))
    mn = int(opt("--min", "3"))
    squad_only = "--squad-only" in sys.argv
    d = json.load(open(os.path.join(ROOT, "out", "cache", f"{mid}-resim.json")))
    H, names = d["H"], d["names"]
    sq = {v["id"]: n for n, v in d["squad"].items() if v["id"] >= 0 and not v.get("mismatch")}

    def nm(p):
        if p in sq:
            return sq[p]
        return f"{names[p][:14]}#{p}T{d['teams'][p]}"

    by = {}
    for r in d["cmdLog"]:
        if r[2] != 2 or not r[5] or r[6] <= 0:
            continue
        by.setdefault(r[4], []).append(r)
    bursts = []
    for q, rows in by.items():
        if squad_only and q not in sq:
            continue
        rows.sort(key=lambda r: r[0])
        cur = [rows[0]]
        for r in rows[1:]:
            if r[0] - cur[-1][0] <= gap:
                cur.append(r)
            else:
                bursts.append((q, cur))
                cur = [r]
        bursts.append((q, cur))
    bursts = [(q, rs) for q, rs in bursts if len(set(r[1] for r in rs)) >= mn]
    bursts.sort(key=lambda x: x[1][0][0])
    print(f"# {mid} 捐款扎堆（同一受捐方、相邻两笔间隔 ≤{gap} 拍、不同捐方 ≥{mn} 个；只算成交的）"
          + ("；只看受捐方是编队号的" if squad_only else "") + f"：{len(bursts)} 串")
    print("# 处理拍 | 受捐方 | 笔数/捐方数 | 到账 税 | 受捐方：第一笔前 地/兵/密度 → 最后一笔后 兵/密度 | 被硬上限截短的笔数 | 捐方（到账）")
    tot = dict(n=0, cmds=0, got=0, tax=0, clipped=0, over100=0, over140=0)
    for q, rs in bursts:
        got = sum(r[6] for r in rs)
        tax = sum(r[7] for r in rs)
        L0, B0 = rs[0][13], rs[0][14]
        L1, B1 = rs[-1][13], rs[-1][14] + rs[-1][6]
        d0 = B0 / max(1, L0)
        d1 = B1 / max(1, L1)
        clipped = 0
        for r in rs:
            want = (r[3] + 1) * r[8] // 1024
            if r[6] < 0.95 * min(want, r[8] - r[7]) and r[14] + r[6] >= 149 * r[13]:
                clipped += 1
        who = " ".join(f"{nm(r[1])}({k(r[6])})" for r in rs)
        print(f"{rs[0][0]:5d}~{rs[-1][0]:<5d} | {nm(q):<12} | {len(rs)} 笔/{len(set(r[1] for r in rs))} 个号 | 到账 {k(got)} 税 {k(tax)} | "
              f"{L0} 格/{k(B0)}/密度 {d0:.0f} → {k(B1)}/密度 {d1:.0f} | 截短 {clipped} | {who}")
        tot["n"] += 1
        tot["cmds"] += len(rs)
        tot["got"] += got
        tot["tax"] += tax
        tot["clipped"] += clipped
        if d1 >= 100:
            tot["over100"] += 1
        if d1 >= 140:
            tot["over140"] += 1
    print(f"# 合计：{tot['n']} 串 {tot['cmds']} 笔，到账 {k(tot['got'])}，税 {k(tot['tax'])}；"
          f"串末受捐方密度 ≥100 的 {tot['over100']} 串、≥140 的 {tot['over140']} 串；被硬上限截短 {tot['clipped']} 笔")


if __name__ == "__main__":
    main()
