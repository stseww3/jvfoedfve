#!/usr/bin/env python3
"""Roster edit of 11-16 12:54: six dead nodes replaced (ctrl 12:49), the size of the train (director 12:50)."""
import re

p = "/agent/repos/c164-aide-f3-b9ab/c164-realms/plan/ROSTER.md"
t = open(p, encoding="utf-8").read()


def swap(old, new):
    global t
    assert t.count(old) == 1, (t.count(old), old)
    t = t.replace(old, new)


NEW = {329: ("node43", "node117"), 332: ("node46", "node118"), 335: ("node49", "node119"),
       338: ("node52", "node120"), 341: ("node55", "node121"), 344: ("node58", "node122")}
lines = t.split("\n")
done = 0
for i, line in enumerate(lines):
    m = re.match(r"^\| ([a-z0-9]+) \| c(\d{3}) \| ([^|]*) \| ", line)
    if not m or int(m.group(2)) not in NEW:
        continue
    old, new = NEW[int(m.group(2))]
    cell = m.group(3)
    assert cell.count(old) == 1, (cell, old)
    cell = cell.replace(old, "%s（%s 是废槽，12:49 换的）" % (new, old))
    lines[i] = "| %s | c%s | %s | %s" % (m.group(1), m.group(2), cell, line[m.end():])
    done += 1
assert done == 6, done
t = "\n".join(lines)

swap(
    "主 Agent 只剩一台在带七十多个会话（总控 12:33）",
    "**12:49 总控：node43、46、49、52、55、58 是拉不回来的废槽，作废别投，换成 cloud node117、review node118、m1 node119、cable node120、lamps node121、scope node122**（总监助理 g2 #1809）；谁的号探两次不通就私信总监助理，等的时候用公共池。"
    "主 Agent 只剩一台在带七十多个会话（总控 12:33）",
)
swap(
    "| 甲 `machines/train`（机车新做，现有的车当客车，齿条） | cable（牵头）、m1（机车） | cr3 |",
    "| 甲 `machines/train`（机车新做，现有的车当客车，齿条）。**总监 12:50 定大小**：客车约 5 格长、3 格宽（两节车身的模型接起来），停站时西端的门在 x 90，车身伸到 x 95；机车约 3.5 格，紧接其东；一台机车推一节客车，不加第二节。座位 12 个，横排长椅 4 排、一排 3 个（2 加 1），全部朝上山的方向，前端整面的窗。车厢里照 `plan/fine.md` 做到近层，是全图最细的一处。a4 改 `_rail.py` 的 CAR、ENGINE、STOP、MOUTH；a2 座位 12 个；mast 上车从前排坐起 | cable（牵头）、m1（机车）；人手不够向总监助理要一个（车厢内饰可以分出去） | cr3 |",
)
open(p, "w", encoding="utf-8").write(t)
print("ok")
