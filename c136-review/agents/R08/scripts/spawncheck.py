#!/usr/bin/env python3
"""spawncheck.py — 出生点：日志里的指派序列 vs 引擎里真正落下的点。

    python3 spawncheck.py <matchId> [--quiet]

需要 out/<mid>/resim.json（真引擎重演）。日志口径：in_game.log 的 [HL-SPAWN] 行（me=号 -> (x,y)）。
输出 out/<mid>/spawncheck.txt：
  [PA] 每个号：指派条数 | 引擎落点 | 落点是第几条指派 | 最后一条指派 | 最后一条是否执行 | 离最近编队友（引擎落点）的距离
  [PB] 落在同一像素 / 相距 <40 像素的号对；最后一条指派相同的号对
  [PC] 汇总（M7 的模式计数直接读这一行）
"""
import math
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from truth import Truth, OUT  # noqa: E402

DATA = os.environ.get("C136_DATA", "/agent/repos/c136-data")


def analyse(mid):
    T = Truth(mid)
    R = T.R
    seqs = defaultdict(list)
    n_lines = 0
    with open(os.path.join(DATA, "bundles", mid, "in_game.log"), encoding="utf-8", errors="replace") as f:
        for l in f:
            if "[HL-SPAWN]" not in l:
                continue
            m = re.search(r"me=(\d+) .*-> \((\d+),(\d+)\)", l)
            if m:
                n_lines += 1
                seqs[int(m.group(1))].append((int(m.group(2)), int(m.group(3))))
    rows = []
    ids = sorted(T.sqIds)
    for p in ids:
        e = tuple(R["spawnXY"][p]) if R["spawnXY"][p] else None
        seq = seqs.get(p, [])
        hit = [i + 1 for i, q in enumerate(seq) if q == e]
        others = [(math.dist(e, R["spawnXY"][q]), q) for q in ids if q != p and e and R["spawnXY"][q]]
        near = min(others) if others else (None, None)
        rows.append(dict(p=p, name=T.names[p], team=T.team(p), n=len(seq), engine=e, hit=hit, last=seq[-1] if seq else None,
                         lastExecuted=bool(seq) and seq[-1] == e, inLog=bool(hit), nearDist=near[0], nearId=near[1]))
    pairs = []
    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            if a["engine"] and b["engine"]:
                d = math.dist(a["engine"], b["engine"])
                if d < 40:
                    pairs.append((d, a, b))
    same_last = []
    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            if a["last"] and a["last"] == b["last"]:
                same_last.append((a, b))
    return T, rows, sorted(pairs, key=lambda x: x[0]), same_last, n_lines


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1
    mid = args[0]
    T, rows, pairs, same_last, n_lines = analyse(mid)
    out = [f"[PA] {mid} 出生点：日志 [HL-SPAWN] {n_lines} 行。号 | 队 | 指派条数 | 引擎落点 | 落点是第几条指派 | 最后一条指派 | 最后一条执行了吗 | 最近编队友（距离）"]
    for r in rows:
        out.append(f"     {r['name']:<12} | T{r['team']} | {r['n']:>2} | {r['engine']} | {r['hit'] or '不在日志里'} | {r['last']} | {'是' if r['lastExecuted'] else '否'} | "
                   f"{T.names[r['nearId']] if r['nearId'] is not None else '-'}（{r['nearDist']:.0f}）" if r["nearDist"] is not None else "")
    out.append("[PB] 引擎落点相距 <40 像素的号对：" + ("；".join(f"{a['name']}(T{a['team']}) 与 {b['name']}(T{b['team']}) {d:.0f} 像素 {a['engine']}/{b['engine']}" for d, a, b in pairs) or "无"))
    out.append("     最后一条指派是同一个点的号对：" + ("；".join(f"{a['name']} 与 {b['name']} {a['last']}" for a, b in same_last) or "无"))
    n = len(rows)
    n_last = sum(1 for r in rows if r["lastExecuted"])
    n_notlog = sum(1 for r in rows if not r["inLog"])
    d_near = sorted(r["nearDist"] for r in rows if r["nearDist"] is not None)
    out.append(f"[PC] 汇总：{n} 个号，人均指派 {sum(r['n'] for r in rows) / max(n, 1):.1f} 条；最后一条指派被执行 {n_last} 个；引擎落点不在日志指派里 {n_notlog} 个；"
               f"同像素号对 {sum(1 for d, a, b in pairs if d == 0)}；<40 像素号对 {len(pairs)}；最后一条指派相同的号对 {len(same_last)}；"
               f"最近编队友距离 中位 {d_near[len(d_near) // 2] if d_near else 0:.0f}、最小 {d_near[0] if d_near else 0:.0f}")
    txt = "\n".join(out)
    with open(os.path.join(OUT, mid, "spawncheck.txt"), "w", encoding="utf-8") as f:
        f.write(txt + "\n")
    if "--quiet" not in args:
        print(txt)
    else:
        print(out[-1])
    return 0


if __name__ == "__main__":
    sys.exit(main())
