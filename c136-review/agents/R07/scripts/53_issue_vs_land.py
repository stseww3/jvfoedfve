#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""53_issue_vs_land.py — R07：真号自己数的指令数 vs 录像里落地的指令数（不靠影子）。

来源：
  bundles/<id>/in_game.log 的 [HL-TICK] 行：每个号每 90 拍一条，cmds= 是策略自己数的「本地引擎接受了的指令」累计条数
      （Strategy.send 里 `if (ok) this.cmds++`，船、捐兵同样计数；选点不计）。
  bundles/<id>/results.csv 的 accepted：出局 / 终局时的同一个计数。
  out/<id>/humans_cmd.tsv：真引擎重放录像得到的逐条指令（落地拍；squad==1 是我方号）。
算三件事：
  A. 每个快照拍：全队累计「发出」/「落地」/ 差（= 发了还没落地，或再也没落地）。
  B. 每个号：最终发出、落地、没落地的条数；差的峰值。
  C. 不靠影子的迟到下限：对相邻三个快照 s0 < s1 < s2（各隔 90 拍），
     落地在 (s1, s2] 的条数 − 发出在 (s0, s2] 的条数，若为正，这么多条一定是 s0 之前发出、s1 之后落地的，
     也就是晚了 90 拍以上（各个落地区间互不重叠，可以相加）。同理隔两个快照是 180 拍以上。
用法：python3 53_issue_vs_land.py <matchId> [<matchId> ...]
输出：out/<matchId>/issue_vs_land.txt；多局时屏幕上另打一张汇总。
"""
import bisect
import csv
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = "/agent/repos/c136-data"
TICK_RE = re.compile(r"\[(\w+)\] \[HL-TICK\] t=(\d+) .*?cmds=(\d+)")


def load(mid):
    issued = defaultdict(dict)
    with open(os.path.join(DATA, "bundles", mid, "in_game.log"), encoding="utf-8", errors="replace") as f:
        for line in f:
            m = TICK_RE.search(line)
            if m:
                issued[m.group(1)][int(m.group(2))] = int(m.group(3))
    final = {}
    rp = os.path.join(DATA, "bundles", mid, "results.csv")
    if os.path.exists(rp):
        with open(rp, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                try:
                    final[r["bot"]] = (int(r["tick"]), int(r["accepted"]), r["event"])
                except (ValueError, KeyError):
                    pass
    land = defaultdict(list)
    hp = os.path.join(HERE, "..", "out", mid, "humans_cmd.tsv")
    if not os.path.exists(hp):
        return None
    with open(hp, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if r.get("squad") != "1":
                continue
            name = r["name"].split("] ")[-1].strip()
            land[name].append(int(r["t"]))
    for b in land:
        land[b].sort()
    return issued, final, land


def landed_upto(ts, t):
    return bisect.bisect_right(ts, t)


def one(mid):
    got = load(mid)
    if got is None:
        return None
    issued, final, land = got
    bots = sorted(issued)
    snaps = sorted({t for b in bots for t in issued[b]})
    lines = [f"# {mid} 真号自己数的指令 vs 录像落地（53_issue_vs_land.py；发出 = [HL-TICK] cmds=，落地 = humans_cmd.tsv 里我方号的全部指令）",
             "# 差 = 发出 − 落地（同一拍；> 0 的部分要么还在路上，要么再也没落地）", "",
             "A. 全队逐快照（只列每 270 拍一行和差的峰值附近）：拍 | 有快照的号 | 累计发出 | 累计落地 | 差 | 本段发出 / 本段落地"]
    prev = None
    rowsA = []
    for t in snaps:
        have = [b for b in bots if t in issued[b]]
        iss = sum(issued[b][t] for b in have)
        lan = sum(landed_upto(land.get(b, []), t) for b in have)
        rowsA.append((t, len(have), iss, lan))
    peak = max(rowsA, key=lambda r: r[2] - r[3]) if rowsA else None
    for i, (t, n, iss, lan) in enumerate(rowsA):
        if t % 270 == 0 or (peak and t == peak[0]) or i == len(rowsA) - 1:
            d = ""
            if prev:
                d = f"{iss - prev[2]} / {lan - prev[3]}"
            lines.append(f"  {t}\t{n}\t{iss}\t{lan}\t{iss - lan}\t{d}")
            prev = (t, n, iss, lan)
    lines.append("")
    lines.append("B. 各号：最后一个计数（拍；来源）| 发出 | 落地 | 没落地（占发出）| 差的峰值（拍）")
    tot_i = tot_l = 0
    for b in bots:
        ts = sorted(issued[b])
        if b in final:
            ft, fi, ev = final[b]
            src = f"results.csv {ev}"
        else:
            ft, fi, src = ts[-1], issued[b][ts[-1]], "最后一条 HL-TICK"
        fl = len(land.get(b, []))
        pk = max(ts, key=lambda t: issued[b][t] - landed_upto(land.get(b, []), t))
        pkv = issued[b][pk] - landed_upto(land.get(b, []), pk)
        tot_i += fi
        tot_l += fl
        lines.append(f"  {b}\t{ft}（{src}）\t{fi}\t{fl}\t{fi - fl}（{100 * (fi - fl) / max(1, fi):.0f}%）\t{pkv}（{pk}）")
    lines.append(f"  合计\t\t{tot_i}\t{tot_l}\t{tot_i - tot_l}（{100 * (tot_i - tot_l) / max(1, tot_i):.0f}%）")
    lines.append("")
    lines.append("C. 不靠影子的迟到下限（各号相加）：时段（按落地拍）| 落地条数 | 其中一定晚 >90 拍的 | 一定晚 >180 拍的")
    per = [(0, 600), (600, 1500), (1500, 3000), (3000, 10 ** 9)]
    agg = {p: [0, 0, 0] for p in per}
    ex = []
    for b in bots:
        ts = sorted(issued[b])
        lt = land.get(b, [])
        for k in range(2, len(ts)):
            s0, s1, s2 = ts[k - 2], ts[k - 1], ts[k]
            if s2 - s1 != 90 or s1 - s0 != 90:
                continue
            ln = landed_upto(lt, s2) - landed_upto(lt, s1)
            late90 = max(0, ln - (issued[b][s2] - issued[b][s0]))
            late180 = 0
            if k >= 3 and ts[k - 3] == s0 - 90:
                late180 = max(0, ln - (issued[b][s2] - issued[b][ts[k - 3]]))
            for p in per:
                if p[0] <= s1 < p[1]:
                    agg[p][0] += ln
                    agg[p][1] += late90
                    agg[p][2] += late180
            if late90 >= 5:
                ex.append((late90, b, s1, s2, ln, issued[b][s0], issued[b][s2], late180))
    for p in per:
        lab = f"{p[0]}~{p[1]}" if p[1] < 10 ** 9 else f"{p[0]}+"
        lines.append(f"  {lab}\t{agg[p][0]}\t{agg[p][1]}\t{agg[p][2]}")
    ex.sort(reverse=True)
    if ex:
        lines.append("  例（一定晚 >90 拍的条数最多的几段）：" + "；".join(
            f"{b} 落地在 ({s1}, {s2}] 的 {ln} 条里至少 {l90} 条是 t≤{s1 - 90} 发的（cmds {i0}→{i2}）" + (f"、至少 {l180} 条是 t≤{s1 - 180} 发的" if l180 else "")
            for l90, b, s1, s2, ln, i0, i2, l180 in ex[:8]))
    out_dir = os.path.join(HERE, "..", "out", mid)
    os.makedirs(out_dir, exist_ok=True)
    open(os.path.join(out_dir, "issue_vs_land.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    return {"mid": mid, "issued": tot_i, "landed": tot_l, "peak": peak, "agg": agg, "lines": lines}


def main():
    mids = sys.argv[1:]
    if len(mids) == 1:
        r = one(mids[0])
        print("\n".join(r["lines"]) if r else f"{mids[0]}: 没有 humans_cmd.tsv")
        return
    print("局\t发出\t落地\t没落地（占发出）\t差的峰值（拍）\t一定晚 >90 拍：0~600 / 600~1500 / 1500~3000 / 3000+")
    for mid in mids:
        r = one(mid)
        if not r:
            print(f"{mid}\t（没有 humans_cmd.tsv）")
            continue
        pk = r["peak"]
        a = r["agg"]
        print(f"{mid}\t{r['issued']}\t{r['landed']}\t{r['issued'] - r['landed']}（{100 * (r['issued'] - r['landed']) / max(1, r['issued']):.0f}%）\t"
              f"{pk[2] - pk[3]}（{pk[0]}）\t" + " / ".join(str(a[p][1]) for p in a))


if __name__ == "__main__":
    main()
