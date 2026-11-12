#!/usr/bin/env python3
"""dispatchq.py — 把一局 events.csv 里的调度行（策略日志 HL-DISPATCH）按类型数出来，可按受捐方、拍段过滤。
只读 c136-data/bundles/<局>/events.csv，不重跑重放。

用法：
  python3 scripts/dispatchq.py <局> [--to 名字] [--from 名字] [--range t0 t1] [--list]
  --list  逐条列出（否则只打合计：按类型、按 受捐方×类型、按 捐方是否被围×类型、按 1000 拍分段）

每条：拍 号 类型 pct → 受捐方 | 捐方是否被围（boxedIn）余额 dMe dAlly | 页面标的 likelyRejected
（拍是页面本地拍；成交与否要看卷宗[H]，这里只是策略想发的）
"""
import collections
import csv
import os
import sys

DATA = os.environ.get("C136_DATA", "/agent/repos/c136-data")


def main():
    args = sys.argv[1:]
    if not args or args[0].startswith("--"):
        print(__doc__)
        sys.exit(2)
    mid = args[0]
    to = args[args.index("--to") + 1] if "--to" in args else None
    frm = args[args.index("--from") + 1] if "--from" in args else None
    t0, t1 = 0, 10 ** 9
    if "--range" in args:
        i = args.index("--range")
        t0, t1 = int(args[i + 1]), int(args[i + 2])
    rows = []
    with open(os.path.join(DATA, "bundles", mid, "events.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["type"] != "DISPATCH":
                continue
            t = int(float(r["t"]))
            if not (t0 <= t <= t1):
                continue
            if to and r["targetName"] != to:
                continue
            if frm and r["bot"] != frm:
                continue
            rows.append((t, r))
    flt = "".join([f" 受捐方={to}" if to else "", f" 捐方={frm}" if frm else "", f" 拍段 {t0}~{t1}" if "--range" in args else ""])
    kinds = collections.Counter(r["kind"] for _, r in rows)
    print(f"# {mid} events.csv 的调度行{flt}：合计 {len(rows)} 条：" + "，".join(f"{k} {n}" for k, n in kinds.most_common()))
    by_to = collections.defaultdict(collections.Counter)
    by_box = collections.defaultdict(collections.Counter)
    by_seg = collections.defaultdict(collections.Counter)
    dme = collections.defaultdict(list)
    dally = collections.defaultdict(list)
    denser = collections.Counter()
    over100 = collections.Counter()
    for t, r in rows:
        by_to[r["targetName"]][r["kind"]] += 1
        by_box[r["boxedIn"]][r["kind"]] += 1
        by_seg[t // 1000 * 1000][r["kind"]] += 1
        try:
            a, b = float(r["dMe"]), float(r["dAlly"])
        except ValueError:
            continue
        dme[(r["kind"], r["boxedIn"])].append(a)
        dally[(r["kind"], r["boxedIn"])].append(b)
        if b > a:
            denser[r["kind"]] += 1
        if b >= 100:
            over100[r["kind"]] += 1
    print("  按受捐方：" + "；".join(f"{n} " + " ".join(f"{k}×{c}" for k, c in v.most_common()) for n, v in sorted(by_to.items(), key=lambda kv: -sum(kv[1].values()))))
    print("  按捐方是否被围：" + "；".join(f"boxedIn={b} " + " ".join(f"{k}×{c}" for k, c in v.most_common()) for b, v in sorted(by_box.items())))
    print("  捐方发令时的密度 dMe（最小/中位/最大）：" + "；".join(
        f"{k} boxedIn={b} {min(v):.0f}/{sorted(v)[len(v) // 2]:.0f}/{max(v):.0f}（{len(v)} 条）" for (k, b), v in sorted(dme.items())))
    print("  受捐方当时的密度 dAlly（最小/中位/最大）：" + "；".join(
        f"{k} boxedIn={b} {min(v):.0f}/{sorted(v)[len(v) // 2]:.0f}/{max(v):.0f}（{len(v)} 条）" for (k, b), v in sorted(dally.items())))
    print("  受捐方比捐方密（dAlly > dMe）的条数：" + "；".join(f"{k} {denser[k]}/{kinds[k]}" for k in kinds)
          + "｜受捐方已过软上限（dAlly ≥ 100）的条数：" + "；".join(f"{k} {over100[k]}/{kinds[k]}" for k in kinds))
    print("  按 1000 拍：" + "；".join(f"{s}~{s + 999} " + " ".join(f"{k}×{c}" for k, c in v.most_common()) for s, v in sorted(by_seg.items())))
    if "--list" in args:
        for t, r in rows:
            print(f"{t} {r['bot']} {r['kind']} pct {r['pct']} -> {r['targetName']} | boxed {r['boxedIn']} B {r['myBal']} dMe {r['dMe']} dAlly {r['dAlly']} | rej {r['likelyRejected']}")


if __name__ == "__main__":
    main()
