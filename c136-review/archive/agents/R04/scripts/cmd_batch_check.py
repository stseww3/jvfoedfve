#!/usr/bin/env python3
"""cmd_batch_check.py — 核对“联机指令每 7 拍成批执行”：录像里出生阶段之后的每条指令，执行拍号对 7 取余的分布。
另外统计同一拍里同一个人同一种指令出现多次的情况（多条指令挤进同一批）。
用法：cd c136-review/agents/R04 && timeout 120 python3 scripts/cmd_batch_check.py [局...] > out/cmd-batch-check.txt
"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from replay_lib import load_replay  # noqa: E402

MINE = ['A022', 'A038', 'A029', 'A073', 'A047', 'A083', 'A099', 'A078', 'A015', 'A081', 'A086', 'A013', 'B034']
tot = Counter()
for mid in (sys.argv[1:] or MINE):
    r = load_replay(f'/agent/repos/c136-data/bundles/{mid}/replay.txt')
    rows = [x for x in r['rows'] if x[1] >= 0]
    c = Counter(x[1] % 7 for x in rows)
    tot.update(c)
    same = Counter((x[1], x[3], x[2]) for x in rows)
    multi = sum(1 for v in same.values() if v > 1)
    mx = max(same.values()) if same else 0
    per_batch = Counter(x[1] for x in rows)
    print(f"{mid}: 真人 {r['H']}，出生阶段后指令 {len(rows)} 条；拍号%7 分布 {dict(sorted(c.items()))}；"
          f"同一拍同一人同一种指令出现多次的组数 {multi}（最多 {mx} 条）；单批最多 {max(per_batch.values()) if per_batch else 0} 条指令")
print(f"合计：拍号%7 分布 {dict(sorted(tot.items()))}")
