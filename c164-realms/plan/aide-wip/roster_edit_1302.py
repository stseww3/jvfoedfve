#!/usr/bin/env python3
"""Roster edit of 11-16 13:02: orrery dropped at 12:52, the four re-pulled at 12:53; tower and cr2 on new nodes;
the public pool as it stands; a3 takes the loose pieces of the carriage."""
p = "/agent/repos/c164-aide-f3-b9ab/c164-realms/plan/ROSTER.md"
t = open(p, encoding="utf-8").read()


def swap(old, new):
    global t
    assert t.count(old) == 1, (t.count(old), old)
    t = t.replace(old, new)


swap(
    "comet 手上没有收尾的活，不补人。再有人掉线，总监助理直接报总监谁手上有四件事里的活。",
    "comet 手上没有收尾的活，不补人。再有人掉线，总监助理直接报总监谁手上有四件事里的活。"
    "**12:52 orrery（c343）也掉了；12:53 总监请总控把四位都重拉了（上下文留着；机器 orrery node57、stair node51、hall node62、comet node44），回来的先私信总监助理报到、读 `plan/fine.md`，代着的人把那一块交回**："
    "行星仪还是 orrery 的（气象站的风向标、自记气压计和前庭测风杆留给 power，探空气球先放）；星厅还 hall（天花的星座轮流亮、弧光灯、正门的铁门留给 lights）；大台阶还 stair；comet 回来找 cr2。十分钟没报到的，总监助理报总监再拉。",
)
swap("| tower | c327 | node41 | ", "| tower | c327 | node83（node41 是废槽，12:54 换的） | ")
swap("| cr2 | c333 | node47 | ", "| cr2 | c333 | node8（node47 是废槽，12:54 换的；node8 别人别再投） | ")
swap(
    "| orrery | c343 | node57 | c236 | machines/orrery | ",
    "| orrery | c343 | node57 | c236 | machines/orrery（**11-16 12:52 会话掉了，12:53 重拉**；回来还是他的，照 `plan/fine.md` 做到近层：月亮、传动轴、蜗杆；气象站三样和前庭测风杆 12:55 给了 power） | ",
)
swap(
    "| a3 | c349 | node63 | c178 | interiors/domeroom | ",
    "| a3 | c349 | node63 | c178 | interiors/domeroom；**11-16 12:56 起帮 cable 做火车客车里的散件**（行李箱和仪器箱、摇着的吊灯、时刻表、搪瓷号牌；单独的模型，跟车走；读 `cursor/c164-cable-train-f3-9cf7` 的 `machines/train.py`；cr3 批）；风暴信号杆排在它后面 | ",
)
swap(
    "**12:49 总控：node43、46、49、52、55、58 是拉不回来的废槽，作废别投，换成 cloud node117、review node118、m1 node119、cable node120、lamps node121、scope node122**（总监助理 g2 #1809）；谁的号探两次不通就私信总监助理，等的时候用公共池。",
    "**12:49 总控：node43、46、49、52、55、58 是拉不回来的废槽，作废别投，换成 cloud node117、review node118、m1 node119、cable node120、lamps node121、scope node122**（总监助理 g2 #1809）；**12:54 又两台废槽：node41 换成 tower node83，node47 换成 cr2 node8（node8 从此是 cr2 自己的，别人的长单改投自己的机器）**；smoke 的 node69 没死，是卡在前一单上，别重投，等它回执，这期间用 node85。"
    "**公共池 12:55 起**（都对 c318–c361 开着）：node73–76 和 node90–92 给 s2 轮着查头，node77–80 是火车线的第二台，node84、85–89、107–116 谁的号不通就私信总监助理要一个，不要自己挑（免得撞单）。谁的号探两次不通就私信总监助理。",
)
open(p, "w", encoding="utf-8").write(t)
print("ok")
