#!/usr/bin/env python3
"""xcheck_trace.py — R01 的实录阶梯（三种口径）对 R06 入库的 traces/<局>.json：同一条落地指令，两边定的决策拍一样不一样。

两边互相独立：各自的影子实现、各自的配对规则。能对照的是两边都有的局（R06 给了 A023、A057、B039）。
按（席位, 落地拍, 种类）把两边的条目对齐（同一拍落地多条时，各自按决策拍排序后逐条对）。

用法：python3 scripts/ckpt/xcheck_trace.py [局号…]
输出：reports/ckpt-data/trace_xcheck.csv 与逐局一段摘要
"""
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
R01 = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(R01, 'reports', 'ckpt-data')
R06 = os.path.join(R01, '..', '..', 'archive', 'agents', 'R06', 'sim-v2', 'traces')
MIDS = ['A023', 'A057', 'B039']


def load(path):
    t = json.load(open(path))
    by = {}
    for p, rows in t['seats'].items():
        for r in rows:
            by.setdefault((p, r[1], r[2]), []).append(r[0])
    for v in by.values():
        v.sort()
    return by


def main():
    mids = sys.argv[1:] or MIDS
    out = []
    for mid in mids:
        f6 = os.path.join(R06, mid + '.json')
        if not os.path.exists(f6):
            print(f'{mid}: R06 没有这一局的阶梯')
            continue
        b6 = load(f6)
        n6 = sum(len(v) for v in b6.values())
        located = load(os.path.join(DATA, 'traces', mid + '.json'))
        for variant, sub in (('located', 'traces'), ('hi', 'traces-hi'), ('lo', 'traces-lo')):
            b1 = load(os.path.join(DATA, sub, mid + '.json'))
            n1 = sum(len(v) for v in b1.values())
            common = same = near = 0
            d_all = []
            # 只看「定位不唯一」的那部分（located 里没有、这一口径补上的）
            add_common = add_same = add_near = 0
            d_add = []
            for k, v1 in b1.items():
                v6 = b6.get(k)
                if not v6:
                    continue
                base = len(located.get(k, []))
                for i, (a, b) in enumerate(zip(v1, v6)):
                    common += 1
                    same += a == b
                    near += abs(a - b) <= 10
                    d_all.append(a - b)
                    # 这一拍里 located 没收全的，算作补上的
                    if len(v1) > base:
                        add_common += 1
                        add_same += a == b
                        add_near += abs(a - b) <= 10
                        d_add.append(a - b)
            med = lambda a: sorted(a)[len(a) // 2] if a else ''
            row = dict(mid=mid, variant=variant, r01Pairs=n1, r06Pairs=n6, common=common, sameTau=same, within10=near, medDiff=med(d_all),
                       addedCommon=add_common, addedSameTau=add_same, addedWithin10=add_near, addedMedDiff=med(d_add))
            out.append(row)
            print(f"{mid} {variant:7s}: R01 {n1} 条、R06 {n6} 条，两边都有的 {common} 条里决策拍相同 {same}（{100 * same / max(1, common):.0f}%）、差 ≤10 拍 {near}；"
                  f"其中含补上条目的落地拍 {add_common} 条：相同 {add_same}、差 ≤10 拍 {add_near}，R01−R06 的决策拍中位差 {med(d_add)}")
    if out:
        with open(os.path.join(DATA, 'trace_xcheck.csv'), 'w', newline='') as fo:
            w = csv.DictWriter(fo, fieldnames=list(out[0].keys()))
            w.writeheader()
            w.writerows(out)


if __name__ == '__main__':
    main()
