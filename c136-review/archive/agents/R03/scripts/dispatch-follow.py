#!/usr/bin/env python3
"""dispatch-follow.py — 进攻档调度（offense_dispatch）发出之后，受捐方有没有真的去打真人。

调度层（Vb tryDonateToTeammate L4457-4459）把受捐方判成「正在推进 / 身边有猎物」才走进攻档：
    activePush     = 受捐方压在真人身上的在途兵 ≥ 它余额的 6% 且密度 < 96
    hasPreyOpening = 受捐方有敌邻，且（敌邻在掉血 或 敌邻密度 < 0.70×受捐方密度），且受捐方密度 < 96
出手层（buyLand L5350-5359）是另一套门槛：报价 < worth 才打（见 worthgate.py）。
这个脚本把两层对一遍：每条进攻档调度（events.csv 的 DISPATCH 行，页面本地拍 t）之后 (t, t+W] 拍里，
受捐方在重放 cmdLog 里有没有落地一条「目标是在线真人」的陆攻。W 默认 150。
同时数：调度发出前 (t−W, t] 受捐方有没有打过真人（区分「正在推进」和「只是身边有猎物」）。

输出：按 1000 拍分段、按受捐方：进攻档调度条数、之后 W 拍内受捐方打过真人的条数、之前之后都没打过的条数；
      「之前之后都没打过」的最长连续段（同一受捐方）：起止拍、条数、捐方个数。

用法：python3 scripts/dispatch-follow.py <局> [--window 150]
"""
import collections
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.environ.get("C136_DATA", "/agent/repos/c136-data")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        sys.exit(2)
    mid = args[0]
    W = int(sys.argv[sys.argv.index("--window") + 1]) if "--window" in sys.argv else 150
    d = json.load(open(os.path.join(ROOT, "out", "cache", f"{mid}-resim.json")))
    H, left = d["H"], d["leftT"]
    sq = {n: v["id"] for n, v in d["squad"].items() if v["id"] >= 0 and not v.get("mismatch")}
    atk = collections.defaultdict(list)  # 号 -> 打在线真人的陆攻落地拍
    for r in d["cmdLog"]:
        if r[2] != 1 or not r[5]:
            continue
        q = r[4]
        if q >= H:
            continue
        if 0 <= left[q] <= r[0]:
            continue  # 离线空壳按 AI 算
        atk[r[1]].append(r[0])
    rows = []
    with open(os.path.join(DATA, "bundles", mid, "events.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["type"] != "DISPATCH" or r["kind"] != "offense_dispatch":
                continue
            to = r["targetName"]
            if to not in sq:
                continue
            rows.append((int(float(r["t"])), r["bot"], to))
    rows.sort()
    print(f"# {mid} 进攻档调度之后受捐方有没有打真人（dispatch-follow.py；窗口 {W} 拍；调度 = events.csv 的 offense_dispatch，出手 = 重放 cmdLog 里对在线真人落地的陆攻）")
    if not rows:
        print("  没有进攻档调度")
        return
    seg = collections.defaultdict(lambda: [0, 0, 0])
    by_to = collections.defaultdict(lambda: [0, 0, 0])
    flags = []
    for t, frm, to in rows:
        ts = atk.get(sq[to], [])
        after = any(t < x <= t + W for x in ts)
        before = any(t - W < x <= t for x in ts)
        idle = (not after) and (not before)
        for acc in (seg[t // 1000 * 1000], by_to[to]):
            acc[0] += 1
            acc[1] += 1 if after else 0
            acc[2] += 1 if idle else 0
        flags.append((t, frm, to, idle))
    tot = [sum(v[i] for v in seg.values()) for i in range(3)]
    print(f"  合计：进攻档调度 {tot[0]} 条；之后 {W} 拍内受捐方打过真人的 {tot[1]} 条；前后 {W} 拍都没打过真人的 {tot[2]} 条")
    print("  按 1000 拍：" + "；".join(f"{s}~{s + 999} 调度 {v[0]}、之后打了 {v[1]}、前后都没打 {v[2]}" for s, v in sorted(seg.items())))
    print("  按受捐方：" + "；".join(f"{n} 调度 {v[0]}、之后打了 {v[1]}、前后都没打 {v[2]}" for n, v in sorted(by_to.items(), key=lambda kv: -kv[1][0])))
    runs = []
    cur = {}
    for t, frm, to, idle in flags:
        c = cur.get(to)
        if idle:
            if c is None:
                cur[to] = [t, t, 1, {frm}]
            else:
                c[1] = t; c[2] += 1; c[3].add(frm)
        elif c is not None:
            runs.append((to, c))
            cur.pop(to)
    for to, c in cur.items():
        runs.append((to, c))
    runs.sort(key=lambda x: -x[1][2])
    print("  「前后都没打过真人」的最长连续段（同一受捐方，中间没有一条调度落在它打真人的窗口里）：")
    for to, c in runs[:6]:
        print(f"    {to}：{c[0]}~{c[1]} 拍，{c[2]} 条调度，来自 {len(c[3])} 个号（{'、'.join(sorted(c[3]))}）")


if __name__ == "__main__":
    main()
