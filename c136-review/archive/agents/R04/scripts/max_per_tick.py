#!/usr/bin/env python3
"""同一个玩家同一拍落地的指令条数（不含选点）：每局的最大值和分布。

用法：python3 scripts/max_per_tick.py [局号 ...]      不给局号 = tmp/truth/ 下所有已重放的局
数据：tmp/truth/<局号>/cmd.tsv（真引擎重放录下的每一条指令）、our.tsv（我方号的座位）。
用途：核对「成摞落地每批最多 9 条」是不是每一局都成立，以及别的玩家有没有超过 9 的。
"""
import collections
import csv
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TRUTH = os.path.join(HERE, "..", "tmp", "truth")


def seats(path):
    s = set()
    if not os.path.exists(path):
        return s
    with open(path) as fh:
        rd = csv.DictReader(fh, delimiter="\t")
        for r in rd:
            s.add(r["p"])
    return s


def scan(mid):
    d = os.path.join(TRUTH, mid)
    ours = seats(os.path.join(d, "our.tsv"))
    mine, rest = collections.Counter(), collections.Counter()
    with open(os.path.join(d, "cmd.tsv")) as fh:
        rd = csv.DictReader(fh, delimiter="\t")
        for r in rd:
            if r["spawnStep"] not in ("-1", ""):
                continue
            key = (r["t"], r["p"])
            (mine if r["p"] in ours else rest)[key] += 1
    return ours, mine, rest


def desc(c):
    if not c:
        return "没有指令"
    dist = collections.Counter(c.values())
    mx = max(dist)
    top = "，".join(f"{k} 条×{dist[k]}" for k in sorted(dist, reverse=True)[:4])
    return f"最多 {mx} 条（{top}）"


def main():
    ids = sys.argv[1:] or sorted(os.path.basename(p) for p in glob.glob(os.path.join(TRUTH, "*")) if os.path.exists(os.path.join(p, "cmd.tsv")))
    print("# 同一个玩家同一拍落地的指令条数（不含选点阶段）")
    over, hit9 = [], []
    for mid in ids:
        ours, mine, rest = scan(mid)
        mx = max(mine.values()) if mine else 0
        if mx > 9:
            over.append(mid)
        if mx == 9:
            hit9.append(mid)
        print(f"  {mid}：我方 {len(ours)} 个号 {desc(mine)}；其他玩家 {desc(rest)}")
    print(f"合计 {len(ids)} 局：我方号到过 9 条的 {len(hit9)} 局，超过 9 条的 {len(over)} 局")


if __name__ == "__main__":
    main()
