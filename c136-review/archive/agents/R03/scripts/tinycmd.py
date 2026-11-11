#!/usr/bin/env python3
"""tinycmd.py — 机械计数：编队号「送出的兵比手续费还少」的指令（不重跑重放，读 out/cache/<局>-resim.json 的 cmdLog）。

引擎口径：陆攻每条收余额的 12/1024，发船每条收余额的 32/1024，与送出多少无关；所以 pct 很小的陆攻（pct < 12）和
装兵很少的船（pct < 32）手续费会比送出的兵多。

用法：
  python3 scripts/tinycmd.py <局> [--list]      --list 逐条列出（否则只打每个号的合计和最贵的 8 条）
产出（标准输出）：每个号 陆攻/发船 各多少条是「送出 < 手续费」，这些条送出合计、手续费合计、目标分类（AI / 空壳真人 / 在线真人 / 无主地）。
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEUTRAL = 512


def k(x):
    x = float(x)
    if abs(x) >= 1e6:
        return f"{x / 1e6:.2f}M"
    if abs(x) >= 1e4:
        return f"{x / 1e3:.0f}k"
    if abs(x) >= 1e3:
        return f"{x / 1e3:.1f}k"
    return f"{x:.0f}"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        sys.exit(2)
    mid = args[0]
    d = json.load(open(os.path.join(ROOT, "out", "cache", f"{mid}-resim.json")))
    H, names, teams, leftT = d["H"], d["names"], d["teams"], d["leftT"]
    sq = {v["id"]: n for n, v in d["squad"].items() if v["id"] >= 0 and not v.get("mismatch")}

    def cls(q, t):
        if q == NEUTRAL:
            return "无主地"
        if q >= H:
            return "AI"
        if leftT[q] is not None and 0 <= leftT[q] <= t:
            return "空壳真人"
        return "在线真人"

    def nm(q):
        if q == NEUTRAL:
            return "无主地"
        if q in sq:
            return sq[q]
        if q < H:
            return f"{names[q][:12]}#{q}T{teams[q]}"
        return f"AI{q}"

    rows = []
    tot_cmd = {1: 0, 3: 0}
    tot_fee = {1: 0, 3: 0}
    for r in d["cmdLog"]:
        t, p, kind, pct, q, ok = r[:6]
        if p not in sq or kind not in (1, 3) or not ok:
            continue
        sent, fee = r[6], r[7]
        tot_cmd[kind] += 1
        tot_fee[kind] += fee
        if sent < fee:
            tgt = r[10] if kind == 3 else q
            rows.append({"t": t, "bot": sq[p], "kind": kind, "pct": pct, "sent": sent, "fee": fee, "bal": r[8], "terr": r[9], "cls": cls(tgt, t), "tgt": nm(tgt)})
    print(f"# {mid} 送出 < 手续费 的指令（只算生效的；编队在场 {len(sq)} 个号）")
    print(f"  全部生效陆攻 {tot_cmd[1]} 条、手续费合计 {k(tot_fee[1])}；全部生效发船 {tot_cmd[3]} 条、船费合计 {k(tot_fee[3])}")
    for kind, label in ((1, "陆攻"), (3, "发船")):
        sub = [r for r in rows if r["kind"] == kind]
        if not sub:
            print(f"  {label}：0 条")
            continue
        by_cls = {}
        for r in sub:
            c = by_cls.setdefault(r["cls"], [0, 0, 0])
            c[0] += 1
            c[1] += r["sent"]
            c[2] += r["fee"]
        print(f"  {label}：{len(sub)} 条，送出合计 {k(sum(r['sent'] for r in sub))}，手续费合计 {k(sum(r['fee'] for r in sub))}；按目标 "
              + "、".join(f"{c} {v[0]} 条（送 {k(v[1])} 费 {k(v[2])}）" for c, v in sorted(by_cls.items(), key=lambda kv: -kv[1][2])))
        by_bot = {}
        for r in sub:
            c = by_bot.setdefault(r["bot"], [0, 0, 0, 9e9, 0])
            c[0] += 1
            c[1] += r["sent"]
            c[2] += r["fee"]
            c[3] = min(c[3], r["t"])
            c[4] = max(c[4], r["t"])
        for b, v in sorted(by_bot.items(), key=lambda kv: -kv[1][2]):
            print(f"    {b:<7} {v[0]:3d} 条（{v[3]:.0f}~{v[4]:.0f} 拍） 送出 {k(v[1])} 手续费 {k(v[2])}")
    if "--list" in sys.argv:
        show = rows
    else:
        show = sorted(rows, key=lambda r: -r["fee"])[:8]
        print("  手续费最贵的 8 条：")
    for r in sorted(show, key=lambda r: r["t"]):
        print(f"    {r['t']:5d} {r['bot']:<7} {'攻' if r['kind'] == 1 else '船'} pct={r['pct']:<4d} → {r['tgt']}（{r['cls']}） 送出 {k(r['sent'])} 手续费 {k(r['fee'])} | 余额 {k(r['bal'])} 地 {r['terr']}")


if __name__ == "__main__":
    main()
